# R-openclaw-timeout-fix: opclaw4103 timeout 链不匹配致 "Agent couldn't generate a response"

**日期**: 2026-08-03
**主机**: HM2
**容器**: opclaw4103
**状态**: 已部署+验证

## 问题

openclaw 报错 `Agent couldn't generate a response. Note: some tool actions may have already been executed — please verify before retrying.`

## 根因

完整的故障链条：

1. **dsv4p_nv40066 容器在 23:00 被 `docker compose up -d` 重建**（config-hash 变化），重启后 NVCF key 大面积 429 冷却
2. **primary (dsv4p_nv40066) 连续返回 content_filter zombie + all_tiers_exhausted** → circuit breaker 累积 5 次故障 → OPEN
3. **fallback (nv_gw:40006/glm5_2_nv) 也遇到 502**（zombie_empty_completion + all_tiers_exhausted + NVStream_IncompleteRead）
4. **关键矛盾：timeout 链不匹配**
   - openclaw `timeoutSeconds=180` (客户端 180s 后断开)
   - opclaw4103 `PROXY_TIMEOUT=240` (adapter 240s 才放弃)
   - `PRIMARY_HEADER_TIMEOUT=180` + `FALLBACK_HEADER_TIMEOUT=180` = 360s 叠加
   - `FALLBACK_RECOVER_S=120` — circuit OPEN 后 2 分钟内全部直走 fallback，如果 fallback 也 sick 就全死
5. **结果**：adapter 还在 fallback retry 循环中（175s），openclaw 180s timeout 已到 → `fetch timeout` → `LLM request timed out` → "Agent couldn't generate a response"

## 修复

opclaw4103 adapter 的 timeout 参数调整，确保 adapter 总耗时 < openclaw 180s timeout：

| 参数 | 旧值 | 新值 | 理由 |
|---|---|---|---|
| `PROXY_TIMEOUT` | 240 | **170** | 必须 < openclaw 180s timeout |
| `PRIMARY_HEADER_TIMEOUT` | 180 | **90** | 90s 覆盖 dsv4p_nv p90 TTFB(~15s) + thinking |
| `FALLBACK_HEADER_TIMEOUT` | 180 | **70** | primary 90s + fallback 70s = 160s < 170s |
| `CC4101_TOTAL_BUDGET_S` | 400 | **170** | 必须在 PROXY_TIMEOUT 内 |
| `FALLBACK_RECOVER_S` | 120 | **30** | 避免 2min 全跳 primary 死区 |
| `FALLBACK_TIMEOUT_S` | 240 | **170** | 对齐 PROXY_TIMEOUT |

**timeout 链**：primary(90s) + fallback(70s) = 160s < PROXY_TIMEOUT(170s) < openclaw timeout(180s)

## 数据

### 修复前 (30 min window, 22:38-23:08)
- dsv4p_nv: 200=36, 502=16, 429=1, **SR=67.9%**
- glm5_2_nv: 200=31, 502=27, **SR=53.4%**
- 错误类型: zombie_empty_completion=25, all_tiers_exhausted=11, buffer_exhausted=3, NVStream_IncompleteRead=3

### 修复后 (23:22+)
- dsv4p_nv: 4/4 200 成功, avg 54s
- 无 timeout, 无 fallback 触发, 无 zombie

## 验证

1. E2E 流式: ✅ dsv4p_nv 返回正常 SSE 流
2. E2E 非流式: ✅ dsv4p_nv 返回正常 chat completion
3. health: ✅ `proxy_timeout=170s`
4. DB 查询: ✅ 修复后 4/4 全 200

## 回滚

```bash
# HM2
cd /opt/cc-infra
cp docker-compose.yml.bak.Ropenclaw_timeout docker-compose.yml
docker compose up -d opclaw4103
```
