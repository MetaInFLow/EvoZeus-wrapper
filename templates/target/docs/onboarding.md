# 安装、初始化与子 Skill 接入

本页是 wrapper 的通用接入契约。实际命令以 `.evozeus-wrapper/wrapper.json` 的 `onboarding` 字段为准。

## 安装

1. 在 EvoZeus-wrapper repo 中运行 `onboarding.installation.command`，把 runtime install 建成指向 canonical repo 的 symlink。
2. 真实目录不会被删除。先用 `--dry-run` 查看计划；确认归档后显式增加 `--approve-archive`。原目录归档到 `~/.evozeus/archives/runtime-installs/`。
3. 运行 `onboarding.installation.verification`，确认 runtime pointer 和 canonical repo 一致。

## 调用

- 调用触发词和业务入口归目标 Skill 的 canonical `SKILL.md` 所有，wrapper 不猜测业务调用方式。
- 按 `onboarding.invocation.instruction` 在新的消费项目会话中调用 Skill。
- 运行 `onboarding.invocation.verification`，确认宿主加载的是 canonical repo，并通过 consumer-project smoke test。

## 初始化

- 初始化逻辑归目标 Skill 所有，wrapper 不实现 company 或业务专用初始化。
- 当 `onboarding.initialization.required` 为 `true` 时，必须运行其中的 `command`，再运行 `verification`；两者缺一不可。
- 当 `required` 为 `false` 时，不额外推断或执行初始化。

## 生成的子 Skill

- 子 Skill 不继承父级 `.codex/hooks.json`，契约固定为 `hooks_inherited: false`。
- 每个子 Skill 必须单独运行 EvoZeus-wrapper lifecycle，生成自己的 manifest、hook 配置和验证材料。
- 在 Codex 中通过 `/hooks` 审核并信任新建或变更的 hook。
- 完成条件包括子 Skill structure preflight 和 consumer-project smoke test；只有文件生成成功不算完成。
