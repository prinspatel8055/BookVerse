# 📚 AI-Book-Translator

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![PyMuPDF](https://img.shields.io/badge/PyMuPDF-1.24%2B-orange.svg)](https://pymupdf.readthedocs.io/)
[![EasyOCR](https://img.shields.io/badge/EasyOCR-1.7%2B-green.svg)](https://github.com/JaidedAI/EasyOCR)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> **High-performance AI-powered batch book translator for PDF & FB2 documents. Translates 500+ page books while maintaining 100% layout fidelity, font hierarchy, and technical diagram illustrations.**

---

## 🌟 Key Features

### 1. 📐 True Layout & Typography Preservation
* **Semantic Block Merging:** Intelligently detects and merges multi-line titles, chapter headers, and split paragraphs into unified coherent blocks.
* **Exact Font Hierarchy:** Accurately retains original font sizes (24pt titles, 14-16pt headings, 10pt body text), font weights (**Bold**, *Italic*), colors, and center/left alignments.
* **Anti-Truncation Geometry:** Automatically expands bounding boxes into available vertical whitespace so translated sentences never overflow, clip, or get truncated.
* **Clean Vector Redaction:** Erases original foreign language glyphs cleanly without painting destructive solid white boxes over background shading, colored callout boxes, or tables.
* **Unicode Normalization:** Strips broken non-breaking space artifacts (`\xa0`) and missing character glyphs for crisp rendering across all PDF readers.

### 2. 🛡️ 100% Zero-Leakage Translation & Code Safety
* **Zero Cyrillic Leakage:** Multi-tier verification pipeline guarantees that 100% of Russian text is translated into English.
* **Code & Syntax Filter:** Preserves programming code listings (Python, C, terminal commands, disassembly, hex addresses like `0x41414141`) in crisp original vector format with zero syntax distortion.

### 3. ⚡ Hybrid & 100% Offline AI Engines
* **Hybrid Mode (Recommended):** Ultra-fast bundled translation requests with a smart circuit breaker.
* **100% Offline AI Mode:** Powered by local neural models (ArgosTranslate / CTranslate2 OpenNMT). Completely immune to API rate limits, internet drops, or throttling — ideal for unlimited overnight conversion.
* **Persistent SQLite Cache:** 0ms instantaneous retrieval for repeated technical terms, abbreviations, and recurring paragraphs.

### 4. 🖼️ In-Diagram Image & Schema OCR Translation
* Scans diagrams, flowcharts, architectures, and screenshots using **EasyOCR**.
* Automatically detects text bounding boxes, in-paints local background colors, and renders translated labels in their exact spatial positions.

### 5. 🚀 Batch 500-Books Converter & Overnight Queue
* Drag-and-drop 10, 50, or 100+ books at once or select an entire library folder.
* Automated sequential queue ("વારાફરતી") converts books continuously through the night without crashing or memory leaks.
* Automatically saves translated outputs directly to your designated output directory.

### 6. 🎛️ Cyberpunk Telemetry HUD & Live Web App
* Sleek responsive Web UI built with **FastAPI** + Tailwind CSS.
* Real-time speedometer (pages/sec, pages/min), remaining ETA countdown, and live progress bars.
* Built-in e-book reader and instant file downloads.

---

## 📁 Project Architecture

```
AI-Book-Translator/
├── core/
│   ├── config.py             # System paths, language maps, OCR thresholds, and fonts
│   ├── cache_manager.py      # Thread-safe SQLite persistent translation cache
│   ├── translator.py         # Hybrid / Offline neural translation engine with circuit breaker
│   ├── ocr_engine.py         # EasyOCR wrapper with confidence thresholding
│   ├── image_translator.py   # Diagram OCR, local inpainting & text replacement
│   ├── pdf_engine.py         # High-precision typography & layout-preserving PDF engine
│   └── fb2_engine.py         # FictionBook 2.0 (FB2) XML DOM traversal & translation engine
├── templates/
│   └── index.html            # Cyberpunk HUD Web UI with batch queue & live telemetry
├── uploads/                  # Temporary upload staging folder
├── output/                   # Default translated books directory
├── web_app.py                # FastAPI web server & batch background worker
├── batch_runner.py           # CLI runner for headless batch automation
├── cli.py                    # Command-line interface for single document conversion
├── requirements.txt          # Python dependencies
└── README.md
```

---

## 🛠️ Installation & Setup

### Prerequisites
* **Python 3.10 or 3.11** (Recommended: 3.11.9)
* **Git** installed on your system

### 1. Clone the Repository
```bash
git clone https://github.com/prinspatel8055/AI-Book-Translator.git
cd AI-Book-Translator
```

### 2. Create a Virtual Environment (Optional but Recommended)
```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Install Offline Neural Translation Model (Optional for Offline Mode)
```bash
python -c "import argostranslate.package, argostranslate.translate; argostranslate.package.update_package_index(); available = argostranslate.package.get_available_packages(); pkg = next(p for p in available if p.from_code == 'ru' and p.to_code == 'en'); argostranslate.package.install_from_path(pkg.download())"
```

---

## 💻 Usage

### Option 1: Modern Web UI (Recommended)
Launch the interactive web application:
```bash
python web_app.py
```
Open your browser and navigate to:
```
http://127.0.0.1:8000
```
* Drag and drop single or multiple **PDF** / **FB2** books (or click **"Select Entire Folder"**).
* Choose your **AI Engine** (Hybrid or 100% Offline AI).
* Click **Start Turbo Translation** and watch live telemetry progress!

### Option 2: Command Line (CLI)
Translate a single book:
```bash
python cli.py input_book.pdf -s ru -t en --pages 1-20
```

Translate an entire folder:
```bash
python batch_runner.py "C:\path\to\books_folder" --engine hybrid
```

---

## 📄 License
This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

---

## 🤝 Contributing
Contributions, bug reports, and feature requests are welcome! Feel free to open an issue or submit a pull request.
