"""
DRAVION v.9 — Perception Engine (VOLT)

Eyes of the system. Handles:
  - Screenshot capture + OCR
  - Webcam capture
  - Gemini multimodal image analysis
  - Future: remote camera sources (phone, glasses, watch via Tailscale)
"""
import os
import io
import base64
import asyncio
import tempfile
from datetime import datetime
from enum import Enum
from core.logger import log

class CameraSource(Enum):
    """Extensible camera source registry. Add new devices here."""
    SCREEN = "screen"
    WEBCAM = "webcam"
    # Future sources:
    # PHONE = "phone"        # via Tailscale + companion app
    # GLASSES = "glasses"    # via Tailscale + AR stream
    # WATCH = "watch"        # via Tailscale + WearOS
    # FRIGATE = "frigate"    # via RTSP stream


class PerceptionEngine:
    """
    Central vision hub. All image capture goes through here.
    Designed so new camera sources just need a _capture_<source> method.
    """

    def __init__(self):
        self._last_capture = None  # Cache last captured image bytes
        self._last_source = None
        log.info("perception_engine_ready")

    # ─── Capture Dispatch ───

    def capture(self, source: str = "screen") -> dict:
        """
        Capture from any registered source.
        Returns: {"image_b64": str, "source": str, "timestamp": str} or {"error": str}
        """
        source = source.lower().strip()
        method = getattr(self, f"_capture_{source}", None)
        if not method:
            return {"error": f"Unknown camera source: '{source}'. Available: screen, webcam"}

        try:
            img_bytes = method()
            if img_bytes is None:
                return {"error": f"Capture from {source} returned nothing."}

            b64 = base64.b64encode(img_bytes).decode("utf-8")
            self._last_capture = img_bytes
            self._last_source = source
            return {
                "image_b64": b64,
                "source": source,
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            log.error("capture_failed", source=source, error=str(e))
            return {"error": f"Capture failed ({source}): {e}"}

    # ─── Screenshot ───

    def _capture_screen(self) -> bytes:
        import pyautogui
        img = pyautogui.screenshot()
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    # ─── Webcam ───

    def _capture_webcam(self) -> bytes:
        import cv2
        import time
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if not cap.isOpened():
            raise RuntimeError("No webcam found. Check if camera is connected.")

        # Let camera warm up — needs time to adjust exposure/white balance
        time.sleep(0.5)
        for _ in range(15):
            cap.read()

        ret, frame = cap.read()
        cap.release()

        if not ret or frame is None:
            raise RuntimeError("Failed to grab frame from webcam.")

        # Check if frame is mostly black (failed capture)
        if frame.mean() < 5:
            raise RuntimeError("Webcam returned a black frame — camera may be blocked or initializing.")

        _, buf = cv2.imencode('.png', frame)
        return buf.tobytes()

    # ─── OCR ───

    def ocr_from_bytes(self, img_bytes: bytes) -> str:
        """Extract text from image bytes using Tesseract."""
        try:
            import pytesseract
            from PIL import Image

            img = Image.open(io.BytesIO(img_bytes))
            text = pytesseract.image_to_string(img).strip()
            return text if text else "No text detected in the image."
        except ImportError:
            return "OCR unavailable — pytesseract not installed."
        except Exception as e:
            return f"OCR failed: {e}"

    def ocr_screen(self) -> str:
        """Capture screen and run OCR."""
        result = self.capture("screen")
        if "error" in result:
            return result["error"]
        return self.ocr_from_bytes(self._last_capture)

    # ─── Gemini Vision Analysis ───

    async def analyze_image(self, img_bytes: bytes, prompt: str = "Describe what you see in this image.") -> str:
        """Send image to Gemini 2.5 Flash for multimodal analysis."""
        try:
            from openai import AsyncOpenAI
            from core.config import config

            client = AsyncOpenAI(
                base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
                api_key=config.gemini_api_key or config.google_api_key,
            )

            b64 = base64.b64encode(img_bytes).decode("utf-8")

            response = await client.chat.completions.create(
                model="gemini-2.5-flash-lite",
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
                    ],
                }],
                max_tokens=1024,
            )
            return response.choices[0].message.content
        except Exception as e:
            log.error("vision_analysis_failed", error=str(e))
            return f"Vision analysis failed: {e}"

    async def analyze_screen(self, prompt: str = "Describe what's on this screen in detail.") -> str:
        """Capture screen → Gemini analysis."""
        result = self.capture("screen")
        if "error" in result:
            return result["error"]
        return await self.analyze_image(self._last_capture, prompt)

    async def analyze_webcam(self, prompt: str = "Describe what you see from this camera.") -> str:
        """Capture webcam → Gemini analysis."""
        result = self.capture("webcam")
        if "error" in result:
            return result["error"]
        return await self.analyze_image(self._last_capture, prompt)

    # ─── Save last capture ───

    def save_last_capture(self, path: str = None) -> str:
        """Save the last captured image to disk."""
        if not self._last_capture:
            return "No image captured yet."
        if not path:
            desktop = os.path.join(os.path.expanduser("~"), "Desktop")
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = os.path.join(desktop, f"dravion_capture_{ts}.png")
        with open(path, "wb") as f:
            f.write(self._last_capture)
        return f"Saved to {path}"


# Singleton
perception = PerceptionEngine()
