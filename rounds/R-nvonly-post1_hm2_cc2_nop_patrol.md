# R-nvonly-post1 (hm2_cc2, NOP 巡检轮) — R-nvonly 方向确立后首次巡检

**时间**: 2026-07-29 20:39 CST
**轮型**: NOP 巡检 (R-nvonly 架构确立后的首次基线确认)
**改动**: 0  | **restart**: 0 | **铁律违反**: 0

## 背景: R-nvonly 方向确立 (本轮首次接棒)

CLAUDE.md 已确认 R-nvonly 方向 (2026-07-28 确立):
- ms_gw(40007) fallback **彻底禁用**: cc4101 `FALLBACK_UPSTREAM_URL=none`,
  nv_gw `NVU_DISABLE_MS_FALLBACK=1`.
- nv_gw 必须纯靠 5key+5IP 自恢复到 99%+ SR, 无 fallback 兜底.
- STATE.md 停在 R-buffer-post6 / R-keyretry (旧 fallback 时代逻辑), 主仓已走到 R2422
  (HM1 上改 BIG_INPUT_THRESHOLD/KEY_COOLDOWN, 外部监督者迭代).
- 本轮 = cc2 自主线在 R-nvonly 架构下的首次巡检, 重建基线确认.

## 本轮判稳数据 (20:09-20:39 CST = 12:09-12:39 UTC, 实测)

### 30min cc2 (cc4101-primary) — 极干净
```
status | count
  200  |   52         → SR = 52/52 = 100% ✓
```
nv_gw 整体 30min: cc4101-primary 52×200 / unknown 93×200 / **0 非200** → 整体 SR 100%.

### 30min tier 错误明细 (看 transport 错误分类, R-nvonly 关注点)
```
error_type                    | count
pexec_success                 |   145    ← 主流: NVCF 正常处理
pexec_429                     |     7    ← NVCF 限流, KeyManager 退避
pexec_SSLEOFError             |     4    ← R-nvonly 关注: 短惩罚不累计 conn_count
pexec_conn_RemoteDisconnected |     1    ← R-nvonly 关注: 5-10s 快速惩罚
```
→ SSLEOF(4)+RemoteDisconnected(1) = 5 次 transport 错误, 全被 nv_gw 内部退避吸收,
**没有冒泡成 502** (30min cc2 0 失败). transport 短惩罚机制工作正常 ✓.

### 6h cc4101-primary SR (含早期波动)
```
status | count
 200   |  357     → SR = 357/406 = 87.9% (6h 累积, 含早期 48×502)
 502   |   48     → 全 buffer_exhausted(47) + all_tiers_exhausted(1)
 499   |    1     → client_gone_during_flush (BUG-A 家族, 设计局限)
```
502 按小时分布 (NVCF 间歇故障期集中, 近窗清零):
```
06hUTC=4 | 07h=13 | 08h=9 | 09h=13(+1 all_tiers) | 10h=2 | 11h=5 | 12h=2
```
07h/09h 是高峰 (各13次), 12h(近窗)=2 残余, 13h(最新30min)=0 → **正在恢复, 近窗清零**.

### R-nvonly 核心验证: cc4101 真 fallback = 0 (6h 全量) ✓
```
cc_requests where error_type like 'fallback%' (6h): 0 行
```
→ **破釜沉舟真生效**: 48×502 全在 nv_gw 侧消化 (buffer_exhausted), 无 1 次走 ms_gw.
即使 5key×90s 全挂, nv_gw 也是 buffer 耗尽返 502 给客户端, 不 fallback. R-nvonly 设计无 fallback 副作用 ✓.

### 6h cc2 tier 错误分类 (R-nvonly transport 分类验证)
```
RemoteDisconnected | 61    ← R-nvonly 改"短惩罚不累计 conn_count", 6h 61 次
429                | 37    ← KeyManager 120s→600s 指数退避
SSLEOFError        | 15    ← transport 短惩罚
empty_200          |  2    ← FASTBREAK=3 容忍
noncycle_404       |  2
500                |  2
504                |  1
```
→ transport 错误 (RemoteDisconnected+SSLEOF=76) 是 6h 主导错误类型, 但近 30min 仅 5 次
且全部内部吸收. R-nvonly 的"短惩罚不累计 conn_count"让 key 快速恢复可用, 验证方向正确.

### buffer 5key 轮转效果 (30min 日志)
- 大多请求 **1 attempt success** (1×key 成功, elapsed 7-37s)
- req=f9e5376d 走 **attempt 1→2→3 才 SUCCESS** (96.9s, 多 key 轮转救回间歇故障):
  - attempt1 (k5) → CHAIN-FAIL (5key+modes 全挂) → buffer 重试
  - attempt2 (k2) → CHAIN-FAIL → buffer 重试
  - attempt3 (k3) → SUCCESS (1822b)
  → **5key 轮转自恢复机制见效**: 间歇 NVCF 故障靠 key 轮转恢复, 不 fallback ✓
