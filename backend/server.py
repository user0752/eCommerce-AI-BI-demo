"""
Flask API 服务器
为 Vue 前端提供 REST API 接口

功能：
  - 流式对话 (SSE)
  - 会话管理 CRUD
  - 审计日志记录
  - 管理后台数据闭环 API
"""
import json
import os
import re
import uuid
from contextlib import closing
from datetime import datetime
from flask import Flask, request, jsonify, Response, session
from flask_cors import CORS
import pymysql

from rag_chatbot import get_chatbot
from intent_parser import parse_question, IntentType
from config import MYSQL_CONFIG, AUDIT_LOG_TABLE
from auth import (
    ensure_users_table, get_user_by_username, create_user,
    verify_password, generate_token, decode_token,
    update_last_login, token_required, admin_required, USERS_TABLE
)

app = Flask(__name__)
app.secret_key = 'qian-shu-zhi-xi-ecommerce-session-secret-2025'
CORS(app, supports_credentials=True)

# 静态文件服务
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'uploads')
app.static_folder = app.config['UPLOAD_FOLDER']

# 会话存储目录
SESSIONS_DIR = os.path.join(os.path.dirname(__file__), '..', 'sessions')
os.makedirs(SESSIONS_DIR, exist_ok=True)


# ============================================================
#  工具函数
# ============================================================

def _get_log_connection():
    """获取审计日志数据库连接（独立连接，避免阻塞主连接）"""
    return pymysql.connect(**MYSQL_CONFIG, cursorclass=pymysql.cursors.DictCursor, charset='utf8mb4')


def _format_sse_event(event_type, content=None):
    """将事件类型和内容格式化为SSE data帧

    Args:
        event_type: 事件类型（thinking_start/thinking_content/thinking_end/content/error）
        content: 事件内容，thinking_start和thinking_end类型时为None

    Returns:
        str: 格式化后的SSE data帧字符串
    """
    event_data = {"type": event_type}
    if content is not None:
        event_data["content"] = content
    return f"data: {json.dumps(event_data, ensure_ascii=False)}\n\n"


def _resolve_response_status(intent_value):
    """根据意图类型确定响应状态（用于审计日志）"""
    if intent_value == "out_of_domain":
        return "fallback"
    if intent_value == "clarify":
        return "clarify"
    return "success"


def _execute_dashboard_query(sql, params=None):
    """执行大屏数据查询并自动序列化浮点数

    Args:
        sql: SQL查询语句
        params: SQL参数元组，无参数时为None

    Returns:
        list[dict] or dict: 查询结果（多行为列表，单行为字典）
    """
    with closing(_get_log_connection()) as conn:
        with closing(conn.cursor()) as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
            for row in rows:
                for col_key, col_val in row.items():
                    if hasattr(col_val, '__float__'):
                        row[col_key] = round(float(col_val), 2)
    return rows


def _generate_captcha_text(length=4):
    """生成验证码文本

    Args:
        length: 验证码字符长度，默认4

    Returns:
        str: 大写字母+数字组成的随机验证码
    """
    import random
    import string
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))


def _render_captcha_image(captcha_text):
    """将验证码文本渲染为PNG图片的base64编码

    Args:
        captcha_text: 验证码文本

    Returns:
        str: data:image/png;base64,... 格式的图片URI
    """
    import random
    from io import BytesIO
    from PIL import Image, ImageDraw, ImageFont
    import base64

    width, height = 120, 40
    image = Image.new('RGB', (width, height), (17, 29, 50))
    draw = ImageDraw.Draw(image)

    try:
        font = ImageFont.truetype("arial.ttf", 28)
    except Exception:
        font = ImageFont.load_default()

    for idx, char in enumerate(captcha_text):
        x = 10 + idx * 26
        y = random.randint(2, 8)
        color = (
            random.randint(100, 255),
            random.randint(150, 255),
            random.randint(200, 255)
        )
        draw.text((x, y), char, font=font, fill=color)

    for _ in range(3):
        x1 = random.randint(0, width)
        y1 = random.randint(0, height)
        x2 = random.randint(0, width)
        y2 = random.randint(0, height)
        draw.line([(x1, y1), (x2, y2)], fill=(60, 80, 120), width=1)

    for _ in range(30):
        px = random.randint(0, width)
        py = random.randint(0, height)
        draw.point((px, py), fill=(80, 100, 140))

    buffer = BytesIO()
    image.save(buffer, format='PNG')
    buffer.seek(0)
    captcha_base64 = base64.b64encode(buffer.read()).decode('utf-8')
    return f'data:image/png;base64,{captcha_base64}'


