# HM2 Optimize HM1 — Round R1287

## 决策: NOP (False Trigger — 零参数变更, 零容器重启)

### 触发分析

cron 脚本输出: `"这是我提交的, 不触发"` (HM2 opc2_uname 自提交)

- 最新 commit `b23591b R1286` author = opc2_uname (HM2)
- R1286 是 HM2→HM1 真实优化轮 (BUDGET 210→205, MS_GW_FALLBACK_TIMEOUT 200→195)
- cron 再次派遣 agent — false trigger / double-dispatch
- HM1 本地 git log 停留在 R821 (466 轮落后 HM2) — HM1 未提交任何新内容
- 脚本正确检测到 `"这是我提交的, 不触发"` 但 cron 仍被派遣

### 数据收集 (改前必有数据 — SSH stdin pipe)

```
6h_overall: 66 req, 51 OK, 15 fail → 77.3% SR
- 12 zombie_empty_completion (NVCF glm5_2 content-filter stop+~6 output, ~215K input avg)
   → 非配置可修复 — NVCF 端内容过滤, gateway 检测+错误chunk正确
- 3 all_tiers_exhausted (dsv4p_nv, avg 72s, 全 pre-restart 旧容器)
   → 当前容器重启 仅7min, 零 post-restart 流量 → 无可评估新行为
- 1h×7 buckets 均匀 ~2-3 req/h, SR ~66.7% (zombie主导, 非 config-rescueable)

Container: restart 2026-07-13T22:14:51Z (7min), 0 post-restart traffic
           → tier_chain/messages 日志全部空白 (仅 startup)
tier_attempts: 0 rows (zero key cycling in 6h)
ms_gw: healthy — glm5_2 ZHIPUAI OK, dsv4p deepseek OK (MS-STREAM-DONE ×5)
       ms_requests 4/0→0% ms_gw SR (非 ms_gw 故障 — 3 ATE pre-restart 非 ms_gw 路径, 12 zombie content-filter 非 ms_gw)
nv_gw env params: all identical to R1286 state (UPSTREAM=66, BUDGET=205,
  MS_GW_FALLBACK_TIMEOUT=195, FASTBREAK PEXEC=1 INTEGRATE=1 EMPTY=2,
  TIER_COOLDOWN_S=15, TIER_BUDGET dsv4p=72 glm5_2=96 minimax=100,
  KEY_AUTHFAIL=60, CONNECT_RESERVE=0, FORCE_STREAM=0, PEER_FALLBACK_TIMEOUT=66)
Compose md5: 6e1b58bc70eca49e500e3034b08376d9 (stable since R1286 deploy)
```

### 决策理由

1. **False trigger**: cron 派遣基于 HM2 自提交, 非 HM1 新变更
2. **数据同R1286**: 66req/51OK/15fail=77.3% — 与 R1286 部署窗口完全一致
3. **zombie不可修复**: 12× zombie_empty_completion = NVCF glm5_2 内容过滤, gateway 检测正确 → 零参数变更可修复
4. **0 post-restart traffic**: 容器仅重启7min, 无可评估新行为 → 修改参数是盲猜, 违反改前必有数据
5. **全参数最优/floor**: R1286 已精调到 floor (UPSTREAM=66, BUDGET=205, MS_GW_FB=195), 
   FASTBREAK=1/1/2 (R997/R1010/R1031 validated), TIER_BUDGET per-model capping, 
   TIER_COOLDOWN=15 (R1103 revert), KEY_AUTHFAIL=60, PEER_FALLBACK_TIMEOUT=66
6. **ms_gw healthy**: dsv4p_ms (deepseek, 30-372s stream OK), glm5_2_ms (ZHIPUAI, 3-4s OK)
7. **保守: 不改**: BUDGET 205→200 or MS_GW_FB 195→190 进一步压缩 → 
   需要 post-restart real traffic 验证, 非 7min 后零流量盲猜

### 状态快照

| 指标 | 值 | 评估 |
|------|-----|------|
| 6h SR | 77.3% (51/66) | zombie主导 (12/15=80%), 非 config-rescueable |
| Post-restart traffic | 0 | 无法验证任何变化 |
| 0 fallback_occurred | 100% requests direct tier | 零 fallback 触发 = 系统安静 |
| 0 tier_attempts | 零 key cycling | 零 NVCF 超时/429/SSLEOF |
| ms_gw throughput | glm5_2 OK, dsv4p OK | 健康, MS_GW_FALLBACK_TIMEOUT=195 充分 |
| zombie_empty_completion | 12× ~4.7-5.4s fast abort | 非修复: NVCF content-filter, code-level detection ✓ |

**铁律**: 只改 HM1 不改 HM2 | 改前必有数据 | 改后必有验证

## ⏳ 轮到HM1优化HM2
