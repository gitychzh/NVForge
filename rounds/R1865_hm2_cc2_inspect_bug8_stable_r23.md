# R1865 (HM2 cc2): 巡检轮 bug8 降级兜底 in-vivo 后第23轮持续0触发 链路稳

## 改前数据 (30min 窗, 本 session 拉取, 当前 09:04 CST)
- **SR 66/70 = 94.3%** (200:66 / 502:4). 远高于 93% 阈值, 抖动区间常态.
  近 13 轮 SR 走势: R1853 94.8 / R1854 94.7 / R1855 94.6 / R1856 92.6 / R1857 90.2
  / R1858 94.7 / R1859 95.2 / R1860 96.2 / R1861 98.0 / R1862 99.0 / R1863 97.6 /
  R1864 98.6 / R1865 本轮 94.3. R1856+R1857 连 2 轮破 93 早被 R1858 94.7 反弹打断,
  R1859 95.2 + R1860 96.2 + R1861 98.0 + R1862 99.0 + R1863 97.6 + R1864 98.6
  连续 6 轮全在 93 上, 本轮 94.3 较 R1864 98.6 回落但**仍在 93 上**
  (连续 7 轮全 >=94.3 > 远 >93).
  绝无系统退化信号, 未达连续 >=3 轮破 93 触发线 (当前连破计数仍 0).
- **4 条 502** = 4 zombie_empty_completion + 1 stream_absolute_cap (502 行=4, error_type
  视角 zombie 4 + abs_cap 1 同 req 复现, 与 R1851-R1864 同构全 NVCF 侧偶发外分支
  config 不可修). 本轮 zombie 数 (涉及 2 个 req) 较 R1864 (0 zombie) 增多, 但同属
  NVCF 侧 zombie_empty_completion 偶发分类, 非新可配置错误分类.
- tier pexec: success 66, **无 ATE 无 SSLEOF 无 429**;
  empty_200 1 / pexec_empty_200 1 / pexec_timeout 1 (NVCF 侧偶发, 合法范围内).
- **fallback 4 条** (全 PRIMARY-FAIL-SKIP-CIRCUIT, bug3 75s 抢断 cc4101 preempt nv_gw
  retry, 非真 nv_gw 失败 NOT counted):
  - 08:38 req=488d38a8 after 75083ms → FALLBACK-OK ms 5204ms (与 R1863/R1864 同 req 跨窗复现).
  - 08:48 req=bd1e7e59 after 75040ms → FALLBACK-OK ms 4611ms (与 R1864 同 req 跨窗复现).
  - 08:56 req=7efcb96e after 75052ms → FALLBACK-OK ms 3783ms (新增本窗).
  - 08:59 req=2c1be8a6 after 75082ms → FALLBACK-OK ms 2311ms (新增本窗).
  **非跳过类真请求失败 0 条**, < 4 阈值. **0 中断**.
- bug8 关键: 实战降级触发 0 (NV-TOOLCALL-JSON-DOWNGRADE 120min 窗空, DB 0 +
  nv_gw log 0 双确认). 兜底在位但 args 全合法不需触发, 符合 R1839 round 文件原话
  "兜底保险就该几乎不触发".
- breaker 30min: **3 条全 CLOSED 未 OPEN** 设计内:
  - 08:40 1 NV-ANTH-ABS-CAP (cap_elapsed=237s, 与 R1863/R1864 同 req=0ec13c01 跨窗
    复现同 237s, 仍超 150s 单请求墙钟逃逸, 全 NVCF 侧单个请求超长不可配置修)
    → 1 NV-ANTH-BREAKER-FAIL stream_absolute_cap (req=0ec13c01) state=CLOSED(1,0).
  - 08:53 1 NV-ANTH-BREAKER-FAIL zombie_empty_completion (req=2f0c7368) state=CLOSED(2,0).
  - 09:03 1 NV-ANTH-BREAKER-FAIL zombie_empty_completion (req=b14f6431) state=CLOSED(3,0).
  注: nv_breaker state 本轮在累积 (1→2→3), 但全 CLOSED, 阈值未达 OPEN. 第二字段
  (consecutive soft-fail) 3 仍远低于 OPEN 阈值, 设计内吸收中. 需后续轮盯是否续增.
  本轮无 OPEN = 链路未到软挂逃逸逃出阈值的程度.
