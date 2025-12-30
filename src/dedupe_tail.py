#!/usr/bin/env python3
"""Remove trailing duplicate pages from Kindle captures."""

import argparse
import glob
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any

from PIL import Image, ImageChops, ImageStat
import yaml

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
        logger.warning("Config file not found: %s, using defaults", config_path)
        return {}
    except Exception as e:
        logger.error("Error loading config: %s", e)
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


def list_pages(input_dir: str) -> List[str]:
    """List page PNGs in order."""
    image_pattern = os.path.join(input_dir, "page_*.png")
    return sorted(glob.glob(image_pattern))


def compare_images(
    prev_path: str,
    curr_path: str,
    duplicate_threshold: int,
    duplicate_diff_mean: float,
    duplicate_size_kb: Optional[float],
    duplicate_size_ratio: Optional[float]
) -> Dict[str, Any]:
    """Compare two images and return metrics + duplicate decision."""
    with Image.open(prev_path) as prev_img, Image.open(curr_path) as curr_img:
        prev_hash = dhash_int(prev_img)
        curr_hash = dhash_int(curr_img)

    distance = hamming_distance(prev_hash, curr_hash)
    mean_diff = mean_image_diff(prev_path, curr_path)

    prev_size_kb = os.path.getsize(prev_path) / 1024
    curr_size_kb = os.path.getsize(curr_path) / 1024
    size_delta_kb = abs(curr_size_kb - prev_size_kb)
    size_ratio = size_delta_kb / prev_size_kb if prev_size_kb else None

    hash_ok = distance <= duplicate_threshold
    diff_ok = mean_diff <= duplicate_diff_mean

    size_ok = True
    if duplicate_size_kb is not None:
        size_ok = size_ok and size_delta_kb <= duplicate_size_kb
    if duplicate_size_ratio is not None and size_ratio is not None:
        size_ok = size_ok and size_ratio <= duplicate_size_ratio

    is_duplicate = hash_ok and diff_ok and size_ok

    return {
        "distance": distance,
        "mean_diff": mean_diff,
        "size_delta_kb": size_delta_kb,
        "size_ratio": size_ratio,
        "is_duplicate": is_duplicate
    }


def update_metadata(
    input_dir: str,
    removed_files: List[str],
    thresholds: Dict[str, Any],
    min_pages: int
) -> None:
    """Update metadata.json to reflect removed files."""
    if not removed_files:
        return

    metadata_path = os.path.join(input_dir, "metadata.json")
    if not os.path.exists(metadata_path):
        logger.info("metadata.json not found; skipping update.")
        return

    try:
        with open(metadata_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)
    except Exception as e:
        logger.warning("Failed to read metadata.json: %s", e)
        return

    removed_names = {Path(p).name for p in removed_files}
    pages = metadata.get("pages")
    if isinstance(pages, list):
        metadata["pages"] = [p for p in pages if p.get("file") not in removed_names]

    remaining_pages = len(list_pages(input_dir))
    metadata["total_pages"] = remaining_pages

    entry = {
        "timestamp": datetime.now().isoformat(),
        "removed_count": len(removed_files),
        "removed_files": sorted(removed_names),
        "thresholds": thresholds,
        "min_pages": min_pages,
        "remaining_pages": remaining_pages
    }

    history = metadata.get("dedupe_tail_history", [])
    if not isinstance(history, list):
        history = []
    history.append(entry)
    metadata["dedupe_tail_history"] = history
    metadata["dedupe_tail"] = entry

    try:
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.warning("Failed to update metadata.json: %s", e)


