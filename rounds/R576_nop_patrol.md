# R576 — NOP 巡检轮 (2026-08-03 09:51 CST)

## 链路数据 (30min, 注入 + 交叉验证一致)
- cc2 (cc4101-primary): 0 req (session 间歇空闲, 无 cc2 评估样本)
- dsv4p_nv 30min: 9 req, 3×200 + 6×429 (SR=33.3%, 全 hermes caller)
- 唯一错误 `all_tiers_exhausted` × 6 (avg_dur=1993ms, NVCF 配额型, 非 nv_gw 故障)
- nv_tier_attempts 0 行 (实测复测) = KeyManager 全局冷却在 tier 层前拦截
- 429 全在空 key/空 IP = NVCF 侧拒绝 (配额波动区间)
- key2 = 3×200 (命中可用 key 时 100% 200, avg_dur=10963ms)
- 无 buffer/wait 日志 (30min 无 buffer 触发), 无 stream_total_deadline, 无 zombie
- finish_reason 全 tool_calls (3)
- 配置与 R472-R575 完全一致, 无漂移

## 交叉验证 (实测)
- `select status,count(*) ... 30min`: 429×6 + 200×3 ✓
- `caller='cc4101-primary'`: 0 rows ✓
- `error_type ... status!=200`: all_tiers_exhausted × 6 (唯一) ✓
- `nv_tier_attempts 30min`: 0 rows ✓
- /health: status=ok, nv_num_keys=5, nv_default_model=glm5_2_nv ✓
- docker ps: nv_gw Up 19h, cc4101 Up 9h, ms_gw/logs_db Up 4 days ✓

## KeyManager 日志行为 (30min, 正常)
- 429 → cooldown 180s (count=1-2), count=3 → 480s (k3 累积), count=4 → 180s (reset 后)
- count decayed (>300s since last 429) resetting 机制正常工作 (k1-k5 多次 decay reset)
- 09:51:00 [NV-GLOBAL-COOLDOWN] tier=dsv4p_nv all keys 429, Marking all cooling 180s
- 09:51:00 [NV-ALL-TIERS-FAIL] All 1 tiers failed, elapsed=1446ms, ABORT-NO-FALLBACK
  → dsv4p_nv 全挂时正确行为: NVU_PEER_FB_SKIP_MODELS 跳过 peer fb,
    NVU_MS_FALLBACK_MODELS=glm5_2_nv (不含 dsv4p_nv) → nv_gw 裸返, cc4101 层 ms_gw 兜底

## 本轮改动
- 无 (NOP). 铁律1 cc2 视角不满足 (0 流量) → 不动码.

## 依据
- cc2 0 流量 → 无评估样本, 铁律1 不满足
- dsv4p_nv 9 req: 3×200+6×429 = NVCF 配额波动区间 (命中 key2 100% 200, 全挂时空 key 429)
- KeyManager 行为完全正确: 429 cooldown/count decay/reset 机制按设计工作
- 全挂时 ABORT-NO-FALLBACK 是预期行为 (dsv4p_nv 跳 peer/ms fallback)
- 无新错误类型, 无参数漂移 → 无介入必要
- 本轮 SR=33.3% vs R575 SR=33.3% 完全一致, 与 R545-R574 同一 NVCF 配额波动模式

## 验证
- 0 restart → 无需 py_compile / curl 复测
- curl /health: status=ok, nv_num_keys=5, models=[kimi_nv,dsv4p_nv,glm5_2_nv]
- docker ps: nv_gw Up 19h, nv_gw_stable Up 32h, cc4101 Up 9h, ms_gw Up 4 days, logs_db Up 4 days

## 下一步
- 继续 NOP 巡检, 等 cc2 流量恢复后观察 dsv4p_nv buffer 路径行为
- 关注新错误类型或 key/IP 级故障再决定介入
- dsv4p_nv 小时级 SR <60% + cc2 流量恢复 → 评估 TIER_COOLDOWN_S 180s 是否过激
- all_tiers_exhausted 中段不恢复再评估 (当前 NVCF 配额型)
- 502 (peer-fb-skip) >=6/h + cc2 流量恢复 → 评估 dsv4p_nv fallback 策略
