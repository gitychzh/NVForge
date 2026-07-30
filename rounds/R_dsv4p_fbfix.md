# R-dsv4p-fbfix: adapter fallback 恢复 — FALLBACK_URL=none→ms_gw

**Date**: 2026-07-30  
**Host**: HM2 (100.109.57.26)  
**Scope**: docker-compose.yml 2 处

## 根因

R-dsv4p-deploy 把 hm4104+opclaw4103 切到 dsv4p_nv 后, NVCF dsv4p 后端间歇故障
(429 账户级限流 + SSLEOFError + RemoteDisconnected) 导致 5 key 全被 KeyManager
cooldown (120s→240s→480s→600s 指数退避). 全挂后 nv_gw all_keys_exhausted → 502.

adapter 层 FALLBACK_URL=none (R-glm52-pure 时期故意禁用 ms_gw fallback),
primary 502 后 fallback 连 "none" → ConnectionRefusedError →
**"⚠️ primary 和 fallback 均不可用, 请稍后重试"** → hermes + openclaw 全挂.

## 变更

### docker-compose.yml (HM2)
- hm4104 (L350): `FALLBACK_URL=none` → `http://ms_gw:40007/v1` (FALLBACK_MODEL=dsv4p_ms 已对)
- opclaw4103 (L307): `FALLBACK_URL=none` → `http://ms_gw:40007/v1`
- opclaw4103 (L308): `FALLBACK_MODEL=glm5_2_ms` → `dsv4p_ms`
- backup: `docker-compose.yml.bak.R-dsv4p-fb`

## 验证

| 测试 | HTTP | 延迟 | 路径 | 结果 |
|---|---|---|---|---|
| hm4104 curl | 200 | 4.5s | fallback→dsv4p_ms ✓ | ms_gw 兜底成功 |
| opclaw4103 curl | 200 | 18.2s | primary→dsv4p_nv ✓ | nv_gw primary 成功 |
| hermes agent | — | — | — | "你好！有什么" ✓ |
| openclaw agent | — | — | dsv4p_nv, fallback=false | status=ok ✓ |

## 效果

NVCF 间歇故障时, adapter 不再双挂, ms_gw dsv4p_ms 兜底成功.
hermes + openclaw 不再报 "primary 和 fallback 均不可用".

## 回滚
- `docker-compose.yml.bak.R-dsv4p-fb` → `docker compose up -d hm4104 opclaw4103`
