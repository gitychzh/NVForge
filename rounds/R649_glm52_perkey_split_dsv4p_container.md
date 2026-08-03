# R649 — glm5_2_nv per-key 混合链路 + dsv4p_nv40066 独立容器作 cc4101 fallback (2026-08-03 15:07 CST)

## 背景 / 动机
- R639-R648 NOP 巡检确认 dsv4p_nv 24h SR 71%, 主因 `all_tiers_exhausted` (96%), NVCF 账户级配额耗尽, 非 nv_gw 侧可改.
- 2026-08-03 多链路对比测试 (cc2 视角):
  - integrate + 5US IP 轮转: SR 96%, p50 13.5s, 零 429, 零 RemoteDisconnected (最稳)
  - pexec fid1 (生产唯一): SR 72%, 全 429 (配额限流)
  - pexec fid2: SR 88%, 3× RemoteDisconnected
  - pexec fid3: SR 52%, 8× RemoteDisconnected (最差)
  - 容器内无 proxy: 0% (integrate.api 对容器 IP 不响应)
  - 本地 IP 直连 integrate: SR 56.7%, p50 37.7s (单 IP throttling)
- 结论: integrate+5IP 最稳, pexec 任意 fid 不稳. 决定: glm5_2_nv 切混合链路 (k1/3/5 pexec 各绑 fid1/2/3, k2/4 走 integrate, 5key 全 5US IP), dsv4p_nv 剥离独立容器作 fallback.

## 本轮改动 (HM2, 改前备份: .bak.R-glm52split.20260803_150723)

### 1. nv_gw 源码: per-key fid 绑定 (新机制, 非全局)
**文件**: `proxy/nv-gw/gateway/config.py` + `upstream.py`
- config.py 新增 `NV_GLM52_KEY_FID_BIND` + `NV_GLM52_KEY_MODE_BIND` 两个独立 env (仅 glm5_2_nv 读, 不影响 dsv4p_nv).
  - 用 `_parse_key_int_map()` 解析 "key_idx:value;..." 格式.
  - **不用 KEY_MODE_BINDING** (全局陷阱, 会拐 dsv4p_nv 进 dead integrate, 见 [[nv-gw-integrate-test-2026-08-01]]).
- config.py 修复 `function_ids` 列表: 从 R_pexec_fid1 的"全绑 fid1"改回 3 个真实 fid 候选 (pos0=fid1 b1b22d03, pos1=fid2 3b9748d8, pos2=fid3 b6029a96). 加 NVCF_GLM52_FUNCTION_ID2/3 env 覆盖支持.
- upstream.py `_glm52_single_attempt` pexec 分支: 加 `if tier_model=="glm5_2_nv" and key_idx in NV_GLM52_KEY_FID_BIND` 守卫, 命中则按 fid_position 选 fid; 未命中 (含 dsv4p_nv 全部) 走原 `_fid_rr_counter` 轮转.
- upstream.py `_try_glm52_mode_chain`: `_bound_mode_name` 查表改为 `NV_GLM52_KEY_MODE_BIND.get(key_idx) or KEY_MODE_BINDING.get(key_idx)` (NV_GLM52_KEY_MODE_BIND 优先, 隔离 dsv4p).

### 2. nv_gw env (docker-compose.yml)
- `NV_GLM52_MODE_CHAIN=` → `pexec_us_rr,integrate_us_rr` (启用 2 档 mode chain)
- `KEY_MODE_BINDING=0:pexec_us_rr;...` → 空 (清空全局, 避免拐 dsv4p)
- 新增 `NV_GLM52_KEY_MODE_BIND=0:pexec_us_rr;1:integrate_us_rr;2:pexec_us_rr;3:integrate_us_rr;4:pexec_us_rr` (k2/4→integrate, k1/3/5→pexec, 仅 glm5_2_nv 读)
- 新增 `NV_GLM52_KEY_FID_BIND=0:0;2:1;4:2` (k1→fid1, k3→fid2, k5→fid3, 候选列表 0-based)
- `NVU_MS_FALLBACK_ENABLED=1` → `0` (关 nv_gw ms_gw fallback, 由 cc4101 fallback dsv4p 代替)
- `NVU_PEER_FALLBACK_ENABLED=1` → `0` (关 peer-fallback HM1)
- `NVU_DISABLE_MS_FALLBACK=0` → `1` (与 CLAUDE.md R-nvonly 声明一致)

### 3. 新增 dsv4p_nv40066 容器 (port 40066)
- 复用 `cc-infra-nv_gw` image + 同源码 bind-mount (per-key fid 绑定有 tier_model=='glm5_2_nv' 守卫, 不影响 dsv4p).
- `NV_INTEGRATE_MODELS=` 空 (dsv4p pexec-only, 历史 integrate 间歇全挂)
- `NVU_DISABLE_MS_FALLBACK=1`, `NVU_MS_FALLBACK_ENABLED=0`, `NVU_PEER_FALLBACK_ENABLED=0` (独立容器无 fallback)
- `NVU_PROXY_URL1~5=7900~7904` (复用 nv_gw 同套 5 US IPv4, 已验证)
- `NVU_HOST_MACHINE=opc2sname-dsv4p40066` (DB 区分用)
- `NVU_CALLER_KEY_MAP=` 空, `NVU_BUFFER_CALLERS=` 空 (free 5-key, 不走 buffer 因 cc4101 层已有)

