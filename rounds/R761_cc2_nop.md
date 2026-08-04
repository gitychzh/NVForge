# R761: cc2 NOP 巡检 — 第 27 连续 100% 轮 (R735~R761)

> cc2 nv_gw 自优化链路. NOP 巡检, 不改码.
> 注: cc2 round 编号与 HM2 其他工作流 (hm4104/opclaw) 共用 rounds/ 目录,
> 本轮文件名加 `cc2_` 前缀以区分, STATE 轮号沿用 R761.

## 改前数据 (created_at 口径, 30min, ~06:30 CST)

### cc2 (cc4101-primary) nv_requests
- status=200: 90 req, SR=100.0%

### cc4101 cc_requests
- total=90, ok=90, fb=0, sr=100.0%

### glm5_2_nv tier (nv_tier_attempts)
- pexec_success: 95
- pexec_429: 1 (buffer 兜住, 零穿透 cc2)
- 无 NVCFPexecRemoteDisconnected / empty_200 / all_tiers_exhausted 在 glm5_2_nv tier

### 注入噪声 (轮前链路分析) — 全在 hermes→dsv4f0731_nv, 不在 cc2 路径
- dsv4f0731_nv 30min SR=82.8% (24/29), 5×502 — hermes 备份 NVCF 容量噪声
- all_tiers_exhausted × 10, NVCFPexecRemoteDisconnected × 14, empty_200 × 4 — hermes 侧 buffer 兜住
- 注入 "f|143" fallback 发生率 → ts 列时区 bug 口径 (created_at 实测 fb=0, 沿 R730/R742~R760 实证)

## 验证 (NOP 无需 restart)
- /health: nv_gw ok (nv_num_keys=5), cc4101 ok (primary=glm5_2_nv)
- docker ps: nv_gw Up 4h, cc4101 Up 5h, dsv4p_nv40066 Up 10h, ms_gw Up 5h, logs_db Up 5d — 全 Up

## 判稳结论
- SR=100% >= 99% ✅, fb=0% < 10% ✅, 无新错误类型 ✅ → NOP 巡检轮
- **cc2 nv_gw 链路连续 27 轮 (R735~R761) SR 100%, fb 0%**
- 本轮 glm5_2_nv tier: 95 pexec_success + 1 pexec_429 (零穿透, buffer 兜住) — 连续第 15 轮最干净
- 流量 90 req/30min (R760=87→R761=90, 窗口抖动正常)

### SR 趋势 (新增一行)
| 轮 | 30min 窗 SR | 备注 |
|---|---|---|
| R760 | 100% (85 nv / 87 cc) | 26th consecutive, 14th cleanest |
| R761 | 100% (90 nv / 90 cc) | **27th consecutive, 15th cleanest (tier pexec_429×1 buffer-absorbed)** |

## 下一步
- 持续监控, 流量低时不动码
- pexec_429 × 1 是 R-glm52split 后首次在 glm5_2_nv tier 出现 429 — 数量极小 (1/96=1%), 不构成异常, 继续观察是否累积
- 若 429 累积或穿透到 cc2, 再查 KeyManager 退避 / per-key 分布

## 参数快照 (沿 R760, 无变化)
- nv_gw: NVU_DISABLE_MS_FALLBACK=1, MODE_CHAIN=pexec_us_rr, 全 key 绑 fid1=b1b22d03,
  KEY_PROXY_BIND=0:7901;1:7894;2:7897;3:7896;4:7899, buffer 5×90s=450s
- cc4101: PRIMARY=glm5_2_nv→nv_gw:40006, FALLBACK=glm5_2_ms→ms_gw:40007,
  STREAM_TOTAL=470, HEADER=400, UPSTREAM_IDLE=150, UPSTREAM_TIMEOUT=130
