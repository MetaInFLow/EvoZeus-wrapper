# EvoZeus-wrapper

EvoZeus-wrapper 是一个面向静态 `SKILL.md` 的通用 harness：让 Skill 在真实使用中被观察、复盘、评估，并通过审查后的 proposal 逐步进化。

它不是 runtime，也不是新的 Skill 分发仓库。它的价值是把“边用边进化”从口号变成可记录、可比较、可回归的工作流。

## 为什么需要

静态 Skill 的优势是低信任成本：人可以先读，再决定是否让 Agent 执行。但静态 Skill 也有天然问题：

- 真实使用后，经验容易散落在聊天记录里。
- Skill 修改常常缺少 case、run record 和演进理由。
- 一次修正可能改善当前任务，却破坏已有行为。
- runtime、factor、report、skill 文档容易混在一起，边界失真。

EvoZeus-wrapper 的第一版只解决一个问题：为静态 Skill 建立最小可验证演进闭环。

```text
static SKILL.md
  -> case
  -> run card
  -> evaluation notes
  -> evolution proposal
  -> reviewed Skill change
  -> regression case
```

## 职责边界

本 repo 负责：

- 定义静态 Skill harness 的最小 contract。
- 提供 case、run card、evolution proposal 模板。
- 提供可复用的 wrapper 工作流和示例。
- 帮助区分事实、推断、建议和待验证结论。

本 repo 不负责：

- EvoZeus 主协议、治理和社区 intake；这些属于 `EvoZeus`。
- 本地 scanner、runner、CLI、TUI、SQLite ledger 或网络执行；这些属于 `evozeus-infra`。
- Session Signal SKILL 和 official factor tools；这些属于 `evozeus-session-signal-skill`。
- 保存 raw private session、客户资料、secret 或未脱敏 evidence。

## 目录结构

```text
.
├── SKILL.md
├── docs/
│   └── harness-contract.md
├── templates/
│   ├── case.md
│   ├── evolution-proposal.md
│   └── run-card.md
└── examples/
    └── minimal-static-skill/
        └── SKILL.md
```

## 最小使用方式

1. 选择一个目标静态 Skill，记录版本、来源和适用任务。
2. 用 `templates/case.md` 写清楚输入、期望行为和验证方式。
3. 执行时用 `templates/run-card.md` 记录实际表现。
4. 如果需要改 Skill，用 `templates/evolution-proposal.md` 写出问题、证据、改法和回归检查。
5. 只有 proposal 通过后，才修改目标 Skill，并补一个 regression case。

## Public safety

这个 repo 可以 public，但 public 不代表可以放任何素材。

- 不提交 raw private session。
- 不提交客户资料、商业资料、secret、token、cookie、个人隐私。
- 如果 case 需要真实来源，先脱敏，再保留来源类型和判断依据。
- 如果需要执行代码、扫描本地文件、上传数据或联网，切到 `evozeus-infra` 的权限模型。

## 当前状态

Seed repo。第一阶段只固化 contract 和模板，不提前实现 CLI。
