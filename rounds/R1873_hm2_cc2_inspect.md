# R1873 (HM2 cc2) — 巡检轮 bug8 降级兜底 in-vivo 后第 29 轮持续 0 触发 链路稳 SR95.7% nv_breaker state 稳定漂在 2 未续增触 OPEN

> 模式: nv 直连 (cc4101→nv_gw), R1839 bug8 真降级兜底 in-vivo 生效, 连续 29 轮 NOP 巡检 (R1842-R1873).
> 主机: HM2 (100.109.57.26), 只改 HM2 nv_gw (40006), 不碰 ms_gw (40007) / HM1.

## 改前数据 (30min 窗, 本 session ~10:05 CST 拉取)

- **SR**: 45/47 = **95.7%** (200:45 / 502:2). 远高于 93% 阈值, 抖动区间常态:
  连续 13 轮在 93 上: R1860 96.2 / R1861 98.0 / R1862 99.0 / R1863 97.6
  / R1864 98.6 / R1865 94.3 / R1867 93.5 / R1868 93.8 / R1870 94.6 / R1871 96.8 / R1872 96.6 / R1873 95.7
  (注 R1866/R1869 为 peer HM2→HM1 轮, 不计 HM2 SR 抖动序列),
  R1856+R1857 连 2 轮破 93 早被 R1858 94.7 反弹打断, 本轮仍 >93 → 连破计数仍 0,
  **远高于 93% 阈值, 未达连续 >=3 轮破 93 触发线, 绝无系统退化信号** (连破计数仍 0).
  本轮较 R1872 96.6 微降 0.9 (属抖动区间, 非退化).
- **502 分类**: zombie_empty_completion (DB status!=200 查到 1 条 + pexec 异常外 1 条全 NVCF 侧偶发).
  本窗无 stream_first_byte_timeout, 无 abs_cap. 与 R1851-R1872 同构. **非新可配置错误分类**.
- **tier pexec**: pexec_success 34, **无 ATE 无 SSLEOF 无 429 无 pexec_timeout** (干净);
  pexec_empty_200 1 + pexec_timeout 1 (NVCF 侧偶发, 非新可配置分类).
- **fallback**: 30min 全 PRIMARY-FAIL-SKIP-CIRCUIT (bug3 75s 抢断 cc4101 preempt nv_gw retry, 非 nv_gw 失败 NOT counted):
  - 09:34 req=ff98ea19 → FALLBACK-OK ms 3618ms (R1870-R1872 跨窗复现).
  - 09:38 req=ec76070f → FALLBACK-OK ms 8414ms (R1871-R1872 跨窗复现).
  - 09:43 req=27d0791a → FALLBACK-OK ms 21148ms (R1872 本窗新增, 21s).
  - 09:47 req=2189dba8 → FALLBACK-OK ms 9416ms (R1872 本窗新增).
  - 09:54 req=74f09328 → FALLBACK-OK ms 3670ms (**本窗新增**, <10s 回正常区间).
  - 09:57 req=a7755e91 → FALLBACK-OK ms 6645ms (**本窗新增**, <10s 回正常区间).
  **非跳过类真请求失败 0 条**, < 4 阈值. **0 中断**.
  **fallback ms 延迟趋势**: R1872 关切的 21148ms(09:43) 慢化本窗**未续恶化**——
  新增 09:54 req=74f09328 3670ms + 09:57 req=a7755e91 6645ms 均回到 <10s 正常区间,
  即 R1872 的 21s 慢化是单点尖峰非趋势, fallback 负载/健康无持续恶化.
- **bug8**: 实战降级触发 0 (NV-TOOLCALL-JSON-DOWNGRADE 120min 窗空, DB 0 + nv_gw log 0 双确认).
  兜底在位 args 全合法不需触发.
