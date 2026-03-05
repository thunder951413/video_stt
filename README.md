# 视频转写工具

一个基于 Web 的 Bilibili 视频和小宇宙播客转写工具，支持语音转文字、AI 改写等功能。
后续考虑支持更多的视频平台
当前登录的cookie还需要从浏览器中获取

## ✨ 功能特性

- **多平台支持**
  - Bilibili 视频下载与转写
  - 小宇宙播客下载与转写
  - 支持 UP 主空间视频列表获取

- **灵活的下载选项**
  - 仅下载音频（快速转写）
  - 下载完整视频（带视频文件）
  - 支持分 P 视频选择（全部或仅第一 P）

- **强大的语音识别**
  - 基于 whisper.cpp 本地语音识别
  - 支持多种模型尺寸（tiny/base/small/medium/large-v3）
  - 支持多语言识别

- **AI 文本改写**
  - 支持 OpenAI 兼容的 LLM API
  - 流式响应，实时预览改写结果
  - 可自定义改写指令

- **友好的 Web 界面**
  - 现代化的三栏式布局
  - 实时任务进度显示
  - 历史记录管理
  - 文件下载功能

## 🚀 快速开始

### 环境要求

- Python 3.8+
- macOS / Linux / Windows

### 安装步骤

1. **克隆仓库**
```bash
git clone <repository-url>
cd bilibili_summarizer
```

2. **创建虚拟环境**
```bash
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# 或
venv\Scripts\activate  # Windows
```

3. **安装依赖**
```bash
pip install -r backend/requirements.txt
```

4. **安装 whisper.cpp**

需要安装 whisper.cpp 并确保 `whisper-cli` 在系统 PATH 中：

```bash
# macOS 示例
brew install whisper.cpp

# 或从源码编译
# https://github.com/ggerganov/whisper.cpp
```

5. **下载模型**

在 `models/` 目录下放置 whisper.cpp 模型文件（如 `ggml-medium.bin`）

6. **启动服务**
```bash
./run.sh
# 或
python3 -m uvicorn backend.app:app --reload --host 0.0.0.0 --port 8000
```

7. **访问应用**

打开浏览器访问 http://localhost:8000

## ⚙️ 配置说明

### LLM 配置

在 Web 界面中配置 LLM API：

- **Base URL**: OpenAI 兼容 API 的基础地址
- **API Key**: 你的 API 密钥
- **默认模型**: 如 `gpt-4`、`deepseek-chat` 等

### 浏览器 Cookie

对于需要登录的 Bilibili 视频，可以配置 `cookies_from_browser`：

- `brave` - Brave 浏览器
- `chrome` - Chrome 浏览器
- `firefox` - Firefox 浏览器
- `safari` - Safari 浏览器（macOS）

## 📖 使用指南

### 转写视频

1. 在左侧输入视频 URL（Bilibili 或小宇宙）
2. 选择平台和下载选项
3. 选择 whisper 模型（推荐 medium 平衡速度与准确度）
4. 点击"创建任务"
5. 等待下载和转写完成
6. 在中间栏查看转写结果

### AI 改写

1. 在右侧配置 LLM API 设置
2. 选择要改写的转写文件
3. 输入改写指令（或使用默认指令）
4. 点击"开始改写"
5. 实时查看 AI 改写结果
6. 满意后保存到文件

### 管理历史记录

- 在左侧栏查看所有历史任务
- 点击任务标题可重命名
- 点击文件夹图标打开文件所在目录
- 点击删除图标移除任务

## 🛠️ 项目结构

```
bilibili_summarizer/
├── backend/              # 后端 API
│   ├── app.py           # FastAPI 主应用
│   ├── tasks.py         # 任务管理
│   ├── bili_downloader.py    # Bilibili 下载器
│   ├── xiaoyuzhou_downloader.py  # 小宇宙下载器
│   ├── whispercpp.py    # 语音识别
│   ├── llm_api.py       # LLM API 接口
│   └── ...
├── frontend/            # 前端界面
│   └── index.html       # 单页应用
├── models/              # 模型文件目录
├── data/                # 数据存储目录
├── run.sh               # 启动脚本
└── README.md
```

## 🔧 API 文档

启动服务后访问 http://localhost:8000/docs 查看自动生成的 API 文档。

### 主要 API 端点

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/tasks` | POST | 创建转写任务 |
| `/api/tasks/{id}` | GET | 获取任务状态 |
| `/api/tasks/{id}/files` | GET | 列出任务文件 |
| `/api/tasks/{id}/download` | GET | 下载文件 |
| `/api/contexts` | GET | 列出历史任务 |
| `/api/llm/rewrite` | POST | AI 改写（SSE 流式） |
| `/api/bili/list` | GET | 获取 UP 主视频列表 |

## 📝 输出格式

转写结果提供多种格式：

- **原始字幕** (`.srt`) - 带时间戳的字幕文件
- **转写文本** (`.txt`) - 纯文本格式
- **格式化文本** (`.formatted.txt`) - 分段格式化的文本

## ⚠️ 注意事项

1. **版权问题**：请确保你有权下载和转写目标视频内容
2. **Cookie 使用**：使用浏览器 Cookie 时请遵守 Bilibili 的使用条款
3. **模型大小**：更大的模型（如 large-v3）准确度更高但需要更多内存和计算时间
4. **存储空间**：视频文件会占用较多磁盘空间，建议定期清理 `data/` 目录

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License

## 🙏 致谢

- [whisper.cpp](https://github.com/ggerganov/whisper.cpp) - 高效的语音识别
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) - 视频下载
- [FastAPI](https://fastapi.tiangolo.com/) - Web 框架
