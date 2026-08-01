# R-nvonly-post17 — NOP 巡检轮 (2026-08-02 01:54 CST)

## 轮前数据 (30min 窗口, 轮前链路分析注入)

### cc2 (cc4101-primary) 专属 — 本轮有 1 req
| status | count | avg_dur_ms |
|--------|-------|------------|
| 200    | 1     | 1639       |

**cc2 SR = 1/1 = 100%** ✅ (glm5_2_nv)

### 其他 caller (hermes, 非 cc2 流量)
| caller | model | status | count |
|--------|-------|--------|-------|
| hermes | dsv4p_nv | 200 | 7 |
| hermes | dsv4p_nv | 429 | 4 |

hermes 仍打 dsv4p_nv, SR=63.6% (4×429 all_tiers_exhausted) — NVCF 侧 dsv4p_nv 限流持续,
**与 cc2 链路无关** (cc2 已切 glm5_2_nv).

### 错误分类
| error_type | sub_type | count | avg_dur_ms |
|------------|----------|-------|------------|
| all_tiers_exhausted | all_tiers_failed_in_mapped_tier | 4 | 1695 |

4 次全挂均来自 hermes→dsv4p_nv, 不是 cc2 流量.

### buffer / wait / keymanager 日志
无 buffer/wait/keymanager 日志触发 (cc2 链路 1 req 直接成功, 无全挂).

## 判稳 + 行动

| 阈值 | 30min 实测 | 判定 |
|------|-----------|------|
| cc2 (cc4101-primary) SR | 1/1 = 100% | ✅ glm5_2_nv 健康 tier |
| cc4101 真 fallback | 0 (NVU_DISABLE_MS_FALLBACK=1) | ✅ 破釜沉舟持续 |
| 新错误类型 (cc2 链路) | 无 | ✅ |
| transport 层 (RemoteDisconnected/SSL) | 0 | ✅ |
| buffer 触发 | 无 (无全挂) | ✅ |
| /health primary | glm5_2_nv ✓, 5 keys ✓ | ✅ |
| docker ps | cc4101 Up 7h, nv_gw Up 3h, logs_db Up 2d | ✅ |

→ **SR=100%, 无新错误, 无 fallback → NOP 巡检轮**, 不改码, 不重启.

## 本轮改动
- 0 改动
- 0 重启

## cc2 SR 走势
| 轮次 | cc2 SR | 错误 | 趋势 |
|------|--------|------|------|
| post9  | 40/40=100% | 0 | 满分 (glm5_2_nv) 🎉 |
| post11 | 36/36=100% | 0 | 满分 (glm5_2_nv) 🎉 |
| post12 | 40/40=100% | 0 | 满分连庄 (glm5_2_nv) 🎉🎉 |
| post15 | 10/29=34% | 19×502 | ❌ dsv4p_nv 429 风暴 → 切回 glm5_2_nv |
| post16 | 0 req | 0 | NOP (回滚后健康, 无流量) |
| **post17** | **1/1=100%** | **0** | ✅ glm5_2_nv 健康, 有流量窗口已恢复满分 |

post15 回滚 (dsv4p_nv→glm5_2_nv) 持续生效, 本轮 cc2 终于有 1 个请求窗口且 200 成功,
**确认回滚成功, cc2 链路回到 glm5_2_nv 健康 tier**.

## 参数快照 (未改, 同 post15/post16)
- cc4101: `PRIMARY_UPSTREAM_MODEL=glm5_2_nv`, `PRIMARY_UPSTREAM_URL=http://nv_gw:40006/v1/messages`,
  `FALLBACK_UPSTREAM_URL=none`, `FALLBACK_UPSTREAM_MODEL=glm5_2_ms`,
  `CC4101_STREAM_TOTAL_DEADLINE_S=470`, `PRIMARY_HEADER_TIMEOUT=400`, `UPSTREAM_TIMEOUT=130`
- nv_gw: `NVU_DISABLE_MS_FALLBACK=1`, 5key(k0-k4)×5美国IP(hysteria2),
  `NVU_BUFFER_MAX_RETRIES=5`, `NVU_BUFFER_TIMEOUT_STAIRS=90,90,90,90,90`, `NVU_BUFFER_TOTAL_DEADLINE_S=450`,
  `NV_INTEGRATE_MODELS=glm5_2_nv`, `NVU_KEYMGR_429_MAX_COOLDOWN=600`
- config.py: `DEFAULT_NV_MODEL=glm5_2_nv` (L224, 未改)

## 下一步
- 等下个有 cc2 流量的 30min 窗口: 期望 SR 持续 100% (glm5_2_nv 健康 tier, 对标 post9-12)
- 若 cc2 SR<99% → 找根因, 小步改
- dsv4p_nv 429 风暴 (hermes caller): 持续监控, 非 cc2 优化目标
