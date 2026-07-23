# R2303 (HM2 only): opclaw4103 PRIMARY_HEADER_TIMEOUT 25→180s — 修"主备均不可用"

> 用户报: openclaw {⚠️ primary 和 fallback 均不可用}. opclaw4103 根本没流量(每请求 25s 秒断切 fallback).

## 改前数据 (opclaw4103 日志 + nv_requests 近 30min)

### opclaw4103 日志 (改前) — 每请求 25s 秒断
```
22:43:59 REQ model=glm5_2_nv stream=True
22:44:24 PRIMARY-FAIL-STREAM nv_gw 流式 timeout status=0 after 25026ms, 切 fallback: header/ttfb timeout after 25.0s: timed out
22:44:26 FALLBACK-STREAM 从 primary 切到 ms_gw
...
23:05:21 PRIMARY-FAIL-STREAM ... after 25026ms ... 25.0s: timed out
00:02:36 PRIMARY-FAIL-STREAM ... 25.0s: timed out
00:03:06 FALLBACK-FAIL-STREAM ms_gw 流式 timeout ... 30.0s: timed out  ← 主备均不可用
```

### 根因
opclaw4103 用 cc-adapter 同款代码 (config.py L11), PRIMARY_HEADER_TIMEOUT 代码默认 **25s** (compose 未设此 env).
config.py L38 注释: "primary 25s 覆盖 p90 TTFB (实测 3-14s, thinking 最慢 71s 由 idle 兜底)" — 基于**旧 TTFB 3-14s**.
但 glm5.2 恢复后 (R2293 切回 glm5_2_nv) integrate TTFB 大幅回升:
- 近 30min caller=other (openclaw 类) glm5_2_nv: **avg TTFB 73.1s, max 159.9s**, 16/17 最终 200 成功
- 73-160s TTFB 全部远超 25s → opclaw4103 每请求 25s 必 fail 切 fallback → ms_gw 也 30s 超时 → "主备均不可用"

### 为何 cc4101 不受影响
cc4101 有 R2154 六档动态 header_timeout (按 input chars), glm5_2_nv 大请求档 150-180s. opclaw4103 从未被同步这套, 仍是固定 25s.

## 改动 (HM2 only, 单 env)
`/opt/cc-infra/docker-compose.yml` opclaw4103 段 (备份 `.bak.R2303`):
opclaw4103 段 `PRIMARY_STREAM_TIMEOUT_S=90` 行后新增:
```
- PRIMARY_HEADER_TIMEOUT=180  # R2303: 代码默认25s 基于旧TTFB3-14s, glm5.2恢复后TTFB avg73s/max160s, 25s必fail. 180s对齐cc4101大请求档.
```
`docker compose up -d opclaw4103` (env 改, 无需 build). 验证 env 生效: `docker exec opclaw4103 env | grep PRIMARY_HEADER` → 180.

## 验证
- 改后 opclaw4103 日志 25s "header/ttfb timeout after 25.0s" = 0 (改前每请求必现)
- 测试请求 (stream=False max_tokens=50): opclaw4103 不再 25s 秒断, 等到 nv_gw 返回 (nv_gw 端 status=200, ttfb=130s, 130<180 不再误杀)
- 注: 个别请求仍走 fallback (glm5_2_ms) — 非 25s 秒断, 是 nv_gw 返回非 200 或 body read 阶段超时, 另一独立问题, 不属本轮

## 回滚
`cp /opt/cc-infra/docker-compose.yml.bak.R2303 /opt/cc-infra/docker-compose.yml && docker compose up -d opclaw4103`

## 关联
- 铁律: 改前有数据(日志+TTFB实测), 改后有验证(25s fail 归零), 聚焦 40006 下游 adapter(opclaw4103 指 nv_gw), 只改 HM2, 写入仓库.
- R2154 cc4101 六档动态 header_timeout 未同步到 opclaw4103, 本轮用固定 180s 兜底 (opclaw4103 流量单一 glm5_2_nv, 无需六档).
