# R-nvonly-post74 — hm2 cc2 NOP 巡检轮 (2026-08-02)

## 轮号
- R-nvonly-post74 (hm2_cc2)
- 时间: 2026-08-02 05:10 CST
- 类型: NOP 巡检轮

## 轮前链路分析 (注入数据)
- 上轮: R-nvonly-post73
- 容器: nv_gw / cc4101 / nv_gw_stable 均 Up 3 hours ago

### 30min 链路总览 (caller × model × status)
| caller | model | status | count |
|--------|-------|--------|-------|
| hermes | dsv4p_nv | 200 | 8 |
| hermes | dsv4p_nv | 429 | 5 |
| openclaw | dsv4p_nv | 502 | 2 |

### 30min 按模型成功率
- dsv4p_nv SR=53.3% (8/15)

### 30min cc4101-primary 专属 (cc2 的请求)
- **0 req** (session 轮前无流量产生, 无数据可判 cc2 SR)

### 30min 错误分类
| error_type | sub | count | avg_dur |
|------------|-----|-------|---------|
| all_tiers_exhausted | all_tiers_failed_in_mapped_tier | 5 | 1103ms |
| zombie_empty_completion | (空) | 2 | 5281ms |

### 30min per-key × status (dsv4p)
- key2: 8×200 (avg_dur=14835ms)
- key3: 2×502
- key?: 5×429

### 30min per-egress-IP (dsv4p)
- 203.10.96.139: 8×100%
- (空IP): 5×0%
- 134.195.101.194: 2×0%

### 30min fallback 发生率
- f=15 (dsv4p_nv 全部 fallback, 因 5key 全挂触发)

## 判稳分析
| 阈值 | 30min 实测 | 判定 |
|------|-----------|------|
| cc2 (cc4101-primary) SR | 0 req (无流量) | — (无数据, 链路健康无故障) |
| 新错误类型 | 无 (0 cc2 tier error) | ✅ |
| transport 层 | 0 错误 (无 cc2 流量) | ✅ |
| buffer 触发 | 无 (cc2 0 req) | ✅ |
| stream_total_deadline (6h) | 0 次 | ✅ |

→ **NOP 巡检轮**, 不改码, 不重启.

### 关于 dsv4p_nv SR=53.3% 的说明
- dsv4p_nv 是 hermes caller 打的, **非 cc2 链路** (cc2 走 glm5_2_nv, 不打 dsv4p_nv).
- 5×all_tiers_exhausted + 5×429 = NVCF 侧 dsv4p 限流 (单 key/key2 9×200 vs key? 5×429).
- egress IP: 203.10.96.139=8×100%, 其余 IP=0% (egress IP 漂移, 单 IP 限流).
- 与 cc2 链路无关, 不在本轮优化范围 (只聚焦 40006 glm5_2_nv 链路).

## 健康验证 (05:10 CST)
| 验证项 | 结果 |
|--------|------|
| nv_gw `/health` | status=ok, nv_default_model=glm5_2_nv, nv_num_keys=5, pexec=[kimi_nv,dsv4p_nv,glm5_2_nv] ✓ |
| docker ps | nv_gw/cc4101/nv_gw_stable Up 3h ✓ |
| buffer/wait 日志 | 0 行 (cc2 0 req 无触发) ✓ |
| stream_total_deadline (6h) | 0 次 ✓ |
| 配置 (注入实测) | NVU_DISABLE_MS_FALLBACK=0 (fallback 已恢复), FALLBACK_UPSTREAM=ms_gw:40007 ✓ |

## 本轮改动
- 0 改动, 0 重启, 0 code change.

## 下一步
- 继续 NOP 巡检. 等 cc2 自身请求产生流量后再判 SR.
- 关注 dsv4p_nv 限流是否扩散影响 (目前仅 hermes caller, cc2 走 glm5_2_nv 不受影响).

## 参数快照
| 参数 | 值 |
|------|-----|
| nv_gw.UPSTREAM_TIMEOUT | 90 |
| nv_gw.TIER_COOLDOWN_S | 180 |
| nv_gw.KEY_COOLDOWN_S | 30 |
| nv_gw.NVU_DISABLE_MS_FALLBACK | 0 (fallback 已恢复) |
| nv_gw.NVU_BUFFER_CALLERS | cc4101-primary,openclaw2 |
| nv_gw.NVU_PEER_FB_SKIP_MODELS | glm5_2_nv,dsv4p_nv |
| cc4101.CC4101_STREAM_TOTAL_DEADLINE_S | 470 |
| cc4101.PRIMARY_HEADER_TIMEOUT | 400 |
| cc4101.FALLBACK_UPSTREAM_URL | ms_gw:40007 |
| cc4101.PRIMARY_UPSTREAM_MODEL | glm5_2_nv |
