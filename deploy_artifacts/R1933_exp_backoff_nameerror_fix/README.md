# R1933: nv_gw upstream.py 补 import 修 R1928 半成品指数退避裸名 NameError

**Host**: HM2 only (cc2 lineage)
**Date**: 2026-07-19
**Restart**: 13:33:43Z (nv_gw)

## 根因

R1932 restart (13:20Z) 重新加载源码, 让一直潜在未触发的 R1928 半成品指数退避
裸名 `NVU_GLM52_EXP_BACKOFF` (upstream.py:1032 引用但 from import 列表漏) 显形
→ nv_gw 每个 glm5_2_nv 请求 NameError crash → cc4101 毫秒级 RemoteDisconnected
→ 全切 ms_gw fallback。

注: R1928 半成品代码 (upstream.py:1027-1037 + config.py:522-527) 已入库但 env
`NVU_GLM52_EXP_BACKOFF` 默认关 (从未 in-vivo 激活)。裸名在 env 关时不该被求值,
但 R1932 restart 触发了 import 期/模块级的求值路径显形。

## 修复

`upstream.py:57` 的 `from .config import (...)` 加 3 个名字:
```python
NVU_GLM52_EXP_BACKOFF, NVU_GLM52_EXP_BACKOFF_STEPS, NVU_GLM52_EXP_BACKOFF_CAP,
```

## 文件

- `upstream.py.before_R1928` — R1928 半成品入库后但 import 漏 (R1933 改前基线, = .bak.R1928)
- `upstream.py.after_R1933` — R1933 补 import 后 (= 当前 live)

## diff (单行 import)

```
56a57
>     NVU_GLM52_EXP_BACKOFF, NVU_GLM52_EXP_BACKOFF_STEPS, NVU_GLM52_EXP_BACKOFF_CAP,  # R1928 指数退避 (R1933 补 import 修 NameError...)
```

## 验证

R1933 restart 后 nv_gw 恢复正常, 每个 glm5_2_nv 请求不再 NameError crash。
post-13:33Z 1h: cc4101 727 OK + 0 parse-fail + nv 502=1 (all_tiers_exhausted 上游侧)。

R1928 指数退避半成品仍冻结 (env 未激活), 激活需同步 chain_budget 120→420 +
cc4101 header 60→450 + post-200 软挂换 key 未实现 + 24h 观测。

关联: R1932 (saw_real_tool_call parse-fail 根治, R1932 restart 让本 bug 显形)。
