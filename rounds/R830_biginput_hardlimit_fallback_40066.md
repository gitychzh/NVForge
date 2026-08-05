# R830: glm5_2_nv 大请求硬限制 + fallback 全链切 40066 dsv4p_nv

## 摘要

两处变更:
1. **buffer_stream.py (40006)**: glm5_2_nv input_chars >180K 时跳过 NVCF 重试直走 fallback (NVCF 200K 硬限制注定失败, 节省 5×90s=450s 无谓重试)
2. **docker-compose.yml**: cc4101 + nv_gw 40006 的 fallback 从 ms_gw:40007 (glm5_2_ms) 切到 dsvf0731_nv40666:40666 (dsv4p_nv)

## 数据 (改前)

- glm5_2_nv >200K input: SR=36.4% (4/11), 主要错误 buffer_exhausted(5)+all_tiers_exhausted(2)
- dsv4f0731_nv >200K input: SR=72.7% (8/11) — 1M context 不受 NVCF 200K 限制
- 大请求失败耗时 ~465s (5 次 buffer 重试全败)
- cc4101 转换缩减 input ~75% (306K cc→64-84K nv), 但压缩触发前的最后一个请求可能仍超限

## 变更

### 1. buffer_stream.py — input 硬限制

文件: `/opt/cc-infra/proxy/nv-gw/gateway/buffer_stream.py`
备份: `buffer_stream.py.bak.R830`

在 `run()` 方法中, NV-BUFFER-START 日志后、R828 breaker 检查前, 新增:

```python
# R830: glm5_2_nv 大请求硬限制 — NVCF 200K context 限制注定失败, 直接 fallback 不浪费 5×90s=450s
if self.request_model == "glm5_2_nv":
    _input_chars = self.metrics.get("total_input_chars", 0)
    if _input_chars > 180000:
        _log("NV-BUFFER-INPUT-OVER-LIMIT", ...)
        _ms_result = self._try_ms_gw_fallback()
        if _ms_result: return True  # fallback 成功
        # fallback 失败 → 落到 NVCF 重试 (保底)
```

逻辑与 R828 breaker OPEN 完全对称, 复用 `_try_ms_gw_fallback()` 路径。

### 2. docker-compose.yml — fallback 切 40066

| 变量 | 旧值 (ms_gw) | 新值 (40066) |
|---|---|---|
| cc4101 FALLBACK_UPSTREAM_URL | http://ms_gw:40007/v1/messages | http://dsvf0731_nv40666:40666/v1/messages |
| cc4101 FALLBACK_UPSTREAM_TOKEN | ms-gw-token | nv-gw-token |
| cc4101 FALLBACK_UPSTREAM_MODEL | glm5_2_ms | dsv4p_nv |
| nv_gw NVU_MS_FALLBACK_URL | http://ms_gw:40007/v1/chat/completions | http://dsvf0731_nv40666:40666/v1/chat/completions |
| nv_gw NVU_MS_FALLBACK_TOKEN | ms-gw-token | nv-gw-token |
| nv_gw NVU_MS_FALLBACK_MODEL | glm5_2_ms | dsv4p_nv |

40066 已配置 `NVU_BUFFER_CALLERS=cc4101-fallback` (R-cc-slow-fix), 会 buffer cc4101-fallback caller 的请求做 5-key 重试。

## 参数表

| 参数 | 值 | 位置 |
|---|---|---|
| glm5_2_nv input hard limit | 180000 chars | buffer_stream.py run() |
| cc4101 fallback URL | dsvf0731_nv40666:40666/v1/messages | docker-compose.yml |
| cc4101 fallback model | dsv4p_nv | docker-compose.yml |
| nv_gw ms_fallback URL | dsvf0731_nv40666:40666/v1/chat/completions | docker-compose.yml |
| nv_gw ms_fallback model | dsv4p_nv | docker-compose.yml |

## 预期效果

- glm5_2_nv >180K input 请求: 失败从 ~465s → <5s (直接 fallback 40066 dsv4p_nv)
- 40066 dsv4p_nv 1M context, 不受 NVCF 200K 限制
- ms_gw:40007 不再被 cc4101 或 nv_gw 40006 作为 fallback 目标
- NV-only 统计: fallback 到 40066 仍走 NVCF (dsv4p_nv), 计入 NV 成功

## 验证

- [x] buffer_stream.py 语法 OK (ast.parse)
- [x] docker compose up -d nv_gw cc4101 成功
- [x] 40006/40066/4101 health 全 ok
- [x] cc4101 env: FALLBACK_UPSTREAM_URL=dsvf0731_nv40666:40666, MODEL=dsv4p_nv, TOKEN=nv-gw-token
- [x] nv_gw env: NVU_MS_FALLBACK_URL=dsvf0731_nv40666:40666, MODEL=dsv4p_nv, TOKEN=nv-gw-token
- [x] R830 代码已加载: docker exec nv_gw python3 → "R830 code loaded OK"
- [x] E2E 正常请求 200 OK (89s, primary 路径, 非大请求不触发硬限制)
- [ ] 大请求触发硬限制 — 需等实际大请求出现观测 NV-BUFFER-INPUT-OVER-LIMIT 日志

## 风险

- 40066 容器挂 = 两层 fallback 都失效. 但 40066 已稳定运行 16h+, 且 ms_gw 本身也有挂的风险.
- dsv4p_nv NVCF 后端可能间歇 404 (R2143 记录). 但 40066 有 5-key 重试 + buffer.
- nv_gw_stable (40005) 仍保留 ms_gw fallback, 不受本次变更影响.
