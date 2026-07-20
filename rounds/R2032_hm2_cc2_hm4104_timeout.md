# R2032 (HM2 cc2): hm4104 adapter header-timeout 放宽 (PRIMARY_HEADER_TIMEOUT 25→80, CIRCUIT 2/300→5/60)

## 背景
不是 nv_gw 改动. 是 cc2 自优化正反馈循环里发现的 hm4104 adapter 容器自陷死循环:
hermes 真实流量 (stream+tools+大 prompt) 走 hm4104→40006→dsv4p_nv 时,
dsv4p_nv 在 nv_gw 内部 integrate→pexec 跨模式 fallback 首字节常 35-46s,
超出 hm4104 默认 PRIMARY_HEADER_TIMEOUT=25s, adapter 25s 抢跑 timeout→切 ms fallback→
CIRCUIT_FAILURE_THRESHOLD=2 一碰就 OPEN→OPEN 期 300s 内所有请求直走 ms, nv_gw 流量空洞.

## 数据 (改前, 11:20-11:30 窗口)
- hm4104 日志: 连续 PRIMARY-BREAKER-SKIP-STREAM "circuit OPEN", 全部直走 ms_gw fallback
- 直发 40006 dsv4p_nv (绕过 adapter): ~3s 成功, 返回 model=deepseek-ai/deepseek-v4-pro
  → 证明底端 dsv4p_nv 健康, 故障只在 adapter 熔断死循环
- opclaw4103 (PRIMARY_MODEL=glm5_2_nv, 同 25s timeout): 端到端 8.99s 成功, 无 fallback
  → glm5_2_nv 首字节快, 25s 够; dsv4p_nv 慢, 25s 不够

## 拟改 (只动 hm4104 adapter env, 不碰 40006 nv_gw 源码, 符合铁律3)
/opt/cc-infra/docker-compose.yml hm4104 段:
- + PRIMARY_HEADER_TIMEOUT=80  (新增, 默认 25; 对齐 dsv4p_nv p90 TTFB ~46s 留余量)
- CIRCUIT_FAILURE_THRESHOLD 2→5  (与 opclaw4103 一致, 一次抖动不 OPEN)
- CIRCUIT_OPEN_S 300→60  (恢复更快, 对齐 opclaw4103)
备份: docker-compose.yml.bak.R_hm4104_timeout_20260720_113052

## 重启 + 验证
docker compose up -d hm4104 (只重建该 adapter, nv_gw 未动)

### E2E TEST 1: openclaw → opclaw4103 → 40006 → glm5_2_nv
curl 4103 stream=False max=40 → content="OPENCLAW-OK", model="z-ai/glm-5.2"
adapter 日志: model agent-tag-opclaw 被改写 (forwarder.py:216 body["model"]=PRIMARY_MODEL)
nv_gw 日志: [NV-GLM52-SUCCESS] tier=glm5_2_nv k5
latency 8.99s, 走 primary 全程, 0 fallback. ✅

### E2E TEST 2: hermes → hm4104 → 40006 → dsv4p_nv (轻载)
curl 4104 stream=False max=40 → content="HERMES-OK", model="deepseek-ai/deepseek-v4-pro"
nv_gw 日志: [NV-SUCCESS] tier=dsv4p_nv k4 first attempt
latency 5.35s, 走 primary 全程, 0 fallback. ✅

### E2E TEST 3: hermes 真实负载 (stream+tools+reasoning)
curl 4104 stream=True tools=1 max=200 大 prompt
- 首轮 (timeout=45 时): 47s 失败, integrate k5 "Remote end closed connection" 35s 后 pexec 成功
  但 adapter 45s 抢先 timeout 切 ms fallback (nv_gw 实际 46s 成功, 差 1s)
- 放宽到 80 后重测: content 首字节 "I" 正常流式, model=deepseek-ai/deepseek-v4-pro
  latency 17.27s, adapter 日志只有 REQ 无 PRIMARY-FAIL/FALLBACK/CIRCUIT-OPEN, 走 primary 全程 ✅

## 验证结论
- 配置层面: openclaw→glm5_2_nv / hermes→dsv4p_nv 已端到端确认 (agent model 标签被 adapter
  强制覆写为 PRIMARY_MODEL env, 真正决定 NVCF 模型的是 adapter env 不是 agent 配置)
- 性能层面: hm4104 不再 25s 抢跑, 真实流式负载走 primary 17s 成功, 0 fallback
- 不碰 40006: 只改 hm4104 容器 env, nv_gw StartedAt/RestartCount 未变

## 后续观察
- dsv4p_nv integrate 偶发 "Remote end closed connection" (NVCF 抖动) 仍存在, 但 80s 余量足够
  让 nv_gw 内部 pexec 兜底成功, 不再触发 adapter fallback
- 若 6h 窗口 dsv4p_nv fallback 率仍高, 下一轮考虑 nv_gw 侧 dsv4p_nv tier 的 integrate
  超时收紧 (那是 40006 改动, 需另开 R 轮走铁律)
