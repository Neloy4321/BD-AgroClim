#!/usr/bin/env python3
"""Build separate complete and reviewer-sized ZIPs with integrity manifests."""
import argparse
import hashlib
import json
import zipfile
from pathlib import Path


def digest(path):
    h=hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda:source.read(1024*1024),b""):
            h.update(block)
    return h.hexdigest()


def includes(root):
    rejected={"smoke","tarc_smoke","__pycache__",".ipynb_checkpoints"}
    for path in sorted(root.rglob("*")):
        if not path.is_file():continue
        rel=path.relative_to(root)
        if any(part in rejected for part in rel.parts) or path.suffix in {".pyc",".pyo"}:
            continue
        if rel.as_posix() in {"evidence/FILE_HASHES_SHA256.txt","evidence/ARCHIVE_INDEX.json"}:
            continue
        yield path,rel


def package(root,dest,files,full):
    with zipfile.ZipFile(dest,"w",allowZip64=True) as archive:
        for path,rel in files:
            if not full and path.suffix==".npz":continue
            compression=zipfile.ZIP_STORED if path.suffix in {".npz",".zip",".png",".pdf"} else zipfile.ZIP_DEFLATED
            archive.write(path,arcname=f"ERA5_Transfer_Reproducibility/{rel.as_posix()}",compress_type=compression)
        for n in ["FILE_HASHES_SHA256.txt","ARCHIVE_INDEX.json"]:
            path=root/"evidence"/n
            archive.write(path,arcname=f"ERA5_Transfer_Reproducibility/evidence/{n}",compress_type=zipfile.ZIP_DEFLATED)
    with zipfile.ZipFile(dest) as archive:
        corrupt=archive.testzip()
        if corrupt:raise AssertionError(f"ZIP integrity failure {corrupt}")
    return {"file":str(dest),"bytes":dest.stat().st_size,"sha256":digest(dest),"complete_predictions":full}


def main(args):
    root=Path(args.root).resolve();dest=Path(args.out).resolve();dest.mkdir(parents=True,exist_ok=True)
    files=list(includes(root))
    manifest={"n_total_files":len(files),"n_prediction_files":sum(p.suffix==".npz" for p,_ in files),
              "sum_source_bytes":sum(p.stat().st_size for p,_ in files),
              "privacy":"No BMD daily observed targets, raw dataset, or any input CSV supplied in these archives.",
              "complete_archive":"includes prediction-only NPZ; companion compact archive has the same metrics and metadata without large NPZ"}
    (root/"evidence"/"ARCHIVE_INDEX.json").write_text(json.dumps(manifest,indent=2))
    (root/"evidence"/"FILE_HASHES_SHA256.txt").write_text("".join(f"{digest(p)}  {r.as_posix()}\n" for p,r in files))
    outputs=[]
    outputs.append(package(root,dest/"ERA5_Transfer_Full_Reproducibility_Results.zip",files,True))
    outputs.append(package(root,dest/"ERA5_Transfer_Reviewer_Evidence_Compact.zip",files,False))
    print(json.dumps(outputs,indent=2))


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root",required=True)
    p.add_argument("--out",required=True)
    main(p.parse_args())
