# R401: NOP 巡检轮 (cc2 0req, dsv4p_nv SR=93.9% 31/33, all_tiers_exhausted×2 avg 20818ms, 一百二十五轮一致)

## 当前轮基线 (2026-08-02 23:31 CST, R400 已完成, R401 巡检)
- 本仓 master: R399 已 commit. hermes 仓: R400 已 push.
- **架构**: cc4101 `PRIMARY_UPSTREAM_MODEL=dsv4p_nv`. cc2 链路 = cc4101(dsv4p_nv) → nv_gw → NVCF.
- **本轮 R401 (hm2_cc2)**: NOP 巡检轮. cc2 (cc4101-primary) 30min 0 req (session 间歇空闲).
  dsv4p_nv 30min 全 caller SR=93.9% (31/33), 失败 2 = all_tiers_exhausted×2
  (sub=`all_tiers_failed_in_mapped_tier`, avg 20818ms, NVCF dsv4p function 本窗口配额瞬时空位,
  全非缓冲 caller mapped-tier 直接失败无轮转保护).
  成功 31×200: key2 30× (hermes mapped, avg 10930ms, egress 203.10.96.139×30) + key3 1× (openclaw, 4445ms, egress 134.195.101.194×1).
  **cc2 是缓冲 caller (NVU_BUFFER_CALLERS), 走 buffer 5key 轮转路径, 不走 mapped-tier 直接失败, 不受影响.**
  错误类型无新增 (dsv4p 仍 all_tiers_exhausted, 一百二十五轮一致).
  cc2 无流量不受影响, 0 fallback 0 deadline. 0 改动 0 restart. **一百二十五轮一致 R268-R401**.
  ProbeWorker + KeyManager decayed reset 自恢复链实测有效.

## R-nvonly 核心铁律 (持续生效)
- 只改 HM2 nv_gw (40006), 不碰 HM1, 不碰 ms_gw 源码.
- ms_gw fallback 已恢复 (`NVU_DISABLE_MS_FALLBACK=0`, `FALLBACK_UPSTREAM=ms_gw:40007`), 不主动禁用.
- 改前有数据, 改后必验证, 写入仓库.

## 本轮关键数据 (30min 实时链路分析注入 ~23:31 CST)

### 1. cc2 (cc4101-primary) 30min 0 req
- session 间歇空闲, 链路空闲健康. 0 fallback 0 deadline.
- buffer/wait 日志 (BUFFER-/WAIT-) 30min 空 (无 buffer 流量).
- caller × model × status: 仅 hermes/dsv4p_nv (30×200+1×429+1×502) + openclaw/dsv4p_nv (1×200), 无 cc4101-primary 行.

### 2. dsv4p_nv 30min 全 caller SR=93.9% (31/33)
| caller | request_model | status | count | avg_dur |
|---|---|---|---|---|
| hermes | dsv4p_nv | 200 | 30 | 10930 |
| hermes | dsv4p_nv | 429 | 1 | 8005 |
| hermes | dsv4p_nv | 502 | 1 | 33630 |
| openclaw | dsv4p_nv | 200 | 1 | 4445 |

per-key (nv_key_idx): 空 → 2×fail (429+502, mapped tier 直接失败时 nv_key_idx 字段为空, 设计行为);
  key2 → 30×200 (avg 10930ms, egress 203.10.96.139×30); key3 → 1×200 (openclaw, 4445ms, egress 134.195.101.194×1).
fallback_occurred=f×33 (全部 false, 0 fallback).
finish_reason 分布: tool_calls×26 + stop×5 (无 zombie/异常长流).

### 3. 30min 错误分类
| error_type | sub | count | avg_dur |
|---|---|---|---|
| all_tiers_exhausted | all_tiers_failed_in_mapped_tier | 2 | 20818 |

### 4. 30min 按分钟趋势 (15:05-15:31 CST)
- 15:05-15:31 稳定 200 流 (31×200), 15:06 502×1 + 15:31 429×1 间夹.
- 失败仅 15:06 (502) 与 15:31 (429), 其余时段全 200, function 配额波动间歇性极低频.

