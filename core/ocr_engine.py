import io
import numpy as np
from PIL import Image
import easyocr
from typing import List, Tuple, Dict, Any, Union
from core.config import (
    EASYOCR_LANG_MAP,
    OCR_CONFIDENCE_THRESHOLD,
    MIN_IMAGE_WIDTH,
    MIN_IMAGE_HEIGHT
)

class OCREngine:
    """
    Lazy-loading, thread-safe OCR Engine powered by EasyOCR.
    Supports detecting text bounding boxes, detected language characters, and confidence filtering.
    """

    _readers: Dict[str, easyocr.Reader] = {}

    def __init__(self, languages: Union[List[str], str] = "auto", gpu: bool = False):
        if isinstance(languages, str):
            self.lang_codes = EASYOCR_LANG_MAP.get(languages.lower(), ["ru", "en"])
        else:
            self.lang_codes = languages
        self.gpu = gpu
        self.lang_key = "_".join(sorted(self.lang_codes))

    def _get_reader(self) -> easyocr.Reader:
        if self.lang_key not in self._readers:
            self._readers[self.lang_key] = easyocr.Reader(self.lang_codes, gpu=self.gpu)
        return self._readers[self.lang_key]

    def is_worth_ocr(self, img: Image.Image) -> bool:
        """Determines if the image is large and complex enough to contain text."""
        w, h = img.size
        if w < MIN_IMAGE_WIDTH or h < MIN_IMAGE_HEIGHT:
            return False
        # Skip pure 1-pixel color lines or extreme aspect ratios
        aspect = max(w / h, h / w)
        if aspect > 25:
            return False
        return True

    def detect_text(self, image_input: Union[bytes, Image.Image, np.ndarray]) -> List[Dict[str, Any]]:
        """
        Detects text bounding boxes in an image.
        Returns list of dicts:
        [
            {
                'bbox': (x0, y0, x1, y1),
                'polygon': [[x,y], [x,y], [x,y], [x,y]],
                'text': 'Detected Text',
                'confidence': 0.85
            },
            ...
        ]
        """
        if isinstance(image_input, bytes):
            pil_img = Image.open(io.BytesIO(image_input)).convert("RGB")
        elif isinstance(image_input, Image.Image):
            pil_img = image_input.convert("RGB")
        elif isinstance(image_input, np.ndarray):
            pil_img = Image.fromarray(image_input).convert("RGB")
        else:
            raise ValueError(f"Unsupported image input type: {type(image_input)}")

        if not self.is_worth_ocr(pil_img):
            return []

        np_img = np.array(pil_img)
        reader = self._get_reader()

        try:
            raw_results = reader.readtext(np_img)
        except Exception:
            return []

        results = []
        for bbox, text, conf in raw_results:
            clean_text = text.strip()
            if conf < OCR_CONFIDENCE_THRESHOLD or not clean_text:
                continue

            xs = [pt[0] for pt in bbox]
            ys = [pt[1] for pt in bbox]
            x0, y0, x1, y1 = int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys))

            # Boundary clamps
            x0 = max(0, x0)
            y0 = max(0, y0)
            x1 = min(pil_img.width, x1)
            y1 = min(pil_img.height, y1)

            if (x1 - x0) <= 4 or (y1 - y0) <= 4:
                continue

            results.append({
                "bbox": (x0, y0, x1, y1),
                "polygon": bbox,
                "text": clean_text,
                "confidence": float(conf)
            })

        return results
