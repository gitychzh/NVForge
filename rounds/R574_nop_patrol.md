# R574 — NOP 巡检轮 (2026-08-03 09:39 CST)

## 链路数据 (30min, 注入)
- cc2 (cc4101-primary): 0 req (session 间歇空闲, 无 cc2 评估样本)
- dsv4p_nv 30min: 6 req, 0×200 + 6×429 (SR=0.0%, 全 hermes caller)
- 唯一错误 `all_tiers_exhausted` × 6 (avg_dur=1405ms, NVCF 配额型, 非 nv_gw 故障)
- nv_tier_attempts 0 行 (实测复测) = KeyManager 全局冷却在 tier 层前拦截
- 429 全在空 key/空 IP = NVCF 侧拒绝 (配额波动区间)
- 无 buffer/wait 日志 (30min 无 buffer 触发)
- 无 stream_total_deadline, 无 zombie
- 配置与 R573 完全一致, 无漂移

## 6h SR 趋势 (dsv4p_nv, 按小时)
| 时段 (UTC) | 200 | 429 | 502 | 备注 |
|---|---|---|---|---|
| 08-02 19:00 | 0 | 3 | 0 | 全挂 |
| 08-02 20:00 | 4 | 12 | 0 | 部分恢复 |
| 08-02 21:00 | 12 | 10 | 1 | 波动 |
| 08-02 22:00 | 3 | 11 | 0 | 波动 |
| 08-02 23:00 | 13 | 9 | 2 | 波动 |
| 08-03 00:00 | 8 | 11 | 0 | 波动 |
| 08-03 01:00 | 5 | 8 | 0 | 波动 |

## 6h per-key × status (dsv4p_nv)
- key2: 41×200 (主力可用 key)
- key3: 4×200 + 1×502
- 空 key (全挂时): 64×429 + 2×502

→ 命中可用 key (key2/key3) 时 100% 200, 全挂时空 key 429 = NVCF 配额型, 非 nv_gw tier 故障

## 本轮改动
- 无 (NOP). 铁律1 cc2 视角不满足 (0 流量) → 不动码.

## 依据
- cc2 0 流量 → 无评估样本, 铁律1 不满足
- dsv4p_nv 6 req 全 429 = NVCF 配额波动区间 (全空 key = NVCF 侧拒绝)
- 6h 趋势: SR 在 20%-55% 波动, 命中可用 key 时 100% 200 → 非 nv_gw tier 故障
- 无新错误类型, 无参数漂移 → 无介入必要
- 本轮 SR=0% vs R573 SR=14.3% 属同一 NVCF 配额波动区间, 非趋势性恶化

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
