# R130: HM1→HM2 — MIN_OUTBOUND_INTERVAL_S 9.0→9.5 (+0.5s inter-request spacing)

**Role**: HM1 (opc_uname) 优化 HM2 (opc2_uname)
**Date**: 2026-06-27 23:47 CST
**Change**: MIN_OUTBOUND_INTERVAL_S: 9.0 → 9.5 (+0.5s inter-request spacing)
**Principles**: 少改多轮(单参数); 铁律:只改HM2不改HM1; 更少报错更快请求超低延迟稳定优先

---

## 数据收集 (Data Collection)

### SSH到HM2收集完整链路数据

```bash
ssh -p 222 opc2_uname@100.109.57.26
```

### Docker运行环境变量

| 参数 | 值 |
|------|-----|
| HM_CONNECT_RESERVE_S | 20 (R129: 18→20) |
| TIER_TIMEOUT_BUDGET_S | 130 (R128: 128→130) |
| KEY_COOLDOWN_S | 45 (= GLOBAL_COOLDOWN=45) |
| TIER_COOLDOWN_S | 45 (= GLOBAL_COOLDOWN=45) |
| MIN_OUTBOUND_INTERVAL_S | 9.0 |
| UPSTREAM_TIMEOUT | 71 |
| PROXY_TIMEOUT | 300 |

### 30分钟窗口DB统计 (hm_requests)

| 指标 | 值 |
|------|-----|
| 总请求数 | 83 |
| 成功 (200) | 83 (100.0%) |
| 失败 | 0 (0.0%) |
| 平均延迟 | 21,222ms |
| p50 | 13,044ms |
| p90 | 46,904ms |
| p95 | 57,438ms |
| 最小 | 2,581ms |
| 最大 | 183,170ms |

### 10分钟突发窗口

| 指标 | 值 |
|------|-----|
| 总请求 | 32 |
| 成功 | 32 (100.0%) |
| 平均延迟 | 19,693ms |
| p50 | 12,162ms |
| p90 | 26,745ms |

### 层级分布 (Tier Distribution)

| Tier | 请求数 | 平均延迟 | Fallback | 429计数 |
|------|--------|----------|----------|---------|
| glm5.1_hm_nv | 80 | 19,033ms | 0 | 38 |
| deepseek_hm_nv | 3 | 79,604ms | 3 (all fallback from glm5.1) | 5 |

### Key-Level错误分解 (hm_tier_attempts — 30min)

| 错误类型 | 计数 |
|----------|------|
| 429_nv_rate_limit | 25 |
| NVCFPexecSSLEOFError | 8 |
| NVCFPexecConnectionResetError | 5 |
| NVCFPexecTimeout | 3 |
| empty_200 | 2 |

**请求级错误**: 0 (所有错误均为key-level重试，非请求失败)

### Error Detail JSONL (最新5条)

最新一条 (23:42:20): `all_429: true` — 纯429爆冲，1个key attempt, elapsed=588ms
其他4条: `all_429: false` — 混合失败 (429+timeout+empty_200+SSLEOFError), elapsed=121-125s

### Budget Break检查

```
docker logs hm40006 --tail 200 | grep "remaining\|minimum\|budget"
→ 无 "remaining X.Xs < 10s minimum" 日志 — tier预算未触发10s阈值
→ 仅 "all keys in cooldown, breaking" (23:42:20) — 所有keys同时冷却，非预算耗尽
```

### Mihomo确认

```
pgrep -a mihomo → 2008535 /home/opc2_uname/.local/bin/mihomo
✅ 运行中 — 绝不触碰
```

---

## 分析 (Analysis)

### 核心发现

1. **100%成功率**: 83请求零失败 — 系统已处于极优状态。所有25×429 + 8×SSLEOF + 5×ConnectionReset + 3×Timeout + 2×empty_200 均为key-level重试，无任何请求级错误。

2. **429是主导key-level错误**: 25×429_nv_rate_limit在glm5.1 tier中占比最高(25/43=58%)。最新error detail显示`all_429: true`(23:42:20) — 纯429爆冲，仅588ms — 证明NV API function-level rate limiting是瓶颈。

3. **Tier预算充足**: 无`remaining X.Xs < 10s minimum`日志 — 130s预算远高于实际消耗。3条deepseek fallback总计33,487+22,154+183,170ms = 238,811ms，但这是跨2 tier(glm5.1+deepseek)的总时间，各tier独立预算。