### 4. cc4101 切 primary + fallback
- `PRIMARY_UPSTREAM_MODEL=dsv4p_nv` → `glm5_2_nv`
- `PRIMARY_UPSTREAM_URL=http://nv_gw:40006/v1/messages` (不变)
- `FALLBACK_UPSTREAM_URL=http://ms_gw:40007/...` → `http://dsv4p_nv40066:40066/v1/messages`
- `FALLBACK_UPSTREAM_MODEL=glm5_2_ms` → `dsv4p_nv`
- `FALLBACK_UPSTREAM_TOKEN=ms-gw-token` → `nv-gw-token`
- `depends_on` 去掉 ms_gw, 加 dsv4p_nv40066 (ms_gw 容器继续运行不删)

## 验证 (2026-08-03 07:13-07:25 UTC)

### 容器健康
- dsv4p_nv40066 /health: ok, 5 keys, port 40066 ✓
- nv_gw /health: ok, 5 keys, port 40006 ✓
- cc4101 /health: ok, **primary=glm5_2_nv** ✓ (改 env 后必须 `docker compose up -d` 重建容器, restart 不加载新 env)

### per-key 路由铁证 (nv_tier_attempts DB, 5min 窗口)
| key_idx | fid (前8位) | upstream_type | count | 期望 |
|---|---|---|---|---|
| 0 (k1) | b1b22d03 | nvcf_pexec | 4 | fid1 pexec ✓ |
| 1 (k2) | integrate | nv_integrate | 1 | integrate ✓ |
| 2 (k3) | 3b9748d8 | nvcf_pexec | 2 | fid2 pexec ✓ |
| 3 (k4) | integrate | nv_integrate | 3 | integrate ✓ |
| 4 (k5) | b6029a96 | nvcf_pexec | 2 | fid3 pexec ✓ |

**per-key 混合链路完美生效**: k1/3/5 各锁 fid1/2/3 (pexec), k2/4 走 integrate, 全部经 5 US IP.

### dsv4p_nv40066 独立响应 (作 fallback 验证)
- 3/3 × 200, 1.0-3.2s, model=dsv4p_nv ✓ (可作 fallback 目标)

### cc4101 端实测 (8 次 glm5_2_nv)
- 7/8 = 200 (1× 000 超时), 初步 SR 87.5% (样本小, 待 30min 窗口)

### 5min SR 总览 (所有 caller)
- 11×200 + 1×429 = 91.7% (改后初期, 趋势向好)

## 下一步
- 等 30min 稳定窗口, 确认 glm5_2_nv (cc4101-primary) SR ≥ 90%, dsv4p fallback 触发率 < 10%.
- 观察 integrate path (k2/4) 是否稳定 (历史 integrate 间歇挂, 但 5US IP 轮转测 96%).
- 观察 fid2/fid3 (k3/k5) 实际表现 (测试时 fid2 88%, fid3 52%, 待生产验证).
- 若 SR < 90% 持续, 考虑把 k3 也切 integrate (fid3 太不稳).
- 触发回切阈值沿用 R621: SR<55% 或 exhausted>=8 持续才回切, 单小时低不触发.

## 参数快照 (R649 部署后)
- cc4101: PRIMARY=glm5_2_nv@nv_gw:40006, FALLBACK=dsv4p_nv@dsv4p_nv40066:40066, HEADER=400, DEADLINE=470
- nv_gw: MODE_CHAIN=pexec_us_rr,integrate_us_rr, KEY_MODE_BIND=k1/3/5 pexec + k2/4 integrate, FID_BIND=k1/3/5→fid1/2/3
- nv_gw: MS_FALLBACK=0, PEER_FALLBACK=0, DISABLE_MS=1 (全关, 由 cc4101 fallback)
- dsv4p_nv40066: pexec-only, 5 US IP (7900-7904), 无 fallback, free 5-key, port 40066
- mihomo (宿主 pid 1056): 7894-7904 共 10 端口, glm5_2 用 7894-7899, dsv4p 用 7900-7904

## 铁律遵守
- ✅ 改前有数据 (R639-R648 NOP + 08-03 多链路测试 96% vs 72%)
- ✅ 改后有验证 (health + DB per-key 铁证 + dsv4p 独立响应 + SR 总览)
- ✅ 聚焦 nv_gw (40006) + 新 40066, 不碰 HM1
- ✅ ms_gw fallback 关闭 (NVU_MS_FALLBACK_ENABLED=0 + NVU_DISABLE_MS_FALLBACK=1, 与 CLAUDE.md R-nvonly 一致)
- ✅ 所有修改写入仓库 (本文件)
- ✅ bind-mount 改 .py 后 restart nv_gw + dsv4p_nv40066 (env 改动用 up -d 重建)
- ✅ 只改 HM2

## 回滚预案
- compose: `cp docker-compose.yml.bak.R-glm52split.20260803_150723 docker-compose.yml`
- 源码: `cp config.py.bak.R-glm52split.20260803_150723 config.py; cp upstream.py.bak.R-glm52split.20260803_150723 upstream.py`
- 重启: `docker compose up -d nv_gw cc4101 && docker rm -f dsv4p_nv40066`