- env 无漂移 (UPSTREAM=66 / TIER_BUDGET=180 / KEY_COOLDOWN=25 / TIER_COOLDOWN=25 /
  NVU_BIG_INPUT_FAIL_N=1, 全与 R1850-R1864 一致).
- oai_to_anth.py md5=4983bcec1d1203a1f3f8acf371786c6c (550 行) 宿主/容器一致
  (host `/opt/cc-infra/proxy/nv-gw/gateway/format/oai_to_anth.py`
   container `/app/gateway/format/oai_to_anth.py`).
  bug8 四要素全在: `_detect_bad_tool_args()` + finish() 正常路径
  `_downgrade_to_end_turn` flag + 两处 final_stop 强制 end_turn.
- nv_gw 真实 StartedAt = **2026-07-18T21:26:29Z** (= R1836 restart, R1839 至 R1865
  未再 restart) → 跑 R1839 改后字节码. docker ps "Up 4 hours" 是容器创建时刻显示.
- /health ok (proxy_role=passthrough, 5 keys, glm5_2_nv 在 tiers). docker ps 全 Up.

## 改动
NOP (不改). 无 compose env / 无 .py 改动. 0 restart.

## 验证结果
链路稳 (SR 94.3% 远 >93 抖动区间常态, 较 R1864 98.6 回落但连续 7 轮全在 93 上仍
在上扬回踩区间无系统退化) + bug8 0 触发 (DB+mv log 双确认) + breaker 3 条全 CLOSED
未 OPEN (nv_breaker state 累积 1→2→3 但仍 CLOSED 设计内吸收, 盯后续是否续增触及 OPEN)
+ fallback 非跳过类 0 + 0 中断 + 0 restart + tier pexec 无 ATE 无 SSLEOF 无 429 +
/health ok. StartedAt 仍 21:26:29Z 确认跑 R1839 改后字节码. 连续 23 轮 NOP (R1842-R1865)
链路稳态.

## 决策理由
介入触发四条全不满足:
1. SR 94.3% 仍 >93, 连续 7 轮全在 93 上, 连续破 93 计数 0 → 无系统退化信号.
2. fallback 非跳过类 0 < 4 阈值 (4 条全 bug3 75s 抢断 SKIP-CIRCUIT NOT counted).
3. NV-ANTH-BREAKER-FAIL 全 CLOSED 未 OPEN (state 第二字段 1/2/3 增长但未达 OPEN).
4. 无新可配置错误分类 (4 zombie + 1 abs_cap 全 NVCF 侧偶发, 与历史同构).
四条全不满足 → 硬改违反铁律 (改前必有数据 + 无据不改). abs_cap 237s 调高破坏安全网不动.

## 下轮该做什么
继续常规巡检. **重点**: R1866 拉数据后 **优先盯 nv_breaker state 累积趋势** (本轮 1→2→3):
- 若 R1866 nv_breaker state 第二字段续增至触及 OPEN 阈值 → 触发线 3 满足, 需动手
  (但 R1839 breaker 设计本就是"宁可 OPEN 走 ms 也不死循环", OPEN 本身是兜底动作,
  非 nv_gw 源码 bug; 真正该看的是 OPEN 是否频繁复现 → 那是 nv_gw 软挂恶化信号).
- 若 R1866 SR <93 → 只算 1 轮新破, 不能与旧 2 轮 (R1856 92.6 + R1857 90.2) 拼成
  3 触发线 (R1858 94.7 已打断旧连破), 需重新累积连续 3 轮破 93 才达介入线.

介入触发条件 (任一满足才动手, 否则继续 NOP 巡检):
1. SR 连续 >=3 轮跌破 93% (系统退化信号, 非抖动; 抖动被打断后重启连破计数).
2. fallback 中非跳过类 (FALLBACK-OK 真正 nv_gw 失败) >=4 次/30min.
3. NV-ANTH-BREAKER-FAIL 出现 OPEN (state 中第一字段变 OPEN, 超过 zombie 软挂).
4. 出现新的可配置错误分类 (非 NVCF 侧 zombie/timeout/gap/cap).
若以上都不满足, 继续 NOP 巡检轮, 维持 bug8 兜底在位观测.
注: 连续 23 轮 NOP (R1842-R1865) 链路稳态. SR 近 8 轮 95.2/96.2/98.0/99.0/97.6/98.6/94.3 在 93 上抖动, 无退化数据, 不主动改.
