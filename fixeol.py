#!/usr/bin/env python3
import argparse
import os
from pathlib import Path

SUPPORTED_EXTENSIONS = {".h", ".c", ".cpp"}


def detect_encoding(data: bytes) -> str:
    # Keep UTF-8 BOM if present
    if data.startswith(b"\xef\xbb\xbf"):
        return "utf-8-sig"

    # Try UTF-8 first
    try:
        data.decode("utf-8")
        return "utf-8"
    except UnicodeDecodeError:
        pass

    # Fallback for older Windows/C source files
    return "cp1252"


def normalize_text(text: str, eol: str, ensure_blank_line_at_end: bool) -> str:
    # Normalize every possible line ending to '\n' first
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    if ensure_blank_line_at_end:
        # Remove trailing newlines, then add two EOLs:
        # one to end the last line, one extra for a blank line at EOF
        text = text.rstrip("\n") + "\n\n"
    else:
        # Only ensure normal single newline at EOF
        text = text.rstrip("\n") + "\n"

    # Convert back to requested EOL style
    if eol != "\n":
        text = text.replace("\n", eol)

    return text


def process_file(path: Path, eol: str, ensure_blank_line_at_end: bool, dry_run: bool) -> bool:
    original_data = path.read_bytes()
    encoding = detect_encoding(original_data)

    try:
        original_text = original_data.decode(encoding)
    except UnicodeDecodeError:
        print(f"[skip] {path} (cannot decode)")
        return False

    new_text = normalize_text(original_text, eol, ensure_blank_line_at_end)
    new_data = new_text.encode(encoding)

    if new_data != original_data:
        print(f"[fix ] {path}")
        if not dry_run:
            path.write_bytes(new_data)
        return True
    else:
        print(f"[ ok ] {path}")
        return False


def should_process(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Recursively fix line endings in .h/.c/.cpp files and ensure a blank line at EOF."
    )
    parser.add_argument(
        "root",
        nargs="?",
        default=".",
        help="Root directory to scan recursively (default: current directory)."
    )
    parser.add_argument(
        "--eol",
        choices=["crlf", "lf"],
        default="crlf",
        help="Output line ending style (default: crlf)."
    )
    parser.add_argument(
        "--no-blank-line-at-end",
        action="store_true",
        help="Do not force an extra empty line at the end of file."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would change without modifying files."
    )

    args = parser.parse_args()

    root = Path(args.root)
    eol = "\r\n" if args.eol == "crlf" else "\n"
    ensure_blank_line_at_end = not args.no_blank_line_at_end

    if not root.exists():
        print(f"Error: path does not exist: {root}")
        return 1

    changed = 0
    scanned = 0

    for dirpath, dirnames, filenames in os.walk(root):
        # Skip common build/source-control folders
        dirnames[:] = [
            d for d in dirnames
            if d not in {".git", ".svn", ".vs", ".idea", "build", "out", "bin", "obj", "__pycache__"}
        ]

        for filename in filenames:
            path = Path(dirpath) / filename
            if should_process(path):
                scanned += 1
                if process_file(path, eol, ensure_blank_line_at_end, args.dry_run):
                    changed += 1

    print()
    print(f"Scanned : {scanned}")
    print(f"Changed : {changed}")
    print(f"Mode    : {'dry-run' if args.dry_run else 'write'}")
    print(f"EOL     : {repr(eol)}")
    print(f"Blank EOF line forced : {ensure_blank_line_at_end}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())