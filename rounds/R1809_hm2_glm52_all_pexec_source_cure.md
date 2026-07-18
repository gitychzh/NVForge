# R1809 — HM2 cc2: 源头治本 — glm5_2_nv 全 key 切 pexec (KEY_MODE_BINDING 去 integrate)

> 铁律：只改 HM2，不改 HM1，不碰 proxy/ms-gw。改前必有数据，改后必有验证。

## 性质
**执行轮（非巡检）**。采纳监督者 22:20 提示的"源头治本方案"，但靶向修正：
监督者建议改 `NV_INTEGRATE_MODELS` 移除 glm5_2_nv，但 R839 起 `NV_INTEGRATE_MODELS=`
（空，早移除了），glm5_2_nv 是通过 **R1621b `KEY_MODE_BINDING` per-key 固定绑定** 才持续
有 integrate 流量。真正旋钮是 compose line 97 的 `KEY_MODE_BINDING`。

## 改前数据（2026-07-18 23:51 CST = 15:51 UTC, R1798 burn-in 后 ~2h25min）

### 30min 窗（nv_gw cc4101-primary glm5_2_nv）
- SR = 57/62 = **91.9%**，失败 5：stream_first_byte_timeout×3 + stream_no_content_gap×2
- 失败 upstream_type：ms_fallback×2（23:29/23:36，nv_gw tier 全坏后转 ms 也超时）
  + nv_integrate×3（23:39/23:41/42，全在 integrate 链路）

### 2h 窗
- SR = 210/232 = **90.5%**，失败 22：stream_first_byte_timeout×10 + stream_no_content_gap×7 +
  all_tiers_exhausted×2 + zombie_empty_completion×2 + stream_absolute_cap×1

### 监督者 22:20 核心发现验证（2h 按 upstream_type 失败率）
| upstream_type | total | ok | fail | fail_pct |
|---|---|---|---|---|
| nvcf_pexec | 99 | 99 | 0 | **0.0%** |
| nv_integrate | 125 | 113 | 12 | **9.6%** |
| ms_fallback | 8 | 0 | 8 | 100.0%（fallback 也超时） |

- **stream_no_content_gap 7/7 全在 nv_integrate，pexec 零** — 22:20 发现精确成立 ✓
- stream_first_byte_timeout：ms_fallback×8 + nv_integrate×2（pexec 零）

### 22:20 要求的"延迟数据"（自拉，2h 200 ok 样本）
| upstream_type | avg_ms | p50 | p90 | p99 | max |
|---|---|---|---|---|---|
| nvcf_pexec | 23573 | 19657 | 44310 | 58329 | 63631 |
| nv_integrate | 26060 | 18987 | 46738 | 106808 | 135886 |

**关键**：pexec avg(23.6s) **不劣于** integrate avg(26.1s)，且 p99/max **远更可控**
（p99 58s vs 107s，max 64s vs 136s — integrate 长尾正是 hang 前兆）。R572 当初选 integrate
的理由（注释说 integrate 快 2-3x）在当前数据下**完全不成立**。

### fallback 率（cc4101 30min）
- grep FALLBACK/PRIMARY-FAIL = 0（30min 无 cc4101 层 fallback；DB 的 2 条 ms_fallback 是
  nv_gw 内部 tier 全坏后转 ms，非 cc4101 抢断）

### peer HM1 佐证
R1804-1808 peer HM1 agent 持续报 "glm5_2 100% pexec, 100% SR(24/24), avg 10285ms"
（HM1 早已全 pexec，HM2 还在 mode chain 喂 60% integrate）。

## 拟改（单点，env 改动）

compose line 97：
```
- KEY_MODE_BINDING=0:integrate_us_rr;1:pexec_us_rr;2:integrate_us_rr;3:pexec_us_rr;4:integrate_us_rr
```
改为（全 5 key 走 pexec_us_rr）：
```
- KEY_MODE_BINDING=0:pexec_us_rr;1:pexec_us_rr;2:pexec_us_rr;3:pexec_us_rr;4:pexec_us_rr
```

- 不改 `NV_GLM52_MODE_CHAIN`（保留 integrate_us_rr,pexec_us_rr 作为故障递进兜底链，
  只是把"正常请求 per-key 绑定"从 60% integrate 改为 100% pexec）。
- 不改 `NV_INTEGRATE_MODELS`（已空）。
- 不碰 `NVU_STREAM_ABSOLUTE_CAP_S=150`（cap 留着兜底 pexec 偶发真 hang，治本+治标不冲突）。

## 预期
1. nv_integrate 流量归零（2h 后 DB `upstream_type=nv_integrate` count 应=0 或接近 0）。
2. stream_no_content_gap 归零（2h 后该 error_type count 应=0）。
3. 整体 SR 从 90.5% → ≥97%（向 peer HM1 的 100% 看齐）。
4. 延迟不劣化（pexec avg ~23.6s 与 integrate 26.1s 同级，p99 反降）。
5. fallback 率保持低位（cc4101 无需 fallback，nv_gw tier pexec 自给自足）。

## 验证清单
- [ ] `docker compose up -d nv_gw`（env 改动必须 up -d 非 restart，R1797 教训）
- [ ] `docker exec nv_gw env | grep KEY_MODE_BINDING` 确认全 pexec
- [ ] `curl -s http://localhost:40006/health` ok
- [ ] `docker ps` nv_gw Up + ms_gw 热备在
- [ ] 下窗口（10-30min）日志：nv_gw NV-GLM52-SUCCESS，DB nv_integrate count 不再涨
- [ ] SR 不掉 + stream_no_content_gap 归零趋势
- 验证失败 → `cp docker-compose.yml.bak.R1809 docker-compose.yml && docker compose up -d nv_gw` 回滚

## 测速脚本覆盖风险评估
`glm52_speedtest.py`（cron 02:00/14:00）注释明确"不改生产配置，只直打测速+打印建议 chain"。
源码确认：只读测速、写 log，**不写 compose/不重启**。所以 02:00 不会覆盖 KEY_MODE_BINDING。
（mode chain 留 integrate 兜底链，即使测速"建议"重排 MODE_CHAIN 也不影响 per-key 绑定。）
