#!/usr/bin/env python3
"""Kindle App Screenshot Capture Script

Captures screenshots from the macOS Kindle app and saves them as PNG files.
"""

import argparse
import json
import logging
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

from PIL import Image, ImageChops, ImageStat
from tqdm import tqdm
import yaml

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DEFAULT_OUTPUT_DIR = "./kindle-captures"
DEFAULT_APP_NAME = "Amazon Kindle"
DEFAULT_PROCESS_NAME = "Kindle"


def load_config(config_path: str = "config.yaml") -> dict:
    """Load configuration from YAML file."""
    try:
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                data = yaml.safe_load(f) or {}
                if isinstance(data, dict):
                    return data
                logger.warning("Config file is not a mapping, using defaults")
                return {}
        logger.warning(f"Config file not found: {config_path}, using defaults")
        return {}
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        return {}


def add_file_logger(log_file: Optional[str]) -> None:
    """Add file handler for logging if requested."""
    if not log_file:
        return
    log_path = Path(log_file).expanduser()
    log_path.parent.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(log_path)
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(file_handler)


def run_osascript(script: str) -> str:
    """Run AppleScript and return stdout."""
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            check=True,
            capture_output=True,
            text=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        message = e.stderr.strip() or str(e)
        raise RuntimeError(f"osascript failed: {message}")


def is_app_running(process_name: str) -> bool:
    """Check if the app process exists."""
    script = f'tell application "System Events" to (exists process "{process_name}")'
    result = run_osascript(script).lower()
    return result == "true"


def activate_app(app_name: str, process_name: str) -> None:
    """Bring the app to the foreground."""
    try:
        run_osascript(f'tell application "{app_name}" to activate')
    except RuntimeError:
        script = f'''
            tell application "System Events"
                if not (exists process "{process_name}") then error "App not running"
                tell process "{process_name}"
                    set frontmost to true
                end tell
            end tell
        '''
        run_osascript(script)
    time.sleep(0.3)


def get_window_bounds(process_name: str, window_title: Optional[str] = None) -> Tuple[int, int, int, int]:
    """Get window bounds as (x1, y1, x2, y2)."""
    target_clause = ""
    if window_title:
        safe_title = window_title.replace('"', '\\"')
        target_clause = f'''
            set target_window to missing value
            repeat with w in windows
                if name of w contains "{safe_title}" then
                    set target_window to w
                    exit repeat
                end if
            end repeat
            if target_window is missing value then error "Window not found"
        '''
    else:
        target_clause = '''
            if (count of windows) is 0 then error "Window not found"
            set target_window to item 1 of windows
        '''

    safe_process = process_name.replace('"', '\\"')
    script = f'''
        tell application "System Events"
            if not (exists process "{safe_process}") then error "App not running"
            tell process "{safe_process}"
                {target_clause}
                set win_pos to position of target_window
                set win_size to size of target_window
                return (item 1 of win_pos) & "," & (item 2 of win_pos) & "," & (item 1 of win_size) & "," & (item 2 of win_size)
            end tell
        end tell
    '''
    output = run_osascript(script)
    parts = re.findall(r"-?\d+", output)
    if len(parts) != 4:
        raise ValueError(f"Unexpected bounds format: {output}")
    x, y, w, h = (int(p) for p in parts)
    return x, y, x + w, y + h


def parse_region(region_str: str) -> Tuple[int, int, int, int]:
    """Parse region string as x,y,width,height."""
    parts = [p.strip() for p in region_str.split(',')]
    if len(parts) != 4:
        raise ValueError("Region must be 'x,y,width,height'")
    x, y, w, h = (int(float(p)) for p in parts)
    return x, y, w, h


def normalize_region(x: int, y: int, w: int, h: int, scale: float) -> Tuple[int, int, int, int]:
    """Apply scale and validate region."""
    if scale <= 0:
        raise ValueError("Scale must be positive")
    sx = int(round(x * scale))
    sy = int(round(y * scale))
    sw = int(round(w * scale))
    sh = int(round(h * scale))
    if sw <= 0 or sh <= 0:
        raise ValueError("Region width/height must be positive")
    return sx, sy, sw, sh


