"""
DRAVION v.9 — Speaker (Google Cloud TTS — Journey Voice)

DRAVION's mouth. Uses service account auth for Google Cloud TTS.

v2: Sentence-level streaming — splits response into chunks and plays
    each one as it's ready. First audio plays in <1s instead of waiting
    for the full response to synthesize.
"""
import asyncio
import json
import time
import re
import aiohttp
import base64
import tempfile
import os
from core.config import config
from core.logger import log


class Speaker:
    TTS_URL = "https://texttospeech.googleapis.com/v1/text:synthesize"
    TOKEN_URL = "https://oauth2.googleapis.com/token"
    SCOPE = "https://www.googleapis.com/auth/cloud-platform"

    def __init__(self, voice_name: str = "en-US-Journey-D"):
        self.voice_name = voice_name
        self._access_token = None
        self._token_expiry = 0
        self._speaking = False

        # Load service account credentials
        creds_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "gcloud-key.json")
        try:
            with open(creds_path) as f:
                self._creds = json.load(f)
            log.info("speaker_ready", voice=self.voice_name)
        except FileNotFoundError:
            log.error("gcloud_key_not_found", path=creds_path)
            self._creds = None

    async def speak(self, text: str):
        """Stream-speak: split into sentences, synthesize & play each chunk."""
        if not self._creds:
            return
        try:
            text = self._clean_for_speech(text)
            text = self._fix_pronunciation(text)

            if not text.strip():
                return

            # Split into speakable chunks (1-2 sentences each)
            chunks = self._split_into_chunks(text)

            if len(chunks) <= 1:
                # Short response — just do it normally
                audio = await self._synthesize(text)
                if audio:
                    self._speaking = True
                    await self._play(audio)
                    self._speaking = False
                return

            # Stream: synthesize next chunk while current one plays
            self._speaking = True
            next_audio = None

            for i, chunk in enumerate(chunks):
                if not self._speaking:
                    break

                # If we pre-fetched the next audio, use it
                if next_audio:
                    current_audio = next_audio
                    next_audio = None
                else:
                    current_audio = await self._synthesize(chunk)

                if not current_audio:
                    continue

                # Start playing current + fetching next in parallel
                if i + 1 < len(chunks):
                    play_task = asyncio.create_task(self._play(current_audio))
                    fetch_task = asyncio.create_task(self._synthesize(chunks[i + 1]))
                    await play_task
                    next_audio = await fetch_task
                else:
                    await self._play(current_audio)

            self._speaking = False

        except Exception as e:
            self._speaking = False
            log.error("tts_error", error=str(e))

    def stop(self):
        """Stop speaking immediately."""
        self._speaking = False
        try:
            import pygame
            pygame.mixer.music.stop()
        except:
            pass

    @staticmethod
    def _split_into_chunks(text: str, max_chars: int = 200) -> list:
        """Split text into sentence-based chunks for streaming TTS."""
        # Split on sentence boundaries
        sentences = re.split(r'(?<=[.!?])\s+', text)

        chunks = []
        current = ""
        for s in sentences:
            if len(current) + len(s) < max_chars:
                current = (current + " " + s).strip()
            else:
                if current:
                    chunks.append(current)
                current = s
        if current:
            chunks.append(current)

        return chunks if chunks else [text]

    @staticmethod
    def _clean_for_speech(text: str) -> str:
        """Clean markdown and code blocks for natural speech."""
        # If text has code blocks AND is long, summarize
        if '```' in text and len(text) > 800:
            return "I've got the details ready. Check the terminal for the full output, Boss."

        # Strip markdown formatting
        text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)   # **bold**
        text = re.sub(r'\*(.+?)\*', r'\1', text)        # *italic*
        text = re.sub(r'`(.+?)`', r'\1', text)          # `code`
        text = re.sub(r'#{1,6}\s+', '', text)            # ### headers
        text = text.replace('```', '')                    # code fences
        text = re.sub(r'\[(.+?)\]\(.+?\)', r'\1', text)  # [links](url)
        text = re.sub(r'^[-*]\s+', '', text, flags=re.MULTILINE)  # bullet points
        text = re.sub(r'\n{2,}', '. ', text)             # double newlines → period
        text = text.replace('\n', ' ')                    # single newlines → space

        return text.strip()

    @staticmethod
    def _fix_pronunciation(text: str) -> str:
        """Fix words that Journey mispronounces."""
        text = re.sub(r'\bDRAVION\b', 'Drayveon', text, flags=re.IGNORECASE)
        return text

    async def _get_token(self) -> str:
        """Get OAuth2 access token from service account JWT."""
        import jwt as pyjwt

        now = int(time.time())
        if self._access_token and now < self._token_expiry - 60:
            return self._access_token

        payload = {
            "iss": self._creds["client_email"],
            "scope": self.SCOPE,
            "aud": self.TOKEN_URL,
            "iat": now,
            "exp": now + 3600,
        }
        signed_jwt = pyjwt.encode(payload, self._creds["private_key"], algorithm="RS256")

        async with aiohttp.ClientSession() as session:
            async with session.post(self.TOKEN_URL, data={
                "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                "assertion": signed_jwt,
            }) as resp:
                data = await resp.json()
                self._access_token = data["access_token"]
                self._token_expiry = now + data.get("expires_in", 3600)
                return self._access_token

    async def _synthesize(self, text: str) -> bytes | None:
        token = await self._get_token()

        payload = {
            "input": {"text": text},
            "voice": {
                "languageCode": "en-US",
                "name": self.voice_name,
            },
            "audioConfig": {
                "audioEncoding": "MP3",
                "speakingRate": 1.0,
            },
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.TTS_URL,
                json=payload,
                headers={"Authorization": f"Bearer {token}"},
            ) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    log.error("tts_api_error", status=resp.status, body=body[:100])
                    return None
                data = await resp.json()
                return base64.b64decode(data["audioContent"])

    async def _play(self, audio_bytes: bytes):
        import pygame

        tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
        try:
            tmp.write(audio_bytes)
            tmp.close()

            if not pygame.mixer.get_init():
                pygame.mixer.init()
            pygame.mixer.music.load(tmp.name)
            pygame.mixer.music.play()

            while pygame.mixer.music.get_busy() and self._speaking:
                await asyncio.sleep(0.05)

            pygame.mixer.music.unload()
        finally:
            try:
                os.unlink(tmp.name)
            except OSError:
                pass
