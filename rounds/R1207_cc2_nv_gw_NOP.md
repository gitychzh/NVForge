# R1207 cc2 nv_gw NOP — 滚动窗口边界归零: 表面 2× buffer_exhausted 全为上轮已计重复, 实际新增失败=0

- 日期: 2026-08-08 (R1206 之后, 07:18 CST 巡检)
- 结论: **NOP**, 不改码。升级监控条件未实质触发。

## 30min 窗口 (cc2 链路, cc4101-primary)
- nv_requests: `200|74`, `502|2` (均 buffer_exhausted) → 表面 SR=97.4%
- dsv4f0731_nv 全量 (含 hermes): SR=100.0% (119/119)
- 容器: nv_gw ok (5 keys), cc4101 ok (primary=dsv4f0731_nv), dsv4p ok; nv_gw 28h, cc4101 27h 无漂移

## 关键判断: 2× 502 全部是上轮重复, R1207 新增失败 = 0
| request_id | ts (UTC) | dur | 归属 |
|---|---|---|---|
| 7562e67f | 22:45:43 | 79860ms | **R1205 blip 重复计入** (22:43-22:47 全-key SSL egress blip) |
| 7f34c956 | 23:04:02 | 167010ms | **R1206 本轮新失败重复计入** (R1206 已完整分析 k1→k2→k3 连续 Remote-end-closed) |

- 滚动窗口边界 re-sample: 上轮已计入的错误请求随 30min 滑窗进入本轮窗口, 逐分钟趋势确认
  22:44/22:47/23:06 的 502 分别对应上面两条, 无其他新增。
- 其余所有错误 attempt (22:32:57 k3 RemoteDisconnected, 22:42:22 k0 Timeout, 22:54:48 k1
  RemoteDisconnected, 22:55:49 k4 Timeout, 23:04:49 k3 Timeout, 23:15:54 k0 Timeout) 均属
  attempt-2/3 **自愈成功**的请求, status 最终 200。单 attempt 瞬时抖动, 防御链 (buffer upgrade +
  key fail) 按设计吸收, 无 out-window 失败。

## R1206「下一步升级监控」条件判断 (本轮的实质增量)
- R1206 约定: "若 R1207 仍见此类分散错误 + SR<99% → 拉 mihomo 隧道线路质量, 评估 key→proxy 绑定"
- 结果: 表面 SR 97.4% <99% 且见 buffer_exhausted, **看似触发**; 但深入归属核实后, 2× 502 实为
  R1205/R1206 已计入错误在滑窗边界的重复采样, **本轮实际无新失败**, 同信号的 attempt 级错误全数
  自愈。故**不满足"仍见此类分散错误"的实质条件**, mihomo 隧道检查延后, 条件暂未闭合。
- 若 **R1208** 出现真实新失败 (非上轮 request_id 残留) 且 SR<99% → 再拉 mihomo 隧道质量。

## 参数快照 (与 R1206 一致, 无变更)
- nv_gw: UPSTREAM_TIMEOUT=90, NVU_BUFFER_MAX_RETRIES=5 (90×5=450s), NVU_DISABLE_MS_FALLBACK=0,
  NVU_FORCE_STREAM_UPGRADE=0, KEY_COOLDOWN_S=30, TIER_COOLDOWN_S=180, MIN_OUTBOUND_INTERVAL_S=10,
  NV_INTEGRATE_KEY_COOLDOWN_S=90, NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150, TIER_TIMEOUT_BUDGET_S=180,
  NVU_BUFFER_CALLERS=cc4101-primary,openclaw2, full-key bind fid index0=281478d0-f307 (dsv4f0731_nv)
- cc4101: PRIMARY_UPSTREAM_MODEL=dsv4f0731_nv, FALLBACK_UPSTREAM_MODEL=glm5_2_ms,
  FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/chat/completions, CC4101_STREAM_TOTAL_DEADLINE_S=470,
  PRIMARY_HEADER_TIMEOUT=400, PRIMARY_FAIL_THRESHOLD=3, PRIMARY_SKIP_S=30, UPSTREAM_TIMEOUT=130

## 上轮
R1206 (NOP): 3× buffer_exhausted 中 2=R1205 blip 重复, 1 新失败 7f34c956 跨 k1-k3 连续 3 次
Remote-end-closed。→ R1207: 该 7f34c956 + 7562e67f 随滑窗带进本轮, 无任何新失败。SSLEOFError
瞬时 egress 抖动自 R1205 泛化后未产生净新增。

## 下一步
- 维持静稳观察。单次瞬时自愈错误 / 上轮残留重计一律 NOP 自愈。
- mihomo 隧道质量检查升格触发条件: **R1208 出现真实新失败 + SR<99%** 才执行 (R1206 条件经本轮
  归属核实证明"表面 SR<99%"不充分, 必须以新增失败为准)。
- 主键: 最大化单位时间 NV 成功数; 存在历史 3h 100% SR 基线, 防御链工作正常。