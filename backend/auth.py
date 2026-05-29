"""
JWT 认证模块
提供用户注册、登录、Token 验证、权限控制等功能
"""
import jwt
import bcrypt
import pymysql
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify, current_app
from config import MYSQL_CONFIG

JWT_SECRET = 'qian-shu-zhi-xi-ecommerce-2025-jwt-secret-key'
JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION_HOURS = 24
JWT_REMEMBER_DAYS = 7

USERS_TABLE = 'users'


def _get_auth_connection():
    """获取认证模块的数据库连接

    Returns:
        pymysql.connections.Connection: 使用字典游标的数据库连接对象
    """
    return pymysql.connect(**MYSQL_CONFIG, cursorclass=pymysql.cursors.DictCursor, charset='utf8mb4')


def ensure_users_table():
    """确保用户表存在，若不存在则自动创建

    创建包含 id、username、password_hash、role、is_active、created_at、last_login_at 字段的用户表，
    并建立 username 和 role 的索引。创建失败时仅打印错误，不抛出异常（非阻塞）。
    """
    try:
        conn = _get_auth_connection()
        cur = conn.cursor()
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS `{USERS_TABLE}` (
                `id` INT AUTO_INCREMENT PRIMARY KEY,
                `username` VARCHAR(50) NOT NULL UNIQUE,
                `password_hash` VARCHAR(255) NOT NULL,
                `role` VARCHAR(20) NOT NULL DEFAULT 'user',
                `is_active` TINYINT(1) NOT NULL DEFAULT 1,
                `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                `last_login_at` TIMESTAMP NULL,
                INDEX `idx_username` (`username`),
                INDEX `idx_role` (`role`)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        conn.commit()
        cur.close()
        conn.close()
        print(f"用户表 {USERS_TABLE} 已就绪")
    except Exception as e:
        print(f"创建用户表失败（非阻塞）: {e}")


def hash_password(password):
    """对明文密码进行bcrypt哈希

    Args:
        password: 明文密码字符串

    Returns:
        str: bcrypt哈希后的密码字符串
    """
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')


def verify_password(password, password_hash):
    """验证明文密码与哈希是否匹配

    Args:
        password: 明文密码字符串
        password_hash: bcrypt哈希后的密码字符串

    Returns:
        bool: 密码匹配返回 True，否则返回 False
    """
    return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))


def generate_token(user_id, username, role, remember=False):
    """生成JWT令牌

    Args:
        user_id: 用户ID
        username: 用户名
        role: 用户角色（如 'user'、'admin'）
        remember: 是否记住登录，为 True 时有效期延长至 JWT_REMEMBER_DAYS 天，默认 False 即 JWT_EXPIRATION_HOURS 小时

    Returns:
        str: 编码后的JWT令牌字符串
    """
    expiration = timedelta(days=JWT_REMEMBER_DAYS) if remember else timedelta(hours=JWT_EXPIRATION_HOURS)
    payload = {
        'user_id': user_id,
        'username': username,
        'role': role,
        'exp': datetime.utcnow() + expiration,
        'iat': datetime.utcnow()
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token):
    """解码并验证JWT令牌

    Args:
        token: JWT令牌字符串

    Returns:
        dict | None: 令牌有效时返回解码后的载荷字典，令牌过期或无效时返回 None
    """
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def get_user_by_username(username):
    """根据用户名查询用户

    Args:
        username: 用户名字符串

    Returns:
        dict | None: 找到用户时返回用户信息字典（含所有字段），未找到或异常时返回 None
    """
    try:
        conn = _get_auth_connection()
        cur = conn.cursor()
        cur.execute(f"SELECT * FROM `{USERS_TABLE}` WHERE username = %s", (username,))
        user = cur.fetchone()
        cur.close()
        conn.close()
        return user
    except Exception:
        return None


def get_user_by_id(user_id):
    """根据用户ID查询用户

    Args:
        user_id: 用户ID（整数）

    Returns:
        dict | None: 找到用户时返回用户信息字典（含所有字段），未找到或异常时返回 None
    """
    try:
        conn = _get_auth_connection()
        cur = conn.cursor()
        cur.execute(f"SELECT * FROM `{USERS_TABLE}` WHERE id = %s", (user_id,))
        user = cur.fetchone()
        cur.close()
        conn.close()
        return user
    except Exception:
        return None


def create_user(username, password, role='user'):
    """创建新用户

    Args:
        username: 用户名字符串，需唯一
        password: 明文密码字符串，将自动进行bcrypt哈希后存储
        role: 用户角色，默认为 'user'

    Returns:
        int | None: 创建成功返回新用户ID，用户名重复（IntegrityError）或其他异常时返回 None
    """
    try:
        conn = _get_auth_connection()
        cur = conn.cursor()
        password_hash = hash_password(password)
        cur.execute(
            f"INSERT INTO `{USERS_TABLE}` (username, password_hash, role) VALUES (%s, %s, %s)",
            (username, password_hash, role)
        )
        conn.commit()
        user_id = cur.lastrowid
        cur.close()
        conn.close()
        return user_id
    except pymysql.err.IntegrityError:
        return None
    except Exception:
        return None


def update_last_login(user_id):
    """更新用户最后登录时间为当前时刻

    Args:
        user_id: 用户ID（整数）

    更新失败时静默忽略，不抛出异常。
    """
    try:
        conn = _get_auth_connection()
        cur = conn.cursor()
        cur.execute(
            f"UPDATE `{USERS_TABLE}` SET last_login_at = NOW() WHERE id = %s",
            (user_id,)
        )
        conn.commit()
        cur.close()
        conn.close()
    except Exception:
        pass


def _extract_and_validate_token():
    """从请求头提取并验证JWT Token

    Returns:
        tuple: (error_response, user_info)
        - 验证失败时: error_response 为 (jsonify响应, 状态码)，user_info 为 None
        - 验证成功时: error_response 为 None，user_info 为用户信息字典
    """
    token = None
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        token = auth_header[7:]

    if not token:
        return (jsonify({'code': 401, 'message': '缺少认证令牌'}), 401), None

    payload = decode_token(token)
    if not payload:
        return (jsonify({'code': 401, 'message': '令牌无效或已过期'}), 401), None

    user = get_user_by_id(payload['user_id'])
    if not user or not user.get('is_active'):
        return (jsonify({'code': 401, 'message': '用户不存在或已禁用'}), 401), None

    user_info = {
        'user_id': user['id'],
        'username': user['username'],
        'role': user['role'],
        'avatar': user.get('avatar')
    }
    return None, user_info


def token_required(f):
    """要求有效JWT令牌的装饰器

    验证请求头中的Bearer Token，成功时将用户信息设置到 request.current_user，
    失败时返回 401 错误响应。

    Args:
        f: 被装饰的视图函数
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        error_response, user_info = _extract_and_validate_token()
        if error_response:
            return error_response
        request.current_user = user_info
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    """要求管理员权限的装饰器

    验证请求头中的Bearer Token，并检查用户角色是否为 admin。
    成功时将用户信息设置到 request.current_user，
    Token无效时返回 401，权限不足时返回 403。

    Args:
        f: 被装饰的视图函数
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        error_response, user_info = _extract_and_validate_token()
        if error_response:
            return error_response
        if user_info['role'] != 'admin':
            return jsonify({'code': 403, 'message': '权限不足，需要管理员权限'}), 403
        request.current_user = user_info
        return f(*args, **kwargs)
    return decorated
