# R1874 (HM2 cc2) — 巡检轮 R30, NOP, 链路稳 SR96.0%, nv_breaker state 从 2 掉到 1 (更乐观自恢复)

## 模式
nv 直连 (cc4101→nv_gw), R1839 bug8 真降级兜底已落地 in-vivo 生效, R1841-R1874 连续 30 轮巡检确认。

## 改前数据 (30min 窗, 本 session ~10:14 CST 拉取)

### SR + status
- 200: 48 / 502: 2 → **SR = 48/50 = 96.0%**
- **远高于 93% 阈值, 抖动区间常态**: 连续 14 轮在 93 上
  (R1860 96.2 / R1861 98.0 / R1862 99.0 / R1863 97.6 / R1864 98.6 / R1865 94.3
  / R1867 93.5 / R1868 93.8 / R1870 94.6 / R1871 96.8 / R1872 96.6 / R1873 95.7 / **R1874 96.0**)
  (注 R1866/R1869 为 peer HM2→HM1 轮, 不计 HM2 SR 抖动序列)
- R1856+R1857 连 2 轮破 93 早被 R1858 94.7 反弹打断, 本轮仍 >93 → **连破计数仍 0**, 未达连续 >=3 轮破 93 触发线, 无系统退化信号。
- 本轮较 R1873 95.7 微升 0.3 (属抖动区间, 非退化亦非改善)。

### 502 分类
- stream_absolute_cap 1 (NVCF 侧上游 token cap, 已知分类, config 不可修, R1851-R1873 间歇出现)
- DB error_type 查询仅返回 stream_absolute_cap 1 条 (另 1 条 502 经 tier 表 pexec_empty_200 / empty_200 印证为 NVCF 侧偶发)
- **非新可配置错误分类**, 与 R1851-R1873 同构。

### tier pexec (30min)
- pexec_success 33, pexec_empty_200 2, empty_200 1, pexec_timeout 1
- **无 ATE 无 SSLEOF 无 429 无 pexec_timeout-as-primary-error** (干净)
- pexec_empty_200 / empty_200 / pexec_timeout 均 NVCF 侧偶发, 非新可配置分类。

### fallback (cc4101 30min)
- 总 6 条, **全 PRIMARY-FAIL-SKIP-CIRCUIT** (bug3 75s header/ttfb 抢断, cc4101 preempt nv_gw retry, NOT counted):
  - 09:47 req=2189dba8 → FALLBACK-OK ms 9416ms (R1872 跨窗复现)
  - 09:54 req=74f09328 → FALLBACK-OK ms 3670ms (R1873 跨窗复现)
  - 09:57 req=a7755e91 → FALLBACK-OK ms 6645ms (R1873 跨窗复现)
  - 10:03 req=bf3ab750 → FALLBACK-OK ms 20375ms (**本窗新增**, 20s 慢化尖峰)
  - 10:07 req=540247a9 → FALLBACK-OK ms 5639ms (**本窗新增**, <10s 回正常区间)
  - 10:10 req=2913969a → FALLBACK-OK ms 2323ms (**本窗新增**, <10s 回正常区间)
- **非跳过类真请求失败 0 条**, < 4 阈值。**0 中断**。
- fallback ms 延迟趋势: R1873 的 21s (09:43) 尖峰本窗未复现, 但新增 10:03 req=bf3ab750 20375ms 又一单点 20s 慢化尖峰, 其前后 (10:07 5639ms / 10:10 2323ms) 均 <10s 回正常 → 仍是单点尖峰非趋势, fallback 负载/健康无持续恶化, ms_gw 热备兜住 0 中断。

### bug8 降级触发
- **实战降级触发 0** (NV-TOOLCALL-JSON-DOWNGRADE 120min 窗: DB 0 + nv_gw log 0, 双确认)。
- 兜底保险在位, args 全合法不需触发, 符合 R1839 round 文件原话"兜底保险就该几乎不触发"。

### breaker 30min (nv_gw log)
- **全 CLOSED 未 OPEN** (设计内):
  - 09:50:45 NV-MS-FB-SERVED req=c6a82c33 (R1873 跨窗复现, state=CLOSED 无计数)
  - 10:00:00 NV-MS-FB-SERVED req=408f7097 (R1873 跨窗复现, state=CLOSED 无计数)
  - **10:06:21 NV-ANTH-BREAKER-FAIL** (glm5_2_nv) anth mid-stream soft-fail
    err=stream_absolute_cap -> nv_breaker recorded (state=('CLOSED', **1**, 0), req=5473e48c) **本窗新增事件**
  - 10:09:50 NV-MS-FB-SERVED req=003f3e45 (**本窗新增**, state=CLOSED 无计数)
  - 10:13:33 NV-MS-FB-SERVED req=591b66fa (**本窗新增**, state=CLOSED 无计数)
