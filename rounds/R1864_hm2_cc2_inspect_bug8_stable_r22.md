# R1864 (HM2 cc2): 巡检轮 bug8 降级兜底 in-vivo 后第22轮持续0触发 链路稳

## 改前数据 (30min 窗, 本 session 拉取, 当前 08:51 CST)
- **SR 71/72 = 98.6%** (200:71 / 502:1). 远高于 93% 阈值, 抖动区间常态.
  近 12 轮 SR 走势: R1853 94.8 / R1854 94.7 / R1855 94.6 / R1856 92.6 / R1857 90.2
  / R1858 94.7 / R1859 95.2 / R1860 96.2 / R1861 98.0 / R1862 99.0 / R1863 97.6 /
  R1864 本轮 98.6. R1856+R1857 连 2 轮破 93 早被 R1858 94.7 反弹打断, 之后 R1859 95.2 +
  R1860 96.2 + R1861 98.0 + R1862 99.0 + R1863 97.6 + 本轮 98.6 连续 6 轮全在 93 上
  (R1863 小幅回落 97.6 后本轮 98.6 再回升, 仍在上扬区间内, 远 >93).
  绝无系统退化信号, 未达连续 >=3 轮破 93 触发线.
- **1 条 502** = 1 stream_absolute_cap, **全 NVCF 侧偶发外分支 config 不可修**
  (与 R1851-R1863 同构; 本轮无 zombie_empty_completion, 较近几轮更干净).
- tier pexec: success 64, **无 zombie 无 ATE 无 SSLEOF 无 429** (干净);
  empty_200 1 / pexec_empty_200 1 / pexec_timeout 1 (NVCF 侧偶发, 合法范围内).
- **fallback 4 条** (全 PRIMARY-FAIL-SKIP-CIRCUIT, bug3 75s 抢断 cc4101 preempt nv_gw
  retry, 非真 nv_gw 失败 NOT counted):
  - 08:25 req=5081e9ef after 75033ms → FALLBACK-OK ms 3171ms (与 R1862/R1863 同 req 跨窗复现).
  - 08:31 req=9d25f4eb after 75073ms → FALLBACK-OK ms 10516ms (与 R1863 同 req 跨窗复现).
  - 08:38 req=488d38a8 after 75083ms → FALLBACK-OK ms 5204ms (与 R1863 同 req 跨窗复现).
  - 08:48 req=bd1e7e59 after 75040ms → FALLBACK-OK ms 4611ms (新增本窗).
  **非跳过类真请求失败 0 条**, 远 < 4 阈值. **0 中断**.
- **bug8**: 实战降级触发 0 (NV-TOOLCALL-JSON-DOWNGRADE 120min 窗空, DB 0 + nv_gw log 0 双确认).
  兜底保险在位, args 全合法不需触发, 符合 R1839 原话"兜底保险就该几乎不触发".
- **breaker 30min**: 1 条全 CLOSED 未 OPEN, 设计内:
  - 1 NV-ANTH-ABS-CAP (cap_elapsed=237s, 与 R1863 同 req=0ec13c01 跨窗复现同 237s,
    仍超 150s 单请求墙钟逃逸, 全 NVCF 侧单个请求超长不可配置修) → 1 NV-ANTH-BREAKER-FAIL
    stream_absolute_cap (req=0ec13c01) CLOSED(1,0).
  注: 本轮无 zombie breaker (R1863 有 1 条 zombie req=6b47318d, 本轮该 req 滚出 30min 窗).
- env 无漂移 (UPSTREAM=66 / TIER_BUDGET=180 / KEY_COOLDOWN=25 / NVU_BIG_INPUT_FAIL_N=1,
  全与 R1850-R1863 一致).
- oai_to_anth.py md5=4983bcec1d1203a1f3f8acf371786c6c (550 行) 宿主/容器一致
  (host `/opt/cc-infra/proxy/nv-gw/gateway/format/oai_to_anth.py`
   vs container `/app/gateway/format/oai_to_anth.py`), bug8 四要素全在.
- nv_gw StartedAt = 2026-07-18T21:26:29Z (R1836 restart, R1839-R1864 未再 restart) → 跑改后字节码.
- /health ok, docker ps nv_gw/cc4101/ms_gw/logs_db 全 Up.

## 改动
NOP (不改). 无 compose env / 无 .py 改动. 0 restart.

## 决策理由
介入触发四条全不满足:
1. SR 连续 >=3 轮跌破 93%: 否 (本轮 SR 98.6% 远 >93; 近 12 轮仅 R1856 92.6 + R1857 90.2 破过,
   已被 R1858 94.7 反弹打断, 之后连续 6 轮 95.2/96.2/98.0/99.0/97.6/98.6 全在 93 上).
2. fallback 非跳过类 >=4: 否 (0 条, 4 条全 SKIP-CIRCUIT bug3 抢断 NOT counted).
3. NV-ANTH-BREAKER-FAIL OPEN: 否 (1 条 CLOSED(1,0) 未 OPEN).
4. 新可配置错误分类: 否 (1 条 502 全 NVCF 侧 abs_cap, 与历史同构配置不可修).
→ 硬改违反铁律 (改前必有数据 + 无据不改). 维持 NOP 巡检.

## 验证结果
链路稳 (SR 98.6% 远 >93 抖动区间常态, 较 R1863 97.6 小幅回升仍在上扬区间无退化)
+ bug8 0 触发 (DB+log 双确认) + breaker 全 CLOSED 未 OPEN + fallback 非跳过类 0 + 0 中断
+ 0 restart + tier pexec 无 zombie 无 ATE 无 SSLEOF 无 429 + /health ok. StartedAt 仍 21:26:29Z
确认跑 R1839 改后字节码. 连续 22 轮 NOP (R1842-R1864) 链路稳态.

## 下轮 R1865 重点
拉数据后优先看 SR:
- 若 R1865 SR >=93% → 抖动区间常态确认, 继续 NOP 巡检.
- 若 R1865 SR <93% → 只算 1 轮新破, 不能与旧 2 轮 (R1856 92.6 + R1857 90.2) 直接拼成 3 轮触发线
  (R1858 94.7 已打断旧连破), 需重新累积连续 3 轮破 93 才达介入线.
介入触发条件不变 (任一满足才动手):
1. SR 连续 >=3 轮跌破 93% (系统退化信号, 非抖动; 抖动被打断后重启连破计数).
2. fallback 中非跳过类 (FALLBACK-OK 真正 nv_gw 失败) >=4 次/30min.
3. NV-ANTH-BREAKER-FAIL 出现 OPEN (state 中第一字段变 OPEN, 超过 zombie 软挂).
4. 出现新的可配置错误分类 (非 NVCF 侧 zombie/timeout/gap/cap).
若以上都不满足, 继续 NOP 巡检轮, 维持 bug8 兜底在位观测.
