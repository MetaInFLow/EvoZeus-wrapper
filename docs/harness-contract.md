# Harness Contract

## 核心判断

顶级 eval harness、agent test harness 和 prompt regression 系统通常有四个共同点：

- Fixture：固定输入和期望行为。
- Trace：记录实际执行过程和输出。
- Judge：明确判断标准，不靠印象打分。
- Change record：每次修改都能解释为什么改、影响什么、如何回归。

EvoZeus-wrapper 借鉴这个结构，但不直接做 runtime。它服务的是静态 `SKILL.md`：一个可读、可审、可复制的 Agent 行为协议。

## Contract

一个被 wrapper 管理的静态 Skill，至少要能回答：

| 问题 | 产物 |
| --- | --- |
| 这个 Skill 要处理什么任务？ | case |
| 这次实际发生了什么？ | run card |
| 哪里好、哪里坏、证据是什么？ | evaluation notes |
| 要怎么改，为什么这样改？ | evolution proposal |
| 怎么避免以后退化？ | regression case |

## Lifecycle

```text
discover
  -> case
  -> run
  -> evaluate
  -> propose
  -> review
  -> patch Skill
  -> regression
```

### Discover

确认目标 Skill、上下文边界和任务类型。不要在不知道目标 Skill 的情况下写通用规则。

### Case

case 是固定输入，不是复盘散文。它必须说明输入、约束、预期行为和验证方式。

### Run

run card 记录一次真实执行。它应该写事实，不应该把解释混进事实。

### Evaluate

评价必须区分：

- 行为正确但表达不好。
- 行为错误但 Skill 没有覆盖。
- Skill 覆盖了但 Agent 没执行。
- 用户需求本身变化。

### Propose

proposal 只能解决一个明确问题。若一次 proposal 想解决多个问题，拆开。

### Review

review 的目标不是让文档更长，而是判断这次修改是否值得进入 Skill。

### Regression

任何已修复的问题都应该形成最小 regression case。否则同类问题会在下一轮 prompt 压缩、模型变化或上下文变化时复发。

## Data Policy

- Public repo 只保存脱敏 case 和公开信息。
- raw private session、客户资料、secret、商业上下文不入仓。
- 需要保留来源时，记录来源类型、时间、路径或公开 URL；不要复制敏感全文。
- 需要执行代码、读取本地大范围文件、联网或上传时，停止在 wrapper 层，改走 `evozeus-infra` 权限模型。

## Ownership Boundary

| 内容 | Owner |
| --- | --- |
| EvoZeus protocol、governance、registry pointer | `EvoZeus` |
| Static Skill wrapper contract、case/run/proposal 模板 | `EvoZeus-wrapper` |
| Local execution kernel、scanner、runner、ledger、CLI/TUI | `evozeus-infra` |
| Session Signal SKILL 和 official factor tools | `evozeus-session-signal-skill` |

## Non-goals

- 不做通用 prompt 管理平台。
- 不做 agent runtime。
- 不做自动评分神谕。
- 不替代 human review。
- 不把所有 Skill 都迁到一个 repo。
