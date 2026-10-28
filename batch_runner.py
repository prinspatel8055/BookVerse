import os
import sys
import time
from pathlib import Path
from typing import List

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from core.config import OUTPUT_DIR
from core.cache_manager import TranslationCache
from core.translator import TranslatorEngine
from core.image_translator import ImageTranslator
from core.pdf_engine import PDFEngine
from core.fb2_engine import FB2Engine

def get_library_root() -> Path:
    candidates = [
        Path(__file__).resolve().parent.parent / "hacking_books_ru-main" / "hacking_books_ru-main",
        Path(__file__).resolve().parent.parent / "hacking_books_ru-main",
        Path(__file__).resolve().parent / "hacking_books_ru-main",
        Path(r"D:\Python books tech\hacking_books_ru-main\hacking_books_ru-main"),
        Path.cwd() / "hacking_books_ru-main" / "hacking_books_ru-main",
        Path.cwd() / "hacking_books_ru-main"
    ]
    for c in candidates:
        if c.exists() and any(c.iterdir()):
            return c.resolve()
    return candidates[0].resolve()

LIBRARY_ROOT = get_library_root()

CATEGORIES = [
    ("ALL", "Entire Library (All 320+ Books Across Subfolders)", LIBRARY_ROOT),
    ("exploits", "Exploit Development & Memory Corruption", LIBRARY_ROOT / "exploits"),
    ("malware", "Malware Analysis & Reverse Engineering", LIBRARY_ROOT / "malware"),
    ("reverse", "Binary Reverse Engineering & Disassembly", LIBRARY_ROOT / "reverse"),
    ("pentest", "Penetration Testing & Offensive Security", LIBRARY_ROOT / "pentest"),
    ("web", "Web Application Security & Exploits", LIBRARY_ROOT / "web"),
    ("phrack", "Phrack Magazine Russian Editions", LIBRARY_ROOT / "phrack"),
    ("wasm", "WebAssembly & Low-level Architectures", LIBRARY_ROOT / "wasm"),
    ("project.zero", "Google Project Zero Research", LIBRARY_ROOT / "project.zero"),
    ("other", "General Security & System Architecture", LIBRARY_ROOT / "other"),
]

def find_books(directory: Path, recursive: bool = True) -> List[Path]:
    if not directory.exists():
        return []
    items = directory.rglob("*") if recursive else directory.iterdir()
    books = [f for f in items if f.is_file() and f.suffix.lower() in (".pdf", ".fb2")]
    return sorted(books, key=lambda x: x.name.lower())

def print_banner():
    print("=" * 75)
    print("      ROCKET BATCH TRANSLATOR - 320+ RUSSIAN HACKING BOOKS")
    print("      Universal PDF & FB2 Multi-Threaded Neural Pipeline")
    print("=" * 75)

