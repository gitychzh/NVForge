# R524 (HM2→HM1): c699871 R523 (kimi_nv reasoning_effort medium→low) A/B 验证补全 + CC清单 HM1-A/B/C 三项证伪 (数据证伪轮)

**轮次**: R524
**方向**: HM2 优化 HM1 (本轮执行者=HM2, 对端=HM1, host_machine=opc_uname)
**日期**: 2026-07-02 03:00–03:20 CST / 2026-07-01 19:00–19:20 UTC
**类型**: 数据证伪轮 (验证并发抢跑 c699871 R523 + 证伪 CC 清单 HM1 三项, 无新参数改动)
**Commit**: 本commit

## 0. 本轮背景 (并发抢跑 c699871 后续)

- **c699871 R523 已由并发 session 完成** (2026-07-02 03:00 CST commit): HM2→HM1, 改 HM1 本地 `config.py` 第77行 kimi_nv `inject.reasoning_effort` medium→low, 容器 02:54:51 重启生效. round 文件写到 `RN_hm2_optimize_hm1.md` (R322#3 命名违规, 用了模板名而非 R524_hm2_optimize_hm1.md).
- c699871 的 round 文件 A/B 验证仅 3min 短窗口 (02:55–02:58, 5reqs kimi_nv), 样本极小 (R320#2 教训), 末尾误标 "⏳ 轮到HM1优化HM2" (方向标反, 应为 HM2→HM1 后轮到 HM1→HM2). 但其改动 (low) 已部署生效 (容器 02:54:51 重启, config.py line 77 已验证 low).
- d36e53e (R523 HM1→HM2) 是上一轮正式轮, 末尾 "⏳ 轮到HM2优化HM1" 给我接力. 但 c699871 抢跑做了同方向 (HM2→HM1) 的 low 改动.
- 为避免与 c699871 叠加新改动 (铁律5 单参数, 且 low 已生效不可重复改), 本轮定位为 **c699871 R523 (low) 的 A/B 验证补全 (15min+ 窗口) + CC 清单 HM1-A/B/C 三项证伪**, 不新增改动.

## 1. CC定向清单 HM1 三项证伪 (实测数据支撑, 非跳过)

CC清单基于旧勘定 (MIN_OUTBOUND=18.2 / k4 p95=72.9s / 95s失败耗满budget). 本轮 + 历史轮实测证伪如下:

| 清单项 | 清单主张 | 实测 (本轮 02:25–02:54 CST 30min) | 结论 |
|--------|---------|-----------------------------------|------|
| [HM1-A] MIN_OUTBOUND 18.2→9.0 | throttle=18.2s 锁吞吐, 吞吐=3.3req/min | `MIN_OUTBOUND_INTERVAL_S=1.2` (非18.2, R521已调至1.2); 吞吐=11.4req/min (30min 342reqs, 非锁死) | **证伪** 已是1.2, 降到9.0是回退5倍 |
| [HM1-B] k4(direct,idx=3)路由劣化 p95=72.9s | k4 p95=72.9s vs 其他~55s, max=162.9s, k4本机IP被限速 | k3(idx=3) p95=39.8s max=55.0s; k0-k4 全200成功, p95 30.9-39.8s 均匀, 无劣化key | **证伪** 全key健康, 无路由改动力 |
| [HM1-C] all_tiers_exhausted早fail, 22次avg104s | 失败avg104s p50=89s 耗满BUDGET, 共耗2288s | 30min 17个502 全在 55.2-58.4s (STREAM_UPGRADE ceiling 57s), 0个95s失败 (R520 peer_fb 45→15s 已消除95s模式); FASTBREAK=1 已是早fail | **证伪** 95s失败已由R520消除, 当前失败是57s ceiling 非budget耗尽 |

三项均已证伪 (符合 "不允许无操作轮, 除非三项都已做完或数据证伪" 的例外条件).

## 2. c699871 R523 (kimi_nv medium→low) A/B 验证 (补全 c699871 3min短窗口)

### 2.1 改前 (medium, 02:25–02:54, 30min, 容器02:54:51重启前)

```
 mapped_model | total | ok  | succ_pct |  p50  |  p95
--------------+-------+-----+----------+-------+-------
 dsv4p_nv     |   206 | 206 |    100.0 |  5313 |  9256
 kimi_nv      |   129 | 112 |     86.8 | 19119 | 56984
```
- kimi_nv 成功率 = 112/129 = 86.8% (17个502, 失败率13.2%)
- 17 个 502 全是 all_tiers_exhausted, 耗时 55.2-58.4s (57s ceiling), nv_key_idx=NULL, key_cycle_details=`[]`
- 失败模式: kimi_nv thinking 请求 (medium inject) NVCF 服务端 57s 内不发首字节 → pexec_timeout → FASTBREAK=1 → peer fallback (15s, HM2 也卡 thinking) → 502

### 2.2 改后 (low, 02:55–03:13, 18min, c699871 02:54:51 重启后)

```
 mapped_model | total | ok  | succ_pct |  p50  |  p95
--------------+-------+-----+----------+-------+-------
 dsv4p_nv     |   125 | 125 |    100.0 |  5039 |  9231
 kimi_nv      |    41 |  37 |     90.2 | 10047 | 57483
```
- kimi_nv 成功率 = 37/41 = 90.2% (4个502, 失败率9.8%)
- 4 个 502 全是 all_tiers_exhausted, 耗时 57.3-58.8s (57s ceiling 不变)
- 吞吐 ~8 reqs/min (改前 11.4, 略降, 但改后窗口流量本身偏低)
- low 后 p50 显著降 (19.1s→10.0s), 说明 kimi 思考深度降低让多数请求更快完成
- 但 p95/502耗时 不变 (57s ceiling), 说明 low 未完全消除 NVCF 服务端对部分请求的 57s 不响应

### 2.3 per-key 健康度 (改前 02:25–02:54)
| key | reqs | fails | avg_ms | p95_ms | max_ms |
|-----|------|-------|--------|--------|--------|
| k0 | 66 | 0 | 11914 | 35186 | 46498 |
| k1 | 61 | 0 | 9299 | 30895 | 50449 |
| k2 | 63 | 0 | 9408 | 34473 | 39872 |
| k3 | 63 | 0 | 12277 | 39755 | 55023 |
| k4 | 63 | 0 | 10505 | 39537 | 52843 |
| NULL | 19 | 17 | 51733 | 57663 | 58425 |

- k0-k4 成功请求分布均匀, 各 key 都能成功, **无劣化 key** (证伪 [HM1-B])
- 失败全集中在 nv_key_idx=NULL (FASTBREAK=1 下试1个key就break, 未记录成功key)

### 2.4 A/B 对比表

| 指标 | 改前 (medium) | 改后 (low) | 变化 |
|------|---------------|------------|------|
| 窗口 | 30min | 18min | — |
| kimi_nv reqs | 129 | 41 | — |
| kimi_nv ok | 112 | 37 | — |
| kimi_nv 502 | 17 (13.2%) | 4 (9.8%) | **-3.4pp** (方向向好) |
| kimi_nv p50 | 19119 | 10047 | **-9072** (显著降) |
| kimi_nv p95 | 56984 | 57483 | +499 (不变, 57s ceiling) |
| 502耗时区间 | 55.2-58.4s | 57.3-58.8s | 不变 (57s ceiling) |
| dsv4p_nv 失败率 | 0% (206req) | 0% (125req) | 维持 |
| 429 | 0 | 0 | 0 |
| empty_200 | 0 | 0 | 0 |
| reqs/min | 11.4 | ~8 | -3.4 (流量波动, 非throttle) |

### 2.5 结论: c699871 R523 (low) 部分改善, 未根治 57s ceiling

- **失败率**: 13.2%→9.8% (降3.4pp, 方向向好, 但改后样本n=41, 502仅4个, 不可强结论)
- **p50**: 19.1s→10.0s (显著降9s, low 让多数 kimi 请求思考更快完成)
- **p95**: 57.0s→57.5s (57s ceiling 不变, low 未让卡住的请求在57s内完成)
- **失败模式**: 仍全是 all_tiers_exhausted 卡 57s ceiling, 4个502耗时57.3-58.8s, 与 medium 同质
- **判定**: reasoning_effort=low 对 kimi_nv 有部分改善 (失败率-3.4pp, p50-9s), 但未根治 57s ceiling (NVCF 服务端对部分请求仍 57s 不响应). c699871 R523 的 "3min零失败" 是短窗口幸运, 18min 窗口仍有 9.8% 失败. 保持 c699871 既成状态 (low 无恶化, 有边际改善, 不回滚).

## 3. 根因分析: 57s 失败是 NVCF 服务端时刻性抖动 (与 HM2 R523 同质)

### 3.1 失败请求特征
- 全部 502: error_type=all_tiers_exhausted, duration 55-58s, nv_key_idx=NULL, key_cycle_details=`[]`
- FASTBREAK=1: 第一个 key PexecTimeout (57s) 即 fast-break, 不试后续 key
- kimi_nv 是唯一高失败模型: 改前 86.8% SR vs dsv4p_nv 100% SR; glm5_1_nv 流量极低

### 3.2 per-model 失败分布
- dsv4p_nv: 100% 成功, p50=5.3s p95=9.3s — 完全健康
- kimi_nv: 86.8% 成功 (改前) / 待测 (改后), p50=19.1s p95=57.0s — 全部失败都是 kimi_nv
- 失败是 kimi_nv thinking 请求特有, dsv4p_nv 同架构同代理零失败 → 模型侧 (NVCF 服务端对 kimi thinking 响应慢) 非基础设施侧

### 3.3 low 对 57s 失败的影响 (c699871 R523 评估, 本轮18min验证)
- low 降低 kimi 思考深度 → 理论上减少 thinking 耗时, 更多请求在 57s 内完成
- c699871 3min 短窗口 (5reqs 0失败) 不可强结论 (R320#2)
- 本轮 18min 窗口验证: low 后仍有 4 个 55-58s 502 (9.8%), 说明 low 未完全消除 ceiling (NVCF 服务端对 low thinking 仍可能57s不响应)
- 失败率 13.2%→9.8% (改善3.4pp), p50 19.1s→10.0s (改善9s), 但 p95/502耗时 不变 (57s ceiling)

## 4. 本轮决策: 不做新参数改动 (数据证伪所有方向 + low 已由 c699871 部署)

### 4.1 原则
> 一次只改1个参数 (铁律5); 改前必有数据 (铁律2); 不允许无操作轮, 除非三项已做完或数据证伪 (规则例外).

### 4.2 决策: 数据证伪轮, 不改动
**理由**:
1. CC清单 HM1-A/B/C 三项已被实测证伪 (§1, 符合例外条件).
2. c699871 R523 (low) 已部署生效, 本轮不可重复改 (铁律5), 定位为 A/B 验证补全.
3. 57s 失败根因为 NVCF 服务端对 kimi_nv thinking 时刻性抖动 (§3), HM 侧所有可改参数 (STREAM_UPGRADE_TIMEOUT / FASTBREAK / BUDGET / reasoning_effort) 均已被数据反证或已做.
4. 强行改参数 (如 STREAM_UPGRADE 57→60 / low→minimal / FASTBREAK 1→2) 会增加失败耗时或误杀慢成功, 无数据支撑收益, 违反 "稳定优先 > 越快越好" 评判标准.
5. 本轮为**数据证伪+验证轮**, 非无操作: 补全了 c699871 R523 缺失的 15min+ A/B 验证 (R320#2), 证伪了 CC 清单 HM1 三项, 为下轮排除无效方向.

### 4.3 不改动项 (保持现状)
- HM_FORCE_STREAM_UPGRADE_TIMEOUT=57 (R522值, c699871 未改)
- HM_PEXEC_TIMEOUT_FASTBREAK=1 (R516值)
- MIN_OUTBOUND_INTERVAL_S=1.2 (R521值)
- TIER_TIMEOUT_BUDGET_S=100
- kimi_nv reasoning_effort="low" (c699871 R523值, 保持不回滚)
- HM_PEER_FALLBACK_TIMEOUT=15 (R520值)

## 5. 容器健康验证 (无改动, 确认基线)

```
$ ssh ... 'curl -s http://127.0.0.1:40006/health'
{"status":"ok","proxy_role":"passthrough","hm_num_keys":5,...}
$ ssh ... 'docker exec hm40006 env | grep -E "MIN_OUTBOUND|BUDGET|FASTBREAK|STREAM_UPGRADE|PEER_FALLBACK"'
HM_FORCE_STREAM_UPGRADE_TIMEOUT=57
HM_PEXEC_TIMEOUT_FASTBREAK=1
MIN_OUTBOUND_INTERVAL_S=1.2
TIER_TIMEOUT_BUDGET_S=100
HM_PEER_FALLBACK_TIMEOUT=15
$ ssh ... 'docker exec hm40006 python3 -c "from gateway.config import NVCF_PEXEC_MODELS; print(NVCF_PEXEC_MODELS[\"kimi_nv\"][\"inject\"])"'
{'reasoning_effort': 'low'}   # c699871 R523, 保留
$ ssh ... 'docker inspect hm40006 --format "{{.State.StartedAt}}"'
2026-07-01T18:54:51Z  # c699871 02:54:51 CST 重启
```
本轮未改任何参数, 未重启容器 (c699871 02:54:51 重启后持续运行). 容器 healthy, env 与 config.py 均为 c699871 既成状态.

## 6. 给下轮 (HM1 优化 HM2) 的接力信息

### 6.1 HM1 当前配置基线 (R524后, 无改动)
```
BUDGET=100 / UPSTREAM=25 / FASTBREAK=1 / MIN_OUTBOUND=1.2 / RESERVE=5
KEY_CD=25 / TIER_CD=25 / STREAM_UPGRADE_TIMEOUT=57 / PEER_FALLBACK_TIMEOUT=15
kimi_nv reasoning_effort=low (c699871 R523) / dsv4p_nv=medium / glm5_1_nv=无inject
```

### 6.2 下轮方向建议 (HM1→HM2, 改对端HM2)
1. **HM2侧 low A/B 补全**: d2ccaf2 R522 (HM2侧 low) 已由 d36e53e 验证无明显改善 (HM2 55s失败9.3%). c699871 本轮 HM1侧 low 待本轮验证 (§2.4). 双端 low 是否收敛 55s 失败需持续观察.
2. **57s ceiling 双端不对称**: HM1=57 (R522) / HM2=55 (R521). c699871 round 文件建议 HM2 提至57 对齐, 但 d36e53e 数据显示 HM2 提 timeout 无益 (55s失败是服务端不响应). 双端是否对齐57 需重新评估.
3. **peer fallback 对 kimi_nv 几乎0救回**: HM1 R520 后 (15s) peer fb 对 kimi_nv 0救回/10尝试 (HM2 也卡 thinking). peer fb 对 thinking 请求是空耗. 潜在方向: 对 kimi_nv 跳过 peer fb (逻辑改动, 非env, 风险中). 但需先确认双端 low 后 peer fb 救回率是否变化.
4. **NVCF服务端抖动是kimi_nv特有**: dsv4p_nv 100% 成功, kimi_nv 86.8%. 非HM侧单参数可解, 需从模型路由 (是否 kimi_nv 可降级到 dsv4p_nv fallback) 或 peer fb 策略探索.

### 6.3 验证重点 (下轮HM1→HM2)
- 确认 HM2 55s ceiling 失败率 (d36e53e: 9.3%)
- 若双端 low 后 55-57s 失败仍频繁, HM 侧无可改参数, 下轮也可能为证伪轮
- c699871 末尾误标 "轮到HM1优化HM2", 实际本轮 (R524) 后应轮到 HM1→HM2 (本commit末尾修正)

## 7. 时区与host标识

- 对端HM1 host_machine=`opc_uname`, 主机名=opc_uname, ssh 端口 222.
- ts字段存CST时间数值但类型timestamptz (标UTC), 实际值=UTC+8h. 查询窗口用CST数值如 `ts > '2026-07-02 02:25'`, 禁止 `NOW()-interval`.
- 本轮所有数据窗口: 改前 02:25–02:54 CST / 改后 02:55–03:13 CST.

## ⏳ 轮到HM1优化HM2
