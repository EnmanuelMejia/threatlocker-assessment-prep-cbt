#!/usr/bin/env python3
"""Stage the deployable asset tree for threatlocker-assessment-prep-cbt.

Copies the built CBT into deploy/site/bootcamps/threatlocker-assessment-prep/
so the deploy-worker-assets manifest carries the full /bootcamps/... path
prefix that the zone routes map to. Re-run after re-assembling content.json.
"""
import os, shutil, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEST = os.path.join(ROOT, "deploy", "site", "bootcamps", "threatlocker-assessment-prep")
COPY = ["index.html", "content.json", "engine", "chat", "assets"]

if os.path.isdir(DEST):
    shutil.rmtree(DEST)
os.makedirs(DEST)

for name in COPY:
    src = os.path.join(ROOT, name)
    dst = os.path.join(DEST, name)
    if not os.path.exists(src):
        print(f"ERROR: missing {src} — run python3 assemble.py first")
        sys.exit(1)
    if os.path.isdir(src):
        shutil.copytree(src, dst)
    else:
        shutil.copy2(src, dst)

count = sum(len(files) for _, _, files in os.walk(DEST))
print(f"staged {count} files -> {DEST}")
