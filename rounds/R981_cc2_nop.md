# R981 — cc2 NOP 巡检轮 (HM2 nv_gw 40006)

轮次: R981 | 类型: NOP (不改码) | 日期: 2026-08-07 13:50 CST
容器: nv_gw Up (10h), cc4101 Up (10h), nv_gw_stable Up (5d)

## 结论
cc2 主链路连续第 **89** 轮 (R893-R981) 100% 干净。**不改码。**

## 数据 (live 复核, 30min 窗口 ≈13:50 CST)

| 指标 | 值 | 状态 |
|---|---|---|
| 主 nv_gw(40006) cc4101-primary | **111/111 = 100% SR, 0 bad** | ✅ |
| cc4101-primary 专属错误 | **0 rows** | ✅ |
| 唯一 bad (非 200) | 502 all_tiers_exhausted ×2 (均 caller=hermes, fid 52e1ddb6) | ⚠️ 越界 |
| fallback (cc_requests) | 0 次 (1888 req, fallback_triggered=0) | ✅ |
| buffer 效果 | attempt=1 success, 5~10s flush, 无重试噪声 | ✅ |
| 容器 | nv_gw/cc4101/nv_gw_stable 皆 Up | ✅ |

## 依据
- cc4101-primary 30min = 111/111 全 200 (live re-pull)。
- 唯一 bad 2 条均 `caller=hermes` + 已知坏 fid 52e1ddb6 (502 all_tiers_exhausted ×2), 越界非 cc2 主链。
- cc_requests fallback_triggered = 0 (1888 req)。
- nv_tier_attempts: pexec_success 21~25 (k0-k4) + RemoteDisconnected 1~5/key + empty_200 1,
  全瞬态, 被多 key round-robin + func_health + buffer 吸收。
- buffer 日志: 全 success_tool_call (attempt=1, 5~10s flush), 无 retry/WAIT-/KEYMGR- 噪声。

## 不改码理由
1. 主链 SR 100% + 专属错误 0 行, 无优化需求;
2. 唯一 bad 全属 hermes (fid 52e1ddb6) 越 cc2 范围;
3. 多 key round-robin (dsv4f0731_nv 为首) + func_health + buffer 已达稳态, 瞬态错误全被吸收。

## 下一步
- 保持 NOP 观察; 继续监控 hermes bad (fid 52e1ddb6) 与主链容器隔离 (host 分离, R897 起保持)。