# R269 hm2_cc2 NOP 巡检轮 (2026-08-02 14:55 CST)

## 本轮动作
- 0 改动 / 0 restart / NOP 巡检轮.
- 接棒 R268, 复核 dsv4p_nv primary 链路 post266 DELEGATE 修复持续生效.
- 本轮新增证据: buffer 5key 全挂后**自恢复链路实测生效** (非流式 retry 第 2 次
  attempt 成功, ProbeWorker 唤醒路径验证).

## 数据依据 (30min 窗口 ~14:20-14:48 注入 + 14:55 复查)

### 1. cc4101-primary (cc2) 30min — 21 req, 16 200 / 5 502
- SR = 76% (表面), 5 个 502 全是 `all_tiers_exhausted`(2) + `buffer_exhausted`(3),
  avg_dur≈165025ms, `fallback_occurred=f` 全部, `tiers_tried_count=0` 全部.
- 按分钟趋势 (DB 实测): 502 集中在 06:28/06:30/06:31/06:32 UTC
  (14:28-14:32 CST), **06:34 (14:34) 之后全 200, 0 失败**.
- 注入摘要里的 `all_tiers_failed_in_mapped_tier` 子类是 extractor 产物,
  DB 实测 `error_subcategory` 全为 NULL, 不存在新错误模式.

### 2. 5 个 502 根因 = 一次性窗口 (非代码缺陷, 跨 R267/R268/R269 三轮一致)
- `nv_tier_attempts` 40min 仅 1 条 429 (k2 @06:24, 无关), 5 个 502 **零 tier
  attempt** → 全 key cooling 时 buffer 5 次 attempt 直接 `execute_failed`
  elapsed=0s, 没真正打 NVCF.
- 与 R267/R268 诊断一致: NVCF + ms_gw 同窗口 (14:26-14:30) 瞬时 429 风暴,
  一次性尾部.

### 3. 自恢复链路实测生效 (本轮新证据, 日志 14:35)
- 14:35:43 NVCF 全 5key 429 → `NV-GLOBAL-COOLDOWN` 标记全 cooling 180s
  (TIER_COOLDOWN).
- 非流式请求 (req=3a3dd02b) attempt=1 `execute_failed` elapsed=0s (全挂).
- `NV-BUFFER-BACKOFF` 退避 5s → attempt=2 → 14:35:57 `success_thinking`
  elapsed=6s, 200.
- 证明: ProbeWorker 后台探测 cooling key 恢复 → set Event 唤醒 WaitQueue →
  buffer 下一次 attempt 命中已恢复的 key. R-nvonly 设计的自恢复闭环在工作.

### 4. 干净窗口跨轮验证 (post266 DELEGATE 对 dsv4p_nv 持续生效)
- 14:34 后: 多 req 全 200, 0 fallback, 全走 `NV-BUFFER-EXEC-DELEGATE`
  (MODE_CHAIN 空委托 execute_request, integrate-first path).
- post266 buffer `_execute_and_drain` MODE_CHAIN 空委托修复在 dsv4p_nv 路径下
  持续生效.
- 最近 15min (14:42-14:55) cc4101-primary: 5×200 dsv4p_nv, 0 失败,
  dur 1.4-7.7s, 全 `fallback_occurred=f`.

## 判稳
- 5 个 502 = 一次性 429 风暴窗口波动, 14:32 后全 200, 无反复, 三轮一致.
- dsv4p_nv 链路健康, post266 修复持续生效, 自恢复闭环实测通过.
- 无新错误模式, 无需改码.
- → NOP 巡检轮, 0 改动 0 restart.

## 下一步
1. 持续观察 dsv4p_nv 在 cc2 primary 下 SR, 看是否有反复 502 窗口.
2. 若 `all_tiers_exhausted` + 零 tier attempt 反复出现, 考察 KeyManager 全挂
   判定是否过早 (buffer 应能等 ProbeWorker 唤醒后重试, 而非 0s execute_failed).
   本轮 14:35 日志显示退避 5s 后第 2 次 attempt 即成功, 说明现有 backoff 间隔
   已足够等 ProbeWorker 唤醒, 暂无需调.
3. 关注 dsv4p_nv 429 是否集中在特定 key/egress IP (本轮 k2/k3 各 1 次, 样本少).