def _query_status_distribution(cur):
    """查询各状态的查询总数分布"""
    cur.execute(f"SELECT status, COUNT(*) as cnt FROM `{AUDIT_LOG_TABLE}` GROUP BY status")
    return {row['status']: row['cnt'] for row in cur.fetchall()}


def _query_today_stats(cur):
    """查询今日各状态的查询数分布"""
    cur.execute(
        f"SELECT status, COUNT(*) as cnt FROM `{AUDIT_LOG_TABLE}` WHERE DATE(created_at) = CURDATE() GROUP BY status"
    )
    return {row['status']: row['cnt'] for row in cur.fetchall()}


def _query_top_fallback(cur, limit=10):
    """查询兜底率最高的Top N问题"""
    cur.execute(
        f"SELECT query_text, COUNT(*) as cnt FROM `{AUDIT_LOG_TABLE}` WHERE status = 'fallback' GROUP BY query_text ORDER BY cnt DESC LIMIT %s",
        (limit,)
    )
    rows = cur.fetchall()
    for item in rows:
        item['query_text'] = item['query_text'][:100] if item['query_text'] else ''
    return rows


def _query_top_clarify(cur, limit=10):
    """查询澄清率最高的Top N问题"""
    cur.execute(
        f"SELECT query_text, COUNT(*) as cnt FROM `{AUDIT_LOG_TABLE}` WHERE status = 'clarify' GROUP BY query_text ORDER BY cnt DESC LIMIT %s",
        (limit,)
    )
    rows = cur.fetchall()
    for item in rows:
        item['query_text'] = item['query_text'][:100] if item['query_text'] else ''
    return rows


def _query_weekly_trend(cur):
    """查询近7天的查询趋势（按日期+状态分组）"""
    cur.execute(f"""
        SELECT DATE(created_at) as date, status, COUNT(*) as cnt
        FROM `{AUDIT_LOG_TABLE}` WHERE created_at >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
        GROUP BY DATE(created_at), status ORDER BY date
    """)
    rows = cur.fetchall()
    for item in rows:
        if item.get('date'):
            item['date'] = item['date'].strftime('%Y-%m-%d')
    return rows


def _ensure_audit_table():
    """确保审计日志表存在"""
    try:
        with closing(_get_log_connection()) as conn:
            with closing(conn.cursor()) as cur:
                cur.execute(f"""
                    CREATE TABLE IF NOT EXISTS `{AUDIT_LOG_TABLE}` (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        query_text TEXT CHARACTER SET utf8mb4,
                        intent VARCHAR(50),
                        tool_used VARCHAR(50),
                        status VARCHAR(20) COMMENT 'success / fallback / clarify',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        INDEX idx_status (status),
                        INDEX idx_created_at (created_at)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """)
                conn.commit()
        print(f"审计日志表 {AUDIT_LOG_TABLE} 已就绪")
    except Exception as e:
        print(f"创建审计日志表失败（非阻塞）: {e}")


