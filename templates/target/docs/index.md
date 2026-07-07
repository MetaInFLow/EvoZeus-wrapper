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
| Wrapper manifest | `.evozeus/wrapper.json` |
| Feedback audit policy | `.evozeus/feedback-policy.json` |
| Feedback audit rule | `.evozeus/audit-rule.md` |
| Wrapper migrations | [`docs/wrapper-migrations/`](wrapper-migrations/) |
| Changelog | [`CHANGELOG.md`]({{REPO_URL}}/blob/main/CHANGELOG.md) |
| Design docs | [`docs/designs/`](designs/) |

## 反馈入口

如果使用中遇到 Skill 输出不满意，请提交 Skill Feedback Issue。Issue 需要包含：

- 不满意的 Skill 结果。
- 期望结果。
- 复现输入或场景。
- 证据边界。
- 影响程度。

## 反馈审计

每轮结束前，如果用户明确纠正、表达不满意、要求换方向，或要求调整可复用机制，先运行反馈审计：

```bash
python3 scripts/evozeus_wrapper.py loop audit \
  --target /absolute/path/to/this-skill \
  --user-input "<current input>" \
  --context "<redacted recent context>" \
  --json
```

`.evozeus/audit-rule.md` 定义语义判断要求，必须返回 `should_capture`、`reason`、`route`、`severity` 和 `evidence_boundary`。`.evozeus/feedback-policy.json` 定义托管模式：`full_managed` 直接提交，`semi_managed` dry-run 请求确认，`manual` 只报告。

## 进化规则

`SKILL.md` 的 frontmatter 后可以包含 `EvoZeus-wrapper 状态检查`，但该段只约束 maintainer/canonical repo 会话中的修改、发布、迁移和 wrapper 维护动作。

如果 `.evozeus/wrapper.json` 或 wrapper tooling 不存在，视为 runtime-only install，继续目标 Skill 业务流程；不要仅因 wrapper 治理文件缺失阻断普通运行。

Wrapper-managed Skill 的源头发现顺序固定：

1. 读取 `.evozeus/wrapper.json`。
2. 检查 `~/.evozeus/.projects/{{REPO_NAME}}` 是否指向 canonical repo。
3. 验证 canonical repo 的 git origin / GitHub repo。
4. 检查 `~/.codex/skills/<skill-name>` 和 `~/.agents/skills/<skill-name>`，它们只能是 runtime pointer。
5. 只有 wrapper 状态无法确认时，才进入 GitHub user/org/public search。

每次维护、发布或迁移 Skill 前，先检查 GitHub latest release 是否有新版本：

```bash
python3 scripts/evozeus_wrapper_preflight.py doctor --repo {{REPO_NAME}}
python3 scripts/evozeus_wrapper_preflight.py version --repo {{REPO_NAME}}
```

运行时集成应通过 start hook 检查 wrapper harness 版本：

```bash
python3 scripts/evozeus_wrapper.py hook start-check \
  --target /absolute/path/to/this-skill \
  --latest-version <latest-wrapper-version> \
  --json
```

hook 只在 `decision.allow` 为 true 时进入 wrapper-managed hook 主链路；`decision.level=block` 时必须先处理 harness 升级或修复。未安装 hook 或 wrapper tooling 的 runtime-only install 继续目标 Skill 业务流程。

每次 Skill 更新必须先写 design doc，再开 PR。根目录 `SKILL.md` 是 repo 化后的可运行入口；`~/.evozeus/.projects/{{REPO_NAME}}` 和 runtime 安装路径应指向同一个 canonical repo，不保留 copied install 作为第二事实源，也不要直接修改 `.codex/skills/...` 或 `.agents/skills/...`。

EvoZeus-wrapper harness 升级时，不能重写目标 Skill 业务段落。先在 EvoZeus-wrapper repo 里生成迁移方案：

```bash
python3 scripts/evozeus_wrapper.py harness upgrade-check --target /absolute/path/to/this-skill --latest-version <wrapper-version> --json
python3 scripts/evozeus_wrapper.py harness upgrade --target /absolute/path/to/this-skill --latest-version <wrapper-version> --dry-run --json
```

迁移记录写入 `docs/wrapper-migrations/`，并记录 from/to wrapper version、planned files、`SKILL.md` 状态检查处理、append-only 处理、Skill patch release 处理、验证命令和回滚方案。wrapper harness version 的事实源是 `.evozeus/wrapper.json`；Skill release 仍以 GitHub release 和 `CHANGELOG.md` 为准。wrapper harness 迁移如果改变可安装 Skill artifact，也必须同步产生目标 Skill patch release entry、tag 和 release notes。

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
python3 scripts/evozeus_wrapper_preflight.py doctor --repo {{REPO_NAME}}
python3 scripts/evozeus_wrapper_preflight.py runtime
python3 scripts/evozeus_wrapper_preflight.py maintainer
python3 scripts/evozeus_wrapper_preflight.py version --repo {{REPO_NAME}}
python3 scripts/evozeus_wrapper_preflight.py pr --design-doc docs/designs/<design-doc>.md
python3 scripts/evozeus_wrapper_preflight.py release --tag {{INITIAL_VERSION}} --release-notes release-notes.md
```