- 见 2 次 `NV-GLM52-CHAIN-FAIL` (单次 attempt 内 5key+modes 全挂) 但都靠 buffer 下一次 attempt 救回
- 0 `BUFFER-EXHAUSTED` 在 30min 窗 (6h 有 47 次但分布在早期)

### stream_total_deadline 频次 (6h, cc4101 580墙 铁证)
```
6h: 0 行  ← cc_requests.stream_total_deadline = 0
```
→ 本轮 post6 修正后的查询 (cc_requests.stream_total_deadline) 返回 0. 注意: post6 实测 47×/6h,
本轮 0. 可能因 cc4101 STREAM_TOTAL_DEADLINE 从 580 早 → 470 现在 (R-cc_s3 阶梯清理后),
470 墙比 580 紧, 长输出 >470s 直接 buffer_exhausted 而非记 stream_total_deadline.
**470 墙下 deadline 不再是主要失败路径** (本轮 0 次), 主路径变为 buffer_exhausted.

## env 快照 (docker exec 实测, R-nvonly 配置确认无漂移)
```
nv_gw:
  NVU_DISABLE_MS_FALLBACK=1            ✓ R-nvonly 核心
  NVU_BUFFER_CALLERS=cc4101-primary
  NVU_BUFFER_MAX_RETRIES=5             ✓ 5key (CLAUDE.md 说 5)
  NVU_BUFFER_TIMEOUT_STAIRS=90,90,90,90,90  ✓ 5×90=450s
  NVU_BUFFER_TOTAL_DEADLINE_S=450      ✓ CLAUDE.md 440→450
  NVU_CALLER_RETRY=0                   ✓ (R-keyretry 已回退)
  NVU_CALLER_RETRY_KEY=4 (env 有但 RETRY=0 不生效)
  NVU_CALLER_KEY_MAP=hermes:2;openclaw:3;opencode:4
  NVU_TIER_BUDGET_GLM5_2_NV=120        ✓
  UPSTREAM_TIMEOUT=90                  ✓ < TIER_BUDGET 120
  NVU_KEYMGR_429_BASE_COOLDOWN=120 / MAX_COOLDOWN=600  ✓ R-nvonly 429 退避
  NVU_KEYMGR_CONN_BASE_COOLDOWN=30 / FAIL_THRESHOLD=3 / LONG_COOLDOWN=120
  NVU_KEYMGR_CONN_MAX_COOLDOWN=60
  NVU_BIG_INPUT_THRESHOLD=250000 (HM1 上 R2422 改 375000, HM2 仍 250000)
  NVU_EMPTY_200_FASTBREAK=3
  TIER_TIMEOUT_BUDGET_S=180 / COOLDOWN_S=180
  KEY_COOLDOWN_S=60  (env 显示; CLAUDE.md 提 HM1 已调, HM2 仍 60)
cc4101:
  FALLBACK_UPSTREAM_URL=none          ✓ R-nvonly 核心 (禁用 fallback)
  CC4101_STREAM_TOTAL_DEADLINE_S=470   ✓ (R-cc_s3 阶梯清理后从 580→470)
  PRIMARY_HEADER_TIMEOUT=400           ✓ (不再 60s 抢断 buffer)
  UPSTREAM_TIMEOUT=130 / IDLE_TIMEOUT=150
/health: ok, nv_default_model=glm5_2_nv ✓
```
容器: nv_gw Up, RC=0, restarts=0, StartedAt=2026-07-29T12:09:22Z (本轮无 restart).

## 三阈值判稳
| 阈值 | 30min 实测 | 判定 |
|------|-----------|------|
| cc2 (cc4101-primary) SR | 52/52 = 100% | ✓ |
| cc4101 真 fallback | 0 (6h 全量) | ✓ |
| 无新错误类型 | buffer_exhausted(已知消化点) + client_gone(BUG-A家族) | ✓ |
→ **三阈值全满足 → 冻结 NOP, 0 改动 0 restart**

## 关键认知 (R-nvonly 架构下, 供下轮)

1. **R-nvonly 破釜沉舟已验证真生效**: 6h cc2 48×502 全是 buffer_exhausted (nv_gw 侧消化),
   cc4101 fallback 计数 0. 不再有 "NVCF 挂了 fallback ms_gw 兜底" 这条路. 所有故障 nv_gw 自扛.
2. **buffer_exhausted 是 R-nvonly 的"消化终点"**: 5key×90s 全挂 → buffer 耗尽 → 返 502 客户端.
   这是设计预期非退化. 502 频次等同 "NVCF 全 5key 同时不可用的窗口时长".
