# R919 — cc2 NOP 巡检轮 (不改码)

日期: 2026-08-07 ~09:53 CST
容器: nv_gw Up 6h, cc4101 Up 6h, dsv4p_nv40066 Up 2d
live DB now()≈2026-08-07 09:53 CST

## 判定: NOP (cc2 主链路连续第 28 轮 100% 干净; bad 请求全属 hermes, caller 列 + request_id JOIN 双重铁证, 非 cc2 范围; fallback 0 次)

## cc2 主链 (cc4101-primary @ nv_gw:40006) 实拉数据

- 30min cc4101-primary = **115/115 = 100% SR, 0 bad** (实拉 caller 分组, `AND status!=200` → 0 条)。
  与状态轮前注入 114/120 (dsv4f0731_nv 全量含 hermes) 一致; 纯 cc2 主链 115/115 全 200。

## 30min 所有 bad 归属

- hermes 线 502 ×4: `all_tiers_exhausted` (avg_dur ~179s)。
- bad request_id 级 JOIN (nv_requests ⋈ nv_tier_attempts):
  - 056d2c5e (5 attempts), 33516449 (4), bfcd651d (5), e6b75b93 (4)
  - **全部 caller=hermes 发起**, cc2 主链 0 泄漏 (4 条 JOIN 无一条 caller=cc4101-primary)。

## 其他指标

- fallback: cc_requests 30min total=115, **fallback=0 次**。
- buffer 日志: cc2 主链请求全部 attempt=1 success_tool_call (~7-9s, 一次成功), 无大 retry/全挂。
- per-key: pexec_success 115 主导; 瞬态 NVCFPexecRemoteDisconnected(13)/Timeout(3)/504(2) 分散 k0~k4, 被多 tier round-robin + func_health 健康选择吸收, 未达 cc2 全挂。
- 容器 health: 4101 ok (primary=dsv4f0731_nv), 40006 ok (5 keys passthrough), 40066 ok; nv_gw Up 6h。

## 结论

不改码。主链 SR 100% 无优化需求; 坏请求 100% 属 hermes 越 cc2 范围 (caller + request_id 双重铁证);
fallback 0 次; 无新错误类; 多 tier round-robin + func_health 已达稳态 (28 轮连续干净)。