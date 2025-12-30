#!/usr/bin/env python3
"""Image Trimming Script for Kindle Captures

Crops margins from captured screenshots with AI-assisted workflow support.
Original images are preserved; trimmed versions are saved to a subdirectory.
"""

import argparse
import glob
import json
import logging
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple, Dict, List
from PIL import Image
from tqdm import tqdm
import yaml

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


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


def parse_crop_box(crop_str: str) -> Tuple[int, int, int, int]:
    """
    Parse crop box string into tuple.

    Args:
        crop_str: Comma-separated string "left,top,right,bottom"

    Returns:
        Tuple of (left, top, right, bottom) as integers

    Raises:
        ValueError: If format is invalid
    """
    try:
        parts = [int(x.strip()) for x in crop_str.split(',')]
        if len(parts) != 4:
            raise ValueError("Crop box must have exactly 4 values")
        return tuple(parts)
    except Exception as e:
        raise ValueError(f"Invalid crop box format '{crop_str}'. Expected: 'left,top,right,bottom' (e.g., '100,50,3700,2100')")


def validate_crop_box(
    crop_box: Tuple[int, int, int, int],
    image_size: Tuple[int, int]
) -> bool:
    """
    Validate crop box dimensions against image size.

    Args:
        crop_box: (left, top, right, bottom) coordinates
        image_size: (width, height) of the image

    Returns:
        True if valid

    Raises:
        ValueError: If crop box is invalid
    """
    left, top, right, bottom = crop_box
    width, height = image_size

    if left < 0 or top < 0:
        raise ValueError(f"Crop coordinates cannot be negative: left={left}, top={top}")

    if right > width or bottom > height:
        raise ValueError(f"Crop box ({right}, {bottom}) exceeds image size ({width}, {height})")

    if left >= right:
        raise ValueError(f"Left ({left}) must be less than right ({right})")

    if top >= bottom:
        raise ValueError(f"Top ({top}) must be less than bottom ({bottom})")

    result_width = right - left
    result_height = bottom - top

    if result_width < 100 or result_height < 100:
        raise ValueError(f"Resulting image too small: {result_width}x{result_height}")

    return True


def crop_image(img: Image.Image, crop_box: Tuple[int, int, int, int]) -> Image.Image:
    """
    Apply crop to a single image.

    Args:
        img: PIL Image object
        crop_box: (left, top, right, bottom) coordinates

    Returns:
        Cropped PIL Image
    """
    return img.crop(crop_box)


def trim_images(
    input_dir: str,
    output_dir: str,
    crop_box: Tuple[int, int, int, int],
    note: Optional[str] = None,
    pages: Optional[List[int]] = None
) -> dict:
    """
    Trim all images in input directory.

    Args:
        input_dir: Directory containing original PNG files
        output_dir: Directory for trimmed images
        crop_box: (left, top, right, bottom) coordinates
        note: Optional note to record in metadata
        pages: Optional list of page numbers to trim (e.g., [5, 8, 10, 12]).
               If None, all pages are trimmed.

    Returns:
        dict: Summary of the operation

    Raises:
        ValueError: If no images found or validation fails
    """
    # Find all screenshot files
    image_pattern = os.path.join(input_dir, "page_*.png")
    image_files = sorted(glob.glob(image_pattern))

    # Filter by specific pages if requested
    if pages:
        def get_page_number(filepath: str) -> int:
            """Extract page number from filename like page_0005.png -> 5"""
            basename = os.path.basename(filepath)
            return int(basename.replace('page_', '').replace('.png', ''))

        image_files = [f for f in image_files if get_page_number(f) in pages]
        logger.info(f"Filtering to pages: {pages}")

    if not image_files:
        raise ValueError(f"No screenshots found in {input_dir}")

    logger.info(f"Found {len(image_files)} screenshots")

    # Validate crop box against first image
    with Image.open(image_files[0]) as first_img:
        original_size = first_img.size
        validate_crop_box(crop_box, original_size)

    # Calculate new size
    left, top, right, bottom = crop_box
    new_size = (right - left, bottom - top)

    logger.info(f"Original size: {original_size[0]}x{original_size[1]}")
    logger.info(f"Crop box: ({left}, {top}, {right}, {bottom})")
    logger.info(f"New size: {new_size[0]}x{new_size[1]}")

    # Create output directory (clear if exists)
    if os.path.exists(output_dir):
        logger.info(f"Clearing existing output directory: {output_dir}")
        shutil.rmtree(output_dir)
    os.makedirs(output_dir, exist_ok=True)

    # Process images
    processed_count = 0
    for img_path in tqdm(image_files, desc="Trimming images"):
        filename = os.path.basename(img_path)
        output_path = os.path.join(output_dir, filename)

        with Image.open(img_path) as img:
            cropped = crop_image(img, crop_box)
            cropped.save(output_path, 'PNG', optimize=True)
            processed_count += 1

    # Create metadata
    metadata = {
        "source_dir": os.path.abspath(input_dir),
        "crop_box": {
            "left": left,
            "top": top,
            "right": right,
            "bottom": bottom
        },
        "original_size": {
            "width": original_size[0],
            "height": original_size[1]
        },
        "trimmed_size": {
            "width": new_size[0],
            "height": new_size[1]
        },
        "total_pages": processed_count,
        "trimmed_at": datetime.now().isoformat(),
        "note": note
    }

    # Load existing metadata to preserve history
    metadata_path = os.path.join(output_dir, "trim_metadata.json")
    history = []

    # Check for previous trim_metadata.json in output_dir's parent
    # (in case we're re-trimming)
    parent_metadata_path = os.path.join(input_dir, "trimmed", "trim_metadata.json")
    if os.path.exists(parent_metadata_path) and parent_metadata_path != metadata_path:
        try:
            with open(parent_metadata_path, 'r') as f:
                old_metadata = json.load(f)
                history = old_metadata.get("history", [])
                # Add the old current as history entry
                if "crop_box" in old_metadata:
                    history.append({
                        "timestamp": old_metadata.get("trimmed_at"),
                        "crop_box": old_metadata.get("crop_box"),
                        "note": old_metadata.get("note")
                    })
        except Exception:
            pass

    metadata["history"] = history

    # Save metadata
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    logger.info(f"✓ Trimmed {processed_count} images")
    logger.info(f"  Output: {output_dir}")
    logger.info(f"  Metadata: {metadata_path}")

    return {
        "processed_count": processed_count,
        "output_dir": output_dir,
        "original_size": original_size,
        "new_size": new_size,
        "crop_box": crop_box
    }


