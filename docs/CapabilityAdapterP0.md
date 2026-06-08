# Capability Adapter P0

更新时间：2026-06-08

Capability Adapter P0 的目标是先把 `$browser`、`$chrome`、`$computer-use` 变成统一、可检查、可记录的 dry-run 能力计划。

P0 不执行真实 GUI 操作。

## 1. 定位

GUI 能力是适配器，不是核心依赖。

当前核心 harness 仍然使用 CLI 和脚本完成：

```text
brief -> plan -> voice -> render -> QA -> package
```

GUI 能力只在需要真实网页演示、登录态页面、桌面软件、文件选择器或上传操作时接入。

## 2. 当前支持能力

| 能力 | 标签 | 用途 | Gate |
|---|---|---|---|
| `browser` | `$browser` | 普通网页、本地 Web Demo、截图、录制前检查 | `execution` |
| `chrome` | `$chrome` | 需要用户已有 Chrome 登录态的页面 | `execution` |
| `computer_use` | `$computer-use` | 桌面 GUI 软件、文件选择器、原生对话框 | `execution` |

## 3. Dry-Run 输出

查看 pipeline 的能力计划：

```bash
ai-video-maker capabilities --pipeline pipeline.example.yml
```

输出：

```text
capability dry-run
mode: dry_run
required: none
- browser: optional, optional, dry_run_only
- chrome: optional, optional, dry_run_only
- computer_use: optional, optional, dry_run_only
```

JSON 输出：

```bash
ai-video-maker capabilities --pipeline pipeline.example.yml --json
```

## 4. Run 产物

当 brief 通过并生成 plan 时，harness 会生成：

```text
runs/<run_id>/plan/capability_plan.yml
```

并写入：

```text
runs/<run_id>/artifacts.yml
```

示例字段：

```yaml
mode: dry_run
required: []
capabilities:
  - name: browser
    label: $browser
    required: false
    gate: execution
    status: optional
    action: dry_run_only
```

## 5. Gate 规则

如果任意 capability 的 `required` 为 `true`：

```yaml
capabilities:
  browser:
    required: true
```

pipeline 会在制作前停在：

```text
awaiting_execution_approval
```

必须确认：

```bash
ai-video-maker approve --run runs/<run_id> --gate execution --summary "确认执行 GUI 操作"
```

P0 仍然不会真的调用 GUI。这个 gate 是给后续真实 adapter 执行前使用的安全边界。

## 6. Smoke 验证

本次执行：

```bash
ai-video-maker run --pipeline pipeline.example.yml --run-id capability-plan-smoke --overwrite
ai-video-maker approve --run runs/capability-plan-smoke --gate brief --summary "确认 capability dry-run smoke brief"
ai-video-maker run --run runs/capability-plan-smoke
ai-video-maker capabilities --run runs/capability-plan-smoke --json
```

结果：

```text
status: awaiting_plan_approval
artifacts: 6
plan/capability_plan.yml generated
```

没有调用 `$browser`、`$chrome`、`$computer-use`，没有打开任何 GUI。

## 7. 下一步

## 7. Browser 本地 Web Demo 预检

新增模板：

```text
templates/pipelines/browser_local_demo.yml
```

该模板描述一个本地 Web Demo 预检任务：

```yaml
capabilities:
  browser:
    required: true
    target_url: "http://localhost:8000"
    viewport:
      width: 1920
      height: 1080
    checks:
      - "page_load"
      - "title_present"
      - "screenshot_non_blank"
    recording:
      enabled: false
      duration_seconds: 10
      output: "assets/browser/local_web_demo.mp4"
```

验证：

```bash
ai-video-maker validate --pipeline templates/pipelines/browser_local_demo.yml
ai-video-maker capabilities --pipeline templates/pipelines/browser_local_demo.yml
```

输出重点：

```text
required: browser
browser_preflight:
  status: ready_for_execution_gate
  target_url: http://localhost:8000
  target_kind: local_web
  recording: False
```

## 8. Browser Preflight Smoke

本次执行：

```bash
ai-video-maker run --pipeline templates/pipelines/browser_local_demo.yml --run-id browser-preflight-smoke --overwrite
ai-video-maker approve --run runs/browser-preflight-smoke --gate brief --summary "确认本地 Web Demo browser preflight brief"
ai-video-maker run --run runs/browser-preflight-smoke
ai-video-maker approve --run runs/browser-preflight-smoke --gate plan --summary "确认 browser preflight 计划但不执行 GUI"
ai-video-maker run --run runs/browser-preflight-smoke
```

结果：

```text
status: awaiting_execution_approval
current_stage: execution
artifacts: 7
```

生成：

```text
runs/browser-preflight-smoke/plan/browser_preflight.yml
```

关键内容：

```yaml
status: ready_for_execution_gate
target_url: http://localhost:8000
target_kind: local_web
actions:
  - open_target_url
  - wait_for_page_load
  - capture_screenshot
  - verify_non_blank_frame
```

这次没有打开 `$browser`，没有录屏，没有进入配音渲染。pipeline 在 `execution` gate 前停住，符合安全边界。

## 9. Browser Adapter P1 结果记录

P1 增加了 `browser-result`，用于把真实浏览器检查结果写回 run。

命令：

```bash
ai-video-maker browser-result \
  --run runs/<run_id> \
  --screenshot output/browser/screenshot.png \
  --url http://localhost:8000/ \
  --title "AI Video Maker Browser Demo" \
  --non-blank
```

写入：

```text
runs/<run_id>/qa/browser_preflight.json
runs/<run_id>/qa/browser_preflight.md
runs/<run_id>/assets/browser/preflight_screenshot.png
```

注意：该命令必须在 `execution` gate 通过后才能执行。

实操记录：

```text
docs/实操记录-BrowserAdapterP1本地页面检查.md
```

## 10. 下一步

1. 为 `recording.enabled: true` 增加录制产物 manifest。
2. 将本地页面截图检查封装成更少手工参数的执行命令。
3. 给 `$chrome` 和 `$computer-use` 增加更严格的账号/文件侧效应确认。
4. 把 browser preflight 截图纳入后续视频剪辑素材计划。
