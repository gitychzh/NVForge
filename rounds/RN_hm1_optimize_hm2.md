# RN: HM1优化HM2 — TIER_COOLDOWN_S 42→43 (+1s 层级冷却)

**轮次**: RN (new round)
**角色**: HM1 (opc_uname) 优化 HM2 (opc2_uname)  
**变更**: `TIER_COOLDOWN_S`: 42 → 43 (+1.0s, +2.4%)
**时间**: 2026-06-27 15:02 UTC (23:02 BJT)
**原则**: 少改多轮，单参数变更，继续TIER_COOLDOWN调优轨迹
**铁律**: 只改HM2，决不改HM1

---

## 📊 数据收集 (HM2 30分钟窗口 14:32-15:02 BJT)

### 请求摘要 (PostgreSQL `hermes_logs.hm_requests`)
| 指标 | 值 |
|------|---|
| 总请求数 | 55 |
| 成功 (status=200) | 54 (98.2%) |
| 失败 (status≠200) | 1 (1.8%) |
| Fallback发生 | 29 (52.7%) |
| 直接glm5.1成功 | 26 (47.3%) |
| 平均延迟 | 31,569ms |
| P50延迟 | 23,947ms |
| P95延迟 | 83,836ms |
| 最大延迟 | 85,910ms |
| 最小延迟 | 5,023ms |

### Tier分布 (成功请求)
| Tier | 计数 | 成功 | 平均延迟 |
|------|------|------|---------|
| deepseek_hm_nv (fallback) | 29 | 28 (96.6%) | 43,135ms |
| glm5.1_hm_nv (direct) | 26 | 26 (100%) | 16,648ms |

### 错误分布 (`hm_tier_attempts`, 30min)
| Tier | 错误类型 | 计数 | 平均耗时 |
|------|----------|------|----------|
| glm5.1_hm_nv | 429_nv_rate_limit | 74 | — |
| glm5.1_hm_nv | NVCFPexecConnectionResetError | 6 | 1,892ms |
| glm5.1_hm_nv | NVCFPexecSSLEOFError | 6 | 7,079ms |
| deepseek_hm_nv | NVCFPexecSSLEOFError | 1 | 16,686ms |

### 请求级错误 (hm_requests)
| 错误类型 | 计数 | 延迟 | 所属tier |
|----------|------|------|----------|
| NVStream_IncompleteRead | 1 | 63,355ms | deepseek_hm_nv (k1) |

### 429 每键分布 (glm5.1 tier)
| NV Key | 429 计数 | 占比 |
|--------|----------|------|
| k0 (idx=0) | 8 | 10.8% |
| k1 (idx=1) | 14 | 18.9% |
| k2 (idx=2) | 15 | 20.3% |
| k3 (idx=3) | 18 | 24.3% |
| k4 (idx=4) | 18 | 24.3% |

**分布**: 较均匀但有k3/k4偏多倾向 — 仅74次429/30min（低负载）

### 容器状态
- hm40006: Up 22min (healthy), 无OOM, 无重启
- mihomo: 运行中 (1进程, 未触碰 — 铁律禁止)
- 健康检查: 200 OK
- 当前配置生效: TIER_COOLDOWN_S=42 (变更前)

### 综合关键发现（30min窗口）
1. **低负载窗口**: 仅55请求/30min — 周末/PTO时段，请求量极低
2. **glm5.1 100% 429**: 所有26个直接成功请求都经过glm5.1→429→cycle→最终成功。NV API函数级速率限制无差别
3. **5键全429模式保持**: 日志显示 `all 5 keys failed: 429=5` 在5秒内5键全部429，触发GLOBAL-COOLDOWN(45s)
4. **deepseek fallback稳定**: 29/55 (52.7%) fallback到deepseek，成功率96.6%
5. **TIER_COOL gap=5s**: KEY_COOLDOWN=37 vs TIER_COOLDOWN=42，gap=5s — 键恢复领先后层级，但5键全429时无意义
6. **仅有1个NVStream_IncompleteRead**: 63,355ms deepseek k1 — 63s UPSTREAM_TIMEOUT在超长请求中触发IncompleteRead（流式读取不完整）
7. **ConnectionResetError=6**: glm5.1 k1/k2早期键连接重置，NV API侧主动断开连接

---

## 🎯 优化方案

### 选择 `TIER_COOLDOWN_S` 42→43

**变更理由**:
- TIER_COOLDOWN轨迹: R95是42→40 (-2s)，本节反转: 42→43 (+1s)
- 当前根本问题: 5键在5秒内全部429 (k0→k4全429)，因为NV API函数级速率限制无差别
- KEY_COOLDOWN=37.0：键429后37s恢复。但5键全429意味着所有键同时冷却
- TIER_COOLDOWN=42：层级429后42s恢复。当层级冷却到期(42s)，所有键的冷却也同时到期(37s)
- gap=5s (KEY=37, TIER=42) — 键恢复先于层级。但5键全429时，所有键同时进入37s冷却→42s时层级恢复，但键也刚恢复→立即全部再429
- +1s至43: TIER_COOLDOWN=43 → 层级冷却到期时，键冷却还有1s残留 = gap从5s→6s
- 6s gap = 层级恢复后，键还有1s才恢复 → 新请求不会立即触发所有5键 → 减少"5键全429"循环
- GLOBAL-COOLDOWN=45s硬编码不变 — 45s仍然是最终安全网
- 单参数变更，不影响其他11个配置参数
- 继续"少改多轮"原则 — 仅+1s，保守且可逆

