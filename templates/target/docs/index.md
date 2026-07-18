---
title: "{{SKILL_NAME}} 自进化驾驶舱"
---

# {{SKILL_NAME}} 自进化驾驶舱

这是 {{SKILL_NAME}} 的最小自进化驾驶舱。它用于公开当前 Skill 状态、收集使用反馈、追踪设计决策和发布记录。

## 当前状态

| 项目 | 内容 |
| --- | --- |
| Skill | [`SKILL.md`]({{REPO_URL}}/blob/main/SKILL.md) |
| EvoZeus 项目指针 | `~/.evozeus/.projects/{{REPO_NAME}}` |
| Repo | `{{REPO_NAME}}` |
| Visibility | `{{VISIBILITY}}` |
| 当前 Skill 版本 | `{{CURRENT_VERSION}}` |
| Wrapper harness 版本 | `{{WRAPPER_VERSION}}` |
| Wrapper manifest | `.evozeus-wrapper/wrapper.json` |
| Codex hook registration | `.codex/hooks.json` |
| Codex hook adapter | `.evozeus-wrapper/hooks/evozeus_wrapper_start_check.py` |
| Wrapper migrations | [`.evozeus-wrapper/docs/migrations/`](migrations/) |
| 安装与接入 | [`.evozeus-wrapper/docs/onboarding.md`](onboarding.html) |
| Changelog | [`.evozeus-wrapper/CHANGELOG.md`]({{REPO_URL}}/blob/main/.evozeus-wrapper/CHANGELOG.md) |
| Design docs | [`.evozeus-wrapper/docs/designs/`](designs/) |

## 反馈入口

如果使用中遇到 Skill 输出不满意，请提交 Skill Feedback Issue。Issue 需要包含：

- 不满意的 Skill 结果。
- 期望结果。
- 复现输入或场景。
- 证据边界。
- 影响程度。

## 进化规则

`SKILL.md` 的 frontmatter 后第一段必须是 `EvoZeus-wrapper 状态检查`。该状态检查先确认当前 Skill release、wrapper harness version 和 source contract；如果当前只是 runtime-only install，不能把安装副本当作事实源，应回 canonical repo 处理维护问题。

`.evozeus-wrapper/wrapper.json` 的 `integration.mode` 说明当前运行时集成等级：

- `native_host_hook`：Codex project-local hook 已注册在 `.codex/hooks.json`，或其他宿主/plugin lifecycle hook 已安装并有证据。
- `bootstrap_skill`：插件 Skill 基础设施可加载控制 Skill，但没有检测到宿主 lifecycle hook。
- `prompt_runtime_check`：靠 `SKILL.md` / `AGENTS.md` 说明要求 agent 执行检查，不是真 hook。
- `manual_only`：只能手动运行 wrapper 命令。

Codex 会从 trusted `.codex/` layer 发现 project-local hook；新建或变更 hook 后，需要通过 `/hooks` 审核并信任。运行时可用 `EVOZEUS_WRAPPER_LATEST_VERSION=vMAJOR.MINOR.PATCH` 强制检查最新 wrapper 版本；用 `EVOZEUS_WRAPPER_HOOK_ENFORCEMENT=strict` 可以在任何可升级版本存在时阻断 wrapper-managed 执行。

安装、调用、初始化和子 Skill hook 接入以 `.evozeus-wrapper/wrapper.json` 的 `onboarding` 字段及 [onboarding 指南](onboarding.html) 为准。子 Skill 不继承父级 hook，必须单独接入 wrapper、通过 `/hooks` 信任审核，并完成 structure preflight 和 consumer-project smoke test。

Wrapper-managed Skill 的源头发现顺序固定：

1. 读取 `.evozeus-wrapper/wrapper.json`。
2. 检查 `~/.evozeus/.projects/{{REPO_NAME}}` 是否指向 canonical repo。
3. 验证 canonical repo 的 git origin / GitHub repo。
4. 检查 `~/.codex/skills/<skill-name>` 和 `~/.agents/skills/<skill-name>`，它们只能是 runtime pointer。
5. 只有 wrapper 状态无法确认时，才进入 GitHub user/org/public search。

每次运行 Skill 前，先检查 GitHub latest release 是否有新版本：

```bash
python3 .evozeus-wrapper/scripts/evozeus_wrapper_preflight.py doctor --repo {{REPO_NAME}}
python3 .evozeus-wrapper/scripts/evozeus_wrapper_preflight.py version --repo {{REPO_NAME}}
```

每次 Skill 更新必须先写 design doc，再开 PR。根目录 `SKILL.md` 是 repo 化后的可运行入口；`~/.evozeus/.projects/{{REPO_NAME}}` 和 runtime 安装路径应指向同一个 canonical repo，不保留 copied install 作为第二事实源，也不要直接修改 `.codex/skills/...` 或 `.agents/skills/...`。

EvoZeus-wrapper harness 升级时，不能重写目标 Skill 业务段落。先在 EvoZeus-wrapper repo 里生成迁移方案：

```bash
python3 scripts/evozeus_wrapper.py harness upgrade-check --target /absolute/path/to/this-skill --json
python3 scripts/evozeus_wrapper.py harness upgrade --target /absolute/path/to/this-skill --latest-version <wrapper-version> --dry-run --json
```

迁移记录写入 `.evozeus-wrapper/docs/migrations/`，并记录 from/to wrapper version、planned files、`SKILL.md` 状态检查处理、append-only 处理、验证命令和回滚方案。wrapper harness version 的事实源是 `.evozeus-wrapper/wrapper.json`；Skill release 仍以 GitHub release 和 `.evozeus-wrapper/CHANGELOG.md` 为准。

Design doc 至少回答：

- 修复的 Issue 是什么。
- 优化目标是什么。
- 优化方向是什么。
- 怎么优化。
- 怎么验证。
- release 如何说明。

## Release 版本标准

使用 `vMAJOR.MINOR.PATCH`：

- `MAJOR`：不兼容的 Skill 行为或输出格式变化。
- `MINOR`：新增能力、必需证据规则或 harness 行为。
- `PATCH`：文案、示例、bug fix、校验修复或不破坏兼容性的澄清。

## 上传前检查

```bash
python3 .evozeus-wrapper/scripts/evozeus_wrapper_preflight.py doctor --repo {{REPO_NAME}}
python3 .evozeus-wrapper/scripts/evozeus_wrapper_preflight.py structure
python3 .evozeus-wrapper/scripts/evozeus_wrapper_preflight.py version --repo {{REPO_NAME}}
python3 .evozeus-wrapper/scripts/evozeus_wrapper_preflight.py pr --design-doc .evozeus-wrapper/docs/designs/<design-doc>.md
python3 .evozeus-wrapper/scripts/evozeus_wrapper_preflight.py release --tag {{INITIAL_VERSION}} --release-notes release-notes.md
```
