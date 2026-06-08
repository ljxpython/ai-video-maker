# TODO：AI Video Maker 功能实现路线图

更新时间：2026-06-08

规则：

- 每个阶段完成后，必须通过对应测试再打勾。
- `upload` 和 `publish` 永远不能默认通过。
- `runs/` 里的产物不提交到 Git。

## 主链优先

- [x] Stage 1：实现 `edit-render` skill 和 harness。
- [x] Stage 2：实现 `qa-revision` skill 和 harness。
- [x] Stage 3：实现 `publish-package` skill 和 harness。
- [x] Stage 4：实现 `browser-capture` skill 和 harness。
- [x] Stage 5：补齐仓库讲解、项目介绍、产品演示三类模板。
- [x] Stage 6：更新 README、使用指南、架构文档和实操记录。
- [x] Stage 7：跑完整测试、模板校验、隐私扫描。

## Stage 1：edit-render

目标：

```text
接收 voice-subtitle handoff，生成横屏 16:9 成片。
```

验收：

- [x] 新增 `skills/edit-render/SKILL.md`。
- [x] 新增 `ai-video-maker edit-render --run ...`。
- [x] 输出 `render/draft.mp4`、`render/final_16x9.mp4`、`render/handoff.edit-render.yml`。
- [x] 无录屏素材时用 storyboard 卡片成片。
- [x] 有 browser capture 录屏素材时插入录屏片段，形成“录屏 + 卡片混剪”。
- [x] handoff 下一步是 `qa-revision`。
- [x] 单元测试覆盖缺 handoff、成功输出、CLI parser。

## Stage 2：qa-revision

目标：

```text
接收 edit-render handoff，检查最终视频并输出返修建议。
```

验收：

- [x] 新增 `skills/qa-revision/SKILL.md`。
- [x] 新增 `ai-video-maker qa-revision --run ...`。
- [x] 输出 `qa/report.md`、`qa/ffprobe.json`、`qa/screenshots/frame_6s.png`、`qa/handoff.qa-revision.yml`。
- [x] 检查视频存在、音轨、视频流、字幕非空、关键帧截图。
- [x] handoff 下一步是 `publish-package`。
- [x] 失败时 `revision_skill_suggestion` 指向 `edit-render` 或 `voice-subtitle`。
- [x] 单元测试覆盖成功和失败报告。

## Stage 3：publish-package

目标：

```text
接收 qa-revision handoff，生成 YouTube 发布包，不自动上传。
```

验收：

- [x] 新增 `skills/publish-package/SKILL.md`。
- [x] 新增 `ai-video-maker publish-package --run ...`。
- [x] 输出 `package/video.mp4`、`title.txt`、`description.md`、`tags.txt`、`upload_checklist.md`、`handoff.publish-package.yml`。
- [x] `upload` 和 `publish` gate 保持 pending。
- [x] handoff 下一步是 `upload` gate，而不是自动上传。
- [x] 单元测试覆盖发布包文件和 gate 不变。

## Stage 4：browser-capture

目标：

```text
直接操作本地或公开网页完成演示录制，输出可被 edit-render 混剪的视频素材。
```

验收：

- [x] 新增 `skills/browser-capture/SKILL.md`。
- [x] 新增 `ai-video-maker browser-capture --run ...`。
- [x] 新增依赖 `playwright`。
- [x] 文档注明需要 `python -m playwright install chromium`。
- [x] 必须检查 `execution` gate。
- [x] 支持打开 URL、等待加载、截图、短录屏。
- [x] 输出 `assets/browser/demo.webm`、`assets/browser/screenshot.png`、`qa/browser_capture.md`、`assets/browser/handoff.browser-capture.yml`。
- [x] 第一版不处理登录态 Chrome 和 YouTube Studio。
- [x] 单元测试 mock Playwright，避免 CI 依赖浏览器安装。

## Stage 5：模板

目标：

```text
补齐仓库讲解、项目介绍、产品演示三类 pipeline 模板。
```

验收：

- [x] 新增 `templates/pipelines/repository_demo.yml`。
- [x] 新增 `templates/pipelines/project_intro.yml`。
- [x] 新增 `templates/pipelines/product_demo.yml`。
- [x] 三个模板都能通过 `validate`。
- [x] 模板都包含 must_show、must_avoid、voice、render、upload。

## Stage 6：文档

验收：

- [x] README 增加新 skill 文档入口。
- [x] 使用指南更新完整链路。
- [x] Skills 架构文档更新已实现状态。
- [x] Skills-First 实操记录更新到 `publish-package`。

## Stage 7：最终检查

验收：

- [x] `".venv/bin/python" -m unittest discover -s "tests"` 通过。
- [x] `".venv/bin/ai-video-maker" validate --pipeline "pipeline.example.yml"` 通过。
- [x] `".venv/bin/ai-video-maker" validate --pipeline "templates/pipelines/skills_self_intro_demo.yml"` 通过。
- [x] `git diff --check` 通过。
- [x] 隐私扫描无本地绝对路径、用户名、邮箱。
