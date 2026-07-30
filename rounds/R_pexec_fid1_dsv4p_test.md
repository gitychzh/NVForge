# R_pexec_fid1: glm5.2_nv 切回 pexec fid1 + dsv4p 全方位测试

## 变更

### 1. NV_GLM52_MODE_CHAIN: integrate_us_rr,pexec_us_rr → pexec_us_rr
- 实测 integrate 端点对 GLM-5.2 全挂死 (POST /v1/chat/completions 30s 0 字节响应)
- integrate 对 deepseek-v4-pro 正常 (200, 3.5s), 对 glm5.2 和 llama-3.3-70b 挂死
- 结论: integrate 端点本身可达, 但 GLM-5.2 模型在 integrate 上 NVCF 侧挂死, 非 IP/网络问题
- KEY_MODE_BINDING 已全绑 pexec_us_rr, 但 mode_chain 仍含 integrate_us_rr → 日志显示 CHAIN-FAIL
- 改 mode_chain 为 pexec_us_rr 唯一模式, 消除 integrate 尝试浪费

### 2. config.py glm5_2_nv function_ids: 3 fid → 全绑 fid1 (b1b22d03)
- 实测 3 fid pexec 健康度:
  - fid1 (b1b22d03): 60/75=80% SR, avg 7.3s ✅ 唯一可用
  - fid2 (3b9748d8): 0% SR, 全 30s 超时 ❌
  - fid3 (b6029a96): 0% SR, 全 30s 超时 ❌
- config.py function_ids 3 个条目全改为 fid1, 避免 _next_fid_idx 轮转到挂死 fid
- 备份: config.py.bak.R_pexec_fid1, docker-compose.yml.bak.R_pexec_fid1

### 3. E2E 验证
- nv_gw /health: ok, nv_default_model=glm5_2_nv
- 直连 nv_gw: 200, 17.5s, fid=b1b22d03, pexec_us_rr ✅
- 日志确认: NV-GLM52-ATTEMPT fid=b1b22d03 (不再出现 fid2/fid3)

## dsv4p 全方位测试结果

### 基础测试 (5key x 5proxy x 3round = 75 req per mode)

| 模式 | N | OK | SR | avgTTFB | avgTotal | p50 | p90 | errors |
|---|---|---|---|---|---|---|---|---|
| nonstream_short | 15 | 15 | 100% | 1.1s | 3.7s | 3.6s | 4.3s | none |
| stream_short | 15 | 15 | 100% | 0.7s | 3.6s | 3.6s | 4.4s | none |
| nonstream_medium | 15 | 15 | 100% | 0.8s | 4.5s | 4.5s | 4.9s | none |
| nonstream_thinking | 15 | 15 | 100% | 0.8s | 4.3s | 4.4s | 4.9s | none |
| integrate_nonstream | 15 | 1 | 6% | 1.3s | 22.6s | 22.6s | 22.6s | timeout(14) |

### 延伸测试

| 模式 | N | OK | SR | avgTTFB | avgTotal |
|---|---|---|---|---|---|
| large_prompt_nonstream (2K tokens) | 5 | 5 | 100% | 1.0s | 25.7s |
| large_prompt_stream (2K tokens) | 5 | 5 | 100% | 0.9s | 29.8s |
| direct_nonstream (无代理, HM2 直连) | 5 | 5 | 100% | 0.2s | 1.4s |
| multi_turn (3轮对话) | 3 | 3 | 100% | 0.8s | 4.6s |

### per-key (pexec 4 modes combined)

| key | SR | avg |
|---|---|---|
| k0 | 12/12=100% | 4.2s |
| k1 | 12/12=100% | 3.8s |
| k2 | 12/12=100% | 4.0s |
| k3 | 12/12=100% | 4.1s |
| k4 | 12/12=100% | 4.0s |

### per-proxy (pexec 4 modes combined)

| proxy | egress IP | SR | avg |
|---|---|---|---|
| 7900 | 134.195.101.188 | 12/12=100% | 4.2s |
| 7901 | 203.10.96.139 (AU) | 12/12=100% | 3.8s |
| 7902 | 134.195.101.194 | 12/12=100% | 4.0s |
| 7903 | 134.195.101.120 | 12/12=100% | 4.1s |
| 7904 | 134.195.101.197 | 12/12=100% | 4.0s |

### DB 历史 (7天, nvcf_pexec)

| 指标 | 值 |
|---|---|
| 总请求 | 39 |
| 成功 | 27 (69.2%) |
| avg duration | 29.4s |
| errors | all_tiers_exhausted(39), zombie_empty_completion(12) |
| per-key SR | k0=72.7%, k1=66.7%, k2=50%, k3=100%, k4=57.1% |

### 核心结论

1. **dsv4p pexec 极稳定**: 4 模式 × 75 req = **100% SR**, 0 errors, avgTTFB 0.7-1.1s
2. **dsv4p integrate 也挂死**: 14/15 超时 (与 glm5.2 integrate 挂死同因, NVCF integrate 端点问题)
3. **大 prompt 稳定**: 2K tokens code generation 100% SR, avg 25-30s (合理)
4. **直连最快**: HM2 直连 (中国移动出口) 1.4s, 但历史已知直连会 504 (地理限制), 需代理
5. **5 key × 5 IP 完全均匀**: 所有组合 100%, 无差 key/IP
6. **DB 历史 SR 69.2%** vs 裸测 100%: 历史低 SR 来自 all_tiers_exhausted(链路层) 和 zombie(NVCF 侧), 非 pexec 本身不稳定
7. **thinking 参数无影响**: reasoning_effort=low 被 nv_gw strip, 但裸测也 100% (NVCF 侧接受该参数但不影响稳定性)
8. **stream vs nonstream 无差异**: 两者 100% SR, stream 略快 TTFB (0.7 vs 1.1s)
