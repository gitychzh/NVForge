# R989 — cc2 NOP 巡检轮 (不改码)

> 日期: 2026-08-07
> 结果: **NOP** — cc2 主链路连续第 **97** 轮 (R893-R989) 100% 干净
> 判定: cc4101-primary = **121/121 = 100% SR, 0 bad**; 唯一 bad 全属 hermes 越界; fallback 0

## 结论一句话

cc2 主链 (nv_gw:40006 → dsv4f0731_nv) 在 30min 窗口 121/121 全 200, 主链专属错误 **0 rows**, fallback 0 次;
唯一 5 个 bad (all_tiers_exhausted ×4 + zombie_empty_completion ×1) 100% 属 caller=hermes + 已知坏 fid 52e1ddb6
(宿主越界容器), 与主链 host 分离。**不改码, NOP 巡检。**

## 本轮数据 (live 复核 2026-08-07 + 注入轮前链路分析)

| 指标 | 值 | 状态 |
|---|---|---|
| cc4101-primary (主 nv_gw:40006) | **121/121 = 100% SR, 0 bad** (live re-pull) | ✅ |
| 主链专属错误 (caller=cc4101-primary) | **0 rows** | ✅ |
| 唯一 bad (非 200) | 5 条, 全 caller=hermes 线 (fid 52e1ddb6) | ⚠️ 越界 |
| bad caller 归属 | 100% hermes; cc2 primary 0 条 | ✅ 隔离 |
| fallback (cc_requests 30min) | 0 次 (1912 req 全未 fb) | ✅ |
| cc_requests 真实 SR | 99.2% (1897/1912) — 全部 15 bad 属 hermes | ✅ |
| tier 瞬态错误 (nv_tier_attempts) | RemoteDisconnected / Timeout / empty_200, 全被吸收 | ✅ |
| 容器 | nv_gw Up, cc4101 Up, health 全 200 | ✅ |

### nv_tier_attempts per-key (30min)
各 key pexec_success 主导 (k0=25, k1=23, k2=25, k3=25, k4=23), 瞬态
NVCFPexecRemoteDisconnected (2-5/key) / NVCFPexecTimeout / empty_200 散落, 全被多 key round-robin +
func_health + buffer 吸收, 无泄漏为 200 以外。

### buffer/wait 日志 (nv_gw live, 最后近 30min)
绝大多数 cc2 primary 请求 attempt=1 一次成功, `verdict=success_tool_call`, elapsed 8-9s, flushed 给 CC
(7505b-18527b, do=1128)。无 attempt>1 重试, 无 502 泄漏。瞬态键错误在 attempt 层即被吸收。

## 依据 (注入轮前链路分析 + live 复核)

- 30min nv_requests cc4101-primary = **121/121 全 200** (live re-pull)。
- bad 分组 (by caller×err_type×fid): `hermes | all_tiers_exhausted | 52e1ddb6 | 502 | 4` +
  `hermes | zombie_empty_completion | 52e1ddb6 | 502 | 1` — 全 hermes 线 + 已知坏 fid。
- cc_requests 30min: total 1912, fb=0, SR 99.2% (1897/1912; 15 bad 全属 hermes 非 cc2 主链)。
- health: 40006/4101 全 200; nv_gw / cc4101 皆 Up。

## 关键判断

1. 主链 SR 100% + 专属错误 0 rows → 无 cc2 优化需求。
2. 唯一 5 bad 全属 hermes 线 (fid 52e1ddb6), R897 起持续 host 隔离, non cc2 范围。
3. 多 key round-robin (dsv4f0731_nv 为首) + func_health + buffer 已达稳态, 瞬态错误全被吸收, 无参数可调。
4. fallback 0 次, ms_gw fallback 保持不禁用 (NVU_DISABLE_MS_FALLBACK=0)。

## 下一步

- 保持 NOP 观察, 主链 dsv4f0731_nv 为首代, 无需参数改动。
- 继续监控 hermes bad (fid 52e1ddb6) host 隔离是否持续 (R897 起从未泄漏进 cc2 主链)。

## 容器健康 / 参数快照

- nv_gw Up (11h), cc4101 Up (11h), /health 40006+4101 全 200。
- nv_gw: nv_default_model=glm5_2_nv, NVU_DISABLE_MS_FALLBACK=0, NVU_BUFFER_MAX_RETRIES=5,
  NVU_BUFFER_CALLERS=cc4101-primary,openclaw2, KeyManager 429 120s-600s 退避。
- cc4101: PRIMARY_UPSTREAM_MODEL=dsv4f0731_nv, PRIMARY_UPSTREAM_URL=http://nv_gw:40006/v1/messages,
  CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400, FALLBACK_UPSTREAM_URL=ms_gw:40007。
- 修复链沿用 R827-R837 + R869/R876/R891 + R987/R988。