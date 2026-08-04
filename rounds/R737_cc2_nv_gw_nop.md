# R737 — cc2 nv_gw NOP 巡检 (2026-08-05 04:51 CST)

## 改动: 不改码 (NOP)

## 依据 (实测 ~04:51 CST, 30min 窗)

### cc2 (cc4101-primary) nv_gw SR
- 注入数据: `cc4101-primary|glm5_2_nv|200|48` → SR 100%
- DB 实测验证: `nv_requests where caller='cc4101-primary' and created_at > now()-interval '30 min'` → **51×200 = 100%**
- avg_dur 33951ms 正常, 无长尾, 无 fallback 触发

### glm5_2_nv per-key (DB 实测)
```
 k0 | pexec_success | 11
 k1 | pexec_success | 10
 k2 | pexec_success |  9
 k3 | pexec_success | 11
 k4 | pexec_success | 10
```
**全 5 key pexec_success, 零 529/零 RemoteDisconnected/零 Timeout** — 达标

### 非 cc2 链路 (hermes caller, dsv4f0731_nv)
- 注入: `hermes|dsv4f0731_nv|200|14` + `hermes|dsv4f0731_nv|502|9` → SR 60.9%
- 9×502 all_tiers_exhausted (avg_dur 60491ms) = dsv4f0731_nv NVCF 上游容量
- per-key 529 storm 全在 dsv4p tier (k0-k4 各 9-16 个 529_nv_overloaded + k4 5 个 529_integrate_overloaded)
- **这是 dsv4f0731_nv tier 问题, 不是 cc2 的 glm5_2_nv 链路, 非 nv_gw 配置可改**

## 容器健康
- nv_gw: ok (5 keys, glm5_2_nv default, Up 2h)
- cc4101: ok (primary=glm5_2_nv, Up 3h)
- dsv4p_nv40066: Up 8h
- docker ps 全 Up, 无异常重启

## 判稳结论

**连续 3 轮 (R735/R736/R737) cc2 nv_gw 链路 SR 100%, fb 0%, per-key 全 pexec_success** — 全面稳定。

### 趋势
| 轮 | 30min 窗 SR | 窗口 | 备注 |
|---|---|---|---|
| R735 | 100% (最近 22min) | 30min 91.6% 被 04:10 前 dsv4p 502 拖低 | 529 余波 |
| R736 | 100% (47/47) | 04:50 CST | 余波平息 |
| R737 | 100% (51/51) | 04:51 CST | 持续稳定 |

dsv4f0731_nv 的 529 storm 仍间歇影响 hermes caller, 但 cc2 的 glm5_2_nv 链路完全独立, 不受影响。

## 参数快照 (沿 R736, 无变化)
- nv_gw: NVU_DISABLE_MS_FALLBACK=1, 单 mode pexec_us_rr, 全 key 绑 fid1 (b1b22d03), 5 IP 轮转
- cc2 deadline: 90s×5=450s buffer < 470s cc4101 < 600s API < 900s idle
- cc4101: PRIMARY=glm5_2_nv→nv_gw:40006, FALLBACK=glm5_2_ms→ms_gw:40007

## 下一步
- 持续监控 cc2 SR + fb 触发率
- dsv4f0731_nv 529 storm 非 cc2 职责
- 流量低时不动码, NOP 记数据
