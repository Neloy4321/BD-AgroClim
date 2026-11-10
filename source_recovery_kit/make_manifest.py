#!/usr/bin/env python3
"""Deterministically hash every other file in this kit after generation/tests."""
from __future__ import annotations

import hashlib
from pathlib import Path


HERE = Path(__file__).resolve().parent
MANIFEST = HERE / "integrity_manifest_sha256.txt"


def main():
    rows = []
    paths = list(HERE.iterdir()) + list((HERE / "drive_original_audit_results").glob("*"))
    for path in sorted(paths, key=lambda p: str(p.relative_to(HERE))):
        if not path.is_file() or path == MANIFEST:
            continue
        rows.append(hashlib.sha256(path.read_bytes()).hexdigest() + "  " + str(path.relative_to(HERE)))
    MANIFEST.write_text("\n".join(rows) + "\n", encoding="utf-8")
    print(f"Hashed {len(rows)} files: {MANIFEST}")


if __name__ == "__main__":
    main()
