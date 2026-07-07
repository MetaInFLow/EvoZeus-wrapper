# Wrapper Migrations

本目录记录 EvoZeus-wrapper harness version 迁移。这里只记录 wrapper-managed 结构、脚本和治理逻辑的迁移，不记录目标 Skill 的业务内容。

## 迁移原则

- `.evozeus_evoinfra/wrapper.json` 是 wrapper harness version 的事实源。
- `SKILL.md` 的 frontmatter 后必须先保留 `EvoZeus-wrapper 状态检查`，再进入目标 Skill 主链路。
- `SKILL.md` 的其他 wrapper 内容只能追加 EvoZeus-wrapper 区域或 migration note，不重写目标 Skill 的业务规则。
- wrapper-managed files 可以按迁移方案复制或合并；如果已有本地修改，必须先做 merge review。
- Skill release version 和 wrapper harness version 是两条版本轴，不能互相覆盖。
- `.evozeus_evoinfra/wrapper.json` 的 `integration.mode` 必须描述事实。没有宿主 hook 文件和 plugin manifest 时，不得记录或宣称 `native_host_hook`。

## 每次迁移必须记录

- From wrapper version。
- To wrapper version。
- 迁移原因。
- Planned files / changed files。
- `SKILL.md` 状态检查处理结果。
- `SKILL.md` 的 append-only 处理结果。
- runtime integration mode 变化及证据。
- 验证命令和结果。
- 回滚方案。
