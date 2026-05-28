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
        card = self.status_cards[key]
        card['status'].config(text=text, bg=bg_color, fg=fg_color)
        card['icon'].config(text=icon)

    def _set_card_starting(self, key):
        self.service_starting[key] = True
        self._update_card(key, '⏳ 启动中…', '#faad14', 'white', '🟡')

    def _set_card_stopping(self, key):
        self._update_card(key, '⏳ 停止中…', '#d9d9d9', '#666', '⚪')

    def _set_card_running(self, key):
        self.service_running[key] = True
        self.service_starting[key] = False
        self._update_card(key, '✅ 运行中', '#52c41a', 'white', '🟢')

    def _set_card_stopped(self, key):
        self.service_running[key] = False
        self.service_starting[key] = False
        self._update_card(key, '⏸ 未启动', '#faad14', 'white', '⚪')

    def _set_card_error(self, key, text='❌ 异常'):
        self.service_running[key] = False
        self.service_starting[key] = False
        self._update_card(key, text, '#ff4d4f', 'white', '🔴')

    def _build_control_buttons(self, parent):
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
        ts = datetime.now().strftime('%H:%M:%S')
        self.log_text.insert(tk.END, f"[{ts}] {message}\n", tag)
        line_count = int(self.log_text.index('end-1c').split('.')[0])
        if line_count > MAX_LOG_LINES + 50:
            self.log_text.delete('1.0', f'{line_count - MAX_LOG_LINES}.0')
        self.log_text.see(tk.END)

    def _clear_log(self):
        self.log_text.delete('1.0', tk.END)
        self.log("日志已清空", 'info')

    def _export_log(self):
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
        self._auto_check_enabled = self.auto_check_var.get()
        if self._auto_check_enabled:
            self.log(f"自动检测已开启（每{AUTO_CHECK_INTERVAL}秒）", 'info')
        else:
            self.log("自动检测已关闭", 'warning')

    def _auto_check_loop(self):
        if self._auto_check_enabled:
            threading.Thread(target=self._do_silent_check, daemon=True).start()
        self.root.after(AUTO_CHECK_INTERVAL * 1000, self._auto_check_loop)

    def _do_silent_check(self):
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
        threading.Thread(target=self._do_initial_check, daemon=True).start()

    def _do_initial_check(self):
        self.log("正在检测服务状态…", 'info')
        self._check_mysql()
        self._check_ollama()
        self._check_backend()
        self._check_frontend()
        self.start_btn.config(state='normal')

    def check_all_services(self):
        threading.Thread(target=self._do_check_all, daemon=True).start()

    def _do_check_all(self):
        self.log("正在检测服务状态…", 'info')
        self._check_mysql()
        self._check_ollama()
        self._check_backend()
        self._check_frontend()

    def _check_ollama(self):
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
        hardcoded = r'C:\Users\86175\AppData\Local\Programs\Ollama\ollama.exe'
        if os.path.isfile(hardcoded):
            return hardcoded
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
        if messagebox.askokcancel("退出", "确定要退出吗？\n所有正在运行的服务将被停止。"):
            self.stop_all_services()
            self.root.destroy()


if __name__ == '__main__':
    root = tk.Tk()
    app = ServiceLauncher(root)
    root.mainloop()