def _write_audit_log(question, intent_value, status):
    """写入审计日志（失败不阻塞主流程）"""
    try:
        tool_used = "sql" if intent_value == "sql_query" else "rag"
        if intent_value == "clarify":
            tool_used = "clarify"
            status = "clarify"

        with closing(_get_log_connection()) as conn:
            with closing(conn.cursor()) as cur:
                cur.execute(
                    f"INSERT INTO `{AUDIT_LOG_TABLE}` (query_text, intent, tool_used, status) VALUES (%s, %s, %s, %s)",
                    (question, intent_value, tool_used, status)
                )
                conn.commit()
    except Exception:
        pass  # 日志写入失败不应阻塞主流程


def _find_session_file(session_id):
    """
    精确匹配会话文件（修复子字符串匹配 bug）。
    文件名格式：{timestamp}_{session_id}.json
    返回完整文件路径，未找到返回 None。
    """
    if not os.path.exists(SESSIONS_DIR):
        return None
    target = f"_{session_id}.json"
    for filename in os.listdir(SESSIONS_DIR):
        if filename.endswith(target):
            return os.path.join(SESSIONS_DIR, filename)
    return None


# 启动时自动确保审计表和用户表存在
_ensure_audit_table()
ensure_users_table()


# ============================================================
#  核心对话接口
# ============================================================

@app.route('/api/status', methods=['GET'])
def check_status():
    """检查后端服务状态"""
    try:
        chatbot = get_chatbot()
        return jsonify({
            'status': 'ok',
            'message': '后端服务正常运行',
            'vector_db_loaded': getattr(chatbot, '_vector_db_loaded', False)
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': '服务启动中，请稍候...'
        }), 503


@app.route('/api/chat/stream', methods=['POST'])
def stream_chat():
    """流式对话接口 (SSE)"""
    data = request.get_json()
    question = data.get('question', '').strip()
    # 不使用对话历史，每次查询独立处理（核心是单次查询→图表输出，非多轮推理）

    if not question:
        return jsonify({'error': '问题不能为空'}), 400

    # 解析意图（仅一次，结果传给 chatbot 避免重复解析）
    parse_result = None
    try:
        parse_result = parse_question(question)
        intent_value = parse_result.intent.value
    except Exception:
        intent_value = "unknown"

    def generate():
        response_status = "success"
        try:
            chatbot = get_chatbot()

            for chunk in chatbot.stream_ask(question, pre_parsed=parse_result):
                if chunk == "__THINKING_START__":
                    yield _format_sse_event("thinking_start")
                elif chunk.startswith("__THINKING_CONTENT__"):
                    thinking_content = chunk.replace("__THINKING_CONTENT__", "")
                    yield _format_sse_event("thinking_content", thinking_content)
                elif chunk == "__THINKING_END__":
                    yield _format_sse_event("thinking_end")
                else:
                    yield _format_sse_event("content", chunk)

            response_status = _resolve_response_status(intent_value)

        except Exception as e:
            print(f"流式对话错误: {e}")
            yield _format_sse_event("error", "服务器处理请求时出错，请稍后重试。")
            response_status = "fallback"

        _write_audit_log(question, intent_value, response_status)
        yield "data: [DONE]\n\n"

    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no'
        }
    )


# ============================================================
#  会话管理接口
# ============================================================

@app.route('/api/sessions', methods=['GET'])
def get_sessions():
    """获取所有会话列表"""
    try:
        sessions = []
        if os.path.exists(SESSIONS_DIR):
            for filename in os.listdir(SESSIONS_DIR):
                if filename.endswith('.json'):
                    filepath = os.path.join(SESSIONS_DIR, filename)
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        sessions.append({
                            'id': data.get('id', filename.replace('.json', '')),
                            'name': data.get('timestamp', filename.replace('.json', '')),
                            'timestamp': data.get('timestamp', ''),
                            'messageCount': len(data.get('messages', [])),
                            'lastMessage': data.get('messages', [{}])[-1].get('content', '')[:50] if data.get('messages') else ''
                        })
                    except Exception:
                        continue

        sessions.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        return jsonify({'sessions': sessions})

    except Exception as e:
        return jsonify({'error': '加载会话列表失败'}), 500


