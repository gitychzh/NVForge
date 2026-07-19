# R1867 (HM2 cc2): 巡检轮 bug8 降级兜底 in-vivo 后第24轮持续0触发 链路稳 SR93.5% 抖动区间连续24轮NOP

## 改前数据 (30min 窗, 09:16 CST 拉取)

### SR
- 200:58 / 502:4 → **SR 58/62 = 93.5%**
- 远 > 93% 阈值, 较 R1865 (94.3%) 小幅回落但仍 > 93
- 连续 8 轮 SR 在 93 上: R1859 95.2 / R1860 96.2 / R1861 98.0 / R1862 99.0 / R1863 97.6
  / R1864 98.6 / R1865 94.3 / R1867 本轮 93.5 (R1866 为 peer 改 HM1 轮, 不计 HM2 SR 抖动序列)
- R1856+R1857 连 2 轮破 93 早被 R1858 94.7 反弹打断, 本轮仍 >93 → 连破计数仍 0, 无系统退化信号

### 502 错误分类 (NVCF 侧)
| error_type | count | 备注 |
|------------|-------|------|
| zombie_empty_completion | 4 | NVCF 侧偶发外分支, config 不可修, 与 R1851-R1865 同构 |
- 0 条新可配置错误分类

### tier pexec (30min)
- pexec_success: 51
- pexec_empty_200: 2 (NVCF 侧偶发, 合法范围)
- **0 ATE / 0 SSLEOF / 0 429 / 0 pexec_timeout**

### fallback (cc4101 30min, 5 条 FALLBACK-OK)
| 时间 | req | 类型 | ms | counted? |
|------|-----|------|-----|----------|
| 08:48 | bd1e7e59 | PRIMARY-FAIL-SKIP-CIRCUIT | 4611 | NOT (bug3 75s 抢断) |
| 08:56 | 7efcb96e | PRIMARY-FAIL-SKIP-CIRCUIT | 3783 | NOT |
| 08:59 | 2c1be8a6 | PRIMARY-FAIL-SKIP-CIRCUIT | 2311 | NOT |
| 09:10 | c9a8bb9f | PRIMARY-FAIL-SKIP-CIRCUIT | 5380 | NOT (本窗新增) |
| 09:12 | 2a4164b0 | PRIMARY-FAIL-SKIP-CIRCUIT | 1960 | NOT (本窗新增) |
- **非跳过类真请求失败 0 条** < 4 阈值, **0 中断**
- 全 bug3 75s 抢断 (cc4101 preempt nv_gw retry), 非 nv_gw 失败

### bug8 降级触发 (120min 双确认)
- DB nv_requests error_type ilike '%downgrade%|%TOOLCALL-JSON%': **0**
- nv_gw log grep TOOLCALL-JSON-DOWNGRADE|bad_tool_args|downgrade_to_end_turn: **0**
- 兜底在位 args 全合法不需触发, 符合 R1839 原话

### breaker 30min (nv_gw log)
- 08:53 NV-ANTH-BREAKER-FAIL zombie req=2f0c7368 state=('CLOSED', 2, 0)
- 09:03 NV-ANTH-BREAKER-FAIL zombie req=b14f6431 state=('CLOSED', 3, 0)
- 09:12+ 3× NV-MS-FB-SERVED (ms 兜底 served, breaker recorded failure state=CLOSED) req=cf0e880d / 8faab390 / etc
- **全 CLOSED 未 OPEN**, nv_breaker state 第二字段 1→2→3 (延续 R1865, 仍远低于 OPEN 阈值, 设计内吸收)
- 注: 本轮 abs_cap 0 (R1863-R1865 同 req=0ec13c01 的 237s 单请求超长本轮未出现)

### env 快照 (无漂移)
```
KEY_COOLDOWN_S=25
TIER_COOLDOWN_S=25
UPSTREAM_TIMEOUT=66
TIER_TIMEOUT_BUDGET_S=180
NVU_BIG_INPUT_FAIL_N=1
MIN_OUTBOUND_INTERVAL_S=0
```

### 字节码一致性
- oai_to_anth.py md5=4983bcec1d1203a1f3f8acf371786c6c 宿主/容器一致
- StartedAt = 2026-07-18T21:26:29Z (R1836 restart, R1839 至 R1867 未再 restart → 跑 改后字节码)
- bug8 四要素全在

### /health
```json
{"status":"ok","proxy_role":"passthrough","nv_num_keys":5,"nvcf_pexec_models":["kimi_nv","dsv4p_nv","glm5_2_nv"],"port":40006}
```

## 改了什么
NOP (不改). 无 compose env / 无 .py 改动. 0 restart.

## 验证结果
- 链路稳: SR 93.5% > 93 抖动区间, 连续 8 轮在 93 上, 无系统退化
- bug8 0 触发 (DB+log 双确认)
- breaker 全 CLOSED 未 OPEN (nv_breaker state 1→2→3 仍设计内吸收)
- fallback 非跳过类 0 + 0 中断 + 0 restart
- tier pexec 无 ATE/SSLEOF/429 + /health ok
- 连续 24 轮 NOP (R1842-R1867) 链路稳态

## 决策理由
介入触发四条全不满足:
1. SR 连续 ≥3 轮跌破 93%: 本轮 93.5 > 93 不破, 连破计数 0
2. fallback 非跳过类 ≥4: 0 < 4
3. NV-ANTH-BREAKER-FAIL OPEN: 全 CLOSED
4. 新可配置错误分类: 4 条全 NVCF zombie 不可修

→ 硬改违反铁律 (改前必有数据 + 无据不改). 4 条 502 全 NVCF 侧 zombie_empty_completion config 不可修.

## 下一轮该做什么
继续常规巡检. **重点盯**:
1. nv_breaker state 第二字段累积趋势 (本轮 1→2→3 续增但全 CLOSED): 若续增至触 OPEN 需查 upstream/key 软挂源 (R1839 breaker 设计本就是"宁可 OPEN 走 ms 也不死循环", OPEN 是兜底动作非 bug, 真信号是 OPEN 频繁复现).
2. SR: 若下一轮 <93 → 只算 1 轮新破, 不能与旧 R1856 92.6 + R1857 90.2 拼成 3 触发线 (R1858 94.7 已打断旧连破), 需重新累积连续 3 轮破 93 才达介入线.

注: peer 已起草 R1866_hm2_optimize_hm1 (KEY/TIER 50→48 改 HM1), 与我 R1867 一并 commit, peer 文件只改 HM1 符合铁律, 对我 HM2 (KEY=25) 0 影响.

### 介入触发条件 (任一满足才动手)
1. SR 连续 ≥3 轮 < 93%
2. fallback 非跳过类 ≥4 次/30min
3. NV-ANTH-BREAKER-FAIL OPEN
4. 新可配置错误分类

全不满足 → 继续 NOP 巡检, 维持 bug8 兜底在位观测.
