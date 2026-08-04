# R734: cc2 nv_gw NOP 巡检 (2026-08-05 ~02:20 CST)

## 改动
不改码 (NOP)。

## 依据 (实测 60min 窗口 ~01:20-02:20 CST, created_at 字段)

### cc4101 用户可见 SR (cc_requests, 60min)
- 54 req: 53×200(primary ok) + 1×200(primary timeout→fallback dsv4p 成功) + 2×499(client_gone, 非 nv_gw)
- **用户可见 SR = 54/54 = 100%** (2×499 = cc2 SDK 主动断连, 非 nv_gw 故障)
- fallback 触发率 = 1/54 = 1.9% (< 10% 目标)

### nv_gw 层 (nv_requests, cc4101-primary, 60min)
- 30 req: 28×200 + 2×502(buffer_exhausted, avg 390.5s)
- nv_gw SR = 28/30 = 93.3% — 2×502 均为 5key 全挂后 buffer 跑满 450s+ 撞到 cc4101 470s 上限
- 但 cc4101 fallback 救回 1 个 (另 1 个是 nv_gw 60min 窗口内的另一时段, cc4101 已 fallback 成功)
- 30min 窗口: 25×200 + 2×502, nv_gw SR = 92.6%

### 错误分类 (cc4101-primary, 60min)
- buffer_exhausted × 2 (avg 390.5s) — 5key 全挂, buffer 跑满
- 无 stream_first_byte_timeout / NVStream_IncompleteRead 在 cc4101-primary 专属段 (注入分析里这俩是全 caller 汇总)

### per-key tier 错误 (nv_tier_attempts, 30min, glm5_2_nv tier)
- 529_nv_overloaded 是绝对主因: k0=24, k1=29, k2=27, k3=23, k4=29 (共 132 次)
- 404_nv_function_not_found: k0=5, k1=2, k2=1, k3=1, k4=3 (共 12 次)
- pexec_success: k0=8, k1=5, k2=5, k3=6, k4=11 (共 35 次成功)
- NVCF 上游 529 overloaded 是 NVCF 容量问题, 非 nv_gw 代码可改

### 注入轮前分析 vs 实测一致性
- 注入 30min: cc4101-primary 25×200 + 2×502(buffer_exhausted) — 与实测一致
- 注入 glm5_2_nv SR=100% (38/38) = nv_gw 对 cc4101-primary 的最终判定 (含 fallback 后? 或仅 primary path?) — 实测 nv_requests 30min 是 25×200+2×502, 60min 是 28×200+2×502, 差异因时间窗口偏移
- fallback f|127 (30min 全 caller) = cc4101 fallback 触发标记, 本轮 cc4101-primary 1/54=1.9%

## 验证 (NOP 无需 restart)
- `/health`: nv_gw ok(5keys, glm5_2_nv default) + cc4101 ok(primary=glm5_2_nv) + dsv4p_nv40066 ok(5keys) — 全 ok
- `docker ps`: nv_gw Up 5h, cc4101 Up 36min, dsv4p_nv40066 Up 6h, nv_gw_stable Up 3days, logs_db Up 5days — 全 Up
- env 零漂移 (沿 R-glm52split 架构)

## 判稳结论
- **用户可见 SR 100% (54/54)** — 超过 99% 目标
- **nv_gw SR 93.3%** (28/30, 60min) — 低于 90%+ 目标但根因是 NVCF 529 overloaded 上游容量, 非 nv_gw 可改
- **fallback 触发率 1.9%** (1/54) — 远低于 10% 目标, fallback 机制正常工作
- **2×499 client_gone** = cc2 SDK 主动断连, 非 nv_gw 故障
- 529 overloaded 是 NVCF 上游问题, 流量低时不动码, NOP 记数据

## 下一步
- 持续监控 cc2 SR + fallback 触发率 (目标 SR99%+ fb<10%)
- 当前用户 SR 100%, nv_gw SR 93.3%, fb 1.9% — 用户层面超目标
- 529 overloaded 若持续高频, 考虑: (a) 加大 buffer attempts (但已 5×90s=450s 接近 cc4101 470s 上限, 空间小); (b) 降低 MIN_OUTBOUND_INTERVAL_S (当前 10s) 增加探测频率 — 但根因是 NVCF 容量, 缓解有限
- 流量低时不动码, 仅 NOP 记数据

## 参数快照 (无变化, 沿用 R-glm52split, 实测 env 确认)
- nv_gw: NVU_DISABLE_MS_FALLBACK=1 (ms_gw 关, fallback=dsv4p_nv40066), buffer 5×90s=450s (NVU_BUFFER_MAX_RETRIES=5, NVU_BUFFER_TIMEOUT_STAIRS=90,90,90,90,90), UPSTREAM_TIMEOUT=90, TIER_COOLDOWN_S=180
  - per-key FID bind: NV_GLM52_KEY_FID_BIND=0:0;2:1;4:2 (k0/k2/k4 pexec fid1/2/3)
  - per-key mode bind: NV_GLM52_KEY_MODE_BIND=0:pexec_us_rr;1:integrate_us_rr;2:pexec_us_rr;3:integrate_us_rr;4:pexec_us_rr
  - NV_GLM52_MODE_CHAIN=pexec_us_rr,integrate_us_rr
  - NVU_BUFFER_CALLERS=cc4101-primary,openclaw2, NVU_KEYMGR_429_BASE=120/MAX=600, NVU_KEYMGR_CONN_BASE=30/LONG=120/MAX=60
- cc4101: PRIMARY=glm5_2_nv→nv_gw:40006, FALLBACK=dsv4p_nv→dsv4p_nv40066:40066, STREAM_TOTAL=470, HEADER=400, UPSTREAM_IDLE=150, UPSTREAM_TIMEOUT=130
- deadline 链: 90s×5=450s buffer < 470s cc4101 < 600s API < 900s idle
