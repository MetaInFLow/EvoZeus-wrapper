# EvoZeus-wrapper

EvoZeus-wrapper 是 EvoZeus 母体调度下的静态 Skill 演进 harness，用来给本地静态 `SKILL.md`、根入口为 `AGENTS.md` 的 runtime kit，或由 hook / plugin 控制的 Skill bundle 构建最小自进化驾驶舱。

用户入口是 EvoZeus，不是 EvoZeus-wrapper。只有当 EvoZeus 判断一个 promoted Skill 或已有本地 Skill 需要 repo 化、反馈闭环和版本治理时，才路由到本 repo。

本 repo 的 root `SKILL.md` 只做薄入口，不承载完整操作流程。实际使用协议放在 `skills/using-evozeus-wrapper/SKILL.md`，再由它按阶段调用 environment diagnosis、target diagnosis、evolution surface diagnosis、status assessment、transform、publish/reinstall、loop 和 harness upgrade Skills。

**Before**：本地可能是单 Skill 文件夹（根 `SKILL.md`），也可能是 runtime kit / Skill bundle（根 `AGENTS.md` + `skills/*/SKILL.md`），还可能是由 plugin manifest 和 session hook 加载控制 Skill 的系统。

**After**：该 Skill 或 runtime kit 变成一个可运行、可反馈、可审查、可发布的 GitHub repo：

- 有一个 GitHub Pages 驾驶舱页面。
- 用户在创建时明确选择 `public` 或 `private`。
- 创建前检查目标 GitHub repo 是否已经存在，避免重复 harness。
- 本地只保留一个 physical canonical repo，`.evozeus/.projects/OWNER/REPO` 和 runtime 安装路径都指向它。
- wrapper 先做 evolution surface assessment，再把 wrapper-owned 状态检查区放进真正控制 agent 行为的说明面：单 Skill 通常是 `SKILL.md`，runtime kit 通常是 `AGENTS.md`，hook/plugin 控制的系统可能是被 session hook 加载的控制 Skill，例如 `skills/<control-skill>/SKILL.md`。新增内容只说明状态检查、自进化方法和 `EvoZeus-wrapper` 路由，不改写业务规则。
- 增加 `.evozeus/wrapper.json`，记录 wrapper version、managed files、canonical repo 和 install links。
- 增加 `.evozeus/feedback-policy.json` 和 `.evozeus/audit-rule.md`，用于 turn-end feedback audit、托管模式和 issue 路由。
- 原 Skill repo 增加 `CHANGELOG.md`，记录每次 Skill 迭代。
- 增加 GitHub Issue 反馈入口，专门收集“使用中结果不满意”的场景。
- 增加 `docs/design-doc-template.md` 和 `docs/designs/`，每次 Skill 更新先写 design doc。
- 增加上传前检查：Issue 格式、PR design doc、CHANGELOG、release tag 和 release notes。

## 第一性原理

静态 Skill 不是一次写完的文档。真正有价值的 Skill 应该能在真实使用中持续吸收反馈，但每次进化都必须可追踪、可审查、可回滚。

EvoZeus-wrapper 的最小闭环是：

```text
environment diagnosis
  -> GitHub access / permission check
  -> target repo architecture, Skill inventory, and evolution surface assessment
  -> component gap report
  -> one physical canonical GitHub repo
  -> ~/.evozeus/.projects/OWNER/REPO pointer
  -> runtime symlink install
  -> GitHub Pages dashboard
  -> feedback Issue
  -> design doc
  -> PR
  -> CHANGELOG
  -> release
  -> run-time latest release check
```

这不是 agent runtime，也不是 prompt 管理平台，也不是和 EvoZeus 平级的用户入口。它只做一件事：在 EvoZeus 调度下，把一个本地 Skill 文件夹或 Skill bundle / runtime kit 包装成可自我进化的协作单元。

## 使用方式

### 1. 分阶段诊断

通常由 EvoZeus 判断并路由到本 repo。维护者也可以直接运行阶段 CLI：

```bash
python3 scripts/evozeus_wrapper.py env diagnose --json
python3 scripts/evozeus_wrapper.py skill diagnose --target /absolute/path/to/my-skill-or-runtime-kit --repo MetaInFLow/my-skill --json
python3 scripts/evozeus_wrapper.py skill transform --mode bootstrap --target /absolute/path/to/my-skill --repo MetaInFLow/my-skill --instruction-surface <relative path> --visibility private --dry-run --json
python3 scripts/evozeus_wrapper.py publish reinstall --skill-name my-skill --canonical-path /absolute/path/to/my-skill --target codex --dry-run --json
python3 scripts/evozeus_wrapper.py hook start-check --target /absolute/path/to/my-skill --latest-version v0.5.0 --json
python3 scripts/evozeus_wrapper.py harness upgrade-check --target /absolute/path/to/my-skill --latest-version v0.4.0 --json
python3 scripts/evozeus_wrapper.py harness upgrade --target /absolute/path/to/my-skill --latest-version v0.4.0 --dry-run --json
```

