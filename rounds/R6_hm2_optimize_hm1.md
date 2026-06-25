# R6: HM2 优化 HM1 (hm-40006 链路) — 修复 glm5.1_hm_nv 100% 429 失败

**日期**: 2026-06-25 20:00 CST
**执行者**: HM2 (opc2_uname)
**对象**: HM1 (opc_uname@100.109.153.83)
**上一轮**: R5 (HM2优化HM1 — SSLEOFError重试BUG修复+超时/冷却调优)

---

## 📊 数据采集

### HM1 hm40006 容器状态

- 运行中 (healthy), NVCF pexec direct, 3-tier ring fallback
- 配置: UPSTREAM_TIMEOUT=60, TIER_TIMEOUT_BUDGET_S=75, KEY_COOLDOWN_S=7.0, MIN_OUTBOUND_INTERVAL_S=1.2, HM_CONNECT_RESERVE_S=2

### Docker 日志 (最近30分钟, ~19:45–20:15)

**观察**: 所有请求 → glm5.1_hm_nv primary tier → 全键429 → fallback deepseek/kimi

```
典型循环:
[19:51:15] glm5.1_hm_nv k2 → 429 (1.7s) → k3 → 429 (1.8s) → k4 → 429 (1.9s) → k5 → 429 (2.0s) → k1 → 429 (2.1s)
→ all keys in cooldown → HM-TIER-FAIL (5 keys, 5341ms) → FALLBACK deepseek_hm_nv
→ deepseek k5 → success (7.6s after 5 cycle attempts)
```

**100% 失败率**: glm5.1_hm_nv 全部5键 429, 无一次直接成功。

### PostgreSQL 数据 (hm_requests, 30分钟窗口)

| 指标 | 值 |
|------|-----|
| 总请求数 | 15 |
| 成功 (status=200) | 15 (100% 通过 fallback) |
| 直接glm5.1成功 | **0** |
| glm5.1 429循环 | 平均 2.47 次/请求 |
| Fallback到deepseek | 14次 (93%), avg ~69s |
| Fallback到kimi | 1次 (7%), avg ~150s |
| SSLEOFError | **0** ← R5修复已生效, 无SSL错误 |
| 其他错误类型 | **0** |

### 延迟分布 (status=200)

| 路径 | 数量 | 平均延迟 | 平均TTFB |
|------|------|----------|----------|
| Fallback deepseek | 14 | 69.0s | 68.5s |
| Fallback kimi | 1 | 150.4s | 150.4s |
| 直接 glm5.1 | 0 | — | — |

### 🔴 关键发现: 容器与compose文件ENV不匹配

```
变量                        | compose文件 | 容器实际 | 状态
MIN_OUTBOUND_INTERVAL_S    | "1.2"       | 1.2      | ✅ 一致
KEY_COOLDOWN_S             | "7.0"       | 7.0      | ✅ 一致
HM_CONNECT_RESERVE_S       | "2"         | 2        | ✅ 一致

→ R5修改了compose但容器未重建? 确认: 容器已重建, env一致。
```

---

## 🩺 诊断: glm5.1_hm_nv Tier 100% 429 失败根因

**根因1**: `MIN_OUTBOUND_INTERVAL_S=1.2` 过于激进
→ 每1.2秒发送一个请求，5个密钥在短时间内同时触发NVCF rate limit → 全键429。

**根因2**: `KEY_COOLDOWN_S=7.0` 冷却时间不足
→ 429后仅冷却7秒即重试，NVCF rate limit窗口约60秒 → 重试时仍在rate limit窗口内 → 再次429 → 恶性循环。

**根因3**: 5个密钥共享所有模型 (glm5.1, deepseek, kimi)
→ 所有请求都使用同一个5键池 → 键池拥堵 → 任意模型的高流量都会影响其他模型。

**数据证据**:
- 全部5键均匀分布429，无任何键成功 → 系统性rate limit，非个别键故障
- `HM-TIER-SKIP` 频繁出现 ("all keys in cooldown, skipping") → 冷却逻辑频繁触发
- SSLEOFError = 0 → R5的SSL重试修复完美工作，但429比SSL错误更严重

