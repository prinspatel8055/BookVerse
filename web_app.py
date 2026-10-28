import os
import sys
import uuid
import time
import shutil
import base64
import fitz
from pathlib import Path
from typing import Dict, Any, List, Set

from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request
from pydantic import BaseModel

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from core.config import UPLOAD_DIR, OUTPUT_DIR, CACHE_DB_PATH
from core.cache_manager import TranslationCache
from core.translator import TranslatorEngine
from core.image_translator import ImageTranslator
from core.pdf_engine import PDFEngine
from core.fb2_engine import FB2Engine

app = FastAPI(title="DocTrans Master - Universal Document Translator")

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Progress tracking dictionaries
TASKS: Dict[str, Dict[str, Any]] = {}
BATCH_TASKS: Dict[str, Dict[str, Any]] = {}

# Shared engines
cache_mgr = TranslationCache()
translator = TranslatorEngine(cache=cache_mgr)
image_translator = ImageTranslator(translator=translator)
pdf_engine = PDFEngine(translator=translator, image_translator=image_translator)
fb2_engine = FB2Engine(translator=translator, image_translator=image_translator)

CANCELLED_TASKS: Set[str] = set()

def run_translation_worker(
    task_id: str,
    file_path: str,
    source_lang: str,
    target_lang: str,
    translate_images: bool,
    page_range_str: str,
    engine_mode: str = "hybrid"
):
    try:
        p = Path(file_path)
        ext = p.suffix.lower()

        # Build dedicated worker engine instance with selected engine_mode
        worker_translator = TranslatorEngine(cache=cache_mgr, mode=engine_mode)
        worker_image_translator = ImageTranslator(translator=worker_translator)
        worker_pdf_engine = PDFEngine(translator=worker_translator, image_translator=worker_image_translator)
        worker_fb2_engine = FB2Engine(translator=worker_translator, image_translator=worker_image_translator)

        def progress_cb(*args, **kwargs):
            if args and isinstance(args[0], dict):
                info = args[0]
                TASKS[task_id]["percent"] = info.get("percent", 0)
                TASKS[task_id]["status"] = info.get("message", "Processing...")
                TASKS[task_id]["speed"] = info.get("speed", "0 p/s")
                TASKS[task_id]["eta"] = info.get("eta", "Calculating...")
                TASKS[task_id]["words"] = info.get("words", 0)
                log_msg = f"[{time.strftime('%H:%M:%S')}] {info.get('message', '')} ({info.get('speed', '')})"
                TASKS[task_id]["logs"].append(log_msg)
            elif len(args) >= 3:
                cur, tot, msg = args[0], args[1], args[2]
                pct = int((cur / max(1, tot)) * 100) if tot else int(cur)
                TASKS[task_id]["percent"] = pct
                TASKS[task_id]["status"] = str(msg)
                TASKS[task_id]["logs"].append(f"[{time.strftime('%H:%M:%S')}] {msg}")
            elif args:
                TASKS[task_id]["percent"] = int(args[0])
            if len(TASKS[task_id]["logs"]) > 50:
                TASKS[task_id]["logs"].pop(0)

        def is_cancelled():
            return task_id in CANCELLED_TASKS

        page_range = None
        if page_range_str and "-" in page_range_str:
            parts = page_range_str.split("-")
            try:
                page_range = (int(parts[0]) - 1, int(parts[1]))
            except Exception:
                page_range = None

        if ext == ".pdf":
            out_filename = f"{p.stem}_translated_{target_lang}.pdf"
            out_path = str(OUTPUT_DIR / out_filename)
            worker_pdf_engine.translate_pdf(
                input_pdf_path=file_path,
                output_pdf_path=out_path,
                source_lang=source_lang,
                target_lang=target_lang,
                translate_images=translate_images,
                page_range=page_range,
                progress_callback=progress_cb,
                cancel_check=is_cancelled
            )
        elif ext == ".fb2":
            out_filename = f"{p.stem}_translated_{target_lang}.fb2"
            out_path = str(OUTPUT_DIR / out_filename)
            worker_fb2_engine.translate_fb2(
                input_fb2_path=file_path,
                output_fb2_path=out_path,
                source_lang=source_lang,
                target_lang=target_lang,
                translate_images=translate_images,
                progress_callback=lambda cur, tot, msg: progress_cb({
                    "percent": int((cur/max(1,tot))*100),
                    "message": msg,
                    "speed": "Fast",
                    "eta": "Processing..."
                }),
                cancel_check=is_cancelled
            )
        elif ext in (".png", ".jpg", ".jpeg"):
            out_filename = f"{p.stem}_translated_{target_lang}{ext}"
            out_path = str(OUTPUT_DIR / out_filename)
            with open(file_path, "rb") as f_in:
                mod_bytes, _, _ = worker_image_translator.translate_image(
                    f_in.read(),
                    source_lang=source_lang,
                    target_lang=target_lang
                )
            with open(out_path, "wb") as f_out:
                f_out.write(mod_bytes)
        else:
            raise ValueError(f"Unsupported format: {ext}")

        if is_cancelled():
            TASKS[task_id]["status"] = "Translation cancelled by user"
            TASKS[task_id]["error"] = "Cancelled"
        else:
            TASKS[task_id]["done"] = True
            TASKS[task_id]["percent"] = 100
            TASKS[task_id]["status"] = "Translation complete!"
            TASKS[task_id]["filename"] = out_filename
            TASKS[task_id]["output_path"] = out_path

    except Exception as e:
        TASKS[task_id]["error"] = str(e)
        TASKS[task_id]["status"] = f"Error: {e}"