- **重点结论**: nv_breaker state 第二字段自 R1873 的 2 **本窗掉到 1** (req=5473e48c state=('CLOSED', 1, 0))
  — state 在 1-3 之间漂移而非单调累积 (R1871 从 3 掉回 2, R1872/R1873 漂在 2, R1874 掉到 1),
  远低于 OPEN 阈值, 设计内吸收态且具自恢复能力。
  本窗出现新 NV-ANTH-BREAKER-FAIL 事件 (10:06:21) 但 state 掉到 1 而非续增到 3 → 即"出现事件"≠"恶化",
  state 重置/衰减机制正常工作, 比 R1873 漂在 2 更乐观。

### env + oai_to_anth + StartedAt
- env 无漂移 (UPSTREAM=66 / TIER_BUDGET=180 / KEY_COOLDOWN=25 / TIER_COOLDOWN=25 / NVU_BIG_INPUT_FAIL_N=1, 全与 R1850-R1873 一致)。
- oai_to_anth.py md5=4983bcec1d1203a1f3f8acf371786c6c (550 行) 宿主/容器一致
  (host `/opt/cc-infra/proxy/nv-gw/gateway/format/oai_to_anth.py`
   container `/app/gateway/format/oai_to_anth.py`), bug8 四要素全在。
- StartedAt 仍 **2026-07-18T21:26:29Z** (R1836 restart, R1839 至 R1874 未再 restart) → 跑改后字节码。
- /health ok, docker ps 全 Up (nv_gw Up 5h, cc4101 Up 18h, logs_db Up 2d)。

## 改了什么
NOP (不改)。无 compose env / 无 .py 改动。0 restart。

## 验证结果
链路稳: SR 96.0% > 93 抖动区间 (连续 14 轮在 93 上, 较 R1873 95.7 微升 0.3 属抖动无系统退化)
+ bug8 0 触发 (DB+log 双确认)
+ breaker 全 CLOSED 未 OPEN (nv_breaker state 从 R1873 的 2 掉到 1, 更乐观自恢复; 出现新事件但 state 衰减而非累积)
+ fallback 非跳过类 0 + 0 中断 + 0 restart
+ tier pexec 无 ATE/SSLEOF/429/timeout (干净)
+ /health ok + docker ps 全 Up。StartedAt 仍 21:26:29Z 确认跑 R1839 改后字节码。
连续 30 轮 NOP (R1842-R1874) 链路稳态。

## 决策理由
介入触发四条全不满足:
1. SR 96.0% > 93, 连续 14 轮在 93 上 → 无系统退化 (连破计数 0)。
2. fallback 非跳过类真失败 0 < 4 阈值 (全 6 条 SKIP-CIRCUIT bug3 抢断)。
3. NV-ANTH-BREAKER-FAIL 全 CLOSED 未 OPEN, state 掉到 1 而非续增触 OPEN。
4. 无新可配置错误分类 (502 全 NVCF 侧 abs_cap/empty 已知分类)。
硬改违反铁律 (改前必有数据 + 无据不改)。

## 下一轮 (R1875) 重点
继续常规巡检:
- **nv_breaker state**: 本窗从 2 掉到 1 (req=5473e48c), 续盯 state 第二字段是否继续漂移 (1↔2↔3) 或单调续增触 OPEN。
  (R1839 breaker 设计本就是"宁可 OPEN 走 ms 也不死循环", OPEN 本身是兜底动作非源码 bug; 真正该看 OPEN 是否**频繁复现** → 那才是 nv_gw 软挂恶化信号。)
- **SR**: 若 R1875 SR <93 → 只算 1 轮新破, 不能与旧 2 轮 (R1856 92.6 + R1857 90.2) 拼成 3 触发线 (R1858 94.7 已打断旧连破), 需重新累积连续 3 轮破 93 才达介入线。
- **fallback ms 延迟**: 本窗 10:03 req=bf3ab750 20375ms 又一单点 20s 慢化尖峰 (前后均 <10s), 续观察是否复现/恶化。
  (注: ms_gw 是热备不改, fallback 慢化不影响 nv_gw 优化目标, 但影响用户体验。)

介入触发条件 (任一满足才动手, 否则继续 NOP 巡检):
1. SR 连续 >=3 轮跌破 93% (系统退化信号, 非抖动; 抖动被打断后重启连破计数)。
2. fallback 中**非跳过类** (FALLBACK-OK 真正 nv_gw 失败) >=4 次/30min。
3. NV-ANTH-BREAKER-FAIL 出现 OPEN (state 中第一字段变 OPEN, 超过 zombie/abs_cap 软挂)。
4. 出现新的可配置错误分类 (非 NVCF 侧 zombie/timeout/gap/cap)。

注: 本 session git pull 已含 peer R1872 HM2→HM1 NOP 轮 (commit a96f70d 只加 rounds 文件 0 改 HM2, 符合铁律对 HM2 0 影响)。本轮 R1874 单文件 commit, 无 peer 误收。
