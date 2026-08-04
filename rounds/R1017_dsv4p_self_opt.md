# R1017: 529 风暴第 8 轮 — 回退 k5 integrate lane (integrate 劣于 pexec)

> 时间: 2026-08-05 05:35 BJT (21:35 UTC)
> 容器: dsvf0731_nv40666 (端口 40666, HM2, DeepSeek V4 via NVCF)
> 状态: **改参数** — revert R1015 `NV_KEY_INTEGRATE_KEYS=dsv4f0731_nv:5` → 空 (全走 pexec DIRECT)
> Fallback: hm4104 持续 fallback 到 dsv4f0731_ms (primary 502/超时触发)

## 1. 背景 (改前必有数据)

R1015 为 dsv4f0731_nv 启用了 k5 integrate 通路 (R838B per-key lane), 期望 integrate 提供
第二条独立 NVCF 路径。R1016 是观察轮 (integrate 样本不足 2/2)。本轮已凑足 6h 数据,
**可对 integrate vs pexec 做出数据支撑的判定**。

### DB 6h 窗口 (mapped_model=dsv4f0731_nv) — 决定性对比

| upstream | total | ok | SR | avg_ms |
|----------|-------|----|-----|--------|
| nvcf_pexec | 190 | 134 | **70.5%** | 34053 |
| nv_integrate | 6 | 3 | **50.0%** | 28305 |

### 30min 窗口 (注入 context)
- 总量 12, 200=4, **SR=33.3%**
- 错误: all_tiers_exhausted=5, **NVStream_IncompleteRead=3**
- upstream: nvcf_pexec 9 (200=4, SR=44%), **nv_integrate 3 (200=0, SR=0%)**
- **NVStream_IncompleteRead=3 全落在 integrate 通路 (k4)** — 流被上游截断
- 429: 0, key_cycle_429s: k0=10

### 2h tier_attempts (tier=dsv4f0731_nv)
- **529_nv_overloaded: 222** (账户级过载风暴持续第 8 轮)
- NVCFPexecRemoteDisconnected: 38
- **529_integrate_overloaded: 5** — integrate 端同样过载
- empty_200: 2, NVCFPexecTimeout: 1

## 2. 决策: 回退 integrate lane (NV_KEY_INTEGRATE_KEYS → 空)

**compose env 变更** (docker-compose.yml 该服务):
```
前: - NV_KEY_INTEGRATE_KEYS=dsv4f0731_nv:5   # R1015 k5 integrate 通路
后: - NV_KEY_INTEGRATE_KEYS=                 # 全走 pexec DIRECT
```

**理由:**
1. **6h 数据反证 R1015 假设**: integrate 50% SR (3/6) **低于** pexec 70.5% (134/190)。
   R1015 基于 dsv4f_nv 的 69.6% integrate SR 推断, 但 dsv4f0731_nv 实测 integrate 并无优势。
2. **integrate 当前 100% 失败**: 30min 内 integrate 3/3 全 502, 且 NVStream_IncompleteRead=3
   全集中在 integrate 通路 — 该 lane 在风暴期是纯负贡献。
3. **integrate 端同样过载**: 529_integrate_overloaded=5/2h — 账户级 NVCF 过载同时影响
   pexec 与 integrate, integrate 非银弹。
4. **与兄弟容器一致**: nv_gw (R2057) 与旧 dsv4f (R1006) 均已清空 integrate — 本容器
   revert 恢复一致性, 全 5-key 走 pexec DIRECT。
5. **恢复 5-key 池**: R1015 使 k5 常走 integrate, 5-key pexec 池实质 4-key。revert 后
   恢复满 5-key pexec 冗余。

## 3. 部署与验证

- [x] `docker compose up -d dsvf0731_nv40666 --no-deps` (Recreate)
- [x] env 生效: `NV_KEY_INTEGRATE_KEYS=` (空)
- [x] /health: status OK, 5 keys, tiers 含 dsv4f0731_nv
- [x] 容器 Up (未重启 mihomo)
- [x] mihomo 端口 7894-7897 全部 listening (recreate 未破坏代理)

## 4. 当前状态 (30min 主指标, 改前)

- 30min SR: **33.3%** (4/12, 风暴窗口低谷)
- Avg/P50/P95: 63061ms / 65089ms / 118667ms
- 错误: all_tiers_exhausted=5, NVStream_IncompleteRead=3
- 429: 0, key_cycle_429s: k0=10
- upstream: pexec 9/200=44%, integrate 3/200=0%
- fallback: hm4104 持续 fallback 到 ms_gw (primary 502/超时触发)

## 5. 上次修改效果 (R1015 integrate lane)

- **revert 判定**: integrate 6h SR=50% 明确劣于 pexec 70.5% — R1015 假设不成立
- 30min integrate 0% SR + NVStream_IncompleteRead 集中于 integrate → 该 lane 在风暴期
  是纯负贡献, 移除正确
- **529 风暴持续第 8 轮未收敛** (222/2h) — 账户级过载, 本容器可调参数已达优化极限

## 6. 下一步建议

1. **观察 revert 后一整窗** — 确认 pexec-only 5-key 池 SR 是否回升 (预期 ≥ 风暴期
   integrate-enabled 状态)。
2. **529 风暴持续第 8 轮** — 账户级过载, 精确优先级不变:
   额外 NVCF key / 不同 egress IP 池 / 换 NVCF function_id。本容器可调参数已无用武之地。
3. **监控 NVStream_IncompleteRead** — revert 后应消失 (该错误此前集中于 integrate)。
4. **若 hm4104 持续 fallback** — 说明上游持续不可用, 需评估 dsv4f0731_nv 依赖过重问题。