def main():
    """Main entry point for CLI."""
    parser = argparse.ArgumentParser(
        description="Trim Kindle screenshots with specified crop box"
    )

    parser.add_argument(
        "--input",
        required=True,
        help="Input directory containing original screenshots (required)"
    )

    parser.add_argument(
        "--crop",
        required=True,
        help="Crop box as 'left,top,right,bottom' (e.g., '100,50,3700,2100')"
    )

    parser.add_argument(
        "--output",
        help="Output directory (default: {input}/trimmed/)"
    )

    parser.add_argument(
        "--note",
        help="Note to record in trim metadata"
    )

    parser.add_argument(
        "--pages",
        help="Specific pages to trim (comma-separated, e.g., '5,8,10,12'). If omitted, all pages are trimmed."
    )

    parser.add_argument(
        "--config",
        default="config.yaml",
        help="Config file path (default: config.yaml)"
    )

    args = parser.parse_args()

    # Load config
    config = load_config(args.config)
    trim_config = config.get('trim', {})

    # Validate input directory
    if not os.path.isdir(args.input):
        print(f"Error: Input directory not found: {args.input}")
        sys.exit(1)

    # Parse crop box
    try:
        crop_box = parse_crop_box(args.crop)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

    # Determine output directory
    default_subdir = trim_config.get('default_output_subdir', 'trimmed')
    output_dir = args.output or os.path.join(args.input, default_subdir)

    # Parse pages if specified
    pages = None
    if args.pages:
        try:
            pages = [int(p.strip()) for p in args.pages.split(',')]
        except ValueError:
            print(f"Error: Invalid pages format '{args.pages}'. Expected comma-separated numbers (e.g., '5,8,10,12')")
            sys.exit(1)

    # Execute trimming
    try:
        result = trim_images(
            input_dir=args.input,
            output_dir=output_dir,
            crop_box=crop_box,
            note=args.note,
            pages=pages
        )

        print("\n" + "="*50)
        print("Trim completed successfully!")
        print(f"  Pages trimmed: {result['processed_count']}")
        print(f"  Original size: {result['original_size'][0]}x{result['original_size'][1]}")
        print(f"  New size: {result['new_size'][0]}x{result['new_size'][1]}")
        print(f"  Output: {result['output_dir']}")
        print("="*50)

    except ValueError as e:
        print(f"\nError: {e}")
        sys.exit(1)

    except Exception as e:
        print(f"\nTrim failed: {e}")
        logger.exception("Full error:")
        sys.exit(1)


if __name__ == "__main__":
    main()
