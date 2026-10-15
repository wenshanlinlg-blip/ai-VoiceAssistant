"""对话大脑：用 openai SDK 连接 DeepSeek，支持 function calling 工具调用。
附带跨会话记忆：对话历史保存到 memory.json。"""
import json
import os

from openai import OpenAI

from tools import TOOLS, run_tool


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
            self.messages = [self.system] + [
                m for m in history
                if isinstance(m, dict) and m.get("role") in ("user", "assistant") and m.get("content")
            ]
        except Exception:
            pass

    def _save_memory(self):
        history = [m for m in self.messages
                   if m.get("role") in ("user", "assistant") and m.get("content")]
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
            model=self.model, messages=self.messages, max_tokens=200, tools=TOOLS
        )
        msg = resp.choices[0].message

        if msg.tool_calls:
            # 模型要调用工具，执行后把结果回传给模型
            self.messages.append({
                "role": "assistant",
                "content": msg.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                    }
                    for tc in msg.tool_calls
                ],
            })
            for tc in msg.tool_calls:
                args = json.loads(tc.function.arguments or "{}")
                result = run_tool(tc.function.name, args)
                self.messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})
            resp2 = self.client.chat.completions.create(
                model=self.model, messages=self.messages, max_tokens=200
            )
            reply = resp2.choices[0].message.content.strip()
        else:
            reply = (msg.content or "").strip()

        self.messages.append({"role": "assistant", "content": reply})
        self._save_memory()
        return reply
