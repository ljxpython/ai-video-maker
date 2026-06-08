# 实操记录：Browser Adapter P1 本地页面检查

更新时间：2026-06-08

## 1. 本次目标

把 browser capability 从 dry-run 计划推进到可记录的本地页面检查。

本次只做：

```text
打开本地页面
-> 读取当前 URL
-> 读取标题
-> 截图
-> 检查截图非空
-> 写回 run 的 QA 和 artifacts
```

本次不录屏，不上传，不使用 Chrome 登录态，不访问第三方账号页面。

## 2. 新增代码能力

新增模块：

```text
src/ai_video_maker/browser_adapter.py
```

新增 CLI：

```bash
ai-video-maker browser-result \
  --run runs/<run_id> \
  --screenshot output/browser/screenshot.png \
  --url http://localhost:8000/ \
  --title "AI Video Maker Browser Demo" \
  --non-blank
```

`browser-result` 只负责记录外部浏览器检查结果，不直接绑定某个浏览器实现。

安全规则：

```text
execution gate 未通过 -> 拒绝写入 browser preflight result
execution gate 已通过 -> 复制截图，写 JSON/Markdown QA，记录 artifacts
```

## 3. 本地 Demo 页面

新增示例页面：

```text
examples/browser-local-demo/index.html
```

启动本地服务：

```bash
.venv/bin/python -m http.server 8000 --directory examples/browser-local-demo
```

目标地址：

```text
http://localhost:8000
```

## 4. Pipeline 执行

创建 run：

```bash
.venv/bin/ai-video-maker run \
  --pipeline templates/pipelines/browser_local_demo.yml \
  --run-id browser-adapter-p1-smoke \
  --overwrite
```

确认 brief：

```bash
.venv/bin/ai-video-maker approve \
  --run runs/browser-adapter-p1-smoke \
  --gate brief \
  --summary "确认 Browser Adapter P1 本地 demo brief"
```

生成 plan：

```bash
.venv/bin/ai-video-maker run --run runs/browser-adapter-p1-smoke
```

确认 plan：

```bash
.venv/bin/ai-video-maker approve \
  --run runs/browser-adapter-p1-smoke \
  --gate plan \
  --summary "确认 browser preflight plan 并允许进入 execution gate"
```

推进到 execution gate：

```bash
.venv/bin/ai-video-maker run --run runs/browser-adapter-p1-smoke
```

结果：

```text
waiting for execution approval
runs/browser-adapter-p1-smoke
approve execution: ai-video-maker approve --run runs/browser-adapter-p1-smoke --gate execution
```

确认 execution：

```bash
.venv/bin/ai-video-maker approve \
  --run runs/browser-adapter-p1-smoke \
  --gate execution \
  --summary "用户确认执行本地 Browser 页面打开和截图检查，不录屏不上传"
```

## 5. 浏览器执行说明

本次优先尝试连接 in-app Browser，但当前会话没有可用 `iab` browser 实例。

因此本次使用本机已有 Playwright CLI + 系统 Chrome channel 作为 fallback：

```bash
playwright screenshot \
  --channel chrome \
  --viewport-size "1920,1080" \
  --wait-for-selector "h1" \
  http://localhost:8000 \
  output/browser/browser-adapter-p1-smoke.png
```

读取结果：

```text
Current URL: http://localhost:8000/
Title: AI Video Maker Browser Demo
Screenshot: 1920x1080
Non blank: True
```

## 6. 写回结果

执行：

```bash
.venv/bin/ai-video-maker browser-result \
  --run runs/browser-adapter-p1-smoke \
  --screenshot output/browser/browser-adapter-p1-smoke.png \
  --url http://localhost:8000/ \
  --title "AI Video Maker Browser Demo" \
  --non-blank
```

结果：

```text
browser preflight passed: runs/browser-adapter-p1-smoke
```

## 7. QA 结果

状态：

```text
status: browser_preflight_ready
current_stage: browser_preflight
approvals:
  brief: approved
  plan: approved
  execution: approved
  upload: pending
  publish: pending
artifacts: 10
```

生成文件：

```text
runs/browser-adapter-p1-smoke/qa/browser_preflight.json
runs/browser-adapter-p1-smoke/qa/browser_preflight.md
runs/browser-adapter-p1-smoke/assets/browser/preflight_screenshot.png
```

报告摘要：

```text
Status: passed
Page load: True
Title present: True
Screenshot non blank: True
```

## 8. 截图

为方便文档展示，已复制到：

```text
docs/assets/browser-adapter-p1-screenshot.png
```

![Browser Adapter P1 截图](./assets/browser-adapter-p1-screenshot.png)

## 9. 测试

执行：

```bash
.venv/bin/python -m unittest discover -s tests
```

结果：

```text
Ran 32 tests
OK
```

新增覆盖：

- `browser-result` CLI 参数解析。
- execution gate 未确认时拒绝记录浏览器结果。
- execution gate 确认后写入截图、JSON、Markdown 和 artifacts。

## 10. 结论

Browser Adapter P1 的最小闭环已经完成：

```text
browser preflight plan
-> execution gate
-> local page screenshot
-> non-blank check
-> QA report
-> artifact manifest
```

下一步可以做 `recording.enabled: true` 的录屏产物规划，但仍应先限制在本地页面和 execution gate 之后。
