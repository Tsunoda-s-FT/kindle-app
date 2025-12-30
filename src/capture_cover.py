#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Optional, Tuple

import capture_app
import get_kindle_book_title as title_helper


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Capture a single cover image from the Kindle macOS app."
    )
    parser.add_argument("--book", help="Book title override for naming.")
    parser.add_argument("--asin", help="ASIN override for lookup.")
    parser.add_argument(
        "--online",
        action="store_true",
        help="Fetch title from Amazon if local sources are empty.",
    )
    parser.add_argument(
        "--output",
        help="Output directory (default: ./kindle-captures/{book})",
    )
    parser.add_argument("--app-name", help="App name (default: config or Amazon Kindle)")
    parser.add_argument("--process-name", help="Process name (default: config or app-name)")
    parser.add_argument("--window-title", help="Window title filter (optional)")
    parser.add_argument("--region", help="Capture region as 'x,y,width,height'")
    parser.add_argument("--scale", type=float, help="Scale factor for region/window bounds")
    parser.add_argument("--wait", type=float, help="Wait time after page turn in seconds")
    parser.add_argument("--initial-wait", type=float, help="Initial wait before first capture")
    parser.add_argument(
        "--next-key",
        choices=["right", "left", "space", "pagedown"],
        help="Key to turn page (default: config or right)",
    )
    parser.add_argument("--log-file", help="Optional log file path")
    parser.add_argument("--config", default="config.yaml", help="Config file path")
    parser.add_argument("--json", action="store_true", help="Output JSON for scripting use")
    return parser.parse_args()


def resolve_book_name(args: argparse.Namespace) -> Tuple[str, Optional[str], str, Optional[str]]:
    if args.book and args.book.strip():
        asin = args.asin.upper() if args.asin else None
        return args.book.strip(), asin, "manual", None

    ebook_root = title_helper.find_ebook_root()
    if not ebook_root:
        raise RuntimeError("Kindle eBooks directory not found.")

    asin_source = "manual"
    if args.asin:
        asin = args.asin.upper()
    else:
        found = title_helper.find_latest_asin(ebook_root)
        if not found:
            raise RuntimeError("No Kindle action files found to infer ASIN.")
        asin, action_file = found
        asin_source = f"action-file:{action_file.name}"

    library_root = ebook_root.parent
    title = title_helper.load_title_from_asset_db(library_root, asin)
    title_source = "ksdk.asset.db" if title else None

    if not title:
        title = title_helper.load_title_from_homefeed(library_root, asin)
        title_source = "homefeed.json" if title else None

    if not title and args.online:
        title = title_helper.fetch_title_from_amazon(asin)
        title_source = "amazon" if title else None

    return title or asin or "kindle_cover", asin, asin_source, title_source


def main() -> int:
    args = parse_args()

    config = capture_app.load_config(args.config)
    app_config = config.get("app_capture", {})

    try:
        book_name, asin, asin_source, title_source = resolve_book_name(args)
    except Exception as exc:
        print(f"❌ Failed to resolve book name: {exc}", file=sys.stderr)
        return 1

    app_name = args.app_name or app_config.get("app_name", capture_app.DEFAULT_APP_NAME)
    process_name = args.process_name or app_config.get("process_name") or app_name
    output_root = app_config.get("output_dir", capture_app.DEFAULT_OUTPUT_DIR)
    sanitized_book = capture_app.sanitize_book_name(book_name)
    output_dir = Path(args.output or (Path(output_root) / sanitized_book)).expanduser()

    window_title = args.window_title or app_config.get("window_title")
    region = None
    if args.region:
        region = capture_app.parse_region(args.region)
    elif app_config.get("capture_region"):
        region = capture_app.parse_region(app_config["capture_region"])

    scale = args.scale if args.scale is not None else app_config.get("scale", 1.0)
    wait_after_turn = args.wait if args.wait is not None else app_config.get("wait_after_turn", 0.6)
    next_key = args.next_key or app_config.get("next_key", "right")
    initial_wait = (
        args.initial_wait
        if args.initial_wait is not None
        else app_config.get("initial_wait", 0.4)
    )
    duplicate_threshold = app_config.get("duplicate_threshold", 3)
    duplicate_diff_mean = app_config.get("duplicate_diff_mean", 3.0)
    duplicate_size_kb = app_config.get("duplicate_size_kb")
    duplicate_size_ratio = app_config.get("duplicate_size_ratio", 0.02)
    duplicate_limit = app_config.get("duplicate_limit", 5)

    capture_app.add_file_logger(args.log_file or app_config.get("log_file"))

    try:
        metadata = capture_app.capture_book(
            book_name=book_name,
            output_dir=str(output_dir),
            app_name=app_name,
            process_name=process_name,
            window_title=window_title,
            region=region,
            scale=scale,
            max_pages=1,
            wait_after_turn=wait_after_turn,
            duplicate_threshold=duplicate_threshold,
            duplicate_diff_mean=duplicate_diff_mean,
            duplicate_size_kb=duplicate_size_kb,
            duplicate_size_ratio=duplicate_size_ratio,
            duplicate_limit=duplicate_limit,
            min_pages=1,
            next_key=next_key,
            initial_wait=initial_wait,
        )
    except Exception as exc:
        print(f"❌ Cover capture failed: {exc}", file=sys.stderr)
        return 1

    cover_src = output_dir / "page_0001.png"
    cover_dest = output_dir / "cover.png"
    if cover_src.exists():
        shutil.copy2(cover_src, cover_dest)
    else:
        print("⚠️ cover source image not found.", file=sys.stderr)

    if args.json:
        payload = {
            "book": book_name,
            "asin": asin,
            "asin_source": asin_source,
            "title_source": title_source,
            "output_dir": str(output_dir),
            "cover": str(cover_dest),
            "captured_at": metadata.get("captured_at"),
        }
        print(json.dumps(payload, ensure_ascii=False))
    else:
        print("\n" + "=" * 50)
        print("✓ Cover capture completed successfully!")
        print(f"  Book: {book_name}")
        if asin:
            print(f"  ASIN: {asin} ({asin_source})")
        if title_source:
            print(f"  Title source: {title_source}")
        print(f"  Output directory: {output_dir}")
        print(f"  Cover image: {cover_dest}")
        print("=" * 50)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
