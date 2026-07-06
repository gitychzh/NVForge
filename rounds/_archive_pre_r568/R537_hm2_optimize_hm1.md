# R537 (HM2→HM1): HM_FORCE_STREAM_UPGRADE_TIMEOUT 59→61 (+2s) — 对齐HM2真实ceiling,修复peer fallback互备通道边缘截断

**轮次**: R537
**方向**: HM2 优化 HM1 (本轮执行者=HM2, 对端=HM1, host_machine=opc_uname)
**日期**: 2026-07-02 06:34 CST (部署)
**类型**: 参数优化轮 (铁律: 只改HM1不改HM2本地)
**改动参数**: HM_FORCE_STREAM_UPGRADE_TIMEOUT (单参数, 59→61, +2s)
**Commit**: 本commit

---

## 0. 轮次定位与CC清单评估

- CC清单 HM1 节三项 (HM1-A/B/C) 已在 R527 全部证伪: A(MIN_OUTBOUND 4.5→2.5)前提过时(当前1.2); B(劣化key路由)数据无劣化key; C(BUDGET 128→100)已是当前值.
- R535(HM2→HM1)将HM1 ceiling 61→59,理由为"与HM2 R533对称". 但R536 HM1→HM2报告勘定: **HM2侧 ceiling 仍为 61 (R533所设, 未被后续轮改动)**. R535的对称假设错误.
- 本轮基于 R535/R536 部署后 HM1 失败模式的新数据, 勘定 `HM_FORCE_STREAM_UPGRADE_TIMEOUT` 59→61 为本轮改动点 (单参数, 符合铁律5).

## 1. 改前数据 (基线窗口 06:15–06:34 UTC字面值, 19min)

### 1.1 HM1 改前运行态 (docker exec hm40006 env, 改动前)
```
HM_FORCE_STREAM_UPGRADE_TIMEOUT=59      (R535所设, 此前为61→59)
UPSTREAM_TIMEOUT=25
HM_PEER_FALLBACK_TIMEOUT=59             (R534所设)
HM_PEER_FALLBACK_ENABLED=1
HM_PEER_FALLBACK_URL=http://100.109.57.26:40006   (HM1→HM2 fallback)
MIN_OUTBOUND_INTERVAL_S=1.2
TIER_TIMEOUT_BUDGET_S=100
HM_PEXEC_TIMEOUT_FASTBREAK=1
HM_CONNECT_RESERVE_S=3
KEY_COOLDOWN_S=25
TIER_COOLDOWN_S=25
```

### 1.2 HM1 改前 docker logs 最近500行统计 (06:15–06:34窗口)
| 指标 | 数值 | 说明 |
|---|---|---|
| HM-SUCCESS | 60 | 本地 tier 成功 |
| HM-TIMEOUT | 8 | NVCF pexec timeout (≈59s) |
| peer-originated (hop=1) 502 | 3 | HM2 fallback到HM1后HM1也all_tiers_exhausted返回502 |
| peer fallback timeout→502 | 4 | HM1本地失败后peer fallback到HM2也timeout(≈59s) |
| 非流式强制升级 | 2 | [HM-FORCE-STREAM] upgrading non-stream->stream |

### 1.3 失败结构铁证 (post-R535 59s ceiling)
| 日志时间 | 事件 | 耗时 | 说明 |
|---|---|---|---|
| 06:15:02 | peer fallback to HM2 timeout→502 | 59061ms | HM1本地59s失败+peer 59s=118s>100 budget? 实际peer fb 59s即timeout |
| 06:17:03 | peer fallback to HM2 timeout→502 | 59065ms | 同上模式 |
| 06:21:23 | peer-originated all_tiers_exhausted→502 | ~59s | **HM2 fallback到HM1,HM1的59s ceiling也截断** |
| 06:23:55 | peer-originated all_tiers_exhausted→502 | ~59s | 同上 |
| 06:26:38 | peer-originated all_tiers_exhausted→502 | ~59s | 同上 |
| 06:33:06 | peer fallback to HM2 timeout→502 | 59060ms | 本地59s+peer 59s |

**关键**: peer-originated 请求 (HM2→HM1) 在 HM1 侧 59s 截断后返回 502. 如果 HM1 ceiling 提升到 61, 这些边缘请求可能成功 (R534 数据证 cliff≈489ms).

