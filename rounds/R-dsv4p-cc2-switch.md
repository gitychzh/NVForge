# R-dsv4p-cc2: cc4101 primary glm5_2_nv → dsv4p_nv 切换 + E2E 验证

**日期**: 2026-08-02  
**主机**: HM2 (opc2sname)  
**目标**: cc2 模型链路切换到 cc4101→40006(dsv4p_nv), 端到端测试稳定性

## 背景数据 (改前必有数据)

### 近 6h nv_gw 模型 SR 对比 (HM2)
| model | total | success | SR% | avg_ms |
|---|---|---|---|---|
| dsv4p_nv | 177 | 124 | 70.1 | 8751 |
| glm5_2_nv | 10 | 10 | 100.0 | 152281 |

- dsv4p_nv 429 风暴: 51 次 429 + 2 次 502, 间歇性 NVCF 账户级限流
- glm5_2_nv 100% 成功但 avg 152s (thinking 长请求)
- R-nvonly-post15 (08-01) 从 dsv4p_nv 回滚到 glm5_2_nv 的注释仍在 compose 中

### dsv4p_nv 429 风暴根因
- 5 key 全走 pexec SOCKS5 (7900-7904), 5 个美国出口 IP
- NVCF 账户级限流 (非 IP 级): 持续流量触发全 key 429 → TIER_COOLDOWN 180s
- 冷却恢复后单次探测可成功, 但持续流量 ~70% SR
- cc4101→nv_gw buffer 系统: 5 key 全 429 时 165s 超时 → 502 buffer_exhausted

## 变更

### docker-compose.yml cc4101 env
```diff
- PRIMARY_UPSTREAM_MODEL=glm5_2_nv  # R-nvonly-post15: dsv4p_nv→glm5_2_nv 应急回滚
+ PRIMARY_UPSTREAM_MODEL=dsv4p_nv  # R-dsv4p-cc2: switch back. 429 storm subsided. glm5_2_nv avg 152s too slow.
```

备份: `docker-compose.yml.bak.R-dsv4p-cc2`

## 探测验证 (改后必有验证)

### dsv4p_nv 直连 nv_gw 40006 (5x)
| # | HTTP | Time |
|---|---|---|
| 1 | 200 | 1.86s |
| 2 | 200 | 9.12s |
| 3 | 200 | 7.91s |
| 4 | 200 | 11.21s |
| 5 | 200 | 4.36s |
**SR: 5/5 = 100%**

### glm5_2_nv 直连 nv_gw 40006 (5x, 对比)
| # | HTTP | Time |
|---|---|---|
| 1 | 200 | 3.63s |
| 2 | 200 | 13.80s |
| 3 | 200 | 10.92s |
| 4 | 200 | 8.00s |
| 5 | 200 | 11.96s |
**SR: 5/5 = 100%**

### E2E cc4101→nv_gw→dsv4p_nv (cc-glm5-2 model, 5x)
| # | HTTP | Time |
|---|---|---|
| 1 | 200 | 2.03s |
| 2 | 200 | 1.77s |
| 3 | 200 | 1.66s |
| 4 | 200 | 1.77s |
| 5 | 200 | 1.70s |
**SR: 5/5 = 100%**

### E2E cc4101→nv_gw→dsv4p_nv (glm5.2_cc model, 实际 cc2 model 名)
- 200, 1.42s — 返回 "Paris" 正确

### 大请求 E2E (500 tokens, Python palindrome 函数)
- 200, 7.68s — 代码内容完整正确

## 429 风暴期间的 cc4101 失败记录
- 在 429 风暴窗口 (06:26-06:30 UTC): cc4101→nv_gw→dsv4p_nv 5 key 全 429 → 165s buffer_exhausted → 502
- nv_gw 日志: `all_keys_exhausted=True`, `NV-GLOBAL-COOLDOWN tier=dsv4p_nv all keys 429, 180s`
- 这是 dsv4p_nv 的已知间歇性问题, 非本次变更引入

## 链路确认
```
cc2 (settings.json)
  → ANTHROPIC_BASE_URL=http://127.0.0.1:4101
  → ANTHROPIC_API_KEY=cc4101-token
  → model=glm5.2_cc
  → cc4101 (MODEL_MAP fallback → PRIMARY_UPSTREAM_MODEL=dsv4p_nv)
  → nv_gw:40006/v1/messages (Authorization: Bearer nv-gw-token)
  → NVCF pexec (deepseek-ai/deepseek-v4-pro, func=12acbc62-3a9...)
  → per-key SOCKS5 7900-7904 → 5 美国 IP
```

## 风险评估
- dsv4p_nv 间歇 429 风暴: 持续流量 SR ~70%, 冷却恢复后 100%
- cc4101 fallback 仍指向 ms_gw/glm5_2_ms: 429 风暴时 fallback 兜底
- glm5_2_nv avg 152s 对 cc2 太慢, dsv4p_nv avg 8.7s 更适合 cc2 交互场景
- 需持续监控: 若 429 风暴频率过高, 可考虑切回 glm5_2_nv 或调整 KEY_COOLDOWN

## 验证 checklist
- [x] cc4101 env: PRIMARY_UPSTREAM_MODEL=dsv4p_nv ✓
- [x] nv_gw /health: ok, 5 keys, dsv4p_nv in pexec_models ✓
- [x] 直连探测 5/5 成功 ✓
- [x] E2E cc4101→nv_gw→dsv4p_nv 5/5 成功 ✓
- [x] glm5.2_cc model 名正确映射 ✓
- [x] 大请求内容完整 ✓
- [x] cc2 settings.json 已指向 cc4101 ✓
- [x] docker-compose.yml 备份 ✓
