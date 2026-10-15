"""对话状态机：后台线程跑，处理自动检测/按键说话两种模式 + 打断。"""
import queue
import threading
import time

import numpy as np

from audio import Microphone
from vad import SpeechDetector, rms
from stt import Transcriber
from llm import ChatBot
from tts import Speaker


class Conversation:
    def __init__(self, config, ui_queue):
        self.config = config
        self.ui_queue = ui_queue  # 向界面发消息的队列

        vad = config["vad"]
        stt = config["stt"]
        llm = config["llm"]
        ast = config["assistant"]
        volc = config.get("volcengine", {})
        tts_cfg = config.get("tts", {})

        self.threshold = vad["energy_threshold"]
        self.silence_ms = vad["silence_ms"]
        self.min_speech_ms = vad["min_speech_ms"]
        self.block_ms = vad["block_ms"]
        self.sample_rate = vad["sample_rate"]

        self.mic = Microphone(self.sample_rate, self.block_ms)
        self.transcriber = Transcriber(
            stt["api_key"], stt["resource_id"], stt["ws_url"]
        )
        self.chatbot = ChatBot(
            llm["base_url"], llm["api_key"], llm["model"], ast["name"], ast["personality"]
        )
        self.speaker = Speaker(
            tts_cfg["api_key"], tts_cfg["resource_id"], tts_cfg["model"],
            tts_cfg["voice"], tts_cfg["url"]
        )

        self.mode = config.get("mode", "auto")
        self.push_talk = threading.Event()
        self.running = False
        self.thread = None

    # ---- 对外接口 ----
    def set_mode(self, mode):
        self.mode = mode

    def start(self):
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)
        self.mic.stop()
        self.speaker.stop()

    # ---- 内部 ----
    def _emit(self, kind, text):
        self.ui_queue.put((kind, text))

    def _loop(self):
        self.mic.start()
        while self.running:
            if self.mode == "auto":
                self._auto_turn()
            else:
                self._push_turn()
        self.mic.stop()

    def _auto_turn(self):
        self._emit("status", "聆听中")
        self.mic.clear()
        detector = SpeechDetector(self.threshold, self.block_ms,
                                  self.silence_ms, self.min_speech_ms)
        while self.running and self.mode == "auto":
            try:
                frame = self.mic.read(timeout=0.2)
            except queue.Empty:
                continue
            event, audio = detector.add(frame)
            if event == "end":
                self._process(audio)
                return

    def _push_turn(self):
        self._emit("status", "待命（按住“说话”按钮）")
        while self.running and self.mode == "push":
            if self.push_talk.is_set():
                self.mic.clear()
                self._emit("status", "聆听中")
                frames = []
                while self.running and self.push_talk.is_set():
                    try:
                        frames.append(self.mic.read(timeout=0.2))
                    except queue.Empty:
                        pass
                if frames:
                    self._process(np.concatenate(frames))
                return
            try:
                self.mic.read(timeout=0.05)
            except queue.Empty:
                pass

    def _process(self, audio):
        self._emit("status", "思考中")
        try:
            text = self.transcriber.transcribe(audio)
            if not text:
                self._emit("status", "聆听中")
                return
            self._emit("log", f"你：{text}")

            reply = self.chatbot.chat(text)

            self._emit("status", "说话中")
            self.speaker.speak(reply)
            self._emit("log", f"助手：{reply}")
            self._wait_speaking()
        except Exception as e:
            self._emit("log", f"[出错] {e}")
            self._emit("status", "聆听中")

    def _wait_speaking(self):
        # 播放期间：自动模式下检测到用户说话就打断
        while self.running and self.speaker.is_playing():
            if self.mode == "auto":
                try:
                    frame = self.mic.read(timeout=0.2)
                except queue.Empty:
                    continue
                if rms(frame) > self.threshold:
                    self.speaker.stop()
                    self._emit("log", "（你打断了助手）")
                    return
            else:
                time.sleep(0.05)