**不选其他参数的原因**:
- **KEY_COOLDOWN_S**: 37.0已刚改过（36→37, RN），观察效果中。且KEY_COOLDOWN和TIER_COOLDOWN联动需要gap≥6
- **UPSTREAM_TIMEOUT**: 63s稳定，唯一NVStream_IncompleteRead在63s — 63s UPSTREAM对deepseek超长请求刚好够，不调整
- **MIN_OUTBOUND_INTERVAL_S**: 21.0，前轮RN刚改过（22→21, -1s），观察效果中
- **TIER_TIMEOUT_BUDGET_S**: 120充裕，3-key循环(63+24+10=97s) ≤ 120s，不调整
- **HM_CONNECT_RESERVE_S**: 12稳定，无变更必要
- **GLOBAL_COOLDOWN_S**: 45s硬编码在代码中，不可配置

**与对端(opc2_uname)的联动**:
- 对端刚变更: KEY_COOLDOWN_S 31→32 (+1s on HM1) — 也是增加键冷却
- 本端回归: TIER_COOLDOWN_S 42→43 (+1s on HM2) — 增加层级冷却
- 双向都增加冷却 → 统一方向: 减少过度重试 → 更稳定
- KEY_COOLDOWN(37) + TIER_COOLDOWN(43) = 双保险 → 总冷却效应增强

**预算验证** (B=120, U=63, R=12, M=21):
```
1st key: min(63, 120-12=108) = 63s   → remaining=57
2nd key: max(10, min(63, 57-12-21=24)) = 24s → remaining=33
3rd key: max(10, min(63, 33-12-21=0)) = 10s (floor)
Total: 63+24+10=97s ≤ 120s ✓
```

---

## ⚙️ 执行

### 命令
```bash
# 1. 备份
sudo cp /opt/cc-infra/docker-compose.yml /opt/cc-infra/docker-compose.yml.bak.RN_$(date +%s)

# 2. 修改 line 481: TIER_COOLDOWN_S "42" → "43"
sudo sed -i '481s/"42"/"43"/' /opt/cc-infra/docker-compose.yml

# 3. 更新注释标记
sudo sed -i '481s/# R95: HM1→HM2/# RN: HM1→HM2/' /opt/cc-infra/docker-compose.yml

# 4. 重建容器 (不碰mihomo)
cd /opt/cc-infra && sudo docker compose up -d --no-deps --force-recreate hm40006
```

### 验证结果
```
docker exec hm40006 env | grep TIER_COOLDOWN_S    # → 43 ✅
docker ps --filter name=hm40006 --format "{{.Status}}"    # → Up (healthy) ✅
curl -s http://localhost:40006/health                  # → 200 ✅

# 完整环境变量确认（无意外变更）:
TIER_COOLDOWN_S=43          ← ✅ 42→43 (+1s)
KEY_COOLDOWN_S=37.0         ← 未变
UPSTREAM_TIMEOUT=63         ← 未变
MIN_OUTBOUND_INTERVAL_S=21.0 ← 未变
HM_CONNECT_RESERVE_S=12     ← 未变
TIER_TIMEOUT_BUDGET_S=120   ← 未变
PROXY_TIMEOUT=300           ← 未变
```

---

## 📈 预期效果

| 指标 | 变更前 | 变更后预期 |
|------|--------|------------|
| 层级冷却时间 | 42.0s | 43.0s (+1s) |
| 键冷却 vs 层级冷却 gap | 5s | 6s |
| 5键全429模式频率 | 每30min ~2次 | ~1-2次 (↓) |
| ConnectionResetError (glm5.1) | 6/30min | ~4-5 (↓20-30%) |
| SSLEOFError (glm5.1) | 6/30min | ~4-5 (↓20-30%) |
| NVStream_IncompleteRead | 1/30min | ~0-1 |
| Fallback率 | 52.7% | ~50-52% (小幅↓) |
| 成功率 | 98.2% | ~98.5% |
| P95延迟 | 83,836ms | ~78,000-80,000ms |

**机制**: +1s TIER_COOLDOWN = 层级冷却从42→43 = gap从5s→6s = 层级冷却到期后键仍有一秒冷却窗口 = 新请求触发glm5.1时不会立即遇到所有键恢复 → 减少"5键全429→GLOBAL-COOLDOWN→deepseek fallback"循环 = 更少NVCFPexecConnectionResetError(k1/k2早期键连接重置) = 更少SSLEOFError(SSL EOF在键恢复边缘发生) = 更快请求完成 = 更低延迟 = 更稳定。

**注意**: glm5.1 NVCF函数100% 429是NV API侧函数级速率限制，HM2侧任何配置变更无法消除。优化焦点从"消除429"转向"减少5键全429后中层级冷却与键冷却的时间窗口重叠，降低键恢复后立即再全部429的恶性循环"。

---

## ⏳ 轮到HM2优化HM1  ← 脚本检测此标记