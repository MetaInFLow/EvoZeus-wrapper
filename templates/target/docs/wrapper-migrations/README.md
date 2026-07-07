# Wrapper Migrations

本目录记录 EvoZeus-wrapper harness version 迁移。这里只记录 wrapper-managed 结构、脚本和治理逻辑的迁移，不记录目标 Skill 的业务内容。

## 迁移原则

- `.evozeus/wrapper.json` 是 wrapper harness version 的事实源。
- `SKILL.md` 中的 `EvoZeus-wrapper 状态检查` 只约束 maintainer/canonical repo 会话中的修改、发布、迁移和 wrapper 维护动作；runtime-only install 不应被 wrapper 治理文件缺失阻断。
- `SKILL.md` 的其他 wrapper 内容只能追加 EvoZeus-wrapper 区域或 migration note，不重写目标 Skill 的业务规则。
- wrapper-managed files 可以按迁移方案复制或合并；如果已有本地修改，必须先做 merge review。
- Skill release version 和 wrapper harness version 是两条版本轴，不能互相覆盖。
- wrapper harness 迁移如果改变可安装 Skill artifact，也必须同步产生目标 Skill patch release entry、tag 和 release notes。

## 每次迁移必须记录

- From wrapper version。
- To wrapper version。
- 迁移原因。
- Planned files / changed files。
- `SKILL.md` 状态检查处理结果。
- `SKILL.md` 的 append-only 处理结果。
- Skill patch release 处理结果。
- 验证命令和结果。
- 回滚方案。
