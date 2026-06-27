# Harness Contract

## 核心判断

EvoZeus-wrapper 的对象不是“所有 prompt”，而是一个已经存在的本地 Skill 文件夹。它不是用户下载入口；用户安装和启动 EvoZeus，由 EvoZeus 在 promoted Skill 或已有本地 Skill 需要 repo 化、反馈闭环和版本治理时路由到 wrapper。

它要把这个文件夹补齐成一个最小自进化驾驶舱：

```text
environment diagnosis
  -> target Skill diagnosis
  -> canonical Skill repo
  -> runtime symlink install
  -> SKILL.md
  -> feedback issue
  -> design doc
  -> PR
  -> CHANGELOG
  -> release
  -> GitHub Pages dashboard
```

## Before / After Contract

| 阶段 | 文件和能力 |
| --- | --- |
| Before | 本地 Skill 文件夹，至少包含 `SKILL.md` |
| After | canonical GitHub repo、GitHub Pages、`.evozeus/wrapper.json`、`CHANGELOG.md`、Issue template、PR template、design doc template、preflight checker、runtime symlink |

## Single Source Contract

同一个 Skill 在本地只允许一个 physical GitHub repo clone。

| 路径 | 语义 |
| --- | --- |
| canonical repo | 唯一事实源 |
| `~/.evozeus/.projects/OWNER/REPO` | 指向 canonical repo 的 EvoZeus 项目指针 |
| `~/.codex/skills/<skill-name>` | 指向 canonical repo 的 Codex runtime 指针 |
| `~/.agents/skills/<skill-name>` | 可选 Agents runtime 指针，保留时也必须指向 canonical repo |

安装副本只是部署入口，不能成为第二事实源。旧 real-directory 安装副本如果与 canonical repo 不一致，必须先 diff、归档或让用户确认。

## 生成后的目标 repo 必须回答

| 问题 | 产物 |
| --- | --- |
| 用户在哪里看这个 Skill 的当前状态？ | `docs/index.md` + GitHub Pages |
| 使用中结果不满意怎么反馈？ | `.github/ISSUE_TEMPLATE/skill-feedback.yml` |
| 修改 Skill 前怎么想清楚？ | `docs/design-doc-template.md` + `docs/designs/*.md` |
| 每次迭代怎么留下记录？ | `CHANGELOG.md` |
| 上传前怎么挡住低质量变更？ | `scripts/evozeus_wrapper_preflight.py` + GitHub Actions |
| release 是否有说明？ | `CHANGELOG.md` tag entry + GitHub release notes |

## Visibility Contract

创建目标 GitHub repo 前，必须让用户选择：

- `public`：适合公开 Skill、公开问题反馈和公开 Pages。
- `private`：适合内部 Skill、客户相关 Skill 或尚未审查的 Skill。

不要默认选择。`public/private` 是产品边界，不是技术细节。

注意：private repo 的 GitHub Pages 可用性取决于 GitHub plan；并且 Pages 发布面可能仍能被外部访问。敏感内容不能进入 `docs/`。

## Evolution Contract

一次 Skill 迭代必须经过：

1. 反馈 Issue：说明不满意结果、期望结果、复现场景、证据边界和影响程度。
2. Design doc：说明修复的 Issue、优化目标、优化方向、怎么优化、怎么验证、release plan。
3. PR：引用 design doc，更新 `SKILL.md` 和 `CHANGELOG.md`。
4. Release：tag 与 `CHANGELOG.md` 对齐，release description 非空。

## Preflight Contract

`scripts/evozeus_wrapper_preflight.py` 至少支持五类检查：

- `doctor`：本地依赖与源头检查。必须确认 `git`、`gh`、`gh auth status`，并验证目标 repo 或 origin remote 可访问；如果当前目录只是安装副本，必须通过 `--repo` 或候选发现确认 canonical source。bootstrap 阶段目标 repo 尚未创建时，允许 `--allow-missing-repo`，但后续发布前必须去掉该豁免。
- `structure`：目标 repo 是否包含驾驶舱必需文件。
- `issue`：Issue 内容是否满足反馈模板字段。
- `pr`：PR 是否有 design doc，且 changelog 有记录。
- `release`：release tag 是否在 changelog 中，release notes 是否非空。

## Lifecycle CLI Contract

`scripts/evozeus_wrapper.py` 负责把运行过程显式拆成阶段：

```bash
python3 scripts/evozeus_wrapper.py env diagnose --json
python3 scripts/evozeus_wrapper.py skill diagnose --target /absolute/path/to/skill --repo OWNER/REPO --json
python3 scripts/evozeus_wrapper.py skill transform --mode bootstrap --target /absolute/path/to/skill --repo OWNER/REPO --visibility private --dry-run --json
python3 scripts/evozeus_wrapper.py publish reinstall --skill-name skill-name --canonical-path /absolute/path/to/repo --target codex --dry-run --json
python3 scripts/evozeus_wrapper.py loop lesson --dry-run --json
python3 scripts/evozeus_wrapper.py loop issue-to-pr --dry-run --json
python3 scripts/evozeus_wrapper.py harness upgrade-check --target /absolute/path/to/skill --json
```

写入、发布、替换安装副本、创建 Issue、创建 PR、启用 Pages 都必须在诊断报告之后进入用户确认。

## Harness Version Contract

目标 Skill release 和 wrapper harness version 是两条版本轴。

- Skill release 描述目标 Skill 行为版本。
- Wrapper harness version 描述 EvoZeus-wrapper 注入的模板、脚本和治理逻辑版本。
- `.evozeus/wrapper.json` 必须记录 `wrapper_repo`、`wrapper_version`、`canonical_repo`、`managed_files` 和 `install_links`。
- wrapper major upgrade 必须用户确认。
- wrapper upgrade 只能改 harness-managed files，不改目标 Skill 业务规则。

## Case: GitHub-backed Skill already exists

`engineering-everything` 自进化时暴露了一个 wrapper 级反模式：agent 先修改安装副本，再查公开 GitHub，最后才发现用户自己的 repo 已存在。正确机制必须进入 wrapper，而不是只留在具体 Skill case 中：

1. 先检查 `git` / `gh` / `gh auth status`。
2. 当前目录在 git repo 内时，先验证 `origin` 是否是可访问 GitHub repo；bootstrap pre-create 阶段可用 `--allow-missing-repo` 验证目标 repo 可创建。
3. 当前目录只是安装副本时，先查当前 `gh` 用户 repo，再查用户所属 org repo，最后才扩大到公开 repo 搜索。
4. lesson 候选先进入 GitHub Issue 队列，再决定是否写入 Skill 内部 lesson / pattern。
5. 安装副本只作为部署目标；GitHub repo clone 才是 canonical source。

## Data Policy

- Public repo 只保存公开或脱敏信息。
- raw private session、客户资料、secret、商业上下文不入仓。
- 需要保留来源时，记录来源类型、时间、路径或公开 URL；不要复制敏感全文。
- 如果 GitHub Pages 可能暴露敏感信息，停止发布 Pages。

## Non-goals

- 不做通用 prompt 管理平台。
- 不做 agent runtime。
- 不做 EvoZeus 的平级入口。
- 不做自动评分神谕。
- 不替代 human review。
- 不把所有 Skill 都迁到一个 repo。
