#!/usr/bin/env python3
"""Kindle Web Reader Screenshot Capture Script

Captures screenshots from Kindle Web Reader and saves them as PNG files.
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional
from tqdm import tqdm
import yaml

from kindle_utils import (
    create_browser_context,
    check_session_valid,
    dismiss_modal_dialogs,
    set_layout_mode,
    goto_position,
    next_page,
    has_next_page,
    get_current_location,
    get_position_range,
    wait_for_page_load,
    KINDLE_READER_URL,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_CHROME_PROFILE
)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def load_config(config_path: str = "config.yaml") -> dict:
    """Load configuration from YAML file."""
    try:
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        else:
            logger.warning(f"Config file not found: {config_path}, using defaults")
            return {}
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        return {}


async def capture_book(
    asin: str,
    layout: str = "single",
    output_dir: Optional[str] = None,
    start_pos: Optional[int] = None,
    end_pos: Optional[int] = None,
    headless: bool = False,
    wait_strategy: str = "hybrid",
    chrome_profile: str = DEFAULT_CHROME_PROFILE
) -> dict:
    """
    Capture screenshots from a Kindle book.

    Args:
        asin: Book ASIN
        layout: "single" or "double" column layout
        output_dir: Output directory for screenshots
        start_pos: Starting position (optional)
        end_pos: Ending position (optional)
        headless: Run in headless mode
        wait_strategy: Page load wait strategy
        chrome_profile: Chrome profile path

    Returns:
        dict: Metadata about the capture

    Raises:
        Exception: If capture fails
    """
    # Setup output directory
    if output_dir is None:
        output_dir = os.path.join(DEFAULT_OUTPUT_DIR, asin)

    os.makedirs(output_dir, exist_ok=True)
    logger.info(f"Output directory: {output_dir}")

    # Launch browser
    logger.info("Launching browser...")
    context, playwright = await create_browser_context(
        profile_path=chrome_profile,
        headless=headless
    )

    page = await context.new_page()

    try:
        # Navigate to reader
        reader_url = KINDLE_READER_URL.format(asin=asin)
        logger.info(f"Navigating to: {reader_url}")
        await page.goto(reader_url, wait_until="networkidle", timeout=60000)

        # Wait for KindleRenderer to be ready
        logger.info("Waiting for KindleRenderer to be ready...")
        await page.wait_for_function(
            "typeof KindleRenderer !== 'undefined'",
            timeout=30000
        )

        # Check session validity
        if not await check_session_valid(page):
            logger.error("❌ Session invalid. Please log in to Kindle in Chrome and retry.")
            await context.close()
            await playwright.stop()
            sys.exit(1)

        logger.info("✓ KindleRenderer ready")

        # Dismiss any modal dialogs (e.g., "Most Recent Page Read")
        await dismiss_modal_dialogs(page)

        # Set layout mode
        if layout != "default":
            success = await set_layout_mode(page, layout)
            if not success:
                logger.warning("Failed to set layout, using default")

        # Get position range
        min_pos, max_pos = await get_position_range(page)

        # Set start and end positions
        start_pos = start_pos or min_pos
        end_pos = end_pos or max_pos

        logger.info(f"Capture range: {start_pos} - {end_pos}")
        logger.info(f"Full book range: {min_pos} - {max_pos}")

        # Go to start position
        logger.info(f"Moving to start position: {start_pos}")
        await goto_position(page, start_pos)
        await wait_for_page_load(page, strategy=wait_strategy)

        # Capture loop
        page_num = 1
        captured_positions = []

        logger.info("Starting capture...")

        with tqdm(desc="Capturing pages", unit="page") as pbar:
            while True:
                # Wait for page content to fully load before taking screenshot
                # This ensures spinner is gone and content is rendered
                await wait_for_page_load(page, strategy=wait_strategy)

                # Get current location
                location = await get_current_location(page)
                current_pos = location.get('current', 0) if location else 0

                # Check if beyond end position
                if end_pos and current_pos > 0:
                    # Get actual position from KindleRenderer if available
                    try:
                        actual_pos = await page.evaluate("KindleRenderer.getPosition?.()")
                        if actual_pos and actual_pos > end_pos:
                            logger.info(f"Reached end position: {actual_pos} > {end_pos}")
                            break
                    except:
                        pass

                # Take screenshot
                screenshot_path = os.path.join(
                    output_dir,
                    f"page_{page_num:04d}.png"
                )

                await page.screenshot(path=screenshot_path, full_page=False)

                # Track metadata
                captured_positions.append({
                    'page': page_num,
                    'location': location,
                    'timestamp': datetime.now().isoformat()
                })

                # Update progress
                pbar.update(1)
                if location:
                    pbar.set_postfix({
                        'location': f"{location.get('current', '?')}/{location.get('total', '?')}",
                        'percent': f"{location.get('percent', '?')}%"
                    })

                # Check for next page
                has_next = await has_next_page(page)
                if not has_next:
                    logger.info("Reached end of book")
                    break

                # Navigate to next page
                success = await next_page(page)
                if not success:
                    logger.error(f"Failed to navigate at page {page_num}")
                    break

                # Periodic session check (every 50 pages)
                if page_num % 50 == 0:
                    if not await check_session_valid(page):
                        logger.error("❌ Session expired during capture")
                        break

                page_num += 1

        # Save metadata
        metadata = {
            'asin': asin,
            'layout': layout,
            'total_pages': page_num,
            'position_range': [min_pos, max_pos],
            'capture_range': [start_pos, end_pos],
            'captured_at': datetime.now().isoformat(),
            'pages': captured_positions
        }

        metadata_path = os.path.join(output_dir, 'metadata.json')
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        logger.info(f"✓ Capture complete!")
        logger.info(f"  Total pages: {page_num}")
        logger.info(f"  Output: {output_dir}")
        logger.info(f"  Metadata: {metadata_path}")

        return metadata

    except Exception as e:
        logger.error(f"Capture failed: {e}")
        raise

    finally:
        # Cleanup
        await context.close()
        await playwright.stop()


def main():
    """Main entry point for CLI."""
    parser = argparse.ArgumentParser(
        description="Capture screenshots from Kindle Web Reader"
    )

    parser.add_argument(
        "--asin",
        required=True,
        help="Book ASIN (required)"
    )

    parser.add_argument(
        "--layout",
        choices=["single", "double", "default"],
        default="single",
        help="Layout mode (default: single)"
    )

    parser.add_argument(
        "--output",
        help="Output directory (default: ./kindle-captures/{ASIN})"
    )

    parser.add_argument(
        "--start",
        type=int,
        help="Start position (optional)"
    )

    parser.add_argument(
        "--end",
        type=int,
        help="End position (optional)"
    )

    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run in headless mode (default: False)"
    )

    parser.add_argument(
        "--chrome-profile",
        default=DEFAULT_CHROME_PROFILE,
        help=f"Chrome profile path (default: {DEFAULT_CHROME_PROFILE})"
    )

    parser.add_argument(
        "--config",
        default="config.yaml",
        help="Config file path (default: config.yaml)"
    )

    args = parser.parse_args()

    # Load config
    config = load_config(args.config)

    # Get settings from config with CLI overrides
    wait_strategy = config.get('capture', {}).get('wait_strategy', 'hybrid')
    chrome_profile = args.chrome_profile or config.get('browser', {}).get('chrome_profile', DEFAULT_CHROME_PROFILE)

    # Run capture
    try:
        metadata = asyncio.run(capture_book(
            asin=args.asin,
            layout=args.layout,
            output_dir=args.output,
            start_pos=args.start,
            end_pos=args.end,
            headless=args.headless,
            wait_strategy=wait_strategy,
            chrome_profile=chrome_profile
        ))

        print("\n" + "="*50)
        print("✓ Capture completed successfully!")
        print(f"  Pages captured: {metadata['total_pages']}")
        print(f"  Output directory: {args.output or os.path.join(DEFAULT_OUTPUT_DIR, args.asin)}")
        print("="*50)

    except KeyboardInterrupt:
        print("\n\n❌ Capture interrupted by user")
        sys.exit(1)

    except Exception as e:
        print(f"\n\n❌ Capture failed: {e}")
        logger.exception("Full error:")
        sys.exit(1)


if __name__ == "__main__":
    main()
