# R1601: 移植 HM2 cc4101→40006→glm5_2_nv 稳定链路到 HM1 本地

## 摘要

把 HM2 已验证稳定的 cc4101→nv_gw→glm5_2_nv→NVCF 链路（R839 mode chain + R1415/R1416/R1418/R1420）
移植到 HM1 本地，供本地测试。**本地 CC 仍走 40001（legacy/glm5.1），未切换**——等用户批准后再切。
所有改动是 cherry-pick / 精准插入，不整体覆盖，保留 HM1 独有的 R830b/c/R832/R551/peer-fallback 逻辑。

## 移植内容

### cc4101（直接覆盖，闲置且 md5 除两文件外全同）
- `proxy/cc4101/gateway/stream.py` ← HM2（+R1415 recv-fallback: http.client fp timed-out-object
  永久崩坏时用 sock.recv 直接读 socket buffer 已达数据）
- `proxy/cc4101/gateway/upstream.py` ← HM2（+R1420 header_timeout 按 input 缩放）

### nv_gw（精准 cherry-pick，不覆盖）
- `gateway/glm52_mode_idx.py` 新建（HM2 整段复制, 91 行, md5 与 HM2 一致）
- `gateway/cooldown.py` 追加 R814 tier_degraded 段（mark_tier_degraded/is_tier_degraded）
- `gateway/config.py` 插入 mode chain env 解析段 + 末尾 import glm52_mode_idx + cooldown re-export 补 tier_degraded
- `gateway/upstream.py`:
  - import 头补: KEY_COOLDOWN_S, is_tier_degraded/mark_tier_degraded, NV_INTEGRATE_EGRESS_IPS,
    NV_GLM52_MODE_CHAIN/SINGLE/RR_US_PROXIES, glm52_*_mode_idx
  - 模块级变量补: _glm52_rr_us_counter, _glm52_rr_us_lock (R858)
  - execute_request 前插入 3 函数: _glm52_resolve_proxy, _glm52_single_attempt, _try_glm52_mode_chain (399 行)
  - execute_request 内 R838b 分叉前插入 R839 分叉块
  - **保留** HM1 独有: FALLBACK_GRAPH/R830b integrate thinking timeout/R832 empty200 cooldown/R551 等
- `gateway/handlers.py` 两个 stream loop 补 R1416 first-byte deadline 按 input 缩放
  (≤50K→20s, 50K-200K→60s, 200K-350K→90s, >350K→120s)
  **不移植** R1407 idle-gap（HM1 简单 idle deadline 历史 100% 可用, 下轮视数据再评估）

### docker-compose.yml env
- nv_gw: NV_INTEGRATE_MODELS "" (空, 移交 mode chain), NV_GLM52_MODE_CHAIN=pexec_us_rr,
  NV_GLM52_SINGLE_US_PROXY/RR_US_PROXIES=http://host.docker.internal:789x (HM1 格式, 非 HM2 的 socks5h://172.18),
  NVU_TIER_BUDGET_GLM5_2_NV 96→120 (对齐 HM2 R858, mode chain chain budget)
- cc4101: UPSTREAM_TIMEOUT 30→60 (R1412 from HM2), PRIMARY_HEADER_TIMEOUT 25→60 (HM1 本地调参)

## 验证数据

冒烟测试 (2026-07-16 08:36-08:45 local):
- 小请求 ×5: 2.2-10.4s 全 200 OK
- 42K context 非流式: 12.1s 200 OK
- 10K context 流式: 52.1s 854 chunks 200 OK
- 23K context 流式中: 34.9s 844 chunks 200 OK
- DB 最近 20min glm5_2_nv: 14/14 全 200, egress_route=glm52-mihomo-7894..7899 (5 代理轮换)
- mode chain 日志: NV-GLM52-CHAIN start_mode_idx=0 pexec_us_rr → NV-GLM52-SUCCESS k1/k3/k4/k5

## 关键发现 / 本地调参

1. **HM1 不能整体覆盖 upstream.py/handlers.py**: HM1 有 77 行 upstream-only (R830b/c/R832/R551)
   + 231 行 handlers-only (peer-fallback/ms_gw-fallback)。整体覆盖会丢这些, 改变 dsv4p/kimi/minimax
   容错行为。必须精准插入。
2. **PRIMARY_HEADER_TIMEOUT=25 在 HM1 不工作**: HM2 用默认 25s 能工作 (NVCF 响应快), 但 HM1 经
   mihomo http 代理 7894-7899 到美国 IP, nv_gw mode chain 单 attempt 首字节实测 33s, cc4101 25s
   header timeout < 33s → nv_gw 还没返回 header cc4101 就超时 (08:41:47 请求, nv_gw 08:42:20 成功 33s,
   cc4101 08:42:12 已 25s 超时). 提至 60s 覆盖 nv_gw mode chain 典型首字节+余量. 这是 HM1 本地代理路径
   延迟特性调参, HM2 的 25s 在 HM1 不适用.
3. **R1420 _hdr_to 被 min(x, UPSTREAM_TIMEOUT) 封顶**: upstream.py:95 header_timeout=min(header_timeout,
   timeout). HM1 旧 UPSTREAM_TIMEOUT=30 会把 R1420 的 60/90/120 全砍到 30. 必须同时提 UPSTREAM_TIMEOUT=60.

## 未做 / 边界

- **不改 settings.json**: 本地 CC 仍 ANTHROPIC_BASE_URL=http://127.0.0.1:40001. 切到 4101 等用户批准.
- **不移植 R1407 idle-gap**: handlers.py 的 last_real_content_time + NVU_STREAM_NO_CONTENT_GAP_S 深度
  耦合 HM2 passthrough loop (679-982), HM1 无. 本轮用 HM1 简单 stream_idle_deadline 兜底, 历史可用.
  下轮若出现 "200-then-hang/空内容 drip" 再评估.
- 不改 HM1 cooldown backoff cap (30), TIER_TIMEOUT_BUDGET_S (205), NV_KEY_INTEGRATE_KEYS
- 不动 HM2 (本轮纯 HM1 本地)

## 验证 checklist

- [x] cc4101 health OK, UPSTREAM_TIMEOUT=60, PRIMARY_HEADER_TIMEOUT=60, R1415/R1420 代码加载
- [x] nv_gw health OK, NV_GLM52_MODE_CHAIN=pexec_us_rr, NV_INTEGRATE_MODELS=空
- [x] 容器内 import upstream/config/handlers 无 NameError
- [x] 冒烟: 小+大+流式请求全 200, mode chain 日志 NV-GLM52-SUCCESS
- [x] DB nv_requests 记录 glm5_2_nv 14/14 全 200, egress 5 代理轮换
- [x] 本地 CC 仍走 40001 (未切)
- [x] glm52_mode_idx.json 持久化 idx=0

## 文件变更清单

- proxy/cc4101/gateway/stream.py (覆盖, .bak.R1601)
- proxy/cc4101/gateway/upstream.py (覆盖, .bak.R1601)
- proxy/nv-gw/gateway/glm52_mode_idx.py (新建)
- proxy/nv-gw/gateway/cooldown.py (追加 tier_degraded, .bak.R1601)
- proxy/nv-gw/gateway/config.py (插入 mode chain, .bak.R1601)
- proxy/nv-gw/gateway/upstream.py (精准插入, .bak.R1601)
- proxy/nv-gw/gateway/handlers.py (R1416 first-byte scaling, .bak.R1601)
- docker-compose.yml (cc4101 + nv_gw env, .bak.R1601)
