# R1990 (HM2 cc2): NOP 巡检 R99 — 30min SR95.97% / 6h SR95.89% 0 真中断, 连续冻结第 36 轮

## 数据 (本 session 拉取, nv_gw StartedAt 13:33:43Z 维 R1933, 0 restart)

### 30min 窗口
- status: 200×119 / 502×5  → **SR = 119/124 = 95.97%** (小样本偏稳)
- error_type (502=5): zombie_empty_completion×3 + all_tiers_exhausted×1 + stream_first_byte_timeout×1 (全已知类)
- v.s R1989 30min (zombie×4+fbt×1): zombie 持平-1 / +1 ATE 单条微调, 0 新类

### 6h 窗口
- status: 200×818 / 502×35 → **SR = 818/853 = 95.89%** (大样本稳态)
- v.s R1989 6h 95.95% → **-0.06pp 0 漂移**
- error_type (502=35): zombie×25 + all_tiers_exhausted×5 + stream_first_byte_timeout×5
- v.s R1989 6h (zombie×25+ATE×4+fbt×5): zombie×25 持平 / ATE +1 / fbt 持平, 全已知类无新可配置类

### abs_cap
- 30min=0 / 6h=0 (DB `error_type like '%abs%'` 0 rows 双重确认; R1918 方案0 持续归零连续多轮)

### 持久化层 / fallback / breaker
- fallback **3** FALLBACK-OK / 30min, 全 75s `PRIMARY-FAIL-SKIP-CIRCUIT` (< chain budget 120s, cc4101 bug3 preempt 层, NOT counted toward circuit)
  - req=247120a7 ms 救回 3205ms / req=838bd9e0 3456ms / req=9daf7e05 15515ms → 0 条 fallback 失败
- `grep -cE "both failed|UPSTREAM-ERROR-SEEN"` = 0 → **0 真中断**
- breaker cc4101 PRIMARY-BREAKER-OPEN 30min = **0**
- nv_gw NV-ANTH-BREAKER-FAIL 30min = **2** 但 state 全 CLOSED: ('CLOSED',2,0)+('CLOSED',3,0) (只记 failure 未达 5/300s 阈值, 不 OPEN) — 已知抖动类
- 120s 跑满类本轮 0 (持续趋稳归零); 注日志 "saves ~120s" 是 BUG-A 修复 SKIP-PEXEC2 路径省时间非 120s 跑满类
- **BUG-A 修复 (R1913) 真实生效**: 30min `NV-GLM52-CHAIN-SKIP-PEXEC2` 触发 **2 次**

## 改动
- **0 改动 0 restart** (NOP 巡检 R99)

## 介入四条判断 (全不满足 → NOP)
1. 6h SR95.89% 大样本稳态 (与 R1989 -0.06pp 0 漂移), 30min 95.97% 小样本非"连续 3+ 轮跌破 80%"介入线
2. 502 全 zombie+ATE+fbt 已知类 (与 R1989 微调无新类), 非新可配置类, abs_cap 30min=0/6h=0 (DB 双重确认)
3. breaker OPEN 30min=0 连续多轮, nv_gw BREAKER-FAIL 2 条但 state=CLOSED 不 OPEN
4. fallback 3/30min 全 FALLBACK-OK 被 ms 兜住 0 真中断, 远低于 15/30min 介入线, 无新监督者激活指令 (R1928 冻结理由仍成立)

## 验证
- env 无漂移 (与 R1989 完全一致; NVU_GLM52_EXP_BACKOFF 不在容器 env 中确认半成品从未激活)
- /health ok (nv_num_keys=5, nvcf_pexec_models=kimi_nv/dsv4p_nv/glm5_2_nv, nv_default_model=dsv4p_nv, proxy_role=passthrough)
- docker ps 全 Up (nv_gw Up 9h, cc4101 Up 10h, ms_gw Up 2d, logs_db Up 3d)
- nv_gw StartedAt 2026-07-19T13:33:43Z (0 restart 维 R1933); cc4101 StartedAt 2026-07-19T12:10:22Z (0 restart 维 R1926)

## 冻结决定
连续第 36 轮冻结指数退避 (R1928 冻结 → R1929/R1930/R1931/R1933-1967/R1970-1989/R1990 NOP)。
R1928 冻结理由 (半成品未 in-vivo 验证 + 激活需同步 chain_budget 120→420 + cc4101 header 60→450 + post-200 软挂换 key 未实现 + 24h 观测) 仍成立。
当前链路稳态 (6h SR95.89% 0 真中断, abs_cap 连续多轮归零, BUG-A 修复真实生效 2 次/30min, 120s 跑满类持续趋零) + 本轮无新监督者激活指令 → 继续冻结。
等监督者再授权激活或数据恶化 (SR 连续 3+ 轮跌破 80%) 再动。