## dsv4p_nv SR 趋势 (近 10 轮, 全非缓冲 caller, cc2 0 req)
- R392 44.4% → R393 44.4% → R394 58.3% → R395 71.4% → R396 87.0% → R397 87.5% → R398 93.3% → R399 93.3% → R400 97.1% → **R401 93.9%**
- 样本极小全非缓冲 caller mapped-tier 直接失败, SR 直接反映 NVCF 瞬时配额波动.
- cc2 缓冲 caller 走 buffer 5key 轮转, 不走 mapped-tier 直接失败, 不受同影响.
- 趋势高位小幅回落 (R400 97.1% → R401 93.9%, 样本极小自然波动), NVCF function 配额波动维持高位区间.

## 根因: NVCF dsv4p function 429/502 波 (非代码缺陷, 沿用 R278-R400 分析)
- 非缓冲 caller hermes mapped-tier 直接走 NVCF, function 配额瞬时空位 → 429/502 → all_tiers_exhausted.
- 5key (k0-k4) 全绑同一 NVCF function, function 级配额耗尽时多 key 同时收 429 → all_tiers_exhausted.
- buffer 5key 轮转设计针对 key/IP 级隔离, 对 function 级 429 是已知盲区 (非代码缺陷).
- cc2 缓冲 caller 走 buffer 路径不走 mapped-tier, 不受影响.

## 判稳
- **NOP 巡检轮**. cc2 primary 0 req, 链路空闲健康, 0 fallback 0 deadline.
- dsv4p_nv 本轮 SR=93.9% (31/33), 较 R400 97.1% 小幅回落 (样本极小自然波动, 趋势持续高位).
- dsv4p 错误类型无新增, 与 R268-R400 一致 (一百二十五轮一致).
- /health ok, 容器全 Up (nv_gw 21h, cc4101 9h, ms_gw 3d, logs_db 3d).

## 下一步
- 继续 NOP 巡检, 等 cc2 流量恢复后观察 dsv4p_nv buffer 路径行为.
- 关注新错误类型 (非 all_tiers_exhausted) 或 key/IP 级故障, 再决定是否介入.
- all_tiers_exhausted 持续 >=5/h 再评估 buffer/KeyManager 参数.

## 参数快照 (本轮未改)
- nv_gw: NVU_DISABLE_MS_FALLBACK=0, UPSTREAM_TIMEOUT=90, TIER_TIMEOUT_BUDGET_S=180,
  TIER_COOLDOWN_S=180, KEY_COOLDOWN_S=30, NV_INTEGRATE_KEY_COOLDOWN_S=90,
  MIN_OUTBOUND_INTERVAL_S=10, NVU_FORCE_STREAM_UPGRADE=0,
  NVU_BUFFER_CALLERS=cc4101-primary,openclaw2, NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv,
  NVU_CALLER_KEY_MAP=hermes:2;openclaw:3;opencode:4
- cc4101: PRIMARY_UPSTREAM_MODEL=dsv4p_nv, PRIMARY_UPSTREAM_URL=http://nv_gw:40006/v1/messages,
  FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/chat/completions, FALLBACK_UPSTREAM_MODEL=glm5_2_ms,
  PRIMARY_HEADER_TIMEOUT=400, CC4101_STREAM_TOTAL_DEADLINE_S=470,
  CC4101_PRIMARY_FAIL_THRESHOLD=3, CC4101_PRIMARY_SKIP_S=30,
  UPSTREAM_TIMEOUT=130, UPSTREAM_IDLE_TIMEOUT=150
- deadline 链: 90s/attempt × 5 = 450s buffer < 470s cc4101 < 500s SDK idle
- settings.json: contextWindow=170000, autoCompactWindow=155000, API_TIMEOUT_MS=600000

## 仓库与主机
- hermes 仓: `~/hm_ps/hermes_improve_self` (remote gitychzh/NVForge, branch main)
- cc2 仓: `~/cc_ps/cc2_repair_self` (remote gitychzh/cc2_repair_self, branch master)
- 容器栈: `/opt/cc-infra` (docker-compose.yml + proxy/nv-gw/gateway/ bind-mount)
- nv_gw 源码: `/opt/cc-infra/proxy/nv-gw/gateway/{config,upstream,handlers,db,key_manager,buffer_stream}.py`
- peer HM1 (别碰): `opc_uname@100.109.153.83`
