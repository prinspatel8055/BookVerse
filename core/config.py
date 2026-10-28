import os
from pathlib import Path

# Base Paths
BASE_DIR = Path(__file__).resolve().parent.parent
CACHE_DB_PATH = BASE_DIR / "translation_cache.db"
OUTPUT_DIR = Path(r"D:\Apnp\outputbook")
if not OUTPUT_DIR.parent.exists():
    OUTPUT_DIR = BASE_DIR.parent / "outputbook"
UPLOAD_DIR = BASE_DIR / "uploads"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Default Translation Settings
DEFAULT_SOURCE_LANG = "auto"
DEFAULT_TARGET_LANG = "en"

# Windows System Fonts
SYSTEM_FONT_CANDIDATES = [
    r"C:\Windows\Fonts\arial.ttf",
    r"C:\Windows\Fonts\segoeui.ttf",
    r"C:\Windows\Fonts\calibri.ttf",
    r"C:\Windows\Fonts\times.ttf"
]

DEFAULT_FONT_PATH = next((f for f in SYSTEM_FONT_CANDIDATES if os.path.exists(f)), None)

# Image OCR Settings
OCR_CONFIDENCE_THRESHOLD = 0.25
MIN_IMAGE_WIDTH = 40
MIN_IMAGE_HEIGHT = 40
IMAGE_INPAINT_PADDING = 3

# Language code mapping for EasyOCR & Translators
LANGUAGE_MAP = {
    "auto": "Auto-Detect",
    "en": "English",
    "ru": "Russian",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "zh": "Chinese (Simplified)",
    "ja": "Japanese",
    "ko": "Korean",
    "ar": "Arabic",
    "hi": "Hindi",
    "gu": "Gujarati",
    "it": "Italian",
    "pt": "Portuguese",
    "tr": "Turkish",
    "uk": "Ukrainian",
    "pl": "Polish",
    "nl": "Dutch",
}

# EasyOCR language code mapping
EASYOCR_LANG_MAP = {
    "ru": ["ru", "en"],
    "en": ["en"],
    "es": ["es", "en"],
    "fr": ["fr", "en"],
    "de": ["de", "en"],
    "zh": ["ch_sim", "en"],
    "ja": ["ja", "en"],
    "ko": ["ko", "en"],
    "ar": ["ar", "en"],
    "hi": ["hi", "en"],
    "it": ["it", "en"],
    "pt": ["pt", "en"],
    "uk": ["uk", "en"],
    "pl": ["pl", "en"],
    "nl": ["nl", "en"],
    "auto": ["ru", "en"]  # Default fallback if auto
}
