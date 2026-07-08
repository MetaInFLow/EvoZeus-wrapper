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
| After | canonical GitHub repo、GitHub Pages、`.evozeus_evoinfra/wrapper.json`、`CHANGELOG.md`、Issue template、PR template、design doc template、preflight checker、runtime symlink |

## Runtime Integration Contract

Wrapper 不能把所有启动检查都叫作 hook。`.evozeus_evoinfra/wrapper.json` 必须记录当前事实级别：

| mode | 含义 |
| --- | --- |
| `native_host_hook` | Codex project-local hook 已注册在 `.codex/hooks.json` 并有 `.codex/hooks/evozeus_wrapper_start_check.py` 适配器，或其他宿主/plugin lifecycle hook 有可验证证据。 |
| `bootstrap_skill` | 插件/Skill 基础设施可加载控制 Skill，但没有检测到宿主 lifecycle hook 文件。 |
| `prompt_runtime_check` | `SKILL.md` 或 `AGENTS.md` 要求 agent 运行检查；这是 prompt-compliance fallback，不是真 hook。 |
| `manual_only` | 只能手动运行 wrapper 命令；没有可检测的运行时入口。 |

`python3 scripts/evozeus_wrapper.py hook start-check ...` 这类 wrapper CLI 命令不是 runtime hook。只有当 Codex `.codex/hooks.json` 或其他宿主集成自动调用它时，才能被描述为 hook-backed execution。

Preflight 必须阻止能力夸大：如果 manifest 声称 `integration.mode=native_host_hook`，但缺少 Codex project-local hook 文件，也缺少其他宿主/plugin lifecycle hook 证据，结构检查必须失败。

## Single Source Contract

同一个 Skill 在本地只允许一个 physical GitHub repo clone。

| 路径 | 语义 |
| --- | --- |
| canonical repo | 唯一事实源 |
| `~/.evozeus/.projects/OWNER/REPO` | 指向 canonical repo 的 EvoZeus 项目指针 |
| `~/.codex/skills/<skill-name>` | 指向 canonical repo 的 Codex runtime 指针 |
| `~/.agents/skills/<skill-name>` | 可选 Agents runtime 指针，保留时也必须指向 canonical repo |

安装副本只是部署入口，不能成为第二事实源。旧 real-directory 安装副本如果与 canonical repo 不一致，必须先 diff、归档或让用户确认。

## Source Discovery Contract

wrapper-managed Skill 的源头发现顺序固定，不允许跳过：

1. 读取目标 repo 的 `.evozeus_evoinfra/wrapper.json`。
2. 用 manifest 的 `canonical_repo` 推导 `~/.evozeus/.projects/OWNER/REPO`。
3. 检查该 project pointer 必须是 symlink，并 resolve 到 canonical repo。
4. 验证 canonical repo 的 git origin 与 `canonical_repo` 一致，且 GitHub repo 可访问。
5. 再检查 `.codex/skills/<skill-name>` 和 `.agents/skills/<skill-name>`；这些路径只能是 runtime pointer，不是可直接修改的事实源。
6. 只有 wrapper manifest 和 project pointer 都不存在时，才允许进入当前用户 repo、用户 org repo、public GitHub search 的 fallback。

如果 project pointer 缺失、不是 symlink、或与 canonical repo 不一致，preflight 必须失败或给出高优先级错误。runtime real-directory copy 必须报告 warning 或 error，不能被描述为 source。

## 生成后的目标 repo 必须回答

| 问题 | 产物 |
| --- | --- |
| 用户在哪里看这个 Skill 的当前状态？ | `docs/index.md` + GitHub Pages |
| 使用中结果不满意怎么反馈？ | `.github/ISSUE_TEMPLATE/skill-feedback.yml` |
| 修改 Skill 前怎么想清楚？ | `docs/design-doc-template.md` + `docs/designs/*.md` |
| 每次迭代怎么留下记录？ | `CHANGELOG.md` |
| wrapper harness 怎么迁移？ | `docs/wrapper-migrations/` + `.evozeus_evoinfra/wrapper.json` |
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

