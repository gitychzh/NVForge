# R1249 hm2opt: cc4101 模型链路切换 dsv4f0731_nv → glm5_2_nv (HM1)

**时间**: 2026-08-12
**主机**: HM1 (opcsname) — 本机
**范围**: 仅 cc4101 (本机唯一 adapter; opclaw4103/hm4104/oc4105 在 HM2, 本次不改)

## 变更原因

24h DB 数据分析 + 实测对比 dsv4f0731_nv vs glm5_2_nv:
- 两模型 SR 接近 (dsv4f 57.4%, glm5.2 53.7% @72h), 延迟 glm5.2 P50 18.9s vs dsv4f 33.8s
- HM2 实测 glm5.2 中位 TTFB 9-12s vs dsv4f 5-22s (波动大)
- 用户决策: 切 cc4101 到 glm5_2_nv/glm5_2_ms 链路

## 参数变更

| 字段 | 变更前 | 变更后 |
|---|---|---|
| PRIMARY_UPSTREAM_MODEL | dsv4f0731_nv | glm5_2_nv |
| FALLBACK_UPSTREAM_MODEL | dsv4f0731_ms | glm5_2_ms |
| PRIMARY_HEADER_TIMEOUT | 25 (默认) | 55 |
| FALLBACK_HEADER_TIMEOUT | 25 (默认) | 30 |

URL 不变: PRIMARY=nv_gw:40006, FALLBACK=ms_gw:40007

## 验证

| 项 | 结果 |
|---|---|
| env | PRIMARY_UPSTREAM_MODEL=glm5_2_nv, FALLBACK_UPSTREAM_MODEL=glm5_2_ms ✓ |
| 启动日志 | primary: glm5_2_nv, fallback: glm5_2_ms (ms_gw 40007) ✓ |
| E2E stream | HTTP 200, SSE 正常 (thinking + message_stop) ✓ |
| DB 记录 | mapped_model=glm5_2_nv (primary), glm5_2_ms (fallback) ✓ |
| Fallback | primary 不可用时自动切 fallback 200 ✓ |

## 注意

- HM1 直连 NVCF 当前不稳定, glm5_2_nv pexec 频繁超时/502, 大量请求走 fallback
- 备份: /opt/cc-infra/docker-compose.yml.bak.R-glm52-switch.20260812
- 其余 3 adapter (opclaw4103/hm4104/oc4105) 本机不存在, 未改
