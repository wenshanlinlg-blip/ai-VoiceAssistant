"""入口：tkinter 界面 + 后台加载模型并启动对话。"""
import json
import queue
import threading
import tkinter as tk

from conversation import Conversation

CONFIG_PATH = "config.json"

# ---- 配色（深色主题）----
BG = "#1a1b26"          # 主背景
CARD = "#24283b"        # 卡片/日志背景
TEXT = "#c0caf5"        # 主文字
DIM = "#565f89"         # 次要文字
ACCENT = "#7aa2f7"      # 强调色（蓝）
GREEN = "#9ece6a"       # 聆听/助手
ORANGE = "#e0af68"      # 思考中
RED = "#f7768e"         # 错误

FONT_TITLE = ("Microsoft YaHei UI", 18, "bold")
FONT_STATUS = ("Microsoft YaHei UI", 13)
FONT_LOG = ("Microsoft YaHei UI", 10)


class App:
    def __init__(self, root, config):
        self.root = root
        self.config = config
        self.ui_queue = queue.Queue()
        self.conversation = None
        self.name = config["assistant"]["name"]

        root.title(self.name)
        root.geometry("500x600")
        root.minsize(420, 500)
        root.configure(bg=BG)

        self._build_ui()

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.after(100, self._poll)
        threading.Thread(target=self._init_conversation, daemon=True).start()

    def _build_ui(self):
        # 标题
        tk.Label(self.root, text=f"🎙 {self.name}", font=FONT_TITLE, bg=BG, fg=TEXT).pack(pady=(26, 2))

        # 状态指示圆点
        self.status_canvas = tk.Canvas(self.root, width=56, height=56, bg=BG, highlightthickness=0)
        self.status_canvas.pack(pady=(10, 0))
        self.status_dot = self.status_canvas.create_oval(14, 14, 42, 42, fill=DIM, outline="")

        self.status_label = tk.Label(self.root, text="正在加载…", font=FONT_STATUS, bg=BG, fg=DIM)
        self.status_label.pack(pady=(6, 14))

        # 按住说话按钮（大按钮）
        self.talk_btn = tk.Button(
            self.root, text="按住说话", font=FONT_STATUS, bg=ACCENT, fg="#1a1b26",
            activebackground=GREEN, activeforeground="#1a1b26",
            relief="flat", padx=34, pady=16, cursor="hand2", bd=0,
            disabledforeground=DIM, highlightthickness=0,
        )
        self.talk_btn.pack(pady=(2, 10))
        self.talk_btn.bind("<ButtonPress-1>", self._on_press)
        self.talk_btn.bind("<ButtonRelease-1>", self._on_release)

        # 模式切换
        self.mode_var = tk.StringVar(value=self.config.get("mode", "auto"))
        mode_frame = tk.Frame(self.root, bg=BG)
        mode_frame.pack(pady=(2, 12))
        tk.Label(mode_frame, text="模式", font=FONT_STATUS, bg=BG, fg=DIM).pack(side="left", padx=(0, 10))
        self.auto_rb = tk.Radiobutton(
            mode_frame, text="自动检测", variable=self.mode_var, value="auto",
            command=self._on_mode_change, bg=BG, fg=TEXT, selectcolor=CARD,
            activebackground=BG, activeforeground=ACCENT, font=FONT_STATUS, bd=0,
        )
        self.auto_rb.pack(side="left", padx=5)
        self.push_rb = tk.Radiobutton(
            mode_frame, text="按键说话", variable=self.mode_var, value="push",
            command=self._on_mode_change, bg=BG, fg=TEXT, selectcolor=CARD,
            activebackground=BG, activeforeground=ACCENT, font=FONT_STATUS, bd=0,
        )
        self.push_rb.pack(side="left", padx=5)
        self._sync_talk_btn()

        # 对话日志
        log_frame = tk.Frame(self.root, bg=CARD)
        log_frame.pack(fill="both", expand=True, padx=18, pady=(0, 18))
        self.log = tk.Text(
            log_frame, bg=CARD, fg=TEXT, font=FONT_LOG, relief="flat",
            wrap="word", state="disabled", padx=14, pady=12, bd=0, cursor="arrow",
        )
        self.log.pack(fill="both", expand=True)
        self.log.tag_configure("user", foreground=ACCENT)
        self.log.tag_configure("assistant", foreground=GREEN)
        self.log.tag_configure("error", foreground=RED)
        self.log.tag_configure("system", foreground=DIM)

    def _status_color(self, text):
        if text.startswith("聆听"):
            return GREEN
        if text.startswith("思考"):
            return ORANGE
        if text.startswith("说话"):
            return ACCENT
        if text.startswith("启动失败") or text.startswith("出错"):
            return RED
        return DIM

    def _set_status(self, text):
        self.status_label.config(text=text, fg=self._status_color(text))
        self.status_canvas.itemconfig(self.status_dot, fill=self._status_color(text))

    def _sync_talk_btn(self):
        push = self.mode_var.get() == "push"
        self.talk_btn.config(state="normal" if push else "disabled",
                             bg=ACCENT if push else CARD)

    def _init_conversation(self):
        try:
            self.conversation = Conversation(self.config, self.ui_queue)
            self.conversation.start()
        except Exception as e:
            self.ui_queue.put(("status", f"启动失败：{e}"))

    def _on_mode_change(self):
        if self.conversation:
            self.conversation.set_mode(self.mode_var.get())
        self._sync_talk_btn()

    def _on_press(self, e):
        if self.conversation:
            self.conversation.push_talk.set()

    def _on_release(self, e):
        if self.conversation:
            self.conversation.push_talk.clear()

    def _poll(self):
        try:
            while True:
                kind, text = self.ui_queue.get_nowait()
                if kind == "status":
                    self._set_status(text)
                elif kind == "log":
                    self._append_log(text)
        except queue.Empty:
            pass
        self.root.after(100, self._poll)

    def _append_log(self, text):
        if text.startswith("你："):
            tag = "user"
        elif text.startswith("助手："):
            tag = "assistant"
        elif text.startswith("[出错]"):
            tag = "error"
        else:
            tag = "system"
        self.log.config(state="normal")
        self.log.insert("end", text + "\n", tag)
        self.log.see("end")
        self.log.config(state="disabled")

    def _on_close(self):
        if self.conversation:
            self.conversation.stop()
        self.root.destroy()


def load_config(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    config = load_config(CONFIG_PATH)
    root = tk.Tk()
    App(root, config)
    root.mainloop()


if __name__ == "__main__":
    main()
