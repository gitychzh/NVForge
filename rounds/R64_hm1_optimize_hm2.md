# R64: HM1→HM2 — KEY_COOLDOWN_S 26.5→30.0 (+3.5s, 冷却时间延长减少重复429)

## HM1 分析 HM2 链路

### 数据收集
**来源**: `docker logs hm40006 --tail 100` (HM2远端, opc2_uname:100.109.57.26)

**指标 (最近1小时)**:
- HM-CYCLE: 46 (429命中导致换键循环)
- HM-SUCCESS: 36 (成功请求)
- COOLDOWN: 48 total
- 成功率 (首次): 36/(36+46) = 43.9%
  - 很多请求需要2-4次循环才能找到可用key
  - 每次429触发~3-5s额外延迟

- **429分布 per key**:
  - k3: 12 (最热)
  - k1: 9
  - k2: 8
  - k4: 7
  - k5: 7
  - 分布相对均匀

- **Error/WARN**: 0 line (最近100行无报错)

### HM2 当前配置
| 参数 | 值 | 来源 |
|------|-----|------|
| LISTEN_PORT | 40006 | env |
| PROXY_TIMEOUT | 300s | env |
| UPSTREAM_TIMEOUT | 58s | env (NVCF pexec超时) |
| TIER_TIMEOUT_BUDGET_S | 111s | env (总tier预算) |
| KEY_COOLDOWN_S | **26.5s** | env (冷却时间) |
| TIER_COOLDOWN_S | 42s | env (tier级冷却) |
| MIN_OUTBOUND_INTERVAL_S | 17.0s | env (最小请求间隔) |
| HM_CONNECT_RESERVE_S | 18s | env (连接预留时间) |
| CHARS_PER_TOKEN_ESTIMATE | *** | env (被mask) |
| HM_NUM_KEYS | 5 | 默认 (k1-k5) |
| 模型层 | glm5.1→deepseek→kimi | 3-tier fallback |
| NVCF函数ID | 3个model各一个 | NVCF pexec直连 |
| mihomo代理端口 | 7894-7899 | per-key SOCKS5 |

### 分析

**关键洞察**: KEY_COOLDOWN_S=26.5s 是当前下限。每个key冷却后立即释放，但NV API速率限制窗口仍在生效。当请求密集时，多个key同时触发429并同时冷却→同时释放→同时再次429。短冷却导致"快速循环-快速429"模式，每次代价~3-5s延迟。

**理论**: 冷却时间越长，key的429间隔越大，减少"冷却→释放→立即再次429"的快速重启循环。5keys×26.5s=132.5s总冷却容量，vs 111s tier预算→tier预算内可完成完整循环。30.0s给出更多时间让key度过NV限流窗口。

**对比HM1**: HM1的KEY_COOLDOWN_S=36s（R63已调整），HM2当前26.5s明显偏短。合理对齐减少跨端差异。

### 计划

**单参数修改: KEY_COOLDOWN_S 26.5 → 30.0 (+3.5s)**

少改多轮策略: 只调整这一个参数，观察效果再决定后续步骤。

**预期效果**:
- ✅ 减少429重复命中率（key在冷却中更久）
- ✅ 降低"冷却→立即429 again"循环
- ✅ 每key请求间隔增大，NV限流更友好
- ⚠️ key不可用时间略增，但tier预算仍覆盖

**后续候选** (下一轮评估):
- MIN_OUTBOUND_INTERVAL_S (17.0→更激进?)
- TIER_TIMEOUT_BUDGET_S (111s调整?)
- UPSTREAM_TIMEOUT (58s优化?)

### 执行

```bash
# HM2侧 (opc2_uname远端)
OLD KEY_COOLDOWN_S=26.5
NEW KEY_COOLDOWN_S=30.0 (+3.5s)

docker rm -f hm40006
docker run -d --name hm40006 \
  -e KEY_COOLDOWN_S=30.0 \
  ... (其他所有env保持不变)
```

**验证**: `docker exec hm40006 sh -c 'echo $KEY_COOLDOWN_S'` → `30.0` ✓
**健康检查**: `curl localhost:40006/health` → `{"status":"ok"}` ✓

**铁律遵守**:
- ✅ 只改HM2配置 (hm40006 @ opc2_uname)
- ✅ 不改HM1本地任何配置
- ✅ 不停止/重启/kill mihomo
- ✅ mihomo 运行正常 (curl 7894-7899端口正常)

### 总结

| 项目 | 值 |
|------|-----|
| 变更数量 | 1 |
| 变更参数 | KEY_COOLDOWN_S |
| 旧值 | 26.5s |
| 新值 | 30.0s |
| 幅度 | +3.5s (+13.2% 增加) |
| 影响 | 减少重复429, 增加每key冷却时间 |
| 风险 | 低 — key可用性略降但仍在tier预算内 |

---

## ⏳ 轮到HM2优化HM1