如果 `env diagnose` 返回 `next_action: install_evozeus`，先安装 / 初始化 EvoZeus，不进入目标 repo transform。如果没有给 `Visibility`，Agent 必须先问用户选择 `public` 还是 `private`。如果本地发现多个 repo clone 或多个 real-directory 安装副本，必须先让用户选择 canonical repo 或归档策略。

目标 repo 诊断必须先用 `gh repo view` 检查 repo 是否存在、visibility、default branch 和当前账号权限，再判断架构并输出 evolution surface 候选事实：

- `single_skill`：根目录 `SKILL.md`。
- `runtime_skill_bundle`：根目录 `AGENTS.md`，并存在 `skills/*/SKILL.md`、`runtime/`、`agents/`、`automation/` 等 runtime 结构。
- `hooked_skill_bundle`：存在 plugin manifest、session hook 和 hook-loaded control Skill，例如 `skills/<control-skill>/SKILL.md`。
- `skill_bundle`：存在多个 `skills/*/SKILL.md`，但没有完整 runtime 结构。
- `agents_runtime`：根目录 `AGENTS.md`，但没有可识别 Skill inventory。

诊断输出必须包含：

- `evolution_surface`：候选说明入口、controller files、脚本事实边界；最终 placement 由 `skills/evolution-surface-diagnosis/SKILL.md` 判断。
- `component_gaps`：当前 repo 缺少哪些 wrapper 文件、manifest、状态检查和 changelog。
- `skill_inventory`：发现了哪些 `skills/*/SKILL.md`。
- `controller_files`：hook / plugin manifest / runtime controller 文件。

诊断 JSON 是事实输入，不直接承担用户解释。诊断后必须先使用 `skills/evolution-surface-diagnosis/SKILL.md` 浏览整个 repo 并选择 instruction surface，再使用 `skills/status-assessment/SKILL.md` 做状态分析，把事实和判断转成用户可理解的流程进度、阻塞项和下一步命令；通过状态分析后才进入 transform。

维护者或 agent 直接使用本 repo 时，应先读取 `skills/using-evozeus-wrapper/SKILL.md`，不要把 root `SKILL.md` 当成完整操作手册。

### 2. 用 bootstrap 脚本生成本地驾驶舱文件

```bash
python3 scripts/evozeus_wrapper_bootstrap.py /absolute/path/to/my-skill \
  --skill-name "My Skill" \
  --repo "MetaInFLow/my-skill"
```

脚本会先用 `gh repo view OWNER/REPO` 检查目标 GitHub repo 是否已经存在；如果已存在，必须停止，不要重复创建 harness。
脚本在检查 repo 前必须先确认本机有 `git`、`gh`，且 `gh auth status` 通过；如果目标 Skill 已经有 git origin，则 origin 必须是可访问的 GitHub repo。bootstrap 阶段允许目标 repo 尚不存在，但必须明确使用 `--allow-missing-repo`。
然后脚本会交互询问 `public/private`，把 `templates/target/` 中的文件注入目标 Skill 文件夹，并复制 preflight checker。
同时，脚本会写入 `.evozeus/wrapper.json`，记录 surface diagnosis 选中的 `instruction_surface`，并在该 surface 加入 `EvoZeus-wrapper 状态检查`，再追加“自进化方法”和 `EvoZeus-wrapper` 章节。新增内容只说明状态检查、wrapper harness 的路由、版本和迁移规则，不改写原业务规则。

### 3. 创建 GitHub repo 和 Pages

在目标 Skill 文件夹中执行：

```bash
git init
git add .
git commit -m "Initialize wrapped Skill dashboard"
gh repo create MetaInFLow/my-skill --source . --public --push
gh release create v0.1.0 --repo MetaInFLow/my-skill --target main \
  --title "v0.1.0" \
  --notes "Initial wrapped Skill harness."
gh api --method POST repos/MetaInFLow/my-skill/pages \
  -f build_type=legacy \
  -f 'source[branch]=main' \
  -f 'source[path]=/docs'
```

如果选择 `private`，把 `--public` 改成 `--private`。注意：GitHub Pages 对 private repo 的可用性取决于 GitHub plan，而且 Pages 站点本身可能仍是互联网可访问的发布面；不要把敏感内容放进 `docs/`。

## 目标 repo 会被增加什么

