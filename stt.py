"""语音转文字：豆包大模型流式语音识别（火山引擎 SAUC WebSocket 二进制协议）。"""
import json
import struct

import numpy as np
import websocket

# 协议常量
PROTOCOL_VERSION = 0b0001
HEADER_SIZE = 0b0001
FULL_CLIENT_REQUEST = 0b0001
AUDIO_ONLY_REQUEST = 0b0010
FULL_SERVER_RESPONSE = 0b1001
ERROR_RESPONSE = 0b1111
NO_SEQUENCE = 0b0000          # header 后无 sequence 字段
POSITIVE_SEQUENCE = 0b0001    # 响应里：header 后有正 sequence
LAST_PACKET = 0b0010          # 音频最后一包（无 sequence）
NEGATIVE_SEQUENCE = 0b0011    # 响应里：header 后有负 sequence
JSON_SERIALIZATION = 0b0001
NO_SERIALIZATION = 0b0000
NO_COMPRESSION = 0b0000


def _header(msg_type, flags, serialization, compression):
    return bytes([
        (PROTOCOL_VERSION << 4) | HEADER_SIZE,
        (msg_type << 4) | flags,
        (serialization << 4) | compression,
        0x00,
    ])


class Transcriber:
    def __init__(self, api_key, resource_id, ws_url):
        self.api_key = api_key
        self.resource_id = resource_id
        self.ws_url = ws_url

    def transcribe(self, audio):
        """audio: float32 16kHz 单声道 numpy 数组 -> 识别文本"""
        pcm = (np.clip(audio, -1.0, 1.0) * 32767).astype(np.int16).tobytes()

        req = {
            "user": {"uid": "pc-assistant"},
            "audio": {"format": "pcm", "codec": "raw", "rate": 16000, "bits": 16, "channel": 1, "language": "zh-CN"},
            "request": {
                "model_name": "bigmodel",
                "enable_itn": False,
                "enable_punc": True,
                "enable_ddc": False,
                "show_utterances": True,
                "result_type": "full",
                "vad_segment_duration": 3000,
                "end_window_size": 800,
            },
        }

        ws = websocket.create_connection(
            self.ws_url,
            header=[f"X-Api-Key: {self.api_key}", f"X-Api-Resource-Id: {self.resource_id}"],
            timeout=15,
        )
        text = ""
        try:
            payload = json.dumps(req, ensure_ascii=False).encode("utf-8")
            ws.send_binary(
                _header(FULL_CLIENT_REQUEST, NO_SEQUENCE, JSON_SERIALIZATION, NO_COMPRESSION)
                + struct.pack(">I", len(payload)) + payload
            )

            # 音频帧不带 sequence（服务器自动分配），每 100ms 一包
            step = 3200
            for i in range(0, len(pcm), step):
                chunk = pcm[i:i + step]
                ws.send_binary(
                    _header(AUDIO_ONLY_REQUEST, NO_SEQUENCE, NO_SERIALIZATION, NO_COMPRESSION)
                    + struct.pack(">I", len(chunk)) + chunk
                )
            # 最后一包：flags=LAST_PACKET，表示音频结束
            ws.send_binary(
                _header(AUDIO_ONLY_REQUEST, LAST_PACKET, NO_SERIALIZATION, NO_COMPRESSION)
                + struct.pack(">I", 0) + b""
            )

            ws.settimeout(10)
            while True:
                try:
                    raw = ws.recv()
                except Exception:
                    break
                if not isinstance(raw, (bytes, bytearray)) or len(raw) < 8:
                    continue
                flags = raw[1] & 0x0F
                msg_type = raw[1] >> 4
                off = 4
                if flags in (POSITIVE_SEQUENCE, NEGATIVE_SEQUENCE):
                    off += 4
                payload_size = struct.unpack(">I", raw[off:off + 4])[0]
                off += 4
                payload = raw[off:off + payload_size]

                if msg_type == FULL_SERVER_RESPONSE:
                    obj = json.loads(payload.decode("utf-8"))
                    t = (obj.get("result") or {}).get("text", "")
                    if t:
                        text = t
                elif msg_type == ERROR_RESPONSE:
                    break
        finally:
            ws.close()
        return text.strip()
