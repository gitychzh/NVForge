# R37: MIN_OUTBOUND_INTERVAL_S 0→10 限流 — 换思路对抗全5key 429

## 数据依据 (改前 30min 窗口, 2026-07-21 00:00-00:30 UTC+8)

| 指标 | 值 |
|------|-----|
| 30min 总请求 | 154 |
| 成功 | **0** |
| SR | **0%** |
| 502 | 140 |
| 429 | 22 |
| 错误类型 | 162 all_tiers_exhausted |
| hm4104 fallback | **240 次** |
| breaker | **持续 OPEN** (PRIMARY-BREAKER-SKIP) |
| caller 分布 | "other"=140 (91%), "unknown"=14 |

### nv_gw 日志验证
```
[NV-TIER] tier=dsv4p_nv Starting (k1-k5 cycle)
[NV-COOLDOWN] k1-k5 all marked cooling after 429
[NV-TIER-FAIL] all 5 keys failed: 429=5, elapsed=7249ms
[NV-GLOBAL-COOLDOWN] tier=dsv4p_nv all keys 429. Marking all cooling 180s
[NV-TIER-SKIP] all keys in cooldown, skipping
```

每 180s TIER_COOLDOWN 到期 → 一条请求进 → 全 5 key 429 (7s 内) → 再锁 180s。死循环。

## 核心发现: caller "other" 占 91%

R36 诊断"NVCF key 配额不足"在本轮得到进一步确认：**caller "other" 占 140/154=91%** ，说明有其他 agent/进程在共享 dsv4p_nv 的 5 个 NVCF key 配额。hermes2 自身只占 14/154=9%。配额被共享耗尽，不是冷却参数能解决的。

## 改动

**docker-compose.yml nv_gw 段**:
```
- MIN_OUTBOUND_INTERVAL_S=0   →   - MIN_OUTBOUND_INTERVAL_S=10
```

**决策逻辑**: 按 STATE.md R37 决策矩阵"全 key 仍 429, SR=0% → 不再调冷却参数，考虑 MIN_OUTBOUND_INTERVAL_S 限流"。10s 间隔强制所有出站请求排队，降低 NVCF 并发压力，给 key RPM/TPM 配额恢复窗口。不是调冷却节奏，而是降低总请求频率。

**不碰的**:
- ❌ ms_gw (热备)
- ❌ TIER_COOLDOWN_S / KEY_COOLDOWN_S (已到天花板)
- ❌ glm5_2_nv / kimi_nv tier 配置
- ❌ function_id / strip_params (NVCF function 正常, 只是 429)

## 验证

```bash
# 备份: docker-compose.yml.bak.R37
$ curl -s http://localhost:40006/health
{"status": "ok", ...}
$ docker ps --filter name=nv_gw
nv_gw Up
$ docker exec nv_gw env | grep -E "MIN_OUTBOUND|TIER_COOLDOWN|KEY_COOLDOWN"
MIN_OUTBOUND_INTERVAL_S=10  ✓
TIER_COOLDOWN_S=180         ✓
KEY_COOLDOWN_S=60           ✓
```

## 下一步 (R38)

- 等待 30min+ 看 MIN_OUTBOUND_INTERVAL_S=10 是否让 key 配额恢复 (SR > 0%)
- 如果仍全 429 → 10s 仍不够，尝试 30s 或更大间隔
- 如果部分恢复 → 巡检轮，记录"限流开始生效"
- 如果仍全 429 且 30s 也无效 → **需人为介入**: 检查 NVCF console 看 dsv4p function 的 key 配额被谁占满，可能需要隔离 caller "other" 或增加 key
- 查 caller "other" 到底是什么 agent/进程，确认是否可控制其流量