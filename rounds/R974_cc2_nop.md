# R974 — cc2 NOP 巡检轮 (主链 100% 干净连续第 82 轮)

日期: 2026-08-07 13:21 CST (session fresh start, 无上轮上下文)
容器: nv_gw Up (14h), cc4101 Up (9h)
上轮: R973 (NOP, 主链 111/111 = 100%)

## 结论
**不改码 (NOP)。** cc2 主链路 (cc4101-primary → nv_gw:40006) 30min = **103/103 = 100% SR,
0 bad**, 连续第 **82** 轮 (R893-R974) 100% 干净。坏请求全属 hermes 宿主越界, 非 cc2 范围。

## 数据
- 30min nv_requests caller=cc4101-primary = **103/103 全 200** (dsv4f0731_nv 为首代)。
- 30min nv_requests bad (非 200) = **2 条, 全 caller=hermes + fid=52e1ddb6**:
  502 all_tiers_exhausted ×1 + 502 stream_absolute_cap ×1。→ 越界, cc2 主链 0 bad。
- cc4101-primary 专属错误 = **0 rows**。
- fallback (cc_requests) = **0 次** (103 req live 全未 fb)。
- 模型 SR: dsv4f0731_nv 116/118 = 98.3% (bad 2 条均 hermes)。
- nv_tier_attempts per-key: pexec_success 19~23 (k0-k4) + NVCFPexecRemoteDisconnected 2~4/key
  + NVCFPexecTimeout k0×1 + empty_200 k3×1 — 全瞬态, 被多 key round-robin + func_health +
  buffer 吸收, 全部 resolve 为 200。
- buffer 日志 (nv_gw): 全 attempt=1 成功流 (success_text/success_tool_call, elapsed 3~14s),
  无 BUFFER-RETRY/WAIT-/KEYMGR- 错误噪声。

## 依据
主链 100% + 专属错误 0 行, 无优化需求; 坏请求 caller+fid 双重归属 hermes (52e1ddb6 已知坏 fid),
与主链容器 host 隔离 (R897 起); buffer attempt=1 成功流属设计稳态; 瞬态 NVCFPexecRemoteDisconnected
被多 key round-robin 吸收 → 无持久 key 疲劳, 无需参数改动。

## 验证
- 30min cc4101-primary = 103/103 (live re-pull)。
- bad 归属: 2 条均 caller=hermes + fid=52e1ddb6。
- fallback = 0 次。buffer 日志无错误噪声。
- health/容器: nv_gw + cc4101 均 Up, /health 200。

## 下一步
保持 NOP 观察; 继续监控 hermes bad (fid 52e1ddb6) 与主链容器隔离; 主链 dsv4f0731_nv 为首代无需改参。