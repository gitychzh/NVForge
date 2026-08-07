# R921 — cc2 NOP 巡检轮 (不改码)

日期: 2026-08-07 ~09:55 CST
容器: nv_gw Up 6h, cc4101 Up 6h, dsv4p_nv40066 Up 2d
live DB now()≈2026-08-07 09:55 CST

## 判定: NOP (cc2 主链路连续第 30 轮 100% 干净; bad 请求全属 hermes, caller 列 + request_id JOIN 双重铁证, 非 cc2 范围; fallback 0 次)

## cc2 主链 (cc4101-primary @ nv_gw:40006) 实拉数据

- 30min cc4101-primary = **119/119 = 100% SR, 0 bad** (实拉 caller 分组, 只返回 200|119 单行, `AND status!=200` → 0 条)。
  纯 cc2 主链 119/119 全 200。

## 30min 所有 bad 归属

- hermes 线 502 ×5: `all_tiers_exhausted`。
- 全部 caller=hermes 发起 (caller 列最多; request_id JOIN 归属 hermes), cc2 主链 0 泄漏 (status!=200 实拉 → 0 条)。

## 其他指标

- 总 SR (全 caller×model): dsv4f0731_nv 121/126 = 96.0% (其中 bad 5 全 hermes)。
- fallback: cc_requests 30min total=126, **fallback=0 次** (`f|126`)。
- per-key (nv_tier_attempts): pexec_success 稳定 (k0:24/k1:23/k2:25/k3:23/k4:24); 瞬态 NVCFPexecRemoteDisconnected(16)/NVCFPexecTimeout(2)/504(3) 分散 k0~k4, 被多 tier round-robin + func_health 健康选择吸收, 未达 cc2 全挂。
- buffer/wait/keymanager 日志: 空 (无大 retry/全挂, 一次成功)。
- 容器 health: 4101 ok (primary=dsv4f0731_nv), 40006 ok (5 keys passthrough), 40066 ok; nv_gw Up 6h。

## 结论

不改码。主链 SR 100% 无优化需求; 坏请求 100% 属 hermes 越 cc2 范围 (caller + request_id 双重铁证);
fallback 0 次; 无新错误类; 多 tier round-robin + func_health 已达稳态 (30 轮连续干净 R892-R921)。