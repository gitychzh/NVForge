# R1844 (HM2 cc2) — 巡检轮: bug8 降级兜底 in-vivo 后第 3 轮持续 0 触发, 链路稳

> 轮号说明: peer HM1 agent 已写 R1843 ("HM2→HM1" 调参轮 commit cefe4fa), 故本轮从 R1844 起
> (git pull 后看最新号 +1, 防 peer 抢号)。

## 性质
**巡检轮 (不改代码不 restart, R1839 降级兜底 in-vivo 后第 3 轮持续观测)**。

## 依据 (STATE R1842 "下一轮该做什么")
1. bug8 降级兜底持续观测: `grep NV-TOOLCALL-JSON-DOWNGRADE` 有命中=真畸形被兜住, 0 命中=理想态。
2. bug8 旧观测标记必带 `-t` 确认 restart 21:26:29Z 之后才算真实漏网。
3. 链路稳巡检: SR≥95% + fallback 低位 + pexec max<60s。
4. bug3 深挖 (可���): 仅当 fallback 持续多轮窗内 ≥4 + pexec max≥200s 才算恶化。

## 改前数据 (30min 窗, 2026-07-19 06:51 CST, StartedAt 21:26:29Z = R1836 restart 后)

### nv_gw 成功率 (nv_requests, 30min)
```
status 200 = 65
status 502 = 2  (1 all_tiers_exhausted + 1 zombie_empty_completion)
```
- **30min SR = 65/67 = 97.0%**, 与 R1842 97.5% (79/81) 基本持平, 远高于 95% 安全线非边缘抖动。
- 2 条 502 全在降级路径之外分支 (NVCF 侧 tier 全挂 / tool 空内容), 非 R1839 降级路径问题。

### tier 30min (nv_tier_attempts)
```
pexec_success     57
pexec_empty_200    3
pexec_429          2
```
- 无 zombie / 无 IntegrateTimeout / 无 pexec_timeout / 无 pexec_SSLEOFError。
- pexec_429 x2 (NVCF 单 key 限流偶发非系统性)。

### pexec elapsed (nv_tier_attempts.error_type=pexec_success, 30min)
```
max_ms=53255  avg_ms=11472  ge60s=0  ge200s=0
```
- **max 53.3s / avg 11.5s / ≥60s 0 / ≥200s 0** — 比 R1842 (max 60.5s/avg 12.4s/≥60s 1) 还好,
  NVCF 侧持续自愈, 远好于 R1831 (max 288s)。无 ≥60s 慢流。

### fallback 30min (cc4101 日志)
- 06:29:38 f47a695b: PRIMARY-FAIL 75s timeout → SKIP-CIRCUIT (cc4101 75s ttfb 抢断甩 ms,
  bug3 75s 抢断非 nv_gw config 可控), FALLBACK-OK 6956ms 成功。
- 06:36:26 b3f771a3: PRIMARY-FAIL 75s timeout → SKIP-CIRCUIT, FALLBACK-OK 3406ms 成功。
- 06:21:31 c3eea079: PRIMARY-FAIL 120s timeout → FALLBACK-OK 5342ms (nv_gw 首字节超 chain
  budget 120s 合法故障递进)。
- **30min = 2 SKIP-CIRCUIT + 3 FALLBACK-OK**, 全 0 中断。
- 比 R1842 (1 SKIP-CIRCUIT) 多 1 条 bug3, 但 30min 窗内 2 条非系统性, **未达恶化阈值** (持续多轮 ≥4)。

### bug8 降级兜底 in-vivo 确认 (核心)
- **R1839 降级代码完整在位**: oai_to_anth.py md5=4983bcec 宿主/容器一致, StartedAt 21:26:29Z
  (R1836 restart, 未再 restart) → 跑改后字节码。
- **实战降级触发 = 0** (`docker logs -t --since 120m | grep NV-TOOLCALL-JSON-DOWNGRADE` 全空):
  120min 实战窗内 args 全合法, 降级路径未 fire — "兜底保险就该几乎不触发"。
- **bug8 旧观测标记带 -t 90min 窗 = 0**: restart 21:26:29Z 之后纯净窗 0 漏网
  (R1832/R1836 历史残留 docker logs 已滚出窗)。

### breaker / env
- NV-ANTH-BREAKER-FAIL 30min 0 条 (比 R1842 1 条少)。
- env 无漂移: UPSTREAM_TIMEOUT=66 / TIER_TIMEOUT_BUDGET_S=180 / KEY_COOLDOWN_S=25 /
  NVU_BIG_INPUT_FAIL_N=1 全与 R1842 快照一致。

## 决策 (不改代码)
当前链路 SR 97.0% (远高于 95% 安全线) + pexec 自愈 (max 53s 无 ≥60s, 比 R1842 还好) +
fallback 低位非恶化 (2 bug3 75s 抢断 + 1 120s timeout 合法递进, 0 中断) + bug8 降级兜底在位
实战 0 触发 + 旧标记 restart 后纯净窗 0 + breaker 0 条未 OPEN + env 无漂移 →
**无 nv_gw config 可改依据**。硬改违反"改前必有数据, 改后必有验证"铁律 → 巡检轮不动。
bug8 R1839 兜底落地后已连续 3 轮 (R1841+R1842+R1844) 0 触发 + restart 后窗 0 漏网, 治本持续确认。

## 验证 (无需 restart, 仅观测)
- `curl /health` ok (passthrough / 5 keys / pexec_models kimi_nv/dsv4p_nv/glm5_2_nv /
  nv_default_model=dsv4p_nv / port 40006)
- `docker inspect nv_gw --format StartedAt` = 2026-07-18T21:26:29Z (R1836 restart, 未再 restart)
- docker ps: nv_gw Up, ms_gw Up (热备未碰), cc4101 Up, logs_db Up
- env 无漂移 md5 同步 4983bcec
- **0 中断** (本轮无 restart, 全程直连, SR 97.0%, fallback 全 FALLBACK-OK)

## 仓库/铁律
- 本轮 0 生效代码改动 (仅写 round), 不 restart, StartedAt 仍 21:26:29Z (R1836)。
- 聚焦 40006, 不碰 40007 (ms_gw 热备未动), 只改 HM2 不改 HM1。
- commit + push origin/main。
