# R988 cc2 NOP 巡检轮 (不改码) — 主链连续第 96 轮 100% 干净

- 轮号: R988 | 时间: 2026-08-07 14:30 CST
- 容器: nv_gw 40006 Up, cc4101 4101 Up | health 全 200
- 类型: NOP 巡检轮 — 只记数据不改码

## 数据 (注入轮前链路分析 + live 复核)

### 30min cc4101-primary (cc2 主请求, 主 nv_gw:40006)
- **126/126 = 100% SR, 0 bad** (live re-pull; 注入 122, live 增至 126 全 200)
- 专属错误 (caller=cc4101-primary, status!=200): **0 rows**

### 30min 全 nv_requests bad (非 200)
- all_tiers_exhausted ×4 + zombie_empty_completion ×1 = **5 条, 全 caller=hermes 线**
  (已知坏 fid 52e1ddb6 越界容器; cc2 primary 0 bad)

### fallback (cc_requests)
- total 1904, fb = **0 次** — 主链稳态, 无 fallback 触发

### nv_tier_attempts per-key 错误 (dsv4f0731_nv, 注入)
- 瞬态: RemoteDisconnected / Timeout / empty_200 散落各 key, pexec_success 主导 (23-26/key)
- **全被 5key round-robin + func_health + buffer 吸收**, 无泄漏为 200 以外 response

### buffer 日志 (nv_gw live)
- 绝大多数请求 attempt=1 一次成功 (elapsed 3-19s, success_tool_call/success_text)
- 1 例 `req=394a6694` attempt=1 key=k5 all_keys_exhausted → NV-BUFFER-BACKOFF 5s → attempt=2 重试
  → **缓冲吸收, 无 502 泄漏给 CC**。这正对应注入 all_tiers_exhausted 诊断, 且 cc2 侧被 buffer 吸收。

## 判断 / 依据
- 主链 dsv4f0731_nv (cc4101-primary) 30min **100% SR (126/126), 专属错误 0 rows**。
- 唯一 5 条 bad 100% 属 hermes 线 (caller=hermes + 已知坏 fid 52e1ddb6 越界容器,
  all_tiers×4 + zombie×1), fallback 0 次。
- cc2 侧的一次 all_keys_exhausted (attempt=1) 被 buffer 5s backoff + attempt=2 全部吸收,
  未泄漏为对 CC 的 502 → 设计稳态如预期。
- **不改码**: ①主链 SR 100% + 专属错误 0 行; ②唯一 bad 全属 hermes 越 cc2 范围;
  ③多 key round-robin + func_health + buffer 已达稳态, 瞬态错误全被吸收, 无参数可调。

## 下一步
- 持续 NOP 观察; 主链 dsv4f0731_nv 为首代健康模型, 无需参数改动。
- 继续监控 hermes bad (fid 52e1ddb6) 是否与主链容器 host 隔离 (R897 起持续隔离保持)。

## 参数/容器快照 (unchanged)
- nv_gw: NVU_DISABLE_MS_FALLBACK=0, NVU_BUFFER_CALLERS=cc4101-primary,openclaw2,
  NVU_BUFFER_MAX_RETRIES=5 (90s×5=450s), nv_default_model=glm5_2_nv
- cc4101: PRIMARY_UPSTREAM_MODEL=dsv4f0731_nv, PRIMARY_UPSTREAM_URL=http://nv_gw:40006,
  FALLBACK_UPSTREAM_URL=http://ms_gw:40007 (保留不禁用), STREAM_TOTAL_DEADLINE_S=470,
  PRIMARY_HEADER_TIMEOUT=400
- 容器 nv_gw/cc4101 皆 Up, health 40006/4101 全 200