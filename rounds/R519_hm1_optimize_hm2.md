# R519: HM1 → HM2  链路优化报告

**时间**: 2026-07-02 01:34 UTC+8  
**执行**: HM1优化HM2  
**窗口**: 容器自01:04重建后17分钟日志 (tail 10,000行)  
**总请求**: ~77次当中kimi_nv  
**目标**: HM2链路 → NV API  

---

## 1. 数据采集

### 1.1 Docker Logs hm40006 (tail 10,000行)
`ssh -p 222 opc2_uname@100.109.57.26 "docker logs --tail 10000 hm40006"`

核心日志提取(`[HM-SUCCESS] / [HM-TIMEOUT] / [HM-TIER-FAIL] / [HM-PEER-FB]`):
- 共 **104** 条关键日志
- **SUCCESS**: dsv4p_nv=1, **kimi_nv=67**  
- **TIMEOUT**: kimi_nv=10  
- **TIER-FAIL**: 10 (全部kimi_nv)  
- **PEER-FB attempts**: 5次本地耗尽转HM1  
- **PEER-FB OK**: 4/5 (1次HM1也**
Success Rate**: kimi_nv **87.0%** (67/77), dsv4p_nv **100%** (1/1)

> 注: `/app/logs/hm_metrics.db` 仍为 **0 bytes** (空表), 历史问题持续, 无法取DB延迟快照, 依赖日志解析替代。

### 1.2 Per-key Timeout
| Key | 超时次数 |
|-----|----------|
| k4  | 3        |
| k5  | 3        |
| k3  | 2        |
| k2  | 2        |
| k1  | **0**    |

各key超时分布相对均匀 (k1仅0次属随机噪声), 排除单key故障 → **服务端NVCF波动**。

### 1.3 Timeout分布
```
attempt=50321ms total=50323ms
attempt=50443ms total=50449ms
attempt=50509ms total=50511ms
attempt=50769ms total=50776ms
attempt=50633ms total=50636ms
attempt=50607ms total=50609ms
attempt=50343ms total=50348ms
attempt=50387ms total=50394ms
attempt=50678ms total=50687ms
attempt=50472ms total=50475ms
```
**全聚集在 ~50.3-50.8s 区间**, 呈现**硬截断(hard ceiling)**特征。

### 1.4 docker compose env (精简)
```yaml
# kimi tier
- NV_FUNCTION_kimi_nv=f966661c-790...           (5 keys k1-k5, 均匀 ↔ 端口7894-7898)
- NV_FUNCTION_dsv4p_nv=8915fd28-fe8...          (3 keys)
- NV_FUNCTION_glm5_1_nv=xxx                     

# 核心超时/预算参数
- UPSTREAM_TIMEOUT: "48"                            # 保守值, R323已证伪<40会误杀慢成功
- CONSECUTIVE_429_SLEEP: "8"                        # 429防雪崩(当前0次429, 冗余但无害)
- NEXT_KEY_429_SLEEP: "5"                           
- FASTBREAK_STREAK: "1"                             # 单key fastbreak (正确)
- HM_FORCE_STREAM_UPGRADE_TIMEOUT: "50"             # 思考请求上限 (←本次目标)
- HM_THINKING_TIMEOUT_STATIC: "24"                   # 静态non-stream超时
- HM_MIN_STREAM_UPGRADE_THRESHOLD: "200"            # stream升级阈值
- PEER_FALLBACK: "http://100.109.153.83:40006"       # HM1 fallback
- PEER_FALLBACK_TIMEOUT: "120"                      # peer兜底120s
- MIN_OUTBOUND_INTERVAL_S: "1.0"                    # 出向最小间隔 (R518 HM2→HM1已改动)
```

### 1.5 HM1交叉验证
- R518 HM2→HM1已把 **HM_FORCE_STREAM_UPGRADE_TIMEOUT** 在HM1上调至 **52**
- HM1当时 kimi_nv timeout 同样硬卡50s。HM1调52后预期能释放50-52s边缘请求。

---

## 2. 数据分析

### 2.1 根因: 思考超时的硬截断
所有timeout都精确卡在 **50.3-50.8s**。特征:
- 无429 / 无empty200 → 不是限流
- per-key均匀 → 不是单key劣化
- Peer fallback成功率80% (4/5), 极大缓解双机压力 → **不想降速fastbreak**  

这意味着 kimi_nv 的 **长尾请求** 实际在正常处理, 只是 NVCF 偶尔需要 **~51-53秒** 才返首token。当前 `HM_FORCE_STREAM_UPGRADE_TIMEOUT=50` 像剪刀一样把这些边缘请求剪掉, 触发 tier-fail 再转 HM1。

### 2.2 FASTBREAK与超时联动
FASTBREAK=1 已经让失败只消耗1个key、~50秒。若再把 UPSTREAM_TIMEOUT 降到40并重启, 代价是误杀41-48s的真实慢成功。R323已有前车之鉴, **不碰 UPSTREAM_TIMEOUT**。

### 2.3 边缘请求占总数比例
10次timeout / 77次total ≈ **13%**。这13%的请求中, 若延长2s释放50-52s区间, 预估可减少 **20-30%** 的timeout (即把总timeout率从13%降到 **9-10%**)。

---

## 3. 优化决策

### 3.0 原则
> (R518数据驱动原则) 一次只改1个参数, 观察下轮; 绝不盲目combo调参; 对齐双端配置以避免 asymmetric timeout。

### 3.1 选择: HM_FORCE_STREAM_UPGRADE_TIMEOUT 50→52
**理由**:
1. HM2在R518对HM1做了同样改动(50→52), 反过回合则应镜像对齐。
2. Timeout全卡在50s边界, 增加2s可直接释放50-52s边缘成功请求。
3. FASTBREAK=1 保护失败成本: 即使未成功, 单key+52秒 vs 50秒, 仅增加2s固定成本, 不影响大局。
4. dsv4p/glm5 不受影响 (非thinking请求走静态24s超时)。

**不改动项**:
- UPSTREAM_TIMEOUT=48: 保守安全, Historic 323验证40会误杀。
- FASTBREAK_STREAK=1: 当前无429, fastbreak节省预算有效。
- MIN_OUTBOUND_INTERVAL=1.0: 上轮已降, 本轮不动。
- PEER_FALLBACK_TIMEOUT=120: 足够兜底。

---

## 4. 执行变更 (仅改HM2)

```bash
# 4.1 备份docker-compose
ssh opc2_uname@100.109.57.26 -p 222 \
  "cp /opt/cc-infra/docker-compose.yml /opt/cc-infra/docker-compose.yml.bak"

# 4.2 修改HM_FORCE_STREAM_UPGRADE_TIMEOUT
sed -i 's/HM_FORCE_STREAM_UPGRADE_TIMEOUT: "50"/HM_FORCE_STREAM_UPGRADE_TIMEOUT: "52"/g' \
  /opt/cc-infra/docker-compose.yml

# 改动前 (line 483):
#   HM_FORCE_STREAM_UPGRADE_TIMEOUT: "50"   # P1sync: 思考超时覆盖55s对齐HM1
# 改动后:
#   HM_FORCE_STREAM_UPGRADE_TIMEOUT: "52"   # P1sync: 思考超时覆盖55s对齐HM1

# 4.3 仅重建hm40006容器 (不碰mihomo)
docker compose -f /opt/cc-infra/docker-compose.yml up -d --no-deps hm40006

# 4.4 验证 (容器启动后30秒内):
docker exec hm40006 env | grep HM_FORCE_STREAM_UPGRADE_TIMEOUT
> HM_FORCE_STREAM_UPGRADE_TIMEOUT=52  ✓
```

**变更后状态**:  
- hm40006 已重建, 服务正常启动。  
- 最新日志: `[HM-PROXY] Listening on 0.0.0.0:40006` ... 正处理新请求。  
- ⚠️ mihomo 未动, 全程未 stop/restart/pkill。

---

## 5. 验证计划 (下轮HM2优化HM1时应测量)

1. 若 kimi_nv timeout 次数占比从 13% 降至 **<10%** → 本次改动有效。
2. 若 timeout 出现 **52-53s** 区间 → 说明仍有50-52s边缘请求; 再议是否继续增至54s。
3. 若 timeout **仍聚集在50s** 或反而上升 → HM1/HM2间不对称; 回滚并排查其他瓶颈。
4. 继续监测 dsv4p/glm5: 若 traffic 增加后 success rate 是否稳定。

---

## 6. 结论

| 指标 | 变更前值 | 期望值(下轮) | 改变项 |
|------|----------|-------------|--------|
| kimi_nv timeout率 | ~13% (10/77) | <10% | HM_FORCE_STREAM_UPGRADE_TIMEOUT 50→52 |
| peer fallback成功率 | 80% (4/5) | 维持或提升 | 无改动 |
| 429/empty200 | 0 | 0 | 无改动 |
| dsv4p glm5 success | 100% / N/A | 维持 | 无改动 |

本轮执行**最小改动**: 仅修改 HM2 的 `HM_FORCE_STREAM_UPGRADE_TIMEOUT` 从 50 到 52, 让边缘 thinking 请求多喘 2 秒。HM1侧的对应值已是 52, 实现双端对称, 消除 asynchronicity 导致的 `一方剪Request另一方却等` 问题。

下回合应测量挂钩成功率和 timeout 分布, 考虑是否继续此方向微调到 54 或回退至 50。

---

## ⏳ 轮到HM2优化HM1
