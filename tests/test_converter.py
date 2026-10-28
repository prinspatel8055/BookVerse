import os
import sys
import unittest
from pathlib import Path
from PIL import Image, ImageDraw

# Ensure project root is in path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.cache_manager import TranslationCache
from core.translator import TranslatorEngine
from core.ocr_engine import OCREngine
from core.image_translator import ImageTranslator
from core.pdf_engine import PDFEngine
from core.fb2_engine import FB2Engine

class TestDocConverter(unittest.TestCase):

    def setUp(self):
        self.cache = TranslationCache()
        self.translator = TranslatorEngine(cache=self.cache)

    def test_01_cache_operations(self):
        text = "Тестовый текст для проверки кэша"
        trans = "Test text for cache checking"
        self.cache.set(text, trans, "ru", "en")
        fetched = self.cache.get(text, "ru", "en")
        self.assertEqual(fetched, trans)

    def test_02_translator_engine(self):
        original = "Глава 1. Введение"
        translated = self.translator.translate_single(original, source_lang="ru", target_lang="en")
        self.assertIn("Chapter", translated)

        # Batch translation
        items = ["Атака на переполнение буфера", "Shellcode исполнение"]
        results = self.translator.translate_batch(items, source_lang="ru", target_lang="en")
        self.assertEqual(len(results), 2)
        self.assertTrue(len(results[0]) > 0)

    def test_03_synthetic_image_translation(self):
        # Create a synthetic image with Russian text
        img = Image.new("RGB", (300, 100), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        # Draw some high contrast box and text
        draw.rectangle([10, 10, 290, 90], outline=(0, 0, 0), width=2)
        # Use simple text
        draw.text((30, 40), "Status: OK", fill=(0, 0, 0))

        img_trans = ImageTranslator(translator=self.translator)
        import io
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        
        mod_bytes, was_mod, logs = img_trans.translate_image(buf.getvalue(), target_lang="en")
        self.assertTrue(len(mod_bytes) > 0)

    def test_04_sample_pdf_translation(self):
        import fitz
        sample_src = Path(r"d:\Python books tech\hacking_books_ru-main\hacking_books_ru-main\exploits\Gray_Hat_Python_RU.pdf")
        test_pdf_path = Path(__file__).resolve().parent / "temp_test_input.pdf"
        out_pdf_path = Path(__file__).resolve().parent / "temp_test_output.pdf"

        if sample_src.exists():
            doc = fitz.open(str(sample_src))
            test_doc = fitz.open()
            test_doc.insert_pdf(doc, from_page=0, to_page=0)
            test_doc.save(str(test_pdf_path))
            test_doc.close()
            doc.close()
        else:
            doc = fitz.open()
            page = doc.new_page()
            page.insert_font(fontname="f0", fontfile=r"C:\Windows\Fonts\arial.ttf")
            page.insert_textbox(fitz.Rect(50, 50, 400, 150), "Глава 1. Введение", fontname="f0", fontsize=12)
            doc.save(str(test_pdf_path))
            doc.close()

        pdf_engine = PDFEngine(translator=self.translator)
        pdf_engine.translate_pdf(
            input_pdf_path=str(test_pdf_path),
            output_pdf_path=str(out_pdf_path),
            source_lang="ru",
            target_lang="en",
            translate_images=False
        )

        self.assertTrue(out_pdf_path.exists())
        res_doc = fitz.open(str(out_pdf_path))
        text = res_doc[0].get_text().lower()
        res_doc.close()

        if test_pdf_path.exists(): test_pdf_path.unlink()
        if out_pdf_path.exists(): out_pdf_path.unlink()

        self.assertTrue("python" in text or "chapter" in text or "introduction" in text)

if __name__ == "__main__":
    unittest.main()
