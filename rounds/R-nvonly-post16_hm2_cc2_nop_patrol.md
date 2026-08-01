# R-nvonly-post16 — NOP 巡检轮 (cc2 0 流量, 回滚后链路健康)

**日期**: 2026-08-02 01:55 CST
**轮次**: R-nvonly-post16 (hm2_cc2)
**类型**: NOP 巡检轮 (无改动, 无重启)

## 接棒
- 上轮 post15: 应急回滚 cc4101 `PRIMARY_UPSTREAM_MODEL: dsv4p_nv → glm5_2_nv`
  (dsv4p_nv NVCF 429 风暴无 retry-after, buffer 5 attempts 全 fail, cc2 SR 34%)
- 本轮轮前数据: 30min cc4101-primary 窗口 **0 req** (cc2 session 间隙无流量)

## 本轮数据 (30min, 轮前注入)

### cc4101-primary (cc2) 专属
| status | count |
|--------|-------|
| (空)   | 0     |

cc2 本轮 30min 无请求产生 → 无 SR 可判, 但**也无任何错误**.

### 其他 caller (hermes, 非 cc2 流量)
| caller | model | status | count |
|--------|-------|--------|-------|
| hermes | dsv4p_nv | 200 | 7 |
| hermes | dsv4p_nv | 429 | 4 |

hermes caller 仍打 dsv4p_nv, SR=63.6% (4×429 all_tiers_exhausted).
这是 NVCF 侧 dsv4p_nv 限流持续, **与 cc2 无关** (cc2 已切 glm5_2_nv).

### buffer/wait 日志
无 buffer/wait/keymanager 日志触发 (无 cc2 流量).

## 判稳三阈值
| 阈值 | 30min 实测 | 判定 |
|------|-----------|------|
| cc2 (cc4101-primary) SR | 0 req (无数据) | ⚠️ 无流量, 但端到端探测 200 ✓ |
| cc4101 真 fallback | 0 (DISABLE_MS_FALLBACK=1, FALLBACK_URL=none) | ✅ 破釜沉舟持续 |
| 新错误类型 | 无 (cc2 无请求, 无错误产生) | ✅ |
| transport 层 | 无 cc2 流量, 无 transport 错误 | ✅ |
| buffer 触发 | 无 (无流量) | ✅ |
→ **NOP 巡检轮**, 不改码, 不重启.

## 回滚生效验证 (post15 改动确认持续)
| 验证项 | 结果 |
|--------|------|
| cc4101 `PRIMARY_UPSTREAM_MODEL` | `glm5_2_nv` ✓ (回滚生效) |
| cc4101 `FALLBACK_UPSTREAM_URL` | `none` ✓ (破釜沉舟持续) |
| nv_gw `/health` | `nv_default_model: glm5_2_nv`, 5 keys ✓ |
| 端到端探测 (cc4101→nv_gw→glm5_2_nv) | 200 `model:glm5_2_nv` "Pong! 🏓" ✓ |
| docker ps | cc4101 Up 6h, nv_gw Up 3h, logs_db Up 2d ✓ |

## 结论
post15 应急回滚 (dsv4p_nv → glm5_2_nv) 持续生效. cc2 本轮 30min 无流量产生
(session 间隙), 无法用 SR 判稳, 但:
1. 端到端探测 200 证明 glm5_2_nv 健康 tier 可达
2. 无任何 cc2 错误 (无请求 = 无错误)
3. fallback=0 持续, 破釜沉舟架构不变
4. hermes caller 的 dsv4p_nv 429 是已知 NVCF 限流, 非 cc2 链路问题

## cc2 SR 走势
| 轮次 | cc2 SR | 错误 | 趋势 |
|------|--------|------|------|
| post9 | 40/40=100% | 0 | 满分 (glm5_2_nv) 🎉 |
| post11 | 36/36=100% | 0 | 满分 (glm5_2_nv) 🎉 |
| post12 | 40/40=100% | 0 | 满分连庄 (glm5_2_nv) 🎉🎉 |
| post15 | 10/29=34% | 19×502 | ❌ dsv4p_nv 429 风暴 → 切回 glm5_2_nv |
| **post16** | **0 req** | **0** | NOP (回滚后健康, 无流量) |

## 参数快照 (未改, 同 post15)
- cc4101: `PRIMARY_UPSTREAM_MODEL=glm5_2_nv`, `PRIMARY_UPSTREAM_URL=http://nv_gw:40006/v1/messages`,
  `FALLBACK_UPSTREAM_URL=none`, `CC4101_STREAM_TOTAL_DEADLINE_S=470`, `PRIMARY_HEADER_TIMEOUT=400`
- nv_gw: `NVU_DISABLE_MS_FALLBACK=1`, 5key(k0-k4)×5美国IP, `NVU_BUFFER_MAX_RETRIES=5`,
  `NVU_BUFFER_TIMEOUT_STAIRS=90,90,90,90,90`, `NVU_BUFFER_TOTAL_DEADLINE_S=450`

## 下一步
- 等下个有 cc2 流量的 30min 窗口: 确认 cc2 SR 回到 ≥99% (glm5_2_nv 健康 tier)
- 若 cc2 有流量且 SR<99% → 找根因, 小步改
- 若 cc2 有流量且 SR=100% (如 post9-12) → 确认回滚成功, 回 NOP 节奏
- dsv4p_nv 429 风暴: 持续监控, 但 cc2 已不走此 tier, 非 cc2 优化目标
