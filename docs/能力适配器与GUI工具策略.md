# 能力适配器与 GUI 工具策略

更新时间：2026-06-08

## 1. 结论

`$browser`、`$chrome`、`$computer-use` 不是项目核心依赖，而是按需启用的能力适配器。

核心流程必须在没有 GUI 工具的情况下也能跑：

```text
brief -> plan -> script -> voice -> subtitle -> render -> qa -> package
```

GUI 工具只在需要真实网页、登录态、桌面软件或平台上传时启用：

```text
capture -> browser/chrome/computer-use
upload -> chrome/computer-use/API
```

## 2. 为什么不能把 GUI 工具做成硬依赖

如果硬依赖 GUI 工具，会有几个破问题：

- 环境差异大：每台机器装的软件、分辨率、权限都不一样。
- 可复现差：GUI 状态、弹窗、登录态会变。
- 安全风险高：登录、上传、发布、删除都可能产生外部副作用。
- 自动化不稳定：坐标、窗口布局、语言、主题都会影响结果。

所以工程上必须分层：

```text
Core Harness: 稳定、可测试、可复现
Capability Adapters: 按需接入 browser/chrome/computer-use
Human Confirmation: 控制高风险动作
```

## 3. 能力矩阵

| 能力 | 是否必需 | 最适合做什么 | 风险 |
|---|---:|---|---|
| CLI/Python/FFmpeg/MoviePy | 必需 | 渲染、配音、字幕、QA、发布包 | 低 |
| `$browser` | 可选 | 普通网页、本地 Demo、截图、录制、DOM 验证 | 中 |
| `$chrome` | 可选 | 已登录网站、YouTube Studio、账号后台 | 高 |
| `$computer-use` | 可选 | 桌面 GUI、OBS、文件选择器、剪辑软件 | 高 |
| YouTube API | 可选 | 自动上传、设置元数据 | 高 |

## 4. 选择规则

### 4.1 录制普通 Web Demo

优先：

```text
$browser
```

适用：

- 本地 Web App。
- 文档站。
- 无需登录的产品页面。
- 可复现的网页操作。

### 4.2 操作已登录网站

优先：

```text
$chrome
```

适用：

- YouTube Studio。
- 已登录的产品后台。
- 用户明确允许使用登录态的网页。

限制：

- 不读取 cookie、localStorage、密码、会话数据。
- 上传、发布、提交前必须确认。

### 4.3 操作桌面软件

优先：

```text
$computer-use
```

适用：

- OBS。
- 剪映、Kdenlive、DaVinci Resolve。
- 原生文件选择器。
- 只能通过 GUI 操作的软件。

限制：

- 能用 CLI/API 做的不要上 GUI。
- 安装软件、删除文件、上传文件、修改系统设置必须确认。

## 5. pipeline.yml 中的声明方式

示例：

```yaml
capabilities:
  browser:
    required: false
  chrome:
    required: false
  computer_use:
    required: false

capture:
  tasks:
    - id: "record_web_demo"
      adapter: "browser"
      requires: ["$browser"]
      confirmation: "not_required"
    - id: "record_desktop_editor"
      adapter: "computer_use"
      requires: ["$computer-use"]
      confirmation: "when_side_effect"

upload:
  enabled: true
  adapter: "chrome"
  requires: ["$chrome"]
  confirmation: "required"
```

## 6. 运行时降级策略

如果某个能力不可用：

| 缺失能力 | 降级方案 |
|---|---|
| `$browser` 不可用 | 使用 Playwright CLI 或跳过网页录制，生成脚本和发布包 |
| `$chrome` 不可用 | 只生成 YouTube 上传包，让用户手动上传 |
| `$computer-use` 不可用 | 优先使用 CLI/API；需要桌面 GUI 的步骤标记为 blocked |
| YouTube API 不可用 | 用 `$chrome` 辅助 YouTube Studio，或生成手动上传包 |

## 7. 安全策略

所有外部副作用都要动作前确认：

- 上传文件。
- 发布视频。
- 修改公开视频元数据。
- 评论、点赞、发消息。
- 创建 OAuth/API key。
- 使用账号登录态执行提交动作。
- 删除、覆盖、移动重要文件。

确认格式要包含：

```text
操作类型
目标平台/账号
要发送或上传的数据
可见性和影响范围
是否可撤销
```

## 8. 项目实现建议

能力适配器后续放到：

```text
src/ai_video_maker/adapters/
  browser.py
  chrome.py
  computer_use.py
  youtube_api.py
```

核心 harness 不直接依赖 GUI 工具，只通过 adapter 接口调用。

