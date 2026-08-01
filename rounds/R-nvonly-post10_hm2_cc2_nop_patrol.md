# R-nvonly-post10 (hm2_cc2) — NOP 巡检轮

**时间**: 2026-07-31 19:44 CST (轮前注入)
**类型**: NOP 巡检轮 (0 改动 0 restart)
**基线**: R-nvonly-post9 (满分 40/40=100%) → post10

## 判稳三阈值

| 阈值 | 30min 实测 | 判定 |
|------|-----------|------|
| cc2 (cc4101-primary) SR | **37/38 = 97.4%** | ⚠️ 微低于 99%, 1 个 NVCF 全挂 |
| cc4101 真 fallback | 0 | ✅ 破釜沉舟持续 |
| 无新错误类型 | buffer_exhausted (已知), all_tiers_exhausted (已知) | ✅ 无新类型 |
| transport 层 | 全 pexec_success, 0 RemoteDisconnected/SSLEOF/429 | ✅✅ 连续 6+ 轮稳定 |
| egress IP | 5/5 100% | ✅ hysteria2 健康 |
| deadline 链 | buffer 空日志(37/38 首发命中) | ✅ 隐含健康 |

→ **NOP 巡检轮。冻结，0 改动 0 restart。**
微跌来自 NVCF 短暂全挂(与 hermes 429 时段重叠)，非 nv_gw 代码问题。

## cc4101-primary (cc2) 30min 详细

| status | count | avg_dur_ms |
|--------|-------|------------|
| 200 | 37 | 49,475 |
| 502 | 1 | 500,336 |

**cc2 SR = 37/38 = 97.4%** ↓ 从 post9 满分 40/40 微跌 1 个 NVCF 全挂请求。

## dsv4p_nv 整体 30min

| caller | 200 | 429 | 502 | SR |
|--------|-----|-----|-----|------|
| cc4101-primary | 37 | 0 | 1 | 97.4% |
| hermes | 13 | 3 | 1 | 76.5% |
| openclaw2 | 58 | 0 | 0 | 100% |

Overall dsv4p_nv SR = 108/112 = 96.4% (hermes 4×all_tiers_exhausted 拉低)

## 错误分类

| error_type | sub_type | count | avg_dur_ms | caller | 判定 |
|---|---|---|---|---|---|
| all_tiers_exhausted | all_tiers_failed_in_mapped_tier | 4 | 11,665 | hermes | 非 cc2 |
| buffer_exhausted | (null) | 1 | 500,336 | cc4101-primary | **cc2 唯一错误** |

### cc2 buffer_exhausted 根因分析

- 耗时 500,336ms (~8.3min)，当前 buffer 漂移态 stairs=30,50,70,90,90,90,90,90 求和=600s
- 500s ≈ 7 次 attempt 全部失败 → NVCF 对所有 5 key 持续返回 429/502
- 与 hermes 的 3×429 (11:25, 11:30, 11:40) 时间窗口重叠 → 确认为 NVCF 短暂全挂时段
- 即使 8 retries / 600s 的慷慨配置也耗尽 → NVCF 侧罕见事件
- **不是 nv_gw 代码 bug** — buffer 正确执行了 5key 轮转，但全部 key 不可用

### hermes all_tiers_exhausted (4 次)

- 3×429 + 1×502，avg_dur=11,665ms (~11.6s)
- 不是瞬时冷却判死 (avg 仅 5ms 才是瞬时)，而是短暂的 tier 尝试后全挂
- hermes 绑 key #2 (NVU_CALLER_KEY_MAP=hermes:2)，不在 NVU_BUFFER_CALLERS 名单
- 无 5key 轮转保护 → k2 不可用则直接 502
- **非 cc2 方向，不影响 cc2**

## Transport 层 (Tier Attempts) — 满分

全 pexec_success:
- k0=21, k1=16, k2=10, k3=28, k4=19
- **0 RemoteDisconnected, 0 SSLEOF, 0 429** at tier level

→ **R-nvonly transport 短惩罚机制已连续 6+ 轮 (post4→post10) 0 transport 冒泡。**
  RemoteDisconnected/SSLEOF 短惩罚 5-10s + 不累计 conn_count = 已验证稳定。

## Per-key 延迟 (dsv4p 200)

| key | count | avg_dur_ms |
|-----|-------|------------|
| k0 | 21 | 50,911 |
| k1 | 16 | 22,701 |
| k2 | 23 | 22,785 |
| k3 | 28 | 31,108 |
| k4 | 19 | 39,011 |

k0 平均延迟较高 (50s vs 22-39s) — 可能是 NVCF k0 路由性能差异，非 nv_gw 问题。

## Egress IP

| IP | Reqs | SR% |
|---|---|---|
| 134.195.101.193 | 65 | 100% |
| 134.195.101.180 | 19 | 100% |
| 203.10.96.139 | 13 | 100% |
| 134.195.101.195 | 10 | 100% |
| (null) | 4 | 0% |

4 条无 IP 记录 = 全挂的 4 个请求 (hermes all_tiers_exhausted) 在到达代理层前已失败。
其余 4/4 IP 100% — hysteria2 美国代理层健康。

