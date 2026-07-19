# R1979 (HM2 cc2): NOP 巡检 R94 — 30min SR93.88%/6h SR95.09% 0 真中断, 与 R1978 6h +0.28pp 0 漂移, 连续冻结第 31 轮延续

**日期**: 2026-07-20
**模式**: nv 直连 (cc4101→nv_gw), 指数退避半成品冻结 (env NVU_GLM52_EXP_BACKOFF 不在 env 中=关, 从未 in-vivo 激活)
**轮号**: R1979 (cc2 第 31 轮 NOP, 巡检 R94)
**改动**: 0 改动 0 restart (NOP 巡检)
**冻结计数**: 连续第 31 轮 (R1928 冻结 → R1929/R1930/R1931/R1933-1967/R1970/R1971/R1972/R1973/R1976/R1977/R1978/R1979 NOP)

## 数据 (本 session 拉取, nv_gw StartedAt 13:33:43Z 维 R1933)

### nv_gw 30min 窗口
- SR = 92/98 = **93.88%** (200:92 / 502:6), 样本 98 小偏稳
- vs R1978 30min 93.51% (72/77) = **+0.37pp**, 几乎一致 0 漂移
- 502=6 全已知类: zombie_empty_completion×5 + stream_first_byte_timeout×1
  - vs R1978 30min 502=5 (zombie×5): 本轮 zombie×5 一致 + 多 1 个 fbt, 同已知类非新类

### nv_gw 6h 窗口
- SR = 717/754 = **95.09%** (200:717 / 502:37), 大样本稳态区间
- vs R1978 6h 94.81% (713/752) = **+0.28pp**, 0 漂移非退化 (R1960-1979 94.0-95.1% 区间内)
- 6h 502=37 全已知类: zombie×24 (R1978 26, -2 区间内波动) + all_tiers_exhausted×7 (R1978 8, -1) + first_byte_timeout×6 (R1978 5, +1)
  - 与 R1978 **几乎 0 漂移 (zombie-2, ATE-1, fbt+1)**

### abs_cap (DB 双重确认)
- 30min = **0** / 6h = **0** (DB `error_type like '%abs%'` 0 rows)
- R1918 方案0 cap_origin 重置持续归零, 连续多轮 (R1931→...→R1978→R1979)

### 持久化层 (30min tier_attempts)
- pexec_success×57 / pexec_429×1 (nv_gw 转发层稳)

### fallback (cc4101 30min)
- FALLBACK-OK = **5**, 0 真中断, 0 fallback 失败
- 全 5 条 75s `PRIMARY-FAIL-SKIP-CIRCUIT` (< chain budget 120s, cc4101 pre-empted nv_gw retry, NOT counted toward circuit — R1947 已知类 cc4101 bug3 preempt 层)
- ms 救回时长: 1832 / 2668 / 3490 / 2370 / 5123ms → 全部 FALLBACK-OK
- vs R1978 fallback 6×75s SKIP, 本轮 5 (-1 区间内波动无恶化)
- **120s 跑满类本轮 0** (R1951 4→R1953 2→R1954 0→...→R1978 0→R1979 0 持续趋稳归零)
- 注: 日志 "saves ~120s" (NV-GLM52-CHAIN-SKIP-PEXEC2) 是 BUG-A 修复路径省时间, 非 120s 跑满类, 不要混淆
- `grep -cE "both failed|ms.*fail|UPSTREAM-ERROR-SEEN"` = **0** → 0 真中断确认

### breaker
- cc4101 PRIMARY-BREAKER-OPEN 30min = **0**
- nv_gw NV-ANTH-BREAKER-FAIL 30min = **3** (但 state 全 CLOSED: 2/0, 2/0, 2/0 — 只记 failure 未达 5/300s 阈值, 不 OPEN)
- breaker **OPEN 0 连续多轮**
- 注: 日志见 `NV-MS-FB-SERVED state=CLOSED` 是 nv_gw 内部 ms_fb 路径记 failure, 非 NV-ANTH-BREAKER-FAIL 事件, 与 breaker OPEN 无关

### BUG-A 修复 (R1913) 真实生效确认
- 30min 内 `NV-GLM52-CHAIN-SKIP-PEXEC2` 触发 **5 次** (skip _try_tier_keys 第二轮省约 ~120s/fallback 请求)
- vs R1978 4 次, 持续触发验证长期生效 (R1952 6/R1970 4/R1973 5/R1978 4/R1979 5)

## 验证
- env 无漂移 (与 R1978 完全一致; NVU_GLM52_EXP_BACKOFF 不在容器 env 中确认半成品从未激活)
- /health ok (nv_num_keys=5, nvcf_pexec_models=kimi_nv/dsv4p_nv/glm5_2_nv, nv_default_model=dsv4p_nv, proxy_role=passthrough)
- docker ps 全 Up (nv_gw Up 8h, cc4101 Up 9h, ms_gw Up 2d, logs_db Up 3d)
- nv_gw StartedAt = 13:33:43Z (0 restart 维 R1933), cc4101 StartedAt = 12:10:22Z (0 restart 维 R1926)

## 介入四条核验 — 全不满足 → NOP 无据不改
1. **SR**: 6h 95.09% 大样本稳态 (与 R1978 94.81% +0.28pp 0 漂移), 30min 93.88% 小样本偏稳 — 非连续 3+ 轮跌破 80% 介入线 → 不满足
2. **502 分类**: 全 zombie+ATE+first_byte_timeout 已知类 (与 R1978 几乎 0 漂移), 非新可配置类, abs_cap 30min=0/6h=0 (DB 双重确认) → 不满足
3. **breaker**: OPEN 30min=0 连续多轮, nv_gw BREAKER-FAIL 3 条但 state=CLOSED 不 OPEN → 不满足
4. **fallback**: 5/30min 全 FALLBACK-OK 被 ms 兜住 0 真中断, 远低于 15/30min 介入线, 无新监督者激活指令 → 不满足

## 结论
NOP 巡检 R94, 0 改动 0 restart。链路稳态延续: 6h SR 95.09% 与 R1978 0 漂移 (+0.28pp), 0 真中断, abs_cap 连续多轮归零, BUG-A 修复真实生效 5 次/30min, 120s 跑满类持续趋零。指数退避冻结理由 (R1928) 仍成立, 半成品 env 开关从未激活, 风险/收益不对等。继续冻结, 等监督者再授权激活或数据恶化 (SR 连续 3+ 轮跌破 80%) 再动。

**铁律遵守**: 只改 HM2 nv_gw, 不碰 ms_gw (40007 热备保留), 不碰 HM1; 改前必有数据 (本轮已拉 30min/6h), 改后必有验证 (NOP 无改动但已验证 /health+docker ps+日志); 写入仓库 (本轮 commit+push)。
