"""
统一配置管理
所有模块共享的配置项集中在此管理，避免硬编码散落各处。
"""
import os

# 项目根目录（backend/ 的上一级）
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# MySQL 数据库配置
MYSQL_CONFIG = {
    'host': os.environ.get('DB_HOST', 'localhost'),
    'port': int(os.environ.get('DB_PORT', '3306')),
    'user': os.environ.get('DB_USER', 'root'),
    'password': os.environ.get('DB_PASSWORD', '201711'),
    'database': os.environ.get('DB_NAME', 'ecommerce'),
}

# 向量数据库路径（绝对路径，避免工作目录漂移）
VECTOR_DB_PATH = os.path.join(_PROJECT_ROOT, 'vector_db')
VECTOR_DB_FINGERPRINT_PATH = os.path.join(VECTOR_DB_PATH, '.fingerprint')

# LLM 模型配置
MODEL_NAME = os.environ.get('LLM_MODEL', 'qwen3:8b')

# HuggingFace 镜像站（国内加速）
HF_ENDPOINT = os.environ.get('HF_ENDPOINT', 'https://hf-mirror.com')

# 知识文档目录（绝对路径）
KNOWLEDGE_DOCS_DIR = os.path.join(os.path.dirname(__file__), 'knowledge_docs')

# RAG 检索参数
RAG_TOP_K = int(os.environ.get('RAG_TOP_K', '12'))
RAG_CHUNK_SIZE = int(os.environ.get('RAG_CHUNK_SIZE', '600'))
RAG_CHUNK_OVERLAP = int(os.environ.get('RAG_CHUNK_OVERLAP', '80'))
RAG_MAX_DOCUMENTS = int(os.environ.get('RAG_MAX_DOCUMENTS', '2000'))

# Embedding 模型名（统一管理，避免硬编码散落各处）
EMBEDDING_MODEL = os.environ.get('EMBEDDING_MODEL', 'BAAI/bge-small-zh-v1.5')

# 审计日志配置
AUDIT_LOG_TABLE = 'ai_audit_log'
