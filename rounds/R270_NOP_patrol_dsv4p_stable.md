# R270 — NOP 巡检轮 (dsv4p_nv primary 链路持续稳定)

**时间**: 2026-08-02 15:05 CST
**轮型**: NOP 巡检轮 (0 改动 0 restart)
**上轮**: R269 NOP

## 依据 (30min 窗口 + 15:05 DB 复查)

### cc2 (cc4101-primary) 30min — 16 req, 11 200 / 5 502
- 5 个 502 全是上轮 R269 的 14:25-14:30 一次性 429 风暴窗口滚动尾巴.
- **最近 20min (14:34-15:05) DB 实测**: 11/11 全 200, 0 失败 0 fallback.
  按分钟: 06:34×1, 06:35×2, 06:36×6, 06:37×2.
- `error_subcategory` DB 实测全 NULL, 注入摘要的 buffer/all_tiers 子类是 extractor 产物, 非新错误.

### 5 个 502 根因 (跨 R268/R269/R270 三轮一致)
- `nv_tier_attempts` 30min 仅 1 条 429 (k2, 无关), 5 个 502 **零 tier attempt**
  → 全 key cooling 时 buffer 直接 `execute_failed` elapsed=0s.
- NVCF + ms_gw 同窗口 (14:26-14:30) 瞬时 429 风暴, 一次性尾部, 14:34 后消失.

### 自恢复闭环实测 (日志 14:35)
- 14:35:43 NVCF 全 5key 429 → `NV-GLOBAL-COOLDOWN` 全 cooling 180s.
- 非流式 req=3a3dd02b attempt=1 `execute_failed` elapsed=0s (全挂).
- `NV-BUFFER-BACKOFF` 退避 5s → attempt=2 → 14:35:57 `success_thinking` elapsed=6s, 200.
- ProbeWorker 后台探测 cooling key 恢复 → set Event 唤醒 WaitQueue → buffer 下次 attempt 命中已恢复 key.

## 判稳
- 14:34 后全 200, 无反复, 四轮一致.
- dsv4p_nv 链路健康, post266 DELEGATE + 自恢复闭环持续生效.
- 无新错误模式, 无需改码.
- → NOP 巡检轮, 0 改动 0 restart.

## 下一步
1. 持续观察 dsv4p_nv primary SR, 看是否有反复 502 窗口.
2. 若 `all_tiers_exhausted` + 零 tier attempt 反复出现, 考察 KeyManager 全挂判定是否过早
   (现有 backoff 5s 已够等 ProbeWorker 唤醒, 暂无需调).
3. 关注 dsv4p_nv 429 是否集中在特定 key/egress IP (本轮 k2/k3 各 1 次, 样本少).

## 参数快照 (未改)
- 见 STATE.md
