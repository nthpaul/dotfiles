#!/usr/bin/env python3
"""Initialize a portable LaTeX brief, or compile and render every page."""

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def executable(value):
    resolved = shutil.which(value)
    if not resolved:
        raise ValueError(
            f"Executable not found: {value}. Install Tectonic and Poppler, "
            "or pass --tectonic /path/to/tectonic and --pdftoppm /path/to/pdftoppm."
        )
    return resolved


def run(command, cwd=None, transcript_path=None):
    result = subprocess.run(command, cwd=cwd, text=True, capture_output=True)
    transcript = result.stdout + result.stderr
    if transcript_path:
        transcript_path.write_text(transcript, encoding="utf-8")
    if result.returncode:
        raise ValueError(f"Command failed ({result.returncode}): {command[0]}\n{transcript}")
    return transcript


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--init", type=Path, help="Copy starter sources into this directory")
    parser.add_argument("--source", type=Path, help="Main LaTeX source")
    parser.add_argument("--output", type=Path, help="Final PDF path")
    parser.add_argument("--tectonic", default="tectonic")
    parser.add_argument("--pdftoppm", default="pdftoppm")
    args = parser.parse_args()
    if args.init:
        if args.source or args.output:
            parser.error("Use --init separately from --source and --output")
        destination = args.init.expanduser().resolve()
        assets = Path(__file__).resolve().parents[1] / "assets"
        names = ("brief.tex", "concise-research.sty")
        if any((destination / name).exists() for name in names):
            raise ValueError(f"Starter already exists in {destination}; no files changed")
        destination.mkdir(parents=True, exist_ok=True)
        for name in names:
            shutil.copy2(assets / name, destination / name)
        print(f"Editable sources: {destination}")
        return
    if not args.source or not args.output:
        parser.error("Provide --source and --output, or --init")
    source = args.source.expanduser().resolve(strict=True)
    output = args.output.expanduser().resolve()
    if source.suffix.lower() != ".tex" or output.suffix.lower() != ".pdf":
        parser.error("Source must be .tex and output must be .pdf")
    engine, renderer = executable(args.tectonic), executable(args.pdftoppm)
    output.parent.mkdir(parents=True, exist_ok=True)
    build = output.parent / f"{output.stem}-build"
    build.mkdir(exist_ok=True)
    # Fresh compilation prevents a stale PDF from satisfying a failed run.
    with tempfile.TemporaryDirectory(prefix="compile-", dir=build) as scratch:
        scratch = Path(scratch)
        transcript = run([engine, "--keep-logs", "--outdir", str(scratch), str(source)],
                         cwd=source.parent, transcript_path=build / "compiler-output.txt")
        log = scratch / f"{source.stem}.log"
        combined = transcript
        if log.exists():
            shutil.copy2(log, build / "compile.log")
            combined += log.read_text(encoding="utf-8", errors="replace")
        problems = re.findall(
            r"^.*(?:Overfull \\[hv]box|(?:Reference|Citation).*undefined|"
            r"undefined references|undefined citations|Rerun to get cross-references right).*$",
            combined, flags=re.MULTILINE | re.IGNORECASE,
        )
        if problems:
            raise ValueError("Layout/reference checks failed; fix and rebuild:\n"
                             + "\n".join(dict.fromkeys(problems)))
        pdf = scratch / f"{source.stem}.pdf"
        if not pdf.exists():
            raise ValueError("Compiler returned without producing the expected PDF")
        # Unique QA directories keep old page images out of the final inspection set.
        qa = Path(tempfile.mkdtemp(prefix=f"{output.stem}-qa-", dir=output.parent))
        run([renderer, "-r", "150", "-png", str(pdf), str(qa / "page")])
        pages = sorted(qa.glob("page-*.png"))
        if not pages:
            raise ValueError(f"Renderer produced no pages; inspect {qa}")
        shutil.copy2(pdf, output)
    print(f"PDF: {output}\nLog: {build}\nQA: {qa}\nRendered pages: {len(pages)}")
    print("Open and inspect every PNG before claiming visual QA passed.")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError) as error:
        print(f"Error: {error}", file=sys.stderr)
        sys.exit(1)
