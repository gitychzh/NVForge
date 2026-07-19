# R1861 (HM2 cc2): 巡检轮 bug8 降级兜底 in-vivo 后第19轮持续0触发 链路稳SR98.0%创近期新高连续上扬抖动区间常态连续19轮NOP

## 改前数据 (30min 窗, 本 session 拉取)
- SR: **100/102 = 98.0%** (200:100 / 502:2). **创近期新高, 连续 4 轮上扬**:
  近 9 轮 R1853 94.8% / R1854 94.7% / R1855 94.6% / R1856 92.6% / R1857 90.2% / R1858 94.7% / R1859 95.2% / R1860 96.2% / R1861 本轮 98.0%,
  R1856+R1857 连 2 轮破 93 早被 R1858 94.7 反弹打断, R1859 95.2 + R1860 96.2 + R1861 98.0 连续 3 轮上扬,
  **远高于 93% 阈值, 未达连续 >=3 轮破 93 触发线, 绝无系统退化信号**。
- 2 条 502 = 1 zombie_empty_completion + 1 stream_absolute_cap,
  **全 NVCF 侧偶发外分支 config 不可修** (与 R1851-R1860 同构).
- tier pexec: success 78 / NVCFPexecTimeout 1 / pexec_empty_200 1 / pexec_timeout 1, **无 zombie 无 ATE**.
- fallback 2 条:
  - 07:59 req=063ad0de PRIMARY-FAIL-SKIP-CIRCUIT (bug3 75s 抢断 cc4101 preempt nv_gw retry, 非 nv_gw 失败 NOT counted)
    → 后 FALLBACK-OK ms 成功 (2912ms 递进合法).
  - 08:25 req=5081e9ef PRIMARY-FAIL-SKIP-CIRCUIT (同 bug3 75s 抢断 NOT counted)
    → 后 FALLBACK-OK ms 成功 (3171ms 递进合法).
  **非跳过类真请求失败 0 条**, < 4 阈值. **0 中断**.
- bug8: 实战降级触发 0 (NV-TOOLCALL-JSON-DOWNGRADE 120min 窗空). 兜底在位 args 全合法不需触发,
  符合 R1839 round 文件原话"兜底保险就该几乎不触发".
- breaker 30min:
  - 1 NV-ANTH-ABS-CAP (cap_elapsed=221s 超 150s, 与 R1857-R1860 一致, 比 R1852-R1856 的 159s 变长, 单请求墙钟逃逸) → NV-ANTH-BREAKER-FAIL state=('CLOSED', 2, 0) 未 OPEN.
  - 1 NV-ANTH-BREAKER-FAIL zombie err (req=6b47318d) state=('CLOSED', 1, 0) 未 OPEN.
  **全 CLOSED**, 设计内.
  注: abs_cap 221s 调高 STREAM_ABS_CAP 150s 检测线 = 死循环请回复, 违反 CLAUDE.md 不动.
- env 无漂移: UPSTREAM_TIMEOUT=66 / TIER_TIMEOUT_BUDGET_S=180 / KEY_COOLDOWN_S=25 / KEY_AUTHFAIL_COOLDOWN_S=60 /
  TIER_COOLDOWN_S=25 / NVU_BIG_INPUT_FAIL_N=1 / NVU_BIG_INPUT_COOLDOWN_S=180 / NV_INTEGRATE_KEY_COOLDOWN_S=90 /
  MIN_OUTBOUND_INTERVAL_S=0 (全与 R1850-R1860 一致).
- oai_to_anth.py md5=4983bcec1d1203a1f3f8acf371786c6c (550 行) 宿主/容器一致:
  host `/opt/cc-infra/proxy/nv-gw/gateway/format/oai_to_anth.py`
  container `/app/gateway/format/oai_to_anth.py`.

## 改了什么
NOP (不改). 无 compose env / 无 .py 改动. 0 restart.
- StartedAt = **2026-07-18T21:26:29Z** (= R1836 restart, R1839 至 R1861 未再 restart) → 跑 R1839 改后字节码.
- /health = ok (proxy_role=passthrough, nv_num_keys=5, nv_default_model=dsv4p_nv, port=40006).

## 验证结果
链路稳 (SR 98.0% 近 4 轮 94.7/95.2/96.2/98.0 连续上扬创近期新高) + bug8 0 触发 + breaker 全 CLOSED
+ fallback 非跳过类 0 + 0 中断 + 0 restart. StartedAt 仍 21:26:29Z 确认跑 R1839 改后字节码. /health ok.

## 决策理由
介入触发四条全不满足:
1. SR 连续 >=3 轮跌破 93%: **否** (本轮 98.0% 远高于 93, 近 4 轮连续上扬).
2. fallback 非跳过类 (FALLBACK-OK 真正 nv_gw 失败) >=4 次/30min: **否** (2 条全 SKIP-CIRCUIT bug3 抢断 NOT counted, 非跳过类 0).
3. NV-ANTH-BREAKER-FAIL 出现 OPEN: **否** (全 CLOSED (2,0)/(1,0)).
4. 出现新的可配置错误分类: **否** (2 条 502 全 NVCF 侧 zombie/abs_cap config 不可修).
四条全不满足, 且 2 条 502 全 NVCF 侧 config 不可修 → 硬改违反铁律 (改前必有数据 + 无据不改).
连续 19 轮 NOP (R1842-R1861) 链路稳态确认. bug8 兜底保险在位, 实战 0 触发符合设计原话.

## 下轮 R1862 重点
继续常规巡检. **优先看 SR**:
- 若 R1862 SR >=93% → 抖动区间常态确认, 继续 NOP 巡检.
- 若 R1862 SR <93% → 需看历史是否再累积连续 3 轮破 93 (R1856 92.6 + R1857 90.2 已被打断,
  新一轮破 93 只算 1 轮, 不能与旧 2 轮直接拼成 3 轮 — 抖动被打断后重启计数), 若此后连续 3 轮破 93
  才达触发线需介入排查 (介入仍需先定位可配置旋钮, 若 502 仍全 NVCF 侧 config 不可修则无法硬改, 仅记录归因).
注: 本轮 SR 98.0% 创新高, R1861 已是连续第 4 轮上扬, 链路处于抖动区间上沿常态.
