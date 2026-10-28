import io
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from typing import Tuple, List, Dict, Any, Optional, Union
from core.config import (
    DEFAULT_FONT_PATH,
    IMAGE_INPAINT_PADDING,
    MIN_IMAGE_WIDTH,
    MIN_IMAGE_HEIGHT
)
from core.ocr_engine import OCREngine
from core.translator import TranslatorEngine

class ImageTranslator:
    """
    Optimized Image OCR & Diagram Inpainting:
    - Fast heuristics to skip icons, separators, and non-diagram images
    - Filters out English debugger screenshots & memory addresses
    - Clean background sampling and high-contrast inpainting
    """

    def __init__(
        self,
        translator: Optional[TranslatorEngine] = None,
        ocr_engine: Optional[OCREngine] = None,
        font_path: Optional[str] = None
    ):
        self.translator = translator or TranslatorEngine()
        self.ocr_engine = ocr_engine or OCREngine()
        self.font_path = font_path or DEFAULT_FONT_PATH

    @staticmethod
    def is_diagram_candidate(img: Image.Image) -> bool:
        """Checks if image is an actual diagram/chart that may contain foreign text."""
        w, h = img.size
        # Must be large enough to be an illustration / diagram
        if w < 120 or h < 80:
            return False
        # Skip banners / dividers
        if (w / h > 9) or (h / w > 9):
            return False
        return True

    @staticmethod
    def _sample_background_color(np_img: np.ndarray, x0: int, y0: int, x1: int, y1: int) -> Tuple[int, int, int]:
        h, w = np_img.shape[:2]
        border_pixels = []
        if y0 > 0: border_pixels.extend(np_img[y0 - 1, x0:x1])
        if y1 < h - 1: border_pixels.extend(np_img[y1, x0:x1])
        if x0 > 0: border_pixels.extend(np_img[y0:y1, x0 - 1])
        if x1 < w - 1: border_pixels.extend(np_img[y0:y1, x1])

        if len(border_pixels) > 0:
            median_color = np.median(border_pixels, axis=0).astype(int)
            return int(median_color[0]), int(median_color[1]), int(median_color[2])
        return (255, 255, 255)

    @staticmethod
    def _get_contrasting_text_color(bg_color: Tuple[int, int, int]) -> Tuple[int, int, int]:
        luminance = 0.299 * bg_color[0] + 0.587 * bg_color[1] + 0.114 * bg_color[2]
        return (0, 0, 0) if luminance > 128 else (255, 255, 255)

    def _get_fitted_font(self, text: str, max_width: int, max_height: int) -> ImageFont.FreeTypeFont:
        if not self.font_path or not os.path.exists(self.font_path):
            return ImageFont.load_default()

        initial_size = max(7, int(max_height * 0.75))
        for size in range(initial_size, 6, -1):
            try:
                font = ImageFont.truetype(self.font_path, size)
                bbox = font.getbbox(text)
                if (bbox[2] - bbox[0]) <= max_width and (bbox[3] - bbox[1]) <= max_height:
                    return font
            except Exception:
                break
        try:
            return ImageFont.truetype(self.font_path, 7)
        except Exception:
            return ImageFont.load_default()

    def translate_image(
        self,
        image_input: Union[bytes, Image.Image],
        source_lang: str = "auto",
        target_lang: str = "en",
        output_format: str = "PNG"
    ) -> Tuple[bytes, bool, List[Dict[str, Any]]]:
        if isinstance(image_input, bytes):
            orig_pil = Image.open(io.BytesIO(image_input)).convert("RGB")
        elif isinstance(image_input, Image.Image):
            orig_pil = image_input.convert("RGB")
        else:
            raise ValueError(f"Unsupported image input type: {type(image_input)}")

        # Heuristic: skip non-diagram images
        if not self.is_diagram_candidate(orig_pil):
            out_buf = io.BytesIO()
            orig_pil.save(out_buf, format=output_format)
            return out_buf.getvalue(), False, []

        detections = self.ocr_engine.detect_text(orig_pil)
        if not detections:
            out_buf = io.BytesIO()
            orig_pil.save(out_buf, format=output_format)
            return out_buf.getvalue(), False, []

        # Filter out text that is already English / code / hex
        foreign_detections = []
        for d in detections:
            txt = d["text"]
            if not self.translator.is_technical_code_or_ascii(txt, target_lang):
                foreign_detections.append(d)

        if not foreign_detections:
            out_buf = io.BytesIO()
            orig_pil.save(out_buf, format=output_format)
            return out_buf.getvalue(), False, []

        raw_texts = [d["text"] for d in foreign_detections]
        translated_texts = self.translator.translate_batch(raw_texts, source_lang=source_lang, target_lang=target_lang)

        mod_pil = orig_pil.copy()
        draw = ImageDraw.Draw(mod_pil)
        np_img = np.array(orig_pil)
        w, h = orig_pil.size

        modified_count = 0
        translation_logs = []

        for det, trans_text in zip(foreign_detections, translated_texts):
            orig_text = det["text"]
            x0, y0, x1, y1 = det["bbox"]

            if not trans_text or trans_text.strip() == orig_text.strip():
                continue

            px0 = max(0, x0 - IMAGE_INPAINT_PADDING)
            py0 = max(0, y0 - IMAGE_INPAINT_PADDING)
            px1 = min(w, x1 + IMAGE_INPAINT_PADDING)
            py1 = min(h, y1 + IMAGE_INPAINT_PADDING)

            box_w = px1 - px0
            box_h = py1 - py0
            if box_w <= 4 or box_h <= 4:
                continue

            bg_color = self._sample_background_color(np_img, px0, py0, px1, py1)
            text_color = self._get_contrasting_text_color(bg_color)

            draw.rectangle([px0, py0, px1, py1], fill=bg_color)
            font = self._get_fitted_font(trans_text, box_w, box_h)
            draw.text((px0 + 1, py0 + 1), trans_text, fill=text_color, font=font)
            modified_count += 1

            translation_logs.append({
                "original": orig_text,
                "translated": trans_text,
                "bbox": [px0, py0, px1, py1],
                "confidence": det["confidence"]
            })

        out_buf = io.BytesIO()
        mod_pil.save(out_buf, format=output_format)
        return out_buf.getvalue(), (modified_count > 0), translation_logs