@app.route('/api/sessions', methods=['POST'])
def create_session():
    """创建新会话"""
    try:
        data = request.get_json()
        session_id = str(uuid.uuid4())[:8]
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
        filename = f"{timestamp}_{session_id}.json"
        filepath = os.path.join(SESSIONS_DIR, filename)

        session_data = {
            'id': session_id,
            'timestamp': timestamp,
            'messages': data.get('messages', [])
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(session_data, f, ensure_ascii=False, indent=2)

        return jsonify({'id': session_id, 'timestamp': timestamp})

    except Exception as e:
        return jsonify({'error': '创建会话失败'}), 500


@app.route('/api/sessions/<session_id>', methods=['GET'])
def get_session(session_id):
    """获取指定会话内容"""
    try:
        filepath = _find_session_file(session_id)
        if not filepath:
            return jsonify({'error': '会话不存在'}), 404

        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return jsonify(data)

    except Exception as e:
        return jsonify({'error': '读取会话失败'}), 500


@app.route('/api/sessions/<session_id>', methods=['PUT'])
def update_session(session_id):
    """更新指定会话内容"""
    try:
        filepath = _find_session_file(session_id)
        if not filepath:
            return jsonify({'error': '会话不存在'}), 404

        data = request.get_json()
        with open(filepath, 'r', encoding='utf-8') as f:
            session_data = json.load(f)

        session_data['messages'] = data.get('messages', [])
        session_data['timestamp'] = datetime.now().strftime("%Y-%m-%d_%H-%M")

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(session_data, f, ensure_ascii=False, indent=2)

        return jsonify({'status': 'ok'})

    except Exception as e:
        return jsonify({'error': '更新会话失败'}), 500


@app.route('/api/sessions/<session_id>', methods=['DELETE'])
def delete_session(session_id):
    """删除指定会话"""
    try:
        filepath = _find_session_file(session_id)
        if not filepath:
            return jsonify({'error': '会话不存在'}), 404

        os.remove(filepath)
        return jsonify({'status': 'ok'})

    except Exception as e:
        return jsonify({'error': '删除会话失败'}), 500


# ============================================================
#  � 用户认证 API
# ============================================================

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    username = (data.get('username') or '').strip()
    password = (data.get('password') or '').strip()
    captcha_input = (data.get('captcha') or '').strip().lower()
    remember = data.get('remember', False)

    if not username or not password:
        return jsonify({'code': 400, 'message': '用户名和密码不能为空'}), 400

    session_captcha = session.get('captcha_text', '')
    if not captcha_input or captcha_input != session_captcha.lower():
        return jsonify({'code': 400, 'message': '验证码错误'}), 400

    user = get_user_by_username(username)
    if not user:
        return jsonify({'code': 401, 'message': '用户名或密码错误'}), 401

    if not user.get('is_active'):
        return jsonify({'code': 403, 'message': '账户已被禁用，请联系管理员'}), 403

    if not verify_password(password, user['password_hash']):
        return jsonify({'code': 401, 'message': '用户名或密码错误'}), 401

    update_last_login(user['id'])

    token = generate_token(user['id'], user['username'], user['role'], remember=remember)

    return jsonify({
        'code': 200,
        'message': '登录成功',
        'data': {
            'token': token,
            'user': {
                'id': user['id'],
                'username': user['username'],
                'role': user['role']
            }
        }
    })


@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.get_json()
    username = (data.get('username') or '').strip()
    password = (data.get('password') or '').strip()
    confirm_password = (data.get('confirm_password') or '').strip()
    captcha_input = (data.get('captcha') or '').strip().lower()

    if not username or not password:
        return jsonify({'code': 400, 'message': '用户名和密码不能为空'}), 400

    if len(username) < 3 or len(username) > 20:
        return jsonify({'code': 400, 'message': '用户名长度需在3-20个字符之间'}), 400

    if len(password) < 6:
        return jsonify({'code': 400, 'message': '密码长度不能少于6个字符'}), 400

    if password != confirm_password:
        return jsonify({'code': 400, 'message': '两次输入的密码不一致'}), 400

    session_captcha = session.get('captcha_text', '')
    if not captcha_input or captcha_input != session_captcha.lower():
        return jsonify({'code': 400, 'message': '验证码错误'}), 400

    existing = get_user_by_username(username)
    if existing:
        return jsonify({'code': 409, 'message': '用户名已存在'}), 409

    user_id = create_user(username, password, role='user')
    if not user_id:
        return jsonify({'code': 500, 'message': '注册失败，请稍后重试'}), 500

    token = generate_token(user_id, username, 'user')

    return jsonify({
        'code': 200,
        'message': '注册成功',
        'data': {
            'token': token,
            'user': {
                'id': user_id,
                'username': username,
                'role': 'user'
            }
        }
    })


@app.route('/api/auth/captcha', methods=['GET'])
def get_captcha():
    """获取验证码（图片或文本）"""
    captcha_text = _generate_captcha_text()
    session['captcha_text'] = captcha_text

    try:
        captcha_image_uri = _render_captcha_image(captcha_text)
        return jsonify({
            'code': 200,
            'data': {
                'captcha': captcha_image_uri
            }
        })
    except ImportError:
        return jsonify({
            'code': 200,
            'data': {
                'captcha_text': captcha_text
            }
        })


@app.route('/api/auth/me', methods=['GET'])
@token_required
def get_current_user():
    user = request.current_user
    return jsonify({
        'code': 200,
        'data': {
            'user': user
        }
    })


@app.route('/api/auth/change-password', methods=['POST'])
@token_required
def change_password():
    data = request.get_json()
    old_password = (data.get('old_password') or '').strip()
    new_password = (data.get('new_password') or '').strip()

    if not old_password or not new_password:
        return jsonify({'code': 400, 'message': '原密码和新密码不能为空'}), 400

    if len(new_password) < 6:
        return jsonify({'code': 400, 'message': '新密码长度不能少于6个字符'}), 400

    user = get_user_by_username(request.current_user['username'])
    if not user or not verify_password(old_password, user['password_hash']):
        return jsonify({'code': 401, 'message': '原密码错误'}), 401

    from auth import hash_password
    try:
        with closing(_get_log_connection()) as conn:
            with closing(conn.cursor()) as cur:
                new_hash = hash_password(new_password)
                cur.execute(
                    f"UPDATE `{USERS_TABLE}` SET password_hash = %s WHERE id = %s",
                    (new_hash, request.current_user['user_id'])
                )
                conn.commit()
        return jsonify({'code': 200, 'message': '密码修改成功'})
    except Exception:
        return jsonify({'code': 500, 'message': '密码修改失败'}), 500


@app.route('/api/auth/upload-avatar', methods=['POST'])
@token_required
def upload_avatar():
    """上传头像"""
    try:
        if 'avatar' not in request.files:
            return jsonify({'code': 400, 'message': '请选择要上传的头像文件'}), 400

        file = request.files['avatar']
        if file.filename == '':
            return jsonify({'code': 400, 'message': '请选择要上传的头像文件'}), 400

        # 验证文件类型
        allowed_extensions = {'png', 'jpg', 'jpeg', 'webp'}
        if '.' not in file.filename or file.filename.rsplit('.', 1)[1].lower() not in allowed_extensions:
            return jsonify({'code': 400, 'message': '只支持上传png、jpg、jpeg、webp格式的图片'}), 400

        # 验证文件大小（2MB）
        if file.content_length > 2 * 1024 * 1024:
            return jsonify({'code': 400, 'message': '头像文件大小不能超过2MB'}), 400

        # 生成唯一文件名
        import uuid
        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = f"{uuid.uuid4()}.{ext}"

        # 保存文件
        uploads_dir = os.path.join(os.path.dirname(__file__), 'uploads', 'avatars')
        os.makedirs(uploads_dir, exist_ok=True)
        filepath = os.path.join(uploads_dir, filename)
        file.save(filepath)

        # 更新用户头像URL
        avatar_url = f"/uploads/avatars/{filename}"
        with closing(_get_log_connection()) as conn:
            with closing(conn.cursor()) as cur:
                cur.execute(
                    f"UPDATE `{USERS_TABLE}` SET avatar = %s WHERE id = %s",
                    (avatar_url, request.current_user['user_id'])
                )
                conn.commit()

        return jsonify({
            'code': 200,
            'message': '头像上传成功',
            'data': {
                'avatar_url': avatar_url
            }
        })
    except Exception as e:
        print(f"上传头像失败: {e}")
        return jsonify({'code': 500, 'message': '头像上传失败，请稍后重试'}), 500


@app.route('/api/auth/update-profile', methods=['POST'])
@token_required
def update_profile():
    """更新用户信息"""
    data = request.get_json()
    username = (data.get('username') or '').strip()

    if not username:
        return jsonify({'code': 400, 'message': '用户名不能为空'}), 400

    if len(username) < 3 or len(username) > 20:
        return jsonify({'code': 400, 'message': '用户名长度需在3-20个字符之间'}), 400

    # 检查用户名是否已被使用
    existing = get_user_by_username(username)
    if existing and existing['id'] != request.current_user['user_id']:
        return jsonify({'code': 409, 'message': '用户名已存在'}), 409

    try:
        with closing(_get_log_connection()) as conn:
            with closing(conn.cursor()) as cur:
                cur.execute(
                    f"UPDATE `{USERS_TABLE}` SET username = %s WHERE id = %s",
                    (username, request.current_user['user_id'])
                )
                conn.commit()

        return jsonify({
            'code': 200,
            'message': '用户信息更新成功',
            'data': {
                'username': username
            }
        })
    except Exception:
        return jsonify({'code': 500, 'message': '用户信息更新失败，请稍后重试'}), 500


@app.route('/api/admin/users', methods=['GET'])
@admin_required
def get_users():
    try:
        with closing(_get_log_connection()) as conn:
            with closing(conn.cursor()) as cur:
                cur.execute(f"SELECT id, username, role, is_active, created_at, last_login_at FROM `{USERS_TABLE}` ORDER BY id")
                users = cur.fetchall()
                for user in users:
                    if user.get('created_at'):
                        user['created_at'] = user['created_at'].strftime('%Y-%m-%d %H:%M:%S')
                    if user.get('last_login_at'):
                        user['last_login_at'] = user['last_login_at'].strftime('%Y-%m-%d %H:%M:%S')
        return jsonify({'code': 200, 'data': {'users': users}})
    except Exception:
        return jsonify({'code': 500, 'message': '查询用户列表失败'}), 500


@app.route('/api/admin/users/<int:user_id>/toggle-active', methods=['PUT'])
@admin_required
def toggle_user_active(user_id):
    try:
        with closing(_get_log_connection()) as conn:
            with closing(conn.cursor()) as cur:
                cur.execute(f"SELECT role, is_active FROM `{USERS_TABLE}` WHERE id = %s", (user_id,))
                user = cur.fetchone()
                if not user:
                    return jsonify({'code': 404, 'message': '用户不存在'}), 404
                if user['role'] == 'admin':
                    return jsonify({'code': 403, 'message': '不能禁用管理员账户'}), 403
                new_status = 0 if user['is_active'] else 1
                cur.execute(f"UPDATE `{USERS_TABLE}` SET is_active = %s WHERE id = %s", (new_status, user_id))
                conn.commit()
        return jsonify({'code': 200, 'message': '用户状态已更新'})
    except Exception:
        return jsonify({'code': 500, 'message': '操作失败'}), 500


# ============================================================
#  �� 管理后台 API（数据闭环）
# ============================================================

@app.route('/api/admin/audit-logs', methods=['GET'])
def get_audit_logs():
    """
    获取审计日志列表
    参数：
      - status: 过滤状态 (success / fallback / clarify)，默认返回全部
      - limit: 返回条数，默认 100
    """
    try:
        status_filter = request.args.get('status', '')
        limit = min(int(request.args.get('limit', 100)), 500)

        with closing(_get_log_connection()) as conn:
            with closing(conn.cursor()) as cur:
                if status_filter:
                    cur.execute(
                        f"SELECT * FROM `{AUDIT_LOG_TABLE}` WHERE status = %s ORDER BY created_at DESC LIMIT %s",
                        (status_filter, limit)
                    )
                else:
                    cur.execute(
                        f"SELECT * FROM `{AUDIT_LOG_TABLE}` ORDER BY created_at DESC LIMIT %s",
                        (limit,)
                    )

                logs = cur.fetchall()
                for log in logs:
                    if log.get('created_at'):
                        log['created_at'] = log['created_at'].strftime('%Y-%m-%d %H:%M:%S')

        return jsonify({"logs": logs})

    except Exception as e:
        return jsonify({"error": "查询审计日志失败"}), 500


@app.route('/api/admin/fence/metrics', methods=['GET'])
def fence_metrics():
    """
    数据围栏指标
    返回：总查询数、各状态分布、兜底率、近期趋势
    """
    try:
        with closing(_get_log_connection()) as conn:
            with closing(conn.cursor()) as cur:
                stats = _query_status_distribution(cur)
                total = sum(stats.values())
                today_stats = _query_today_stats(cur)
                top_fallback = _query_top_fallback(cur)
                top_clarify = _query_top_clarify(cur)
                trend = _query_weekly_trend(cur)

        return jsonify({
            "total_queries": total,
            "fallback_rate": round(stats.get('fallback', 0) / max(total, 1) * 100, 2),
            "clarify_rate": round(stats.get('clarify', 0) / max(total, 1) * 100, 2),
            "success_rate": round(stats.get('success', 0) / max(total, 1) * 100, 2),
            "status_distribution": stats,
            "today_distribution": today_stats,
            "top_fallback_questions": top_fallback,
            "top_clarify_questions": top_clarify,
            "weekly_trend": trend,
        })

    except Exception as e:
        return jsonify({"error": "查询围栏指标失败"}), 500


@app.route('/api/admin/knowledge/gaps', methods=['GET'])
def knowledge_gaps():
    """
    知识缺口分析 —— 识别需要补充知识的领域
    返回所有 fallback + clarify 记录，用于管理员标记待补充知识
    """
    try:
        with closing(_get_log_connection()) as conn:
            with closing(conn.cursor()) as cur:
                cur.execute(
                    f"SELECT id, query_text, intent, status, created_at FROM `{AUDIT_LOG_TABLE}` "
                    f"WHERE status IN ('fallback', 'clarify') ORDER BY created_at DESC LIMIT 200"
                )
                gaps = cur.fetchall()
                for item in gaps:
                    if item.get('created_at'):
                        item['created_at'] = item['created_at'].strftime('%Y-%m-%d %H:%M:%S')
                    item['query_text'] = item['query_text'][:200] if item['query_text'] else ''

        return jsonify({"gaps": gaps})

    except Exception as e:
        return jsonify({"error": "查询知识缺口失败"}), 500


# ============================================================
#  📊 可视化大屏 API（四张 ADS 层表数据）
# ============================================================

@app.route('/api/dashboard/region_consume', methods=['GET'])
def dashboard_region_consume():
    """区域消费分析数据 - 按城市聚合"""
    try:
        rows = _execute_dashboard_query("""
            SELECT city_name,
                   SUM(total_active_user) as total_active_user,
                   SUM(total_pay_user) as total_pay_user,
                   ROUND(SUM(total_pay_user) / SUM(total_active_user), 4) as total_pay_rate,
                   SUM(total_order_count) as total_order_count,
                   SUM(total_sale_amount) as total_sale_amount,
                   AVG(city_avg_order_value) as city_avg_order_value,
                   AVG(main_category_avg_price) as main_category_avg_price,
                   MAX(main_consume_category) as main_consume_category,
                   MAX(main_consume_brand) as main_consume_brand
            FROM ads_region_consume_analysis
            GROUP BY city_name
            ORDER BY total_sale_amount DESC
        """)
        return jsonify({"data": rows})
    except Exception as e:
        return jsonify({"error": f"查询区域消费数据失败: {e}"}), 500


@app.route('/api/dashboard/product_feature', methods=['GET'])
def dashboard_product_feature():
    """商品特征数据 - 按品类聚合"""
    try:
        rows = _execute_dashboard_query("""
            SELECT product_category,
                   SUM(total_sale_quantity) as total_sale_quantity,
                   SUM(total_sale_amount) as total_sale_amount,
                   AVG(buy_conversion_rate) as buy_conversion_rate,
                   AVG(product_rating) as product_rating
            FROM ads_product_feature_full
            GROUP BY product_category
            ORDER BY total_sale_amount DESC
        """)
        return jsonify({"data": rows})
    except Exception as e:
        return jsonify({"error": f"查询商品特征数据失败: {e}"}), 500


@app.route('/api/dashboard/user_profile', methods=['GET'])
def dashboard_user_profile():
    """用户画像数据 - 按年龄段/性别/城市聚合"""
    try:
        age_data = _execute_dashboard_query("""
            SELECT age_group,
                   COUNT(*) as user_count,
                   AVG(total_consumption) as avg_consumption,
                   AVG(avg_order_value) as avg_order_value,
                   AVG(repurchase_count) as avg_repurchase
            FROM ads_user_profile_full
            GROUP BY age_group
            ORDER BY avg_consumption DESC
        """)
        gender_data = _execute_dashboard_query("""
            SELECT user_gender,
                   COUNT(*) as user_count,
                   AVG(total_consumption) as avg_consumption
            FROM ads_user_profile_full
            GROUP BY user_gender
        """)
        city_data = _execute_dashboard_query("""
            SELECT user_city,
                   COUNT(*) as user_count,
                   AVG(total_consumption) as avg_consumption
            FROM ads_user_profile_full
            GROUP BY user_city
            ORDER BY avg_consumption DESC
        """)

        return jsonify({
            "data": {
                "age_data": age_data,
                "gender_data": gender_data,
                "city_data": city_data
            }
        })
    except Exception as e:
        return jsonify({"error": f"查询用户画像数据失败: {e}"}), 500


@app.route('/api/dashboard/interaction', methods=['GET'])
def dashboard_interaction():
    """用户-商品交互数据 - 按月份聚合趋势"""
    try:
        trend_data = _execute_dashboard_query("""
            SELECT stat_month,
                   SUM(pv_count) as pv_count,
                   SUM(fav_count) as fav_count,
                   SUM(cart_count) as cart_count,
                   SUM(buy_count) as buy_count,
                   AVG(interaction_score) as avg_interaction_score
            FROM ads_user_item_interaction_matrix
            GROUP BY stat_month
            ORDER BY stat_month
        """)
        funnel_rows = _execute_dashboard_query("""
            SELECT SUM(pv_count) as total_pv,
                   SUM(fav_count) as total_fav,
                   SUM(cart_count) as total_cart,
                   SUM(buy_count) as total_buy
            FROM ads_user_item_interaction_matrix
        """)
        funnel_data = funnel_rows[0] if funnel_rows else None

        return jsonify({
            "data": {
                "trend_data": trend_data,
                "funnel_data": funnel_data
            }
        })
    except Exception as e:
        return jsonify({"error": f"查询交互数据失败: {e}"}), 500


if __name__ == '__main__':
    print("=" * 60)
    print("  区域电商智能数据分析助手 - 后端服务")
    print("  API地址: http://localhost:5000")
    print("=" * 60)
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
