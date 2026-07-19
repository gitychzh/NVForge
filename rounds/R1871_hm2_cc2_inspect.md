# R1871 (HM2 cc2) 巡检轮 — bug8 降级兜底 in-vivo 后第27轮持续0触发 链路稳 SR96.8% nv_breaker state 从3掉回2漂移(非单调累积)

## 改前数据 (30min 窗, 本 session ~09:45 CST 拉取)
- SR 60/62 = **96.8%** (200:60 / 502:2). 远 > 93% 阈值, 抖动区间常态:
  连续 11 轮在 93 上 (R1860 96.2 / R1861 98.0 / R1862 99.0 / R1863 97.6 / R1864 98.6
  / R1865 94.3 / R1867 93.5 / R1868 93.8 / R1870 94.6 / R1871 96.8),
  注 R1866 为 peer 改 HM1 轮, R1869 为 peer HM2→HM1 NOP 轮, 不计 HM2 SR 抖动序列.
  R1856+R1857 连 2 轮破 93 早被 R1858 94.7 反弹打断, 本轮仍 >93 → 连破计数仍 0.
  本轮较 R1870 94.6 小幅回升 (属抖动区间, 非退化). 无系统退化信号.
- 502 分类: zombie_empty_completion 1 + stream_first_byte_timeout 1. 注:
  stream_first_byte_timeout 属 NVCF 侧 timeout 偶发**已知分类** (非全新可配置分类,
  历史轮曾多次出现). 2 条 502 **全 NVCF 侧偶发外分支 config 不可修**, 与 R1851-R1870 同构.
  本轮无 abs_cap. **非新可配置错误分类**.
- tier pexec: pexec_success 40, **无 ATE 无 SSLEOF 无 429 无 pexec_timeout** (干净).
- fallback **5 条全 SKIP-CIRCUIT** (bug3 75s 抢断 cc4101 preempt nv_gw retry, 非 nv_gw 失败 NOT counted):
  - 09:12 req=2a4164b0 → FALLBACK-OK ms 1960ms (与 R1867-R1870 同 req 跨窗复现).
  - 09:19 req=b31ffce1 → FALLBACK-OK ms 3399ms (与 R1868-R1870 同 req 跨窗复现).
  - 09:26 req=8ea3dfb7 → FALLBACK-OK ms 3611ms (与 R1870 同 req 跨窗复现).
  - 09:34 req=ff98ea19 → FALLBACK-OK ms 3618ms (**本窗新增**).
  - 09:38 req=ec76070f → FALLBACK-OK ms 8414ms (**本窗新增**, 较前几条慢一倍但仍 OK 0 中断).
  **非跳过类真请求失败 0 条**, < 4 阈值. **0 中断**.
- bug8: 实战降级触发 0 (NV-TOOLCALL-JSON-DOWNGRADE 120min 窗空, DB 0 + nv_gw log 0 双确认).
  兜底在位 args 全合法不需触发.
- breaker 30min: **全 CLOSED 未 OPEN** 设计内:
  - 09:12 / 09:15 / 09:22 / 09:29 / 09:37 / 09:40 6× NV-MS-FB-SERVED
    (ms 兜底 served, nv breaker recorded failure state=CLOSED 无计数).
    注 req: 09:12 cf0e880d / 09:15 8faab390 / 09:22 a0ad8435 / 09:29 1c6a93bc
    / 09:37 c09b0d7a (本窗新增) / 09:40 3e24e4f0 (本窗新增).
  - **09:31:47 NV-ANTH-BREAKER-FAIL zombie_empty_completion req=ada74bbf state=('CLOSED', 2, 0)** ← 本窗新增事件.
  - **重点新现象/结论**: nv_breaker state 第二字段自 R1865 (09:03 req=b14f6431) 起停在 3,
    本轮 R1871 出现 **新 req=ada74bbf** 的 zombie breaker event, state 记录为 **('CLOSED', 2, 0)**,
    即 state 第二字段 **从 3 掉回 2** (不是续增到 4, 而是衰减/重置).
    这正面回答了 R1867-R1870 连续盯的"state 是否续增触 OPEN"问题:
    **state 不是单调累积, 而是在 2-3 之间漂移** (成功请求后重置或时间窗口衰减),
    远低于 OPEN 阈值, 设计内吸收态且具备自恢复能力. 比单纯"停 3 未续增"更乐观.