@app.post("/api/cancel-task/{task_id}")
async def cancel_task(task_id: str):
    CANCELLED_TASKS.add(task_id)
    if task_id in TASKS:
        TASKS[task_id]["status"] = "Cancelling..."
    return {"success": True, "message": f"Task {task_id} cancellation requested"}


@app.get("/", response_class=HTMLResponse)
async def serve_index(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

@app.post("/api/start-translation")
async def start_translation(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    source_lang: str = Form("auto"),
    target_lang: str = Form("en"),
    translate_images: bool = Form(True),
    page_range: str = Form(""),
    engine_mode: str = Form("hybrid")
):
    task_id = str(uuid.uuid4())
    upload_path = UPLOAD_DIR / f"{task_id}_{file.filename}"
    
    with open(upload_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    TASKS[task_id] = {
        "status": "Queued for processing...",
        "percent": 0,
        "done": False,
        "error": None,
        "filename": None,
        "output_path": None,
        "logs": [f"[{time.strftime('%H:%M:%S')}] Uploaded {file.filename}"]
    }

    background_tasks.add_task(
        run_translation_worker,
        task_id=task_id,
        file_path=str(upload_path),
        source_lang=source_lang,
        target_lang=target_lang,
        translate_images=translate_images,
        page_range_str=page_range,
        engine_mode=engine_mode
    )

    return {"task_id": task_id, "filename": file.filename}

@app.get("/api/progress/{task_id}")
async def get_progress(task_id: str):
    task = TASKS.get(task_id)
    if not task:
        return JSONResponse({"error": "Task not found"}, status_code=404)
    return task

@app.post("/api/translate-diagram")
async def translate_diagram_studio(
    file: UploadFile = File(...),
    source_lang: str = Form("auto"),
    target_lang: str = Form("en")
):
    """Interactive Image & Diagram OCR Studio endpoint."""
    img_bytes = await file.read()
    mod_bytes, was_mod, logs = image_translator.translate_image(
        img_bytes,
        source_lang=source_lang,
        target_lang=target_lang,
        output_format="PNG"
    )

    orig_b64 = "data:image/png;base64," + base64.b64encode(img_bytes).decode("ascii")
    trans_b64 = "data:image/png;base64," + base64.b64encode(mod_bytes).decode("ascii")

    return {
        "original_image": orig_b64,
        "translated_image": trans_b64,
        "was_modified": was_mod,
        "detections": logs,
        "count": len(logs)
    }

class ScanFolderRequest(BaseModel):
    folder_path: str
    recursive: bool = True

@app.post("/api/scan-folder")
async def scan_folder(req: ScanFolderRequest):
    """Scans local folder on disk (including subfolders if recursive) and returns list of PDF and FB2 files."""
    folder = Path(req.folder_path)
    if not folder.exists() or not folder.is_dir():
        raise HTTPException(status_code=400, detail="Directory not found")

    results = []
    items = folder.rglob("*") if req.recursive else folder.iterdir()
    for item in sorted(items, key=lambda x: x.name.lower()):
        if item.is_file() and item.suffix.lower() in (".pdf", ".fb2"):
            size_mb = item.stat().st_size / (1024 * 1024)
            size_str = f"{size_mb:.2f} MB" if size_mb >= 1 else f"{item.stat().st_size / 1024:.1f} KB"
            pages = 0
            if item.suffix.lower() == ".pdf":
                try:
                    d = fitz.open(str(item))
                    pages = len(d)
                    d.close()
                except Exception:
                    pages = 0

            # Check if translated version already exists in output directory
            out_pdf = OUTPUT_DIR / f"{item.stem}_translated_en.pdf"
            out_fb2 = OUTPUT_DIR / f"{item.stem}_translated_en.fb2"
            already_done = out_pdf.exists() or out_fb2.exists() or any(
                item.stem in p.name and "translated" in p.name and p.suffix.lower() == item.suffix.lower()
                for p in OUTPUT_DIR.glob(f"*{item.stem}*")
            )

            # Relative path to keep display clean
            rel_path = str(item.relative_to(folder)) if req.recursive else item.name

            results.append({
                "name": item.name,
                "display_name": rel_path,
                "path": str(item.resolve()),
                "ext": item.suffix.lower(),
                "size_str": size_str,
                "pages": pages,
                "already_done": already_done
            })

    return {"files": results, "folder": str(folder.resolve()), "count": len(results)}

class BatchRequest(BaseModel):
    files: List[str]
    source_lang: str = "auto"
    target_lang: str = "en"
    translate_images: bool = True
    engine_mode: str = "hybrid"
    skip_existing: bool = True

def run_batch_worker(
    batch_id: str,
    file_paths: List[str],
    src_lang: str,
    tgt_lang: str,
    trans_img: bool,
    engine_mode: str = "hybrid",
    skip_existing: bool = True
):
    import gc
    total = len(file_paths)
    BATCH_TASKS[batch_id]["total"] = total
    
    # Initialize dedicated worker engines with requested engine_mode
    worker_translator = TranslatorEngine(cache=cache_mgr, mode=engine_mode)
    worker_image_translator = ImageTranslator(translator=worker_translator)
    worker_pdf_engine = PDFEngine(translator=worker_translator, image_translator=worker_image_translator)
    worker_fb2_engine = FB2Engine(translator=worker_translator, image_translator=worker_image_translator)

    for idx, f_path in enumerate(file_paths):
        p = Path(f_path)
        BATCH_TASKS[batch_id]["current_index"] = idx + 1
        BATCH_TASKS[batch_id]["current_file"] = p.name
        BATCH_TASKS[batch_id]["percent"] = int(((idx) / max(1, total)) * 100)
        BATCH_TASKS[batch_id]["status"] = f"Translating [{idx+1}/{total}] {p.name}..."

        # Update per-item status if present
        if "items" in BATCH_TASKS[batch_id] and idx < len(BATCH_TASKS[batch_id]["items"]):
            BATCH_TASKS[batch_id]["items"][idx]["status"] = "converting"

        ext = p.suffix.lower()
        clean_stem = p.stem
        # Strip internal task prefix if present (e.g. 8-char hex or uuid)
        if "_" in clean_stem and len(clean_stem.split("_")[0]) in (8, 36):
            clean_stem = "_".join(clean_stem.split("_")[1:])
        out_filename = f"{clean_stem}_translated_{tgt_lang}{ext}"
        out_path = OUTPUT_DIR / out_filename

        # Skip if already translated
        if skip_existing and out_path.exists() and out_path.stat().st_size > 1024:
            BATCH_TASKS[batch_id]["completed_files"].append(f"{p.name} (Skipped - already translated)")
            BATCH_TASKS[batch_id]["percent"] = int(((idx + 1) / max(1, total)) * 100)
            if "items" in BATCH_TASKS[batch_id] and idx < len(BATCH_TASKS[batch_id]["items"]):
                BATCH_TASKS[batch_id]["items"][idx]["status"] = "done"
                BATCH_TASKS[batch_id]["items"][idx]["percent"] = 100
                BATCH_TASKS[batch_id]["items"][idx]["out_filename"] = out_filename
            continue

        def sub_progress(*args, **kwargs):
            sub_pct = 0
            sub_speed = ""
            sub_eta = ""
            msg = ""
            if args:
                if isinstance(args[0], dict):
                    info = args[0]
                    sub_pct = info.get("percent", 0)
                    sub_speed = info.get("speed", "")
                    sub_eta = info.get("eta", "")
                    msg = info.get("message", "")
                elif len(args) >= 3:
                    cur, tot, m = args[0], args[1], args[2]
                    sub_pct = int((cur / max(1, tot)) * 100) if tot else int(cur)
                    msg = str(m)
                elif len(args) == 2:
                    cur, tot = args[0], args[1]
                    sub_pct = int((cur / max(1, tot)) * 100) if tot else int(cur)
                elif isinstance(args[0], (int, float)):
                    sub_pct = int(args[0])
            elif "percent" in kwargs:
                sub_pct = kwargs.get("percent", 0)
                msg = kwargs.get("message", "")

            BATCH_TASKS[batch_id]["current_sub_progress"] = sub_pct
            status_text = f"[{idx+1}/{total}] {p.name}: {sub_pct}%"
            if sub_speed:
                status_text += f" ({sub_speed}"
                if sub_eta:
                    status_text += f", ETA {sub_eta}"
                status_text += ")"
            elif msg:
                status_text += f" - {msg}"
            BATCH_TASKS[batch_id]["status"] = status_text
            if "items" in BATCH_TASKS[batch_id] and idx < len(BATCH_TASKS[batch_id]["items"]):
                BATCH_TASKS[batch_id]["items"][idx]["percent"] = sub_pct

        try:
            if ext == ".pdf":
                worker_pdf_engine.translate_pdf(
                    input_pdf_path=str(p),
                    output_pdf_path=str(out_path),
                    source_lang=src_lang,
                    target_lang=tgt_lang,
                    translate_images=trans_img,
                    progress_callback=sub_progress
                )
            elif ext == ".fb2":
                worker_fb2_engine.translate_fb2(
                    input_fb2_path=str(p),
                    output_fb2_path=str(out_path),
                    source_lang=src_lang,
                    target_lang=tgt_lang,
                    translate_images=trans_img,
                    progress_callback=sub_progress
                )
            BATCH_TASKS[batch_id]["completed_files"].append(p.name)
            if "items" in BATCH_TASKS[batch_id] and idx < len(BATCH_TASKS[batch_id]["items"]):
                BATCH_TASKS[batch_id]["items"][idx]["status"] = "done"
                BATCH_TASKS[batch_id]["items"][idx]["percent"] = 100
                BATCH_TASKS[batch_id]["items"][idx]["out_filename"] = out_filename
        except Exception as e:
            BATCH_TASKS[batch_id]["errors"].append(f"{p.name}: {e}")
            if "items" in BATCH_TASKS[batch_id] and idx < len(BATCH_TASKS[batch_id]["items"]):
                BATCH_TASKS[batch_id]["items"][idx]["status"] = "error"
                BATCH_TASKS[batch_id]["items"][idx]["error"] = str(e)
        finally:
            gc.collect()

    BATCH_TASKS[batch_id]["percent"] = 100
    BATCH_TASKS[batch_id]["done"] = True
    BATCH_TASKS[batch_id]["status"] = f"Batch finished! Successfully processed {len(BATCH_TASKS[batch_id]['completed_files'])} books into {OUTPUT_DIR}."

@app.post("/api/start-batch-upload")
async def start_batch_upload(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    source_lang: str = Form("auto"),
    target_lang: str = Form("en"),
    translate_images: bool = Form(False),
    engine_mode: str = Form("hybrid"),
    skip_existing: bool = Form(False)
):
    """Handles multi-book uploads (10+ books or folder contents) and automatically queues them."""
    batch_id = str(uuid.uuid4())
    saved_paths = []
    items_meta = []

    for f in files:
        fname = Path(f.filename).name
        ext = Path(fname).suffix.lower()
        if ext not in (".pdf", ".fb2"):
            continue

        save_name = f"{uuid.uuid4().hex[:8]}_{fname}"
        save_dest = UPLOAD_DIR / save_name
        with open(save_dest, "wb") as buffer:
            shutil.copyfileobj(f.file, buffer)

        size_b = save_dest.stat().st_size
        size_str = f"{size_b / (1024*1024):.2f} MB" if size_b >= 1024*1024 else f"{size_b / 1024:.1f} KB"

        saved_paths.append(str(save_dest))
        items_meta.append({
            "name": fname,
            "ext": ext.lstrip("."),
            "size_str": size_str,
            "status": "pending",
            "percent": 0,
            "out_filename": None,
            "error": None
        })

    if not saved_paths:
        raise HTTPException(status_code=400, detail="No valid .pdf or .fb2 books were uploaded.")

    BATCH_TASKS[batch_id] = {
        "batch_id": batch_id,
        "total": len(saved_paths),
        "current_index": 0,
        "current_file": "",
        "current_sub_progress": 0,
        "percent": 0,
        "done": False,
        "status": f"Queue ready with {len(saved_paths)} books. Converting sequentially...",
        "items": items_meta,
        "completed_files": [],
        "errors": []
    }

    background_tasks.add_task(
        run_batch_worker,
        batch_id=batch_id,
        file_paths=saved_paths,
        src_lang=source_lang,
        tgt_lang=target_lang,
        trans_img=translate_images,
        engine_mode=engine_mode,
        skip_existing=skip_existing
    )

    return {"batch_id": batch_id, "count": len(saved_paths)}

@app.post("/api/start-batch")
async def start_batch(req: BatchRequest, background_tasks: BackgroundTasks):
    batch_id = str(uuid.uuid4())
    items_meta = []
    for fp in req.files:
        p = Path(fp)
        items_meta.append({
            "name": p.name,
            "ext": p.suffix.lower().lstrip("."),
            "size_str": "",
            "status": "pending",
            "percent": 0,
            "out_filename": None,
            "error": None
        })
    BATCH_TASKS[batch_id] = {
        "batch_id": batch_id,
        "total": len(req.files),
        "current_index": 0,
        "current_file": "",
        "current_sub_progress": 0,
        "percent": 0,
        "done": False,
        "status": "Starting batch...",
        "items": items_meta,
        "completed_files": [],
        "errors": []
    }
    background_tasks.add_task(
        run_batch_worker,
        batch_id=batch_id,
        file_paths=req.files,
        src_lang=req.source_lang,
        tgt_lang=req.target_lang,
        trans_img=req.translate_images,
        engine_mode=req.engine_mode,
        skip_existing=req.skip_existing
    )
    return {"batch_id": batch_id}

@app.get("/api/batch-progress/{batch_id}")
async def get_batch_progress(batch_id: str):
    info = BATCH_TASKS.get(batch_id)
    if not info:
        return JSONResponse({"error": "Batch task not found"}, status_code=404)
    return info

@app.get("/api/preview/{filename}")
async def preview_pdf(filename: str):
    """Streams PDF directly into browser iframe / viewer."""
    file_path = OUTPUT_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(
        path=str(file_path),
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename={filename}"}
    )

@app.get("/api/download/{filename}")
async def download_file(filename: str):
    file_path = OUTPUT_DIR / filename
    if not file_path.exists():
        return JSONResponse({"error": "File not found"}, status_code=404)
    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type="application/octet-stream"
    )

@app.delete("/api/delete-file/{filename}")
async def delete_file(filename: str):
    file_path = OUTPUT_DIR / filename
    if file_path.exists() and file_path.is_file():
        file_path.unlink()
        return {"success": True, "message": f"Deleted {filename}"}
    return JSONResponse({"error": "File not found"}, status_code=404)

@app.get("/api/history")
async def get_history():
    files = []
    if OUTPUT_DIR.exists():
        for p in OUTPUT_DIR.glob("*.*"):
            if p.is_file() and p.suffix.lower() in (".pdf", ".fb2", ".png", ".jpg"):
                st = p.stat()
                size_mb = st.st_size / (1024 * 1024)
                size_str = f"{size_mb:.2f} MB" if size_mb >= 1 else f"{st.st_size / 1024:.1f} KB"
                files.append({
                    "name": p.name,
                    "ext": p.suffix.lower().lstrip("."),
                    "size_str": size_str,
                    "mtime": st.st_mtime,
                    "time_str": time.strftime("%Y-%m-%d %H:%M", time.localtime(st.st_mtime))
                })
    files.sort(key=lambda x: x["mtime"], reverse=True)
    return files

@app.get("/api/cache-info")
async def get_cache_info():
    count = cache_mgr.get_count()
    size_kb = 0
    if CACHE_DB_PATH.exists():
        size_kb = CACHE_DB_PATH.stat().st_size / 1024
    return {"count": count, "size_kb": f"{size_kb:.1f} KB"}

@app.post("/api/clear-cache")
async def clear_cache_endpoint():
    cache_mgr.clear()
    return {"success": True, "message": "Translation cache cleared successfully"}

if __name__ == "__main__":
    import uvicorn
    print("\nStarting DocTrans Master Web UI at: http://127.0.0.1:8000\n")
    uvicorn.run("web_app:app", host="127.0.0.1", port=8000, reload=False)
