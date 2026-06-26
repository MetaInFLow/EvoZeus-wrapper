---
title: "{{SKILL_NAME}} 自进化驾驶舱"
---

# {{SKILL_NAME}} 自进化驾驶舱

这是 {{SKILL_NAME}} 的最小自进化驾驶舱。它用于公开当前 Skill 状态、收集使用反馈、追踪设计决策和发布记录。

## 当前状态

| 项目 | 内容 |
| --- | --- |
| Skill | [`SKILL.md`]({{REPO_URL}}/blob/main/SKILL.md) |
| 本地 Skill 镜像 | `~/.evozeus/.projects/{{REPO_NAME}}/SKILL.md` |
| Repo | `{{REPO_NAME}}` |
| Visibility | `{{VISIBILITY}}` |
| 当前版本 | `{{INITIAL_VERSION}}` |
| Changelog | [`CHANGELOG.md`]({{REPO_URL}}/blob/main/CHANGELOG.md) |
| Design docs | [`docs/designs/`](designs/) |

## 反馈入口

如果使用中遇到 Skill 输出不满意，请提交 Skill Feedback Issue。Issue 需要包含：

- 不满意的 Skill 结果。
- 期望结果。
- 复现输入或场景。
- 证据边界。
- 影响程度。

## 进化规则

每次运行 Skill 前，先检查 GitHub latest release 是否有新版本：

```bash
python3 scripts/evozeus_wrapper_preflight.py version --repo {{REPO_NAME}}
```

每次 Skill 更新必须先写 design doc，再开 PR。根目录 `SKILL.md` 是 repo 化后的可运行入口；`~/.evozeus/.projects/{{REPO_NAME}}/SKILL.md` 保留 bootstrap 时的本地 Skill 项目镜像，用于对照后续演进。

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
- `MINOR`：新增筛选能力、必需证据规则或 harness 行为。
- `PATCH`：文案、示例、bug fix、校验修复或不破坏兼容性的澄清。

## 上传前检查

```bash
python3 scripts/evozeus_wrapper_preflight.py structure
python3 scripts/evozeus_wrapper_preflight.py version --repo {{REPO_NAME}}
python3 scripts/evozeus_wrapper_preflight.py pr --design-doc docs/designs/<design-doc>.md
python3 scripts/evozeus_wrapper_preflight.py release --tag {{INITIAL_VERSION}} --release-notes release-notes.md
```
