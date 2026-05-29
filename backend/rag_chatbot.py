"""
RAG 聊天机器人核心模块

架构原则：
  - RAG 只处理非结构化文档（SOP、市场报告、经济年鉴、知识文档等）
  - SQL 处理结构化数仓表（通过 SQLExecutor）
  - 两者彻底解耦，检索速度大幅提升，Token 消耗显著降低
"""
import re
import os
import random
import hashlib
import json

os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'

from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_community.llms import Ollama
from langchain_core.prompts import PromptTemplate
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader, DirectoryLoader

from intent_parser import parse_question, IntentType
from sql_executor import SQLExecutor, TABLE_SCHEMA, METRIC_SYNONYMS, PREAGG_TABLE_ROUTE, INTERACTION_TABLE_GUARD
from config import (
    MYSQL_CONFIG, MODEL_NAME, VECTOR_DB_PATH, VECTOR_DB_FINGERPRINT_PATH,
    KNOWLEDGE_DOCS_DIR, RAG_TOP_K, RAG_CHUNK_SIZE, RAG_CHUNK_OVERLAP, RAG_MAX_DOCUMENTS,
    EMBEDDING_MODEL,
)

# 兜底话术池
FALLBACK_RESPONSES = [
    "亲，我只回答贵州电商平台相关的数据分析问题哦～",
    "不好意思，该问题超出了我的服务范围，我仅能解答区域电商消费、用户行为、商品销量等相关问题。",
    '抱歉，我无法回答这个问题，您可以尝试询问"贵阳消费品类""遵义销售额"等电商数据分析问题。'
]

# ============================================================
#  图表生成指令常量（用户明确请求图表时使用，必须输出图表JSON）
# ============================================================
_CHART_INSTRUCTION_REQUIRED = """【图表生成指令】：
用户明确请求了图表，你**必须**在回答末尾附加一个JSON代码块，格式如下：
```chart
{
  "type": "bar",
  "title": "{{图表标题}}",
  "xAxis": ["{{维度值1}}", "{{维度值2}}"],
  "yAxis": [{{数值1}}, {{数值2}}],
  "showLabel": false,
  "showMarkPoint": true,
  "showMarkLine": true
}
```
支持图表类型：
1. bar（柱状图）：适合比较不同类别的数值，如城市对比、品类排名
2. line（折线图）：适合展示趋势变化，如月度销售额趋势
3. pie（饼图）：适合展示占比分布，如品类占比、城市份额
4. scatter（散点图）：适合展示两个变量之间的关系
5. radar（雷达图）：适合展示多维度评估，如用户画像多维度分析

图表类型选择指南：
- 数据为分类对比 → 选择 bar
- 数据为时间趋势 → 选择 bar
- 数据为占比分布 → 选择 pie
- 数据为二维关系 → 选择 scatter
- 数据为多维度评估 → 选择 radar

雷达图特殊格式：
```chart
{
  "type": "radar",
  "title": "{{图表标题}}",
  "indicators": [{"name": "维度1", "max": {{最大值}}}, {"name": "维度2", "max": {{最大值}}],
  "data": [{"value": [{{值1}}, {{值2}}], "name": "{{系列名}}"}]
}
```

JSON字段说明：
- type: 图表类型（bar/line/pie/scatter/radar）
- title: 图表标题（基于问题自动生成）
- xAxis: 横轴数据数组（bar/line/scatter使用）
- yAxis: 纵轴数据数组（bar/line使用）或对象数组（pie使用[{"name":"品类","value":100}]格式）
- data: 特殊图表数据（scatter/radar使用）
- indicators: 雷达图指标数组 [{"name":"维度1","max":100}, {"name":"维度2","max":100}]
- showLabel: 是否显示数据标签
- showMarkPoint: 是否显示最大值最小值标记
- showMarkLine: 是否显示平均值线

⚠️ 严禁省略图表JSON！只要数据有2个及以上维度值，就必须生成图表。
⚠️ 严禁编造数据，JSON必须严格对应查询结果。"""

# ============================================================
#  图表生成指令常量（数据适合可视化时可选输出，不强制）
# ============================================================
_CHART_INSTRUCTION_OPTIONAL = """【图表生成指令】：
如果数据适合可视化展示（如多城市对比、趋势数据、品类排名等），请在回答末尾附加一个JSON代码块，格式如下：
```chart
{
  "type": "bar",
  "title": "{{图表标题}}",
  "xAxis": ["{{维度值1}}", "{{维度值2}}"],
  "yAxis": [{{数值1}}, {{数值2}}],
  "showLabel": false,
  "showMarkPoint": true,
  "showMarkLine": true
}
```
支持图表类型：
1. bar（柱状图）：适合比较不同类别的数值，如城市对比、品类排名
2. line（折线图）：适合展示趋势变化，如月度销售额趋势
3. pie（饼图）：适合展示占比分布，如品类占比、城市份额
4. scatter（散点图）：适合展示两个变量之间的关系
5. radar（雷达图）：适合展示多维度评估，如用户画像多维度分析

图表类型选择指南：
- 数据为分类对比 → 选择 bar
- 数据为时间趋势 → 选择 line
- 数据为占比分布 → 选择 pie
- 数据为二维关系 → 选择 scatter
- 数据为多维度评估 → 选择 radar

雷达图特殊格式：
```chart
{
  "type": "radar",
  "title": "{{图表标题}}",
  "indicators": [{"name": "维度1", "max": {{最大值}}}, {"name": "维度2", "max": {{最大值}}],
  "data": [{"value": [{{值1}}, {{值2}}], "name": "{{系列名}}"}]
}
```

JSON字段说明：
- type: 图表类型（bar/line/pie/scatter/radar）
- title: 图表标题（基于问题自动生成）
- xAxis: 横轴数据数组（bar/line/scatter使用）
- yAxis: 纵轴数据数组（bar/line使用）或对象数组（pie使用[{"name":"品类","value":100}]格式）
- data: 特殊图表数据（scatter/radar使用）
- indicators: 雷达图指标数组 [{"name":"维度1","max":100}, {"name":"维度2","max":100}]
- showLabel: 是否显示数据标签（默认false）
- showMarkPoint: 是否显示最大值最小值标记（默认true）
- showMarkLine: 是否显示平均值线（默认true）

智能图表生成规则：
1. 如果只有单一数值或数据不适合图表展示，则不要输出图表JSON
2. 如果数据包含时间维度，优先选择line图表
3. 如果数据为占比类，优先选择pie图表
4. 如果数据为城市/品类对比，优先选择bar图表
5. 如果数据量过大（>20条），考虑简化或分组显示
6. 严禁编造数据，JSON必须严格对应查询结果。"""

# 全局聊天机器人实例
_chatbot = None


