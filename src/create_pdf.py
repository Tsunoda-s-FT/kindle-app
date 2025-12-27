#!/usr/bin/env python3
"""PDF Generation Script

Converts captured screenshots to PDF format.
"""

import argparse
import glob
import logging
import os
import sys
from pathlib import Path
from PIL import Image
from tqdm import tqdm
import img2pdf
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


def create_pdf(
    input_dir: str,
    output_path: str = None,
    quality: int = 85,
    resize: float = 1.0
) -> str:
    """
    Convert screenshots to PDF using img2pdf.

    Args:
        input_dir: Directory containing screenshots
        output_path: Output PDF path (default: {dirname}.pdf)
        quality: JPEG quality if conversion needed (1-100)
        resize: Resize ratio (0.1-1.0, 1.0 = no resize)

    Returns:
        str: Path to created PDF file

    Raises:
        ValueError: If no screenshots found
        Exception: If PDF creation fails
    """
    # Find all screenshot files
    image_pattern = os.path.join(input_dir, "page_*.png")
    image_files = sorted(glob.glob(image_pattern))

    if not image_files:
        raise ValueError(f"No screenshots found in {input_dir}")

    logger.info(f"Found {len(image_files)} screenshots")

    # Default output path
    if not output_path:
        dirname = os.path.basename(input_dir.rstrip('/'))
        output_path = f"{dirname}.pdf"

    logger.info(f"Creating PDF: {output_path}")

    # Process images if needed
    processed_images = []
    temp_files = []

    try:
        if resize < 1.0:
            logger.info(f"Resizing images to {resize * 100:.0f}% of original size...")

            for img_path in tqdm(image_files, desc="Processing images"):
                # Open image
                img = Image.open(img_path)

                # Calculate new size
                new_size = (
                    int(img.width * resize),
                    int(img.height * resize)
                )

                # Resize image
                img_resized = img.resize(new_size, Image.Resampling.LANCZOS)

                # Save to temp file as JPEG
                temp_path = img_path.replace('.png', f'_resized_{resize}.jpg')
                img_resized.save(temp_path, 'JPEG', quality=quality)

                processed_images.append(temp_path)
                temp_files.append(temp_path)

                img.close()
                img_resized.close()

        else:
            # Use original PNG files
            processed_images = image_files

        # Convert to PDF using img2pdf (lossless for PNG)
        logger.info("Converting to PDF...")

        with open(output_path, "wb") as f:
            f.write(img2pdf.convert(processed_images))

        # Cleanup temp files
        if temp_files:
            logger.info("Cleaning up temporary files...")
            for temp_file in temp_files:
                try:
                    os.remove(temp_file)
                except Exception as e:
                    logger.warning(f"Failed to remove temp file {temp_file}: {e}")

        # Report results
        file_size_mb = os.path.getsize(output_path) / (1024 * 1024)

        logger.info("✓ PDF created successfully!")
        logger.info(f"  Output: {output_path}")
        logger.info(f"  Pages: {len(image_files)}")
        logger.info(f"  Size: {file_size_mb:.2f} MB")

        return output_path

    except Exception as e:
        logger.error(f"Failed to create PDF: {e}")

        # Cleanup temp files on error
        for temp_file in temp_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except:
                pass

        raise


def main():
    """Main entry point for CLI."""
    parser = argparse.ArgumentParser(
        description="Convert Kindle screenshots to PDF"
    )

    parser.add_argument(
        "--input",
        required=True,
        help="Input directory containing screenshots (required)"
    )

    parser.add_argument(
        "--output",
        help="Output PDF filename (default: {directory_name}.pdf)"
    )

    parser.add_argument(
        "--quality",
        type=int,
        default=None,
        help="JPEG quality if conversion needed (1-100, default: config or 85)"
    )

    parser.add_argument(
        "--resize",
        type=float,
        default=None,
        help="Resize ratio (0.1-1.0, default: config or 1.0 = no resize)"
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
    pdf_config = config.get('pdf', {})
    quality = args.quality if args.quality is not None else pdf_config.get('default_quality', 85)
    resize = args.resize if args.resize is not None else pdf_config.get('default_resize', 1.0)

    # Validate arguments
    if not os.path.isdir(args.input):
        print(f"❌ Error: Input directory not found: {args.input}")
        sys.exit(1)

    if quality < 1 or quality > 100:
        print("❌ Error: Quality must be between 1 and 100")
        sys.exit(1)

    if resize < 0.1 or resize > 1.0:
        print("❌ Error: Resize ratio must be between 0.1 and 1.0")
        sys.exit(1)

    # Create PDF
    try:
        output_path = create_pdf(
            input_dir=args.input,
            output_path=args.output,
            quality=quality,
            resize=resize
        )

        print("\n" + "="*50)
        print("✓ PDF created successfully!")
        print(f"  Output: {output_path}")
        print("="*50)

    except ValueError as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

    except Exception as e:
        print(f"\n❌ PDF creation failed: {e}")
        logger.exception("Full error:")
        sys.exit(1)


if __name__ == "__main__":
    main()
