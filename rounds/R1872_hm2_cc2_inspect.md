# R1872 (HM2 cc2) — 巡检轮 bug8 降级兜底 in-vivo 后第 28 轮持续 0 触发 链路稳 SR96.6% nv_breaker state 稳定漂在 2 未续增触 OPEN

> 模式: nv 直连 (cc4101→nv_gw), R1839 bug8 真降级兜底 in-vivo 生效, 连续 28 轮 NOP 巡检 (R1842-R1872).
> 主机: HM2 (100.109.57.26), 只改 HM2 nv_gw (40006), 不碰 ms_gw (40007) / HM1.

## 改前数据 (30min 窗, 本 session ~09:51 CST 拉取)

- **SR**: 56/58 = **96.6%** (200:56 / 502:2).
  - 远 > 93% 阈值, 抖动区间常态. 连续 12 轮在 93 上:
    R1860 96.2 / R1861 98.0 / R1862 99.0 / R1863 97.6 / R1864 98.6 / R1865 94.3
    / R1867 93.5 / R1868 93.8 / R1870 94.6 / R1871 96.8 / R1872 96.6
    (注 R1866 为 peer 改 HM1 轮, R1869 为 peer HM2→HM1 NOP 轮, 不计 HM2 SR 抖动序列).
  - R1856+R1857 连 2 轮破 93 早被 R1858 94.7 反弹打断, 本轮仍 >93 → 连破计数仍 0,
    **未达连续 >=3 轮破 93 触发线, 绝无系统退化信号**.
  - 本轮较 R1871 96.8 微降 0.2 (属抖动区间, 非退化).

- **502 分类**: zombie_empty_completion 2. 注: 本轮**无** stream_first_byte_timeout
  (R1871 有 1, 本窗该类 0), 无 abs_cap. 2 条 502 全 NVCF 侧 zombie 偶发外分支 config 不可修,
  与 R1851-R1871 同构. **非新可配置错误分类**.

- **tier pexec 30min**: pexec_success 40, **无 ATE 无 SSLEOF 无 429 无 pexec_timeout** (干净);
  pexec_empty_200 1 + pexec_timeout 1 (NVCF 侧偶发, 非新可配置分类).

- **fallback 30min** (跨 R1871 拼接, 本窗新增两条):
  - 09:26 req=8ea3dfb7 → FALLBACK-OK ms 3611ms (与 R1867-R1871 同 req 跨窗复现).
  - 09:34 req=ff98ea19 → FALLBACK-OK ms 3618ms (与 R1870-R1871 同 req 跨窗复现).
  - 09:38 req=ec76070f → FALLBACK-OK ms 8414ms (与 R1871 同 req 跨窗复现, **R1871 关切慢一倍**).
  - 09:43 req=27d0791a → FALLBACK-OK ms 21148ms (**本窗新增, 较 ec76070f 再慢一倍+, 21s**) .
  - 09:47 req=2189dba8 → FALLBACK-OK ms 9416ms (**本窗新增, 慢但 <10s**).
  - **5 条全 PRIMARY-FAIL-SKIP-CIRCUIT** (bug3 75s 抢断 cc4101 preempt nv_gw retry, 非 nv_gw 失败 NOT counted),
    后 FALLBACK-OK ms 全成功. **非跳过类真请求失败 0 条**, < 4 阈值. **0 中断**.
  - **新现象**: fallback ms 延迟本窗有上升趋势 (8414ms→21148ms→9416ms), 仍 FALLBACK-OK 0 中断,
    但 R1871 关切的 ec76070f 8414ms 慢一倍现象本窗**复现且更慢** (21148ms). 续观察是否恶化.

- **bug8**: 实战降级触发 0 (NV-TOOLCALL-JSON-DOWNGRADE 120min 窗空, DB 0 + nv_gw log 0 双确认).
  兜底在位 args 全合法不需触发. 符合 R1839 round 文件原话"兜底保险就该几乎不触发".

- **breaker 30min**: **全 CLOSED 未 OPEN** 设计内:
  - 09:22 / 09:29 / 09:37 / 09:40 / 09:50 5× NV-MS-FB-SERVED (ms 兜底 served, nv breaker
    recorded failure state=CLOSED 无计数). req: a0ad8435 / 1c6a93bc / c09b0d7a / 3e24e4f0 / c6a82c33 (本窗新增).
  - 09:31:47 NV-ANTH-BREAKER-FAIL zombie_empty_completion req=ada74bbf state=('CLOSED', 2, 0)
    (R1871 同 req 跨窗复现).
  - **09:45:18 NV-ANTH-BREAKER-FAIL zombie_empty_completion req=e17703ad state=('CLOSED', 2, 0)** ← 本窗新增事件.
  - **重点结论**: R1871 新发现 nv_breaker state 第二字段从 3 掉回 2 (漂移/自恢复), 本轮 R1872
    新 req=e17703ad 记录 state=('CLOSED', 2, 0) → **state 仍稳定漂在 2, 未续增到 3 触 OPEN**.
    即 R1871 的漂移结论本轮被强化: state 在 2-3 之间漂移而非单调累积, 远低于 OPEN 阈值,
    设计内吸收态且具自恢复能力. 比单纯"停 3 未续增"更乐观, 比停 2 更稳.

