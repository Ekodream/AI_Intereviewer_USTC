# 🎯 AI 面试官 — Cybernetic Command

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-blue?logo=python" alt="Python">
  <img src="https://img.shields.io/badge/LLM-Qwen--Turbo/Max-green" alt="LLM">
  <img src="https://img.shields.io/badge/RAG-ChromaDB-orange" alt="RAG">
  <img src="https://img.shields.io/badge/TTS-Edge--TTS-purple" alt="TTS">
  <img src="https://img.shields.io/badge/Frontend-Glassmorphism%20Dashboard-0a0e1a" alt="UI">
  <img src="https://img.shields.io/badge/Backend-FastAPI-009688" alt="Framework">
</p>

> **一款面向技术求职者的 AI 面试陪练系统**，通过大语言模型模拟真实面试官，提供全流程、多维度、沉浸式的面试训练体验。前端采用 **「指挥舱」** 深空主题 Dashboard 设计，所有核心功能一屏可达，零 Tab 切换。

---

## 📋 目录

- [核心功能](#-核心功能)
- [界面设计](#-界面设计)
- [系统架构](#-系统架构)
- [技术栈](#-技术栈)
- [快速开始](#-快速开始)
- [项目结构](#-项目结构)
- [个性化定制](#-个性化定制)
- [未来规划](#-未来规划)

---

## 🚀 核心功能

### 全流程面试模拟

系统支持完整的 **8 阶段面试流程**，顶部进度条实时追踪当前阶段：

```
开始 → 自我介绍 → 项目介绍 → 项目问答 → 技术基础 → 代码题目 → 候选人反问 → 结束
```

### 功能矩阵

| 功能 | 说明 |
|------|------|
| **语音面试** | Web Audio API 录音 → StepFun ASR 识别 → 自动发送至对话 |
| **文字对话** | SSE 流式响应，实时逐字渲染 AI 回复 |
| **流式 TTS** | Edge-TTS 句子级并行合成，边生成边播放，首句响应 < 2s |
| **RAG 知识库** | ChromaDB 向量检索，5 大 CS 领域 120+ 专业题目 |
| **代码编辑器** | 多语言 IDE 面板，进入代码阶段自动弹出，支持提交历史 |
| **AI 面试报告** | Qwen-max 深度推理模式，多维度加权评分，Markdown 导出 |
| **简历解析** | PDF 上传 → AI 分析，面试官将针对性提问 |
| **面试官人格** | 温和型 / 正常型 / 压力型 / 完全自定义 Prompt |

### 知识库覆盖

| 领域 | 文件 | 内容 |
|------|------|------|
| 后端开发 | `qa_backend.jsonl` | 框架、并发、缓存、消息队列等 |
| 数据库 | `qa_database.jsonl` | 索引、事务、分库分表、SQL 优化 |
| 数据结构 | `qa_datastructure.jsonl` | 树、图、堆、高级数据结构 |
| 计算机网络 | `qa_network.jsonl` | TCP/IP、HTTP、DNS、安全协议 |
| 系统设计 | `qa_system_design.jsonl` | 高并发架构、分布式、微服务 |

---

## 🎨 界面设计

### 「指挥舱」Cybernetic Command 主题

前端采用 **深空 Glassmorphism Dashboard** 设计语言，颠覆传统 Tab 切换布局：

```
┌─────────────────────────────────────────────────────────────────┐
│  [≡]  AI Interview · Cybernetic Command                        │
│       ●──●──●──●──○──○──○   面试阶段进度条    [+] [📊] [📚]  │
├──────┬──────────────────────────────────────────┬───────────────┤
│      │                                          │               │
│ 控   │         中央对话区                        │  IDE 面板     │
│ 制   │     (语音 + 文字统一界面)                  │  (代码阶段    │
│ 面   │                                          │   自动弹出)   │
│ 板   │     [TTS 浮层播放器]                      │               │
│      │                                          │  RAG / 报告   │
│      │                                          │  右侧抽屉     │
│      ├──────────────────────────────────────────┤               │
│      │  🎤  [  输入你的回答...            ➤ ]   │               │
└──────┴──────────────────────────────────────────┴───────────────┘
```

### 设计系统

| 维度 | 规格 |
|------|------|
| **主色** | `#060a14` 深空黑 |
| **辅助色** | `#141829` 舱体灰 |
| **强调色** | `#00d4ff → #a855f7` 霓虹蓝 → 量子紫渐变 |
| **字体** | Inter + Noto Sans SC · 代码: JetBrains Mono |
| **质感** | `backdrop-filter: blur(24px)` 毛玻璃面板 |
| **间距** | 8px 基准网格 |
| **圆角** | 8px 按钮 / 12px 卡片 / 9999px 胶囊输入框 |

### 交互亮点

- **录音光环球 (Record Orb)** — 带脉冲波纹扩散动画的语音按钮
- **面试阶段星际航线** — 顶部进度节点发光 + 脉冲，完成后流光连线
- **毛玻璃消息气泡** — 用户消息霓虹渐变，AI 回复半透明悬浮
- **右侧滑入抽屉** — RAG 知识库、面试报告按需呼出，互斥动画
- **IDE 自动联动** — 进入代码题阶段(Phase 6)，编辑器面板自动展开
- **`prefers-reduced-motion`** — 尊重用户减少动画偏好设置

---

## 🏗️ 系统架构

```
用户浏览器 (原生 HTML/CSS/JS)
    │
    ├── 语音录制 ──→ POST /api/asr ──→ StepFun ASR
    │
    ├── 文字/语音消息 ──→ POST /api/chat/stream (SSE)
    │                          │
    │                          ├── RAG 检索 (ChromaDB)
    │                          ├── LLM 流式生成 (Qwen-Turbo)
    │                          └── 句子级 TTS (Edge-TTS)
    │
    ├── 简历上传 ──→ POST /api/resume/upload ──→ PDF 解析 + AI 分析
    │
    └── 报告生成 ──→ POST /api/report/stream ──→ Qwen-Max 深度推理
```

### 前后端分离架构

- **后端 (FastAPI)** — 核心引擎：LLM 流式对话、SSE 推送、TTS/ASR 处理、RAG 检索、简历解析、报告生成。通过 `StaticFiles` 托管前端静态资源。
- **前端 (HTML + CSS + JS)** — 原生 Web 技术栈：Glassmorphism Dashboard 布局，Web Audio API 录音，SSE 流式渲染，队列式 TTS 播放。

---

## 🛠️ 技术栈

### 核心框架

| 组件 | 技术 | 说明 |
|------|------|------|
| **后端** | FastAPI | 异步高性能、SSE 流式推送、自动 API 文档 |
| **LLM** | 阿里云 DashScope (Qwen-Turbo/Max) | 国内低延迟，支持流式输出与思考模式 |
| **向量库** | ChromaDB + DashScope Embedding | 本地持久化、元数据过滤 |
| **RAG** | LangChain | 文本分块 (800 tokens, 50 overlap) |
| **TTS** | Edge-TTS | 免费零成本、多声色可选 |
| **ASR** | StepFun step-asr | 中文识别准确率高 |
| **简历解析** | pdfplumber + LLM | PDF 提取 → AI 结构化分析 |

### 前端技术

| 技术 | 用途 |
|------|------|
| **HTML5 语义化** | 页面结构 |
| **CSS3 变量 + Glassmorphism** | 深空主题设计系统 |
| **Font Awesome 6** (CDN) | 图标体系 |
| **Google Fonts** (CDN) | Inter + Noto Sans SC + JetBrains Mono |
| **Web Audio API** | 浏览器录音 |
| **SSE (EventSource)** | 流式对话接收 |
| **HTML5 Audio** | TTS 队列播放 |

### 关键优化

| 优化点 | 方案 | 效果 |
|--------|------|------|
| 句子级流式 TTS | 正则检测句子边界，完整句立即送 TTS | 首句响应 < 2s |
| API Key 轮询 | 8 Key 轮询 + 智能冷却 | 突破单 Key 限流 |
| 有序音频推送 | Counter 标记 + 顺序输出 | 播放无乱序 |

---

## ⚡ 快速开始

### 环境要求

- Python 3.10+
- 阿里云 DashScope API Key
- StepFun API Key（ASR 语音识别）

### 安装与运行

```bash
# 1. 克隆项目
git clone https://github.com/your-repo/ai_interviewer.git
cd ai_interviewer

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置 API Key（编辑 config.py 或设置环境变量）
export DASHSCOPE_API_KEY="your-dashscope-key"
export STEPFUN_API_KEY_1="your-stepfun-key"

# 4. 构建知识库向量索引
python scripts/build_cs_vector_store.py

# 5. 启动服务
uvicorn main:app --host 0.0.0.0 --port 8000
```

### 访问

| 地址 | 说明 |
|------|------|
| `http://localhost:8000` | Web 主界面 |
| `http://localhost:8000/docs` | FastAPI 交互文档 |

---

## 📁 项目结构

```
AI_Interviewer_USTC/
├── main.py                        # FastAPI 后端入口，挂载静态资源
├── config.py                      # 配置中心 (API Key、模型、路径)
├── requirements.txt               # Python 依赖
├── README.md
│
├── modules/                       # 后端核心模块
│   ├── llm_agent.py              # LLM 流式对话代理
│   ├── rag_engine.py             # RAG 向量检索引擎
│   ├── audio_processor.py        # TTS 合成 + ASR 识别
│   ├── interview_manager.py      # 面试阶段状态机
│   ├── ai_report.py              # AI 评价报告生成
│   └── resume_parser.py          # PDF 简历解析
│
├── static/                        # 前端 (Cybernetic Command 主题)
│   ├── index.html                # Dashboard 主页面
│   ├── css/
│   │   └── style.css             # 深空 Glassmorphism 设计系统
│   └── js/
│       ├── app.js                # 应用初始化、设置、抽屉面板、报告
│       ├── chat.js               # SSE 对话、阶段检测、IDE 联动
│       ├── audio.js              # Web Audio API 录音
│       └── tts-stream.js         # 流式 TTS 队列播放器
│
├── data/                          # 数据集
│   └── cs/                       # CS 知识库 (JSONL)
│       ├── qa_backend.jsonl
│       ├── qa_database.jsonl
│       ├── qa_datastructure.jsonl
│       ├── qa_network.jsonl
│       └── qa_system_design.jsonl
│
├── vector_db/                     # ChromaDB 持久化向量库
│   └── cs/
│
├── scripts/
│   └── build_cs_vector_store.py  # 知识库向量化构建脚本
│
├── output/
│   ├── reports/                  # 面试报告输出
│   └── videos/                   # 预留
│
├── temp_audio/                    # TTS/ASR 临时音频文件
│
└── components/                    # (旧版 Streamlit UI 组件，已弃用)
```

---

## 🎨 个性化定制

### 面试官角色

在控制面板中切换预设角色，或选择「自定义」编写完整 System Prompt：

- **温和型** — 循循善诱，给予充分提示
- **正常型** — 标准技术面试节奏
- **压力型** — 高频追问，模拟高压场景

### 知识库扩展

```bash
# 新增领域只需 3 步：
# 1. 准备 JSONL 数据 → data/new_domain/qa_xxx.jsonl
# 2. 运行向量化脚本 → python scripts/build_cs_vector_store.py
# 3. 前端自动识别 vector_db/ 下的新领域目录
```

### TTS 声音

Edge-TTS 支持多种中文声色，在 `config.py` 中配置：
- `zh-CN-YunjianNeural` — 云健（沉稳磁性，默认）
- `zh-CN-YunxiNeural` — 云希（年轻活泼）
- `zh-CN-XiaoxiaoNeural` — 晓晓（甜美女声）

---

## 🔮 未来规划

- [ ] **视频面试模式** — WebRTC 实时视频 + 表情追踪
- [ ] **代码沙盒** — 在线运行与自动评测
- [ ] **多语言面试** — 英文面试官角色
- [ ] **多 Agent 协作** — 技术面 + HR 面联动
- [ ] **学习路径推荐** — 基于薄弱点生成个性化学习计划

---

## 📄 许可证

MIT License

---

<p align="center">
  <strong>🌟 如果这个项目对你有帮助，请给一个 Star 支持！</strong>
</p>
