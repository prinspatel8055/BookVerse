import os
import sys
import argparse
from pathlib import Path
from typing import Optional

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from core.config import OUTPUT_DIR, LANGUAGE_MAP

def print_banner():
    print("=" * 70)
    print("   UNIVERSAL DOCUMENT & IMAGE TRANSLATOR (PDF / FB2)")
    print("   Translates Foreign Text + OCR Image Text into English")
    print("=" * 70)

def parse_page_range(val: str) -> Optional[tuple[int, int]]:
    if not val:
        return None
    try:
        parts = val.split("-")
        if len(parts) == 1:
            p = int(parts[0]) - 1
            return (p, p + 1)
        start = int(parts[0]) - 1
        end = int(parts[1])
        return (start, end)
    except Exception:
        print(f"[!] Invalid page range '{val}'. Processing all pages.")
        return None

def handle_translate_file(args):
    input_path = Path(args.input).resolve()
    if not input_path.exists():
        print(f"[ERROR] Input file does not exist: {input_path}")
        return 1

    ext = input_path.suffix.lower()
    out_dir = Path(args.output).resolve() if args.output else OUTPUT_DIR
    
    if out_dir.is_dir() or not out_dir.suffix:
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_dir / f"{input_path.stem}_translated_{args.target}{ext}"
    else:
        out_file = out_dir
        out_file.parent.mkdir(parents=True, exist_ok=True)

    print(f"[*] Input File:     {input_path.name}")
    print(f"[*] Output Target:  {out_file}")
    print(f"[*] Source Lang:    {args.source}")
    print(f"[*] Target Lang:    {args.target} ({LANGUAGE_MAP.get(args.target, 'Custom')})")
    engine_mode = getattr(args, "engine", "hybrid")
    print(f"[*] Engine Mode:    {engine_mode.upper()}")
    print(f"[*] OCR on Images:  {'ENABLED' if not args.no_images else 'DISABLED'}")

    from core.translator import TranslatorEngine
    from core.image_translator import ImageTranslator
    from core.pdf_engine import PDFEngine
    from core.fb2_engine import FB2Engine

    translator = TranslatorEngine(mode=engine_mode)
    image_translator = ImageTranslator(translator=translator)

    def progress(cur, total, msg):
        pct = int((cur / max(1, total)) * 100)
        bar_len = 30
        filled = int(bar_len * cur // max(1, total))
        bar = "#" * filled + "-" * (bar_len - filled)
        sys.stdout.write(f"\r[{bar}] {pct:3d}% | {msg[:35]:<35}")
        sys.stdout.flush()

    if ext == ".pdf":
        page_range = parse_page_range(args.pages) if hasattr(args, "pages") else None
        engine = PDFEngine(translator=translator, image_translator=image_translator)
        print("\nStarting PDF translation...")
        out = engine.translate_pdf(
            input_pdf_path=str(input_path),
            output_pdf_path=str(out_file),
            source_lang=args.source,
            target_lang=args.target,
            translate_images=(not args.no_images),
            page_range=page_range,
            progress_callback=progress
        )
        print(f"\n[SUCCESS] Translated PDF saved to: {out}\n")
    elif ext == ".fb2":
        engine = FB2Engine(translator=translator, image_translator=image_translator)
        print("\nStarting FB2 translation...")
        out = engine.translate_fb2(
            input_fb2_path=str(input_path),
            output_fb2_path=str(out_file),
            source_lang=args.source,
            target_lang=args.target,
            translate_images=(not args.no_images),
            progress_callback=progress
        )
        print(f"\n[SUCCESS] Translated FB2 saved to: {out}\n")
        
        # If user also requested PDF conversion for this FB2
        if getattr(args, "to_pdf", False):
            pdf_out = out_file.with_suffix(".pdf")
            print(f"[*] Rendering FB2 to PDF ebook: {pdf_out.name}...")
            engine.fb2_to_pdf(str(out_file), str(pdf_out))
            print(f"[SUCCESS] Converted PDF saved to: {pdf_out}\n")
    else:
        print(f"[ERROR] Unsupported format '{ext}'. Supported: .pdf, .fb2")
        return 1

    return 0

def handle_batch(args):
    folder_path = Path(args.folder).resolve()
    if not folder_path.exists() or not folder_path.is_dir():
        print(f"[ERROR] Folder does not exist: {folder_path}")
        return 1

    out_dir = Path(args.output).resolve() if args.output else (folder_path / "translated_output")
    out_dir.mkdir(parents=True, exist_ok=True)

    patterns = []
    if "pdf" in args.format.lower():
        patterns.append("*.pdf")
    if "fb2" in args.format.lower():
        patterns.append("*.fb2")

    files = []
    for pat in patterns:
        if args.recursive:
            files.extend(list(folder_path.rglob(pat)))
        else:
            files.extend(list(folder_path.glob(pat)))

    files = sorted(set(files), key=lambda x: x.name.lower())

    if not files:
        print(f"[!] No matching {args.format} files found in {folder_path}")
        return 0

    skip_existing = not args.no_skip
    queue = []
    skipped = 0
    for f in files:
        ext = f.suffix.lower()
        out_f = out_dir / f"{f.stem}_translated_{args.target}{ext}"
        if skip_existing and out_f.exists() and out_f.stat().st_size > 1024:
            skipped += 1
        else:
            queue.append(f)

    print(f"[*] Found {len(files)} total files ({skipped} already translated, {len(queue)} to process).")
    print(f"[*] Engine Mode:    {args.engine.upper()}")
    print(f"[*] Output Target:  {out_dir}\n")

    for idx, f in enumerate(queue):
        print(f"\n[{idx+1}/{len(queue)}] Processing: {f.name}")
        class DummyArgs:
            input = str(f)
            output = str(out_dir)
            source = args.source
            target = args.target
            no_images = args.no_images
            pages = None
            to_pdf = getattr(args, "to_pdf", False)
            engine = args.engine
        try:
            handle_translate_file(DummyArgs)
        except Exception as e:
            print(f"[ERROR] Failed to process {f.name}: {e}")

    print(f"\n[BATCH FINISHED] All converted files are located in:\n{out_dir}\n")
    return 0

def main():
    print_banner()
    parser = argparse.ArgumentParser(description="Universal Document & Diagram Image Translator")
    subparsers = parser.add_subparsers(dest="command")

    # Command: translate
    t_parser = subparsers.add_parser("translate", help="Translate a single PDF or FB2 file")
    t_parser.add_argument("input", help="Path to input PDF or FB2 file")
    t_parser.add_argument("-o", "--output", help="Output file or directory path")
    t_parser.add_argument("-s", "--source", default="auto", help="Source language (default: auto)")
    t_parser.add_argument("-t", "--target", default="en", help="Target language (default: en)")
    t_parser.add_argument("--pages", help="Page range for PDF (e.g. 1-10 or 5)")
    t_parser.add_argument("--no-images", action="store_true", help="Skip OCR and image translation")
    t_parser.add_argument("--to-pdf", action="store_true", help="When translating FB2, also generate PDF")
    t_parser.add_argument("--engine", choices=["hybrid", "offline"], default="hybrid", help="AI Engine: hybrid (fast) or offline (pure local CPU)")

    # Command: batch
    b_parser = subparsers.add_parser("batch", help="Batch translate all PDFs / FB2s in a folder")
    b_parser.add_argument("folder", help="Folder containing files")
    b_parser.add_argument("-o", "--output", help="Output directory")
    b_parser.add_argument("-s", "--source", default="auto", help="Source language (default: auto)")
    b_parser.add_argument("-t", "--target", default="en", help="Target language (default: en)")
    b_parser.add_argument("-f", "--format", default="pdf,fb2", help="Formats to convert (comma separated: pdf,fb2)")
    b_parser.add_argument("--no-images", action="store_true", help="Skip OCR and image translation")
    b_parser.add_argument("--to-pdf", action="store_true", help="Also convert FB2s to PDF")
    b_parser.add_argument("--engine", choices=["hybrid", "offline"], default="hybrid", help="AI Engine: hybrid (fast) or offline (pure local CPU)")
    b_parser.add_argument("--no-recursive", dest="recursive", action="store_false", help="Do not search subfolders recursively")
    b_parser.add_argument("--no-skip", action="store_true", help="Do not skip already translated books")
    b_parser.set_defaults(recursive=True)

    args = parser.parse_args()
    if args.command == "translate":
        return handle_translate_file(args)
    elif args.command == "batch":
        return handle_batch(args)
    else:
        parser.print_help()
        return 0

if __name__ == "__main__":
    sys.exit(main())
