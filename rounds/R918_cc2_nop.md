# R918 — cc2 NOP 巡检轮 (不改码)

日期: 2026-08-07 ~09:47 CST
容器: nv_gw Up 11h+, cc4101 Up 6h
live DB now()≈2026-08-07 09:47 CST

## 判定: NOP (cc2 主链路连续第 27 轮 100% 干净; bad 请求全属 hermes, caller 列 + request_id JOIN 双重铁证, 非 cc2 范围; fallback 0 次)

## cc2 主链 (cc4101-primary @ nv_gw:40006) 实拉数据

- 30min cc4101-primary = **119/119 = 100% SR, 0 bad** (实拉 caller 分组, `AND status!=200` → 0 条)。
  注入轮前数据 116/116 一致 (窗口时间略偏移)。

## 30min 所有 bad 归属

- hermes 线 502 ×4: `all_tiers_exhausted ×3` + `stream_absolute_cap ×1`。
- bad request_id 级 JOIN (nv_requests ⋈ nv_tier_attempts):
  - 056d2c5e (5 attempts), bfcd651d (5), 33516449 (4), 5d3afd42 (3)
  - 全部 caller=hermes 发起 (NVCFPexecRemoteDisconnected/Timeout/504 混合), cc2 主链 0 泄漏��

## 其他指标

- fallback: cc_requests 30min total=120, **fallback=0 次**。
- buffer 日志: 主链请求全部 attempt=1 success_tool_call (~2-12s), 无 kw 重试, 主链健康无全挂。
- per-key: pexec_success 主导, 瞬态 RemoteDisconnected/Timeout 分散 k0~k4, 被多 tier round-robin + func_health 吸收。
- 容器 health: 4101/40006/40066 全 ok (200), nv_gw 5 keys passthrough, dsv4p_nv40066 Up 2d。

## 结论

不改码。主链 SR 100% 无优化需求; 坏请求 100% 属 hermes 越 cc2 范围; 链路稳态已维持 27 轮。