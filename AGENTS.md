# AGENTS.md

## 项目约定

- 项目产出默认用中文，关键专有名词和专业名词可以用英文。
- 本 repo 面向 public-ready harness，不保存 raw private session、客户资料、商业资料、secret 或未脱敏 evidence。
- 修改必须保持小步、可解释、可回归；不要为了“通用”提前写框架。

## Repo 职责

EvoZeus-wrapper 负责把一个本地 Skill 文件夹包装成最小自进化驾驶舱：

- 为目标 Skill repo 生成 GitHub Pages dashboard。
- 让用户明确选择 `public` 或 `private`。
- 注入 `CHANGELOG.md`。
- 注入 Skill 反馈 Issue template。
- 注入 Skill 更新 design doc template。
- 注入 GitHub 上传前 preflight 检查。

它不负责改写目标 Skill 的业务内容，也不保存 raw private session、客户资料、商业资料、secret 或未脱敏 evidence。

## 编辑原则

1. 先明确目标 Skill 文件夹、GitHub repo 名称和 visibility。
2. visibility 没有明确给出时必须问用户，不要默认 public 或 private。
3. 对目标 Skill 文件夹做增量注入，不覆盖用户已有文件，除非用户明确要求。
4. 检查逻辑放在 `scripts/evozeus_wrapper_preflight.py`，模板放在 `templates/target/`。
5. 不要把 wrapper 做成复杂 runtime；它只负责驾驶舱文件和上传前检查。
6. 如果涉及 Session Signal 方法或 official factor tools，把内容路由到 `evozeus-session-signal-skill`。

## 验证标准

- 文档变更至少通过人工阅读检查：边界清楚、无内部废话、无 private 数据。
- 模板变更必须能支持最小闭环：feedback Issue -> design doc -> PR -> CHANGELOG -> release。
- `scripts/evozeus_wrapper_preflight.py` 变更后必须用一个临时 target folder 跑通 structure / issue / pr / release 检查。