def capture_region(x: int, y: int, w: int, h: int, output_path: str) -> None:
    """Capture a region using macOS screencapture."""
    region = f"{x},{y},{w},{h}"
    subprocess.run(
        ["screencapture", "-x", "-t", "png", "-R", region, output_path],
        check=True
    )


def dhash_int(image: Image.Image, hash_size: int = 8) -> int:
    """Compute difference hash (dHash) as int."""
    resized = image.convert("L").resize(
        (hash_size + 1, hash_size),
        Image.Resampling.LANCZOS
    )
    bits = 0
    for row in range(hash_size):
        for col in range(hash_size):
            left = resized.getpixel((col, row))
            right = resized.getpixel((col + 1, row))
            bits = (bits << 1) | (1 if left > right else 0)
    return bits


def hash_hex(hash_value: int, hash_size: int = 8) -> str:
    """Format hash int as zero-padded hex."""
    width = (hash_size * hash_size) // 4
    return f"{hash_value:0{width}x}"


def hamming_distance(a: int, b: int) -> int:
    """Compute Hamming distance between two hashes."""
    return (a ^ b).bit_count()


def mean_image_diff(path_a: str, path_b: str, sample_size: int = 64) -> float:
    """Compute mean pixel difference on downsampled grayscale images."""
    with Image.open(path_a) as img_a, Image.open(path_b) as img_b:
        gray_a = img_a.convert("L").resize((sample_size, sample_size), Image.Resampling.LANCZOS)
        gray_b = img_b.convert("L").resize((sample_size, sample_size), Image.Resampling.LANCZOS)
        diff = ImageChops.difference(gray_a, gray_b)
        stat = ImageStat.Stat(diff)
        return stat.mean[0]


def sanitize_book_name(name: str) -> str:
    """Make a safe directory name from book title."""
    cleaned = re.sub(r"[\\/]+", "_", name.strip())
    cleaned = re.sub(r"[:*?\"<>|]", "_", cleaned)
    return cleaned or "kindle_book"


def send_next_page(process_name: str, next_key: str) -> None:
    """Send a page-turn keystroke to the app."""
    key = next_key.lower()
    if key == "right":
        key_command = "key code 124"
    elif key == "left":
        key_command = "key code 123"
    elif key == "space":
        key_command = "keystroke \" \""
    elif key == "pagedown":
        key_command = "key code 121"
    else:
        raise ValueError(f"Unsupported next key: {next_key}")

    safe_process = process_name.replace('"', '\\"')
    script = f'''
        tell application "System Events"
            if not (exists process "{safe_process}") then error "App not running"
            tell process "{safe_process}"
                set frontmost to true
            end tell
            {key_command}
        end tell
    '''
    run_osascript(script)


