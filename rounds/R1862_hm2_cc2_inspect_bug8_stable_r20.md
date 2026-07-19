# R1862 (HM2 cc2): 巡检轮 — bug8 降级兜底 in-vivo 后第 20 轮持续 0 触发, 链路稳 SR 99.0% 创近期新高连续 5 轮上扬抖动区间常态连续 20 轮 NOP

## 改前数据 (30min 窗, 本 session 拉取)

- **SR 99/100 = 99.0%** (200:99 / 502:1). **创近期新高, 连续 5 轮上扬**:
  近 10 轮 R1853 94.8% / R1854 94.7% / R1855 94.6% / R1856 92.6% / R1857 90.2% / R1858 94.7% / R1859 95.2% / R1860 96.2% / R1861 98.0% / R1862 本轮 99.0%,
  R1856+R1857 连 2 轮破 93 早被 R1858 94.7 反弹打断, R1859 95.2 + R1860 96.2 + R1861 98.0 + R1862 99.0 连续 4 轮上扬,
  **远高于 93% 阈值, 未达连续 >=3 轮破 93 触发线, 绝无系统退化信号**。
- **1 条 502 = zombie_empty_completion**, **全 NVCF 侧偶发外分支 config 不可修** (与 R1851-R1861 同构). 本轮是近 20 轮 502 最少 (仅 1 条)。
- **tier pexec: success 77**, 无 zombie 无 ATE 无 SSLEOF 无 429 无 timeout 无 empty_200 (近 20 轮最干净)。
- **fallback 2 条**:
  - 08:25 req=5081e9ef PRIMARY-FAIL-SKIP-CIRCUIT (bug3 75s 抢断 cc4101 preempt nv_gw retry, 非 nv_gw 失败 NOT counted)
    → 后 FALLBACK-OK ms 成功 (3171ms 递进合法).
  - 08:31 req=9d25f4eb PRIMARY-FAIL-SKIP-CIRCUIT (同 bug3 75s 抢断 NOT counted)
    → 后 FALLBACK-OK ms 成功 (10516ms 递进合法, 比 R1861 的 ms 稍慢但在合法范围).
  **非跳过类真请求失败 0 条**, < 4 阈值. **0 中断**.
- **bug8**: 实战降级触发 0 (NV-TOOLCALL-JSON-DOWNGRADE 120min 窗空, DB 0 + nv_gw log 0 双确认). 兜底在位 args 全合法不需触发, 符合 R1839 round 文件原话"兜底保险就该几乎不触发"。
- **breaker 30min**: **1 条** NV-ANTH-BREAKER-FAIL zombie (req=6b47318d) state=CLOSED(1,0), **未 OPEN**。
  注: 本轮 **abs_cap 0** (R1861 有 1 条 221s abs_cap, R1862 无, 单请求墙钟逃逸本轮未出现), 全 CLOSED 设计内。
- **env 无漂移** (UPSTREAM=66 / TIER_BUDGET=180 / KEY_COOLDOWN=25 / NVU_BIG_INPUT_FAIL_N=1, 全与 R1850-R1861 一致)。
- **oai_to_anth.py md5=4983bcec1d1203a1f3f8acf371786c6c** (550 行) 宿主/容器一致
  (host `/opt/cc-infra/proxy/nv-gw/gateway/format/oai_to_anth.py`
   container `/app/gateway/format/oai_to_anth.py`), bug8 四要素全在 (`_detect_bad_tool_args` + finish 正常路径 `_downgrade_to_end_turn` flag + 两处 final_stop 强制 end_turn)。

## 验证结果

链路稳 (SR 99.0% 创近期新高, 近 5 轮 94.7/95.2/96.2/98.0/99.0 连续上扬) + bug8 0 触发 + breaker 全 CLOSED (本轮无 abs_cap) +
fallback 非跳过类 0 + 0 中断 + 0 restart + tier pexec 全 success + /health ok。
StartedAt 仍 2026-07-18T21:26:29Z (R1836 restart, R1839 至 R1862 未再 restart) → 确认跑 R1839 改后字节码。

## 决策 (NOP, 0 改动)

介入触发四条全不满足:
1. SR 99.0% 远 > 93 且连续 5 轮上扬创新高 → 无系统退化。
2. fallback 非跳过类 (FALLBACK-OK 真正 nv_gw 失败) 0 < 4。
3. NV-ANTH-BREAKER-FAIL 未 OPEN (只 1 条 zombie CLOSED(1,0))。
4. 无新可配置错误分类 (1 条 502 全 NVCF 侧 zombie)。

+ 1 条 502 全 NVCF 侧 config 不可修 → 硬改违反铁律 (改前必有数据 + 无据不改)。NOP 巡检轮。

## 巡检计数

bug8 降级兜底 in-vivo 后连续 20 轮巡检 (R1842-R1862) 持续 0 触发, 链路稳态。本轮是第 20 轮。
SR 近 5 轮上扬 (94.7→95.2→96.2→98.0→99.0) 创近期新高, 无退化数据, 不主动改。用户诉求 (2026-07-19 01:40) "可以报错但不能让 cc2 中断" 仍达成 (本轮 0 中断)。

## 下轮 R1863 重点

拉数据后优先看 SR:
- 若 R1863 SR >=93% → 抖动区间常态确认, 继续 NOP 巡检。
- 若 R1863 SR <93% → 只算 1 轮新破, 不能与旧 2 轮 (R1856 92.6 + R1857 90.2) 直接拼成 3 轮触发线
  (R1858 94.7 已打断旧连破), 需重新累积连续 3 轮破 93 才达介入线。
- 介入触发条件 (任一满足才动手, 否则 NOP): SR 连续 >=3 轮破 93 / fallback 非跳过类 >=4/30min /
  NV-ANTH-BREAKER-FAIL OPEN / 新可配置错误分类。若全不满足维持 bug8 兜底在位观测 NOP。

## 0 restart 0 中断 0 改动

铁律遵守: 改前必有数据 (30min + tier + breaker + fallback + md5 全拉), 改后必有验证 (health/StartedAt/md5 确认),
聚焦 40006, 不碰 40007, 写入仓库 (本文件), 只改 HM2 不改 HM1, 尽量多走 glm5_2_nv 少走 glm5_2_ms。
