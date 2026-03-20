# 🎯 AI Lab-InterReviewer — Cybernetic Command

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-blue?logo=python" alt="Python">
  <img src="https://img.shields.io/badge/FastAPI-0.109+-009688?logo=fastapi" alt="FastAPI">
  <img src="https://img.shields.io/badge/Architecture-Clean%20Architecture-blueviolet" alt="Architecture">
  <img src="https://img.shields.io/badge/LLM-Qwen%20Plus-green" alt="LLM">
  <img src="https://img.shields.io/badge/RAG-ChromaDB-orange" alt="RAG">
  <img src="https://img.shields.io/badge/TTS-Edge--TTS-purple" alt="TTS">
  <img src="https://img.shields.io/badge/Frontend-Modular%20ES%20Modules-0a0e1a" alt="UI">
</p>

> **一款面向顶尖高校实验室申请场景的 AI 面试系统**，通过大语言模型模拟不同面试风格，提供全流程、多维度、沉浸式的面试训练体验。采用 **Clean Architecture** 分层架构重构，前端采用 **「指挥舱」** 深空主题 Dashboard 设计。

---

## 📋 目录

- [核心功能](#-核心功能)
- [系统架构](#-系统架构)
- [技术栈](#-技术栈)
- [快速开始](#-快速开始)
- [环境变量配置](#-环境变量配置)
- [项目结构](#-项目结构)
- [API 接口说明](#-api-接口说明)
- [个性化定制](#-个性化定制)

---

## 🚀 核心功能

### 全流程面试模拟

系统支持完整的 **10 阶段面试流程**，顶部进度条实时追踪：

```
开始 → 自我介绍 → 经历深挖 → 基础知识 → 代码 → 科研动机 → 科研潜力 → 综合追问 → 学生反问 → 结束
```

### 功能矩阵

| 功能 | 说明 |
|------|------|
| **语音面试** | Web Audio API 录音 → StepFun ASR 识别 → 自动发送至对话 |
| **文字对话** | SSE 流式响应，实时逐字渲染 AI 回复 |
| **流式 TTS** | Edge-TTS 句子级并行合成，边生成边播放，首句响应 < 2s |
| **沉浸式模式** | 全屏语音交互界面，极简操作体验 |
| **RAG 知识库** | ChromaDB 向量检索，CS 领域专业题库 |
| **代码编辑器** | CodeMirror IDE 面板，语法高亮、括号匹配、代码折叠 |
| **AI 面试报告** | 多维度加权评分，Markdown 导出 |
| **简历解析** | PDF 上传 → AI 分析，针对性个性化提问 |
| **导师信息搜索** | 联网检索目标导师信息，注入面试上下文 |
| **视频录制** | 可选 WebRTC 摄像头录制，面试留存 |
| **测试房间** | 导师创建房间 → 学生加入 → 标准化测试，结果自动上传 |
| **精简对话模式** | 仅显示当前轮次问答，模拟真实面试界面 |

---

## 🏗️ 系统架构

### Clean Architecture 分层设计

```
┌─────────────────────────────────────────────┐
│                  API 层                      │
│         FastAPI Routes / Dependencies        │
├─────────────────────────────────────────────┤
│                 服务层                        │
│  ChatService / AudioService / ResumeService  │
│  AdvisorService / RoomService / ReportService│
├─────────────────────────────────────────────┤
│                 领域层                        │
│    Entities / Interfaces / Value Objects     │
├─────────────────────────────────────────────┤
│              基础设施层                       │
│  LLM / TTS / ASR / RAG / Storage / Utils    │
└─────────────────────────────────────────────┘
```

### 请求流程

```
浏览器 (ES Modules 模块化前端)
  │
  ├── POST /api/asr         → ASRProvider → StepFun ASR
  │
  ├── POST /api/chat/stream → ChatService
  │                              ├── RAGEngine (ChromaDB 检索)
  │                              ├── LLMProvider (Qwen 流式生成)
  │                              └── TTSProvider (Edge-TTS 合成)
  │
  ├── POST /api/resume/upload → ResumeService → PDF解析 + AI分析
  │
  ├── POST /api/advisor/search → AdvisorService → 联网检索
  │
  ├── POST /api/report/stream  → ReportService → AI报告生成
  │
  ├── POST /api/teacher/create → RoomService → 创建测试房间
  │
  └── POST /api/student/join/{id} → RoomService → 加入房间
```

---

## 🛠️ 技术栈

### 后端

| 组件 | 技术 | 说明 |
|------|------|------|
| **Web 框架** | FastAPI | 异步高性能、SSE 流式推送、自动 API 文档 |
| **架构模式** | Clean Architecture + DI | 依赖注入容器，分层解耦 |
| **配置管理** | Pydantic Settings | 类型安全配置，.env 文件支持 |
| **LLM** | DashScope (Qwen-Plus) | 国内低延迟，流式输出 |
| **Embedding** | DashScope Embedding | 向量化中文文本 |
| **向量库** | ChromaDB | 本地持久化，元数据过滤 |
| **RAG** | LangChain | 文本分块 + 向量检索 |
| **TTS** | Edge-TTS | 免费多声色，句子级并行 |
| **ASR** | StepFun step-asr | 中文识别准确率高 |
| **HTTP 客户端** | httpx | 异步 HTTP，ASR API 调用 |
| **PDF 解析** | pdfplumber + PyPDF2 | 简历 + 导师文档解析 |

### 前端

| 技术 | 用途 |
|------|------|
| **原生 HTML/CSS/JS** | 零框架依赖，轻量高效 |
| **ES Modules** | 模块化前端架构，EventBus 事件解耦 |
| **EventBus** | 发布-订阅模式，解耦模块间通信 |
| **StateManager** | 单一数据源，集中管理应用状态 |
| **Web Audio API** | 浏览器录音 |
| **SSE (EventSource)** | 流式对话接收 |
| **CodeMirror 5** | Web IDE 编辑器 |
| **CSS Glassmorphism** | 深空主题设计系统 |

---

## ⚡ 快速开始

### 环境要求

- Python **3.10+**
- 阿里云 DashScope API Key（LLM + Embedding）
- StepFun API Key（ASR 语音识别，TTS 可选）

### 安装步骤

```bash
# 1. 克隆项目
git clone https://github.com/your-repo/AI_Intereviewer_USTC.git
cd AI_Intereviewer_USTC

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置环境变量
cp .env.example .env
# 编辑 .env 填写 API Keys

# 4. 构建知识库向量索引
python scripts/build_cs_vector_store.py

# 5. 启动服务
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 访问

| 地址 | 说明 |
|------|------|
| `http://localhost:8000` | 学生端主界面 |
| `http://localhost:8000/static/teacher.html` | 导师端管理界面 |
| `http://localhost:8000/docs` | FastAPI 交互文档 |

---

## 🔧 环境变量配置

所有配置通过 `.env` 文件或环境变量注入，参考 [`.env.example`](.env.example)。

### 必填项

| 变量 | 说明 |
|------|------|
| `DASHSCOPE_API_KEY` | 阿里云 DashScope API Key（LLM + Embedding） |
| `STEPFUN_API_KEY_1` | StepFun API Key（至少配置一个） |

### 可选项

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `LLM_MODEL` | `qwen-plus` | 使用的 LLM 模型 |
| `TTS_PROVIDER` | `edge` | TTS 提供者：`edge`（免费）或 `stepfun` |
| `TTS_VOICE` | `zh-CN-YunjianNeural` | Edge-TTS 声色 |
| `PORT` | `8000` | 服务端口 |
| `DEBUG` | `false` | 调试模式 |
| `SESSION_TTL_HOURS` | `2` | 会话有效期（小时） |
| `MAX_CONVERSATION_TURNS` | `50` | 最大对话轮数 |
| `STEPFUN_API_KEY_2~8` | 空 | 多 Key 轮询（可选，突破限流） |

### TTS 声色选项

| 声色 | 名称 | 特点 |
|------|------|------|
| `zh-CN-YunjianNeural` | 云健 | 沉稳磁性（默认） |
| `zh-CN-YunxiNeural` | 云希 | 年轻活泼 |
| `zh-CN-XiaoxiaoNeural` | 晓晓 | 甜美女声 |

---

## 📁 项目结构

```
AI_Intereviewer_USTC/
├── main.py                          # FastAPI 应用入口
├── config.py                        # 旧版配置（向后兼容）
├── requirements.txt                 # Python 依赖
├── pytest.ini                       # 测试配置
├── .env.example                     # 环境变量模板
│
├── backend/                         # 后端分层架构（Clean Architecture）
│   ├── config/
│   │   ├── settings.py              # Pydantic Settings 配置管理
│   │   └── prompts/                 # 预设提示词
│   │
│   ├── domain/                      # 领域层（业务核心）
│   │   ├── entities/                # 实体：InterviewSession, ResumeInfo, AdvisorInfo
│   │   ├── interfaces/              # 抽象接口：LLMProvider, TTSProvider, ASRProvider
│   │   ├── value_objects/           # 值对象
│   │   └── events/                  # 领域事件
│   │
│   ├── infrastructure/              # 基础设施层（外部依赖实现）
│   │   ├── llm/                     # LLM 提供者（DashScope/StepFun）
│   │   ├── tts/                     # TTS 提供者（Edge-TTS）
│   │   ├── asr/                     # ASR 提供者（StepFun）
│   │   ├── rag/                     # RAG 引擎（ChromaDB）
│   │   ├── storage/                 # 存储（会话/文件）
│   │   └── utils/                   # 工具（文本清理等）
│   │
│   ├── services/                    # 服务层（业务逻辑编排）
│   │   ├── chat_service.py          # 流式聊天
│   │   ├── audio_service.py         # TTS + ASR
│   │   ├── resume_service.py        # 简历解析
│   │   ├── advisor_service.py       # 导师搜索
│   │   ├── room_service.py          # 测试房间管理
│   │   └── report_service.py        # 面试报告生成
│   │
│   ├── api/                         # API 层（路由 + 依赖注入）
│   │   ├── routes/
│   │   │   ├── chat.py              # /api/chat/* /api/asr
│   │   │   ├── resume.py            # /api/resume/*
│   │   │   ├── advisor.py           # /api/advisor/*
│   │   │   ├── room.py              # /api/teacher/* /api/student/*
│   │   │   └── report.py            # /api/report/*
│   │   └── dependencies.py          # 通用依赖（presets等）
│   │
│   ├── container.py                 # 依赖注入容器
│   └── tests/                       # 测试
│       ├── conftest.py              # 通用 fixtures
│       ├── unit/                    # 单元测试
│       │   ├── test_domain/
│       │   ├── test_services/
│       │   └── test_infrastructure/
│       └── integration/             # 集成测试
│           └── test_api/
│
├── frontend/                        # 前端模块化架构（ES Modules）
│   ├── core/
│   │   ├── event-bus.js             # 全局事件总线
│   │   ├── state-manager.js         # 状态管理器
│   │   ├── api-client.js            # API 客户端封装
│   │   └── config.js                # 前端配置
│   ├── modules/
│   │   ├── settings/
│   │   │   ├── settings-manager.js  # 设置管理
│   │   │   ├── sidebar-manager.js   # 侧边栏
│   │   │   └── drawer-manager.js    # 抽屉面板
│   │   ├── resume/
│   │   │   └── resume-manager.js    # 简历管理
│   │   ├── advisor/
│   │   │   └── advisor-manager.js   # 导师搜索
│   │   └── interview/
│   │       ├── mode-manager.js      # 面试模式（标准/沉浸/测试）
│   │       ├── phase-timeline.js    # 阶段时间线
│   │       └── report-manager.js    # 报告生成
│   └── main.js                      # 模块化应用入口
│
├── static/                          # 静态资源（传统前端，仍在使用）
│   ├── index.html                   # 学生端主页面
│   ├── teacher.html                 # 导师端页面
│   ├── css/style.css                # 深空 Glassmorphism 设计系统
│   └── js/
│       ├── app.js                   # 主应用逻辑（单体，历史遗留）
│       ├── chat.js                  # 对话模块
│       ├── audio.js                 # 录音模块
│       ├── tts-stream.js            # TTS 流式播放
│       ├── vad.js                   # 语音活动检测
│       ├── video.js                 # 视频录制
│       ├── teacher.js               # 导师端逻辑
│       └── markdown-renderer.js     # Markdown 渲染
│
├── modules/                         # 旧版后端模块（向后兼容）
│   ├── llm_agent.py
│   ├── rag_engine.py
│   ├── audio_processor.py
│   ├── interview_manager.py
│   ├── ai_report.py
│   ├── resume_parser.py
│   ├── advisor_search.py
│   ├── advisor_docs.py
│   └── room_manager.py
│
├── data/                            # 知识库数据
│   └── cs ai/                       # CS 专业题库（JSONL）
│
├── vector_db/                       # ChromaDB 向量数据库（本地持久化）
├── scripts/
│   └── build_cs_vector_store.py     # 知识库向量化构建脚本
│
├── output/                          # 运行时输出（gitignored）
│   ├── reports/                     # 面试报告
│   ├── videos/                      # 录像文件
│   ├── rooms/                       # 房间数据
│   └── advisor_docs/                # 导师文档
│
└── temp_audio/                      # TTS/ASR 临时音频（gitignored）
```

---

## 📡 API 接口说明

所有接口通过 `X-Session-ID` Header 传递会话 ID。

### 对话接口

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/chat/stream` | 流式聊天（SSE） |
| `POST` | `/api/asr` | 语音识别（上传音频 → 返回文字） |
| `POST` | `/api/tts` | 文字转语音 |
| `GET`  | `/api/settings` | 获取会话设置 |
| `POST` | `/api/settings` | 保存会话设置 |
| `GET`  | `/api/presets` | 获取预设提示词 |
| `GET`  | `/api/rag/domains` | 获取可用 RAG 领域 |
| `GET`  | `/api/rag/history` | 获取检索历史 |

### 简历接口

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/resume/upload` | 上传并解析简历 PDF |
| `GET`  | `/api/resume/status` | 获取简历上传状态 |
| `DELETE` | `/api/resume` | 删除简历 |

### 导师接口

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/advisor/search` | 联网搜索导师信息 |
| `GET`  | `/api/advisor/status` | 获取当前导师状态 |
| `DELETE` | `/api/advisor` | 清除导师信息 |
| `POST` | `/api/advisor/document/upload` | 上传导师文档 |
| `GET`  | `/api/advisor/document/list` | 获取文档列表 |
| `DELETE` | `/api/advisor/document/{filename}` | 删除指定文档 |

### 报告接口

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/report/stream` | 流式生成面试报告（SSE） |
| `GET`  | `/api/report/download/json` | 下载 JSON 格式对话记录 |
| `GET`  | `/api/report/download/txt` | 下载 TXT 格式对话记录 |

### 测试房间接口（导师端）

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/teacher/create` | 创建测试房间 |
| `GET`  | `/api/teacher/rooms` | 列出所有房间 |
| `GET`  | `/api/teacher/room/{id}` | 获取房间详情 |
| `PUT`  | `/api/teacher/room/{id}/close` | 关闭房间 |
| `GET`  | `/api/teacher/room/{id}/results` | 获取学生结果 |

### 测试房间接口（学生端）

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/student/join/{room_id}` | 加入测试房间 |
| `POST` | `/api/student/submit` | 提交测试结果 |

---

## 🎨 个性化定制

### 面试官风格

在控制面板切换预设角色，或选择「自定义」编写完整 System Prompt：

| 风格 | 特点 |
|------|------|
| **温和型** | 循循善诱，充分提示，适合初学者 |
| **正常型（默认）** | 导师面试常规节奏，平衡考察基础与潜力 |
| **压力型** | 高频深挖，检验科研严谨性与抗压表达 |
| **自定义** | 完全自定义 System Prompt |

### 知识库扩展

```bash
# 新增领域只需 3 步：
# 1. 准备 JSONL 数据 → data/<新领域>/qa_xxx.jsonl
# 2. 运行向量化脚本
python scripts/build_cs_vector_store.py
# 3. 前端自动识别 vector_db/ 下的新领域目录
```

### 运行测试

```bash
# 运行所有单元测试
pytest backend/tests/unit/ -v

# 运行基础设施层测试
pytest backend/tests/unit/test_infrastructure/ -v

# 运行服务层测试
pytest backend/tests/unit/test_services/ -v

# 运行带覆盖率报告
pytest backend/tests/ --cov=backend --cov-report=html
```

---

## 🔮 未来规划

- [ ] **多用户并发优化** — 进一步优化 API Key 轮询策略
- [ ] **视频面试分析** — 表情 + 姿态分析模块
- [ ] **多语言面试** — 英文面试官角色
- [ ] **学习路径推荐** — 基于薄弱点生成个性化学习计划
- [ ] **多 Agent 协作** — 技术面 + HR 面联动

---

## 📄 许可证

MIT License

---

<p align="center">
  <strong>🌟 如果这个项目对你有帮助，请给一个 Star 支持！</strong>
</p>
