---
name: r858-rr-us-persistent-rotation
description: "R858 修 BUG6(rr_us 每请求从0起致7894压倒性过载13:1)+BUG7(chain budget 70s仅容1次attempt), 跨请求持久RR计数器+budget提至120s; 验证端口分布均匀2:2:2:1:1+5/5真实CC回归OK"
metadata: 
  node_type: memory
  type: project
  originSessionId: 3c8d8f5f-50f9-4f31-9c0c-b1eae74a0183
---

R858 深挖续修 nv_gw BUG6+BUG7（[[r857-mode-stall-fix]] 之后继续深挖）。

## BUG6: rr_us 模式不跨请求轮换 IP（7894 过载真因）
- **症状**: `integrate_us_rr` mode 实测端口分布 **7894:13, 7895:1**（5 口里 7894 压倒性占 93%）。7894 过载→SSL 断流高发→mid-response。
- **根因**: `_glm52_resolve_proxy` 旧代码 `pool[attempt_idx % len(pool)]`，attempt_idx 是 **per-request** 序号（每请求从 0 起）。所以每请求首 attempt 永远取 `pool[0]=7894`。同请求内 fault 重试才偏移到 7895/7896，但首 attempt 集中 7894。
- **修复** (`/opt/cc-infra/proxy/nv-gw/gateway/upstream.py` ~line 102 + ~935 `_glm52_resolve_proxy`):
  - 新增模块级持久计数器 `_glm52_rr_us_counter`（+threading.Lock），**跨请求**递增。
  - `rr_us` 分支改 `pool[(_glm52_rr_us_counter + attempt_idx) % len(pool)]`：跨请求持久 RR 分散负载 + 同请求内 fault 重试偏移（attempt_idx）。
- **验证**: 强制单 mode `integrate_us_rr`（临时改 chain）+ 8 请求 → 端口分布 **7894:2, 7895:2, 7896:2, 7897:1, 7899:1**（5 口均匀）。修前 13:1，修后接近 1:1:1。
- **间接收益**: 7894 不再过载 → SSL 断流应显著减少（[[r850-thinking-silence-miskill-fix]]/[[r846-stream-interrupted-fix]] 的网络层诱因之一被釜底抽薪）。

## BUG7: chain budget 70s 仅容 1 次 attempt
- **症状**: `NVU_TIER_BUDGET_GLM5_2_NV=70`，但单 attempt `UPSTREAM_TIMEOUT=66s`。1 个 timeout 就 abort 整个 chain，mode 容错名存实亡（没机会切 mode 重试）。
- **修复**: `docker-compose.yml` line 45 `70→120`（容 2 次 mode 切换，每次 66s）。

## 回归验证（必须用软件本身测试成功）
1. 临时单 mode `integrate_us_rr` 验证 BUG6 → 端口均匀（如上）。
2. **恢复 chain 原始 4 mode**: `integrate_us_rr,pexec_us_rr,pexec_us_single,integrate_us_single` + reset `glm52_mode_idx.json` idx=0 + recreate nv_gw。
3. **真实 CC 模拟**（走 cc4101→nv_gw 完整生产路径，stream+system+claude-opus 模型名）5 次:
   - **5/5 OK 0 fail**，延迟 1.7-2.7s，text 40-50c 实质回答（无 empty/zombie/filtered）。

## 铁律
- 修改 `nv_gw` 的 `config.py` 或模块级常量后**必须 docker restart/recreate**（Python import 时求值，进程内缓存旧值）——同 [[r854-delete-40007-force-thinking-rootcause]] 教训。
- bind mount 宿主源码 `/opt/cc-infra/proxy/nv-gw/gateway/upstream.py`，改宿主 + restart 即生效，备份 `upstream.py.preR858`。
- 验证 rr_us 分布必须强制单 mode（否则 mode_idx 会跳到 pexec_us_single=固定7894，掩盖 rr 行为）。