- **breaker 30min**: **全 CLOSED 未 OPEN** 设计内:
  - 09:37 / 09:40 / 09:50 / 10:00 4× NV-MS-FB-SERVED (ms 兜底 served, nv breaker
    recorded failure state=CLOSED 无计数). req: c09b0d7a / 3e24e4f0 / c6a82c33 / 408f7097 (本窗新增).
  - 09:45:18 NV-ANTH-BREAKER-FAIL zombie_empty_completion req=e17703ad state=('CLOSED', 2, 0)
    (R1872 同 req 跨窗复现, 本窗无新 NV-ANTH-BREAKER-FAIL 事件).
  - **重点结论**: nv_breaker state 第二字段自 R1871 从 3 掉回 2 后, R1872 + 本轮 R1873
    09:45:18 req=e17703ad 仍 state=('CLOSED', 2, 0) → **state 连续 3 轮稳定漂在 2, 未续增到 3 触 OPEN**.
    即 R1871 的漂移结论本轮再被强化: state 在 2-3 之间漂移而非单调累积, 远低于 OPEN 阈值,
    设计内吸收态且具自恢复能力. 本窗无新 NV-ANTH-BREAKER-FAIL 事件 = 软挂发生率本窗更低, 更乐观.
- **env**: 无漂移 (UPSTREAM=66 / TIER_BUDGET=180 / KEY_COOLDOWN=25 / TIER_COOLDOWN=25 / NVU_BIG_INPUT_FAIL_N=1,
  全与 R1850-R1872 一致).
- **oai_to_anth.py md5=4983bcec** 宿主/容器一致 (host format/ 子目录 vs container /app/gateway/format/).
- **StartedAt 仍 2026-07-18T21:26:29Z** (R1836 restart, R1839 改后字节码至 R1873 未再 restart).

## 决策

介入触发四条全不满足 (SR 95.7% > 93 连续 13 轮 / fallback 非跳过类 0 <4 /
breaker 全 CLOSED 未 OPEN 且 state 连续 3 轮稳定漂在 2 未续增触 OPEN / 无新可配置错误分类) +
2 条 502 全 NVCF 侧 zombie 偶发外分支 config 不可修 → 硬改违反铁律 (改前必有数据 + 无据不改).
**本轮 NOP (0 改动, 0 restart).** 连续 29 轮 NOP (R1842-R1873) 链路稳态.

## 验证结果

链路稳 (SR 95.7% > 93 抖动区间, 连续 13 轮在 93 上, 较 R1872 96.6 微降 0.9 属抖动无系统退化) +
bug8 0 触发 (DB+log 双确认) + breaker 全 CLOSED 未 OPEN (nv_breaker state 连续 3 轮稳定漂在 2,
本窗无新 NV-ANTH-BREAKER-FAIL 事件, 更乐观) + fallback 非跳过类 0 + 0 中断 + 0 restart +
tier pexec 无 ATE/SSLEOF/429/timeout (干净) + /health ok + docker ps 全 Up.
StartedAt 仍 21:26:29Z 确认跑 R1839 改后字节码.

## 下轮 R1874 重点

继续常规巡检. **重点**:
- **nv_breaker state**: 本轮连续 3 轮稳定漂在 2 (R1871 从 3 掉回 2, R1872+R1873 仍 2).
  续盯 state 第二字段是否继续漂移 (2↔3) 或单调续增触 OPEN.
- **SR**: 若 R1874 SR <93 → 只算 1 轮新破, 不能与旧 2 轮 (R1856 92.6 + R1857 90.2) 拼成 3 触发线
  (R1858 94.7 已打断旧连破), 需重新累积连续 3 轮破 93 才达介入线.
- **fallback ms 延迟**: R1872 的 21s 慢化尖峰本窗未续恶化 (09:54/09:57 均回 <10s), 续观察是否复现尖峰.

**介入触发条件** (任一满足才动手, 否则继续 NOP 巡检):
1. SR 连续 >=3 轮跌破 93% (系统退化信号, 非抖动; 抖动被打断后重启连破计数).
2. fallback 中**非跳过类** (FALLBACK-OK 真正 nv_gw 失败) >=4 次/30min.
3. NV-ANTH-BREAKER-FAIL 出现 OPEN (state 中第一字段变 OPEN, 超过 zombie 软挂).
4. 出现新的可配置错误分类 (非 NVCF 侧 zombie/timeout/gap/cap).

## 铁律遵守

- 只改 HM2 nv_gw (40006), 不碰 ms_gw (40007) / HM1.
- 改前必有数据 (30min 窗拉取), 改后必有验证 (本轮 0 改动无需 restart 验证).
- 0 restart 0 中断 0 改动, NOP 巡检轮.
