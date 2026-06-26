---
title: "{{SKILL_NAME}} 自进化驾驶舱"
---

# {{SKILL_NAME}} 自进化驾驶舱

这是 {{SKILL_NAME}} 的最小自进化驾驶舱。它用于公开当前 Skill 状态、收集使用反馈、追踪设计决策和发布记录。

## 当前状态

| 项目 | 内容 |
| --- | --- |
| Skill | [`SKILL.md`]({{REPO_URL}}/blob/main/SKILL.md) |
| Repo | `{{REPO_NAME}}` |
| Visibility | `{{VISIBILITY}}` |
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

每次 Skill 更新必须先写 design doc，再开 PR。

Design doc 至少回答：

- 修复的 Issue 是什么。
- 优化目标是什么。
- 优化方向是什么。
- 怎么优化。
- 怎么验证。
- release 如何说明。

## 上传前检查

```bash
python3 scripts/evozeus_wrapper_preflight.py structure
python3 scripts/evozeus_wrapper_preflight.py pr --design-doc docs/designs/<design-doc>.md
python3 scripts/evozeus_wrapper_preflight.py release --tag v0.1.0 --release-notes release-notes.md
```
