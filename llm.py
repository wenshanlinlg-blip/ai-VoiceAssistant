"""对话大脑：用 openai SDK 连接 DeepSeek（改 config 里的 base_url 即可换接口）。
附带跨会话记忆：对话历史保存到 memory.json，重启后继续记得聊过的内容。"""
import json
import os

from openai import OpenAI


class ChatBot:
    def __init__(self, base_url, api_key, model, assistant_name, personality, memory_file="memory.json"):
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        self.memory_file = memory_file
        self.system = {
            "role": "system",
            "content": f"你叫{assistant_name}。{personality} 请用中文回答，尽量简短（一两句话），口语化，适合语音朗读，不要长篇大论。",
        }
        self.messages = [self.system]
        self._load_memory()

    def _load_memory(self):
        if not os.path.exists(self.memory_file):
            return
        try:
            with open(self.memory_file, "r", encoding="utf-8") as f:
                history = json.load(f)
            # 只恢复 user/assistant 消息，system 消息始终用当前配置
            self.messages = [self.system] + [
                m for m in history
                if isinstance(m, dict) and m.get("role") in ("user", "assistant")
            ]
        except Exception:
            pass

    def _save_memory(self):
        history = [m for m in self.messages if m.get("role") in ("user", "assistant")]
        # 只保留最近 20 条，避免文件无限增大、控制 token 成本
        history = history[-20:]
        try:
            with open(self.memory_file, "w", encoding="utf-8") as f:
                json.dump(history, f, ensure_ascii=False)
        except Exception:
            pass

    def clear_memory(self):
        self.messages = [self.system]
        try:
            if os.path.exists(self.memory_file):
                os.remove(self.memory_file)
        except Exception:
            pass

    def chat(self, user_text):
        self.messages.append({"role": "user", "content": user_text})
        resp = self.client.chat.completions.create(
            model=self.model, messages=self.messages, max_tokens=200
        )
        reply = resp.choices[0].message.content.strip()
        self.messages.append({"role": "assistant", "content": reply})
        self._save_memory()
        return reply
