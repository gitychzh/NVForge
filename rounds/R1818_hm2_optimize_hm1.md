# R1818 (HM2→HM1): kimi_nv peer-fb skip — 节省 ~700ms/ATE failure path

## 数据来源 (HM1 DB, 6h window)

```
total: 29 req, 25 OK (86.2% SR), 4 fail
  glm5_2_nv: 24/24 OK (100% SR), avg=10370ms, 100% key_cycle_429s (24/24)
  kimi_nv:   0/4 OK (0% SR), 4 ATE
  dsv4p_nv:  1/1 OK (100% SR), 2391ms
```

## 问题分析

4 kimi ATE 全部 NVCF function-level degradation（外部 NVCF 降级）：
- 第1个请求：tier 尝试 1715ms 后 ATE，peer-fb 到 HM2 失败（~700ms），返回 502
- 后续 3 个请求：DEGRADED cooldown 短接（1ms），但 peer-fb 仍被尝试——每次都失败
- 根因：两台主机使用相同的 NVCF KIMI function ID `f966661c`，HM2 也无法成功
- 每次 peer-fb 尝试浪费 ~700ms（连接建立 + 超时等待）

**peer-fb 对 kimi_nv 结构性无效**：同一 function 在 NVCF 侧同时降级，两机均无法成功。

## 优化方案

`NVU_PEER_FB_SKIP_MODELS` 从 `""` 改为 `"kimi_nv"`：
- 节省每 ATE ~700ms failure path
- 不影响 dsv4p_nv 的 peer-fb（dsv4p_nv 不在 SKIP 列表）
- 不影响 glm5_2_nv（100% SR 无 ATE）
- 单参数，只改 HM1

## 验证

- 容器重启后，未来 kimi ATE 不再尝试 peer-fb
- 旧行为：`[NV-PEER-FB] local all_tiers_exhausted (model=kimi_nv), attempting peer fallback to ...`
- 新行为：kimi ATE 直接返回 502，无 peer-fb 尝试

## 预算验证

```
TIER_BUDGET kimi: 无独立 BUDGET (使用全局 TIER_TIMEOUT_BUDGET_S=180)
SKIP 后: 180s < 195s ✓（无 peer-fb 延长，总路径更短）
```

铁律：只改HM1不改HM2
## ⏳ 轮到HM1优化HM2
