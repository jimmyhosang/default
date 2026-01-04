/**
 * Unified AI Browser Extension - Popup Script
 */

// Default configuration
const DEFAULT_CONFIG = {
  serverUrl: 'http://localhost:8000',
  includeMetadata: true,
  includeLinks: true,
  includeImages: false,
};

// State
let config = { ...DEFAULT_CONFIG };
let recentCaptures = [];

// DOM Elements
const elements = {
  status: null,
  capturePageBtn: null,
  captureSelectionBtn: null,
  captureClipboardBtn: null,
  serverUrl: null,
  saveConfigBtn: null,
  testConnectionBtn: null,
  includeMetadata: null,
  includeLinks: null,
  includeImages: null,
  capturesList: null,
  openDashboard: null,
  notification: null,
};

// Initialize popup
document.addEventListener('DOMContentLoaded', async () => {
  // Cache DOM elements
  Object.keys(elements).forEach(id => {
    elements[id] = document.getElementById(id);
  });

  // Load configuration
  await loadConfig();

  // Setup event listeners
  setupEventListeners();

  // Check server status
  checkServerStatus();

  // Load recent captures
  loadRecentCaptures();
});

// Load configuration from storage
async function loadConfig() {
  try {
    const stored = await chrome.storage.local.get(['config', 'recentCaptures']);
    if (stored.config) {
      config = { ...DEFAULT_CONFIG, ...stored.config };
    }
    if (stored.recentCaptures) {
      recentCaptures = stored.recentCaptures;
    }

    // Update UI
    elements.serverUrl.value = config.serverUrl;
    elements.includeMetadata.checked = config.includeMetadata;
    elements.includeLinks.checked = config.includeLinks;
    elements.includeImages.checked = config.includeImages;
  } catch (error) {
    console.error('Failed to load config:', error);
  }
}

// Save configuration
async function saveConfig() {
  try {
    config.serverUrl = elements.serverUrl.value.trim();
    config.includeMetadata = elements.includeMetadata.checked;
    config.includeLinks = elements.includeLinks.checked;
    config.includeImages = elements.includeImages.checked;

    await chrome.storage.local.set({ config });
    showNotification('Configuration saved', 'success');
  } catch (error) {
    showNotification('Failed to save configuration', 'error');
  }
}

// Setup event listeners
function setupEventListeners() {
  elements.capturePageBtn.addEventListener('click', capturePage);
  elements.captureSelectionBtn.addEventListener('click', captureSelection);
  elements.captureClipboardBtn.addEventListener('click', captureClipboard);
  elements.saveConfigBtn.addEventListener('click', saveConfig);
  elements.testConnectionBtn.addEventListener('click', testConnection);
  elements.openDashboard.addEventListener('click', openDashboard);

  // Save options on change
  elements.includeMetadata.addEventListener('change', saveConfig);
  elements.includeLinks.addEventListener('change', saveConfig);
  elements.includeImages.addEventListener('change', saveConfig);
}

// Check server status
async function checkServerStatus() {
  try {
    const response = await fetch(`${config.serverUrl}/api/stats`, {
      method: 'GET',
      headers: { 'Accept': 'application/json' },
    });

    if (response.ok) {
      elements.status.textContent = 'Connected';
      elements.status.className = 'status connected';
    } else {
      throw new Error('Server error');
    }
  } catch (error) {
    elements.status.textContent = 'Disconnected';
    elements.status.className = 'status disconnected';
  }
}

// Test connection
async function testConnection() {
  elements.testConnectionBtn.disabled = true;
  elements.testConnectionBtn.textContent = 'Testing...';

  try {
    const response = await fetch(`${config.serverUrl}/api/stats`);
    if (response.ok) {
      showNotification('Connection successful!', 'success');
      elements.status.textContent = 'Connected';
      elements.status.className = 'status connected';
    } else {
      throw new Error('Server returned error');
    }
  } catch (error) {
    showNotification('Connection failed: ' + error.message, 'error');
    elements.status.textContent = 'Disconnected';
    elements.status.className = 'status disconnected';
  } finally {
    elements.testConnectionBtn.disabled = false;
    elements.testConnectionBtn.textContent = 'Test';
  }
}

// Capture current page
async function capturePage() {
  elements.capturePageBtn.disabled = true;

  try {
    // Get current tab
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

    // Execute content script to extract page content
    const results = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: extractPageContent,
      args: [config.includeLinks, config.includeImages],
    });

    const pageContent = results[0].result;

    // Prepare capture data
    const captureData = {
      source_type: 'browser',
      content: pageContent.text,
      metadata: config.includeMetadata ? {
        url: tab.url,
        title: tab.title,
        links: pageContent.links,
        images: pageContent.images,
        captured_at: new Date().toISOString(),
      } : { url: tab.url, title: tab.title },
    };

    // Send to server
    await sendCapture(captureData);

    showNotification('Page captured successfully!', 'success');
    addToRecentCaptures(tab.title, 'page');
  } catch (error) {
    showNotification('Failed to capture page: ' + error.message, 'error');
  } finally {
    elements.capturePageBtn.disabled = false;
  }
}