class RAGChatbot:
    def __init__(self):
        self.vector_db = None
        self.qa_chain = None
        self._llm = Ollama(
            model=MODEL_NAME,
            keep_alive="5m",
            num_ctx=4096,
            temperature=0.1,
            top_p=0.9
        )
        self._vector_db_loaded = False

    # ============================================================
    #  向量数据库管理（基于本地知识文档）
    # ============================================================

    def _compute_fingerprint(self):
        """
        计算知识文档指纹。
        基于文档目录下所有文件的路径 + 大小 + 修改时间生成 MD5。
        数据变更时自动触发向量库重建。
        """
        parts = []
        if os.path.exists(KNOWLEDGE_DOCS_DIR):
            for root, dirs, files in os.walk(KNOWLEDGE_DOCS_DIR):
                dirs.sort()
                for fname in sorted(files):
                    fpath = os.path.join(root, fname)
                    stat = os.stat(fpath)
                    parts.append(f"{fpath}:{stat.st_size}:{stat.st_mtime}")
        raw = "|".join(parts)
        return hashlib.md5(raw.encode('utf-8')).hexdigest()

    def _is_vector_db_valid(self):
        try:
            if not os.path.exists(VECTOR_DB_PATH) or len(os.listdir(VECTOR_DB_PATH)) == 0:
                return False
            if not os.path.exists(VECTOR_DB_FINGERPRINT_PATH):
                return False
            with open(VECTOR_DB_FINGERPRINT_PATH, 'r') as f:
                saved_fingerprint = f.read().strip()
            current_fingerprint = self._compute_fingerprint()
            if saved_fingerprint != current_fingerprint:
                print("知识文档指纹不匹配，需要重建向量数据库")
                return False
            return True
        except Exception as e:
            print(f"检查向量数据库有效性时出错: {e}")
            return False

    def _save_fingerprint(self):
        try:
            fingerprint = self._compute_fingerprint()
            os.makedirs(VECTOR_DB_PATH, exist_ok=True)
            with open(VECTOR_DB_FINGERPRINT_PATH, 'w') as f:
                f.write(fingerprint)
        except Exception as e:
            print(f"保存指纹文件时出错: {e}")

    def _load_data(self):
        """
        加载向量数据库。
        优先使用缓存，文档变更时自动重建。
        """
        print("正在检查向量数据库...")
        os.makedirs(KNOWLEDGE_DOCS_DIR, exist_ok=True)

        if self._is_vector_db_valid():
            print("发现有效缓存，正在加载向量数据库...")
            embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
            self.vector_db = Chroma(
                persist_directory=VECTOR_DB_PATH,
                embedding_function=embeddings
            )
            print("向量数据库加载完成！（使用缓存）")
            return

        print(f"正在从本地文档构建向量库... 目录: {KNOWLEDGE_DOCS_DIR}")
        documents = self._load_from_docs()

        if not documents:
            print("⚠️ 知识文档目录为空，创建占位说明文档")
            placeholder_content = (
                "【知识库说明】\n"
                "本目录用于存放非结构化知识文档（SOP、市场报告、经济年鉴等）。\n"
                "请将 .txt / .md 文件放入 knowledge_docs/ 目录后重启服务。\n"
                "结构化数仓数据由 SQL 路径处理，无需放入此目录。"
            )
            documents = [Document(
                page_content=placeholder_content,
                metadata={'source': 'placeholder', 'row': 0}
            )]

        effective_max_docs = max(1, RAG_MAX_DOCUMENTS)
        if len(documents) > effective_max_docs:
            print(f"文档数量超过限制，只处理前{effective_max_docs}个文档")
            documents = documents[:effective_max_docs]

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=RAG_CHUNK_SIZE,
            chunk_overlap=RAG_CHUNK_OVERLAP
        )
        split_docs = text_splitter.split_documents(documents)

        print(f"正在生成向量数据库... (分块数: {len(split_docs)})")
        embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
        self.vector_db = Chroma.from_documents(
            documents=split_docs,
            embedding=embeddings,
            persist_directory=VECTOR_DB_PATH
        )
        self.vector_db.persist()
        self._save_fingerprint()
        print("向量数据库构建完成，已缓存。")

    def _load_from_docs(self):
        """从 knowledge_docs/ 加载非结构化文档"""
        documents = []
        try:
            try:
                loader = DirectoryLoader(
                    KNOWLEDGE_DOCS_DIR,
                    glob="**/*.txt",
                    loader_cls=TextLoader,
                    loader_kwargs={"encoding": "utf-8"}
                )
                txt_docs = loader.load()
                documents.extend(txt_docs)
                print(f"加载 .txt 文件: {len(txt_docs)} 个")
            except Exception as e:
                print(f"加载 .txt 文件出错: {e}")

            try:
                loader = DirectoryLoader(
                    KNOWLEDGE_DOCS_DIR,
                    glob="**/*.md",
                    loader_cls=TextLoader,
                    loader_kwargs={"encoding": "utf-8"}
                )
                md_docs = loader.load()
                documents.extend(md_docs)
                print(f"加载 .md 文件: {len(md_docs)} 个")
            except Exception as e:
                print(f"加载 .md 文件出错: {e}")

            for idx, doc in enumerate(documents):
                if 'source' not in doc.metadata:
                    doc.metadata['source'] = f'doc_{idx}'
                else:
                    doc.metadata['source'] = os.path.basename(doc.metadata['source'])
                doc.metadata['row'] = idx

        except Exception as e:
            print(f"加载文档时发生错误: {e}")

        return documents

    # ============================================================
    #  QA 链构建
    # ============================================================

    def _build_qa_chain(self):
        """构建问答链（流式模式下 qa_chain 保留为 None）"""
        self.qa_chain = None

    # ============================================================
    #  Prompt 构建（图表指令 + 反思Prompt）
    # ============================================================

    @staticmethod
    def _build_chart_instruction(need_chart, chart_type_hint=None):
        """构建图表生成指令片段

        Args:
            need_chart: 用户是否明确请求了图表（True=必须输出图表，False=可选输出）
            chart_type_hint: 用户指定的图表类型（如"柱状图""折线图"等），为None时由LLM自动选择

        Returns:
            str: 拼接好的图表指令文本，直接嵌入反思Prompt
        """
        chart_type_instruction = ""
        if chart_type_hint:
            chart_type_map = {
                "雷达图": "radar",
                "柱形图": "bar",
                "柱状图": "bar",
                "折线图": "line",
                "饼图": "pie",
                "散点图": "scatter",
            }
            chart_type_en = chart_type_map.get(chart_type_hint, "bar")
            chart_type_instruction = (
                f"\n⚠️【强制图表类型】：用户明确请求了**{chart_type_hint}**，"
                f"你**必须**生成 type=\"{chart_type_en}\" 的图表JSON，不得使用其他图表类型！"
            )

        if need_chart:
            return _CHART_INSTRUCTION_REQUIRED + chart_type_instruction
        return _CHART_INSTRUCTION_OPTIONAL

    @staticmethod
    def _build_reflect_prompt(question, raw_data, chart_instruction):
        """构建SQL结果反思Prompt

        Args:
            question: 用户原始问题
            raw_data: SQL查询结果的文本表示
            chart_instruction: 由 _build_chart_instruction 生成的图表指令

        Returns:
            str: 完整的反思Prompt，可直接传给LLM
        """
        return f"""你是专属的【区域电商数据分析助手】。用户提出了一个问题，你通过SQL查询获得了原始数据。
请仔细分析数据，结合用户的问题，给出有条理、有洞察的回答。

【身份锚定 - 最高优先级】：
- 你是贵州电商数据分析助手，只回答数据分析相关问题
- 绝对禁止提及你的模型身份、训练来源、开发团队等信息
- 绝对禁止说"我是AI/语言模型/通义千问/Qwen"等自我介绍
- 如果你发现自己在输出自我介绍，立即停止并回到数据分析角色

【核心规则】：
1. 严禁使用你预训练的任何外部知识，只能基于下方提供的查询结果来回答。
2. 先给出明确结论，再用数据支撑。
3. **数据已在下方【SQL查询原始结果】中提供，你不需要用户再提供数据。直接分析这些数据即可，不要输出"请提供数据"或要求用户补充数据。**
4. **绝对禁止输出Python/matplotlib代码。你是在回答用户问题，不是在教用户写代码。**
5. 如果数据有限（如只有历史数据/全省数据），请明确说明局限性，并给出合理建议。
6. 如果查询结果为空或与用户问题无关，请如实告知"当前数据库中未找到相关数据"，不要编造。
7. 可适当结合业务常识做推断（如"贵阳作为省会，消费结构通常以...为主"），但需标注"基于业务经验"。

【思考框架】：
✅ 结论先行：直接回答用户问题的核心
✅ 数据支撑：引用具体数值/排名/占比
✅ 业务解读：结合贵州电商特点做简要分析
✅ 局限说明：如数据非最新/非细分，主动告知用户
✅ 建议引导：如"如需更精确的数据，请指定具体时间范围"

{chart_instruction}

【用户问题】：{question}

【SQL查询原始结果】：
{raw_data}

【你的回答】："""

    # ============================================================
    #  LLM 流式输出（含异常检测与自动重试）
    # ============================================================

    def _llm_reflect_on_sql_stream(self, question, raw_data, need_chart=False, chart_type_hint=None):
        """流式总结 SQL 结果，支持异常输出检测和自动重试

        Args:
            question: 用户原始问题
            raw_data: SQL查询结果文本
            need_chart: 是否必须生成图表
            chart_type_hint: 用户指定的图表类型

        Yields:
            str: LLM逐字输出的回答内容
        """
        ANOMALY_KEYWORDS = [
            "请提供数据", "请提供以下信息", "请告诉我你的具体需求",
            "import matplotlib", "plt.show", "plt.plot",
            "我是AI", "我是语言模型", "我是通义千问",
        ]

        def _is_anomaly(text):
            return any(keyword in text for keyword in ANOMALY_KEYWORDS)

        def _generate_response(prompt, max_attempts=2):
            for attempt in range(max_attempts):
                full_response = ""
                buffer_yielded = False
                for chunk in self._llm.stream(prompt):
                    prev_len = len(full_response)
                    full_response += chunk
                    if len(full_response) <= 200 and _is_anomaly(full_response):
                        print(f"[LLM异常检测] 第{attempt+1}次输出异常，重试...")
                        break
                    if len(full_response) > 200:
                        if not buffer_yielded:
                            yield full_response[:prev_len]
                            buffer_yielded = True
                        yield chunk
                        continue
                else:
                    if len(full_response) <= 200:
                        if _is_anomaly(full_response):
                            print(f"[LLM异常检测] 第{attempt+1}次输出异常（短响应），重试...")
                            continue
                        yield full_response
                    else:
                        if not buffer_yielded:
                            yield full_response
                    return
            yield full_response

        try:
            chart_instruction = self._build_chart_instruction(need_chart, chart_type_hint)
            reflect_prompt = self._build_reflect_prompt(question, raw_data, chart_instruction)
            yield from _generate_response(reflect_prompt)
        except Exception as e:
            print(f"LLM 流式调用失败: {e}")
            yield f"查询成功，但AI总结失败。原始数据：\n{raw_data[:500]}"

    # ============================================================
    #  核心入口：流式提问
    # ============================================================

    def stream_ask(self, question, chat_history=None, pre_parsed=None):
        """流式提问入口，根据意图分发到对应处理分支

        Args:
            question: 用户问题
            chat_history: 聊天历史（当前未使用，每次独立回答）
            pre_parsed: 预解析结果（server.py已调用parse_question时传入，避免重复解析）
        """
        yield "__THINKING_START__"

        if not self._vector_db_loaded:
            yield "__THINKING_CONTENT__" + "🔄 正在初始化知识库（首次加载可能需要几秒）...\n"
            try:
                self._load_data()
                self._vector_db_loaded = True
            except Exception as e:
                print(f"⚠️ 向量库加载失败: {e}")
                yield "__THINKING_END__"
                yield "⚠️ 知识库初始化失败，请检查 knowledge_docs/ 目录配置。当前仅支持SQL查询。"

        parse_result = pre_parsed if pre_parsed else parse_question(question)

        thinking_text = (
            f"正在分析您的问题：{question}\n"
            f"   意图识别：{parse_result.intent}\n"
            f"   提取槽位：{parse_result.slots}\n\n"
        )

        if parse_result.intent == IntentType.OUT_OF_DOMAIN:
            yield from self._handle_out_of_domain(thinking_text)
            return

        if parse_result.intent == IntentType.CLARIFY:
            yield from self._handle_clarify(parse_result, thinking_text)
            return

        if parse_result.intent == IntentType.SQL_QUERY:
            yield from self._handle_sql_query(question, parse_result, thinking_text)
            return

        yield from self._rag_stream(question, chat_history, thinking_text, is_fallback=False)

    # ============================================================
    #  意图处理：域外问题 / 澄清意图
    # ============================================================

    def _handle_out_of_domain(self, thinking_text):
        """处理域外问题：返回兜底话术

        Args:
            thinking_text: 已累积的思考过程文本

        Yields:
            str: 思考过程 + 兜底回答
        """
        thinking_text += "检测到域外问题，返回兜底话术\n"
        yield "__THINKING_CONTENT__" + thinking_text
        yield "__THINKING_END__"
        yield random.choice(FALLBACK_RESPONSES)

    def _handle_clarify(self, parse_result, thinking_text):
        """处理澄清意图：信息缺失，向用户追问

        Args:
            parse_result: 意图解析结果，slots中包含missing和partial信息
            thinking_text: 已累积的思考过程文本

        Yields:
            str: 思考过程 + 追问提示
        """
        missing = parse_result.slots.get("missing", [])
        partial = parse_result.slots.get("partial", {})
        thinking_text += "检测到信息缺失，需要向用户澄清\n"
        thinking_text += f"   缺失槽位：{missing}\n"
        thinking_text += f"   已有信息：{partial}\n"
        yield "__THINKING_CONTENT__" + thinking_text
        yield "__THINKING_END__"

        clarify_parts = ["为了更准确地回答您的问题，请补充以下信息：\n\n"]
        is_non_covered = partial.get("_non_covered_hint") if partial else False
        for slot_name in missing:
            if slot_name == "城市/区域":
                clarify_parts.append("📍 **城市/区域**：请指定具体城市（如贵阳、遵义等），或说全省查看所有城市\n")
            elif slot_name == "时间范围":
                clarify_parts.append("📅 **时间范围**：请指定具体时间（如2025年3月、今年等）\n")
            elif slot_name == "查询指标/意图":
                city_name = partial.get("city", "") if partial else ""
                city_display = city_name.replace("市", "").replace("州", "") if city_name else "该城市"
                if is_non_covered:
                    clarify_parts.append(
                        f"⚠️ **区域提示**：您查询的地区「{city_display}」不在系统覆盖范围内，"
                        f"当前系统仅覆盖**贵州省9个市州**（贵阳、遵义、六盘水、毕节、铜仁、安顺、黔东南、黔南、黔西南）。\n\n"
                        f"📊 **您可以换一种方式提问**：\n"
                        f"   - 💰 查询贵州省整体数据：\"贵州全省的销售额是多少？\"\n"
                        f"   - 🏙️ 查询覆盖城市数据：\"贵阳的销售额是多少？\"\n"
                        f"   - 📈 对比各城市数据：\"各城市销售额排名\"\n"
                        f"   - 🏷️ 品类分析：\"贵州各品类销量对比\"\n\n"
                        f"💡 例如：\"贵州全省的GMV是多少\"、\"贵阳和遵义的销售额对比\"、\"各城市消费趋势\"\n"
                    )
                else:
                    clarify_parts.append(
                        f"📊 **查询目标**：您想了解{city_display}的哪方面数据？\n"
                        f"   - 💰 销售额/销量/订单数\n"
                        f"   - 👥 用户数/付费率\n"
                        f"   - 📈 月度趋势\n"
                        f"   - 🏷️ 品类分布/消费结构\n"
                        f"   - 🛒 热销商品/爆款排名\n\n"
                        f"💡 例如：\"{city_display}的销售额是多少\"、\"{city_display}各品类销量对比\"、\"{city_display}消费趋势\"\n"
                    )
        if partial:
            clarify_parts.append(f"\n已识别信息：{json.dumps(partial, ensure_ascii=False)}")

        yield "".join(clarify_parts)

    # ============================================================
    #  意图处理：SQL查询（含城市商品兜底、指标全零、四级降级）
    # ============================================================

    def _handle_sql_query(self, question, parse_result, thinking_text):
        """处理SQL查询分支：选表→生成SQL→执行→指标全零检测→正常响应/四级降级

        Args:
            question: 用户原始问题
            parse_result: 意图解析结果
            thinking_text: 已累积的思考过程文本
        """
        slots = parse_result.slots
        thinking_text += "检测到结构化查询，走SQL查询路径\n正在连接数据库...\n"
        yield "__THINKING_CONTENT__" + thinking_text

        executor = None
        try:
            table_name = self._select_table(parse_result)

            # 城市级商品查询兜底：ais_product_top_ranking 无城市维度
            if slots.get("_city_product_query"):
                yield from self._handle_city_product_fallback(question, slots, thinking_text)
                return

            executor = SQLExecutor(table_name=table_name)
            thinking_text += f"选择数据表：{table_name}\n正在生成SQL查询语句...\n"
            sql, params = executor.generate_sql(parse_result)

            # sql为None表示指标在该表不支持，尝试备选表
            if sql is None:
                thinking_text += f"⚠️ 指标 '{slots.get('metric')}' 在表 {table_name} 中不支持\n尝试切换到其他数据表...\n"
                yield "__THINKING_CONTENT__" + thinking_text
                alt_table = self._find_alternative_table(slots.get("metric"), table_name)
                if alt_table:
                    thinking_text += f"切换到备选表：{alt_table}\n"
                    yield "__THINKING_CONTENT__" + thinking_text
                    executor.close()
                    executor = SQLExecutor(table_name=alt_table)
                    sql, params = executor.generate_sql(parse_result)

            if sql is None:
                thinking_text += "无法生成有效SQL，切换到RAG检索\n"
                yield "__THINKING_CONTENT__" + thinking_text
                yield from self._rag_stream(question, None, thinking_text, is_fallback=True)
                return

            thinking_text += f"SQL语句：{sql}\n查询参数：{params}\n正在执行查询...\n"
            yield "__THINKING_CONTENT__" + thinking_text

            sql_result = executor.execute_sql(sql, params)

            if not sql_result.empty:
                # 指标全零检测与降级切换
                handled, executor, table_name, thinking_text = yield from self._handle_metric_all_zero(
                    question, slots, sql_result, executor, table_name, thinking_text
                )
                if handled:
                    return

                # 正常响应路径
                thinking_text += f"查询成功，获取到 {len(sql_result)} 条记录 | 🤖 AI 生成回答中...\n"
                yield "__THINKING_CONTENT__" + thinking_text
                yield "__THINKING_END__"
                raw_data = sql_result.to_string(index=False)
                yield from self._llm_reflect_on_sql_stream(
                    question, raw_data,
                    need_chart=slots.get("need_chart", False),
                    chart_type_hint=slots.get("chart_type_hint")
                )
                yield f"\n【数据来源】：\n- {table_name} (SQL查询)"
                return
            else:
                # 四级降级策略
                thinking_text += "精确查询无结果，启动智能降级策略...\n"
                yield "__THINKING_CONTENT__" + thinking_text

                original_city = slots.get("city", "")
                is_non_covered = slots.get("_non_covered_city", False)

                # Level 1：去除时间限制
                if slots.get("time"):
                    success, thinking_text = yield from self._degrade_level_1_remove_time(
                        question, slots, executor, table_name, thinking_text
                    )
                    if success:
                        return

                # Level 2：去除城市限制
                if slots.get("city") and slots["city"] != "ALL_CITIES":
                    success, thinking_text = yield from self._degrade_level_2_remove_city(
                        question, slots, executor, table_name, thinking_text,
                        original_city, is_non_covered
                    )
                    if success:
                        return

                # Level 3：切换AIS预聚合表
                success, executor, thinking_text = yield from self._degrade_level_3_switch_ais(
                    question, slots, table_name, is_non_covered, thinking_text, executor
                )
                if success:
                    return

                # Level 4：RAG知识库兜底
                yield from self._degrade_level_4_rag(question, table_name, thinking_text)
                return

        except ValueError as e:
            thinking_text += f"配置错误：{e}\n切换到RAG路径...\n"
            yield "__THINKING_CONTENT__" + thinking_text
            yield from self._rag_stream(question, None, thinking_text, is_fallback=True)
            return
        except Exception as e:
            error_type = type(e).__name__
            error_msg = str(e)[:200] if str(e) else "未知错误"
            thinking_text += f"查询异常：{error_type}: {error_msg}\n"
            yield "__THINKING_CONTENT__" + thinking_text
            yield "__THINKING_END__"
            if "Connection" in error_type or "connect" in error_msg.lower() or "timeout" in error_msg.lower():
                yield "⚠️ 数据库连接异常，请检查数据库服务是否正常运行。"
            elif "ValueError" in error_type:
                yield f"⚠️ 查询配置异常：{error_msg}。请尝试换个方式提问。"
            else:
                yield f"⚠️ 查询过程中发生异常，请稍后重试或换个方式提问。"
            return
        finally:
            if executor:
                executor.close()

    def _handle_city_product_fallback(self, question, slots, thinking_text):
        """城市级商品查询兜底：商品排名表仅支持省级，降级查全省数据并提示

        Args:
            question: 用户原始问题
            slots: 解析出的槽位信息
            thinking_text: 已累积的思考过程文本

        Yields:
            str: 思考过程 + 省级商品排名数据 + 温馨提示
        """
        city_name = slots.get("city", "该城市")
        thinking_text += f"⚠️ 检测到城市级商品排名查询（{city_name}），当前商品排名表仅支持省级数据\n"
        yield "__THINKING_CONTENT__" + thinking_text
        yield "__THINKING_END__"

        executor = None
        try:
            executor = SQLExecutor(table_name="ais_product_top_ranking")
            province_slots = {slot_key: slot_val for slot_key, slot_val in slots.items()
                             if slot_key not in ("city", "_city_product_query", "_product_rank_query")}
            province_slots["city"] = "ALL_CITIES"
            from intent_parser import QuestionParseResult
            province_pr = QuestionParseResult(
                intent="sql_query",
                slots=province_slots,
                original_question=question
            )
            sql_province, params_province = executor.generate_sql(province_pr)
            if sql_province is not None:
                sql_result_province = executor.execute_sql(sql_province, params_province)
                if not sql_result_province.empty:
                    raw_data = sql_result_province.to_string(index=False)
                    yield from self._llm_reflect_on_sql_stream(question, raw_data, need_chart=False, chart_type_hint=None)
                    yield (f"\n\n⚠️ **温馨提示**：平台数据针对{city_name}的具体商品排名还在更新中，"
                           f"暂时无法提供{city_name}的详细解答。以上为**贵州省全省**的商品排名数据供参考。\n"
                           f"您可以查询贵州省整体的商品排名，例如：\"贵州卖的最好的手机是哪款？\"")
                    yield f"\n【数据来源】：\n- ais_product_top_ranking (SQL查询，省级数据)"
                    return
        except Exception:
            pass
        finally:
            if executor:
                executor.close()

        yield (f"⚠️ 平台数据针对{city_name}的具体商品排名还在更新中，"
               f"暂时无法提供{city_name}的详细解答。\n"
               f"您可以查询贵州省整体的商品排名，例如：\"贵州卖的最好的手机是哪款？\"")

    def _handle_metric_all_zero(self, question, slots, sql_result, executor, table_name, thinking_text):
        """指标全零检测与降级：当查询结果指标列全为0时，尝试切换到相关指标重新查询

        降级策略：销量→销售额, 订单数→销售额, 订单量→销售额。
        切换后可能需要换表，因此返回更新后的executor和table_name。

        Args:
            sql_result: 原始查询结果DataFrame
            executor: 当前SQL执行器（可能被替换为新表的执行器）
            table_name: 当前查询表名（可能被更新）

        Returns:
            tuple: (handled, executor, table_name, updated_thinking_text)
            handled=True表示已成功切换指标并yield了完整响应
        """
        metric_col_name = slots.get("metric", "")
        if not metric_col_name or len(sql_result.columns) < 2:
            return False, executor, table_name, thinking_text

        # 检查非维度列是否全为0
        is_all_zero = False
        for col in sql_result.columns:
            if col != "维度" and sql_result[col].dtype in ['float64', 'int64', 'float32', 'int32']:
                if (sql_result[col] == 0).all():
                    is_all_zero = True
                    break

        if not is_all_zero:
            return False, executor, table_name, thinking_text

        thinking_text += f"查询成功但指标'{metric_col_name}'全为0，尝试切换到相关指标...\n"
        yield "__THINKING_CONTENT__" + thinking_text

        METRIC_FALLBACK = {"销量": "销售额", "订单数": "销售额", "订单量": "销售额"}
        fallback_metric = METRIC_FALLBACK.get(metric_col_name)
        if not fallback_metric:
            return False, executor, table_name, thinking_text

        thinking_text += f"  └─ 切换指标：{metric_col_name} → {fallback_metric}\n"
        yield "__THINKING_CONTENT__" + thinking_text

        fallback_slots = {**slots}
        fallback_slots["metric"] = fallback_metric
        fallback_slots.pop("metric_field", None)
        fallback_slots.pop("table_hint", None)

        from intent_parser import QuestionParseResult as _QR, METRIC_TABLE_HINT, INTERACTION_METRIC_MAP
        if fallback_metric in METRIC_TABLE_HINT:
            fallback_slots["table_hint"] = METRIC_TABLE_HINT[fallback_metric]
        if fallback_metric in INTERACTION_METRIC_MAP:
            fallback_slots["metric_field"] = INTERACTION_METRIC_MAP[fallback_metric]

        fallback_pr = _QR(
            intent="sql_query",
            slots=fallback_slots,
            original_question=question
        )
        try:
            new_table = self._select_table(fallback_pr)
            if new_table != table_name:
                executor.close()
                executor = SQLExecutor(table_name=new_table)
                table_name = new_table
            sql_fb, params_fb = executor.generate_sql(fallback_pr)
            if sql_fb is not None:
                sql_result_fb = executor.execute_sql(sql_fb, params_fb)
                if not sql_result_fb.empty:
                    fb_has_data = False
                    for col in sql_result_fb.columns:
                        if col != "维度" and sql_result_fb[col].dtype in ['float64', 'int64', 'float32', 'int32']:
                            if not (sql_result_fb[col] == 0).all():
                                fb_has_data = True
                                break
                    if fb_has_data:
                        thinking_text += f"  └─ ✅ 切换成功，用'{fallback_metric}'数据分析 | 🤖 AI 生成回答中...\n"
                        yield "__THINKING_CONTENT__" + thinking_text
                        yield "__THINKING_END__"
                        raw_data = sql_result_fb.to_string(index=False)
                        yield from self._llm_reflect_on_sql_stream(
                            question, raw_data,
                            need_chart=slots.get("need_chart", False),
                            chart_type_hint=slots.get("chart_type_hint")
                        )
                        yield f"\n\n💡 提示：'{metric_col_name}'数据全为0，已自动切换到'{fallback_metric}'进行分析。"
                        yield f"\n【数据来源】：\n- {table_name} (SQL查询，指标降级: {metric_col_name}→{fallback_metric})"
                        return True, executor, table_name, thinking_text
        except Exception:
            pass

        return False, executor, table_name, thinking_text

    # ============================================================
    #  四级降级策略（查询结果为空时逐级放宽条件）
    # ============================================================

    def _degrade_level_1_remove_time(self, question, slots, executor, table_name, thinking_text):
        """降级Level 1：去除时间限制，查询全部历史数据

        当用户指定的时间范围不在数据库覆盖范围内时，移除时间过滤条件重试。

        Returns:
            tuple: (success, updated_thinking_text)
            success=True时已yield完整响应（含降级提示）
        """
        original_time = slots.get("time", "")
        thinking_text += "  ├─ Level 1：移除时间限制，查询全部历史数据...\n"
        yield "__THINKING_CONTENT__" + thinking_text

        slots_without_time = {slot_key: slot_val for slot_key, slot_val in slots.items() if slot_key != "time" and not slot_key.startswith("_")}
        from intent_parser import QuestionParseResult
        degraded_pr = QuestionParseResult(
            intent="sql_query",
            slots=slots_without_time,
            original_question=question
        )
        try:
            sql_degraded, params_degraded = executor.generate_sql(degraded_pr)
            if sql_degraded is not None:
                sql_result_degraded = executor.execute_sql(sql_degraded, params_degraded)
                if not sql_result_degraded.empty:
                    thinking_text += "  └─ ✅ Level 1 降级成功 | 🤖 AI 生成回答中...\n"
                    yield "__THINKING_CONTENT__" + thinking_text
                    yield "__THINKING_END__"
                    raw_data = sql_result_degraded.to_string(index=False)
                    yield from self._llm_reflect_on_sql_stream(
                        question, raw_data,
                        need_chart=slots.get("need_chart", False),
                        chart_type_hint=slots.get("chart_type_hint")
                    )
                    time_hint = f"您指定的时间「{original_time}」不在数据库覆盖范围内" if original_time else "指定时间范围内无数据"
                    yield (f"\n\n💡 **降级提示（Level 1 - 去除时间限制）**：{time_hint}，"
                           f"已自动查询全部历史数据。数据库当前覆盖时间为**2025年1-12月**。")
                    yield f"\n【数据来源】：\n- {table_name} (SQL查询，降级: 去除时间→全时间范围)"
                    return True, thinking_text
        except Exception:
            pass

        return False, thinking_text

    def _degrade_level_2_remove_city(self, question, slots, executor, table_name, thinking_text,
                                      original_city, is_non_covered):
        """降级Level 2：去除城市限制，查询全省聚合数据

        当指定城市在数据表中无匹配记录时，移除城市过滤条件，查询全省汇总数据。

        Args:
            original_city: 用户原始查询的城市名
            is_non_covered: 城市是否不在系统覆盖范围内（9市州之外）

        Returns:
            tuple: (success, updated_thinking_text)
        """
        thinking_text += "  ├─ Level 2：移除城市限制，查询全省聚合数据...\n"
        yield "__THINKING_CONTENT__" + thinking_text

        slots_province_aggregate = {slot_key: slot_val for slot_key, slot_val in slots.items()
                         if slot_key != "time" and slot_key != "city" and not slot_key.startswith("_")}
        slots_province_aggregate["city"] = "ALL_CITIES"
        slots_province_aggregate["is_aggregate"] = True
        from intent_parser import QuestionParseResult
        degraded_pr = QuestionParseResult(
            intent="sql_query",
            slots=slots_province_aggregate,
            original_question=question
        )
        try:
            sql_degraded, params_degraded = executor.generate_sql(degraded_pr)
            if sql_degraded is not None:
                sql_result_degraded = executor.execute_sql(sql_degraded, params_degraded)
                if not sql_result_degraded.empty:
                    thinking_text += "  └─ ✅ Level 2 降级成功 | 🤖 AI 生成回答中...\n"
                    yield "__THINKING_CONTENT__" + thinking_text
                    yield "__THINKING_END__"
                    raw_data = sql_result_degraded.to_string(index=False)
                    yield from self._llm_reflect_on_sql_stream(
                        question, raw_data,
                        need_chart=slots.get("need_chart", False),
                        chart_type_hint=slots.get("chart_type_hint")
                    )
                    if is_non_covered:
                        city_display = original_city
                        yield (f"\n\n💡 **降级提示（Level 2 - 去除城市限制）**："
                               f"您查询的地区「{city_display}」不在系统覆盖范围内，"
                               f"当前系统仅覆盖**贵州省9个市州**（贵阳、遵义、六盘水、毕节、铜仁、安顺、黔东南、黔南、黔西南）。"
                               f"已为您展示**贵州省整体数据**作为参考。")
                    else:
                        city_display = original_city.replace("市", "").replace("州", "")
                        yield (f"\n\n💡 **降级提示（Level 2 - 去除城市限制）**："
                               f"「{city_display}」在当前数据表中未找到匹配记录，"
                               f"已为您展示**贵州省整体数据**作为参考。"
                               f"如需查看具体城市数据，可尝试：\"贵阳的销售额\"、\"遵义的消费趋势\"")
                    yield f"\n【数据来源】：\n- {table_name} (SQL查询，降级: 去除城市→全省汇总)"
                    return True, thinking_text
        except Exception:
            pass

        return False, thinking_text

    def _degrade_level_3_switch_ais(self, question, slots, table_name, is_non_covered, thinking_text, executor):
        """降级Level 3：切换到AIS预聚合表查询

        根据问题关键词和已有槽位信息，智能选择最合适的AIS层预聚合表：
        - 有品类意图 → ais_category_monthly_summary 或 ais_city_category_summary
        - 有趋势/月度意图 → ais_city_monthly_summary
        - 有城市但无上述意图 → ais_city_monthly_summary
        - 兜底 → ais_category_monthly_summary

        Args:
            executor: 当前SQL执行器（将被替换为AIS表的执行器）

        Returns:
            tuple: (success, updated_executor, updated_thinking_text)
        """
        thinking_text += "  ├─ Level 3：切换到AIS预聚合表查询...\n"
        yield "__THINKING_CONTENT__" + thinking_text

        metric = slots.get("metric", "销售额")
        ais_table = None
        if slots.get("category") or any(keyword in question for keyword in ["品类", "类型", "结构"]):
            if slots.get("city") and slots["city"] != "ALL_CITIES" and not is_non_covered:
                ais_table = "ais_city_category_summary"
            else:
                ais_table = "ais_category_monthly_summary"
        elif any(keyword in question for keyword in ["趋势", "月度", "走势", "按月"]):
            ais_table = "ais_city_monthly_summary"
        elif slots.get("city") and slots["city"] != "ALL_CITIES" and not is_non_covered:
            ais_table = "ais_city_monthly_summary"
        else:
            ais_table = "ais_category_monthly_summary"

        if ais_table and ais_table != table_name:
            try:
                executor.close()
                executor = SQLExecutor(table_name=ais_table)
                slots_ais_degraded = {slot_key: slot_val for slot_key, slot_val in slots.items() if slot_key != "time" and not slot_key.startswith("_")}
                if is_non_covered:
                    slots_ais_degraded["city"] = "ALL_CITIES"
                    slots_ais_degraded["is_aggregate"] = True
                from intent_parser import QuestionParseResult
                ais_degraded_result = QuestionParseResult(
                    intent="sql_query",
                    slots=slots_ais_degraded,
                    original_question=question
                )
                sql_ais, params_ais = executor.generate_sql(ais_degraded_result)
                if sql_ais is not None:
                    sql_result_ais = executor.execute_sql(sql_ais, params_ais)
                    if not sql_result_ais.empty:
                        thinking_text += f"  └─ ✅ Level 3 降级成功，获取到 {len(sql_result_ais)} 条记录 | 🤖 AI 生成回答中...\n"
                        yield "__THINKING_CONTENT__" + thinking_text
                        yield "__THINKING_END__"
                        raw_data = sql_result_ais.to_string(index=False)
                        yield from self._llm_reflect_on_sql_stream(
                            question, raw_data,
                            need_chart=slots.get("need_chart", False),
                            chart_type_hint=slots.get("chart_type_hint")
                        )
                        yield (f"\n\n💡 **降级提示（Level 3 - 切换预聚合表）**："
                               f"原表（{table_name}）数据不足，已自动切换到预聚合表（{ais_table}）查询。"
                               f"数据粒度可能有所调整，但能为您提供宏观参考。")
                        yield f"\n【数据来源】：\n- {ais_table} (AIS预聚合表，降级: {table_name}→{ais_table})"
                        return True, executor, thinking_text
            except Exception:
                pass

        return False, executor, thinking_text

    def _degrade_level_4_rag(self, question, table_name, thinking_text):
        """降级Level 4：前三级结构化查询均无匹配，切换RAG知识库兜底

        Args:
            table_name: 之前尝试的表名（用于提示信息）
            thinking_text: 已累积的思考过程文本
        """
        thinking_text += "  ├─ Level 4：结构化数据全部无匹配，切换RAG知识库检索...\n"
        yield "__THINKING_CONTENT__" + thinking_text
        yield "__THINKING_END__"
        yield from self._rag_stream_with_hint(question, None, table_name)

    # ============================================================
    #  RAG 检索流
    # ============================================================

    def _rag_stream_with_hint(self, question, chat_history, failed_table):
        """Level 4 RAG降级 + 数据覆盖范围提示

        先尝试RAG检索，无论是否找到文档，都附加数据覆盖范围提示。
        """
        docs_content = None
        if self.vector_db is not None:
            try:
                docs = self.vector_db.as_retriever(search_kwargs={"k": RAG_TOP_K}).invoke(question)
                if docs:
                    docs_content = "\n\n".join([doc.page_content for doc in docs])
            except Exception:
                pass

        if docs_content:
            yield from self._rag_stream(question, chat_history, "", is_fallback=True)
        else:
            yield "__THINKING_END__"

        hint = (
            "\n\n💡 **降级提示（Level 4 - RAG知识库兜底）**："
            "前三级结构化查询均未找到匹配数据，已切换到知识库检索。\n\n"
            "📊 **数据覆盖范围**：\n"
            "- 🕐 时间范围：**2025年1-12月**\n"
            "- 📍 地区范围：**贵州省9个市州**（贵阳、遵义、六盘水、毕节、铜仁、安顺、黔东南、黔南、黔西南）\n"
            "- 🏷️ 品类范围：**11个品类**（电子数码、家用电器、服饰鞋帽、美妆护肤、食品饮料、酒类、运动户外、母婴用品、家居日用、农产品、旅游文创）\n\n"
            "💡 **建议**：如需精确数据，请调整查询条件后重试，例如：\n"
            "- \"贵阳2025年的销售额是多少？\"\n"
            "- \"各城市消费趋势\"\n"
            "- \"家用电器品类的销量排名\""
        )
        yield hint

    def _rag_stream(self, question, chat_history, thinking_text, is_fallback=False):
        """RAG 检索流的内部实现

        流程：向量检索 → 幻觉防护（关键词匹配拦截无关文档） → LLM生成回答 → 附加数据来源

        幻觉防护机制：通过检查检索文档是否包含电商领域关键词来过滤无关文档，
        避免LLM基于不相关上下文编造答案。
        """
        if self.vector_db is None:
            thinking_text += "向量库未就绪，无法执行RAG检索\n"
            yield "__THINKING_CONTENT__" + thinking_text
            yield "__THINKING_END__"
            yield "⚠️ 知识库未初始化，暂时无法回答分析类问题。请稍后再试或尝试数据查询类问题。"
            return

        context_label = "SQL无结果，自动切换" if is_fallback else "检测到分析类问题"
        thinking_text += f"{context_label}，走RAG检索路径\n正在检索相关文档...\n"
        yield "__THINKING_CONTENT__" + thinking_text

        try:
            docs = self.vector_db.as_retriever(search_kwargs={"k": RAG_TOP_K}).invoke(question)
        except Exception as e:
            thinking_text += f"文档检索失败: {type(e).__name__}\n"
            yield "__THINKING_CONTENT__" + thinking_text
            yield "__THINKING_END__"
            yield "⚠️ 知识库检索异常，暂时无法回答分析类问题。请稍后再试或尝试数据查询类问题。"
            return

        thinking_text += f"找到 {len(docs)} 条相关文档\n"
        for idx, doc in enumerate(docs[:5], 1):
            thinking_text += f"   {idx}. 来源: {doc.metadata.get('source', 'unknown')}\n"
        if len(docs) > 5:
            thinking_text += f"   ... 还有 {len(docs) - 5} 条\n"
        thinking_text += "正在构建上下文...\n"
        yield "__THINKING_CONTENT__" + thinking_text

        if not docs:
            thinking_text += "未找到相关文档，生成无相关信息提示...\n"
            yield "__THINKING_CONTENT__" + thinking_text
            yield "__THINKING_END__"
            yield "当前知识库中无相关信息，无法为你提供答案"
            return

        context = "\n\n".join([doc.page_content for doc in docs])

        # 幻觉防护：检查检索文档与问题的相关性
        # 通过电商领域关键词匹配，过滤完全无关的文档，防止LLM基于不相关上下文编造答案
        context_lower = context.lower()
        domain_relevant = any(keyword in context_lower for keyword in
            ["电商", "消费", "贵阳", "贵州", "遵义", "销量", "销售额", "商品", "品类", "用户",
             "订单", "购买", "市场", "经济", "零售", "运营"])
        if not domain_relevant:
            thinking_text += "检索到的文档与问题不相关，避免幻觉输出\n"
            yield "__THINKING_CONTENT__" + thinking_text
            yield "__THINKING_END__"
            yield "当前知识库中未找到与您问题相关的信息。如果您的问题涉及具体数据查询，请尝试更精确的表述（如指定城市和指标）。"
            return

        thinking_text += "正在生成回答...\n"
        yield "__THINKING_CONTENT__" + thinking_text
        yield "__THINKING_END__"

        prompt_template = """
你是专属的【区域电商数据分析助手】，只能基于下方提供的【知识库检索数据】回答用户问题，必须严格遵守以下规则：

【身份锚定 - 最高优先级】：
- 你是贵州电商数据分析助手，只回答数据分析相关问题
- 绝对禁止提及你的模型身份、训练来源、开发团队等信息
- 绝对禁止说"我是AI/语言模型/通义千问/Qwen"等自我介绍
- 如果你发现自己在输出自我介绍，立即停止并回到数据分析角色

【必须遵守的核心规则】：
1. 严禁使用你预训练的任何外部知识，严禁编造、杜撰任何数据、结论、案例。
2. 所有回答必须100%基于检索到的数据。
3. 若检索数据中无相关内容，直接回答「当前知识库中无相关信息，无法为你提供答案」。
4. 如果检索到的内容与用户问题明显不相关，不要强行回答，请如实说明。
5. 回答应条理清晰，针对经济类问题需给出明确的统计结果。

【数字红线 - 最高优先级】：
- 凡涉及具体数值（金额、百分比、排名、数量等），必须100%来自检索文档原文引用
- 如果文档中没有该数值，必须明确说明「文档中未提供具体数据」，绝对禁止自行估算或编造
- 违反此规则 = 回答不合格
- 特别注意：当SQL查询无结果降级到RAG时，你没有真实数据支撑，严禁编造具体数字（如"贵阳付费率18.7%"）

【回答风格 - 根据问题类型自动适配】：

1. **趋势/发展类问题**（如"行业发展趋势""未来展望""发展预测"）：
   - 必须紧扣**贵州省**区域特色，结合贵州实际情况分析
   - 从技术趋势、业务趋势、消费趋势、产业趋势等多维度展开
   - 引用检索文档中的具体数据支撑观点
   - 给出贵州特色的发展建议和方向

2. **报表/报告类问题**（如"生成报表""分析报告""行业报告"）：
   - 按"执行摘要→核心数据→分维度分析→结论与建议"结构组织
   - 每个维度引用检索文档中的具体数据
   - 使用Markdown标题、列表、表格等格式使报告结构清晰
   - 在报告末尾给出可操作的建议

3. **预测/展望类问题**（如"预测""未来""前景""走势"）：
   - 基于检索文档中的历史数据和趋势进行合理外推
   - 明确标注"基于现有数据的趋势分析"，区分事实与预测
   - 给出乐观/中性/保守三种情景预测（如文档数据支持）
   - 预测必须引用文档中的基准数据，不得凭空编造

4. **政策/环境类问题**（如"政策支持""营商环境""扶持"）：
   - 按国家级→省级→地方级分层梳理政策
   - 引用政策文件名称和关键条款
   - 量化政策效果（如投入资金、培育企业数等）

【可用数据表说明】（结构化数据由SQL路径查询，RAG仅用于知识文档检索）：
"""
        for tbl, schema in TABLE_SCHEMA.items():
            prompt_template += f"▶ {tbl}（{schema['description']}）：字段包括 {', '.join(schema['metrics'][:3])} 等\n"

        prompt_template += """
【知识库检索数据】：
{context}

【用户问题】：
{question}

【你的回答】："""

        prompt = prompt_template.format(context=context, question=question)

        for chunk in self._llm.stream(prompt):
            yield chunk

        # 添加数据来源（去重）
        source_parts = ["\n【数据来源】：\n"]
        seen_sources = set()
        source_docs = []
        for doc in docs:
            src = doc.metadata.get('source', 'unknown')
            if src not in seen_sources:
                seen_sources.add(src)
                source_docs.append(src)
        for src in source_docs[:5]:
            source_parts.append(f"- {src}\n")
        yield "".join(source_parts)

    # ============================================================
    #  智能选表
    # ============================================================

    def _select_table(self, parse_result):
        """根据意图解析结果智能选择查询表

        三级路由机制（优先级从高到低）：
          P0: intent_parser 的 table_hint —— 已包含AIS智能路由逻辑
              （有城市→交叉表，无城市→品类表），优先级最高
          P1: PREAGG_TABLE_ROUTE 关键词路由 —— 关键词命中直接锁定表
          P2: 加权评分机制 —— 对问题文本做关键词匹配，选得分最高的表

        交互表保护：ads_user_item_interaction_matrix 需要精确主键
        （user_id 或 product_id），否则降级到 ais_city_monthly_summary。

        Args:
            parse_result: 意图解析结果

        Returns:
            str: 选中的表名
        """
        slots = parse_result.slots
        question = parse_result.original_question.lower()

        # P0: 优先使用 intent_parser 的 table_hint
        if slots.get("table_hint"):
            hinted_table = slots["table_hint"]
            if hinted_table == INTERACTION_TABLE_GUARD["table"]:
                has_precise_key = any(slots.get(slot_key) for slot_key in INTERACTION_TABLE_GUARD["required_slots"])
                if not has_precise_key:
                    return INTERACTION_TABLE_GUARD["fallback_table"]
            return hinted_table

        # P1: 预聚合表路由 —— 关键词命中直接锁定表
        for keyword, table in PREAGG_TABLE_ROUTE.items():
            if keyword in question:
                if table == INTERACTION_TABLE_GUARD["table"]:
                    has_precise_key = any(slots.get(slot_key) for slot_key in INTERACTION_TABLE_GUARD["required_slots"])
                    if not has_precise_key:
                        return INTERACTION_TABLE_GUARD["fallback_table"]
                # ais_city_category_summary 需要城市条件，无城市时降级到全省品类汇总
                if table == "ais_city_category_summary" and not (slots.get("city") and slots["city"] != "ALL_CITIES"):
                    return "ais_category_monthly_summary"
                return table

        # P2: 加权评分机制 —— 每个表配置关键词权重，对问题文本匹配求和，选最高分
        table_scores = {
            "ads_product_feature_full": {
                "keywords": {"商品": 2, "产品": 2, "品牌": 2, "价格": 1, "热销": 2, "滞销": 2, "sku": 1, "库存": 1, "商品详情": 2, "商品分类": 2},
            },
            "ads_user_profile_full": {
                "keywords": {"用户画像": 3, "年龄": 1, "职业": 1, "收入": 1, "会员": 1, "rfm": 2, "用户价值": 2, "用户分布": 1, "用户群体": 1, "用户特征": 1},
            },
            "ads_user_item_interaction_matrix": {
                "keywords": {"转化漏斗": 3, "复购": 2},
            },
            "ads_region_consume_analysis": {
                "keywords": {"区域": 2, "全省": 2, "市场份额": 1, "消费分析": 3},
            },
            "ais_city_monthly_summary": {
                "keywords": {"趋势": 2, "月度": 2, "走势": 2, "对比": 1, "排名": 1, "排行": 1, "城市": 1, "消费": 1, "销售额": 2, "付费率": 2},
            },
            "ais_category_monthly_summary": {
                "keywords": {"品类": 2, "分布": 2, "结构": 1, "雷达": 2},
            },
            "ais_city_category_summary": {
                "keywords": {"消费类型": 2, "消费结构": 2, "品类构成": 2, "品类": 1},
            },
        }

        scores = {}
        for table, config in table_scores.items():
            score = sum(weight for keyword, weight in config["keywords"].items() if keyword in question)
            scores[table] = score

        best_table = max(scores, key=scores.get)
        selected = best_table if scores[best_table] > 0 else "ads_region_consume_analysis"

        if selected == INTERACTION_TABLE_GUARD["table"]:
            has_precise_key = any(slots.get(slot_key) for slot_key in INTERACTION_TABLE_GUARD["required_slots"])
            if not has_precise_key:
                return INTERACTION_TABLE_GUARD["fallback_table"]

        return selected

    def _find_alternative_table(self, metric, exclude_table):
        """当指标在首选表不支持时，查找其他可支持该指标的表

        Args:
            metric: 指标关键词（如"销售额""销量"）
            exclude_table: 需要排除的表名（已尝试过的表）

        Returns:
            str or None: 支持该指标的备选表名，无匹配时返回None
        """
        for tbl, schema in TABLE_SCHEMA.items():
            if tbl == exclude_table:
                continue
            table_map = schema.get("metric_map", {})
            if metric in table_map:
                col = table_map[metric]
                if col in schema.get("metrics", []):
                    return tbl
        return None


def get_chatbot():
    """获取或初始化全局聊天机器人实例"""
    global _chatbot
    if _chatbot is None:
        _chatbot = RAGChatbot()
    return _chatbot
