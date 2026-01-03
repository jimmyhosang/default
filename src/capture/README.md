# Screen Capture Daemon

A local-first screen capture system that automatically captures screenshots, extracts text via OCR, and stores everything in a searchable SQLite database.

## Features

- **Automatic Capture**: Takes screenshots every 5 seconds (configurable)
- **Change Detection**: Only stores when screen content changes significantly
- **OCR Text Extraction**: Extracts and indexes all visible text
- **Full-Text Search**: Search through all captured content using SQLite FTS5
- **Active Window Tracking**: Records which app and window was active
- **Privacy-First**: All data stored locally in `~/.unified-ai/capture.db`
- **Efficient**: Minimal CPU usage, runs in background

## macOS Setup

### 1. Install Dependencies

```bash
# Install Python packages
pip install -r requirements.txt

# Install Tesseract OCR (required for text extraction)
brew install tesseract
```

### 2. Grant Permissions

macOS requires explicit permissions for screen capture:

1. **System Settings** → **Privacy & Security** → **Screen Recording**
2. Add your terminal application (e.g., Terminal.app, iTerm2)
3. Restart your terminal

For window detection:
1. **System Settings** → **Privacy & Security** → **Accessibility**
2. Add your terminal application
3. Restart your terminal

### 3. Run the Daemon

```bash
# Start capturing (default: 5 second interval)
python -m src.capture.screen_capture

# Custom interval (e.g., every 10 seconds)
python -m src.capture.screen_capture --interval 10

# Search captured content
python -m src.capture.screen_capture --search "meeting notes"
```

## Usage Examples

### Running as Background Service

```bash
# Run in background with nohup
nohup python -m src.capture.screen_capture &

# Stop the daemon
pkill -f screen_capture
```

### Searching Captured Content

```python
from src.capture.screen_capture import ScreenCapture

# Initialize
capture = ScreenCapture()

# Search for content
results = capture.search("project deadline")
for result in results:
    print(f"{result['timestamp']} - {result['app']}")
    print(f"  {result['text'][:200]}")
```

### Integration with Other Tools

```python
from src.capture.screen_capture import CaptureManager

# Use the manager for multiple capture sources
manager = CaptureManager()
await manager.start_all()
```

## Database Schema

Captures are stored in `~/.unified-ai/capture.db`:

```sql
-- Main captures table
CREATE TABLE captures (
    id INTEGER PRIMARY KEY,
    timestamp TEXT NOT NULL,
    screen_hash TEXT NOT NULL,
    extracted_text TEXT,
    active_window TEXT,
    active_app TEXT,
    metadata JSON,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Full-text search index
CREATE VIRTUAL TABLE captures_fts USING fts5(
    extracted_text,
    content='captures',
    content_rowid='id'
);
```

## Performance

- **CPU Usage**: <5% on average (M1/M2 Macs)
- **Storage**: ~100-500 KB per capture (text only, no images stored)
- **OCR Speed**: ~1-2 seconds per screenshot
- **Change Detection**: <50ms per check

## Privacy Considerations

- **Local Only**: All data stays on your machine
- **No Screenshots Stored**: Only text is extracted and stored
- **Selective Capture**: Only captures when content changes
- **User Control**: You control what gets captured and when

## Troubleshooting

### "Screen Recording permission denied"
Grant Screen Recording permission in System Settings → Privacy & Security

### "OCR not working"
Ensure Tesseract is installed: `brew install tesseract`

### "Can't detect active window"
Grant Accessibility permission in System Settings → Privacy & Security

### "High CPU usage"
Increase capture interval: `--interval 10` or higher

## Configuration

Customize behavior in code:

```python
capture = ScreenCapture(
    db_path=Path("~/.unified-ai/capture.db"),
    capture_interval=5,  # seconds between captures
    min_change_threshold=0.1,  # 10% change required
)
```

## Next Steps

This module is part of the larger Unified AI System:
- **System of Record**: ← You are here
- **System of Action**: Workflow automation (coming soon)
- **System of Thought**: LLM reasoning (coming soon)

See [unified-ai-system-plan.md](../../unified-ai-system-plan.md) for the full roadmap.