// Capture selection
async function captureSelection() {
  elements.captureSelectionBtn.disabled = true;

  try {
    // Get current tab
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

    // Execute content script to get selection
    const results = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: () => window.getSelection().toString(),
    });

    const selectedText = results[0].result;

    if (!selectedText || selectedText.trim() === '') {
      showNotification('No text selected', 'warning');
      return;
    }

    // Prepare capture data
    const captureData = {
      source_type: 'browser_selection',
      content: selectedText,
      metadata: {
        url: tab.url,
        title: tab.title,
        captured_at: new Date().toISOString(),
      },
    };

    // Send to server
    await sendCapture(captureData);

    showNotification('Selection captured!', 'success');
    addToRecentCaptures(`Selection from ${tab.title}`, 'selection');
  } catch (error) {
    showNotification('Failed to capture selection: ' + error.message, 'error');
  } finally {
    elements.captureSelectionBtn.disabled = false;
  }
}

// Capture clipboard
async function captureClipboard() {
  elements.captureClipboardBtn.disabled = true;

  try {
    const text = await navigator.clipboard.readText();

    if (!text || text.trim() === '') {
      showNotification('Clipboard is empty', 'warning');
      return;
    }

    // Prepare capture data
    const captureData = {
      source_type: 'clipboard',
      content: text,
      metadata: {
        captured_at: new Date().toISOString(),
      },
    };

    // Send to server
    await sendCapture(captureData);

    showNotification('Clipboard captured!', 'success');
    addToRecentCaptures('Clipboard content', 'clipboard');
  } catch (error) {
    showNotification('Failed to read clipboard: ' + error.message, 'error');
  } finally {
    elements.captureClipboardBtn.disabled = false;
  }
}

// Extract page content (injected into page)
function extractPageContent(includeLinks, includeImages) {
  // Get main text content
  const textContent = document.body.innerText || '';

  const result = {
    text: textContent.substring(0, 50000), // Limit to 50KB
    links: [],
    images: [],
  };

  // Extract links
  if (includeLinks) {
    const links = document.querySelectorAll('a[href]');
    result.links = Array.from(links)
      .map(a => ({ text: a.innerText.trim(), href: a.href }))
      .filter(l => l.text && l.href.startsWith('http'))
      .slice(0, 100); // Limit to 100 links
  }

  // Extract images
  if (includeImages) {
    const images = document.querySelectorAll('img[alt]');
    result.images = Array.from(images)
      .map(img => ({ alt: img.alt, src: img.src }))
      .filter(i => i.alt)
      .slice(0, 50); // Limit to 50 images
  }

  return result;
}

// Send capture to server
async function sendCapture(data) {
  const response = await fetch(`${config.serverUrl}/api/content`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    throw new Error(`Server returned ${response.status}`);
  }

  return response.json();
}

// Add to recent captures
async function addToRecentCaptures(title, type) {
  const capture = {
    title: title.substring(0, 50),
    type,
    timestamp: new Date().toISOString(),
  };

  recentCaptures.unshift(capture);
  recentCaptures = recentCaptures.slice(0, 10); // Keep last 10

  await chrome.storage.local.set({ recentCaptures });
  renderRecentCaptures();
}

// Load recent captures from storage
async function loadRecentCaptures() {
  renderRecentCaptures();
}

// Render recent captures list
function renderRecentCaptures() {
  if (recentCaptures.length === 0) {
    elements.capturesList.innerHTML = '<p class="empty">No captures yet</p>';
    return;
  }

  elements.capturesList.innerHTML = recentCaptures.map(capture => {
    const time = new Date(capture.timestamp).toLocaleTimeString();
    const icon = capture.type === 'page' ? '📄' : capture.type === 'selection' ? '✂️' : '📋';
    return `
      <div class="capture-item">
        <span class="capture-icon">${icon}</span>
        <span class="capture-title">${escapeHtml(capture.title)}</span>
        <span class="capture-time">${time}</span>
      </div>
    `;
  }).join('');
}

// Open dashboard
function openDashboard(e) {
  e.preventDefault();
  chrome.tabs.create({ url: config.serverUrl });
}

// Show notification
function showNotification(message, type = 'info') {
  elements.notification.textContent = message;
  elements.notification.className = `notification ${type}`;
  elements.notification.classList.remove('hidden');

  setTimeout(() => {
    elements.notification.classList.add('hidden');
  }, 3000);
}

// Escape HTML
function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}
