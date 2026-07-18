# 完整迁移与可选 Pages 部署

Related issues: #10, #11

## 优化目标

1. `migrate-layout` 只有在迁移后的 target 可直接通过 wrapper preflight 时才返回成功。
2. Codex hook registration 必须安全合并，不能覆盖 target 已有 hooks。
3. wrapper-owned 状态与 manifest 必须反映实际安装版本和宿主接入状态。
4. GitHub Pages 是可选发布能力，不能阻断 private repo 的基础 validation。

## 实现方向

- 迁移计划阶段解析 `.codex/hooks.json`；格式不合法时在任何写入前阻断。
- 应用阶段保留非 wrapper hooks，创建或刷新唯一的 wrapper `SessionStart` entry。
- 刷新 status prelude 和无 `--latest-version` 自比较的检查命令，追加 migration note，保持业务段不变。
- 根据最终文件重新计算 manifest integration、hook registration、onboarding 和 dashboard contract。
- `v0.9.0 -> v0.9.1` 可直接刷新已经 consolidated、但状态残缺的 v2 harness，不要求先还原到 legacy layout。
- 删除 legacy manifest 后运行 structure post-validation；失败时返回错误并要求回滚迁移 commit。
- workflow 增加始终运行的 validation job；Pages job 依赖 validation，并由 repository variable `EVOZEUS_PAGES_ENABLED=true` 显式开启。

## 验证计划

- 完整 v0.6 target 在没有 `.codex/` 时迁移成功并直接通过 structure、maintainer、runtime 和 hook smoke test。
- 非法 hooks JSON 在写入前阻断；自定义 SessionStart hook 在合并后保留。
- status prelude 显示目标版本且不传自比较 latest；业务段字节保持不变。
- private/unsupported Pages 场景仍运行 validation；Pages 未启用时 deployment job 跳过而不失败。
- dashboard contact link 指向 consolidated layout。

## 发布计划

作为 v0.9.0 的迁移与 workflow 修复发布 `v0.9.1`，关联并关闭 #10、#11。
