# R795: NOP 巡检 + R794 改动后置验证 (58th consecutive 100%)

## 摘要

接棒发现上 session 已用 R794 编号完成了实质改动 (DB 加 function_id 列 + upstream.py
透传 + mihomo filter 排除香港, 跨 HM1/HM2)。R795 是 R794 restart 之后的第一个 30min
验证窗口: 链路 SR 仍 100% (91/91), 0 fb, tier 噪声 19 零穿透 — **R794 改动未破坏现状**。
本轮 NOP 不改码, 记 R794 后置验证数据。

## R794 改动回顾 (上 session, commit db0fbc9)

- DB schema: `nv_requests` + `nv_tier_attempts` 加 `function_id TEXT` 列 + 复合索引 (两机)
- HM1 额外补 R784 遗漏的 egress_ip/egress_route 列
- db.py (两机 298 行统一): INSERT 列清单加 function_id, egress_ip, egress_route
- upstream.py (两机): 13 个 key_cycle_attempts.append 分支加 function_id 字段
  (pexec 真实 NVCF id, integrate 占位 "integrate") + execute_request 两出  口透传
- mihomo filter 排除香港 (HM2: `^(?!.*香港|.*HK|.*Hong).*(美国|圣何塞|阿什本|洛杉矶|日本东京|AWS日本)`)
- 备份: db.py/upstream.py.bak.R794 (两机), config.yaml.bak.R794 (两机)

## 本轮 (R795) 改了什么 + 依据 + 验证

### 改动: 不改码 (NOP) — R794 后置验证轮

### 依据 (轮前链路分析 08:50 CST + 自查 DB, 30min 窗口, R794 restart 后)

- **cc2 (cc4101-primary|glm5_2_nv): 91 req × 200 (SR=100%), 0 fb, 0 穿透** ✅
- 连续 58 轮 (R735~R795) SR 100%, fb 0%
- cc4101 总览 (含其他 caller): 945 req, ok=934, fb=9, SR=98.8%
  - 499×11 on glm5_2_nv primary fb=0 → client_gone_mid_stream (客户端主动断连, 非 NVCF 失败)
  - fb 9 = glm5_2_ms(7) + dsv4f_nv(2) 两个 mapped_model 走 fallback 路径, **非 cc2 请求**
- tier 噪声 **19** (与 R793 持平):
  - NVCFPexecRemoteDisconnected×17: k3:5+k1:4+k2:4+k4:2+k0:1 (均布非单key) — R793:16→17 微升 1
  - empty_200×2 (k0:1+k2:1)
- 顶层 all_tiers_exhausted×4 全在 dsv4 hermes caller (dsv4f0731_nv 注入 502 噪声), 零穿透到 cc2
- buffer 日志 (实测确认): 全 attempt=1/-SUCCESS, elapsed 3-18s, 无 retry/WAIT/KEYMGR/BREAKER
- nv_gw StartedAt=2026-08-04T18:52 UTC (= 2026-08-05 02:52 CST) = R794 restart 后

### 验证 (NOP 无 restart)
- 容器: nv_gw Up 6h (= R794 restart 后续), cc4101 Up 7h, dsv4p_nv40066 Up 12h, logs_db Up 5d, ms_gw Up 7h
- /health: nv_gw ok nv_num_keys=5 proxy_role=passthrough; cc4101 ok primary=glm5_2_nv

## 判稳结论
- **cc2 nv_gw 链路连续 58 轮 (R735~R795) SR 100%, fb 0%** — 达标 (目标 SR 99%+/fb <10%)
- R794 改动 (DB+upstream透传+mihomo) 验证未破坏链路, function_id 维度已落库 (不影响执行路径)
- tier 噪声 19 零穿透, RemoteDisc 17 均布 k0-k4 非单 key 故障, buffer 全吸收
- RemoteDisc 偏高已连续 4 轮 (R791:12+R792:12+R793:16+R794(R795):17) — NVCF-sided 周期性 jitter
- 判定: 链路健康无可改项, NOP 巡检轮