4. **10min vs 30min延迟差异**: 10min窗口p90=26,745ms vs 30min窗口p90=46,904ms — 差距20s说明近期请求更轻量，历史窗口包含大请求(long-context)拉高均值。

### 优化方向论证

**为什么选MIN_OUTBOUND_INTERVAL_S (+0.5s)**:
- 429是主导key-level错误(25条)，增加间隔直接减少429碰撞概率
- +0.5s是11%增量(9.0→9.5)，保守且可逆，不破坏100%成功率
- 5-key cycle alignment: 5×9.5=47.5s vs GLOBAL_COOLDOWN=45s — 轻微超出2.5s，给予额外缓冲而非完全对齐
- 10min窗口p90=26,745ms表明请求本身快速，+0.5s间隔不会显著增加总延迟

**为什么不选其他参数**:
- TIER_TIMEOUT_BUDGET_S: 预算已充足(130s)，无budget break事件，增加无意义
- KEY_COOLDOWN_S/TIER_COOLDOWN_S: 已=45=GLOBAL_COOLDOWN，R127收敛完成
- UPSTREAM_TIMEOUT: 71s已足够，p95=57,438ms远低于71s
- HM_CONNECT_RESERVE_S: 已20(R129刚+2s)，让HM2观察后再定

---

## 优化执行 (Execution)

### 变更: MIN_OUTBOUND_INTERVAL_S: 9.0 → 9.5

```bash
# 1. 修改docker-compose.yml (line 479)
ssh -p 222 opc2_uname@100.109.57.26 \
  "sed -i '479s|MIN_OUTBOUND_INTERVAL_S: \"9.0\"|MIN_OUTBOUND_INTERVAL_S: \"9.5\"|' \
   /opt/cc-infra/docker-compose.yml"

# 2. 重建容器 (仅hm40006, 不碰mihomo)
cd /opt/cc-infra && docker compose up -d --no-deps --force-recreate hm40006
```

### 验证

| 检查项 | 结果 |
|--------|------|
| `docker exec hm40006 env \| grep MIN_OUTBOUND` | `MIN_OUTBOUND_INTERVAL_S=9.5` ✅ |
| `docker ps --filter name=hm40006` | `Up ... (healthy)` ✅ |
| `curl -s localhost:40006/health` | `200 OK` ✅ |
| `pgrep -a mihomo` | PID 2008535 运行中 ✅ |

### Cross-Machine Tier Config (Health)

```json
{
  "hm_model_tiers": ["glm5.1_hm_nv", "deepseek_hm_nv", "kimi_hm_nv"],
  "hm_default_model": "glm5.1_hm_nv",
  "nvcf_pexec_models": ["deepseek_hm_nv", "kimi_hm_nv", "glm5.1_hm_nv"]
}
```
✅ Tiers correct — no config drift

---

## 预期效果 (Expected Effects)

| 指标 | 变更前 (9.0s) | 变更后 (9.5s) | 预期 |
|------|---------------|---------------|------|
| MIN_OUTBOUND_INTERVAL_S | 9.0 | 9.5 | +0.5s spacing |
| 5-key cycle alignment | 45.0s | 47.5s | 轻微> GLOBAL=45s |
| 429碰撞频率 | 25/30min | ↓ 预计减少~10% | 更少429浪费 |
| 30min成功率 | 100% (83/83) | 保持100% | 不破坏零失败记录 |
| 平均延迟 | 21,222ms | ↑ ~500ms (间隔增加) | 可接受的微小增加 |
| p90延迟 | 46,904ms | 预计保持 | 间隔不影响单请求延迟 |

### 5-Key Cycle Alignment (理论对齐)

```
变更前: 5 × 9.0 = 45.0s = GLOBAL_COOLDOWN=45s (精确对齐)
变更后: 5 × 9.5 = 47.5s > GLOBAL_COOLDOWN=45s (2.5s超出)

→ 超出2.5s意味着: 完成5-key rotation需要47.5s, 
  但GLOBAL_COOLDOWN=45s在45s时已过期。
  剩余2.5s是"安全余量" — 不需要精确对齐，
  轻微超出避免恰好撞上rate-limit窗口刷新时刻。
```

---

## ⏳ 轮到HM2优化HM1  ← 脚本检测此标记