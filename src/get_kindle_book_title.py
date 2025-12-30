#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
import urllib.request
from html import unescape
from pathlib import Path
from typing import Dict, Iterable, Optional, Tuple

ASIN_RE = re.compile(r"(StartActions|EndActions)\.data\.([A-Z0-9]{10})\.asc", re.I)


def find_ebook_root() -> Optional[Path]:
    candidates = [
        Path.home() / "Library/Containers/com.amazon.Lassen/Data/Library/eBooks",
        Path.home() / "Library/Containers/com.amazon.Kindle/Data/Library/eBooks",
        Path.home() / "Library/Containers/com.amazon.kindle/Data/Library/eBooks",
    ]
    for path in candidates:
        if path.is_dir():
            return path
    return None


def iter_action_files(ebook_root: Path) -> Iterable[Path]:
    # The Kindle app writes action files per book under eBooks/<ASIN>/<UUID>/.
    for pattern in ("*/**/StartActions.data.*.asc", "*/**/EndActions.data.*.asc"):
        yield from ebook_root.glob(pattern)


def find_latest_asin(ebook_root: Path) -> Optional[Tuple[str, Path]]:
    candidates = []
    for path in iter_action_files(ebook_root):
        match = ASIN_RE.search(path.name)
        if match:
            candidates.append((path.stat().st_mtime, match.group(2).upper(), path))
    if not candidates:
        return None
    candidates.sort(reverse=True, key=lambda item: item[0])
    _, asin, path = candidates[0]
    return asin, path


def load_title_from_asset_db(library_root: Path, asin: str) -> Optional[str]:
    asset_db = library_root / "KSDK/ksdk.asset.db"
    if not asset_db.exists():
        return None
    try:
        con = sqlite3.connect(asset_db)
        cur = con.cursor()
        cur.execute(
            "SELECT TITLE, ADDITIONAL_DATA FROM Nodes WHERE ASIN = ? "
            "ORDER BY LAST_OPEN_TIME DESC LIMIT 1",
            (asin,),
        )
        row = cur.fetchone()
    finally:
        if "con" in locals():
            con.close()
    if not row:
        return None
    title, additional = row
    if title:
        return title.strip()
    if additional:
        try:
            data = json.loads(additional)
        except json.JSONDecodeError:
            return None
        for key in ("title", "bookTitle", "displayTitle", "docTitle"):
            value = data.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None


def load_title_from_homefeed(library_root: Path, asin: str) -> Optional[str]:
    homefeed = library_root / "Caches/homefeed.json"
    if not homefeed.exists():
        return None
    try:
        payload = json.loads(homefeed.read_text())
    except json.JSONDecodeError:
        return None

    def walk(node: object) -> Optional[str]:
        if isinstance(node, dict):
            asin_value = node.get("asin") or node.get("ASIN") or node.get("asinId")
            if isinstance(asin_value, str) and asin_value.upper() == asin:
                title = node.get("title") or node.get("Title") or node.get("name")
                if isinstance(title, str) and title.strip():
                    return title.strip()
            for value in node.values():
                result = walk(value)
                if result:
                    return result
        elif isinstance(node, list):
            for value in node:
                result = walk(value)
                if result:
                    return result
        return None

    return walk(payload)


def fetch_title_from_amazon(asin: str) -> Optional[str]:
    url = f"https://www.amazon.co.jp/dp/{asin}"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
    except Exception:
        return None

    match = re.search(r'id="productTitle"[^>]*>([^<]+)<', html)
    if match:
        return unescape(match.group(1)).strip()
    match = re.search(r"<title>([^<]+)</title>", html, re.IGNORECASE)
    if match:
        return unescape(match.group(1)).strip().replace(" - Amazon.co.jp", "")
    return None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Detect the currently opened Kindle book title on macOS."
    )
    parser.add_argument("--asin", help="ASIN to resolve (skip auto-detect).")
    parser.add_argument(
        "--online",
        action="store_true",
        help="Fetch title from Amazon if local sources are empty.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output JSON for scripting use.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    ebook_root = find_ebook_root()
    if not ebook_root:
        print("Kindle eBooks directory not found.", file=sys.stderr)
        return 1

    asin = args.asin
    source = "manual"
    action_file = None
    if not asin:
        found = find_latest_asin(ebook_root)
        if not found:
            print("No Kindle action files found to infer ASIN.", file=sys.stderr)
            return 1
        asin, action_file = found
        source = f"action-file:{action_file.name}"

    library_root = ebook_root.parent
    title = load_title_from_asset_db(library_root, asin)
    title_source = "ksdk.asset.db" if title else None

    if not title:
        title = load_title_from_homefeed(library_root, asin)
        title_source = "homefeed.json" if title else None

    if not title and args.online:
        title = fetch_title_from_amazon(asin)
        title_source = "amazon" if title else None

    if args.json:
        payload: Dict[str, Optional[str]] = {
            "asin": asin,
            "title": title,
            "asin_source": source,
            "title_source": title_source,
        }
        print(json.dumps(payload, ensure_ascii=False))
    else:
        print(f"ASIN: {asin}")
        if action_file:
            print(f"ASIN source: {source}")
        if title:
            print(f"Title: {title}")
            print(f"Title source: {title_source}")
        else:
            print("Title: (not found)")
            print("Tip: re-run with --online to query Amazon.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
