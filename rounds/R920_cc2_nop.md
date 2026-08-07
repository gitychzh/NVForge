# R920 — cc2 NOP 巡检轮 (不改码)

日期: 2026-08-07 ~09:53 CST
容器: nv_gw Up 6h, cc4101 Up 6h, dsv4p_nv40066 Up 2d
live DB now()≈2026-08-07 09:53 CST

## 判定: NOP (cc2 主链路连续第 29 轮 100% 干净; bad 请求全属 hermes, caller 列 + request_id JOIN 双重铁证, 非 cc2 范围; fallback 0 次)

## cc2 主链 (cc4101-primary @ nv_gw:40006) 实拉数据

- 30min cc4101-primary = **116/116 = 100% SR, 0 bad** (实拉 caller 分组, 只返回 200|116 单行, `AND status!=200` → 0 条)。
  纯 cc2 主链 116/116 全 200。

## 30min 所有 bad 归属

- hermes 线 502 ×5: `all_tiers_exhausted`。
- 全部 caller=hermes 发起 (caller 列 + request_id 级 JOIN 铁证), cc2 主链 0 泄漏 (status!=200 实拉 → 0 条)。

## 其他指标

- fallback: cc_requests 30min total=1587, **fallback=0 次**。
- buffer 日志: cc2 主链请求全部 attempt=1 success_tool_call (~8-10s, 一次成功), 无大 retry/全挂。
- per-key: pexec_success 稳定 (k0:23/k1:22/k2:24/k3:24/k4:23); 瞬态 NVCFPexecRemoteDisconnected(14)/Timeout(4)/504(3) 分散 k0~k4, 被多 tier round-robin + func_health 健康选择吸收, 未达 cc2 全挂。
- 容器 health: 4101 ok (primary=dsv4f0731_nv), 40006 ok (5 keys passthrough), 40066 ok; nv_gw Up 6h。

## 结论

不改码。主链 SR 100% 无优化需求; 坏请求 100% 属 hermes 越 cc2 范围 (caller + request_id 双重铁证);
fallback 0 次; 无新错误类; 多 tier round-robin + func_health 已达稳态 (29 轮连续干净)。