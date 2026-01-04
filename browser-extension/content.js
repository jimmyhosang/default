/**
 * Unified AI Browser Extension - Content Script
 *
 * Runs in the context of web pages.
 * Handles:
 * - Page content extraction
 * - Selection detection
 * - Visual feedback
 */

// Listen for messages from background script or popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  switch (request.action) {
    case 'extractPage':
      sendResponse(extractPageContent(request.options));
      break;

    case 'getSelection':
      sendResponse({ text: window.getSelection().toString() });
      break;

    case 'showFeedback':
      showCapturedFeedback(request.message);
      sendResponse({ success: true });
      break;

    default:
      sendResponse({ error: 'Unknown action' });
  }

  return true; // Keep channel open for async response
});

/**
 * Extract content from the current page
 */
function extractPageContent(options = {}) {
  const {
    includeLinks = true,
    includeImages = false,
    includeHeadings = true,
    maxLength = 50000,
  } = options;

  const result = {
    text: '',
    title: document.title,
    url: window.location.href,
    links: [],
    images: [],
    headings: [],
    metadata: {},
  };

  // Extract main content
  // Try to find main content area first
  const mainContent = document.querySelector('main, article, [role="main"]');
  const contentSource = mainContent || document.body;

  // Get text content
  result.text = getCleanText(contentSource, maxLength);

  // Extract metadata
  result.metadata = extractMetadata();

  // Extract links
  if (includeLinks) {
    result.links = extractLinks(contentSource);
  }

  // Extract images with alt text
  if (includeImages) {
    result.images = extractImages(contentSource);
  }

  // Extract headings
  if (includeHeadings) {
    result.headings = extractHeadings(contentSource);
  }

  return result;
}

/**
 * Get clean text content from an element
 */
function getCleanText(element, maxLength) {
  // Clone the element to avoid modifying the page
  const clone = element.cloneNode(true);

  // Remove script, style, nav, footer, aside elements
  const removeSelectors = ['script', 'style', 'nav', 'footer', 'aside', 'noscript', 'iframe'];
  removeSelectors.forEach(selector => {
    clone.querySelectorAll(selector).forEach(el => el.remove());
  });

  // Get text and clean it up
  let text = clone.innerText || '';

  // Remove excessive whitespace
  text = text
    .replace(/\s+/g, ' ')
    .replace(/\n{3,}/g, '\n\n')
    .trim();

  // Truncate if needed
  if (text.length > maxLength) {
    text = text.substring(0, maxLength) + '...';
  }

  return text;
}

/**
 * Extract page metadata
 */
function extractMetadata() {
  const metadata = {};

  // Get meta tags
  const metaTags = {
    description: 'meta[name="description"]',
    keywords: 'meta[name="keywords"]',
    author: 'meta[name="author"]',
    ogTitle: 'meta[property="og:title"]',
    ogDescription: 'meta[property="og:description"]',
    ogImage: 'meta[property="og:image"]',
    twitterTitle: 'meta[name="twitter:title"]',
    twitterDescription: 'meta[name="twitter:description"]',
  };

  for (const [key, selector] of Object.entries(metaTags)) {
    const element = document.querySelector(selector);
    if (element) {
      metadata[key] = element.getAttribute('content');
    }
  }

  // Get canonical URL
  const canonical = document.querySelector('link[rel="canonical"]');
  if (canonical) {
    metadata.canonical = canonical.getAttribute('href');
  }

  // Get published date
  const dateSelectors = [
    'meta[property="article:published_time"]',
    'meta[name="date"]',
    'time[datetime]',
  ];

  for (const selector of dateSelectors) {
    const element = document.querySelector(selector);
    if (element) {
      metadata.publishedDate = element.getAttribute('content') || element.getAttribute('datetime');
      break;
    }
  }

  return metadata;
}

/**
 * Extract links from content
 */
function extractLinks(element) {
  const links = element.querySelectorAll('a[href]');

  return Array.from(links)
    .map(link => ({
      text: link.innerText.trim(),
      href: link.href,
      title: link.getAttribute('title'),
    }))
    .filter(link => {
      return (
        link.text &&
        link.href.startsWith('http') &&
        !link.href.includes('#') // Skip anchor links
      );
    })
    .slice(0, 100); // Limit to 100 links
}

/**
 * Extract images with alt text
 */
function extractImages(element) {
  const images = element.querySelectorAll('img[alt]');

  return Array.from(images)
    .map(img => ({
      alt: img.alt,
      src: img.src,
      title: img.getAttribute('title'),
    }))
    .filter(img => img.alt && img.alt.length > 3) // Skip empty/short alt text
    .slice(0, 50); // Limit to 50 images
}

/**
 * Extract headings for structure
 */
function extractHeadings(element) {
  const headings = element.querySelectorAll('h1, h2, h3, h4, h5, h6');

  return Array.from(headings)
    .map(h => ({
      level: parseInt(h.tagName.charAt(1)),
      text: h.innerText.trim(),
    }))
    .filter(h => h.text.length > 0)
    .slice(0, 50); // Limit to 50 headings
}

/**
 * Show visual feedback when content is captured
 */
function showCapturedFeedback(message = 'Captured!') {
  // Create feedback element
  const feedback = document.createElement('div');
  feedback.id = 'unified-ai-feedback';
  feedback.innerHTML = `
    <div style="
      position: fixed;
      top: 20px;
      right: 20px;
      z-index: 999999;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      color: white;
      padding: 16px 24px;
      border-radius: 8px;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      font-size: 14px;
      font-weight: 500;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
      display: flex;
      align-items: center;
      gap: 8px;
      animation: slideIn 0.3s ease;
    ">
      <span style="font-size: 18px;">✓</span>
      <span>${escapeHtml(message)}</span>
    </div>
    <style>
      @keyframes slideIn {
        from {
          transform: translateX(100%);
          opacity: 0;
        }
        to {
          transform: translateX(0);
          opacity: 1;
        }
      }
      @keyframes fadeOut {
        from {
          opacity: 1;
        }
        to {
          opacity: 0;
        }
      }
    </style>
  `;

  // Remove existing feedback
  const existing = document.getElementById('unified-ai-feedback');
  if (existing) {
    existing.remove();
  }

  // Add to page
  document.body.appendChild(feedback);

  // Remove after animation
  setTimeout(() => {
    feedback.querySelector('div').style.animation = 'fadeOut 0.3s ease';
    setTimeout(() => feedback.remove(), 300);
  }, 2000);
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

// Log that content script is loaded (for debugging)
console.log('Unified AI Capture content script loaded');
