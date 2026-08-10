# R1247 cc2 — 40666/nv_gw 单 fid + integrate 兜底 + 两 agent 链路配置

- **日期**: 2026-08-10
- **类型**: 内容改动 (用户 7 项任务全部执行)
- **主机**: HM2 (100.109.57.26)
- **用户决策**: 保持 OpenAI 协议 (任务7) + 复用现有 dynamic 机制 (任务1/2)

## 数据锚点 (改前, 直连 NVCF 实测)

**dsv4f0731 (40666)**: pexec (fid 281478d0) 5/5 200, total avg ~2.0s; integrate (须 -0731 名) 5/5 200, total avg ~3.3s.
**glm5.2 (nv_gw)**: pexec (fid 3b9748d8) 5/5 200, total avg ~7.1s; integrate 5/5 200, total avg ~6.8s.
结论: 两模型 pexec 与 integrate 均健康稳定, pexec 优先 + integrate 兜底合理.

## 改动 (7 项)

### 1. dsvf0731_nv40666 单 fid + integrate 内部兜底
- compose: 删 4 行多余 NVCF_FUNCTION_ID env (52e1ddb6 坏/12acbc62 EOL/glm52/kimi), 保留 NVU_FID_DISCOVERY (fid 281478d0 自动发现).
- upstream.py line 2577: `tier_model == "dsv4f_nv"` → `in ("dsv4f_nv","dsv4f0731_nv")`, 让 40666 的 dsv4f0731 复用 dsv4f-dynamic (pexec 优先 → pexec 失败下一 key integrate). 备份 upstream.py.bak.R1247.

### 2. nv_gw(40006) glm5.2 单 fid + integrate 内部兜底
- R1246 已单 fid 3b9748d8. mode chain: `pexec_us_rr` → `pexec_us_rr,integrate_us_rr` (pexec 优先, 故障递进 integrate). NV_INTEGRATE_MODELS=glm5_2_nv 已设.

### 3. 清理其他 fid (仅这两个容器)
- 40666 删 4 行 NVCF_FUNCTION_ID (见 1). nv_gw 已删 b1b22d03 (R1246).

### 4. pexec vs integrate 对比测试 (直连 NVCF)
| 模型 | pexec total | integrate total | 结论 |
|---|---|---|---|
| dsv4f0731 | avg ~2.0s (1.43-2.72) | avg ~3.3s (1.49-6.19) | pexec 快 |
| glm5.2 | avg ~7.1s (2.5-11.1) | avg ~6.8s (2.65-10.55) | 相近, integrate TTFB 略优 |
- dsv4f0731 integrate 用普通名 `deepseek-v4-flash` → 410 Gone, 必须 -0731 名.

### 5. hm4104 (hermes agent)
- compose hm4104: FALLBACK_URL ms_gw:40007→nv_gw:40006, FALLBACK_MODEL dsv4f0731_ms→glm5_2_nv, MS_GW_API_KEY ms-gw-token→nv-gw-token (forwarder FALLBACK 路径认证), depends_on 去 ms_gw.
- hermes config.yaml: default & default_model → dsv4f0731_nv.

### 6. opclaw4103 (openclaw agent)
- compose opclaw4103: PRIMARY_URL dsv4p_nv40066→dsvf0731_nv40666:40666, PRIMARY_MODEL dsv4p_nv→dsv4f0731_nv, FALLBACK ms_gw→nv_gw(glm5_2_nv), MS_GW_API_KEY→nv-gw-token, depends_on 去 dsv4p/ms_gw.
- openclaw.json: primary "nv_cus/dsv4f_nv"→"nv_cus/dsv4f0731_nv", fallback "ms_cus/glm5_2_ms"→"nv_cus/glm5_2_nv", provider 加 dsv4f0731_nv 模型定义.
- 重启 openclaw-gateway + hermes-gateway (systemd user), agent model 确认为 dsv4f0731_nv.

### 7. 协议
保持 OpenAI /v1/chat/completions (两 agent transport=openai_chat / api=openai-completions 不变, cc-adapter 不改).

## 验证 (全通过)

| 项 | 结果 |
|---|---|
| compose config | VALID |
| 容器 health | nv_gw/40666/hm4104/opclaw4103/cc4101/dsv4p 全 Up |
| nv_gw glm5.2 | 200, fid 3b9748d8 |
| 40666 dsv4f0731 | 200, fid 281478d0 (discovery) |
| nv_gw mode chain | pexec_us_rr,integrate_us_rr 生效 |
| 源码 dynamic gate | dsv4f0731_nv 接入 integrate 兜底 |
| openclaw 端到端 primary | 4103 → 40666 dsv4f0731, 200, 3.6s, caller=openclaw fid=281478d0 |
| hermes 端到端 primary | 4104 → 40666 dsv4f0731, 200, 14.7s, caller=hermes fid=281478d0 |
| openclaw fallback | 停 40666 → 4103 → nv_gw glm5_2, 200 5.3s (初测 k4 empty 是 NVCF 瞬态) |
| hermes fallback | 停 40666 → 4104 → nv_gw glm5_2, 200 8.3s |
| agent 重启 | dsv4f0731_nv 模型确认加载 |

## 测试中排除的干扰
任务4 的 glm5.2 10 连打探针 + 多次直连触发 nv_gw 5key NVCF 限流/cooldown (KV linux timeout/429), 导致 adapter fallback 初测 70s 超时. 属测试自致限流, 非配置问题. 等 cooldown 恢复后 fallback 200 验证通过.

## 备份
- docker-compose.yml.bak.R1247
- proxy/nv-gw/gateway/upstream.py.bak.R1247
- /home/opc2_uname/.hermes/config.yaml.bak.R1247
- /home/opc2_uname/.openclaw/openclaw.json.bak.R1247

## 下一步
- 观察 1h: hermes/openclaw 主链 (40666 dsv4f0731) SR + fallback 触发率 (应 <5%).
- 监控 dsv4f0731 pexec→integrate dynamic 兜底触发率.
- 若 glm5.2 integrate 在 mode chain 使用增多, 观察其大请求 (3b9748d8 历史 429 多) 是否触发 cooldown.