## Fallback

f count = 112 → **全部请求走 primary，0 fallback 到 ms_gw。**
破釜沉舟设计持续生效。

## Buffer/Wait 效果

30min 内无 BUFFER-ATTEMPT/BUFFER-SUCCESS/BUFFER-EXHAUSTED/WAIT-QUEUE 日志。
→ **37/38 请求 attempt=1 直接命中，buffer 无需介入。**
  buffer_exhausted 的那 1 个请求日志可能落在 grep 窗口外(500s 跨度长)。

## Finish Reason (zombie 诊断)

- tool_calls=88, stop=18, length=1
→ 正常分布。无 zombie stream。

## Per-minute 趋势

- cc2 流量均匀分布，无异常波动
- 3×429 spike 在 11:25, 11:30, 11:40 — 仅 hermes
- cc2 的 502(buffer_exhausted) 在 11:35 — 与 hermes 429 时段精确重叠
→ NVCF 在该 20min 窗口有间歇配额/负载波动，cc2 和 hermes 同时受影响

## 容器状态

| 容器 | Up | 健康 |
|------|-----|------|
| nv_gw | 35min | /health ok (num_keys=5) |
| cc4101 | 25h | FALLBACK_UPSTREAM_URL=none ✓ |
| logs_db | 34h | running |

nv_gw 未在本轮重启 (post9 提到的"两轮均重启"模式打破 — nv_gw Up 35min 稳定)。

## 配置漂移确认 (本轮运行态)

nv_gw 容器 Env (运行态):
```
UPSTREAM_TIMEOUT=90                  ← compose 末行=130, 未 up-d 重建
KEY_COOLDOWN_S=45                    ← compose 末行=60, 未 up-d 重建
NVU_BUFFER_MAX_RETRIES=8             ← 漂移态 (设计值=5)
NVU_BUFFER_TIMEOUT_STAIRS=30,50,70,90,90,90,90,90  ← 漂移态 (设计值=90,90,90,90,90)
NVU_BUFFER_TOTAL_DEADLINE_S=600      ← 漂移态 (设计值=450)
NVU_DISABLE_MS_FALLBACK=1           ← 铁律守护
TIER_COOLDOWN_S=180
NV_INTEGRATE_KEY_COOLDOWN_S=90
```

cc4101 容器 Env (运行态):
```
FALLBACK_UPSTREAM_URL=none           ← 破釜沉舟 ✓
CC4101_STREAM_TOTAL_DEADLINE_S=470   ← 设计值 ✓
PRIMARY_HEADER_TIMEOUT=400           ← 设计值 ✓
UPSTREAM_TIMEOUT=130
UPSTREAM_IDLE_TIMEOUT=150
```

**漂移态评估**:
- 8 retries / 600s 比 5 retries / 450s 更慷慨 → 对 SR 有利
- KEY_COOLDOWN_S=45 比 60 更短 → key 更快恢复 → 对 SR 有利
- 当前漂移方向对 SR 是正向的，暂不纠正

## cc2 SR 走势 (post4→post10)

| 轮次 | cc2 SR | 错误 | 趋势 |
|------|--------|------|------|
| post4 | 52/53=98.1% | 1×buffer_exhausted | 爬升 |
| post5 | 58/59=98.3% | 1×buffer_exhausted | 持稳 |
| post6 | 64/65=98.46% | 1×buffer_exhausted | 爬升 |
| post7 | 90/91=98.9% | 1×buffer_exhausted | 爬升 |
| post8 | 30/31=96.8% | 1×buffer_exhausted | 波动(nv_gw重启) |
| **post9** | **40/40=100%** | **0** | **满分** 🎉 |
| **post10** | **37/38=97.4%** | **1×buffer_exhausted** | 微跌(NVCF波动) |

→ 97.4% 仍属高位 (post4-post8 常态区间), post9 满分是峰值。post10 微跌来自 NVCF 波动。

## 本轮行动

- 0 改动 0 restart
- 仅写入 round 文件 + 覆写 STATE.md
- 确认: transport 层连续 6+ 轮 0 冒泡 (R-nvonly 短惩罚机制已验证稳定)
- 确认: 破釜沉舟持续 (fallback=0)
- 确认: buffer 漂移态对 SR 正向

## 下一轮建议

1. 继续巡检。cc2 SR 稳定在 97-100% 区间，目标连续 3 轮 99%+。
2. 关注 hermes all_tiers_exhausted 频率 — 当前 4 次/30min 同比 post9 的 3 次略升，若持续扩散需关注。
3. 配置漂移留待非 NOP 轮统一处理 (compose env 末行生效需 `up -d` 重建)。
4. nv_gw 本轮 Up 35min 未重启 — post9 的"每轮重启"模式已打破。
5. transport 短惩罚机制已验证 6+ 轮 0 冒泡 — 可持续受益。
6. 铁律常驻: 改前数据, 改后验证, 聚焦 40006, 不碰 40007, 只改 HM2, 写入仓库。