```text
target-skill/
├── <evolution-surface>
├── CHANGELOG.md
├── WRAPPER.md
├── docs/
│   ├── index.md
│   ├── _config.yml
│   ├── design-doc-template.md
│   ├── designs/
│   │   └── README.md
│   └── wrapper-migrations/
│       └── README.md
├── scripts/
│   └── evozeus_wrapper_preflight.py
├── .evozeus/
│   ├── wrapper.json
│   ├── feedback-policy.json
│   └── audit-rule.md
└── .github/
    ├── ISSUE_TEMPLATE/
    │   ├── config.yml
    │   └── skill-feedback.yml
    ├── pull_request_template.md
    └── workflows/
        └── evozeus-wrapper-preflight.yml
```

## 上传前检查

目标 Skill repo 中可以运行：

```bash
python3 scripts/evozeus_wrapper_preflight.py doctor --repo MetaInFLow/my-skill --allow-missing-repo
python3 scripts/evozeus_wrapper_preflight.py structure
python3 scripts/evozeus_wrapper_preflight.py version --repo MetaInFLow/my-skill
python3 scripts/evozeus_wrapper_preflight.py issue --file issue.md
python3 scripts/evozeus_wrapper_preflight.py pr --design-doc docs/designs/2026-06-26-example.md
python3 scripts/evozeus_wrapper_preflight.py release --tag v0.1.0 --release-notes release-notes.md
```

检查规则：

- Doctor：必须能找到 `git`、`gh`，`gh auth status` 必须通过；如果 `.evozeus/wrapper.json` 存在，先读取 manifest，再验证 `~/.evozeus/.projects/OWNER/REPO` symlink、canonical repo origin、GitHub repo 和 runtime install pointer。只有 wrapper state 不存在时，才回退到 origin remote、当前用户 repo、org repo 或 public search。bootstrap 阶段目标 repo 尚未创建时，使用 `--allow-missing-repo`。
- Structure：目标 repo 必须包含 wrapper 文件。说明入口由 `.evozeus/wrapper.json` 的 `instruction_surface` 或根 `SKILL.md` / `AGENTS.md` 决定；hook/plugin 控制的系统必须先通过 `skills/evolution-surface-diagnosis/SKILL.md` 选出 surface，再记录到 manifest。该 surface 必须先出现 `EvoZeus-wrapper 状态检查`，再描述自进化方法和 canonical repo pointer。
- Version：运行 Skill 前必须检查 GitHub latest release；如果远端 release 比本地 `CHANGELOG.md` 新，先更新再运行。
- Existing repo version：如果目标 Skill 已经有 GitHub repo，不得把 Skill 版本重置为 `v0.1.0`。先取 GitHub latest release tag；如果没有 release 但 `CHANGELOG.md` 有最新 `vMAJOR.MINOR.PATCH` 条目，先为该 tag 创建或确认 release；两者都没有时停止并让 owner 选择首个 Skill 版本。
- Harness：目标 repo 的 `.evozeus/wrapper.json` 记录 wrapper harness version；Skill / kit release 与 wrapper version 必须分开检查。wrapper 版本升级时，先生成迁移方案，记录到 `docs/wrapper-migrations/`；assessment 选中的 evolution surface 先确保存在状态检查，其他 wrapper 内容只追加 `EvoZeus-wrapper` 区域或 migration note，不重写目标业务段落。
- Start hook：目标 Skill 启动前由 hook 调 `python3 scripts/evozeus_wrapper.py hook start-check --target <skill> --latest-version <latest-wrapper-version> --json`。hook 根据 `decision.level` 决定继续、警告或阻断；不要只靠 `SKILL.md` 文本提醒检查 harness 版本。
- Issue：必须符合反馈模板，说明不满意结果、期望结果、复现场景、证据边界和影响程度。
- PR：必须有 design doc，且 design doc 说明修复 issue、优化目标、优化方向、实现方式和验证计划。
- PR：必须更新 `CHANGELOG.md`。
- Release：必须有对应 tag 的 changelog 记录，且 release description 非空。

## Release 版本标准

所有 release tag 必须使用 `vMAJOR.MINOR.PATCH`。

- `MAJOR`：不兼容的 Skill 行为、输入要求或输出格式变化。
- `MINOR`：新增能力、新增必需证据规则、新增 harness 行为。
- `PATCH`：文案、示例、bug fix、校验修复或不破坏兼容性的澄清。

新建目标 repo 的首个 wrapped Skill release 使用 `v0.1.0`。已有 repo 走 `adopt`，保留既有 Skill release；`.evozeus/wrapper.json` 中的 wrapper harness version 是另一条版本轴。

## 边界

本 repo 不保存目标 Skill 的业务内容，不上传 raw private session，不替代目标 Skill 的 owner 判断。

如果目标 Skill 涉及客户资料、商业资料、secret 或个人隐私，默认使用 private repo，并且 `docs/` 里只放脱敏内容。
