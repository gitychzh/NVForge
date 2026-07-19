# R1875 — HM2 cc2 巡检轮 (bug8 降级兜底 in-vivo 后第 31 轮持续 0 触发)

> 日期: 2026-07-19 ~10:30 CST
> 模式: nv 直连 (cc4101→nv_gw)
> 上一轮: R1874 (commit 771292d) 巡检轮 SR 96.0%
> 本轮: **NOP 巡检轮, 0 改动, 0 restart, 0 中断**

## 改前数据 (30min 窗, ~10:30 CST 拉取)

### SR
- 58/60 = **96.7%** (200:58 / 502:2)
- 较 R1874 的 96.0 微升 0.7, 属抖动区间常态
- **连续 15 轮在 93 上**: R1860 96.2 / R1861 98.0 / R1862 99.0 / R1863 97.6
  / R1864 98.6 / R1865 94.3 / R1867 93.5 / R1868 93.8 / R1870 94.6 / R1871 96.8
  / R1872 96.6 / R1873 95.7 / R1874 96.0 / R1875 96.7
  (注 R1866/R1869 为 peer HM2→HM1 轮, 不计 HM2 SR 抖动序列)
- R1856+R1857 连 2 轮破 93 早被 R1858 94.7 反弹打断 → 连破计数仍 0
- **远高于 93% 阈值, 未达连续 >=3 轮破 93 触发线, 绝无系统退化信号**

### 502 分类
- stream_absolute_cap 1 (NVCF 侧上游 token abs_cap, 已知分类 config 不可修, R1851-R1874 间歇)
- stream_first_byte_timeout 1 (NVCF 侧 timeout 偶发, 已知分类非新可配置分类)
- **全 NVCF 侧偶发外分支, config 不可修, 与 R1851-R1874 同构, 非新可配置错误**

### tier pexec
- pexec_success 30, **无 ATE 无 SSLEOF 无 429 无 pexec_timeout-as-primary-error** (干净)
- pexec_empty_200 4 + pexec_timeout 2 + empty_200 1 (NVCF 侧偶发, 非新可配置分类)

### bug8 降级触发
- **实战降级触发 0** (NV-TOOLCALL-JSON-DOWNGRADE 120min 窗空, DB 0 + nv_gw log 0 双确认)
- 兜底在位 args 全合法不需触发, 符合 R1839 round 文件原话"兜底保险就该几乎不触发"

### fallback (cc4101 30min, 7 条全 SKIP-CIRCUIT)
- bug3 75s header/ttfb 抢断 cc4101 preempt nv_gw retry, 非 nv_gw 失败 NOT counted
- 10:03 req=bf3ab750 → FALLBACK-OK ms 20375ms (R1874 跨窗复现, 20s 单点慢化尖峰)
- 10:07 req=540247a9 → FALLBACK-OK ms 5639ms (R1874 跨窗复现, <10s)
- 10:10 req=2913969a → FALLBACK-OK ms 2323ms (R1874 跨窗复现, <10s)
- 10:16 req=415287ef → FALLBACK-OK ms 7741ms (**本窗新增**, <10s)
- 10:20 req=a5f8d554 → FALLBACK-OK ms 3846ms (**本窗新增**, <10s)
- 10:21 req=8c32b1bc → FALLBACK-OK ms 3678ms (**本窗新增**, <10s)
- 10:25 req=84c6bb92 → FALLBACK-OK ms 4630ms (**本窗新增**, <10s)
- **非跳过类真请求失败 0 条**, < 4 阈值, **0 中断**
- fallback ms 延迟趋势: R1874 的 10:03 req=bf3ab750 20375ms 单点 20s 慢化尖峰本窗未续恶化,
  本窗新增 4 条 (10:16/10:20/10:21/10:25) 均 <10s 回正常区间 →
  仍是单点尖峰非趋势, fallback 负载/健康无持续恶化, ms_gw 热备兜住 0 中断

### breaker 30min (全 CLOSED 未 OPEN, 设计内)
- 10:06:21 NV-ANTH-BREAKER-FAIL (glm5_2_nv) anth mid-stream soft-fail
  err=stream_absolute_cap -> nv_breaker recorded (state=('CLOSED', **1**, 0), req=5473e48c) (R1874 跨窗复现)
- 10:09:50 / 10:13:33 / 10:23:13 / 10:24:37 / 10:28:25 NV-MS-FB-SERVED
  (ms 兜底 served, nv breaker recorded failure state=CLOSED 无计数)
  req=003f3e45 / 591b66fa / e988d0b4 / 3f898157 / a4dfdee0 (后 3 条本窗新增)
- **重点结论**: nv_breaker state 第二字段自 R1873 的 2 → R1874 掉到 1 →
  **本窗 R1875 仍 1** (req=5473e48c state=('CLOSED', 1, 0) 跨窗复现, **本窗无新 NV-ANTH-BREAKER-FAIL 事件更乐观**)
- state 在 1-3 之间漂移而非单调累积 (R1871 从 3 掉回 2, R1872/R1873 漂在 2, R1874 掉到 1, R1875 仍 1),
  远低于 OPEN 阈值, 设计内吸收态且具自恢复能力
- **出现新事件 ≠ 恶化**: state 重置/衰减机制正常工作

