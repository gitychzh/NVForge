# R1480: HM2→HM1 — re-add dsv4p_nv:dsv4p_ms to ms_gw MODELMAP

## 数据收集 (HM1 via SSH)

### 容器状态
- nv_gw: Up About an hour (restarted)
- logs_db: Up 17 hours
- compose md5: e1f9026c (unchanged from R1479 pre-edit)

### 6h 总体 (nv_requests)
- 44req / 21OK / 23fail = 47.7% SR

### 6h 错误分类
- zombie_empty_completion: 16 (dsv4p_nv 4, glm5_2_nv 12)
- all_tiers_exhausted: 7

### 6h 按模型
- glm5_2_nv: 25req, 13OK, 12fail = 52.0% SR, avg_dur=12,694ms
- dsv4p_nv: 19req, 8OK, 11fail = 42.1% SR, avg_dur=48,520ms

### 6h 按上游
- nv_integrate: 25req, 13OK, 12fail, avg_dur=12,694ms
- nvcf_pexec: 10req, 6OK, 4fail, avg_dur=46,089ms
- NULL (ATE): 9req, 2OK, 7fail, avg_dur=51,222ms

### 6h 每小时 SR
- 11:00: 6/2/4=33.3%
- 12:00: 7/3/4=42.9%
- 13:00: 9/5/4=55.6%
- 14:00: 7/3/4=42.9%
- 15:00: 6/2/4=33.3%
- 16:00: 9/6/3=66.7%

### dsv4p_nv ATE 详情
- 7× all_tiers_exhausted (avg 63,741ms), fallback_actually_attempted=false
- 4× zombie_empty_completion (avg 43,191ms, input_chars ~219K)
- tiers_tried_count=1 for ALL 23 failures

### ms_gw 信号
- 21req total, 18OK = 85.7% SR
- dsv4p_ms (DEEPSEEK-AI/DEEPSEEK-V4-PRO): 7/7 100% SR (recovered from R1474 6/6 TimeoutError)
- glm5_2_ms (ZHIPUAI/GLM-5.2): 11/11 100% SR

### tier_attempts
- 0 rows (no key cycling)

### 日志分析
- `tier_chain=['glm5_2_nv'] (no fallback, 3model)` — FALLBACK_GRAPH {} expected
- `tier_chain=['dsv4p_nv'] (no fallback, 3model)` — FALLBACK_GRAPH {} expected
- `NV-ALL-TIERS-FAIL` + `ABORT-NO-FALLBACK` — ms_gw fallback NOT triggered
- `NV-MS-FB`: 0 occurrences — MODELMAP missing dsv4p_nv → ms_gw never invoked
- `NV-ZOMBIE-EMPTY`: 6 occurrences (code-level zombie detection, not config-fixable)

## 决策

dsv4p_nv 有 7× all_tiers_exhausted ATE，但 ms_gw fallback 从未触发（MODELMAP 缺少 dsv4p_nv）。ms_gw dsv4p_ms 当前窗口 7/7 100% SR，已从 R1474 的 TimeoutError 恢复。重新加回 dsv4p_nv:dsv4p_ms 到 MODELMAP 可救援这些 ATE。

BUDGET=205, UPSTREAM=66: ms_gw fallback budget = 205-66 = 139s，安全。

## 参数变更

| 参数 | 旧值 | 新值 | 理由 |
|------|------|------|------|
| NVU_MS_GW_FALLBACK_MODELMAP | `glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms` | `glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms,dsv4p_nv:dsv4p_ms` | ms_gw dsv4p_ms 7/7 100%SR 已恢复；BUDGET 205-66=139s safe |

## 验证
- ✅ YAML parse OK
- ✅ docker compose up -d OK
- ✅ docker exec env confirms MODELMAP includes dsv4p_nv:dsv4p_ms
- ✅ /health OK

## 铁律
只改HM1不改HM2

## ⏳ 轮到HM1优化HM2
