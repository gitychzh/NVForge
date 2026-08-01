# R-nvonly-post108 — hm2_cc2 NOP 巡检轮

**时间**: 2026-08-02 06:50 CST
**上轮**: R-nvonly-post107 (git HEAD 7895ecb 已 push)
**本轮**: NOP 巡检轮, 0 改动, 0 重启

## 1. 判稳依据

本轮 30min 窗口 (06:45 CST 注入数据) 与 post107 同窗口:
- **cc2 (cc4101-primary) 30min**: 0 req (session 轮前无流量产生, 无数据可判 SR).
- 链路健康无故障: 容器全 Up, env 配置正确, 0 cc2 tier error, 0 buffer/wait 日志.
- dsv4p_nv SR=37.5% (3/8) 仍是 hermes 链路周期性 429 (NVCF 侧 dsv4p 限流), **非 cc2 链路** (cc2 走 glm5_2_nv).
- 30min fallback 发生率: f=8 (dsv4p 全挂 fallback ms, ms_gw fallback 正常工作).
- glm5_2_nv 连续 post100-post108 (9 轮) 无 dsv4p 故障扩散.

判稳: SR 无数据 (0 req), 无新错误, 链路健康 → NOP 巡检轮, 不改码.

## 2. 健康验证 (06:50 CST)

| 验证项 | 结果 |
|--------|------|
| nv_gw /health | ok, passthrough, 5 keys, default glm5_2_nv ✓ |
| nv_gw env | NVU_DISABLE_MS_FALLBACK=0, BUFFER_MAX_RETRIES=5, TOTAL_DEADLINE=450s, UPSTREAM_TIMEOUT=90s ✓ |
| cc4101 env | STREAM_TOTAL_DEADLINE=470, PRIMARY_HEADER_TIMEOUT=400, FALLBACK=ms_gw:40007 ✓ |
| docker ps | nv_gw/cc4101/nv_gw_stable Up 5h, ms_gw/logs_db Up 2d ✓ |
| cc2 (cc4101-primary) 30min SR | 0 rows (无流量, 链路健康无故障) ✓ |
| 30min 错误分类 | all_tiers_exhausted × 5 (全 hermes+dsv4p, 非 cc2) ✓ |
| buffer/wait 日志 | 无 (cc2 0 req) ✓ |

## 3. 本轮改动

无. 0 改动, 0 重启.

## 4. 下一步

- 继续观察 cc2 (cc4101-primary) 流量产生后的 glm5_2_nv SR.
- 若 cc2 有流量且 SR<99%, 拉错误分类找根因.
- dsv4p_nv 周期性 429 是 NVCF 侧限流, 非 cc2 范围, 不处理.

## 5. 参数快照 (2026-08-02 06:50 CST)

- nv_gw: NVU_DISABLE_MS_FALLBACK=0, BUFFER_MAX_RETRIES=5, BUFFER_TIMEOUT_STAIRS=90×5, BUFFER_TOTAL_DEADLINE=450s, TIER_TIMEOUT_BUDGET=180s, UPSTREAM_TIMEOUT=90s
- cc4101: CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400, FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/chat/completions
- 链路: cc2→cc4101(4101)→nv_gw(40006, glm5_2_nv)→NVCF, fallback ms_gw(40007) 已恢复
- 铁律: 只改 HM2 nv_gw, 不碰 HM1, 不碰 ms_gw 源码, 改前有数据改后必验证
