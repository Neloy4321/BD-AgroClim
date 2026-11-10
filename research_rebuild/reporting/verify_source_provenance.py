#!/usr/bin/env python3
"""Verify shipped paper1_pipeline files byte-for-byte against notebook's embedded source."""
import argparse
import base64
import hashlib
import json
import re
import zipfile
import zlib
from pathlib import Path


def sha(contents):
    return hashlib.sha256(contents).hexdigest()


def verify(notebooks, source_dir):
    with zipfile.ZipFile(notebooks) as archive:
        nb = json.loads(archive.read("Paper1_01_Data_Audit_Q1_Revision.ipynb"))
    cell = "".join(nb["cells"][1]["source"])
    match = re.search(r"base64\.b64decode\('([A-Za-z0-9+/=]+)'\)", cell)
    if not match:
        raise AssertionError("Embedded source archive missing")
    source_dict = json.loads(zlib.decompress(base64.b64decode(match.group(1))))
    result = []
    for name, source in sorted(source_dict.items()):
        actual = (Path(source_dir)/name).read_bytes()
        reference = source.encode("utf-8")
        result.append({"file":name,"exact_match":actual == reference,
                       "sha256_embedded":sha(reference),"sha256_distributed":sha(actual)})
    if not all(r["exact_match"] for r in result):
        raise AssertionError("Recovered source file differs from the original embedded code")
    return {"result":"PASS","matched_files":len(result),"files":result,
            "notebook_sha256":sha(Path(notebooks).read_bytes())}


if __name__ == "__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--notebooks",required=True)
    p.add_argument("--source-dir",required=True)
    p.add_argument("--output",required=True)
    a=p.parse_args()
    result=verify(a.notebooks,a.source_dir)
    Path(a.output).write_text(json.dumps(result,indent=2))
    print(f"{result['result']}: {result['matched_files']} original source files")
