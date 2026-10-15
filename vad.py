"""能量检测（VAD）：根据音量判断一句话何时开始、何时说完。"""
import numpy as np


def rms(frame):
    """一帧音频的响度（均方根），数值越大声音越响。"""
    return float(np.sqrt(np.mean(np.square(frame.astype(np.float32)))))


class SpeechDetector:
    def __init__(self, threshold, block_ms, silence_ms, min_speech_ms):
        self.threshold = threshold
        self.silence_limit = max(1, int(round(silence_ms / block_ms)))
        self.min_speech = max(1, int(round(min_speech_ms / block_ms)))
        self.frames = []
        self.speech_count = 0
        self.silence_count = 0
        self.in_speech = False

    def reset(self):
        self.frames = []
        self.speech_count = 0
        self.silence_count = 0
        self.in_speech = False

    def add(self, frame):
        """喂入一帧，返回 (事件, 音频)。
        "speech" 表示正在说话；"end" 表示一句话说完了（音频是完整的一句话）。"""
        if rms(frame) > self.threshold:
            self.in_speech = True
            self.speech_count += 1
            self.silence_count = 0
            self.frames.append(frame)
            return ("speech", None)
        else:
            if not self.in_speech:
                return (None, None)  # 一直是静音，忽略
            self.silence_count += 1
            self.frames.append(frame)
            if self.silence_count >= self.silence_limit:
                if self.speech_count >= self.min_speech:
                    audio = np.concatenate(self.frames)
                    self.reset()
                    return ("end", audio)
                self.reset()  # 太短，当作噪音丢掉
            return (None, None)