- `doctor`：本地依赖与源头检查。必须确认 `git`、`gh`、`gh auth status`。当 `.evozeus_evoinfra/wrapper.json` 存在时，必须先验证 wrapper manifest、`~/.evozeus/.projects/OWNER/REPO`、canonical origin 和 runtime pointer；只有 wrapper state 不存在时，才验证目标 repo/origin 或进入候选发现。bootstrap 阶段目标 repo 尚未创建时，允许 `--allow-missing-repo`，但后续发布前必须去掉该豁免。
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
python3 scripts/evozeus_wrapper.py loop audit --target /absolute/path/to/skill --user-input "<input>" --json
python3 scripts/evozeus_wrapper.py loop issue-to-pr --dry-run --json
python3 scripts/evozeus_wrapper.py harness upgrade-check --target /absolute/path/to/skill --latest-version v0.7.0 --json
python3 scripts/evozeus_wrapper.py harness upgrade --target /absolute/path/to/skill --latest-version v0.7.0 --dry-run --json
```

`loop audit` 默认不写 GitHub；它输出 `should_capture`、`route`、`severity`、脱敏 Issue body 和可执行的 `gh issue create` 命令。写入、发布、替换安装副本、创建 Issue、创建 PR、启用 Pages 都必须在诊断报告之后进入用户确认。

## Harness Version Contract

目标 Skill release 和 wrapper harness version 是两条版本轴。

- Skill release 描述目标 Skill 行为版本。
- Wrapper harness version 描述 EvoZeus-wrapper 注入的模板、脚本和治理逻辑版本。
- `.evozeus_evoinfra/wrapper.json` 必须记录 `wrapper_repo`、`wrapper_version`、`canonical_repo`、`managed_files`、`install_links` 和 `integration.mode`。
- wrapper major upgrade 必须用户确认。
- wrapper upgrade 只能改 harness-managed files，不改目标 Skill 业务规则。
- wrapper upgrade 必须生成迁移方案，说明 from/to wrapper version、planned files、`SKILL.md` 状态检查动作、append-only 动作、验证命令和回滚方案。
- 目标 `SKILL.md` 的 frontmatter 后必须先出现 `EvoZeus-wrapper 状态检查`，列出当前 Skill release、wrapper harness version、source contract 检查和对应解决方法；如果当前只是 runtime-only install，不能把安装副本当作事实源，应回 canonical repo 处理维护问题。
- 目标 `SKILL.md` 中的 `EvoZeus-wrapper` 区域只能追加或补缺；如果已经存在，升级时追加 migration note，不改写旧业务段落。
- `docs/wrapper-migrations/` 是 wrapper harness 迁移账本；`CHANGELOG.md` 仍主要记录目标 Skill 行为 release，除非 wrapper 迁移同时改变了 Skill 行为。

## Case: GitHub-backed Skill already exists

`engineering-everything` 自进化时暴露了一个 wrapper 级反模式：agent 先修改安装副本，再查公开 GitHub，最后才发现用户自己的 repo 已存在。正确机制必须进入 wrapper，而不是只留在具体 Skill case 中：

1. 先检查 `git` / `gh` / `gh auth status`。
2. 当前目录在 git repo 内时，先验证 `origin` 是否是可访问 GitHub repo；bootstrap pre-create 阶段可用 `--allow-missing-repo` 验证目标 repo 可创建。
3. 当前目录只是安装副本时，先查当前 `gh` 用户 repo，再查用户所属 org repo，最后才扩大到公开 repo 搜索。
4. lesson 候选先进入 GitHub Issue 队列，再决定是否写入 Skill 内部 lesson / pattern。
5. 安装副本只作为部署目标；GitHub repo clone 才是 canonical source。
6. 已有 repo 的 Skill release 不能重置为 wrapper 的 `v0.1.0`。版本来源顺序是：
   - GitHub latest release tag。
   - `CHANGELOG.md` 最新 `vMAJOR.MINOR.PATCH` 条目，并先为该 tag 创建或确认 GitHub release。
   - 两者都没有时停止，让 owner 选择首个 Skill version。
7. `v0.1.0` 只用于新建目标 repo 的首个 wrapped Skill release；wrapper harness version 另由 `.evozeus_evoinfra/wrapper.json` 记录。

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
