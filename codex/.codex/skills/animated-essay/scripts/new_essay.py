#!/usr/bin/env python3
"""Start or build an animated essay.

  new_essay.py --init OUT_DIR                     copy the starter to OUT_DIR/essay.html (refuses to overwrite)
  new_essay.py --source essay.html --data d.json --output built.html
                                                  inject JSON into <script type="application/json" id="data">
"""
import argparse, json, pathlib, re, shutil, sys

SKILL = pathlib.Path(__file__).resolve().parent.parent
ap = argparse.ArgumentParser()
ap.add_argument("--init")
ap.add_argument("--source")
ap.add_argument("--data")
ap.add_argument("--output")
a = ap.parse_args()

if a.init:
    out = pathlib.Path(a.init).expanduser() / "essay.html"
    if out.exists():
        sys.exit(f"refusing to overwrite {out}")
    out.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(SKILL / "assets" / "essay.html", out)
    print(out)
    sys.exit(0)

if not (a.source and a.output):
    ap.error("use --init OUT_DIR, or --source with --output (and optional --data)")
html = pathlib.Path(a.source).read_text()
if a.data:
    blob = json.dumps(json.loads(pathlib.Path(a.data).read_text()), separators=(",", ":")).replace("</", "<\\/")
    html, n = re.subn(r'(<script type="application/json" id="data">)(.*?)(</script>)', lambda m: m.group(1) + blob + m.group(3), html, count=1, flags=re.S)
    if n != 1:
        sys.exit('no <script type="application/json" id="data"> tag found')
pathlib.Path(a.output).write_text(html)
print(a.output, len(html) // 1024, "KB")
