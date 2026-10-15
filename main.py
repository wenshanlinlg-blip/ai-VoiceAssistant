"""入口：现代深色 tkinter 界面 + 后台加载并启动对话。"""
import json
import math
import queue
import threading
import tkinter as tk

from conversation import Conversation

CONFIG_PATH = "config.json"

# ---- 配色（深色主题）----
BG = "#1a1b26"
CARD = "#24283b"
TEXT = "#c0caf5"
DIM = "#565f89"
ACCENT = "#7aa2f7"
GREEN = "#9ece6a"
ORANGE = "#e0af68"
RED = "#f7768e"

FONT_TITLE = ("Microsoft YaHei UI", 18, "bold")
FONT_STATUS = ("Microsoft YaHei UI", 13)
FONT_LOG = ("Microsoft YaHei UI", 10)
FONT_BTN = ("Microsoft YaHei UI", 10)
FONT_HINT = ("Microsoft YaHei UI", 8)


class App:
    def __init__(self, root, config):
        self.root = root
        self.config = config
        self.ui_queue = queue.Queue()
        self.conversation = None
        self.name = config["assistant"]["name"]

        self._status_text = "正在加载…"
        self._anim_phase = 0
        self._running = True

        root.title(self.name)
        root.geometry("500x640")
        root.minsize(440, 540)
        root.configure(bg=BG)

        self._build_ui()
        self._bind_keys()

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.after(100, self._poll)
        self.root.after(60, self._animate)
        threading.Thread(target=self._init_conversation, daemon=True).start()

    # ---- UI 构建 ----
    def _build_ui(self):
        tk.Label(self.root, text=f"🎙 {self.name}", font=FONT_TITLE, bg=BG, fg=TEXT).pack(pady=(24, 2))
        tk.Label(self.root, text="你的个人语音助手", font=FONT_BTN, bg=BG, fg=DIM).pack()

        # 状态动画画布
        self.status_canvas = tk.Canvas(self.root, width=220, height=72, bg=BG, highlightthickness=0)
        self.status_canvas.pack(pady=(10, 0))
        self.status_label = tk.Label(self.root, text="正在加载…", font=FONT_STATUS, bg=BG, fg=DIM)
        self.status_label.pack(pady=(2, 10))

        # 按住说话按钮
        self.talk_btn = tk.Button(
            self.root, text="按住说话", font=FONT_STATUS, bg=ACCENT, fg="#1a1b26",
            activebackground=GREEN, activeforeground="#1a1b26",
            relief="flat", padx=34, pady=15, cursor="hand2", bd=0,
            disabledforeground=DIM, highlightthickness=0, takefocus=0,
        )
        self.talk_btn.pack(pady=(2, 6))
        self.talk_btn.bind("<ButtonPress-1>", self._on_press)
        self.talk_btn.bind("<ButtonRelease-1>", self._on_release)
        tk.Label(self.root, text="提示：空格键也可以按住说话", font=FONT_HINT, bg=BG, fg=DIM).pack(pady=(0, 8))

        # 模式切换
        self.mode_var = tk.StringVar(value=self.config.get("mode", "auto"))
        mode_frame = tk.Frame(self.root, bg=BG)
        mode_frame.pack(pady=(0, 10))
        tk.Label(mode_frame, text="模式", font=FONT_STATUS, bg=BG, fg=DIM).pack(side="left", padx=(0, 10))
        self.auto_rb = tk.Radiobutton(
            mode_frame, text="自动检测", variable=self.mode_var, value="auto",
            command=self._on_mode_change, bg=BG, fg=TEXT, selectcolor=CARD,
            activebackground=BG, activeforeground=ACCENT, font=FONT_STATUS, bd=0, takefocus=0,
        )
        self.auto_rb.pack(side="left", padx=5)
        self.push_rb = tk.Radiobutton(
            mode_frame, text="按键说话", variable=self.mode_var, value="push",
            command=self._on_mode_change, bg=BG, fg=TEXT, selectcolor=CARD,
            activebackground=BG, activeforeground=ACCENT, font=FONT_STATUS, bd=0, takefocus=0,
        )
        self.push_rb.pack(side="left", padx=5)
        self._sync_talk_btn()

        # 对话日志
        log_frame = tk.Frame(self.root, bg=CARD)
        log_frame.pack(fill="both", expand=True, padx=18, pady=(0, 6))
        self.log = tk.Text(
            log_frame, bg=CARD, fg=TEXT, font=FONT_LOG, relief="flat",
            wrap="word", state="disabled", padx=14, pady=12, bd=0,
        )
        self.log.pack(fill="both", expand=True)
        self.log.tag_configure("user", foreground=ACCENT)
        self.log.tag_configure("assistant", foreground=GREEN)
        self.log.tag_configure("error", foreground=RED)
        self.log.tag_configure("system", foreground=DIM)

        # 底部操作按钮
        btn_frame = tk.Frame(self.root, bg=BG)
        btn_frame.pack(pady=(0, 14))
        self._small_btn(btn_frame, "清空对话", self._on_clear_log).pack(side="left", padx=6)
        self._small_btn(btn_frame, "清除记忆", self._on_clear_memory).pack(side="left", padx=6)

    def _small_btn(self, parent, text, cmd):
        return tk.Button(
            parent, text=text, font=FONT_BTN, bg=CARD, fg=TEXT,
            activebackground=ACCENT, activeforeground="#1a1b26",
            relief="flat", padx=14, pady=6, cursor="hand2", bd=0, command=cmd, takefocus=0,
        )

    def _bind_keys(self):
        self.root.bind("<space>", self._on_press)
        self.root.bind("<KeyRelease-space>", self._on_release)

    # ---- 状态与动画 ----
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
        self._status_text = text
        self.status_label.config(text=text, fg=self._status_color(text))

    def _animate(self):
        if not self._running:
            return
        self._anim_phase += 1
        c = self.status_canvas
        c.delete("all")
        w, h = 220, 72
        color = self._status_color(self._status_text)
        if self._status_text.startswith("聆听") or self._status_text.startswith("说话"):
            n, bw, gap = 7, 8, 14
            total = n * bw + (n - 1) * gap
            x0 = (w - total) / 2
            for i in range(n):
                v = (math.sin(self._anim_phase * 0.3 + i * 0.85) + 1) / 2
                bh = 6 + v * (h - 16)
                x = x0 + i * (bw + gap)
                c.create_rectangle(x, (h - bh) / 2, x + bw, (h + bh) / 2, fill=color, outline="")
        else:
            pulse = 0
            if self._status_text.startswith("思考") or self._status_text.startswith("正在加载"):
                pulse = (math.sin(self._anim_phase * 0.15) + 1) / 2 * 3
            r = 13 + pulse
            c.create_oval(w / 2 - r, h / 2 - r, w / 2 + r, h / 2 + r, fill=color, outline="")
        self.root.after(60, self._animate)

    # ---- 事件处理 ----
    def _sync_talk_btn(self):
        push = self.mode_var.get() == "push"
        self.talk_btn.config(state="normal" if push else "disabled", bg=ACCENT if push else CARD)

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

    def _on_press(self, e=None):
        if self.conversation:
            self.conversation.push_talk.set()

    def _on_release(self, e=None):
        if self.conversation:
            self.conversation.push_talk.clear()

    def _on_clear_log(self):
        self.log.config(state="normal")
        self.log.delete("1.0", "end")
        self.log.config(state="disabled")

    def _on_clear_memory(self):
        if self.conversation:
            self.conversation.clear_memory()

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
        self._running = False
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
