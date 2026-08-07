# R975 — cc2 NOP 巡检轮 (主链 100% 干净连续第 83 轮)

日期: 2026-08-07 13:23 CST (session fresh start, 无上轮上下文)
容器: nv_gw Up (10h), cc4101 Up (9h)
上轮: R974 (NOP, 主链 103/103 = 100%)

## 结论
**不改码 (NOP)。** cc2 主链路 (cc4101-primary → nv_gw:40006) 30min = **106/106 = 100% SR,
0 bad**, 连续第 **83** 轮 (R893-R975) 100% 干净。坏请求全属 hermes 宿主越界, 非 cc2 范围。

## 数据
- 30min nv_requests caller=cc4101-primary = **106/106 全 200** (dsv4f0731_nv 为首代)。
- 30min nv_requests bad (非 200) = **3 条, 全 caller=hermes + fid=52e1ddb6**:
  502 stream_absolute_cap ×2 + 502 all_tiers_exhausted ×1。→ 越界, cc2 主链 0 bad。
- cc4101-primary 专属错误 = **0 rows** (106 request 全 200)。
- fallback (cc_requests) = **0 次** (107 req live 全未 fb)。
- 模型 SR: dsv4f0731_nv 114/117 = 97.4% (bad 3 条均 hermes + 已知坏 fid)。
- nv_tier_attempts per-key: pexec_success 18~24 (k0-k4) + NVCFPexecRemoteDisconnected 散落
  k0-k4 (~13) + NVCFPexecTimeout k0×1 + empty_200 k3×1 — 全瞬态, 被多 key round-robin +
  func_health + buffer 吸收, 全部 resolve 为 200。
- buffer 日志 (nv_gw): 全 attempt=1 成功流 (success_text/success_tool_call, elapsed 6~25s),
  无 BUFFER-RETRY/WAIT-/KEYMGR- 错误噪声。

## 依据
主链 100% + 专属错误 0 行, 无优化需求; 坏请求 caller+fid 双重归属 hermes (52e1ddb6 已知坏 fid),
与主链容器 host 隔离 (R897 起); buffer attempt=1 成功流属设计稳态; 瞬态 NVCFPexecRemoteDisconnected
被多 key round-robin 吸收 → 无持久 key 疲劳, 无需参数改动。

## 验证
- 30min cc4101-primary = 106/106 (live re-pull)。
- bad 归属: 3 条均 caller=hermes + fid=52e1ddb6。
- fallback = 0 次。buffer 日志无错误噪声。
- health/容器: nv_gw + cc4101 均 Up, /health 40006 + 4101 全 200。

## 下一步
保持 NOP 观察; 继续监控 hermes bad (fid 52e1ddb6) 与主链容器隔离; 主链 dsv4f0731_nv 为首代无需改参。