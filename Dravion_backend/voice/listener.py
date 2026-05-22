"""
DRAVION v.9 — Listener (Google Cloud STT)

Uses SpeechRecognition library with Google's free speech API.
Same engine as v2 — reliable, cloud-based, no local model needed.
"""
import speech_recognition as sr
from core.logger import log

# Sci-fi terminal palette
BLUE      = "\033[38;5;33m"
CYAN      = "\033[38;5;51m"
ICE       = "\033[38;5;117m"
STEEL     = "\033[38;5;244m"
GREEN     = "\033[38;5;48m"
YELLOW    = "\033[38;5;220m"
RESET     = "\033[0m"

# Vocabulary corrections — Google hears real words for "DRAVION"
VOCAB_CORRECTIONS = {
    "dragon": "DRAVION", "draven": "DRAVION", "drayton": "DRAVION",
    "davion": "DRAVION", "driven": "DRAVION", "gravion": "DRAVION",
    "gravy on": "DRAVION", "dravian": "DRAVION", "drave": "DRAVION",
    "dry on": "DRAVION", "trevion": "DRAVION", "dravy on": "DRAVION",
    "draveon": "DRAVION", "dray": "DRAVION", "travio": "DRAVION",
    "travel on": "DRAVION", "trivion": "DRAVION", "gravier": "DRAVION",
    "el gravy on": "DRAVION", "dr avion": "DRAVION",
}


class Listener:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.energy_threshold = 4000

        # Auto-detect best mic
        self.mic_index = None
        log.info("listener_ready", engine="Google STT")

    def _correct_vocabulary(self, text: str) -> str:
        if not text:
            return text
        corrected = text
        for wrong, right in VOCAB_CORRECTIONS.items():
            if " " in wrong:
                corrected = corrected.replace(wrong, right)
                corrected = corrected.replace(wrong.title(), right)
        words = corrected.split()
        result = []
        for word in words:
            clean = word.lower().strip(".,!?;:")
            if clean in VOCAB_CORRECTIONS:
                result.append(VOCAB_CORRECTIONS[clean])
            else:
                result.append(word)
        return " ".join(result)

    async def listen(self, timeout: int = 8) -> str | None:
        """Listen for a voice command. Returns transcribed text or None."""
        import asyncio
        return await asyncio.to_thread(self._listen_sync, timeout)

    def _listen_sync(self, timeout: int = 8) -> str | None:
        print(f"  {STEEL}◈ Listening...{RESET}", end="", flush=True)
        try:
            with sr.Microphone(device_index=self.mic_index) as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=15)

            print(f" {GREEN}locked.{RESET}")

            text = self.recognizer.recognize_google(audio)
            if text:
                text = self._correct_vocabulary(text)
                return text.strip()

        except sr.WaitTimeoutError:
            print(f" {STEEL}(silence){RESET}")
            return None
        except sr.UnknownValueError:
            print(f" {YELLOW}(missed that){RESET}")
            return None
        except sr.RequestError as e:
            print(f" {YELLOW}(STT error){RESET}")
            return None
        except Exception as e:
            log.error("listen_error", error=str(e))
            return None

        return None
