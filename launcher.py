"""
区域电商智能数据分析助手 - GUI 启动管理器
一键启动后端服务、前端服务和 Ollama AI 模型服务
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import subprocess
import threading
import time
import os
import sys
import platform
import webbrowser
import json
from datetime import datetime

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(PROJECT_ROOT, 'backend')
BACKEND_ENTRY = os.path.join(BACKEND_DIR, 'server.py')

FRONTEND_PORT = 5173
BACKEND_PORT = 5000
OLLAMA_PORT = 11434
MYSQL_PORT = 3306

IS_WINDOWS = platform.system() == 'Windows'

MAX_LOG_LINES = 200
AUTO_CHECK_INTERVAL = 8

SERVICE_ORDER = ['mysql', 'ollama', 'backend', 'frontend']
SERVICE_NAMES = {
    'mysql': '🗄️ MySQL 数据库',
    'ollama': '🤖 Ollama AI 模型',
    'backend': '📡 Flask 后端 API',
    'frontend': '🎨 Vue 前端页面',
}


class ServiceLauncher:
    def __init__(self, root):
        """初始化启动管理器

        设置窗口属性、服务状态字典，构建界面，并启动初始检测与自动检测循环。
        root 为 tkinter 根窗口实例。
        """
        self.root = root
        self.root.title("黔数智析 - 启动管理器")
        self.root.geometry("980x760")
        self.root.minsize(820, 620)
        self.root.configure(bg='#f0f2f5')

        self.backend_process = None
        self.frontend_process = None
        self.ollama_process = None
        self._backend_pid = None
        self._frontend_pid = None
        self._backend_log_file = None
        self._frontend_log_file = None

        self.service_running = {k: False for k in SERVICE_ORDER}
        self.service_starting = {k: False for k in SERVICE_ORDER}
        self.status_cards = {}

        self._auto_check_enabled = True

        self.setup_ui()

        self.start_btn.config(state='disabled')
        self.root.after(500, self._initial_check)
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.root.after(AUTO_CHECK_INTERVAL * 1000, self._auto_check_loop)

    def setup_ui(self):
        """构建主界面

        依次创建标题栏、服务状态卡片、控制按钮区域和日志输出区域。
        """
        title_frame = tk.Frame(self.root, bg='#1890ff', height=90)
        title_frame.pack(fill='x')
        title_frame.pack_propagate(False)

        tk.Label(
            title_frame,
            text="黔数智析",
            font=('Microsoft YaHei UI', 18, 'bold'),
            bg='#1890ff', fg='white'
        ).pack(pady=(15, 2))

        tk.Label(
            title_frame,
            text="区域电商智能数据分析助手 · 服务监测管理",
            font=('Microsoft YaHei UI', 10),
            bg='#1890ff', fg='#d6eaff'
        ).pack()

        main = tk.Frame(self.root, bg='#f0f2f5')
        main.pack(fill='both', expand=True, padx=20, pady=15)

        self._build_status_cards(main)
        self._build_control_buttons(main)
        self._build_log_area(main)

    def _build_status_cards(self, parent):
        """构建服务状态卡片

        在 parent 容器中创建四张服务状态卡片（MySQL、Ollama、后端、前端），
        每张卡片包含图标、标题、副标题和状态标签。
        """
        frame = tk.Frame(parent, bg='#f0f2f5')
        frame.pack(fill='x', pady=(0, 15))

        cards_info = [
            ('mysql',   '数据库服务',  f'MySQL · 端口 {MYSQL_PORT}'),
            ('ollama',  'AI 模型服务',  'Ollama (qwen3:8b)'),
            ('backend', '后端 API 服务', f'Flask · 端口 {BACKEND_PORT}'),
            ('frontend','前端页面服务', f'Vue 3 + Vite · 端口 {FRONTEND_PORT}'),
        ]

        for col, (key, title, subtitle) in enumerate(cards_info):
            card_frame = tk.Frame(frame, bg='white', relief='groove', bd=1)
            card_frame.grid(row=0, column=col, padx=8, pady=5, sticky='nsew')
            frame.grid_columnconfigure(col, weight=1, minsize=180)

            icon_lbl = tk.Label(card_frame, text="⏸",
                                font=('Segoe UI Emoji', 26), bg='white')
            icon_lbl.pack(pady=(12, 4))

            tk.Label(card_frame, text=title,
                     font=('Microsoft YaHei UI', 11, 'bold'),
                     bg='white', fg='#333').pack()

            tk.Label(card_frame, text=subtitle,
                     font=('Microsoft YaHei UI', 9),
                     bg='white', fg='#999').pack(pady=(2, 6))

            status_lbl = tk.Label(card_frame, text="检测中…",
                                  font=('Microsoft YaHei UI', 9, 'bold'),
                                  bg='#e6f7ff', fg='#1890ff',
                                  padx=18, pady=4)
            status_lbl.pack(pady=(0, 12))

            self.status_cards[key] = {
                'frame': card_frame,
                'icon': icon_lbl,
                'status': status_lbl,
            }

    def _update_card(self, key, text, bg_color, fg_color, icon):
        """更新状态卡片显示

        根据 key 定位卡片，更新状态文本、背景色、前景色和图标。
        """
        card = self.status_cards[key]
        card['status'].config(text=text, bg=bg_color, fg=fg_color)
        card['icon'].config(text=icon)

    def _set_card_starting(self, key):
        """将指定服务的状态卡片切换为「启动中」

        同时将 service_starting 标记为 True。
        """
        self.service_starting[key] = True
        self._update_card(key, '⏳ 启动中…', '#faad14', 'white', '🟡')

    def _set_card_stopping(self, key):
        """将指定服务的状态卡片切换为「停止中」"""
        self._update_card(key, '⏳ 停止中…', '#d9d9d9', '#666', '⚪')

    def _set_card_running(self, key):
        """将指定服务的状态卡片切换为「运行中」

        同时将 service_running 标记为 True，service_starting 标记为 False。
        """
        self.service_running[key] = True
        self.service_starting[key] = False
        self._update_card(key, '✅ 运行中', '#52c41a', 'white', '🟢')

    def _set_card_stopped(self, key):
        """将指定服务的状态卡片切换为「未启动」

        同时将 service_running 和 service_starting 均标记为 False。
        """
        self.service_running[key] = False
        self.service_starting[key] = False
        self._update_card(key, '⏸ 未启动', '#faad14', 'white', '⚪')

    def _set_card_error(self, key, text='❌ 异常'):
        """将指定服务的状态卡片切换为「异常」

        text 为显示的异常文本，默认为「❌ 异常」。
        同时将 service_running 和 service_starting 均标记为 False。
        """
        self.service_running[key] = False
        self.service_starting[key] = False
        self._update_card(key, text, '#ff4d4f', 'white', '🔴')

    def _build_control_buttons(self, parent):
        """构建控制按钮区域

        包含一键启动、停止全部、打开前端页面、重新检测按钮和自动检测复选框。
        """
        frame = tk.Frame(parent, bg='#f0f2f5')
        frame.pack(fill='x', pady=(0, 15))

        btn_style = dict(relief='flat', cursor='hand2', bd=0)

        self.start_btn = tk.Button(
            frame, text="🚀 一键启动全部", command=self.start_all_services,
            bg='#52c41a', fg='white', activebackground='#389e0d',
            font=('Microsoft YaHei UI', 11, 'bold'),
            padx=28, pady=10, **btn_style
        )
        self.start_btn.pack(side='left', padx=(0, 10))

        self.stop_btn = tk.Button(
            frame, text="⏹ 停止全部服务", command=self.stop_all_services,
            bg='#ff4d4f', fg='white', activebackground='#cf1322',
            font=('Microsoft YaHei UI', 11, 'bold'),
            padx=28, pady=10, state='disabled', **btn_style
        )
        self.stop_btn.pack(side='left', padx=(0, 10))

        self.open_btn = tk.Button(
            frame, text="🌐 打开前端页面", command=self.open_frontend,
            bg='#1890ff', fg='white', activebackground='#096dd9',
            font=('Microsoft YaHei UI', 10),
            padx=20, pady=8, **btn_style
        )
        self.open_btn.pack(side='left', padx=(0, 10))

        right_frame = tk.Frame(frame, bg='#f0f2f5')
        right_frame.pack(side='right')

        self.check_btn = tk.Button(
            right_frame, text="🔄 重新检测", command=self.check_all_services,
            bg='#faad14', fg='white', activebackground='#d48806',
            font=('Microsoft YaHei UI', 10),
            padx=16, pady=8, **btn_style
        )
        self.check_btn.pack(side='right', padx=(8, 0))

        self.auto_check_var = tk.BooleanVar(value=True)
        auto_cb = tk.Checkbutton(
            right_frame, text="自动检测", variable=self.auto_check_var,
            command=self._toggle_auto_check,
            bg='#f0f2f5', font=('Microsoft YaHei UI', 9),
            activebackground='#f0f2f5'
        )
        auto_cb.pack(side='right')

    def _build_log_area(self, parent):
        """构建日志输出区域

        包含日志标题栏（清空、导出按钮）和可滚动的日志文本框，
        文本框支持 info/success/warning/error/step 五种颜色标签。
        """
        frame = tk.Frame(parent, bg='#f0f2f5')
        frame.pack(fill='both', expand=True)

        header = tk.Frame(frame, bg='#f0f2f5')
        header.pack(fill='x', pady=(0, 5))

        tk.Label(header, text="📋 运行日志",
                 font=('Microsoft YaHei UI', 10, 'bold'),
                 bg='#f0f2f5', fg='#333').pack(side='left')

        btn_style = dict(relief='flat', cursor='hand2', bd=0,
                         font=('Microsoft YaHei UI', 8), padx=8, pady=2)

        tk.Button(header, text="🗑 清空", command=self._clear_log,
                  bg='#d9d9d9', fg='#333', **btn_style).pack(side='right', padx=(4, 0))
        tk.Button(header, text="💾 导出", command=self._export_log,
                  bg='#d9d9d9', fg='#333', **btn_style).pack(side='right')

        self.log_text = scrolledtext.ScrolledText(
            frame, wrap=tk.WORD,
            font=('Consolas', 9),
            bg='#1e1e1e', fg='#d4d4d4',
            insertbackground='white',
            relief='flat', padx=10, pady=10
        )
        self.log_text.pack(fill='both', expand=True)

        self.log_text.tag_config('info',    foreground='#4ecdc4')
        self.log_text.tag_config('success', foreground='#52c41a')
        self.log_text.tag_config('warning', foreground='#ffa502')
        self.log_text.tag_config('error',   foreground='#ff4d4f')
        self.log_text.tag_config('step',    foreground='#69b1ff')

    def log(self, message, tag='info'):
        """输出日志

        在日志文本框中追加带时间戳的日志消息，tag 控制颜色（info/success/warning/error/step）。
        超过 MAX_LOG_LINES + 50 行时自动裁剪旧日志。
        """
        ts = datetime.now().strftime('%H:%M:%S')
        self.log_text.insert(tk.END, f"[{ts}] {message}\n", tag)
        line_count = int(self.log_text.index('end-1c').split('.')[0])
        if line_count > MAX_LOG_LINES + 50:
            self.log_text.delete('1.0', f'{line_count - MAX_LOG_LINES}.0')
        self.log_text.see(tk.END)

    def _clear_log(self):
        """清空日志文本框"""
        self.log_text.delete('1.0', tk.END)
        self.log("日志已清空", 'info')

    def _export_log(self):
        """导出日志到文件

        弹出文件保存对话框，将日志文本框内容写入用户指定的 .log 文件。
        """
        filepath = filedialog.asksaveasfilename(
            defaultextension='.log',
            filetypes=[('日志文件', '*.log'), ('文本文件', '*.txt')],
            initialfile=f'launcher_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
        )
        if filepath:
            try:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(self.log_text.get('1.0', tk.END))
                self.log(f"日志已导出到: {filepath}", 'success')
            except Exception as e:
                self.log(f"导出失败: {e}", 'error')

    def _toggle_auto_check(self):
        """切换自动检测开关

        根据复选框状态启用或禁用自动检测，并输出相应日志。
        """
        self._auto_check_enabled = self.auto_check_var.get()
        if self._auto_check_enabled:
            self.log(f"自动检测已开启（每{AUTO_CHECK_INTERVAL}秒）", 'info')
        else:
            self.log("自动检测已关闭", 'warning')

    def _auto_check_loop(self):
        """自动检测循环

        每隔 AUTO_CHECK_INTERVAL 秒触发一次静默检测，通过 root.after 实现非阻塞定时。
        """
        if self._auto_check_enabled:
            threading.Thread(target=self._do_silent_check, daemon=True).start()
        self.root.after(AUTO_CHECK_INTERVAL * 1000, self._auto_check_loop)

    def _do_silent_check(self):
        """静默检测服务状态

        在后台线程中检测所有服务，若有任何服务状态变化则输出提示日志。
        有服务正在启动时跳过本次检测。
        """
        any_starting = any(self.service_starting.values())
        if any_starting:
            return
        prev = dict(self.service_running)
        self._check_mysql()
        self._check_ollama()
        self._check_backend()
        self._check_frontend()
        changed = False
        for k in SERVICE_ORDER:
            if prev.get(k) != self.service_running[k]:
                changed = True
                break
        if changed:
            self.log("🔄 服务状态已变化，已自动刷新", 'info')

    def _initial_check(self):
        """初始检测

        在后台线程中执行首次服务状态检测，完成后启用启动按钮。
        """
        threading.Thread(target=self._do_initial_check, daemon=True).start()

    def _do_initial_check(self):
        """执行初始检测

        依次检测 MySQL、Ollama、后端、前端服务状态，检测完成后启用启动按钮。
        """
        self.log("正在检测服务状态…", 'info')
        self._check_mysql()
        self._check_ollama()
        self._check_backend()
        self._check_frontend()
        self.start_btn.config(state='normal')

    def check_all_services(self):
        """手动检测所有服务

        在后台线程中执行全量服务状态检测。
        """
        threading.Thread(target=self._do_check_all, daemon=True).start()

    def _do_check_all(self):
        """执行手动检测

        依次检测 MySQL、Ollama、后端、前端服务状态并更新卡片。
        """
        self.log("正在检测服务状态…", 'info')
        self._check_mysql()
        self._check_ollama()
        self._check_backend()
        self._check_frontend()

    def _check_ollama(self):
        """检测 Ollama 服务状态

        通过 HTTP 请求 /api/tags 接口判断 Ollama 是否就绪，
        成功则标记为运行中，否则标记为未启动。
        """
        try:
            import urllib.request
            req = urllib.request.Request(
                f'http://localhost:{OLLAMA_PORT}/api/tags',
                headers={'Connection': 'close'}
            )
            with urllib.request.urlopen(req, timeout=2) as resp:
                if resp.status == 200:
                    self._set_card_running('ollama')
                    self.log("Ollama 服务已就绪", 'success')
                    return
        except Exception:
            pass
        self._set_card_stopped('ollama')
        self.log("Ollama 服务未运行，点击「一键启动」可自动启动", 'warning')

    def _check_mysql(self):
        """检测 MySQL 服务状态

        通过 TCP 连接 MySQL 端口判断服务是否就绪，
        成功则标记为运行中，否则标记为异常。
        """
        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex(('localhost', MYSQL_PORT))
            sock.close()
            if result == 0:
                self._set_card_running('mysql')
                self.log("MySQL 数据库服务已就绪", 'success')
                return
        except Exception:
            pass
        self._set_card_error('mysql', '❌ 未启动')
        self.log("MySQL 服务未运行，请先启动 MySQL 服务", 'error')

    def _check_backend(self):
        """检测后端服务状态

        通过 HTTP 请求 /api/status 接口判断 Flask 后端是否就绪，
        成功则标记为运行中，否则标记为未启动。
        """
        try:
            import urllib.request
            req = urllib.request.Request(
                f'http://localhost:{BACKEND_PORT}/api/status',
                headers={'Connection': 'close'}
            )
            with urllib.request.urlopen(req, timeout=2) as resp:
                if resp.status == 200:
                    self._set_card_running('backend')
                    self.log("后端服务运行中", 'success')
                    return
        except Exception:
            pass
        self._set_card_stopped('backend')

    def _check_frontend(self):
        """检测前端服务状态

        通过 HTTP 请求前端端口判断 Vue 前端是否就绪，
        成功则标记为运行中，否则标记为未启动。
        """
        try:
            import urllib.request
            req = urllib.request.Request(
                f'http://localhost:{FRONTEND_PORT}',
                headers={'Connection': 'close'}
            )
            with urllib.request.urlopen(req, timeout=2) as resp:
                if resp.status == 200:
                    self._set_card_running('frontend')
                    self.log("前端服务运行中", 'success')
                    return
        except Exception:
            pass
        self._set_card_stopped('frontend')

    def _check_ollama_model(self):
        """检查 Ollama 模型是否已安装

        查询 /api/tags 接口，检查是否包含 qwen3:8b 模型。
        返回 True 表示模型已就绪，False 表示未找到或检测失败。
        """
        try:
            import urllib.request
            req = urllib.request.Request(
                f'http://localhost:{OLLAMA_PORT}/api/tags',
                headers={'Connection': 'close'}
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode())
                models = [m.get('name', '') for m in data.get('models', [])]
                for m in models:
                    if 'qwen3' in m.lower() and '8b' in m.lower():
                        self.log(f"✅ 检测到模型: {m}", 'success')
                        return True
                self.log(f"⚠️ 已安装模型: {models}，未找到 qwen3:8b", 'warning')
                return False
        except Exception as e:
            self.log(f"⚠️ 模型检测失败: {e}", 'warning')
            return False

    def start_all_services(self):
        """一键启动全部服务

        前置检查 MySQL 是否就绪，若未就绪则弹窗提示并中止。
        启动前会清理已占用端口的旧进程，随后在后台线程中按顺序启动各服务。
        """
        self.log("=" * 60, 'info')
        self.log("开始按顺序启动所有服务…", 'info')

        if not self.service_running.get('mysql'):
            self.log("❌ MySQL 服务未启动，无法启动后端", 'error')
            messagebox.showerror("错误", "MySQL 数据库服务未启动！\n请先启动 MySQL 服务后再试。")
            return

        self.start_btn.config(state='disabled')
        self.stop_btn.config(state='normal')
        self._auto_check_enabled = False

        if self.service_running.get('backend') or self.service_running.get('frontend'):
            self.log("⚠️ 检测到已有服务运行，先清理旧进程…", 'warning')
            self._kill_port(BACKEND_PORT, 'Flask 后端')
            self._kill_port(FRONTEND_PORT, 'Vite 前端')
            time.sleep(2)

        threading.Thread(target=self._start_sequential, daemon=True).start()

    def _start_sequential(self):
        """按顺序启动服务

        依次启动 MySQL（检测）、Ollama、后端、前端，每步输出进度提示。
        MySQL 未就绪时中止后续启动。
        """
        total = 4
        step = 0

        step += 1
        self.log(f"━━━ [{step}/{total}] MySQL 数据库 ━━━", 'step')
        if self.service_running.get('mysql'):
            self.log("MySQL 已在运行，跳过", 'info')
        else:
            self._set_card_starting('mysql')
            self.log("⚠️ MySQL 未运行，请手动启动 MySQL 服务", 'error')
            self._set_card_error('mysql', '❌ 未启动')
            self.log("❌ MySQL 是必要服务，无法继续启动后续服务", 'error')
            self.start_btn.config(state='normal')
            self._auto_check_enabled = self.auto_check_var.get()
            return

        step += 1
        self.log(f"━━━ [{step}/{total}] Ollama AI 模型服务 ━━━", 'step')
        if self.service_running.get('ollama'):
            self.log("Ollama 已在运行，跳过", 'info')
        else:
            self._set_card_starting('ollama')
            self._start_ollama()
            if not self.service_running.get('ollama'):
                self.log("⚠️ Ollama 启动失败，后续 AI 功能将不可用", 'warning')

        if self.service_running.get('ollama'):
            self._check_ollama_model()

        step += 1
        self.log(f"━━━ [{step}/{total}] Flask 后端 API 服务 ━━━", 'step')
        if self.service_running.get('backend'):
            self.log("后端已在运行，跳过", 'info')
        else:
            self._set_card_starting('backend')
            self._start_backend()

        step += 1
        self.log(f"━━━ [{step}/{total}] Vue 前端页面服务 ━━━", 'step')
        if self.service_running.get('frontend'):
            self.log("前端已在运行，跳过", 'info')
        else:
            self._set_card_starting('frontend')
            self._start_frontend()

        self.log("=" * 60, 'success')
        self.log(f"✨ 所有服务启动完成！访问 http://localhost:{FRONTEND_PORT}", 'success')
        self.start_btn.config(state='normal')
        self._auto_check_enabled = self.auto_check_var.get()

    def _start_ollama(self):
        """启动 Ollama 服务

        查找 ollama 可执行文件并以 serve 模式启动子进程，
        最多等待 20 秒确认服务就绪，超时则标记为启动失败。
        """
        try:
            self.log("🤖 正在启动 Ollama 服务…", 'info')
            ollama_exe = self._find_ollama()
            if ollama_exe:
                self.ollama_process = subprocess.Popen(
                    [ollama_exe, 'serve'],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW if IS_WINDOWS else 0
                )
                for i in range(20):
                    time.sleep(1)
                    try:
                        import urllib.request
                        with urllib.request.urlopen(
                            f'http://localhost:{OLLAMA_PORT}/api/tags', timeout=2
                        ) as resp:
                            if resp.status == 200:
                                self._set_card_running('ollama')
                                self.log("✅ Ollama 服务启动成功", 'success')
                                return
                    except Exception:
                        pass
                self.log("⚠️ Ollama 启动超时，可能需要手动启动", 'warning')
                self._set_card_error('ollama', '❌ 启动超时')
            else:
                self.log("⚠️ 未找到 Ollama，请手动启动 ollama serve", 'warning')
                self._set_card_error('ollama', '❌ 未安装')
        except Exception as e:
            self.log(f"❌ Ollama 启动失败: {e}", 'error')
            self._set_card_error('ollama', '❌ 启动失败')

    def _find_ollama(self):
        """查找 Ollama 可执行文件路径

        查找顺序：
          1. LOCALAPPDATA 环境变量下的标准安装路径
          2. 系统 PATH 中的 ollama 命令（where/which）

        Returns:
            str or None: 找到的 ollama 可执行文件路径
        """
        candidates = [
            os.path.join(os.environ.get('LOCALAPPDATA', ''),
                         'Programs', 'Ollama', 'ollama.exe'),
        ]
        for path in candidates:
            if os.path.isfile(path):
                return path
        try:
            result = subprocess.run(
                ['where', 'ollama'],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip().split('\n')[0].strip()
        except Exception:
            pass
        return None

    def _start_backend(self):
        """启动后端服务

        检查 Python 依赖后以子进程启动 Flask 后端，将输出重定向到日志文件和界面，
        最多等待 60 秒确认服务就绪。
        """
        try:
            self.log("📡 正在启动 Flask 后端服务…", 'info')
            self._check_python_deps()

            cmd = [sys.executable, BACKEND_ENTRY]
            log_file_path = os.path.join(PROJECT_ROOT, 'backend_output.log')
            self._backend_log_file = open(log_file_path, 'w', encoding='utf-8')

            self.backend_process = subprocess.Popen(
                cmd,
                cwd=BACKEND_DIR,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1,
                env={**os.environ},
                creationflags=subprocess.CREATE_NO_WINDOW if IS_WINDOWS else 0
            )

            threading.Thread(
                target=self._drain_output,
                args=(self.backend_process, '📡', self._backend_log_file),
                daemon=True
            ).start()

            for i in range(60):
                time.sleep(1)
                try:
                    import urllib.request
                    with urllib.request.urlopen(
                        f'http://localhost:{BACKEND_PORT}/api/status', timeout=2
                    ) as resp:
                        if resp.status == 200:
                            break
                except Exception:
                    pass
            else:
                self.log("⚠️ 后端启动可能较慢，继续等待…", 'warning')

            self._set_card_running('backend')
            self._backend_pid = self.backend_process.pid
            self.log(f"✅ 后端服务启动成功 (http://localhost:{BACKEND_PORT})", 'success')

        except Exception as e:
            self.log(f"❌ 后端启动失败: {e}", 'error')
            self._set_card_error('backend', '❌ 启动失败')
            self.start_btn.config(state='normal')

    def _start_frontend(self):
        """启动前端服务

        首次运行时自动安装 npm 依赖，以子进程启动 Vite 开发服务器，
        将输出重定向到日志文件和界面，最多等待 60 秒确认服务就绪。
        """
        try:
            self.log("🎨 正在启动 Vue 前端服务…", 'info')

            if not os.path.isdir(os.path.join(PROJECT_ROOT, 'node_modules')):
                self.log("📦 首次运行，正在安装前端依赖…", 'info')
                install_proc = subprocess.run(
                    ['npm', 'install'],
                    cwd=PROJECT_ROOT,
                    capture_output=True, text=True, timeout=300,
                    shell=IS_WINDOWS
                )
                if install_proc.returncode != 0:
                    self.log(f"⚠️ npm install 有警告: {install_proc.stderr[:200]}", 'warning')
                else:
                    self.log("✅ 前端依赖安装完成", 'success')

            log_file_path = os.path.join(PROJECT_ROOT, 'frontend_output.log')
            self._frontend_log_file = open(log_file_path, 'w', encoding='utf-8')

            if IS_WINDOWS:
                self.frontend_process = subprocess.Popen(
                    ['npm', 'run', 'dev'],
                    cwd=PROJECT_ROOT,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    universal_newlines=True,
                    bufsize=1,
                    shell=True,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
                )
            else:
                self.frontend_process = subprocess.Popen(
                    ['npm', 'run', 'dev'],
                    cwd=PROJECT_ROOT,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    universal_newlines=True,
                    bufsize=1,
                )

            threading.Thread(
                target=self._drain_output,
                args=(self.frontend_process, '🎨', self._frontend_log_file),
                daemon=True
            ).start()

            for _ in range(60):
                time.sleep(1)
                try:
                    import urllib.request
                    with urllib.request.urlopen(
                        f'http://localhost:{FRONTEND_PORT}', timeout=2
                    ) as resp:
                        if resp.status == 200:
                            break
                except Exception:
                    pass
            else:
                self.log("⚠️ 前端启动可能较慢，继续等待…", 'warning')

            self._set_card_running('frontend')
            self._frontend_pid = self.frontend_process.pid
            self.log(f"✅ 前端服务启动成功 (http://localhost:{FRONTEND_PORT})", 'success')

        except Exception as e:
            self.log(f"❌ 前端启动失败: {e}", 'error')
            self._set_card_error('frontend', '❌ 启动失败')
            self.start_btn.config(state='normal')

    def _drain_output(self, proc, prefix, log_file=None):
        """消费子进程输出

        在后台线程中持续读取子进程 stdout，将每行输出到界面日志和可选的日志文件。
        proc 为子进程对象，prefix 为日志前缀标识，log_file 为可选的日志文件句柄。
        子进程异常退出时输出错误提示。
        """
        try:
            for line in proc.stdout:
                stripped = line.rstrip()
                if not stripped:
                    continue
                if log_file:
                    try:
                        log_file.write(line)
                        log_file.flush()
                    except Exception:
                        pass
                self.log(f"{prefix} {stripped}", 'info')
                if proc.poll() is not None:
                    break
        except Exception:
            pass
        if proc.poll() is not None and proc.poll() != 0:
            self.log(f"{prefix} 进程异常退出 (code={proc.returncode})", 'error')
        if log_file:
            try:
                log_file.close()
            except Exception:
                pass

    def _check_python_deps(self):
        """检查 Python 依赖

        读取后端 requirements.txt 并以 pip install -r 静默安装缺失的依赖包。
        """
        try:
            requirements = os.path.join(BACKEND_DIR, 'requirements.txt')
            if not os.path.isfile(requirements):
                return
            self.log("📦 检查 Python 依赖…", 'info')
            proc = subprocess.run(
                [sys.executable, '-m', 'pip', 'install', '-r', requirements, '-q'],
                capture_output=True, text=True, timeout=120
            )
            if proc.returncode == 0:
                self.log("✅ Python 依赖就绪", 'success')
            else:
                self.log(f"⚠️ 部分 Python 依赖可能缺失: {proc.stderr[:200]}", 'warning')
        except Exception as e:
            self.log(f"⚠️ Python 依赖检查失败: {e}", 'warning')

    def _kill_port(self, port, name):
        """终止占用指定端口的进程

        通过 netstat 查找监听指定端口的 PID，然后 taskkill 强制终止。
        port 为端口号，name 为服务名称（用于日志提示）。仅在 Windows 上有效。
        """
        try:
            result = subprocess.run(
                ['netstat', '-ano'],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode != 0:
                return
            pids = set()
            for line in result.stdout.splitlines():
                parts = line.split()
                if f':{port}' in line and 'LISTENING' in line:
                    pid = parts[-1]
                    if pid.isdigit():
                        pids.add(pid)
            for pid in pids:
                self.log(f"  终止 {name} (PID={pid})…", 'warning')
                subprocess.run(
                    ['taskkill', '/F', '/T', '/PID', pid],
                    capture_output=True, timeout=5
                )
        except Exception as e:
            self.log(f"  清理端口 {port} 失败: {e}", 'error')

    def stop_all_services(self):
        """停止所有服务

        按逆序停止前端、后端、Ollama 服务（跳过 MySQL），
        清理进程引用并恢复按钮状态。
        """
        self.log("⏹ 正在停止所有服务…", 'warning')
        self._auto_check_enabled = False

        for key in reversed(SERVICE_ORDER):
            if key == 'mysql':
                continue
            self._set_card_stopping(key)

        self._terminate_process('frontend', self.frontend_process, '🎨 前端服务')
        self._terminate_process('backend',  self.backend_process,  '📡 后端服务')
        self._terminate_process('ollama',   self.ollama_process,   '🤖 Ollama')

        self.backend_process = None
        self.frontend_process = None
        self.ollama_process = None

        self.start_btn.config(state='normal')
        self.stop_btn.config(state='disabled')
        self.log("✅ 所有服务已停止", 'success')
        self._auto_check_enabled = self.auto_check_var.get()

    def _terminate_process(self, card_key, proc, name):
        """终止指定进程

        card_key 为状态卡片键名，proc 为子进程对象，name 为服务名称（用于日志提示）。
        Windows 下使用 taskkill /F /T 强制终止进程树，其他平台使用 terminate()。
        """
        if proc and proc.poll() is None:
            try:
                if IS_WINDOWS:
                    subprocess.run(
                        ['taskkill', '/F', '/T', '/PID', str(proc.pid)],
                        capture_output=True, timeout=10
                    )
                else:
                    proc.terminate()
                    proc.wait(timeout=5)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
            self._set_card_stopped(card_key)
            self.log(f"{name} 已停止", 'warning')
        elif proc:
            self._set_card_stopped(card_key)

    def open_frontend(self):
        """打开前端页面

        在浏览器中打开前端页面。若后端未就绪则弹窗确认是否继续。
        """
        if not self.service_running.get('backend'):
            result = messagebox.askyesno(
                "提示",
                "后端 API 服务未启动，前端页面可能无法正常使用。\n\n是否仍要打开？"
            )
            if not result:
                self.log("已取消打开前端（后端未就绪）", 'warning')
                return

        url = f'http://localhost:{FRONTEND_PORT}'
        webbrowser.open(url)
        self.log(f"🌐 正在打开 {url}", 'info')

    def on_closing(self):
        """窗口关闭处理

        弹窗确认退出，确认后停止所有服务并销毁窗口。
        """
        if messagebox.askokcancel("退出", "确定要退出吗？\n所有正在运行的服务将被停止。"):
            self.stop_all_services()
            self.root.destroy()


if __name__ == '__main__':
    root = tk.Tk()
    app = ServiceLauncher(root)
    root.mainloop()
