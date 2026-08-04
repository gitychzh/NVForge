# R-dsv4f-fb-fix: hm4104+opclaw4103 fallback 改为 nv_gw:40006/glm5_2_nv

**日期**: 2026-08-04
**主机**: HM2

## 摘要

hm4104 (hermes adapter) 和 opclaw4103 (openclaw adapter) 的 fallback 配置不合理:
- hm4104 fallback 指向 ms_gw:40007/glm5_2_ms (独立 ms_gw, 无 mode chain)
- opclaw4103 fallback 指向 dsv4p_nv40066:40066/dsv4p_nv (dsv4p_nv pexec 全 404, 基本无用)

统一改为 nv_gw:40006/glm5_2_nv — 40006 有完整 mode chain + ms_gw 兜底, 比 ms_gw 或 dsv4p_nv 都强。

## 变更

| Adapter | 旧 FALLBACK_URL | 新 FALLBACK_URL | 旧 FALLBACK_MODEL | 新 FALLBACK_MODEL |
|---|---|---|---|---|
| hm4104 | ms_gw:40007/v1 | nv_gw:40006/v1 | glm5_2_ms | glm5_2_nv |
| opclaw4103 | dsv4p_nv40066:40066/v1 | nv_gw:40006/v1 | dsv4p_nv | glm5_2_nv |

hm4104 MS_GW_API_KEY 也从 ms-gw-token 改为 nv-gw-token (fallback 指向 nv_gw 需要 nv-gw-token)。

## 验证

- hm4104 E2E: 200 OK, 11s, model=deepseek-ai/deepseek-v4-flash
- opclaw4103 E2E: 200 OK, 3.2s, model=deepseek-ai/deepseek-v4-flash
- 两 adapter env 确认 FALLBACK_URL=http://nv_gw:40006/v1, FALLBACK_MODEL=glm5_2_nv
