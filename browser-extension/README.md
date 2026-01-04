# Unified AI Browser Extension

A Chrome/Firefox browser extension for capturing web content to the Unified AI System.

## Features

- **Page Capture**: Capture the full text content of any webpage
- **Selection Capture**: Capture just the selected text
- **Clipboard Capture**: Capture current clipboard contents
- **Context Menu**: Right-click menu for quick capture
- **Keyboard Shortcuts**:
  - `Ctrl+Shift+C` (Mac: `Cmd+Shift+C`): Capture current page
  - `Ctrl+Shift+S` (Mac: `Cmd+Shift+S`): Capture selection
- **Link & Image Capture**: Capture links and image references via context menu

## Installation

### Chrome/Chromium

1. Open Chrome and navigate to `chrome://extensions/`
2. Enable "Developer mode" in the top right corner
3. Click "Load unpacked" and select this `browser-extension` folder
4. The extension icon should appear in your toolbar

### Firefox

1. Open Firefox and navigate to `about:debugging`
2. Click "This Firefox" in the sidebar
3. Click "Load Temporary Add-on"
4. Select the `manifest.json` file from this folder

Note: For permanent Firefox installation, the extension needs to be signed by Mozilla.

### Creating Icon Files

The extension requires PNG icons. Create them from the SVG:

```bash
# Using ImageMagick
convert icons/icon.svg -resize 16x16 icons/icon16.png
convert icons/icon.svg -resize 48x48 icons/icon48.png
convert icons/icon.svg -resize 128x128 icons/icon128.png

# Or using Inkscape
inkscape icons/icon.svg -w 16 -h 16 -o icons/icon16.png
inkscape icons/icon.svg -w 48 -h 48 -o icons/icon48.png
inkscape icons/icon.svg -w 128 -h 128 -o icons/icon128.png
```

## Configuration

1. Click the extension icon to open the popup
2. Configure the server URL (default: `http://localhost:8000`)
3. Click "Test" to verify connection
4. Adjust capture options as needed

## Usage

### Popup Actions

- **Capture Page**: Extracts all text content from the current tab
- **Capture Selection**: Captures any text you've selected on the page
- **Capture Clipboard**: Captures current clipboard contents

### Context Menu

Right-click anywhere on a page to access:
- "Capture Selection to Unified AI" (when text is selected)
- "Capture Page to Unified AI"
- "Capture Link to Unified AI" (when right-clicking a link)
- "Capture Image Alt Text" (when right-clicking an image)

### Keyboard Shortcuts

- `Ctrl+Shift+C`: Quick capture current page
- `Ctrl+Shift+S`: Quick capture selected text

## Captured Data

Each capture includes:
- **Content**: The text content
- **Source Type**: `browser`, `browser_selection`, `browser_link`, etc.
- **Metadata**:
  - Page URL
  - Page title
  - Timestamp
  - Extracted links (optional)
  - Image descriptions (optional)

## Privacy

- All data is sent to your local Unified AI server
- No data is sent to external servers
- The extension only activates when you explicitly capture content

## Troubleshooting

### "Disconnected" Status
- Make sure the Unified AI dashboard is running on `localhost:8000`
- Check that no firewall is blocking the connection

### Captures Not Working
- Ensure the extension has permission for the current page
- Some pages (like Chrome settings pages) cannot be captured

### Icons Not Showing
- Generate PNG icons from the SVG as described above

## Development

To modify the extension:

1. Edit files in this folder
2. Go to `chrome://extensions/`
3. Click the refresh icon on the extension card
4. Changes will be applied immediately

## Files

- `manifest.json` - Extension configuration
- `popup.html` - Popup UI
- `popup.js` - Popup logic
- `background.js` - Background service worker
- `content.js` - Content script injected into pages
- `styles.css` - Popup styling
- `icons/` - Extension icons
