# R573 — NOP 巡检轮 (2026-08-03 09:35 CST)

## 链路数据 (30min, 注入)
- cc2 (cc4101-primary): 0 req (session 间歇空闲, 无 cc2 评估样本)
- dsv4p_nv 30min: 7 req, 1×200 + 6×429 (SR=14.3%, 全 hermes caller)
- 唯一错误 `all_tiers_exhausted` × 6 (avg_dur=2199ms, NVCF 配额型, 非 nv_gw 故障)
- nv_tier_attempts 0 行 = KeyManager 全局冷却在 tier 层前拦截
- 命中 key2 + 命中 203.10.96.139 IP 的请求 100% 200 → 非 nv_gw tier 故障
- 429 全在空 key/空 IP = NVCF 侧拒绝 (配额波动区间)
- 无 stream_total_deadline, 无 zombie, 无 buffer/wait 日志
- 200 延迟 avg 4094ms (在 90s budget 内, 健康), finish_reason=tool_calls
- fallback 0/7 (dsv4p_nv 跳过 peer fallback, 裸返 429/502)
- 配置与 R572 完全一致, 无漂移

## 本轮改动
- 无 (NOP). 铁律1 cc2 视角不满足 (0 流量) → 不动码.

## 依据
- cc2 0 流量 → 无评估样本, 铁律1 不满足
- dsv4p_nv 7 req 1×200+6×429 = NVCF 配额波动区间 (6×429 全在空 key/空 IP = NVCF 侧拒绝)
- 命中 key2 + 命中 203.10.96.139 IP 的请求 100% 200 → 非 nv_gw tier 故障
- 无新错误类型, 无参数漂移 → 无介入必要

## 验证
- 0 restart → 无需 py_compile / curl 复测
- curl /health: status=ok, nv_num_keys=5, nv_default_model=glm5_2_nv, models=[kimi_nv,dsv4p_nv,glm5_2_nv]
- docker ps: nv_gw Up 19h, nv_gw_stable Up 32h, cc4101 Up 9h, ms_gw Up 4 days, logs_db Up 4 days

## 下一步
- 继续 NOP 巡检, 等 cc2 流量恢复后观察 dsv4p_nv buffer 路径行为
- 关注新错误类型或 key/IP 级故障再决定介入
- dsv4p_nv 小时级 SR <60% + cc2 流量恢复 → 评估 TIER_COOLDOWN_S 180s 是否过激
- all_tiers_exhausted 中段不恢复再评估 (当前 ~12/h 全 NVCF 配额型)
- 502 (peer-fb-skip) >=6/h + cc2 流量恢复 → 评估 dsv4p_nv fallback 策略
