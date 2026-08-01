# R-nvonly-post18 — NOP 巡检轮 (2026-08-02 01:57 CST)

## 轮前数据 (30min 窗口, 轮前链路分析注入)

### cc2 (cc4101-primary) 专属 — 本轮 1 req
| status | count | avg_dur_ms |
|--------|-------|------------|
| 200    | 1     | 1639       |

**cc2 SR = 1/1 = 100%** ✅ (glm5_2_nv 健康 tier, 对标 post9-12/post17)

### 其他 caller (hermes, 非 cc2 流量)
| caller | model | status | count |
|--------|-------|--------|-------|
| hermes | dsv4p_nv | 200 | 7 |
| hermes | dsv4p_nv | 429 | 4 |

hermes 仍打 dsv4p_nv, SR=63.6% (4×429 all_tiers_exhausted) — NVCF 侧 dsv4p_nv 限流持续,
**与 cc2 链路无关** (cc2 已切 glm5_2_nv, post15 回滚持续生效).

### 错误分类 (30min, status!=200)
| error_type | sub | count | avg_dur_ms |
|------------|-----|-------|------------|
| all_tiers_exhausted | all_tiers_failed_in_mapped_tier | 4 | 1574 |

→ 4×429 全部来自 hermes→dsv4p_nv, 非 cc2 流量.

### buffer / wait 日志
无 buffer/wait/keymanager 日志 (cc2 1 req 直接成功, 无重试).

## 判稳
| 阈值 | 30min 实测 | 判定 |
|------|-----------|------|
| cc2 (cc4101-primary) SR | 1/1 = 100% | ✅ glm5_2_nv 健康 tier |
| cc4101 真 fallback | 0 (DISABLE_MS_FALLBACK=1) | ✅ 破釜沉舟持续 |
| 新错误类型 | 无 | ✅ |
| transport 层 | 0 错误 | ✅ |
| buffer 触发 | 无 (1 req 直接成功) | ✅ |
→ **NOP 巡检轮**, 不改码, 不重启.

## 健康/容器验证
- `/health`: `nv_default_model: glm5_2_nv`, 5 keys, 3 models ✓
- docker ps: cc4101 Up 7h, nv_gw Up 3h, logs_db Up 2d ✓

## cc2 SR 走势
| 轮次 | cc2 SR | 错误 | 趋势 |
|------|--------|------|------|
| post9  | 40/40=100% | 0 | 满分 (glm5_2_nv) 🎉 |
| post11 | 36/36=100% | 0 | 满分 (glm5_2_nv) 🎉 |
| post12 | 40/40=100% | 0 | 满分连庄 (glm5_2_nv) 🎉🎉 |
| post15 | 10/29=34% | 19×502 | ❌ dsv4p_nv 429 风暴 → 切回 glm5_2_nv |
| post16 | 0 req | 0 | NOP (回滚后健康, 无流量) |
| post17 | 1/1=100% | 0 | ✅ glm5_2_nv 健康, 有流量窗口恢复满分 |
| **post18** | **1/1=100%** | **0** | ✅ 连续满分 (glm5_2_nv) |

## 本轮改动
0 改动, 0 重启. NOP 巡检轮.

## 下一步
- 等下个有 cc2 流量的 30min 窗口: 期望 SR 持续 100% (glm5_2_nv 健康 tier)
- 若 cc2 SR<99% → 找根因, 小步改
- dsv4p_nv 429 风暴 (hermes caller): 持续监控, 非 cc2 优化目标
