# R1868 (HM2 cc2): 巡检轮 bug8 降级兜底 in-vivo 后第25轮持续0触发 链路稳 SR93.8% nv_breaker state 停留3未续增触OPEN否决答案

**轮型**: 巡检轮 (NOP), 0 改动 0 restart. 连续 25 轮 NOP (R1842-R1868).
**日期**: 2026-07-19 09:23 CST (本 session 拉取).

## 改前数据 (30min 窗, 09:23 CST)
- **SR 61/65 = 93.8%** (200:61 / 502:4). **>93% 连续9轮在93上** (R1859 95.2/R1860 96.2/R1861 98.0/R1862 99.0/R1863 97.6/R1864 98.6/R1865 94.3/R1867 93.5/R1868 93.8). **连破计数仍0** (R1856+R1857 连2轮破93 早被 R1858 94.7 反弹打断, 本轮仍 >93 无系统退化). 本轮较 R1867 93.5 小幅回升属抖动区间常态.
- **502 分类**: zombie_empty_completion 3 + stream_first_byte_timeout 1. 注: stream_first_byte_timeout 属 NVCF 侧 timeout 偶发**已知分类** (非全新可配置分类, 历史轮曾多次出现), 4 条 502 **全 NVCF 侧偶发外分支 config 不可修**, 与 R1851-R1867 同构.
- **tier pexec**: pexec_success 45, pexec_empty_200 2. **无 ATE 无 SSLEOF 无 429 无 pexec_timeout** (干净).
- **fallback (cc4101 30min)**: 5 条全 PRIMARY-FAIL-SKIP-CIRCUIT (bug3 75s 抢断 cc4101 preempt nv_gw retry, 非 nv_gw 失败 NOT counted):
  - 08:56 req=7efcb96e → FALLBACK-OK ms 3783ms (与 R1863-R1867 同 req 跨窗复现).
  - 08:59 req=2c1be8a6 → FALLBACK-OK ms 2311ms.
  - 09:10 req=c9a8bb9f → FALLBACK-OK ms 5380ms.
  - 09:12 req=2a4164b0 → FALLBACK-OK ms 1960ms.
  - 09:19 req=b31ffce1 → FALLBACK-OK ms 3399ms (本窗新增).
  **非跳过类真请求失败 0 条**, <4 阈值. **0 中断**.
- **bug8**: 实战降级触发 0 (NV-TOOLCALL-JSON-DOWNGRADE 120min 窗空, DB 0 + nv_gw log 0 双确认). 兜底在位 args 全合法不需触发, 符合 R1839 原话"兜底保险就该几乎不触发".
- **breaker 30min**: **全 CLOSED 未 OPEN**:
  - 09:03 1 NV-ANTH-BREAKER-FAIL zombie_empty_completion (req=b14f6431) state=('CLOSED', 3, 0) — **延续 R1865 同 req, state 第二字段仍 3**.
  - 08:59/09:02/09:12/09:15/09:22 5× NV-MS-FB-SERVED (ms 兜底 served, nv breaker recorded failure state=CLOSED, 无计数).
  - **重点结论**: nv_breaker state 第二字段自 R1865 (09:03 req=b14f6431) 起停在 3, 本轮 R1868 (09:03 同 req) **仍 3, 未续增 (无 3→4 递进)**. 这正是 R1867 "盯后续是否续增触 OPEN" 的**否决答案**: 未续增 = 未恶化, 设计内吸收态 (fallback 路径取走 ms 兜底但不累加 mid-stream soft-fail 计数). 仍远低于 OPEN 阈值.
- **env**: 无漂移 (UPSTREAM=66 / TIER_BUDGET=180 / KEY_COOLDOWN=25 / TIER_COOLDOWN=25 / NVU_BIG_INPUT_FAIL_N=1, 全与 R1850-R1867 一致).
- **oai_to_anth.py**: md5=4983bcec1d1203a1f3f8acf371786c6c (550 行) 宿主/容器一致 (host `/opt/cc-infra/proxy/nv-gw/gateway/format/oai_to_anth.py` / container `/app/gateway/format/oai_to_anth.py`). bug8 四要素全在 (_detect_bad_tool_args + _downgrade_to_end_turn + 两处 final_stop 强制 endTurn + NV-TOOLCALL-JSON-DOWNGRADE 日志).
- **StartedAt**: 仍 2026-07-18T21:26:29Z (R1836 restart, R1839 至 R1868 未再 restart) → 跑 R1839 改后字节码.
- **/health**: ok (passthrough, nv_num_keys=5, models kimi_nv/dsv4p_nv/glm5_2_nv). docker ps 全 Up (nv_gw Up 4h / cc4101 Up 17h / ms_gw Up 45h / logs_db Up 2d).

## 决策理由
介入触发四条全不满足:
1. SR 93.8% > 93 连续9轮在93上 (远>93阈值, 连破计数0).
2. fallback 非跳过类真请求失败 0 <4 (5 条全 SKIP-CIRCUIT bug3 抢断).
3. NV-ANTH-BREAKER-FAIL 全 CLOSED 未 OPEN, 且 state 第二字段停在 3 未续增 (R1867 盯的"是否触 OPEN"否决答案).
4. 无新可配置错误分类 (stream_first_byte_timeout 为已知 NVCF 侧 timeout 偶发分类, 非新增).
4 条 502 全 NVCF 侧偶发外分支 config 不可修 → 硬改违反铁律 (改前必有数据 + 无据不改).

## 验证结果
链路稳 (SR 93.8% > 93 连续9轮) + bug8 0 触发 (DB+log 双确认) + breaker 全 CLOSED 未 OPEN (state 3 未续增, 否决 R1867 OPEN 顾虑) + fallback 非跳过类 0 + 0 中断 + 0 restart + tier pexec 无 ATE/SSLEOF/429 timeout + /health ok + env 无漂移 + md5 一致. StartedAt 仍 21:26:29Z 跑 R1839 改后字节码. 连续 25 轮 NOP (R1842-R1868) 链路稳态.

## 下轮
R1869 继续常规巡检. 重点:
- **nv_breaker state**: 本轮停在 3 未续增是好消息. 续盯 state 第二字段是否仍停留/续增/触 OPEN (若触 OPEN 需查 upstream/key 软挂源, 但 OPEN 本身是 R1839 兜底动作非源码 bug, 真正该看是否频繁复现 OPEN).
- **SR**: 若 <93 只算 1 轮新破, 不能与旧 R1856 92.6 + R1857 90.2 拼成 3 触发线 (R1858 94.7 已打断), 需重新累积连续 3 轮破 93.