### env (无漂移)
- UPSTREAM_TIMEOUT=66 / TIER_TIMEOUT_BUDGET_S=180 / MIN_OUTBOUND_INTERVAL_S=0
- KEY_COOLDOWN_S=25 / TIER_COOLDOWN_S=25 / NVU_BIG_INPUT_FAIL_N=1
- 全与 R1850-R1874 一致

### oai_to_anth.py (bug8 四要素全在)
- md5=4983bcec1d1203a1f3f8acf371786c6c (550 行)
- 宿主/容器一致 (host `/opt/cc-infra/proxy/nv-gw/gateway/format/oai_to_anth.py`
  vs container `/app/gateway/format/oai_to_anth.py`)
- `_detect_bad_tool_args()` + finish() 正常路径 `_downgrade_to_end_turn` flag
  + 两处 final_stop 强制 end_turn (zombie 修路 / 正常完成路径) 四要素全在

### StartedAt + 健康
- nv_gw 真实 StartedAt = **2026-07-18T21:26:29Z** (= R1836 restart, R1839 至 R1874 未再 restart)
- 确认跑 R1839 改后字节码
- /health ok (proxy_role=passthrough, nv_num_keys=5, nvcf_pexec_models=['kimi_nv','dsv4p_nv','glm5_2_nv'])
- docker ps 全 Up (nv_gw Up 5h / cc4101 Up 19h / logs_db Up 2d)

## 改了什么
- **NOP (不改)**: 无 compose env / 无 .py 改动 / 0 restart

## 决策理由 (介入触发四条全不满足)
1. SR 96.7% > 93, 连续 15 轮在 93 上, 连破计数 0 (R1856+R1857 连 2 轮破 93 早被 R1858 94.7 反弹打断)
2. fallback 非跳过类真请求失败 0 条 < 4 阈值 (7 条全 SKIP-CIRCUIT, bug3 75s 抢断非 nv_gw 失败)
3. NV-ANTH-BREAKER-FAIL 全 CLOSED 未 OPEN, state 第二字段本窗仍 1 (比 R1873 漂在 2 更乐观), 无新事件
4. 502 全 NVCF 侧 abs_cap/timeout 已知分类 config 不可修, 无新可配置错误分类

→ 硬改违反铁律 (改前必有数据 + 无据不改). 连续 31 轮 NOP (R1842-R1875) 链路稳态.

## 验证结果
- 链路稳 (SR 96.7% > 93 抖动区间, 连续 15 轮在 93 上, 较 R1874 96.0 微升 0.7 属抖动无系统退化)
- bug8 0 触发 (DB + nv_gw log 双确认, 120min 窗=0)
- breaker 全 CLOSED 未 OPEN (nv_breaker state 本窗仍 1, 比 R1873 漂在 2 更乐观; 无新 NV-ANTH-BREAKER-FAIL 事件)
- fallback 非跳过类 0 + 0 中断 + 0 restart
- tier pexec 无 ATE/SSLEOF/429/timeout (干净)
- /health ok + docker ps 全 Up
- StartedAt 仍 21:26:29Z 确认跑 R1839 改后字节码
- env 无漂移 + oai_to_anth md5 一致 bug8 四要素全在
- 连续 31 轮 NOP (R1842-R1875) 链路稳态

## 下轮该做什么
继续常规巡检. **重点**:
- **nv_breaker state**: R1874 掉到 1, R1875 仍 1, 续盯 state 第二字段是否继续漂移 (1↔2↔3) 或单调续增触 OPEN
  (R1839 breaker 设计本就是"宁可 OPEN 走 ms 也不死循环", OPEN 本身是兜底动作非源码 bug;
  真正该看的是 OPEN 是否**频繁复现** → 那才是 nv_gw 软挂恶化信号, 需查 upstream/key 软挂源.)
- **SR**: 若 R1876 SR <93 → 只算 1 轮新破, 不能与旧 2 轮 (R1856 92.6 + R1857 90.2) 拼成 3 触发线
  (R1858 94.7 已打断旧连破), 需重新累积连续 3 轮破 93 才达介入线.
- **fallback ms 延迟**: R1874 的 10:03 req=bf3ab750 20375ms 单点 20s 慢化尖峰本窗未续恶化,
  本窗新增 4 条均 <10s 回正常. 续观察是否复现尖峰.
  (注: ms_gw 是热备不改, fallback 慢化不影响 nv_gw 优化目标, 但影响用户体验.)

**介入触发条件** (任一满足才动手, 否则继续 NOP 巡检):
1. SR 连续 >=3 轮跌破 93% (系统退化信号, 非抖动; 抖动被打断后重启连破计数).
2. fallback 中**非跳过类** (FALLBACK-OK 真正 nv_gw 失败) >=4 次/30min.
3. NV-ANTH-BREAKER-FAIL 出现 OPEN (state 中第一字段变 OPEN, 超过 zombie 软挂).
4. 出现新的可配置错误分类 (非 NVCF 侧 zombie/timeout/gap/cap).

若以上都不满足, 继续 NOP 巡检轮, 维持 bug8 兜底在位观测.
注: 连续 31 轮 NOP (R1842-R1875) 链路稳态. SR 近 14 轮 96.2/98.0/99.0/97.6/98.6/94.3/93.5/93.8/94.6/96.8/96.6/95.7/96.0/96.7 在 93 上抖动, 无退化数据, 不主动改.
