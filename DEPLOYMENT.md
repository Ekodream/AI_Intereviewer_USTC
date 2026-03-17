# AI Lab-InterReviewer 部署指南

## 架构说明

本次重构实现了导师-学生分离架构：

### 导师端
- 访问地址：`http://your-server:8000/static/teacher.html`
- 功能：创建测试房间、管理房间、查看学生结果

### 学生端
- 访问地址：`http://your-server:8000/static/index.html`
- 模式1：练习模式（原有功能，不受影响）
- 模式2：沉浸式模式（原有功能）
- 模式3：测试房间模式（新增，输入房间号参加测试）

## 数据存储结构

```
output/
├── rooms/                    # 房间数据
│   ├── rooms.json           # 房间索引
│   └── {room_id}/           # 单个房间
│       ├── config.json      # 房间配置
│       └── students/        # 学生结果
│           └── {session_id}/
│               ├── metadata.json      # 元数据
│               ├── conversation.json  # 对话记录
│               ├── report.md         # AI报告
│               └── video_*.webm      # 录像
├── reports/                 # 练习模式报告
├── videos/                  # 练习模式视频
└── advisor_docs/            # 导师文档
```

## 启动服务

```bash
cd AI_Intereviewer_USTC
python main.py
```

服务将在 `http://127.0.0.1:8000` 启动

## 使用流程

### 导师创建测试
1. 访问 teacher.html
2. 填写导师姓名
3. 配置面试参数（导师风格、TTS、视频录制等）
4. 点击"创建房间"
5. 获得6位房间号，告知学生

### 学生参加测试
1. 访问 index.html
2. 选择"测试房间模式"
3. 输入6位房间号
4. 开始面试（设置已锁定）
5. 完成后生成报告，结果自动上传

### 导师查看结果
1. 在房间列表中点击"查看结果"
2. 查看所有参与学生
3. 下载对话记录、AI报告

## API 端点

### 导师端 API
- `POST /api/teacher/room/create` - 创建房间
- `GET /api/teacher/rooms` - 列出所有房间
- `GET /api/teacher/room/{room_id}` - 获取房间详情
- `PUT /api/teacher/room/{room_id}/close` - 关闭房间
- `GET /api/teacher/room/{room_id}/results` - 获取学生结果列表
- `GET /api/teacher/room/{room_id}/student/{session_id}` - 获取单个学生详情

### 学生端 API
- `POST /api/student/join/{room_id}` - 加入测试房间
- `POST /api/student/submit` - 提交测试结果

## 注意事项

1. **数据持久化**：房间数据保存在文件系统，服务器重启后仍可访问
2. **会话隔离**：每个学生通过独立的 session_id 区分，数据完全隔离
3. **向后兼容**：练习模式完全不受影响，可继续使用
4. **房间状态**：关闭的房间学生无法加入，但历史数据保留
5. **自动提交**：学生生成AI报告时自动提交结果到导师端

## 新增文件

- `modules/room_manager.py` - 房间管理核心逻辑
- `static/teacher.html` - 导师端界面
- `static/js/teacher.js` - 导师端逻辑

## 修改文件

- `config.py` - 添加 ROOMS_DIR 配置
- `main.py` - 添加导师/学生 API，增强会话管理
- `static/index.html` - 添加测试房间模式入口
- `static/js/app.js` - 添加房间加入逻辑
