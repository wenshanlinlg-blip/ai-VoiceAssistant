"""文字转语音：豆包语音合成（火山引擎 seed-tts-2.0）。"""
import base64
import json
import os
import uuid

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
import pygame
import requests


class Speaker:
    def __init__(self, api_key, resource_id, model, voice, url):
        self.api_key = api_key
        self.resource_id = resource_id
        self.model = model
        self.voice = voice
        self.url = url
        self.tmp_file = None
        self._prev_file = None
        self._mixer_ready = False

    def _ensure_mixer(self):
        if not self._mixer_ready:
            pygame.mixer.init()
            self._mixer_ready = True

    def speak(self, text):
        self._ensure_mixer()
        self._synthesize(text)
        pygame.mixer.music.load(self.tmp_file)
        pygame.mixer.music.play()
        self._cleanup_prev()

    def _synthesize(self, text):
        payload = {
            "req_params": {
                "text": text,
                "model": self.model,
                "speaker": self.voice,
                "audio_params": {"format": "mp3", "sample_rate": 24000, "speech_rate": 0, "loudness_rate": 0},
            }
        }
        headers = {
            "X-Api-Key": self.api_key,
            "X-Api-Resource-Id": self.resource_id,
            "X-Api-Request-Id": str(uuid.uuid4()),
            "Content-Type": "application/json",
        }
        resp = requests.post(self.url, json=payload, headers=headers, stream=True, timeout=30)
        resp.raise_for_status()
        audio = bytearray()
        for line in resp.iter_lines():
            if not line:
                continue
            obj = json.loads(line)
            data = obj.get("data")
            if data:
                audio.extend(base64.b64decode(data))
        # 每次用唯一文件名，避免上一个文件还被 pygame 占用导致 Permission denied
        self.tmp_file = f"reply_{uuid.uuid4().hex[:8]}.mp3"
        with open(self.tmp_file, "wb") as f:
            f.write(bytes(audio))

    def _cleanup_prev(self):
        if self._prev_file and os.path.exists(self._prev_file):
            try:
                os.remove(self._prev_file)
            except OSError:
                pass
        self._prev_file = self.tmp_file

    def stop(self):
        if self._mixer_ready:
            pygame.mixer.music.stop()

    def is_playing(self):
        if not self._mixer_ready:
            return False
        return bool(pygame.mixer.music.get_busy())
