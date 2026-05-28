# 黔数智析 - 区域电商智能数据分析助手

> 基于离线数仓与本地大模型的贵州电商数据分析助手，采用 Vue 3 + Flask 前后端分离架构，包含 GUI 启动管理器。

## 技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| 前端 | Vue 3 + Vite | 现代化响应式UI |
| 后端 | Flask + SSE | REST API + 流式传输 |
| AI模型 | Ollama (qwen3:8b) | 本地大语言模型 |
| 向量数据库 | Chroma | 本地向量存储 |
| 关系数据库 | MySQL | 电商业务数据 |

## 功能特性

- 🔐 用户认证系统（登录/注册/登出）
- 🎨 GUI 启动管理器（服务状态监测、一键启动/停止）
- ✅ 智能意图识别（SQL查询 / RAG检索 / 多轮澄清 / 域外拒绝）
- ✅ 多轮澄清对话（信息不足时主动追问城市、时间等关键信息）
- ✅ 流式对话输出，实时显示AI思考过程
- ✅ AI 自动生成可视化图表（柱状图、折线图、饼图）
- ✅ 动态表结构注册（新增数据表只需在 `TABLE_SCHEMA` 注册）
- ✅ SQL 安全熔断（白名单字段 + 强制 LIMIT + 参数化查询）
- ✅ 数据围栏管理（拦截率、兜底率、澄清率实时监控）
- ✅ 审计日志记录（所有查询可追溯）
- ✅ 知识闭环管理（识别知识缺口，支持补充知识）
- ✅ RAG 与 SQL 架构解耦（RAG 只处理非结构化文档）
- ✅ 会话管理（新建 / 查看 / 删除历史会话）
- ✅ Markdown渲染，结构化展示分析结果
- ✅ 数据来源可溯源
- ✅ 响应式布局，支持移动端

## 快速开始

### 环境要求

- Node.js >= 18
- Python >= 3.10
- MySQL 数据库（ecommerce 数据库）
- Ollama + qwen3:8b 模型

### 推荐方式：GUI 启动器

运行 `launcher.py` 启动图形化管理器，支持：
- 🟢 实时服务状态监测
- 🚀 一键启动全部服务
- 📋 运行日志查看与导出
- 🌐 一键打开前端页面

```bash
python launcher.py
```

### 备用方式：脚本启动

双击 `start.bat` 或使用命令行手动启动：

```bash
# 1. 安装前端依赖
npm install

# 2. 安装Python依赖
pip install -r backend/requirements.txt

# 3. 启动Ollama服务
ollama serve

# 4. 启动后端 (新终端)
cd backend
python server.py

# 5. 启动前端 (新终端)
npm run dev
```

启动后访问 http://localhost:5173

## 项目结构

```
ecommerce-ai-chat/
├── launcher.py                # 🎨 GUI 启动管理器
├── start.bat                  # 一键启动脚本
├── AAAAA启动管理器.bat        # 备用启动脚本
├── package.json               # 前端依赖配置
├── package-lock.json          # 前端依赖锁定文件
├── vite.config.js             # Vite配置（含API代理）
├── index.html                 # HTML入口
├── src/
│   ├── main.js                # Vue入口
│   ├── App.vue                # 主组件
│   ├── HomeView.vue           # 首页
│   ├── DashboardView.vue      # 仪表盘页面
│   ├── LoginView.vue          # 登录页面
│   ├── RegisterView.vue       # 注册页面
│   ├── router.js              # Vue Router 路由配置
│   ├── style.css              # 全局样式
│   └── api.js                 # API封装
├── backend/
│   ├── config.py              # 统一配置管理
│   ├── server.py              # Flask API服务器
│   ├── auth.py                # 用户认证模块
│   ├── rag_chatbot.py         # RAG聊天机器人核心
│   ├── intent_parser.py       # 意图解析模块
│   ├── sql_executor.py        # SQL执行器
│   ├── requirements.txt       # Python依赖
│   ├── migrations/            # 数据库迁移脚本
│   │   ├── 001_create_audit_log.sql
│   │   └── 002_create_users.sql
│   └── knowledge_docs/        # 知识文档目录（RAG数据源）
│       ├── Guizhou_Ecommerce_Policy_Environment_2025.md
│       ├── Guizhou_Ecommerce_Industry_Trends_2025.md
│       ├── Guizhou_Ecommerce_Regional_IP_Report_2025.md
│       ├── Guizhou_Ecommerce_Comprehensive_Report_2025.md
│       ├── economic_yearbook_guizhou.md
│       ├── data_analysis_methodology.md
│       ├── business_rules_manual.md
│       ├── sop_ecommerce_analysis.md
│       ├── database_design_and_sql_optimization.md
│       └── ecommerce_knowledge_base.txt
├── .venv/                     # Python虚拟环境（需自行创建）
├── .gitignore                 # Git忽略文件
├── sessions/                  # 会话存储目录（自动生成）
└── vector_db/                 # 向量数据库缓存（自动生成）
```

## 数据库配置

推荐使用环境变量配置（编辑 `.env` 文件），或直接修改 `backend/config.py`：

```python
# config.py（支持环境变量覆盖）
MYSQL_CONFIG = {
    'host': os.environ.get('DB_HOST', 'localhost'),
    'port': int(os.environ.get('DB_PORT', 3306)),
    'user': os.environ.get('DB_USER', 'root'),
    'password': os.environ.get('DB_PASSWORD', '201711'),
    'database': os.environ.get('DB_NAME', 'ecommerce'),
}
```

## 知识文档管理

RAG 向量库基于 `backend/knowledge_docs/` 目录下的非结构化文档构建，包含：

- 📊 贵州省电商综合报告、政策环境、行业趋势分析
- 📈 区域 IP 分析、经济年鉴数据
- 📝 数据分析方法论、业务规则手册
- 💻 数据库设计与 SQL 优化文档

- 支持 `.txt` 和 `.md` 格式
- 文档变更后重启服务自动重建向量库（基于文件指纹缓存）
- 结构化数仓数据由 SQL 路径处理，无需放入此目录

## API 接口

### 用户认证接口
| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/register` | POST | 用户注册 |
| `/api/login` | POST | 用户登录 |
| `/api/logout` | POST | 用户登出 |

### 核心接口
| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/status` | GET | 服务状态检查 |
| `/api/chat/stream` | POST | 流式对话 (SSE) |
| `/api/sessions` | GET | 获取会话列表 |
| `/api/sessions` | POST | 创建新会话 |
| `/api/sessions/:id` | GET | 获取指定会话 |
| `/api/sessions/:id` | PUT | 更新会话 |
| `/api/sessions/:id` | DELETE | 删除会话 |

### 管理后台接口
| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/admin/audit-logs` | GET | 审计日志查询（支持 status 过滤） |
| `/api/admin/fence/metrics` | GET | 数据围栏指标（拦截率、趋势等） |
| `/api/admin/knowledge/gaps` | GET | 知识缺口列表 |
