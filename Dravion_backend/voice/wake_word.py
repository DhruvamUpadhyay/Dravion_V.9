import asyncio
from core.logger import log
from core.event_bus import event_bus

class WakeWordDetector:
    """
    Wake word detection (Porcupine/Picovoice)
    """
    def __init__(self, wake_word: str = "dravion"):
        self.wake_word = wake_word
        self.running = False

    async def start(self):
        self.running = True
        log.info("wake_word_detector_started", wake_word=self.wake_word)
        
        # Simulate background listener loop
        asyncio.create_task(self._listen_loop())

    async def stop(self):
        self.running = False
        log.info("wake_word_detector_stopped")

    async def _listen_loop(self):
        while self.running:
            # Simulate detection waiting
            await asyncio.sleep(10)
            if self.running:
                log.debug("wake_word_detected")
                await event_bus.publish("wake.word.detected", {"timestamp": "now"})

wake_word_detector = WakeWordDetector()
