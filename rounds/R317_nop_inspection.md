# R317 — NOP 巡检轮 (cc2 self-opt, HM2)

- 时间: 2026-08-02 18:03 CST
- 链路: cc4101(dsv4p_nv) → nv_gw(40006) → NVCF
- 改动: 0  restart: 0  fallback: 0

## 30min 实时数据 (注入分析 + DB 校验一致)

### 1. cc2 (cc4101-primary) 30min 0 req
- session 间歇空闲, 链路空闲健康. 0 fallback 0 deadline.
- buffer/wait 日志空 (无 buffer 流量).

### 2. dsv4p_nv 30min 全 caller SR=85.0% (17/20)
| caller | model | status | count |
|---|---|---|---|
| hermes | dsv4p_nv | 200 | 17 |
| hermes | dsv4p_nv | 429 | 3 |

- per-key (dsv4p): key2 → 17×200 (avg_dur 10910), 空 key → 3×429 (1922).
- per-egress: 203.10.96.139 → 17×100, 空 IP → 3×0 (429).
- finish_reason: tool_calls×14, stop×3 (无 zombie).
- 分钟趋势: 09:35/09:45/09:50 三波 429, 09:40-09:41 恢复 8×200 + 09:55-10:01 恢复 9×200 (配额周期自恢复).
- 延迟 (200): avg_dur 10910, max 32671, min 4669, avg_ttfb 10390.
- fallback 0/20.

### 3. 错误分类
- 3 错误: 全 all_tiers_exhausted (avg_dur 1922, sub=all_tiers_failed_in_mapped_tier).
- 09:35+09:45+09:50 三波 429 → 5key 同 function 同时挂 → all_tiers_exhausted.
- 与 R268-R316 错误类型集合一致 (all_tiers_exhausted 历史仍存在).
- tier_attempts 30min 0 行 (429 在 NVCF 侧, 未进入 nv_gw tier 重试).

### 4. 健康
- /health 200, nv_num_keys=5, default glm5_2_nv, pexec=[kimi_nv,dsv4p_nv,glm5_2_nv].
- 容器 nv_gw/cc4101/ms_gw/logs_db 全 Up.

## 根因 (沿用 R278-R316, 无变化)
- dsv4p_nv 5key 全绑同一 NVCF function, function 级 429 配额耗尽时 5key 同时挂.
- buffer 5key 轮转对 key/IP 级 429 有效, 对 function 级 429 是已知设计盲区 (非代码缺陷).
- 本轮三波 429 证明是 NVCF function 配额周期自恢复.
- KEYMGR 指数退避 + ProbeWorker 探测唤醒 正常工作.

## 判稳
- **NOP 巡检轮**. cc2 primary 0 req, 链路空闲健康.
- dsv4p_nv SR=85.0% (17/20) (窗口命中三波 429, NVCF function 配额周期; 总 req 20 少).
- 错误类型无新增 (全 all_tiers_exhausted), 与 R268-R316 一致.
- 五十轮一致 R268-R317.

## 下一步
- 继续 NOP 巡检, 等 cc2 流量恢复后观察 dsv4p_nv SR.
- 关注是否出现新错误类型 (非 all_tiers_exhausted) 或 key/IP 级故障, 再决定是否介入.
