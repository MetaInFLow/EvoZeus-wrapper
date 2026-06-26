# AGENTS.md

## 项目约定

- 项目产出默认用中文，关键专有名词和专业名词可以用英文。
- 本 repo 面向 public-ready harness，不保存 raw private session、客户资料、商业资料、secret 或未脱敏 evidence。
- 修改必须保持小步、可解释、可回归；不要为了“通用”提前写框架。

## Repo 职责

EvoZeus-wrapper 负责静态 `SKILL.md` 的使用与演进 harness：

- 记录 case。
- 记录 run card。
- 提出 evolution proposal。
- 把已验证经验转成 Skill 修改。
- 为修改补 regression case。

它不负责 runtime 执行、扫描本地文件、联网、上传、CLI/TUI、ledger、factor tools 或 EvoZeus 主协议治理。

## 编辑原则

1. 先明确目标 Skill、使用场景和成功标准。
2. 先写 case 或 run card，再提修改。
3. 修改 Skill 前必须说明证据：事实、推断、建议要分开。
4. 单次变更只解决一个明确问题。
5. 如果需要执行能力，停止在 contract 层，把实现路由到 `evozeus-infra`。
6. 如果涉及 Session Signal 方法或 official factor tools，把内容路由到 `evozeus-session-signal-skill`。

## 验证标准

- 文档变更至少通过人工阅读检查：边界清楚、无内部废话、无 private 数据。
- 模板变更必须能支持最小闭环：case -> run card -> proposal -> reviewed change -> regression case。
- 新增代码前必须先说明为什么模板或文档无法解决。
