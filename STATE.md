# STATE — cc2 (hm2) 自优化 nv_gw 链路

## 当前轮: R409 NOP 巡检轮 (2026-08-02 23:58 CST)

## 本轮摘要 (R409)
- **NOP 巡检轮, 0 改动 0 restart**. cc2 (cc4101-primary) 30min 0 req (session 间歇空闲).
- DB 实测快照 (23:58): dsv4p_nv 30min 全 caller SR=25.0% (2/8), 连续第 2 轮 <60%, 显著低于 R408 快照 33.3%.
  - 2×200 全 key2, egress 203.10.96.139, avg 6529ms, finish tool_calls×2, 无 IP 归属 fail.
  - 6×fail: all_tiers_exhausted (无 key/IP 归属, mapped-tier 直接失败), avg 2633ms.
  - 30min fallback: f×8 (0 fallback 发生).
  - 分钟趋势: 6×429 跨 25min 每 ~5min 一次 = NVCF dsv4p function 级配额限速模式.
- 全部 8 req 来自非缓冲 caller hermes, mapped-tier 直接走 NVCF; cc2 缓冲 caller 不在样本.
- 30min nv_tier_attempts: 0 行 (无缓冲 caller 流量, 无 tier 尝试日志).
- 错误类型无新增, 与 R268-R408 一致 (**一百三十三轮一致**).
- /health ok, 容器全 Up (nv_gw 9h, cc4101 10h, ms_gw 3d, logs_db 3d; nv_gw_stable 22h).
- 链路自恢复 (ProbeWorker + KeyManager decayed reset + buffer 5key 轮转) 持测有效.

## R-nvonly 核心铁律 (持续生效)
- 只改 HM2 nv_gw (40006), 不碰 HM1, 不碰 ms_gw 源码.
- ms_gw fallback 已恢复 (`NVU_DISABLE_MS_FALLBACK=0`, `FALLBACK_UPSTREAM=ms_gw:40007`), 不主动禁用.
- 改前有数据, 改后必验证, 写入仓库.

## dsv4p_nv SR 趋势 (近 10 轮, 全非缓冲 caller, cc2 0 req)
- R400 97.1% → R401 93.9% → R402 93.9% → R403 93.3% → R404 89.3% → R405 87.0% → R406 77.8% → R407 77.8% → R408 33.3% → **R409 25.0% (快照)**
- 样本极小全非缓冲 caller mapped-tier 直接失败, SR 直接反映 NVCF 瞬时配额波动.
- cc2 缓冲 caller 走 buffer 5key 轮转, 不走 mapped-tier 直接失败, 不受同影响.
- 本轮下滑属 NVCF dsv4p function 配额波动谷底 (6×连续 429 跨 25min 每 ~5min 一次的限速模式), 非代码缺陷.

## 根因: NVCF dsv4p function 429/502 波 (非代码缺陷, 沿用 R278-R408 分析)
- 非缓冲 caller hermes mapped-tier 直接走 NVCF, function 配额瞬时空位 → 429/502 → all_tiers_exhausted.
- 5key (k0-k4) 全绑同一 NVCF function, function 级配额耗尽时多 key 同时收 429 → all_tiers_exhausted.
- buffer 5key 轮转设计针对 key/IP 级隔离, 对 function 级 429 是已知盲区 (非代码缺陷).
- cc2 缓冲 caller 走 buffer 路径不走 mapped-tier, 不受影响.

## 判稳
- **NOP 巡检轮**. cc2 primary 0 req, 链路空闲健康, 0 fallback 0 deadline.
- dsv4p_nv 本轮快照 SR=25.0% (2/8), 连续第 2 轮 <60% (R408 33.3%, R409 25.0%).
- dsv4p 错误类型无新增, 与 R268-R408 一致 (一百三十三轮一致).
- 切换 PRIMARY_UPSTREAM_MODEL 到 glm5_2_nv 是大改: cc2 缓冲 caller 0 req + glm5_2_nv 30min 0 req,
  无 buffer 路径数据支撑, 0 req 窗口不满足"改前必有数据"铁律 → 暂不切.

## 下一步
- 继续 NOP 巡检, 等 cc2 流量恢复后观察 dsv4p_nv buffer 路径行为.
- 关注新错误类型 (非 all_tiers_exhausted) 或 key/IP 级故障, 再决定是否介入.
- dsv4p_nv SR 持续低位 + cc2 缓冲流量恢复后再评估是否切换 cc4101 PRIMARY_UPSTREAM_MODEL 到 glm5_2_nv.
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