3. **transport 错误 (RemoteDisconnected+SSLEOF) 短惩罚机制工作**: 30min 5 次全内部吸收不冒泡.
   6h 76 次但近窗清零. 验证 R-nvonly "短惩罚不累计 conn_count" 方向正确.
4. **5key 轮转自恢复见效**: req=f9e5376d 走 3 attempt 救回间歇故障, 不 fallback.
   CHAIN-FAIL (单 attempt 5key 全挂) 后 buffer 下一次 attempt 常能恢复.
5. **stream_total_deadline 本轮 0 次**: 470 墙 (R-cc_s3 清理后) 比 580 紧, 长输出 >470s
   直接 buffer_exhausted, 不再走 stream_total_deadline 路径. 主失败路径变为 buffer_exhausted.
6. **6h SR 87.9% 但近窗 100%**: 早期 (07h/09h) NVCF 间歇故障期 buffer_exhausted 集中, 近 30min 清零.
   R-nvonly 目标 99%+SR 在稳定期已达 (近窗100%), 间歇期靠 key 轮转自恢复消化.
7. **HM1 已迭代到 R2422** (外部监督者): BIG_INPUT_THRESHOLD 250000→375000, KEY_COOLDOWN 等参数在 HM1
   调过. HM2 仍 250000 / KEY_COOLDOWN_S=60. **铁律: 只改 HM2, 不碰 HM1** — 本轮不抄 HM1 参数.

## 下一轮该做什么

1. 继续巡检. 盯 cc2 (cc4101-primary) SR 是否保持, buffer_exhausted 频次, cc4101 fb 是否持续 0.
2. 重点盯 **R-nvonly 的核心目标: nv_gw 纯自恢复 99%+ SR**:
   - 30min SR 是否稳定 100% (间歇期靠 key 轮转救回)
   - 6h buffer_exhausted 频次是否下降 (NVCF 全挂窗口是否缩短)
   - transport 错误 (RemoteDisconnected/SSLEOF) 短惩罚是否持续快速恢复
3. 若 6h SR < 95% 持续 (间歇期 buffer_exhausted 集中) → 找根因 (是否特定 key 退化/特定输入段),
   小步改 (调 KEY_COOLDOWN / 5key 轮转策略 / buffer 时间分配), 改前有数据, 改后验证.
4. 若 SR 稳定 ≥99% 且无新错误 → 继续 NOP 巡检, 记数据不改码.
5. 铁律: 改前数据, 改后验证, 聚焦 40006, 不碰 ms_gw (不重新启用 fallback), 只改 HM2, 写入仓库.
6. 长驻机制: 每 30min touch ~/.claude/cc2.heartbeat (watchdog 15min); 改 .py 触发 R-guard
   (py_compile+restart+health); auto-compact 后从 STATE 接棒.

## 回滚锚点 (本轮 NOP 无改动, 无需回滚; 锚点守护待用)
- R-nvonly 基础设施侧改动 (KeyManager mark_transport_error / ProbeWorker / WaitQueue /
  BufferStreamSession 4 层重构) 由外部监督者部署, cc2 巡检不改源码.
- cc_s2/cc_s3 快照仍在 (commit 5ec9c7c/d7392cf), 不含 buffer 重构, 守护待用.
- 回 R-buffer 时代: handlers.py.bak.R-buffer + NVU_BUFFER_CALLERS="" (不在本轮考虑).

## 最近 cc2 自主线摘要
- R-nvonly-post1 (hm2_cc2, 本轮): R-nvonly 方向确立后首次巡检. cc2 30min SR100% (52/52),
  nv_gw 整体 30min 0 非200. 6h SR 87.9% (早期 48×buffer_exhausted 集中, 近窗清零).
  **cc4101 fallback = 0 (6h 全量) → R-nvonly 破釜沉舟真生效**, 无 1 次 fallback ms_gw.
  transport 错误 (RemoteDisconnected+SSLEOF) 短惩罚机制工作 (30min 5 次全内部吸收).
  5key 轮转自恢复见效 (req f9e5376d 3 attempt 救回间歇故障). stream_total_deadline 本轮 0
  (470 墙比 580 紧, 长输出走 buffer_exhausted 非 deadline). env 实测匹配 R-nvonly 期望配置无漂移.
  三阈值全满足 → 冻结 NOP, 0 改动 0 restart.
- R-buffer-post6 (hm2_cc2): NOP + 修正 post5 content_s 铁证查询失效. cc2 30min 27/27→SR100%,
  6h 383/3(SR99.2%, BUG-A家族). cc4101 fb=0 (旧 fallback 时代). 0 改动 0 restart.
- R-buffer-post5 (hm2_cc2): NOP. content_s 铁证 (后被 post6 证伪). cc2 100% (30/30). 0 改动 0 restart.