def dedupe_tail(
    input_dir: str,
    duplicate_threshold: int,
    duplicate_diff_mean: float,
    duplicate_size_kb: Optional[float],
    duplicate_size_ratio: Optional[float],
    min_pages: int,
    max_remove: Optional[int],
    dry_run: bool
) -> List[str]:
    """Remove trailing duplicate pages and return removed file paths."""
    files = list_pages(input_dir)
    if len(files) < 2:
        logger.info("Not enough pages to dedupe.")
        return []

    removed: List[str] = []
    index = len(files) - 1

    while index > 0:
        remaining = len(files) - len(removed)
        if remaining <= min_pages:
            logger.info("Reached min_pages=%d; stopping dedupe.", min_pages)
            break

        prev_path = files[index - 1]
        curr_path = files[index]

        try:
            metrics = compare_images(
                prev_path,
                curr_path,
                duplicate_threshold=duplicate_threshold,
                duplicate_diff_mean=duplicate_diff_mean,
                duplicate_size_kb=duplicate_size_kb,
                duplicate_size_ratio=duplicate_size_ratio
            )
        except Exception as e:
            logger.warning("Comparison failed for %s vs %s: %s", prev_path, curr_path, e)
            break

        logger.info(
            "Tail check: prev=%s curr=%s distance=%d mean_diff=%.2f "
            "size_delta_kb=%.1f size_ratio=%s duplicate=%s",
            Path(prev_path).name,
            Path(curr_path).name,
            metrics["distance"],
            metrics["mean_diff"],
            metrics["size_delta_kb"],
            f"{metrics['size_ratio']:.4f}" if metrics["size_ratio"] is not None else "n/a",
            "yes" if metrics["is_duplicate"] else "no"
        )

        if not metrics["is_duplicate"]:
            break

        removed.append(curr_path)
        index -= 1

        if max_remove is not None and len(removed) >= max_remove:
            logger.info("Reached max_remove=%d; stopping dedupe.", max_remove)
            break

    if not removed:
        logger.info("No trailing duplicates detected.")
        return []

    if dry_run:
        logger.info("Dry run enabled; no files were removed.")
        return removed

    for path in removed:
        try:
            os.remove(path)
            logger.info("Removed %s", path)
        except Exception as e:
            logger.warning("Failed to remove %s: %s", path, e)

    return removed


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Remove trailing duplicate pages from captured screenshots"
    )

    parser.add_argument(
        "--input",
        required=True,
        help="Input directory containing page_*.png"
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
        "--min-pages",
        type=int,
        default=None,
        help="Minimum pages to keep (default: config or 2)"
    )

    parser.add_argument(
        "--max-remove",
        type=int,
        default=None,
        help="Stop after removing this many pages (default: unlimited)"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only report duplicates, do not delete files"
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

    if not os.path.isdir(args.input):
        print(f"Error: Input directory not found: {args.input}")
        sys.exit(1)

    config = load_config(args.config)
    app_config = config.get("app_capture", {})

    duplicate_threshold = args.dup_threshold if args.dup_threshold is not None else app_config.get("duplicate_threshold", 3)
    duplicate_diff_mean = args.dup_diff_mean if args.dup_diff_mean is not None else app_config.get("duplicate_diff_mean", 3.0)
    duplicate_size_kb = args.dup_size_kb if args.dup_size_kb is not None else app_config.get("duplicate_size_kb")
    duplicate_size_ratio = args.dup_size_ratio if args.dup_size_ratio is not None else app_config.get("duplicate_size_ratio", 0.02)
    min_pages = args.min_pages if args.min_pages is not None else app_config.get("min_pages", 2)

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
    if min_pages <= 0:
        print("❌ Error: min-pages must be a positive integer")
        sys.exit(1)
    if args.max_remove is not None and args.max_remove <= 0:
        print("❌ Error: max-remove must be a positive integer")
        sys.exit(1)

    add_file_logger(args.log_file or app_config.get("log_file"))

    removed = dedupe_tail(
        input_dir=args.input,
        duplicate_threshold=duplicate_threshold,
        duplicate_diff_mean=duplicate_diff_mean,
        duplicate_size_kb=duplicate_size_kb,
        duplicate_size_ratio=duplicate_size_ratio,
        min_pages=min_pages,
        max_remove=args.max_remove,
        dry_run=args.dry_run
    )

    thresholds = {
        "duplicate_threshold": duplicate_threshold,
        "duplicate_diff_mean": duplicate_diff_mean,
        "duplicate_size_kb": duplicate_size_kb,
        "duplicate_size_ratio": duplicate_size_ratio
    }

    if removed and not args.dry_run:
        update_metadata(args.input, removed, thresholds, min_pages)

    print("\n" + "=" * 50)
    if removed:
        action = "Would remove" if args.dry_run else "Removed"
        print(f"{action} {len(removed)} trailing duplicate page(s).")
        for path in removed:
            print(f"  - {Path(path).name}")
    else:
        print("No trailing duplicate pages found.")
    print("=" * 50)


if __name__ == "__main__":
    main()
