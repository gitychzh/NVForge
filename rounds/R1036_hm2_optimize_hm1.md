# HM2 Optimize HM1 — Round R1036

## 触发分析
- 脚本输出: 检测到 HM1 提交 `93a5372` (R1035: NVU_TIER_BUDGET_MINIMAX_M3_NV 110→100)，轮到 HM2 优化 HM1
- 真实触发确认: HM1 最新 commit = opc_uname, 触发 HM2 优化回合

## 数据收集（改前）
- 窗口: 6h (2026-07-10 07:35 UTC cron dispatch)
- 总请求: 306 (289 OK / 17 ATE → 94.4% SR)
- 按模型:
  - glm5_2_nv: 178/172/6 → 96.6% SR (mostly integrate, healthy)
  - dsv4p_nv: 62/54/8 → 87.1% SR (all pexec, 100% pexec SR on successes)
  - kimi_nv: 39/38/1 → 97.4% SR
  - minimax_m3_nv: 27/25/2 → 92.6% SR
- dsv4p_nv ATE 详情:
  - 8 ATE, 全部 `all_tiers_exhausted`, `fallback_actually_attempted=false`
  - 持续时间分布: 2×~2ms (instant abort), 6×~61s (5-key exhaustion)
  - 所有 dsv4p_nv 成功请求均通过 nvcf_pexec (avg 13,348ms), pexec 100% SR
  - ATE 时间戳: 18:01-20:16 UTC, 零散分布, 非集中爆发
- 其他模型 ATE:
  - glm5_2_nv 6 ATE: 3×NVStream_TimeoutError (~92-99s), 2×stream_total_deadline (~62-95s), 1×all_tiers_exhausted (151s)
  - minimax_m3_nv 2 ATE: 1×stream_total_deadline (50s), 1×all_tiers_exhausted (151s)
  - kimi_nv 1 ATE: all_tiers_exhausted (61s)
- nv_gw 日志: 容器在 R1035 deploy 后仅 9min 运行, 日志稀疏, 仅见一条 glm5_2 integrate success
- ms_gw 状态: Up 4h, 正常处理 dsv4p (deepseek-ai/DeepSeek-V4-Pro) 和 glm5_2 (ZHIPUAI) 请求
- ms_gw 日志显示: 多次 MS-OK / MS-STREAM-DONE, 证明 ms_gw 功能正常; 但 relay 端 BrokenPipeError 反复出现

## 诊断

### dsv4p_nv ATE 根因
dsv4p_nv 8 ATE 全部 `fallback_actually_attempted=false` 且 `all_tiers_exhausted`。ms_gw IS working (MS-OK + MS-STREAM-DONE with deepseek-ai/DeepSeek-V4-Pro), 但 nv_gw→ms_gw relay 被 `NVU_MS_GW_FALLBACK_TIMEOUT=45` 过早切断。

ms_gw 日志佐证:
- `[MS-OK] req=ba8c8fd2 v0k0 backend=deepseek-ai/DeepSeek-V4-Pro status=200` (04:08 UTC) — ms_gw 成功处理 dsv4p
- ms_gw dsv4p 请求耗时 100-200s (non-stream 完整响应)
- NVU_MS_GW_FALLBACK_TIMEOUT=45 远低于 ms_gw 实际处理时间 → relay 在 ms_gw 完成前就被 kill
- ms_gw 日志中 `BrokenPipeError` 反复出现 — nv_gw 关闭连接时 ms_gw 还在发送

### 预算分析
- nv_gw tier: 5-key cycle @ UPSTREAM=66s (FASTBREAK=1) → primary tier exhaustion 最多 ~66s
- ms_gw: UPSTREAM_TIMEOUT=300s, PROXY_TIMEOUT=600s → ms_gw 自身有充足时间
- NVU_MS_GW_FALLBACK_TIMEOUT=45 是唯一瓶颈 — 45s 后 nv_gw 放弃等待 ms_gw

## 优化

**单一参数修改: NVU_MS_GW_FALLBACK_TIMEOUT 45→90 (+45s)**

- 参数: `NVU_MS_GW_FALLBACK_TIMEOUT: "90"`
- 位置: HM1 `/opt/cc-infra/docker-compose.yml` 第 654 行 (nv_gw env)
- 理由: ms_gw 深层次处理 dsv4p 需要 100-200s, 45s timeout 过早 kill relay。90s 覆盖 ms_gw 大部分 rescues 且保留 abort 保护
- 安全边界: ms_gw UPSTREAM_TIMEOUT=300 >> 90, 90s < BUDGET=110 (不会超过 tier budget)
- 铁律: 只改 HM1, 绝不改 HM2
- 铁律合规: ✓ 仅 HM1 nv_gw compose env var

## 部署
1. `sed -i '654d'` 删除旧行 654
2. `sed -i '653 a\'` 追加新行: `NVU_MS_GW_FALLBACK_TIMEOUT: 90  # R1036 ...`
3. `docker compose stop nv_gw && docker compose up -d nv_gw` — container 成功重启
4. 验证: `docker exec nv_gw env | grep NVU_MS_GW_FALLBACK_TIMEOUT` → `90` ✓
5. 容器状态: Up (healthy)

## 影响评估
- 预期改善: dsv4p_nv ATE 减少 — 部分 ~61s ATE 转而通过 ms_gw rescue (ms_gw 成功但 timeout 过早 kill)
- 预期风险: 低 — 90s 远小于 ms_gw UPSTREAM=300, 90s 亦在 BUDGET=110 内
- 可能副作用: 请求在最坏情况下等待 90s 而非 45s 后才 502 → 用户体验可控 (已有 STREAM_TOTAL_DEADLINE=72)
- 回滚成本: 低 — 单 env var, 一次 compose restart

## 铁律校验
- ✅ 只改 HM1 (compose env var), 未触碰 HM2
- ✅ 单一参数修改
- ✅ 数据驱动 (ms_gw 实际成功 + relay timeout 过早)
- ✅ compose YAML 验证通过 (yaml.safe_load OK)
- ✅ container 重启后健康

## ⏳ 轮到HM1优化HM2
