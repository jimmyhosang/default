/**
 * Unified AI Browser Extension - Background Service Worker
 *
 * Handles:
 * - Keyboard shortcuts
 * - Context menu actions
 * - Background capture requests
 */

// Default configuration
const DEFAULT_SERVER_URL = 'http://localhost:8000';

// Initialize extension
chrome.runtime.onInstalled.addListener(async (details) => {
  if (details.reason === 'install') {
    // Set default configuration
    await chrome.storage.local.set({
      config: {
        serverUrl: DEFAULT_SERVER_URL,
        includeMetadata: true,
        includeLinks: true,
        includeImages: false,
      },
      recentCaptures: [],
    });

    console.log('Unified AI Capture extension installed');
  }

  // Create context menu items
  chrome.contextMenus.create({
    id: 'captureSelection',
    title: 'Capture Selection to Unified AI',
    contexts: ['selection'],
  });

  chrome.contextMenus.create({
    id: 'capturePage',
    title: 'Capture Page to Unified AI',
    contexts: ['page'],
  });

  chrome.contextMenus.create({
    id: 'captureLink',
    title: 'Capture Link to Unified AI',
    contexts: ['link'],
  });

  chrome.contextMenus.create({
    id: 'captureImage',
    title: 'Capture Image Alt Text to Unified AI',
    contexts: ['image'],
  });
});

// Handle keyboard shortcuts
chrome.commands.onCommand.addListener(async (command) => {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab) return;

  switch (command) {
    case 'capture_page':
      await capturePageContent(tab);
      break;
    case 'capture_selection':
      await captureSelection(tab);
      break;
  }
});

// Handle context menu clicks
chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  switch (info.menuItemId) {
    case 'captureSelection':
      await captureSelection(tab, info.selectionText);
      break;
    case 'capturePage':
      await capturePageContent(tab);
      break;
    case 'captureLink':
      await captureLink(tab, info.linkUrl);
      break;
    case 'captureImage':
      // Note: We can't get alt text from context menu, would need content script
      await captureImage(tab, info.srcUrl);
      break;
  }
});

// Get server URL from config
async function getServerUrl() {
  const { config } = await chrome.storage.local.get(['config']);
  return config?.serverUrl || DEFAULT_SERVER_URL;
}

// Capture page content
async function capturePageContent(tab) {
  try {
    // Execute content script
    const results = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: () => {
        return {
          text: document.body.innerText.substring(0, 50000),
          title: document.title,
          url: window.location.href,
        };
      },
    });

    const pageContent = results[0].result;

    const captureData = {
      source_type: 'browser',
      content: pageContent.text,
      metadata: {
        url: pageContent.url,
        title: pageContent.title,
        captured_at: new Date().toISOString(),
      },
    };

    await sendCapture(captureData);
    showBadge('success');
    notify('Page captured', pageContent.title);
  } catch (error) {
    console.error('Capture failed:', error);
    showBadge('error');
    notify('Capture failed', error.message);
  }
}

// Capture selection
async function captureSelection(tab, selectionText = null) {
  try {
    let text = selectionText;

    if (!text) {
      const results = await chrome.scripting.executeScript({
        target: { tabId: tab.id },
        func: () => window.getSelection().toString(),
      });
      text = results[0].result;
    }

    if (!text || text.trim() === '') {
      notify('No selection', 'Please select some text first');
      return;
    }

    const captureData = {
      source_type: 'browser_selection',
      content: text,
      metadata: {
        url: tab.url,
        title: tab.title,
        captured_at: new Date().toISOString(),
      },
    };

    await sendCapture(captureData);
    showBadge('success');
    notify('Selection captured', `${text.substring(0, 50)}...`);
  } catch (error) {
    console.error('Capture failed:', error);
    showBadge('error');
    notify('Capture failed', error.message);
  }
}

// Capture link
async function captureLink(tab, linkUrl) {
  try {
    const captureData = {
      source_type: 'browser_link',
      content: linkUrl,
      metadata: {
        source_url: tab.url,
        source_title: tab.title,
        captured_at: new Date().toISOString(),
      },
    };

    await sendCapture(captureData);
    showBadge('success');
    notify('Link captured', linkUrl);
  } catch (error) {
    console.error('Capture failed:', error);
    showBadge('error');
  }
}

// Capture image
async function captureImage(tab, imageUrl) {
  try {
    const captureData = {
      source_type: 'browser_image',
      content: `Image from: ${imageUrl}`,
      metadata: {
        image_url: imageUrl,
        source_url: tab.url,
        source_title: tab.title,
        captured_at: new Date().toISOString(),
      },
    };

    await sendCapture(captureData);
    showBadge('success');
    notify('Image reference captured', imageUrl);
  } catch (error) {
    console.error('Capture failed:', error);
    showBadge('error');
  }
}

// Send capture to server
async function sendCapture(data) {
  const serverUrl = await getServerUrl();

  const response = await fetch(`${serverUrl}/api/content`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    throw new Error(`Server returned ${response.status}`);
  }

  // Update recent captures
  const { recentCaptures = [] } = await chrome.storage.local.get(['recentCaptures']);
  recentCaptures.unshift({
    title: data.metadata?.title || data.content.substring(0, 50),
    type: data.source_type,
    timestamp: new Date().toISOString(),
  });

  await chrome.storage.local.set({
    recentCaptures: recentCaptures.slice(0, 10),
  });

  return response.json();
}

// Show badge on extension icon
function showBadge(type) {
  const colors = {
    success: '#27ae60',
    error: '#e74c3c',
    pending: '#f39c12',
  };

  const text = type === 'success' ? '✓' : type === 'error' ? '!' : '...';

  chrome.action.setBadgeText({ text });
  chrome.action.setBadgeBackgroundColor({ color: colors[type] || colors.pending });

  // Clear badge after 2 seconds
  setTimeout(() => {
    chrome.action.setBadgeText({ text: '' });
  }, 2000);
}

// Show notification
function notify(title, message) {
  chrome.notifications.create({
    type: 'basic',
    iconUrl: 'icons/icon128.png',
    title: `Unified AI: ${title}`,
    message: message || '',
  });
}

// Handle messages from popup or content scripts
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'capture') {
    sendCapture(request.data)
      .then(() => sendResponse({ success: true }))
      .catch(error => sendResponse({ success: false, error: error.message }));
    return true; // Keep channel open for async response
  }

  if (request.action === 'getServerUrl') {
    getServerUrl().then(url => sendResponse({ url }));
    return true;
  }
});
