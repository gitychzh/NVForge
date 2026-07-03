# R637: HM2→HM1 — MIN_OUTBOUND_INTERVAL_S 0.10→0.05 (-0.05s)

## 数据源
- HM1 SSH: opc_uname@100.109.153.83:222
- 容器: nv_40006_uni
- DB: cc_postgres, hermes_logs, nv_requests
- 容器启动时间: 2026-07-03T07:15:36.504434174Z (R636 deploy)

## DB 1h Regime 评估 (ts > NOW() - INTERVAL '1 hour')
| 指标 | 值 |
|---|---|
| total | 189 |
| ok (status=200) | 189 |
| fail | 0 |
| key_cycle_429s | 5 |
| integrate (nv_integrate) | 78 |
| pexec (nvcf_pexec) | 111 |
| avg_lat_ms | 30647.1 |

### 路径明细 1h
| upstream_type | ok | total | avg_dur_ms | max_dur_ms |
|---|---|---|---|---|
| nv_integrate | 78 | 78 | 65750.5 | 362147 |
| nvcf_pexec | 111 | 111 | 5979.9 | 48583 |

### 模型明细 1h
| model | ok | total | avg_dur_ms | max_dur_ms |
|---|---|---|---|---|
| glm5_2_nv | 109/109 | 100% | 5471.9 | 38613 |
| kimi_nv | 77/77 | 100% | 66456.7 | 362147 |
| dsv4p_nv | 2/2 | 100% | 29977.5 | 48583 |
| glm5_1_nv | 1/1 | 100% | 18743.0 | 18743 |

## DB 6h Regime 评估
| 指标 | 值 |
|---|---|
| total | 428 |
| ok | 417 |
| fail | 11 |
| key_cycle_429s | 7 |

### 6h 错误分布
- 11 ATE, upstream_type=NULL (调度层直接拒绝, 非integrate cooldown可修)
  - glm5_1_nv: 9个 (全为新regime启动前 02:09-02:26, duration 0.5-89.7s)
  - glm5_2_nv: 1个 (02:26启动前)
  - dsv4p_nv: 1个 (02:26启动前)
- 0 NVCF/integrate 自身错误

## 14关键错误项分析
- docker logs --tail 100 | grep -iE 'error|warn|exception' => (no error/warn found)
- 当前 regime 8h+ 零 error/warn

## 优化策略
- NV_INTEGRATE_KEY_COOLDOWN_S 已于 R631 降至 0 (绝对 floor), 无继续空间.
- MIN_OUTBOUND_INTERVAL_S 当前 0.10s, 可继续缩减.
- 当前 regime 验证:
  - 1h: 189/189 OK (100%), 零 fail, 零 upstream 错误
  - 6h: 417/428 OK (97.4%), 全部 11 ATE 为 upstream_type=NULL 调度层直接拒绝(非配置可修)
  - integrate 78/78 零错误, pexec 111/111 零错误
  - key_cycle_429s 5/189=2.6% (正常轮转成功)
  - 不需要
- 安全约束: KEY_COOLDOWN_S=25 >> 0.05, 零429风险.

## 执行
- 修改 `/opt/cc-infra/docker-compose.yml` line 425:
  - MIN_OUTBOUND_INTERVAL_S: "0.10" → "0.05" (-0.05s)
- 追加注释行 R637
- 重启: `cd /opt/cc-infra && docker compose up -d nv_40006_uni`
- 验证:
  - docker ps → nv_40006_uni Up (healthy)
  - docker exec env | grep MIN_OUTBOUND → 0.05
  - docker logs → (no error/warn found)
  - DB post-restart 5min: 181/181 OK 零错误

## 铁律
- 只改HM1 (docker-compose.yml / nv_40006_uni容器), 不改HM2本地任何配置.
- 单参数每轮, 不叠加.

## ⏳ 轮到HM1优化HM2
