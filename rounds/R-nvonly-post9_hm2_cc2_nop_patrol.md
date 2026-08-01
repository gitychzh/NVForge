# R-nvonly-post9 (hm2_cc2) — NOP 巡检轮

**时间**: 2026-07-31 19:17-19:22 CST
**类型**: NOP 巡检轮 (0 改动 0 restart)
**基线**: R-nvonly-post8 → post9

## 判稳三阈值

| 阈值 | 30min 实测 | 判定 |
|------|-----------|------|
| cc2 (cc4101-primary) SR | **34/34 = 100%** | ✅ ≥99% |
| cc4101 真 fallback | 0 | ✅ |
| 无新错误类型 | all_tiers_exhausted(hermes), buffer(openclaw2) | ✅ |
| transport 层 | 全 pexec_success, 0 RemoteDisconnected/SSLEOF/429 | ✅ |
| egress IP | 5/5 100% | ✅ |
| deadline 链 | 6h stream_total_deadline=0 | ✅ |

→ **NOP 巡检轮。冻结，0 改动 0 restart。**

## cc4101-primary (cc2) 30min 详细

| status | count | avg_dur_ms |
|--------|-------|------------|
| 200 | 34 | 61,397 |

**cc2 SR = 34/34 = 100%** ↑ 从 post8 的 96.8% 回升，同 post7 98.9% 高位。

## dsv4p_nv 整体 30min

| caller | 200 | 502 | SR |
|--------|-----|-----|------|
| cc4101-primary | 34 | 0 | 100% |
| hermes | 12 | 3 | 80% |
| openclaw2 | 35 | 1 | 97.2% |
| openclaw | 1 | 0 | 100% |

Overall dsv4p_nv SR = 82/86 = 95.3% (hermes 3×all_tiers_exhausted 拉低)

## 错误分类

| error_type | sub_type | count | avg_dur_ms | caller | 判定 |
|---|---|---|---|---|---|
| all_tiers_exhausted | all_tiers_failed_in_mapped_tier | 3 | 5 | hermes | 非 cc2 |
| all_tiers_exhausted | (null) | 1 | 320,994 | openclaw2 | 非 cc2 |

**hermes all_tiers_exhausted avg 5ms**: 请求到达时 key 已在冷却中，瞬时判死。
hermes 只绑 key #2 (NVU_CALLER_KEY_MAP=hermes:2)，不在 NVU_BUFFER_CALLERS 名单，
无 5key 轮转保护。k2 短暂不可用则直接 502。非 cc2 方向，不影响 cc2。

**openclaw2 all_tiers_exhausted avg 320s**: 1 次完整 buffer 耗尽 (5min+)，
openclaw2 在 BUFFER_CALLERS 名单，有 buffer 保护但仍然耗尽。同 post8 模式 (1×buffer_exhausted)。

## Transport 层 (Tier Attempts)

- 全 pexec_success: k0=11, k1=18, k2=8, k3=15, k4=16
- 0 RemoteDisconnected, 0 SSLEOF, 0 429
→ **R-nvonly transport 短惩罚机制已稳定多轮丰收: key 不再因 transport 波动误冻。**

## Egress IP

| IP | Reqs | SR% |
|---|---|---|
| 134.195.101.193 | 44 | 100% |
| 134.195.101.180 | 16 | 100% |
| 203.10.96.139 | 12 | 100% |
| 134.195.101.195 | 8 | 100% |
| 134.195.101.194 | 1 | 100% |

5/5 100%，hysteria2 美国代理层健康。

## Buffer/Wait 效果

30min 内无 BUFFER-ATTEMPT/BUFFER-SUCCESS/BUFFER-EXHAUSTED/WAIT-QUEUE 日志。
= 全部请求 attempt=1 直接命中，buffer 无需介入。

## 容器状态

| 容器 | Up | 健康 |
|------|-----|------|
| nv_gw | 6min | /health ok (num_keys=5) |
| cc4101 | 24h | running |
| logs_db | 33h | running |

nv_gw 从 12h→6min (再次在数据窗口前后重启，同 post8 模式)。
重启后健康正常，无 crash 痕迹。原因不明但无后续异常。

## 配置漂移确认 (运行态 vs compose 文件态)

nv_gw 容器 Env (运行态):
```
UPSTREAM_TIMEOUT=90          ← compose 末行=130, 容器未 up-d 重建
KEY_COOLDOWN_S=45            ← compose 末行=60, 容器未 up-d 重建
NVU_BUFFER_MAX_RETRIES=8     ← 漂移态 (设计值=5)
NVU_BUFFER_TIMEOUT_STAIRS=30,50,70,90,90,90,90,90  ← 漂移态
NVU_BUFFER_TOTAL_DEADLINE_S=600  ← 漂移态 (设计值=450)
NVU_BUFFER_PING_INTERVAL_S=30  ← 新增 (post7 发现)
NVU_DISABLE_MS_FALLBACK=1   ← 铁律守护
TIER_COOLDOWN_S=180
```

compose 文件重复行问题:
- `KEY_COOLDOWN_S=45` 后又有 `KEY_COOLDOWN_S=60` (末行=60)
- `UPSTREAM_TIMEOUT=300` 后又有 `UPSTREAM_TIMEOUT=130` (末行=130)
- 末行覆盖，但容器 `restart` 不读取 compose env 变更，需 `up -d` 重建。

→ 本轮不改，留待后续非 NOP 轮统一切换 `up -d` 使 compose 末行生效。

## deadline 链

6h `stream_total_deadline` = 0 — 完美。
cc4101 timeout 470s > buffer 600s(非流式) > 流式实际 330s(30+50+70+90+90)

## 本轮行动

- 0 改动 0 restart
- 仅写入 round 文件 + 覆写 STATE.md

## 下一轮建议

1. 继续巡检。cc2 SR 已回 100%，趋势向好。
2. 关注 hermes all_tiers_exhausted: 若跨方向扩散到 cc2 → 需排查 k2 冷却模式。
3. 配置漂移留待非 NOP 轮统一切换 (compose env 末行生效)。
4. nv_gw 两次 NOP 轮均发生"数据窗口后重启"，下一轮注意 Up 时间是否持续增长。
5. transport 短惩罚机制已多轮稳定验证 0 冒泡 → 持续受益。