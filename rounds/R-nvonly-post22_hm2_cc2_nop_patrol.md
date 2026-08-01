# R-nvonly-post22 — hm2 cc2 NOP 巡检轮

**时间**: 2026-08-02 02:18 CST
**方向**: R-nvonly (nv_gw 自优化)
**轮型**: NOP 巡检轮 (0 改动, 0 重启)

## 本轮判稳依据 (30min 窗口)

### cc2 (cc4101-primary) — 3 req, SR 100%
| status | count | avg_dur_ms |
|--------|-------|------------|
| 200    | 3     | 57666      |

- 2 req glm5_2_nv 直接成功
- 1 req fallback 到 glm5_2_ms (ms_gw 兜底, 符合 "fallback 已恢复" 指令)
- 无 transport 错误, 无 buffer 触发

### tier 错误 (30min)
| key | error_type | count |
|-----|-----------|-------|
| 2   | 429_nv_rate_limit | 1 |

仅 1× dsv4p_nv 429, 无 RemoteDisconnected/SSL EOF. R-nvonly 短惩罚分类持续生效.

### 其他 caller (非 cc2 流量)
- dsv4p_nv SR=69.0% (20/29): hermes/openclaw/other caller 打, 9× all_tiers_exhausted + 5×429 + 2×502
- NVCF 侧 dsv4p_nv 限流持续, 与 cc2 无关

## 三阈值判稳
| 阈值 | 实测 | 判定 |
|------|------|------|
| cc2 SR | 3/3 = 100% | ✅ |
| 新错误类型 | 无 | ✅ |
| transport 层 | 0 错误 | ✅ |
| buffer 触发 | 无 | ✅ |
→ **NOP 巡检轮**, 不改码, 不重启.

## 健康验证
- `/health`: `nv_default_model: glm5_2_nv`, `nv_num_keys: 5` ✓
- docker ps: cc4101 Up 16m, nv_gw Up 16m, nv_gw_stable Up 19m, ms_gw Up 2d, logs_db Up 2d ✓

## 配置实测 (与 prompt 指令一致)
- nv_gw `NVU_DISABLE_MS_FALLBACK=0` (ms_gw fallback 已恢复)
- cc4101 `FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/chat/completions` (fallback 已恢复)
- cc4101 `PRIMARY_UPSTREAM_MODEL=glm5_2_nv` (post15 回滚持续生效)

## cc2 SR 走势
post17→18→19→20→21→**22** 连续满分 (6 连庄).

## 结论
cc2 链路 (glm5_2_nv) 健康, post15 回滚 (切回 glm5_2_nv + 恢复 ms_gw fallback) 持续生效.
本轮 0 改动 0 重启, 维持稳态. dsv4p_nv 429 风暴为 NVCF 侧限流, 非 cc2 优化目标.
