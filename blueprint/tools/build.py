#!/usr/bin/env python3
"""PHANTOMS // PROJECT BLUEPRINT — one-command build.

usage:  .venv/bin/python tools/build.py [--pdf-only|--web-only]

outputs:
  dist/PHANTOMS-Project-Blueprint.pdf   (A4, RTL, print-ready)
  dist/web/index.html                   (live preview + browser print)
"""
import os, shutil, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import mdast
import render_pdf
import render_web

def main():
    arg = sys.argv[1] if len(sys.argv) > 1 else ""
    docs = mdast.load_all(os.path.join(ROOT, "content"))
    pdf_path = os.path.join(ROOT, "dist", "PHANTOMS-Project-Blueprint.pdf")
    if arg != "--web-only":
        pages = render_pdf.render(docs, pdf_path)
        print(f"[pdf ] {pdf_path}  ({max(pages.values()) if pages else '?'}+ pages)")
    if arg != "--pdf-only":
        web = render_web.render(docs, os.path.join(ROOT, "dist", "web"))
        shutil.copy(pdf_path, os.path.join(ROOT, "dist", "web",
                                            os.path.basename(pdf_path)))
        print(f"[web ] {web}")
    print("[ok  ] build complete")

if __name__ == "__main__":
    main()
