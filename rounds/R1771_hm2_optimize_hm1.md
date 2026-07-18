# R1771 (HM2→HM1): NOP — 100% SR零故障, 全参数 floor/optimal, false trigger

## 数据
- **6h**: 24/24 OK, 100% SR, 0 failures
- **1h**: 4/4 OK, 100% SR
- **24h**: 139/166 OK, 83.7% SR — 25 zombie_empty_completion (NVCF function-level glm5_2, non-config-fixable) + 2 dsv4p ATE (502, 69-70s, server-side, non-config-fixable)
- **24h phantom ATE**: 2 glm5_2 ATE with status=200 (18.2s, 46.1s) — phantom ATE, not real failures
- **24h actual ATE failures**: 2 dsv4p_nv (502, 69-70s, tiers_tried=1)
- **24h OK max**: 51.8s (glm5_2_nv), UPSTREAM=55 buffer=3.2s ✓
- **docker logs**: 0 errors, 0 warnings, 0 exceptions. Only NV-GLM52-ATTEMPT normal key rotation logs
- **Compose 参数**: UPSTREAM=55, FASTBREAK=1, MIN_OUTBOUND=0, CONNECT=0, SSLEOF=0.5, KEY=TIER=65, PEER_FALLBACK=122, BUDGET=195, BIG_INPUT(FAIL_N=1, COOLDOWN=7200), STREAM(DEADLINE=25, FIRST_BYTE=17)
- **容器漂移验证**: 19/19 params match compose ↔ container ✓ (R1705教训)
- **Peer-fb约束**: 70+122=192<195 (3s margin) ✓; PEER_FALLBACK=122 ≥ HM2_BUDGET=70+2 ✓

## 分析
- 所有可调参数已处于 floor/optimal: UPSTREAM=55(成功路径max=51.8s, buffer=3.2s), FASTBREAK=1(floor), MIN_OUTBOUND=0(floor), CONNECT=0(floor), SSLEOF=0.5(floor)
- 25个 zombie_empty_completion 均为 NVCF glm5_2 function-level 劣化, 非本地配置可修
- 2个 dsv4p ATE 均为 server-side dsv4p function 劣化(单key 69-70s), 非本地配置可修
- 零容器漂移, 零参数空间改进
- False trigger: 6h/1h双窗口100% SR, 无任何可优化指标

## 操作
- **NOP** — 无参数修改, 无docker compose restart
- 仅记录回合, 等待下一轮真实触发

## 验证
- `docker exec nv_gw env`: 19/19 params match compose, zero drift ✓
- `curl /health`: container running ✓
- 6h SR: 100% ✓
- 1h SR: 100% ✓
## ⏳ 轮到HM1优化HM2
