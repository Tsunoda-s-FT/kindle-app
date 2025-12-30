#!/usr/bin/env python3
"""Crop Marker Script for Kindle Captures

Draws crop markers on original images to visually preview trim positions
before actual trimming. This enables accurate crop box adjustment.

Generates 5 images per page:
1. Full image with crop markers
2. Top edge zoom (for precise top boundary check)
3. Bottom edge zoom (for precise bottom boundary check)
4. Left edge zoom (for precise left boundary check)
5. Right edge zoom (for precise right boundary check)

Workflow:
1. Run mark.py with crop values to draw markers on sample pages
2. Review marked images (especially edge zooms) to check crop positions
3. Adjust crop values and re-run mark.py if needed
4. Once satisfied, run trim.py with the final crop values
"""

import argparse
import glob
import os
import sys
from pathlib import Path
from typing import List, Optional, Tuple

from PIL import Image, ImageDraw


def parse_crop_box(crop_str: str) -> Tuple[int, int, int, int]:
    """Parse crop box string into tuple."""
    try:
        parts = [int(x.strip()) for x in crop_str.split(',')]
        if len(parts) != 4:
            raise ValueError("Crop box must have exactly 4 values")
        return tuple(parts)
    except Exception as e:
        raise ValueError(
            f"Invalid crop box format '{crop_str}'. "
            "Expected: 'left,top,right,bottom' (e.g., '100,50,3700,2100')"
        )


def draw_crop_markers(
    img: Image.Image,
    crop_box: Tuple[int, int, int, int],
    line_color: str = "red",
    line_width: int = 4,
    corner_length: int = 80
) -> Image.Image:
    """
    Draw crop markers on an image.

    Draws:
    - Full border rectangle showing the crop area
    - L-shaped corner markers for precise positioning

    Args:
        img: PIL Image object
        crop_box: (left, top, right, bottom) coordinates
        line_color: Color for the markers
        line_width: Width of the marker lines
        corner_length: Length of the L-shaped corner markers

    Returns:
        New PIL Image with markers drawn
    """
    # Create a copy to avoid modifying the original
    marked_img = img.copy()
    draw = ImageDraw.Draw(marked_img)

    left, top, right, bottom = crop_box

    # Draw the full rectangle border
    draw.rectangle(
        [left, top, right, bottom],
        outline=line_color,
        width=line_width
    )

    # Draw L-shaped corner markers (thicker, for emphasis)
    corner_width = line_width * 2

    # Top-left corner
    draw.line([(left, top), (left + corner_length, top)], fill=line_color, width=corner_width)
    draw.line([(left, top), (left, top + corner_length)], fill=line_color, width=corner_width)

    # Top-right corner
    draw.line([(right, top), (right - corner_length, top)], fill=line_color, width=corner_width)
    draw.line([(right, top), (right, top + corner_length)], fill=line_color, width=corner_width)

    # Bottom-left corner
    draw.line([(left, bottom), (left + corner_length, bottom)], fill=line_color, width=corner_width)
    draw.line([(left, bottom), (left, bottom - corner_length)], fill=line_color, width=corner_width)

    # Bottom-right corner
    draw.line([(right, bottom), (right - corner_length, bottom)], fill=line_color, width=corner_width)
    draw.line([(right, bottom), (right, bottom - corner_length)], fill=line_color, width=corner_width)

    return marked_img


def create_edge_zoom(
    marked_img: Image.Image,
    crop_box: Tuple[int, int, int, int],
    edge: str,
    margin: int = 150,
    zoom_height: int = 300
) -> Image.Image:
    """
    Create a zoomed image focusing on one edge of the crop box.

    Args:
        marked_img: Image with markers already drawn
        crop_box: (left, top, right, bottom) coordinates
        edge: Which edge to zoom: 'top', 'bottom', 'left', 'right'
        margin: Pixels to include on each side of the crop line
        zoom_height: Height of the zoomed strip (for top/bottom edges)

    Returns:
        Cropped and zoomed image focusing on the specified edge
    """
    left, top, right, bottom = crop_box
    img_width, img_height = marked_img.size

    if edge == 'top':
        # Horizontal strip around top edge
        y_start = max(0, top - margin)
        y_end = min(img_height, top + margin)
        x_start = max(0, left - margin)
        x_end = min(img_width, right + margin)
        crop_region = (x_start, y_start, x_end, y_end)

    elif edge == 'bottom':
        # Horizontal strip around bottom edge
        y_start = max(0, bottom - margin)
        y_end = min(img_height, bottom + margin)
        x_start = max(0, left - margin)
        x_end = min(img_width, right + margin)
        crop_region = (x_start, y_start, x_end, y_end)

    elif edge == 'left':
        # Vertical strip around left edge
        x_start = max(0, left - margin)
        x_end = min(img_width, left + margin)
        y_start = max(0, top - margin)
        y_end = min(img_height, bottom + margin)
        crop_region = (x_start, y_start, x_end, y_end)

    elif edge == 'right':
        # Vertical strip around right edge
        x_start = max(0, right - margin)
        x_end = min(img_width, right + margin)
        y_start = max(0, top - margin)
        y_end = min(img_height, bottom + margin)
        crop_region = (x_start, y_start, x_end, y_end)

    else:
        raise ValueError(f"Unknown edge: {edge}")

    return marked_img.crop(crop_region)