- **env 无漂移** (UPSTREAM=66 / TIER_BUDGET=180 / KEY_COOLDOWN=25 / TIER_COOLDOWN=25 /
  NVU_BIG_INPUT_FAIL_N=1, 全与 R1850-R1871 一致).

- **oai_to_anth.py md5=4983bcec** 宿主/容器一致
  (host /opt/cc-infra/proxy/nv-gw/gateway/format/oai_to_anth.py
   container /app/gateway/format/oai_to_anth.py).

## 改动
**NOP (不改)**. 无 compose env / 无 .py 改动. 0 restart.

## 决策理由
介入触发四条全不满足:
1. SR 96.6% > 93, 连续 12 轮在 93 上, 连破计数 0 (R1858 94.7 已打断旧连破).
2. fallback 非跳过类 (FALLBACK-OK 真正 nv_gw 失败) 0 次/30min < 4.
3. NV-ANTH-BREAKER-FAIL 全 CLOSED 未 OPEN (state 第二字段稳定漂在 2, 未续增触 OPEN).
4. 无新可配置错误分类 (2× zombie 全 NVCF 侧偶发外分支 config 不可修).
→ 硬改违反铁律 (改前必有数据 + 无据不改). 维持 bug8 兜底在位观测.

## 验证结果
- /health ok, docker ps 全 Up (nv_gw Up 4h / cc4101 Up 18h / ms_gw Up 45h / logs_db Up 2d).
- StartedAt 仍 **2026-07-18T21:26:29Z** (R1836 restart, R1839 至 R1872 未再 restart) → 跑 R1839 改后字节码.
- oai_to_anth.py md5=4983bcec 宿主/容器一致, bug8 四要素全在.
- SR 96.6% > 93 抖动区间常态, bug8 0 触发, breaker 全 CLOSED 未 OPEN (state 漂在 2 未续增),
  fallback 非跳过类 0 + 0 中断 + 0 restart + tier pexec 无 ATE/SSLEOF/429/timeout (干净).
- 连续 28 轮 NOP (R1842-R1872) 链路稳态.
- **0 中断** (用户诉求 "可以报错但不能让 cc2 中断" 仍达成).

## 下一轮该做什么
继续常规巡检. **重点**: R1873 拉数据后:
- **nv_breaker state**: 本轮稳定漂在 2 (R1871 从 3 掉回 2, 本轮新 req 仍 2, 强化漂移结论).
  续盯 state 第二字段是否继续漂移 (2↔3) 或单调续增触 OPEN.
  (R1839 breaker 设计本就是"宁可 OPEN 走 ms 也不死循环", OPEN 本身是兜底动作非源码 bug;
  真正该看的是 OPEN 是否**频繁复现** → 那才是 nv_gw 软挂恶化信号, 需查 upstream/key 软挂源.)
- **SR**: 若 R1873 SR <93 → 只算 1 轮新破, 不能与旧 2 轮 (R1856 92.6 + R1857 90.2) 拼成 3 触发线
  (R1858 94.7 已打断旧连破), 需重新累积连续 3 轮破 93 才达介入线.
- **fallback ms 延迟上升趋势**: R1871 ec76070f 8414ms → 本窗 27d0791a 21148ms + 2189dba8 9416ms,
  仍 FALLBACK-OK 0 中断, 但 fallback 慢化是 ms_gw 侧负载/健康信号, 续观察是否复现/恶化.
  (注: ms_gw 是热备不改, fallback 慢化不影响 nv_gw 优化目标, 但影响用户体验.)

**介入触发条件** (任一满足才动手, 否则继续 NOP 巡检):
1. SR 连续 >=3 轮跌破 93% (系统退化信号, 非抖动; 抖动被打断后重启连破计数).
2. fallback 中**非跳过类** (FALLBACK-OK 真正 nv_gw 失败) >=4 次/30min.
3. NV-ANTH-BREAKER-FAIL 出现 OPEN (state 中第一字段变 OPEN, 超过 zombie 软挂).
4. 出现新的可配置错误分类 (非 NVCF 侧 zombie/timeout/gap/cap).
若以上都不满足, 继续 NOP 巡检轮, 维持 bug8 兜底在位观测.

## 注
- 仓库最新 commit = eca8087 (peer R1871 HM2→HM1 NOP 轮, 只加 rounds 文件 0 改 HM2 nv_gw, 符合铁律).
  本 session git pull 已含 peer 该轮, 对 HM2 0 影响.
- 本轮 R1872 单文件 commit (rounds/R1872_hm2_cc2_inspect.md), 无 peer 误收.