def capture_book(
    book_name: str,
    output_dir: str,
    app_name: str,
    process_name: str,
    window_title: Optional[str],
    region: Optional[Tuple[int, int, int, int]],
    scale: float,
    max_pages: Optional[int],
    wait_after_turn: float,
    duplicate_threshold: int,
    duplicate_diff_mean: float,
    duplicate_size_kb: Optional[float],
    duplicate_size_ratio: Optional[float],
    duplicate_limit: int,
    min_pages: int,
    next_key: str,
    initial_wait: float
) -> dict:
    """Capture screenshots from the Kindle app."""
    if not is_app_running(process_name):
        raise RuntimeError(f"{process_name} is not running")

    os.makedirs(output_dir, exist_ok=True)
    logger.info(f"Output directory: {output_dir}")

    activate_app(app_name, process_name)

    region_source = "manual" if region is not None else "window"
    if region is None:
        bounds = get_window_bounds(process_name, window_title)
        x1, y1, x2, y2 = bounds
        region = (x1, y1, x2 - x1, y2 - y1)

    raw_x, raw_y, raw_w, raw_h = region
    x, y, w, h = normalize_region(*region, scale=scale)
    logger.info(f"Capture region: x={x}, y={y}, w={w}, h={h}")
    logger.info(
        "Capture settings: book=%s app=%s process=%s window=%s region_source=%s "
        "raw_region=%s,%s,%s,%s scale=%.2f next_key=%s wait=%.2fs initial_wait=%.2fs "
        "dup_threshold=%d dup_diff_mean=%.2f dup_size_kb=%s dup_size_ratio=%s "
        "dup_limit=%d min_pages=%d max_pages=%s",
        book_name,
        app_name,
        process_name,
        window_title or "front window",
        region_source,
        raw_x,
        raw_y,
        raw_w,
        raw_h,
        scale,
        next_key,
        wait_after_turn,
        initial_wait,
        duplicate_threshold,
        duplicate_diff_mean,
        f"{duplicate_size_kb:.1f}" if duplicate_size_kb is not None else "none",
        f"{duplicate_size_ratio:.4f}" if duplicate_size_ratio is not None else "none",
        duplicate_limit,
        min_pages,
        max_pages if max_pages is not None else "unlimited"
    )

    if initial_wait > 0:
        time.sleep(initial_wait)

    pages = []
    last_hash = None
    last_image_path = None
    last_size_kb = None
    duplicate_count = 0

    pbar = tqdm(
        desc="Capturing pages",
        unit="page",
        total=max_pages
    )

    page_num = 1
    capture_started_at = time.perf_counter()
    try:
        while True:
            filename = f"page_{page_num:04d}.png"
            screenshot_path = os.path.join(output_dir, filename)

            capture_start = time.perf_counter()
            try:
                capture_region(x, y, w, h, screenshot_path)
            except Exception as e:
                logger.error(
                    "Screenshot failed: page=%d path=%s region=%d,%d,%d,%d error=%s",
                    page_num,
                    screenshot_path,
                    x,
                    y,
                    w,
                    h,
                    e
                )
                raise
            capture_ms = (time.perf_counter() - capture_start) * 1000

            with Image.open(screenshot_path) as img:
                current_hash = dhash_int(img)

            current_hash_hex = hash_hex(current_hash)
            size_kb = os.path.getsize(screenshot_path) / 1024
            size_delta_kb = None
            size_ratio = None
            mean_diff = None
            duplicate_candidate = False
            distance = None
            if last_hash is not None and last_image_path and last_size_kb is not None:
                distance = hamming_distance(last_hash, current_hash)
                size_delta_kb = abs(size_kb - last_size_kb)
                size_ratio = size_delta_kb / last_size_kb if last_size_kb else None
                try:
                    mean_diff = mean_image_diff(last_image_path, screenshot_path)
                except Exception as e:
                    logger.warning("Mean diff calculation failed: %s", e)

                hash_ok = distance <= duplicate_threshold
                diff_ok = mean_diff is not None and mean_diff <= duplicate_diff_mean
                size_ok = True
                if duplicate_size_kb is not None:
                    size_ok = size_ok and size_delta_kb is not None and size_delta_kb <= duplicate_size_kb
                if duplicate_size_ratio is not None:
                    size_ok = size_ok and size_ratio is not None and size_ratio <= duplicate_size_ratio

                duplicate_candidate = hash_ok and diff_ok and size_ok
                if duplicate_candidate:
                    duplicate_count += 1
                else:
                    duplicate_count = 0

            if page_num >= min_pages and duplicate_count >= duplicate_limit:
                logger.info(
                    "Duplicate threshold reached; attempting recovery (page=%d distance=%s mean_diff=%s "
                    "size_delta_kb=%s size_ratio=%s dup_count=%d)",
                    page_num,
                    distance,
                    f"{mean_diff:.2f}" if mean_diff is not None else "n/a",
                    f"{size_delta_kb:.1f}" if size_delta_kb is not None else "n/a",
                    f"{size_ratio:.4f}" if size_ratio is not None else "n/a",
                    duplicate_count
                )

                confirm_filename = f"page_{page_num + 1:04d}.png"
                confirm_path = os.path.join(output_dir, confirm_filename)
                try:
                    send_next_page(process_name, next_key)
                    time.sleep(wait_after_turn)
                    capture_region(x, y, w, h, confirm_path)
                except Exception as e:
                    logger.warning("Recovery capture failed: %s", e)
                    try:
                        if os.path.exists(confirm_path):
                            os.remove(confirm_path)
                    except Exception:
                        pass
                    logger.info("Stopping after duplicate threshold due to recovery failure.")
                    break

                with Image.open(confirm_path) as confirm_img:
                    confirm_hash = dhash_int(confirm_img)

                confirm_hash_hex = hash_hex(confirm_hash)
                confirm_size_kb = os.path.getsize(confirm_path) / 1024
                confirm_distance = hamming_distance(current_hash, confirm_hash)
                confirm_mean_diff = mean_image_diff(screenshot_path, confirm_path)
                confirm_size_delta_kb = abs(confirm_size_kb - size_kb)
                confirm_size_ratio = confirm_size_delta_kb / size_kb if size_kb else None

                confirm_hash_ok = confirm_distance <= duplicate_threshold
                confirm_diff_ok = confirm_mean_diff <= duplicate_diff_mean
                confirm_size_ok = True
                if duplicate_size_kb is not None:
                    confirm_size_ok = confirm_size_ok and confirm_size_delta_kb <= duplicate_size_kb
                if duplicate_size_ratio is not None and confirm_size_ratio is not None:
                    confirm_size_ok = confirm_size_ok and confirm_size_ratio <= duplicate_size_ratio

                confirm_duplicate = confirm_hash_ok and confirm_diff_ok and confirm_size_ok
                if confirm_duplicate:
                    logger.info(
                        "Recovery capture still duplicate; stopping (distance=%d mean_diff=%.2f "
                        "size_delta_kb=%.1f size_ratio=%s)",
                        confirm_distance,
                        confirm_mean_diff,
                        confirm_size_delta_kb,
                        f"{confirm_size_ratio:.4f}" if confirm_size_ratio is not None else "n/a"
                    )
                    try:
                        os.remove(confirm_path)
                    except Exception as e:
                        logger.warning("Failed to remove recovery screenshot: %s", e)
                    try:
                        os.remove(screenshot_path)
                    except Exception as e:
                        logger.warning("Failed to remove duplicate screenshot: %s", e)
                    break

                logger.info(
                    "Recovery capture advanced; continuing (distance=%d mean_diff=%.2f size_delta_kb=%.1f "
                    "size_ratio=%s)",
                    confirm_distance,
                    confirm_mean_diff,
                    confirm_size_delta_kb,
                    f"{confirm_size_ratio:.4f}" if confirm_size_ratio is not None else "n/a"
                )

                pages.append({
                    "page": page_num,
                    "file": filename,
                    "timestamp": datetime.now().isoformat(),
                    "hash": current_hash_hex,
                    "hash_distance": distance,
                    "mean_diff": mean_diff,
                    "size_kb": round(size_kb, 2),
                    "size_delta_kb": round(size_delta_kb, 2) if size_delta_kb is not None else None,
                    "size_delta_ratio": round(size_ratio, 6) if size_ratio is not None else None
                })

                pages.append({
                    "page": page_num + 1,
                    "file": confirm_filename,
                    "timestamp": datetime.now().isoformat(),
                    "hash": confirm_hash_hex,
                    "hash_distance": confirm_distance,
                    "mean_diff": confirm_mean_diff,
                    "size_kb": round(confirm_size_kb, 2),
                    "size_delta_kb": round(confirm_size_delta_kb, 2),
                    "size_delta_ratio": round(confirm_size_ratio, 6) if confirm_size_ratio is not None else None
                })

                pbar.update(2)
                last_hash = confirm_hash
                last_image_path = confirm_path
                last_size_kb = confirm_size_kb
                duplicate_count = 0
                page_num += 2
                continue

            total_elapsed = time.perf_counter() - capture_started_at
            logger.info(
                "Captured page=%d file=%s size=%.1fKB hash=%s distance=%s mean_diff=%s "
                "size_delta_kb=%s size_ratio=%s dup_candidate=%s dup_count=%d "
                "capture_ms=%.0f elapsed=%.1fs",
                page_num,
                filename,
                size_kb,
                current_hash_hex,
                distance,
                f"{mean_diff:.2f}" if mean_diff is not None else "n/a",
                f"{size_delta_kb:.1f}" if size_delta_kb is not None else "n/a",
                f"{size_ratio:.4f}" if size_ratio is not None else "n/a",
                "yes" if duplicate_candidate else "no",
                duplicate_count,
                capture_ms,
                total_elapsed
            )

            pages.append({
                "page": page_num,
                "file": filename,
                "timestamp": datetime.now().isoformat(),
                "hash": current_hash_hex,
                "hash_distance": distance,
                "mean_diff": mean_diff,
                "size_kb": round(size_kb, 2),
                "size_delta_kb": round(size_delta_kb, 2) if size_delta_kb is not None else None,
                "size_delta_ratio": round(size_ratio, 6) if size_ratio is not None else None
            })

            last_hash = current_hash
            last_image_path = screenshot_path
            last_size_kb = size_kb
            pbar.update(1)

            if max_pages and page_num >= max_pages:
                logger.info(f"Reached max pages: {max_pages}")
                break

            send_next_page(process_name, next_key)
            time.sleep(wait_after_turn)
            page_num += 1

    finally:
        pbar.close()

    metadata = {
        "source": "app",
        "book": book_name,
        "app_name": app_name,
        "window_title": window_title,
        "capture_region": {
            "x": x,
            "y": y,
            "width": w,
            "height": h,
            "scale": scale
        },
        "total_pages": len(pages),
        "wait_after_turn": wait_after_turn,
        "duplicate_threshold": duplicate_threshold,
        "duplicate_diff_mean": duplicate_diff_mean,
        "duplicate_size_kb": duplicate_size_kb,
        "duplicate_size_ratio": duplicate_size_ratio,
        "duplicate_limit": duplicate_limit,
        "min_pages": min_pages,
        "next_key": next_key,
        "captured_at": datetime.now().isoformat(),
        "pages": pages
    }

    metadata_path = os.path.join(output_dir, "metadata.json")
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    logger.info("✓ Capture complete!")
    logger.info(f"  Total pages: {metadata['total_pages']}")
    logger.info(f"  Output: {output_dir}")
    logger.info(f"  Metadata: {metadata_path}")

    return metadata


