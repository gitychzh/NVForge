# R268 hm2_cc2 NOP 巡检轮 (2026-08-02 14:46 CST)

## 本轮动作
- 0 改动 / 0 restart / NOP 巡检轮.
- 接棒 R267, 复核 dsv4p_nv primary 链路 post266 DELEGATE 修复持续生效.

## 数据依据 (30min 窗口 14:15-14:45 注入 + 14:46 复查)

### 1. cc4101-primary (cc2) 30min — 25 req, 20 200 / 5 502
- SR = 80% (表面), 5 个 502 全是 `all_tiers_exhausted;buffer_exhausted`,
  avg_dur=165025ms.
- 按分钟趋势: 502 集中在 06:25/06:28/06:30 (14:25-14:30 CST), **06:34 (14:34)
  之后全 200, 0 失败**.

### 2. 5 个 502 根因 = 一次性窗口 (非代码缺陷)
- `nv_tier_attempts` 30min 仅 1 条 429 (key2, 无关), 5 个 502 **零 tier attempt** →
  全 key cooling 时 buffer 5 次 attempt 直接 `execute_failed` elapsed=0s, 没真正打
  NVCF.
- 与 R267 诊断一致: NVCF + ms_gw 同窗口 (14:26-14:30) 瞬时 429 风暴, 一次性尾部.

### 3. 干净窗口跨轮验证 (post266 DELEGATE 对 dsv4p_nv 持续生效)
- 14:32 后 (R267): 11 req 全 200, 0 fallback, 全 `nvcf_pexec`.
- 本轮 14:46 复查最近 12min: 11×200, 0 502, 最新请求 14:46.
- post266 buffer `_execute_and_drain` MODE_CHAIN 空委托 `execute_request` 修复在
  dsv4p_nv 路径下持续生效.

## 判稳
- 5 个 502 = 一次性窗口波动, 14:32 后全 200, 无反复.
- dsv4p_nv 链路健康, post266 修复持续生效, 无新错误模式.
- → NOP 巡检轮, 0 改动 0 restart.

## 下一步
1. 持续观察 dsv4p_nv 在 cc2 primary 下 SR, 看是否有反复 502 窗口.
2. 若 `all_tiers_exhausted` + 零 tier attempt 反复出现, 考察 KeyManager 全挂
   判定是否过早 (buffer 应能等 ProbeWorker 唤醒后重试, 而非 0s execute_failed).
3. 关注 dsv4p_nv 429 是否集中在特定 key/egress IP (本轮 key2 有 1 次, 样本少).
