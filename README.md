# EvoZeus-wrapper

EvoZeus-wrapper 是 EvoZeus 母体调度下的静态 Skill 演进 harness，用来给本地静态 `SKILL.md` 构建最小自进化驾驶舱。

用户入口是 EvoZeus，不是 EvoZeus-wrapper。只有当 EvoZeus 判断一个 promoted Skill 或已有本地 Skill 需要 repo 化、反馈闭环和版本治理时，才路由到本 repo。

**Before**：本地只有一个 Skill 文件夹，通常只有 `SKILL.md` 和少量说明。

**After**：该 Skill 变成一个可运行、可反馈、可审查、可发布的 GitHub repo：

- 有一个 GitHub Pages 驾驶舱页面。
- 用户在创建时明确选择 `public` 或 `private`。
- 创建前检查目标 GitHub repo 是否已经存在，避免重复 harness。
- 本地只保留一个 physical canonical repo，`.evozeus/.projects/OWNER/REPO` 和 runtime 安装路径都指向它。
- 原 `SKILL.md` 会补充自进化方法说明，但不改写业务规则。
- 增加 `.evozeus/wrapper.json`，记录 wrapper version、managed files、canonical repo 和 install links。
- 原 Skill repo 增加 `CHANGELOG.md`，记录每次 Skill 迭代。
- 增加 GitHub Issue 反馈入口，专门收集“使用中结果不满意”的场景。
- 增加 `docs/design-doc-template.md` 和 `docs/designs/`，每次 Skill 更新先写 design doc。
- 增加上传前检查：Issue 格式、PR design doc、CHANGELOG、release tag 和 release notes。

## 第一性原理

静态 Skill 不是一次写完的文档。真正有价值的 Skill 应该能在真实使用中持续吸收反馈，但每次进化都必须可追踪、可审查、可回滚。

EvoZeus-wrapper 的最小闭环是：

```text
environment diagnosis
  -> target Skill diagnosis
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

这不是 agent runtime，也不是 prompt 管理平台，也不是和 EvoZeus 平级的用户入口。它只做一件事：在 EvoZeus 调度下，把一个本地 Skill 文件夹包装成可自我进化的协作单元。

## 使用方式

### 1. 分阶段诊断

通常由 EvoZeus 判断并路由到本 repo。维护者也可以直接运行阶段 CLI：

```bash
python3 scripts/evozeus_wrapper.py env diagnose --json
python3 scripts/evozeus_wrapper.py skill diagnose --target /absolute/path/to/my-skill --repo MetaInFLow/my-skill --json
python3 scripts/evozeus_wrapper.py skill transform --mode bootstrap --target /absolute/path/to/my-skill --repo MetaInFLow/my-skill --visibility private --dry-run --json
python3 scripts/evozeus_wrapper.py publish reinstall --skill-name my-skill --canonical-path /absolute/path/to/my-skill --target codex --dry-run --json
python3 scripts/evozeus_wrapper.py harness upgrade-check --target /absolute/path/to/my-skill --json
```

如果没有给 `Visibility`，Agent 必须先问用户选择 `public` 还是 `private`。如果本地发现多个 repo clone 或多个 real-directory 安装副本，必须先让用户选择 canonical repo 或归档策略。

### 2. 用 bootstrap 脚本生成本地驾驶舱文件

```bash
python3 scripts/evozeus_wrapper_bootstrap.py /absolute/path/to/my-skill \
  --skill-name "My Skill" \
  --repo "MetaInFLow/my-skill"
```

脚本会先用 `gh repo view OWNER/REPO` 检查目标 GitHub repo 是否已经存在；如果已存在，必须停止，不要重复创建 harness。
脚本在检查 repo 前必须先确认本机有 `git`、`gh`，且 `gh auth status` 通过；如果目标 Skill 已经有 git origin，则 origin 必须是可访问的 GitHub repo。bootstrap 阶段允许目标 repo 尚不存在，但必须明确使用 `--allow-missing-repo`。
然后脚本会交互询问 `public/private`，把 `templates/target/` 中的文件注入目标 Skill 文件夹，并复制 preflight checker。
同时，脚本会写入 `.evozeus/wrapper.json`，并在目标 Skill 根目录 `SKILL.md` 中追加“自进化方法”章节。

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

## 目标 Skill 会被增加什么

```text
target-skill/
├── SKILL.md
├── CHANGELOG.md
├── WRAPPER.md
├── docs/
│   ├── index.md
│   ├── _config.yml
│   ├── design-doc-template.md
│   └── designs/
│       └── README.md
├── scripts/
│   └── evozeus_wrapper_preflight.py
├── .evozeus/
│   └── wrapper.json
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

- Doctor：必须能找到 `git`、`gh`，`gh auth status` 必须通过；如果目标有 origin remote，origin 必须是可访问的 GitHub repo；如果是安装副本或非 git 目录，必须显式传 `--repo` 或能发现候选 repo。bootstrap 阶段目标 repo 尚未创建时，使用 `--allow-missing-repo`。
- Structure：目标 repo 必须包含 wrapper 文件，且根目录 `SKILL.md` 必须描述自进化方法和 canonical repo pointer。
- Version：运行 Skill 前必须检查 GitHub latest release；如果远端 release 比本地 `CHANGELOG.md` 新，先更新再运行。
- Harness：目标 repo 的 `.evozeus/wrapper.json` 记录 wrapper harness version；Skill release 与 wrapper version 必须分开检查。
- Issue：必须符合反馈模板，说明不满意结果、期望结果、复现场景、证据边界和影响程度。
- PR：必须有 design doc，且 design doc 说明修复 issue、优化目标、优化方向、实现方式和验证计划。
- PR：必须更新 `CHANGELOG.md`。
- Release：必须有对应 tag 的 changelog 记录，且 release description 非空。

## Release 版本标准

所有 release tag 必须使用 `vMAJOR.MINOR.PATCH`。

- `MAJOR`：不兼容的 Skill 行为、输入要求或输出格式变化。
- `MINOR`：新增能力、新增必需证据规则、新增 harness 行为。
- `PATCH`：文案、示例、bug fix、校验修复或不破坏兼容性的澄清。

初始 harness release 固定使用 `v0.1.0`。

## 边界

本 repo 不保存目标 Skill 的业务内容，不上传 raw private session，不替代目标 Skill 的 owner 判断。

如果目标 Skill 涉及客户资料、商业资料、secret 或个人隐私，默认使用 private repo，并且 `docs/` 里只放脱敏内容。
