# Wenyi 5xx 探测修复

问题：Wenyi 的「测试连接」对同一个本地反代（`http://127.0.0.1:7863/v1`）
间歇报 `提供商暂时不可用（HTTP 502/503）`，而 dsh 用同一端点正常。

根因（已在本机实测）：
- 反代上游是共享账号池，并发请求命中冷却/掉登录态账号时返回 5xx
  （原始响应体：`国内版的账号当前都不可用（冷却中，或需要重新登录）`）。
- Wenyi 的连通性探测 `packages/core/wenyi_core/llm/connectivity.py`：
  - `MAX_PROBE_WORKERS = 8`，并发打向账号池；
  - 探测时强制 `max_retries = 0`，一次 5xx 就直接判失败，无重试兜底。
- 串行 10 次全 200；8 并发 24 次里 14 次 5xx。

## 修改内容（`wenyi-5xx-fix.patch`）

- `MAX_PROBE_WORKERS`: 8 → 1，探测串行化，避免并发打向冷却账号池。
- 探测通过共享的 `llm/retrying.py::provider_retry` 对瞬时错误（5xx / 连接错误 /
  超时）做最多 2 次短退避重试；永久错误（401/403/404 等）仍快速失败。
- SDK 内部 `max_retries` 仍为 0，避免嵌套重试。
- 保留空/截断响应 → `reachable` 的原有语义。
- 更新 `test_llm_connectivity.py`：503 现在预期重试后再判定，新增
  「瞬时 5xx 后成功」回归用例。

## 云端编译

`.github/workflows/wenyi-build.yml`：在 GitHub Actions 上 clone 上游、应用补丁、
跑 Ruff + 连通性回归测试，再构建 wenyi-core/cli/backend/desktop 的 wheel 与
sdist，产物上传为 artifact。本机不编译。

手动触发：Actions → `Wenyi 5xx probe fix - build` → Run workflow。
