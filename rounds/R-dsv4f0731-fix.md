# R-dsv4f0731-fix: dsv4f0731_nv 100% 404 → 修复 model 名 (FID 复用错误)

- **日期**: 2026-08-05 02:32 CST
- **容器**: dsvf0731_nv40666 (port 40666, DeepSeek V4 flash via NVCF)
- **类型**: 部署缺陷修复 (非参数调优)

## 症状

hm4104 (PRIMARY_MODEL=dsv4f0731_nv, PRIMARY_URL=http://dsvf0731_nv40666:40666/v1)
持续 fallback 到 ms_gw。日志显示 `PRIMARY-BREAKER-SKIP-STREAM` + `FALLBACK-STREAM` 每秒交替。

## 根因 (数据支撑)

`dsv4f0731_nv` 与 `dsv4f_nv` **共享同一 FID** `52e1ddb6-c745-4802-93f5-ba012d04c336`
(ai-deepseek-v4-flash, ACTIVE, via 共享 env `NVCF_DEEPSEEK_FLASH_FUNCTION_ID`)。

但两 tier 向 NVCF 发送的 **model 名不同**:

| tier | model 名 | 30min SR |
|---|---|---|
| dsv4f_nv | `deepseek-ai/deepseek-v4-flash` | **82%** (46/56) |
| dsv4f0731_nv | `deepseek-ai/deepseek-v4-flash-0731` | **0%** (7/7 → 404) |

`upstream.py:967` 用 `NV_MODEL_IDS[tier_model]` 作为发送给 NVCF pexec 的 model 名。
FID `52e1ddb6` 对应的 NVCF 部署只认 `deepseek-v4-flash`，`-0731` 后缀不被识别 →
**每个请求都 404 "Inference error"** (non-cycling, 直接 abort tier)。

日志证据 (02:26-02:28):
```
[NV-KEY] tier=dsv4f0731_nv attempt 1/7: k5 → NVCF pexec 52e1ddb6 ... 
[NV-NONCYCLE-ERR] tier=dsv4f0731_nv k5 resp.status=404 non-cycling, aborting tier ...
  body={"type":"urn:inference-service:problem-details:not-found","title":"Not Found",
        "status":404,"detail":"Inference error"}
[NV-ALL-TIERS-FAIL] All 1 tiers failed ... ABORT-NO-FALLBACK
[NV-PEER-FB] model=dsv4f0731_nv in peer-fb skip list ... returning local 502
```

5 个 key 全部 404 (k1,k2,k3,k4,k5 逐一尝试均 404)。同窗 `dsv4f_nv` 5 key 全部正常
(pexec 首尝试成功)。

注: 这是**部署缺陷** (给正确 FID 配了错误的 model 名), 不是可调参数问题。
任何 timeout/cooldown/budget 调优都无法修复 100% 404。

## 修改

`/opt/cc-infra/proxy/nv-gw/gateway/config.py` (bind-mount, 共享 gateway 目录):

```diff
-    "dsv4f0731_nv": "deepseek-ai/deepseek-v4-flash-0731",
+    "dsv4f0731_nv": "deepseek-ai/deepseek-v4-flash",
```

备份: `config.py.bak.R-dsv4f0731-fix`

## 验证

- 语法: `python3 -c "import ast; ast.parse(...)"` → SYNTAX OK
- 重启: `docker restart dsvf0731_nv40666`
- /health: `status: ok`, tiers 含 dsv4f0731_nv
- 端到端测试: `POST /v1/chat/completions` model=dsv4f0731_nv → **200 OK**,
  `finish_reason=stop`, `model: deepseek-ai/deepseek-v4-flash`
- 日志: `[NV-SUCCESS] tier=dsv4f0731_nv k4 succeeded on first attempt`
- DB: `dsv4f0731_nv | 200 | nvcf_pexec | stop` (修复后最新请求 200)
- nv_gw (40006) 不受影响: tiers 无 dsv4f0731_nv, health ok

## 影响面

- 仅 `dsvf0731_nv40666` 容器 (专用 dsv4f0731 通路)。
- `nv_gw` (40006) 无此 tier, 不受 config.py 修改影响
  (其 NV_MODEL_TIERS 由 env 覆盖, 不含 dsv4f0731_nv)。
- hm4104 的 primary 现在应能恢复 200, fallback 应停止。

## 预期效果 / 下一步

- hm4104 fallback 应逐步停止 (primary dsv4f0731_nv 恢复 200)。
- 下一轮: 观察 30min 窗口 dsv4f0731_nv SR 是否达到 ~82% (与 dsv4f_nv 对齐)。
- 若 SR 恢复, 再评估是否值得将 hm4104 的 PRIMARY_MODEL 保持 dsv4f0731_nv
  (自优化 track) 或回退到 dsv4f_nv。
- 若仍有 fallback, ��查 ms_gw 侧 dsv4f0731_ms 是否同样需要 model 名对齐。