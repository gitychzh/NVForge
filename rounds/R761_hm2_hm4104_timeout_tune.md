# R761: HM2 hm4104 超时下调 — 修复 hermes 流式 fallback 超时 (R759 漏了 hm4104)

> R759 只调了 opclaw4103, 漏了 hm4104 (同问题). 本轮补齐. 仅 HM2 hm4104 env。

## 改前数据 (1h)

### hm4104 配置漂移 (与 opclaw4103 R759 改前一致)
- PRIMARY_STREAM_TIMEOUT_S=150, FALLBACK_TIMEOUT_S=300, PROXY_TIMEOUT=300
- CIRCUIT_FAILURE_THRESHOLD=3, CIRCUIT_OPEN_S=60, FALLBACK_RECOVER_S=30
- 最坏: 150+300=450s > hermes dialog_timeout_s=300s

### hm4104 近 1h 错误 (77 REQ)
- PRIMARY-FAIL: 8 次 (nv_gw dsv4p_nv 失败)
- STREAM-UPSTREAM-ERR: 12 次 (fallback ms_gw dsv4p_ms 读超时, hermes 已断开)
- dsv4p_nv 成功 avg=29.8s p90=39.8s, 失败 avg=67s p90=110s
- dsv4p_ms fallback 实际 100% 成功 (11/11), 但 hm4104 12 次 STREAM-UPSTREAM-ERR 说明 fallback 读太久 hermes 早断

### 根因
hermes dialog_timeout_s=300s (config.yaml:68). hm4104 150(primary)+300(fallback)=450s > 300s.
primary 150s 超时后切 fallback, fallback 再 300s, hermes 在 300s 时已 dialog_timeout 断开, hm4104 还在读 → STREAM-UPSTREAM-ERR.

## 改动 (对齐 opclaw4103 R759 方案, hm4104 only)

| 参数 | 改前→改后 | 理由 |
|---|---|---|
| PRIMARY_STREAM_TIMEOUT_S | 150→90 | dsv4p_nv 成功 p90=39.8s, 90s 覆盖; 失败 110s 到顶, 90s 已注定 |
| FALLBACK_TIMEOUT_S | 300→120 | dsv4p_ms 流式不该 300s, 120s 够 |
| PROXY_TIMEOUT | 300→240 | 对齐 hermes dialog 300s, 留余量 |
| CIRCUIT_FAILURE_THRESHOLD | 3→2 | dsv4p_nv 偶发失败, 2 次即开 circuit |
| CIRCUIT_OPEN_S | 60→300 | 打开后 5min 直接 fallback |
| FALLBACK_RECOVER_S | 30→120 | 2min 内不探 primary |

最坏: 90+120=210s < hermes dialog 300s (90s 余量).
circuit 打开后: 直接 fallback ~5s.

### 不改
- hermes config (agent 配置铁律, dialog_timeout 300s 合理)
- nv_gw/ms_gw 源码 (模块化)
- HM1 / opclaw4103(已R759) / oc4105 / cx4102

## 改后验证
- env 生效, health 200
- hermes CLI "验收" 17s 成功, 无 fallback
- hm4104 REQ 正常

## 预期
- STREAM-UPSTREAM-ERR (hermes 断开真因): 12/h → 大幅下降
- dsv4p_nv primary 成功 30-40s, 失败 95s, circuit 后 5s
- hermes 不再 dialog_timeout 断开

## 风险
- 低: 对齐 R759 验证方案
- 回滚: env 改回

## 遗留
- ms_gw glm5_2_ms stream_no_data cycle (55次, 但最终成功, 非阻塞, 下轮观察)
- oc4105/cx4104 超时未调 (有流量后再评估)
- HM1 同步待授权
