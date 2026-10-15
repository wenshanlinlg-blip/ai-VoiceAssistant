"""麦克风采集：用 sounddevice 的 callback 把音频帧放进队列，避免缓冲堆积。"""
import queue

import sounddevice as sd


class Microphone:
    def __init__(self, sample_rate=16000, block_ms=30):
        self.sample_rate = sample_rate
        self.block_ms = block_ms
        self.block_size = int(sample_rate * block_ms / 1000)
        # 最多缓存 100 帧（约 3 秒），满了就丢最旧的，防止积压导致延迟
        self.q = queue.Queue(maxsize=100)
        self.stream = None

    def _callback(self, indata, frames, time_info, status):
        if self.q.full():
            try:
                self.q.get_nowait()
            except queue.Empty:
                pass
        self.q.put(indata[:, 0].copy())

    def start(self):
        self.stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype="float32",
            blocksize=self.block_size,
            callback=self._callback,
        )
        self.stream.start()

    def read(self, timeout=1.0):
        """取一帧音频；没有新数据时会阻塞到超时并抛出 queue.Empty。"""
        return self.q.get(timeout=timeout)

    def clear(self):
        """清空积压的旧音频帧（每轮对话开始前调用）。"""
        while not self.q.empty():
            try:
                self.q.get_nowait()
            except queue.Empty:
                break

    def stop(self):
        if self.stream is not None:
            self.stream.stop()
            self.stream.close()
            self.stream = None