def mark_images(
    input_dir: str,
    output_dir: str,
    crop_box: Tuple[int, int, int, int],
    pages: Optional[List[int]] = None,
    line_color: str = "red",
    line_width: int = 4,
    edge_margin: int = 150
) -> dict:
    """
    Draw crop markers on images and create edge zoom images.

    Args:
        input_dir: Directory containing original PNG files
        output_dir: Directory for marked images
        crop_box: (left, top, right, bottom) coordinates
        pages: Optional list of page numbers to mark
        line_color: Color for the markers
        line_width: Width of the marker lines
        edge_margin: Pixels to include around each edge in zoom images

    Returns:
        dict: Summary of the operation
    """
    # Find all screenshot files
    image_pattern = os.path.join(input_dir, "page_*.png")
    image_files = sorted(glob.glob(image_pattern))

    # Filter by specific pages if requested
    if pages:
        def get_page_number(filepath: str) -> int:
            basename = os.path.basename(filepath)
            return int(basename.replace('page_', '').replace('.png', ''))

        image_files = [f for f in image_files if get_page_number(f) in pages]
        print(f"Marking pages: {pages}")

    if not image_files:
        raise ValueError(f"No screenshots found in {input_dir}")

    print(f"Found {len(image_files)} screenshots")

    # Validate crop box against first image
    with Image.open(image_files[0]) as first_img:
        original_size = first_img.size
        left, top, right, bottom = crop_box

        if right > original_size[0] or bottom > original_size[1]:
            raise ValueError(
                f"Crop box ({right}, {bottom}) exceeds image size "
                f"({original_size[0]}, {original_size[1]})"
            )

    print(f"Image size: {original_size[0]}x{original_size[1]}")
    print(f"Crop box: ({left}, {top}, {right}, {bottom})")
    print(f"Result size after trim: {right - left}x{bottom - top}")

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    # Process images
    processed_files = []
    for img_path in image_files:
        filename = os.path.basename(img_path)
        base_name = filename.replace('.png', '')

        with Image.open(img_path) as img:
            # 1. Full image with markers
            marked_img = draw_crop_markers(
                img, crop_box,
                line_color=line_color,
                line_width=line_width
            )

            # Save full marked image
            full_path = os.path.join(output_dir, f"{base_name}_marked.png")
            marked_img.save(full_path, 'PNG')
            processed_files.append(full_path)

            # 2-5. Edge zoom images
            for edge in ['top', 'bottom', 'left', 'right']:
                edge_img = create_edge_zoom(
                    marked_img, crop_box, edge,
                    margin=edge_margin
                )
                edge_path = os.path.join(output_dir, f"{base_name}_{edge}.png")
                edge_img.save(edge_path, 'PNG')
                processed_files.append(edge_path)

            print(f"  Marked: {base_name} (full + 4 edge zooms)")

    print(f"\n✓ Generated {len(processed_files)} images ({len(image_files)} pages × 5 views)")
    print(f"  Output: {output_dir}")

    return {
        "processed_count": len(image_files),
        "output_dir": output_dir,
        "output_files": processed_files,
        "original_size": original_size,
        "crop_box": crop_box
    }


def main():
    """Main entry point for CLI."""
    parser = argparse.ArgumentParser(
        description="Draw crop markers on Kindle screenshots to preview trim positions"
    )

    parser.add_argument(
        "--input",
        required=True,
        help="Input directory containing original screenshots"
    )

    parser.add_argument(
        "--crop",
        required=True,
        help="Crop box as 'left,top,right,bottom' (e.g., '305,115,3280,1955')"
    )

    parser.add_argument(
        "--output",
        help="Output directory (default: {input}/marked/)"
    )

    parser.add_argument(
        "--pages",
        help="Specific pages to mark (comma-separated, e.g., '5,8,10,12')"
    )

    parser.add_argument(
        "--color",
        default="red",
        help="Marker color (default: red). Options: red, green, blue, yellow, cyan, magenta"
    )

    parser.add_argument(
        "--width",
        type=int,
        default=4,
        help="Marker line width in pixels (default: 4)"
    )

    parser.add_argument(
        "--margin",
        type=int,
        default=150,
        help="Margin around edges in zoom images (default: 150 pixels)"
    )

    args = parser.parse_args()

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
    output_dir = args.output or os.path.join(args.input, "marked")

    # Parse pages if specified
    pages = None
    if args.pages:
        try:
            pages = [int(p.strip()) for p in args.pages.split(',')]
        except ValueError:
            print(f"Error: Invalid pages format '{args.pages}'")
            sys.exit(1)

    # Execute marking
    try:
        result = mark_images(
            input_dir=args.input,
            output_dir=output_dir,
            crop_box=crop_box,
            pages=pages,
            line_color=args.color,
            line_width=args.width,
            edge_margin=args.margin
        )

        print("\n" + "="*50)
        print("Marking completed!")
        print(f"  Pages marked: {result['processed_count']}")
        print(f"  Crop box: {result['crop_box']}")
        print(f"  Output: {result['output_dir']}")
        print("="*50)
        print("\nGenerated files per page:")
        print("  - {page}_marked.png  : Full image with crop markers")
        print("  - {page}_top.png     : Top edge zoom")
        print("  - {page}_bottom.png  : Bottom edge zoom")
        print("  - {page}_left.png    : Left edge zoom")
        print("  - {page}_right.png   : Right edge zoom")
        print("\nNext steps:")
        print("1. Review edge zoom images to check crop positions precisely")
        print("2. Adjust crop values if needed and re-run mark.py")
        print("3. Once satisfied, run trim.py with the final crop values")

    except ValueError as e:
        print(f"\nError: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\nMarking failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
