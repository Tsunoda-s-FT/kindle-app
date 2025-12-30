# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Kindle automation tool that captures screenshots from Amazon Kindle books (Web Reader or macOS app) and converts them to PDF. Web mode uses Playwright to control Chrome and interacts with the KindleRenderer JavaScript API.

## Architecture

The tool follows a two-stage pipeline:

1. **Screenshot Capture** (`src/capture.py`)
   - Launches Chrome via Playwright with persistent context (user's Chrome profile)
   - Navigates to Kindle Web Reader (read.amazon.co.jp)
   - Uses KindleRenderer API to navigate through pages
   - Implements hybrid page-load detection (location change + spinner disappearance)
   - Saves screenshots as PNG files with metadata

2. **PDF Generation** (`src/create_pdf.py`)
   - Reads PNG screenshots from capture directory
   - Optionally resizes/compresses images
   - Converts to PDF using img2pdf (lossless for PNG)

3. **Local App Capture** (`src/capture_app.py`)
   - Uses osascript/screencapture to capture the Kindle macOS app window
   - Turns pages via key events and stops on duplicates or max pages

**Key Components:**
- `src/kindle_utils.py`: Browser control, KindleRenderer API wrappers, page load detection
- `config.yaml`: Runtime configuration (wait strategies, timeouts, quality settings)

## Common Commands

### Development Workflow

```bash
# Install dependencies (uses system Chrome, no browser install needed)
pip install -r requirements.txt

# Capture a book (two-step process)
python src/capture.py --asin <ASIN> --chrome-profile /tmp/kindle-test-profile
python src/create_pdf.py --input ./kindle-captures/<ASIN>/

# Capture via Kindle macOS app
python src/capture_app.py --book "<TITLE>"
python src/create_pdf.py --input "./kindle-captures/<TITLE>/"

# Partial capture (by position range)
python src/capture.py --asin <ASIN> --start 1000 --end 5000 --chrome-profile /tmp/kindle-test-profile

# Generate optimized PDF (mobile-friendly)
python src/create_pdf.py --input ./kindle-captures/<ASIN>/ --resize 0.7 --quality 80
```

### Chrome Profile Handling (Critical)

**Always use `--chrome-profile /tmp/kindle-test-profile`** to avoid conflicts with running Chrome instances. The tool uses Playwright's `launch_persistent_context` which locks the profile directory.

Default profile (`~/Library/Application Support/Google/Chrome`) requires Chrome to be fully closed, but using a temporary profile allows normal Chrome usage alongside the tool.

## Important Implementation Details

### KindleRenderer API Usage

The tool relies on Kindle Web Reader's internal JavaScript API:
- `getMinimumPosition()` / `getMaximumPosition()`: Get book position range
- `gotoPosition(position)`: Navigate to specific location
- `nextScreen()`: Move to next page
- `hasNextScreen()`: Check if more pages exist
- Session validation checks `typeof KindleRenderer !== 'undefined'`

### Page Load Detection Strategies

Defined in `kindle_utils.py:wait_for_page_load()`:

- **hybrid** (default): Tries location text change, falls back to fixed wait + spinner check
- **location_change**: Monitors DOM for location text change (e.g., "Location 101 of 241")
- **fixed**: Simple fixed timeout with spinner disappearance check

Configured via `config.yaml` `capture.wait_strategy` or per-run.

### Session Management

- Requires active Kindle login in Chrome profile before running
- Session validation occurs at startup and every 50 pages
- If session expires, user must manually re-login via Chrome

## Claude Code Skill Integration

This tool is also a Claude Code Skill (`.claude/skills/kindle-capture/`). When users request "PDF化して" or provide book names:

1. Use `mcp__claude-in-chrome__*` tools to search Kindle library if book name is ambiguous
2. Extract ASIN from Kindle URLs (format: `https://read.amazon.co.jp/?asin=B0DSKPTJM5`)
3. Always activate venv: `source venv/bin/activate`
4. Run two-step process with `--chrome-profile /tmp/kindle-test-profile`

## Platform Constraints

- **macOS only tested** (uses macOS default Chrome profile path)
- **System Chrome required** (not Chromium)
- **Reflow books only** (fixed-layout and comics unsupported)
- **2K viewport** hardcoded (2560x1440) for consistent rendering
- **Local capture requires screen recording/accessibility permissions**

## Configuration

`config.yaml` controls:
- `browser.chrome_profile`: Profile path (default: system Chrome profile)
- `capture.wait_strategy`: Page load detection method
- `capture.wait_timeout`: Maximum wait time per page (default: 3.0s)
- `pdf.default_quality`: JPEG quality if resizing (1-100)
- `pdf.default_resize`: Resize ratio (0.1-1.0, 1.0 = no resize)

Increase `wait_timeout` to 5.0+ for slow networks.

## Output Structure

```
kindle-captures/
└── {ASIN or book}/
    ├── page_0001.png
    ├── page_0002.png
    ├── ...
    └── metadata.json  # Contains position info, timestamps, layout settings
```

PDF output: `{ASIN}.pdf` in current directory (or `--output` specified path)
