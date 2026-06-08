# Skills 安装指南

本文档说明如何把 AI Video Maker 的 workflow skills 安装到用户自己的 Codex skills 目录。

## 支持的 skills

完整列表以 `skills/manifest.yml` 为准。当前包括：

```text
ai-video-maker
video-brief
video-plan
video-script
browser-capture
terminal-capture
chrome-capture
desktop-capture
voice-subtitle
edit-render
qa-revision
publish-package
youtube-upload
```

## 安装前检查

先在仓库内运行：

```bash
rtk ".venv/bin/ai-video-maker" skills validate
```

如果输出 `skills passed`，说明 manifest、frontmatter 和 skill 路径有效。

## Dry-run 安装

安装脚本默认不修改目标目录。必须显式传入目标 skills 目录：

```bash
rtk ".venv/bin/python" scripts/install_skills.py --dry-run --target "<codex-skills-dir>"
```

## Copy 安装

复制 skills 到目标目录：

```bash
rtk ".venv/bin/python" scripts/install_skills.py --copy --target "<codex-skills-dir>"
```

## Link 安装

用软链接安装，适合开发者调试：

```bash
rtk ".venv/bin/python" scripts/install_skills.py --link --target "<codex-skills-dir>"
```

## 安全规则

- 默认不覆盖同名 skill。
- 只有显式传 `--force` 才会覆盖。
- 不自动修改 shell 配置。
- 不自动安装全局依赖。
- 不提交 OAuth token、cookie、本地绝对路径或私有邮箱。

## 卸载

删除目标目录中对应的 skill 文件夹或软链接即可。卸载不会影响本仓库源码。
