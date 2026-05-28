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
    return pymysql.connect(**MYSQL_CONFIG, cursorclass=pymysql.cursors.DictCursor, charset='utf8mb4')


def ensure_users_table():
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
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')


def verify_password(password, password_hash):
    return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))


def generate_token(user_id, username, role, remember=False):
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
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def get_user_by_username(username):
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


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header[7:]

        if not token:
            return jsonify({'code': 401, 'message': '缺少认证令牌'}), 401

        payload = decode_token(token)
        if not payload:
            return jsonify({'code': 401, 'message': '令牌无效或已过期'}), 401

        user = get_user_by_id(payload['user_id'])
        if not user or not user.get('is_active'):
            return jsonify({'code': 401, 'message': '用户不存在或已禁用'}), 401

        request.current_user = {
            'user_id': user['id'],
            'username': user['username'],
            'role': user['role'],
            'avatar': user.get('avatar')
        }
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header[7:]

        if not token:
            return jsonify({'code': 401, 'message': '缺少认证令牌'}), 401

        payload = decode_token(token)
        if not payload:
            return jsonify({'code': 401, 'message': '令牌无效或已过期'}), 401

        user = get_user_by_id(payload['user_id'])
        if not user or not user.get('is_active'):
            return jsonify({'code': 401, 'message': '用户不存在或已禁用'}), 401

        if user['role'] != 'admin':
            return jsonify({'code': 403, 'message': '权限不足，需要管理员权限'}), 403

        request.current_user = {
            'user_id': user['id'],
            'username': user['username'],
            'role': user['role'],
            'avatar': user.get('avatar')
        }
        return f(*args, **kwargs)
    return decorated
