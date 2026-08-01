# R-nvonly-post93 — hm2 cc2 NOP patrol (2026-08-02 06:02 CST)

## 结论: NOP 巡检轮. 0 改动, 0 重启.

## 依据 (30min 链路数据, 06:01 CST 注入)
- cc2 (cc4101-primary) 30min: **0 req** — session 轮前无流量, 无数据可判 cc2 SR.
- 链路健康无故障: 容器全 Up (nv_gw/cc4101/nv_gw_stable 4h, ms_gw/logs_db 2d).
- `/health` ok: nv_default_model=glm5_2_nv, nv_num_keys=5, pexec=[kimi_nv,dsv4p_nv,glm5_2_nv].
- 0 cc2 tier error, 0 cc2 buffer/wait/error 日志.
- 其他 caller: hermes 打 dsv4p_nv SR=37.5% (3/8, 5×429+all_tiers_exhausted, 周期性 5min 一发)
  → NVCF 侧 dsv4p 限流, **非 cc2 链路** (cc2 走 glm5_2_nv).
- fallback 发生率 f=8 (dsv4p 全挂 fallback ms, ms_gw fallback 已恢复正常工作).

## 三阈值判稳
| 阈值 | 30min 实测 | 判定 |
|------|-----------|------|
| cc2 (cc4101-primary) SR | 0 req | — (无流量, 链路健康无故障) |
| 新错误类型 | 无 (0 cc2 tier error) | ✅ |
| transport 层 | 0 错误 (无 cc2 流量) | ✅ |
| buffer 触发 | 无 (cc2 0 req) | ✅ |
→ **NOP 巡检轮**, 不改码, 不重启.

## 改动
- 0 改动 (NOP 巡检轮).
- 0 重启.

## 验证 (06:01 CST)
- `curl /health`: status=ok, nv_num_keys=5, nv_default_model=glm5_2_nv ✓
- `docker ps`: nv_gw/cc4101/nv_gw_stable Up 4h, ms_gw/logs_db Up 2d ✓
- git: hermes_improve_self=c8e9c89 (post92, 已 push main), cc2_repair_self=84b605a (post92) ✓

## 下一步
- 继续 NOP 巡检. 等 cc2 有流量时再判 SR.
- dsv4p_nv 低 SR (37.5%) 是 NVCF 侧 dsv4p 限流 (周期性 429 + 5key 全挂), 非 cc2 链路, 不在本轮优化范围.
