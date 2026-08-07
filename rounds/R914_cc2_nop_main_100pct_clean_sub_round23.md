# R914 — cc2 NOP 巡检轮 (23rd consecutive clean, R892-R914)

> 日期: 2026-08-07 ~09:32 CST
> 判定: **NOP 不改码** — cc2 主链路 100% SR 干净, 无新错误类; 所有 bad 请求全属 hermes 线。

## 判定依据

### 30min 链路总览 (caller × model × status)
```
cc4101-primary|dsv4f0731_nv|200|119     ← cc2 主链 119/119 全 200
hermes|dsv4f0731_nv|200|10
hermes|dsv4f0731_nv|502|4               ← 4 bad 全属 hermes
```

### cc2 主链 (caller=cc4101-primary) 专属
```
200|119  → 100% SR, 0 bad (status!=200 实查 = 0 条)
```

### 30min 错误分类 (只属 hermes)
```
hermes|stream_absolute_cap|2  (avg_dur 155678ms)
hermes|all_tiers_exhausted|2  (avg_dur 180053ms)
```
- 2 bad 类型 (all_tiers_exhausted/stream_absolute_cap) 均为 hermes 线长尾失败, 与 R892-R913 同源。
- JOIN 铁证 (前几轮持续): 这些 bad request_id 全属 hermes 宿主, **0 进 cc2 主链候选池**。

### fallback
```
0 / 1544  (cc_requests 实算 fb 触发 = 0 次)
```

### per-key tier 分布 (nv_tier_attempts, 主链吸收瞬态)
- pexec_success 每 key 23-24, 占绝对主导。
- 瞬态错误 (NVCFPexecRemoteDisconnected 2-5/key, 529_nv_overloaded 1-2, NVCFPexecTimeout 1):
  正常 NVCF 底层抖动, 被多 tier round-robin + func_health 健康选择吸收, 未导致主链失败。

### 容器健康
```
4101:200  40006:200  40066:200
nv_gw /health: proxy_role=passthrough, 5 keys, nvcf_pexec_models=[kimi_nv,dsv4p_nv,dsv4f_nv,dsv4f0731_nv,glm5_2_nv]
```

## 改动
无 (NOP)。主链 SR=100% 无优化需求, bad 全属 hermes 越 cc2 范围, 无新错误类。

## 下一步
- 续 NOP 巡检。重点盯: ①hermes 线 all_tiers_exhausted/stream_absolute_cap 是否会跨 host 泄漏进 cc2
  (延续 JIN 铁证); ②nv_gw 底层 NVCF 瞬态错误率若持续上升, 评估 func_health/多 tier 是否需微调。
- 保持 fallback 0 次 (>5% 阈值远未触碰)。

## 参数快照 (nv_gw / cc4101)
- nv_gw.UPSTREAM_TIMEOUT=90 | TIER_TIMEOUT_BUDGET_S=180 | NVU_DISABLE_MS_FALLBACK=0
- nv_gw.TIER_COOLDOWN_S=180 | KEY_COOLDOWN_S=30 | NV_INTEGRATE_KEY_COOLDOWN_S=90
- nv_gw.NVU_FORCE_STREAM_UPGRADE=0 | MIN_OUTBOUND_INTERVAL_S=10 | NVU_BUFFER_CALLERS=cc4101-primary,openclaw2
- cc4101.PRIMARY_UPSTREAM_MODEL=dsv4f0731_nv | PRIMARY_UPSTREAM_URL=http://nv_gw:40006/v1/messages
- cc4101.FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/chat/completions | CC4101_STREAM_TOTAL_DEADLINE_S=470
- cc4101.PRIMARY_HEADER_TIMEOUT=400 | CC4101_PRIMARY_FAIL_THRESHOLD=3 | CC4101_PRIMARY_SKIP_S=30