def main():
    print_banner()

    print("\nSelect Library Category to Translate:")
    for idx, (cat_id, desc, path) in enumerate(CATEGORIES, start=1):
        count = len(find_books(path, recursive=(cat_id == "ALL")))
        print(f"  [{idx:2d}] {cat_id:<12} - {desc} ({count} books)")
    print("  [ C] Custom Folder Path")
    print("  [ Q] Quit")

    choice = input("\nEnter selection (1-10, C, or Q) [default 1]: ").strip().lower()
    if choice in ("q", "quit", "exit"):
        print("Exiting.")
        return 0

    target_dir = None
    recursive = True

    if not choice or choice == "1":
        target_dir = LIBRARY_ROOT
        recursive = True
    elif choice.isdigit() and 2 <= int(choice) <= len(CATEGORIES):
        target_dir = CATEGORIES[int(choice) - 1][2]
        recursive = False
    elif choice == "c":
        custom_input = input("Enter full folder path: ").strip().strip('"')
        target_dir = Path(custom_input)
        recursive = True
    else:
        target_dir = LIBRARY_ROOT
        recursive = True

    books = find_books(target_dir, recursive=recursive)
    if not books:
        print(f"\n[!] No .pdf or .fb2 books found in: {target_dir}")
        return 0

    print(f"\n[*] Found {len(books)} books in {target_dir}")

    # Mode selection
    print("\nSelect Translation Engine Mode:")
    print("  [1] ⚡ Hybrid Mode (High Speed Google Pool + Offline AI Fallback) [RECOMMENDED]")
    print("  [2] 🛡️ 100% Offline AI Mode (Pure CPU Neural Matrix)")
    engine_choice = input("Enter choice (1/2) [default 1]: ").strip()
    engine_mode = "offline" if engine_choice == "2" else "hybrid"

    # Skip existing check
    skip_input = input("Skip books that are already translated? (Y/n) [default Y]: ").strip().lower()
    skip_existing = skip_input != "n"

    # Filter books if skip_existing
    queue = []
    already_done_count = 0
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    for b in books:
        out_name = f"{b.stem}_translated_en{b.suffix.lower()}"
        out_file = OUTPUT_DIR / out_name
        is_already_done = out_file.exists() or any(
            b.stem in p.name and "translated" in p.name and p.suffix.lower() == b.suffix.lower()
            for p in OUTPUT_DIR.glob(f"*{b.stem}*")
        )
        if skip_existing and is_already_done:
            already_done_count += 1
        else:
            queue.append(b)

    print(f"\n[INFO] Total books found:    {len(books)}")
    print(f"[INFO] Already translated:   {already_done_count} (Skipping)")
    print(f"[INFO] Books to translate:   {len(queue)}")
    print(f"[INFO] Engine Mode:          {engine_mode.upper()}")
    print(f"[INFO] Output Directory:     {OUTPUT_DIR}\n")

    if not queue:
        print("[SUCCESS] All books in this category are already translated! Nothing to do.")
        return 0

    confirm = input("Press ENTER to start batch translation (or Ctrl+C to abort)...")

    # Initialize shared engines
    print("\nInitializing Neural Translation Pipeline & Cache...")
    cache_mgr = TranslationCache()
    translator = TranslatorEngine(cache=cache_mgr, mode=engine_mode)
    image_translator = ImageTranslator(translator=translator)
    pdf_engine = PDFEngine(translator=translator, image_translator=image_translator)
    fb2_engine = FB2Engine(translator=translator, image_translator=image_translator)

    success_count = 0
    error_count = 0
    start_total_time = time.time()

    def make_progress(book_name, current_idx, total_queue):
        def cb(info):
            if isinstance(info, dict):
                pct = info.get("percent", 0)
                speed = info.get("speed", "")
                eta = info.get("eta", "")
                msg = info.get("message", "Processing")
                bar_len = 25
                filled = int(bar_len * pct // 100)
                bar = "█" * filled + "░" * (bar_len - filled)
                sys.stdout.write(f"\r  [{current_idx}/{total_queue}] [{bar}] {pct:3d}% | {speed} | ETA: {eta} | {msg[:25]:<25}")
                sys.stdout.flush()
            elif isinstance(info, (int, float)):
                pct = int(info)
                bar_len = 25
                filled = int(bar_len * pct // 100)
                bar = "█" * filled + "░" * (bar_len - filled)
                sys.stdout.write(f"\r  [{current_idx}/{total_queue}] [{bar}] {pct:3d}%")
                sys.stdout.flush()
        return cb

    print("=" * 75)
    print("STARTING BATCH PROCESSING")
    print("=" * 75)

    for idx, book_path in enumerate(queue, start=1):
        book_start = time.time()
        ext = book_path.suffix.lower()
        out_file = OUTPUT_DIR / f"{book_path.stem}_translated_en{ext}"
        print(f"\n\n--> [{idx}/{len(queue)}] {book_path.name}")
        print(f"    Path: {book_path}")
        print(f"    Size: {book_path.stat().st_size / (1024*1024):.2f} MB")

        cb = make_progress(book_path.name, idx, len(queue))

        try:
            if ext == ".pdf":
                pdf_engine.translate_pdf(
                    input_pdf_path=str(book_path),
                    output_pdf_path=str(out_file),
                    source_lang="ru",
                    target_lang="en",
                    translate_images=True,
                    progress_callback=cb
                )
            elif ext == ".fb2":
                fb2_engine.translate_fb2(
                    input_fb2_path=str(book_path),
                    output_fb2_path=str(out_file),
                    source_lang="ru",
                    target_lang="en",
                    translate_images=True,
                    progress_callback=cb
                )
            elapsed = time.time() - book_start
            print(f"\n    [DONE] Completed in {elapsed:.1f}s -> {out_file.name}")
            success_count += 1
        except KeyboardInterrupt:
            print("\n\n[!] Batch interrupted by user. Progress is safely saved.")
            break
        except Exception as e:
            print(f"\n    [ERROR] Failed to translate {book_path.name}: {e}")
            error_count += 1

    total_elapsed = time.time() - start_total_time
    print("\n" + "=" * 75)
    print(f"BATCH SUMMARY:")
    print(f"  Successfully Translated: {success_count} books")
    if error_count:
        print(f"  Errors:                  {error_count} books")
    print(f"  Total Time Taken:        {total_elapsed/60:.1f} minutes")
    print(f"  Output Directory:        {OUTPUT_DIR}")
    print("=" * 75 + "\n")
    return 0

if __name__ == "__main__":
    sys.exit(main())