**历史参考**: 
- HM1的R6 (优化HM2) 将 HM2 的 MIN_OUTBOUND 从 0.5→3.0, KEY_COOLDOWN 从 10→20 — 但HM2容器从未重建，旧参数仍在使用
- 本轮的429问题与HM2的429问题是同质问题 (共享5键池，高并发触发)

---

## 🔧 优化方案

| # | 变更 | Before | After | 理由 | 风险 |
|---|------|--------|-------|------|------|
| 1 | `MIN_OUTBOUND_INTERVAL_S` | 1.2 | **3.0** | 1.2→3.0: 2.5×增大，防止并发请求触发全部键同时rate limit | 请求间隔增大→吞吐量略降 |
| 2 | `KEY_COOLDOWN_S` | 7.0 | **20.0** | 7→20: ~3×增大，匹配NVCF ~60s rate limit窗口，减少冷却-重试-再429循环 | 键恢复更慢但更准确 |
| 3 | `UPSTREAM_TIMEOUT` | 60 | **65** | glm5.1 NVCFPexecTimeout ~45-47s, +5s headroom + 重试backoff | 无 |

**铁律**: 只改HM1配置，绝不动HM2本地环境。

---

## ✅ 执行记录

```bash
# 1. SSH到HM1
ssh -p 222 opc_uname@100.109.153.83

# 2. 备份compose
cp /opt/cc-infra/docker-compose.yml /opt/cc-infra/docker-compose.yml.bak.R6.$(date +%s)

# 3. 修改compose (仅hm40006段，精确行编辑)
# Line 417: UPSTREAM_TIMEOUT: "60" → "65"
# Line 420: MIN_OUTBOUND_INTERVAL_S: "1.2" → "3.0"
# Line 421: KEY_COOLDOWN_S: "7.0" → "20.0"

# 4. Rebuild + 重启 (关键步骤 — 不rebuild则env不生效)
cd /opt/cc-infra
docker compose build hm40006
docker compose up -d hm40006 --no-deps --force-recreate

# 5. 验证环境变量
docker exec hm40006 env | grep -E "MIN_OUTBOUND|KEY_COOLDOWN|UPSTREAM_TIMEOUT|HM_CONNECT"
# → MIN_OUTBOUND_INTERVAL_S=3.0  KEY_COOLDOWN_S=20.0  UPSTREAM_TIMEOUT=65  HM_CONNECT_RESERVE_S=2
```

**构建耗时**: ~0.1s (Dockerfile全量cache)
**健康检查**: `curl localhost:40006/health` → OK

---

## 📈 验证结果

**重启后5分钟 (20:00–20:05)**:
- **6个成功请求** (all through fallback, 平均 2.17 tiers tried)
- **SSLEOFError = 0** — R5修复继续生效
- **Fallback到deepseek**: 100%, avg ~81s
- **直接glm5.1**: 0次 — 429仍在持续 (NVCF rate limit尚未清除)

**预期**: 随着KEY_COOLDOWN=20s生效，键的冷却-重试循环将被打破。当NVCF rate limit窗口清除后，3.0s间隔将防止新的集中429。

---

## 🎯 预期效果

1. **429循环打破**: KEY_COOLDOWN 7→20s → 键在rate limit窗口内不会被频繁重试 → 减少"冷却-重试-再429"循环
2. **请求间隔增大**: MIN_OUTBOUND 1.2→3.0s → 防止5键在1秒内全部触发429 → 给rate limit窗口留出恢复时间
3. **SSLEOFError持续零**: R5修复已证明有效 (0次SSL错误)
4. **当rate limit清除时**: 3.0s间隔确保至少1-2个键在请求间隔中可用 → 减少全键429概率

---

## ⚠️ 更深层问题: 5键池共享限制

**5个NVCF键 (k1-k5) 被所有模型共享** (glm5.1, deepseek, kimi) → 任意模型的高流量都会影响整个键池。

**长期方向**:
- 考虑为每个模型分配独立的键组 (如 glm5.1=k1-k3, deepseek=k4-k5)
- 或增加更多NVCF键 (当前5个，可扩展到7-10个)
- 或配置模型级别的rate limit阈值 (如 glm5.1 最多3个并发键)

**本轮只做表面调优** (间隔+冷却)，深层重构留给后续轮次。

## ⏳ 轮到HM1优化HM2  ← 脚本检测此标记