- env 无漂移 (UPSTREAM=66 / TIER_BUDGET=180 / KEY_COOLDOWN=25 / TIER_COOLDOWN=25 / NVU_BIG_INPUT_FAIL_N=1,
  全与 R1850-R1870 一致).
- oai_to_anth.py md5=4983bcec1d1203a1f3f8acf371786c6c (550 行) 宿主/容器一致
  (host `/opt/cc-infra/proxy/nv-gw/gateway/format/oai_to_anth.py`
   container `/app/gateway/format/oai_to_anth.py`), bug8 四要素全在.
- nv_gw 真实 StartedAt = 2026-07-18T21:26:29Z (= R1836 restart, R1839 至 R1871 未再 restart) → 跑改后字节码.
- /health ok: `{"status":"ok","proxy_role":"passthrough","nv_num_keys":5,...,"port":40006}`.

## 改了什么
NOP (不改). 无 compose env / 无 .py 改动. 0 restart.

## 决策理由
介入触发四条全不满足:
1. SR 96.8% > 93, 连续 11 轮在 93 上, 连破计数 0 → 未达"连续 >=3 轮破 93"触发线.
2. fallback 非跳过类 0 条 < 4 阈值 (5 条全 SKIP-CIRCUIT bug3 抢断 NOT counted).
3. NV-ANTH-BREAKER-FAIL 全 CLOSED 未 OPEN, 且 state 第二字段从 3 掉回 2 (漂移非累积), 远低于 OPEN 阈值.
4. 无新可配置错误分类 (2 条 502 全 NVCF 侧偶发已知分类, config 不可修).
→ 硬改违反铁律 (改前必有数据 + 无据不改). 维持 bug8 兜底在位观测节奏.

## 验证结果
链路稳 (SR 96.8% > 93 抖动区间, 连续 11 轮在 93 上, 较 R1870 94.6 小幅回升属抖动无系统退化) +
bug8 0 触发 (DB+log 双确认) + breaker 全 CLOSED 未 OPEN (nv_breaker state 从 3 掉回 2 漂移,
正面回答"是否续增触 OPEN"——非单调累积, 设计内吸收且具自恢复) +
fallback 非跳过类 0 + 0 中断 + 0 restart + tier pexec 无 ATE/SSLEOF/429/timeout (干净) +
/health ok. StartedAt 仍 21:26:29Z 确认跑 R1839 改后字节码. 连续 27 轮 NOP (R1842-R1871) 链路稳态.

## 下轮重点
R1872 拉数据后:
- **nv_breaker state**: 本轮从 3 掉回 2 是新发现 (漂移/自恢复), 比停 3 更乐观. 续盯 state 第二字段
  是否继续漂移或单调续增触 OPEN. OPEN 本身是兜底动作非源码 bug, 真正该看的是 OPEN 是否**频繁复现**.
- **SR**: 若 R1872 SR <93 → 只算 1 轮新破, 不能与旧 2 轮 (R1856 92.6 + R1857 90.2) 拼成 3 触发线
  (R1858 94.7 已打断旧连破), 需重新累积连续 3 轮破 93 才达介入线.
- **fallback 09:38 req=ec76070f 8414ms 慢一倍**: 本窗新现象, 但仍 FALLBACK-OK 0 中断, 续观察是否复现/恶化.

## 注
- 本 session git pull 已含 peer R1870 HM2→HM1 调参轮 (commit 76cbbea, KEY/TIER 48→46 只改 HM1, 符合铁律, 对 HM2 KEY=25 0 影响).
- commit 1a4dfa6 = 上一 session (我) 的 R1870 cc2 轮. 本轮 R1871 为 cc2 序列续号.
