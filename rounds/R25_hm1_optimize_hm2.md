# R25: HM1优化HM2 — MIN_OUTBOUND_INTERVAL_S 10.0→11.0 (+1.0s 请求间隔)

**轮次**: R25  
**角色**: HM1 (opc_uname) 优化 HM2 (opc2_uname)  
**变更**: `MIN_OUTBOUND_INTERVAL_S`: 10.0 → 11.0 (+1.0s, +10%)  
**时间**: 2026-06-26 07:36  
**原则**: 少改多轮，单参数变更  
**铁律**: 只改HM2，决不改HM1

---

## 📊 数据收集 (HM2 30分钟窗口)

### 请求摘要
| 指标 | 值 |
|------|---|
| 总请求数 | 94 |
| 直接成功 (非fallback) | 4 (4.3%) |
| Fallback成功 | 90 (95.7%) |
| Fallback平均延迟 | 19,423ms |
| 直接平均延迟 | 11,201ms |
| all_tiers_exhausted | 0 (0次) |

### 错误分布 (hm_tier_attempts, 30min)
| 错误类型 | 计数 | 占比 |
|----------|------|------|
| 429_nv_rate_limit (glm5.1) | 230 | 93.5% |
| NVCFPexecSSLEOFError (deepseek) | 13 | 5.3% |
| NVCFPexecConnectionResetError | 2 | 0.8% |
| NVCFPexecTimeout | 1 | 0.4% |

### Per-Key 429分布 (glm5.1_hm_nv)
| Key | 429次数 |
|-----|---------|
| k1 | 48 |
| k2 | 48 |
| k3 | 46 |
| k4 | 45 |
| k5 | 48 |

### Fallback延迟桶
| 桶 | 请求数 |
|----|--------|
| 0-10s | 16 |
| 10-20s | 45 |
| 20-30s | 19 |
| 30-50s | 6 |
| 50s+ | 4 |

### 关键发现
- **0-tier failures = 0** — HM2的 `HM_CONNECT_RESERVE_S=3` 正常工作，无 pre-tier 连接失败
- **429 100%函数级限流** — glm5.1 NVCF函数ID `822231fa-d4f3` 被NVCF完全限制，所有5个key均匀命中
- **deepseek SSLEOFError 13次** — 这是SOCKS5+SSL连接层面的SSL握手失败，非可调参数消除
- **RESERVE瓶颈不存在** — 不需要增加RESERVE

---

## 🎯 优化方案

### 选择 `MIN_OUTBOUND_INTERVAL_S`

**为什么选这个参数**:
- 230次429在30分钟 = 每秒 ~0.13次429 = 每7-8秒1次
- `MIN_OUTBOUND_INTERVAL_S=10.0` → 5key×10s=50s 最小请求间隔
- 当前10s间隔下，每50s完成一轮5key循环 → 30分钟=36次完整循环
- 函数级限流触发频率 = 每次循环触发230/36≈6.4次429
- **增加至11.0s** → 5key×11s=55s → 30分钟≈32.7次完整循环
- 有效请求率降低10%：从每分钟~3.1次降至~2.8次
- 直接减少NVCF函数限流触发次数

**单独变更原则**: 仅改1个参数 `MIN_OUTBOUND_INTERVAL_S`，不碰任何其他参数（RESERVE=3保持不变，UPSTREAM=55不变，BUDGET=105不变，KEY_COOLDOWN=30.0不变，TIER_COOLDOWN=60不变）。

---

## ⚙️ 执行

### 变更前 (docker-compose.yml)
```yaml
MIN_OUTBOUND_INTERVAL_S: "10.0"
```

### 变更后 (docker-compose.yml)
```yaml
MIN_OUTBOUND_INTERVAL_S: "11.0"  # +1.0s first-key delay (10% spacing)
```

### 执行命令
```bash
ssh opc2_uname@100.109.57.26
cd /opt/cc-infra
sed -i 's/MIN_OUTBOUND_INTERVAL_S: "10.0"/MIN_OUTBOUND_INTERVAL_S: "11.0"/' docker-compose.yml
docker compose up -d --force-recreate hm40006
```

### 验证
```bash
# 配置确认
docker exec hm40006 python3 -c 'import os; print(os.environ["MIN_OUTBOUND_INTERVAL_S"])'
# → 11.0 ✅

# 健康检查
curl http://100.109.57.26:40006/health
# → {"status": "ok", "proxy_role": "passthrough", ...} ✅

# 服务状态
docker ps | grep hm40006
# → Up (healthy) ✅
```

---

## 📈 预期效果

| 指标 | 当前值 | 预期改善 |
|------|--------|----------|
| 429/30min | 230 | ↓10% → ~207 |
| 有效请求率 | 3.1/min | ↓10% → 2.8/min |
| Fallback率 | 95.7% | ~95% (函数级限流仍在) |
| 0-tier失败 | 0 | 保持0 |
| 平均延迟 | 19.4s | ~19s (10% 间隔增加，延迟持平) |

**关键**: 此轮不改RESERVE（HM2的RESERVE=3无0-tier失败），只调MIN_OUTBOUND_INTERVAL_S来降低整体请求频率，给NVCF函数级限流更多恢复窗口。

---

## 📝 历史轨迹

| 轮次 | 变更 | 参数 | 作者 |
|------|------|------|------|
| R20 | MIN_OUTBOUND 12.0→8.0, UPSTREAM 35→45, BUDGET 70→90, RESERVE 2→4 | HM1→HM2 | opc_uname |
| R21 | RESERVE 4→6 | HM2→HM1 | opc2_uname |
| R22 | RESERVE 6→8 | HM2→HM1 | opc2_uname |
| R23 | RESERVE 8→14 | HM2→HM1 | opc2_uname |
| R24 | RESERVE 14→18 | HM2→HM1 | opc2_uname |
| **R25** | **MIN_OUTBOUND 10.0→11.0** | **HM1→HM2** | **opc_uname** |

---

## ⏳ 轮到HM2优化HM1