def main() -> None:
    """Main entry point for CLI."""
    parser = argparse.ArgumentParser(
        description="Capture screenshots from Kindle macOS app"
    )

    parser.add_argument(
        "--book",
        required=True,
        help="Book title or identifier (required)"
    )

    parser.add_argument(
        "--output",
        help="Output directory (default: ./kindle-captures/{book})"
    )

    parser.add_argument(
        "--app-name",
        default=None,
        help="App name (default: config or Amazon Kindle)"
    )

    parser.add_argument(
        "--process-name",
        default=None,
        help="Process name (default: config or app-name)"
    )

    parser.add_argument(
        "--window-title",
        default=None,
        help="Window title filter (optional)"
    )

    parser.add_argument(
        "--region",
        default=None,
        help="Capture region as 'x,y,width,height' (overrides window detection)"
    )

    parser.add_argument(
        "--scale",
        type=float,
        default=None,
        help="Scale factor for region/window bounds (default: config or 1.0)"
    )

    parser.add_argument(
        "--wait",
        type=float,
        default=None,
        help="Wait time after page turn in seconds (default: config or 0.6)"
    )

    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Max pages to capture (default: config or unlimited)"
    )

    parser.add_argument(
        "--dup-threshold",
        type=int,
        default=None,
        help="Duplicate hash distance threshold (default: config or 3)"
    )

    parser.add_argument(
        "--dup-diff-mean",
        type=float,
        default=None,
        help="Duplicate mean-diff threshold (default: config or 3.0)"
    )

    parser.add_argument(
        "--dup-size-kb",
        type=float,
        default=None,
        help="Duplicate size delta threshold in KB (default: config or None)"
    )

    parser.add_argument(
        "--dup-size-ratio",
        type=float,
        default=None,
        help="Duplicate size delta ratio threshold (default: config or 0.02)"
    )

    parser.add_argument(
        "--dup-limit",
        type=int,
        default=None,
        help="Stop after this many consecutive duplicates (default: config or 5)"
    )

    parser.add_argument(
        "--min-pages",
        type=int,
        default=None,
        help="Minimum pages before duplicate stop applies (default: config or 2)"
    )

    parser.add_argument(
        "--next-key",
        default=None,
        choices=["right", "left", "space", "pagedown"],
        help="Key to turn page (default: config or right)"
    )

    parser.add_argument(
        "--initial-wait",
        type=float,
        default=None,
        help="Initial wait before first capture (default: config or 0.4)"
    )

    parser.add_argument(
        "--log-file",
        default=None,
        help="Optional log file path"
    )

    parser.add_argument(
        "--config",
        default="config.yaml",
        help="Config file path (default: config.yaml)"
    )

    args = parser.parse_args()

    config = load_config(args.config)
    app_config = config.get("app_capture", {})

    book_name = args.book.strip()
    app_name = args.app_name or app_config.get("app_name", DEFAULT_APP_NAME)
    process_name = args.process_name or app_config.get("process_name") or app_name
    output_root = app_config.get("output_dir", DEFAULT_OUTPUT_DIR)
    sanitized_book = sanitize_book_name(book_name)
    output_dir = args.output or os.path.join(output_root, sanitized_book)

    window_title = args.window_title or app_config.get("window_title")
    region = None
    if args.region:
        region = parse_region(args.region)
    elif app_config.get("capture_region"):
        region = parse_region(app_config["capture_region"])

    scale = args.scale if args.scale is not None else app_config.get("scale", 1.0)
    wait_after_turn = args.wait if args.wait is not None else app_config.get("wait_after_turn", 0.6)
    max_pages = args.max_pages if args.max_pages is not None else app_config.get("max_pages")
    duplicate_threshold = args.dup_threshold if args.dup_threshold is not None else app_config.get("duplicate_threshold", 3)
    duplicate_diff_mean = args.dup_diff_mean if args.dup_diff_mean is not None else app_config.get("duplicate_diff_mean", 3.0)
    duplicate_size_kb = args.dup_size_kb if args.dup_size_kb is not None else app_config.get("duplicate_size_kb")
    duplicate_size_ratio = args.dup_size_ratio if args.dup_size_ratio is not None else app_config.get("duplicate_size_ratio", 0.02)
    duplicate_limit = args.dup_limit if args.dup_limit is not None else app_config.get("duplicate_limit", 5)
    min_pages = args.min_pages if args.min_pages is not None else app_config.get("min_pages", 2)
    next_key = args.next_key or app_config.get("next_key", "right")
    initial_wait = args.initial_wait if args.initial_wait is not None else app_config.get("initial_wait", 0.4)
    log_file = args.log_file or app_config.get("log_file")

    if max_pages is not None and max_pages <= 0:
        print("❌ Error: max pages must be a positive integer")
        sys.exit(1)
    if duplicate_threshold < 0 or duplicate_threshold > 64:
        print("❌ Error: dup-threshold must be between 0 and 64")
        sys.exit(1)
    if duplicate_diff_mean < 0:
        print("❌ Error: dup-diff-mean must be non-negative")
        sys.exit(1)
    if duplicate_size_kb is not None and duplicate_size_kb < 0:
        print("❌ Error: dup-size-kb must be non-negative")
        sys.exit(1)
    if duplicate_size_ratio is not None and duplicate_size_ratio < 0:
        print("❌ Error: dup-size-ratio must be non-negative")
        sys.exit(1)
    if duplicate_limit <= 0:
        print("❌ Error: dup-limit must be a positive integer")
        sys.exit(1)
    if min_pages <= 0:
        print("❌ Error: min-pages must be a positive integer")
        sys.exit(1)
    if wait_after_turn < 0 or initial_wait < 0:
        print("❌ Error: wait values must be non-negative")
        sys.exit(1)

    add_file_logger(log_file)

    try:
        metadata = capture_book(
            book_name=book_name,
            output_dir=output_dir,
            app_name=app_name,
            process_name=process_name,
            window_title=window_title,
            region=region,
            scale=scale,
            max_pages=max_pages,
            wait_after_turn=wait_after_turn,
            duplicate_threshold=duplicate_threshold,
            duplicate_diff_mean=duplicate_diff_mean,
            duplicate_size_kb=duplicate_size_kb,
            duplicate_size_ratio=duplicate_size_ratio,
            duplicate_limit=duplicate_limit,
            min_pages=min_pages,
            next_key=next_key,
            initial_wait=initial_wait
        )

        print("\n" + "=" * 50)
        print("✓ Capture completed successfully!")
        print(f"  Pages captured: {metadata['total_pages']}")
        print(f"  Output directory: {output_dir}")
        print("=" * 50)

    except KeyboardInterrupt:
        print("\n\n❌ Capture interrupted by user")
        sys.exit(1)

    except Exception as e:
        print(f"\n\n❌ Capture failed: {e}")
        logger.exception("Full error:")
        sys.exit(1)


if __name__ == "__main__":
    main()