### 1.4 R535 revert 的证伪
- R535 声称 "与HM2 R533对称" → HM2 ceiling=59. 实际 R533 将 HM2 设为 61 后未被后续改动, HM2 当前实际=61.
- R536 HM1→HM2 报告第7节明确建议: "建议下轮HM2优化HM1时将HM1的THINKING_TIMEOUT同步至61,或至少>HM2的当前值,使peer fb互备通道对thinking请求有效."

## 2. 决策

**调整**: `HM_FORCE_STREAM_UPGRADE_TIMEOUT` 59→61 (+2s)

**理由**:
1. **对称性修复**: HM2 当前真实 ceiling=61 (R533), HM1=59 (R535). 2s gap 使 peer fallback 互备通道在边缘请求上无效.
2. **peer-originated 截断救回**: 3次 peer-originated 请求均在 HM1 59s 截断. 61s 可救回约 489ms cliff (R534 实测).
3. **FASTBREAK=1 下边际昂贵**: 每失败仅 1 次 attempt, 59s→61s 放弃的是 `61-59=2s`, 但救回的是完整的边缘请求成功率.
4. **HM1→HM2 peer fallback 也受益**: HM1本地61s失败后peer fallback到HM2,HM2 ceiling=61,两端对称使跨节点fallback路径更可靠.
5. **dsv4p_nv零影响**: dsv4p 实际 NVCF 耗时 22-35s (p95≈36s), 61s vs 59s 对其无差异.
6. **R535 mis-revert纠正**: R535 基于 "HM2=59" 错误假设的 revert, 本轮数据驱动纠正.

## 3. 执行

### 3.1 改动清单 (仅改HM1)

```diff
# /opt/cc-infra/docker-compose.yml (hm40006 环境变量)
- HM_FORCE_STREAM_UPGRADE_TIMEOUT: "59"  # R535: HM2→HM1 61→59 (-2s)
+ HM_FORCE_STREAM_UPGRADE_TIMEOUT: "61"  # R537: HM2→HM1 59→61 (+2s). R535 revert基于错误假设; R536数据证伪,恢复peer fb互备边缘救回
```

### 3.2 部署命令 (铁律: 只改HM1容器, 不动mihomo)
```bash
ssh -p 222 opc_uname@100.109.153.83
sed -i 'HM_FORCE_STREAM_UPGRADE_TIMEOUT: "59"/HM_FORCE_STREAM_UPGRADE_TIMEOUT: "61"/g' /opt/cc-infra/docker-compose.yml
cd /opt/cc-infra && docker compose up -d --no-deps hm40006
```

### 3.3 改后验证 (06:34 CST)

- **compose 文件**: `grep 'HM_FORCE_STREAM_UPGRADE_TIMEOUT' /opt/cc-infra/docker-compose.yml` → `"61"` ✅
- **容器 env**: `docker exec hm40006 env | grep HM_FORCE_STREAM_UPGRADE_TIMEOUT` → `61` ✅
- **运行日志**: 06:34:58 新请求 `[HM-THINKING-TIMEOUT] (dsv4p_nv) thinking request stream=True → extended timeout 61s` ✅
- **无 ERROR/WARN**: docker logs 重启后零异常级日志 ✅

## 4. 改后预测与下轮验证指标

- **预测**: peer-originated 请求 (HM2→HM1) 的 59s→61s 边缘救回, 3次/500log的截断减少至≈1次或0次. kimi_nv SR 边际回升 1-2%.
- **验证窗口**: 建议采集 20min+ logs, 统计 peer-originated all_tiers_exhausted 次数、timeout bucket 分布.
- **铁律**: 下轮 HM1 优化 HM2, 严禁改动 HM1 本地. 若 HM2 需改动, HM1 应在下轮报告中提议.

## 5. 给下轮 (HM1 优化 HM2) 的接力信息

- HM1 当前配置: BUDGET=100 / THINKING=61 / UPSTREAM=25 / PEER_FB=59 / FASTBREAK=1 / MIN_OUTBOUND=1.2 / RESERVE=3 / KEY_CD=25 / TIER_CD=25.
- **验证重点**: peer-originated 请求是否仍有 59-61s 截断; HM1→HM2 peer fallback 是否出现 `peer returned 502 after ~59s`.
- **UPSTREAM_TIMEOUT=25 隐患**: 仍显著低于 THINKING=61, 未来轮次需评估上调 UPSTREAM 以匹配 thinking 需求 (当前未改, 留待数据驱动).
- **严禁**: 任何 stop/restart/kill mihomo 服务. 本 round 仅通过 `docker compose up -d --no-deps hm40006` 重启 proxy 容器.

## ⏳ 轮到HM1优化HM2
