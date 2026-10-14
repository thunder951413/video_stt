# 视频转写工具

一个基于 Web 的 Bilibili 视频和小宇宙播客转写工具，支持语音转文字、AI 改写等功能。
后续考虑支持更多的视频平台
当前登录的cookie还需要从浏览器中获取

## ✨ 功能特性

- **多平台支持**
  - Bilibili 视频下载与转写
  - 小宇宙播客下载与转写
  - 抖音视频下载与转写
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

对于需要登录的视频，可以配置 `cookies_from_browser`：

- `brave` - Brave 浏览器
- `chrome` - Chrome 浏览器
- `firefox` - Firefox 浏览器
- `safari` - Safari 浏览器（macOS）

### 抖音视频链接格式

抖音视频支持多种链接格式，工具会自动处理转换：

**支持的格式：**
1. **标准视频页面**：`https://www.douyin.com/video/视频ID`
2. **短链接**：`https://v.douyin.com/随机字符/`（从App分享获得）
3. **分享链接**：`https://www.iesdouyin.com/share/video/视频ID/`
4. **非标准页面**（自动转换）：
   - 精选页面：`https://www.douyin.com/jingxuan?modal_id=视频ID`
   - 用户主页：`https://www.douyin.com/user/...?modal_id=视频ID&...`
   - 点赞页面：`https://www.douyin.com/user/self?modal_id=视频ID&showTab=like`
   - 发布页面：`https://www.douyin.com/user/...?modal_id=视频ID&showTab=post`
   - 任意页面：`https://www.douyin.com/任意路径?modal_id=视频ID`

**自动转换规则：**
- 检测URL中的`modal_id`参数
- 自动转换为标准视频链接：`https://www.douyin.com/video/视频ID`
- 支持各种抖音页面格式

**常见问题解决：**

1. **"不支持的URL格式"错误**：
   - 确保URL包含`modal_id=视频ID`参数
   - 或使用抖音App分享的短链接

2. **"需要登录/Cookie"错误**：
   - 在浏览器中打开抖音网站 (https://www.douyin.com) 并登录您的账号
   - 返回工具，在"Cookies 来源（浏览器）"输入框中选择对应的浏览器类型（如chrome、brave、firefox）
   - 确保登录状态有效（Cookie未过期）
   - 如果仍然失败，尝试使用抖音App分享的短链接
   - 确保视频是公开可见的（非私密视频）

3. **"视频不可访问"错误**：
   - 视频可能被删除或设为私密
   - 检查视频是否公开可见
   - 尝试使用其他视频链接

**最佳实践：**
1. 使用抖音App分享功能获取短链接（最可靠）
2. 确保已登录抖音并配置浏览器Cookie
3. 优先使用公开可见的视频

### 抖音 UP 主批量下载

支持获取抖音 UP 主发布的所有视频列表，批量下载转写：

**使用步骤：**
1. 选择"抖音"平台
2. 输入 UP 主主页链接，格式如：`https://www.douyin.com/user/用户ID`
3. 点击"获取UP主视频列表"按钮
4. 在弹出的对话框中选择要下载的视频（支持全选/取消全选）
5. 点击"开始批量下载"

**注意事项：**
- 首次使用需要安装 playwright 浏览器：`playwright install chromium`
- 由于抖音反爬机制，可能需要多次尝试或等待一段时间
- 建议配置浏览器 Cookie 以提高成功率
- 单次最多获取 100 个视频

## 📖 使用指南

### 转写视频

1. 在左侧输入视频 URL（Bilibili、小宇宙或抖音）
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
│   ├── douyin_downloader.py  # 抖音下载器
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
| `/api/tasks/batch` | POST | 批量创建转写任务 |
| `/api/tasks/{id}` | GET | 获取任务状态 |
| `/api/tasks/{id}/files` | GET | 列出任务文件 |
| `/api/tasks/{id}/download` | GET | 下载文件 |
| `/api/contexts` | GET | 列出历史任务 |
| `/api/llm/rewrite` | POST | AI 改写（SSE 流式） |
| `/api/bili/list` | GET | 获取 B 站 UP 主视频列表 |
| `/api/douyin/user/videos` | GET | 获取抖音 UP 主视频列表 |

## 📝 输出格式

转写结果提供多种格式：

- **原始字幕** (`.srt`) - 带时间戳的字幕文件
- **转写文本** (`.txt`) - 纯文本格式
- **格式化文本** (`.formatted.txt`) - 分段格式化的文本

## ⚠️ 注意事项

1. **版权问题**：请确保你有权下载和转写目标视频内容
2. **Cookie 使用**：使用浏览器 Cookie 时请遵守各平台的使用条款（Bilibili、抖音等）
3. **抖音限制**：抖音视频可能需要登录才能下载高清版本，建议配置浏览器Cookie
4. **模型大小**：更大的模型（如 large-v3）准确度更高但需要更多内存和计算时间
5. **存储空间**：视频文件会占用较多磁盘空间，建议定期清理 `data/` 目录

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License

## 🙏 致谢

- [whisper.cpp](https://github.com/ggerganov/whisper.cpp) - 高效的语音识别
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) - 视频下载
- [FastAPI](https://fastapi.tiangolo.com/) - Web 框架
