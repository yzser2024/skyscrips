# Wenyi 5xx 探测修复

问题：Wenyi 的「测试连接」对同一个本地反代（`http://127.0.0.1:7863/v1`）
间歇报 `提供商暂时不可用（HTTP 502/503）`，而 dsh 用同一端点正常。

## 根因（本机实测）

反代上游是共享账号池，**并发**请求命中冷却账号时返回 5xx：

```json
{"error":{"message":"国内版的账号当前都不可用（冷却中，或需要重新登录）"}}
```

对照实验（同一端点、同一模型 `hy4flash-free`、串行与 8 并发各 20 次）：

| 模式 | 结果 |
| --- | --- |
| 串行 20 次 | **20/20 全部 200** |
| 8 并发 20 次 | **17 次 503** |

冷却窗口实测 **< 1 秒**（burst 后串行轮询 0.8s 即恢复 200）。
所以问题不是「冷却太久」，而是 **并发瞬间打满账号池**。

Wenyi 原实现的两处缺陷（`packages/core/wenyi_core/llm/connectivity.py`）：

1. `MAX_PROBE_WORKERS = 8` —— 探测并发 8，正好触发账号池限流；
2. 探测强制 `max_retries = 0` —— 一次 5xx 就直接判失败，没有重试兜底。

## 修改内容（`apply_fix.py`）

`apply_fix.py` 用精确文本替换把修复打到上游源码上（每个替换点都校验唯一匹配，
否则立即报错）：

- **`MAX_PROBE_WORKERS`: 8 → 1** —— 探测串行化。这是根治项：串行实测 100% 成功。
- **探测重试**：通过共享的 `llm/retrying.py::provider_retry` 对瞬时错误
  （5xx / 连接错误 / 超时）做最多 3 次重试；永久错误（401/403/404）仍快速失败。
- **尊重服务器 `Retry-After`**：等待值原样交给 tenacity（服务器说等 N 秒就等 N 秒），
  只按探测超时预算封顶，避免设置界面卡死。
- **SDK 内部 `max_retries` 保持 0** —— 避免嵌套重试。
- **保留空/截断响应 → `reachable`** 的原有语义。
- 更新 `test_llm_connectivity.py`：503 改为「重试后判定」，新增「瞬时 5xx 后成功」
  回归用例；移除两个依赖并发的 `reversed` 参数化用例（串行化后不再适用）。

## 行为验证（离线，假 adapter）

```
503,503,503,200 -> success: attempts=4  waits=[0.08, 0.15, 0.67]   PASS
401             -> fail fast: attempts=1 waits=[]                  PASS
always 503      -> exhausted: attempts=4                           PASS
Retry-After: 7  -> wait recorded [7.0]                             PASS
```

## 云端编译

两个工作流，都在 GitHub Actions 上完成，本机不编译：

- `.github/workflows/wenyi-build.yml` —— Linux：clone 上游 → 打补丁 → Ruff →
  回归测试 → 构建 wenyi-core/cli/backend/desktop 的 wheel + sdist。
- `.github/workflows/wenyi-win-build.yml` —— Windows：clone 上游 → 打补丁 →
  构建 PyInstaller sidecar + Tauri NSIS 安装包。

手动触发：Actions → 选对应 workflow → Run workflow。