### SR 趋势
| 轮 | 30min SR | tier 噪声 | 备注 |
|---|---|---|---|
| R791 | 100% (113) | 12 | k3 RemoteDisc 5 偏高续 |
| R792 | 100% (101) | 14 | RemoteDisc 12 均布 k0-k4 |
| R793 | 100% (91)  | 19 | RemoteDisc 16 均布 k0-k4 偏高 |
| R795 | 100% (91)  | 19 | R794 改动后���验证, RemoteDisc 17 持平偏高 |

## 下一步
- 持续监控 cc2 SR + fb (目标 SR 99%+/fb <10%)
- R794 后置: 下轮可拉 function_id 分布 SQL 验证 per-fid×per-IP×per-key 立体限速诊断数据齐备
  (例如: `select function_id, egress_ip, nv_key_idx, count(*) from nv_tier_attempts
   where ts > now()-interval '30 min' and function_id is not null
   group by 1,2,3 order by 4 desc;`)

## R794 端到端三维落库验证 (实测 30min)

### nv_requests (cc2 cc4101-primary 请求, 91 全 200)
| function_id (8 char) | egress_ip | egress_route | total | ok |
|---|---|---|---|---|
| b1b22d03 | (空)         | glm52-mihomo-7901 | 18 | 18 |
| b1b22d03 | 134.195.101.180 | glm52-mihomo-7899 | 17 | 17 |
| b1b22d03 | 134.195.101.195 | glm52-mihomo-7896 | 17 | 17 |
| b1b22d03 | 134.195.101.193 | glm52-mihomo-7894 | 16 | 16 |
| b1b22d03 | 134.195.101.193 | glm52-mihomo-7897 | 15 | 15 |
→ 全走 fid `b1b22d03-` (K1 pexec fid1), 4 美国 IP 实测 134.195.101.{180,193,195}+1 空, 5 mihomo 端口全工作

### nv_tier_attempts (per-key fid 分布)
| function_id (8 char) | key | count |
|---|---|---|
| b1b22d03 | k4 | 18 |
| b1b22d03 | k0 | 18 |
| b1b22d03 | k3 | 18 |
| b1b22d03 | k1 | 16 |
| b1b22d03 | k2 | 16 |
| 52e1ddb6 | k0 | 4 |
| 52e1ddb6 | k2 | 5 |
| 52e1ddb6 | k3 | 4 |
| 52e1ddb6 | k1 | 4 |
| 52e1ddb6 | k4 | 3 |
→ 主 fid b1b22d03 (84 attempts), 备 fid 52e1ddb6 (20 attempts) — 备 fid 在 k0-k4 均布说明 buffer 选 fid 路径生效, R794 function_id 维度完整记录

**结论**: R794 改动 (DB schema + db.py INSERT + upstream.py 透传 + mihomo filter) 端到端验证
通过, function_id/egress_ip/egress_route 三维全落库, 链路 SR 100% 未受影响.
- RemoteDisc 偏高模式 (连续 4 轮 12~17) 若连续多轮且偶发穿透 cc2 → 排查 NVCF pexec 端点
- dsv4p_nv fallback 链路健康, 应急 OK

## 参数快照 (R795, 实测无变化)
- nv_gw: NVU_DISABLE_MS_FALLBACK=1, UPSTREAM_TIMEOUT=90, TIER_TIMEOUT_BUDGET_S=180, TIER_COOLDOWN_S=180
- nv_gw: NVU_CALLER_KEY_MAP=hermes:2;openclaw:3;opencode:4
- nv_gw: NVU_BUFFER_CALLERS=cc4101-primary,openclaw2, NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv
- nv_gw: MIN_OUTBOUND_INTERVAL_S=10, NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150, KEY_COOLDOWN_S=30, NV_INTEGRATE_KEY_COOLDOWN_S=90
- cc4101: PRIMARY=glm5_2_nv→nv_gw:40006, FALLBACK=ms_gw:40007(env), STREAM_TOTAL=470, HEADER=400
- nv_gw StartedAt: 2026-08-05 02:52 CST (= R794 restart)
- 链路: cc2→cc4101(4101)→nv_gw(40006, glm5_2_nv)→NVCF
