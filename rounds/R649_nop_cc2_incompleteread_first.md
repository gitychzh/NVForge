# R649: NOP 巡检轮 — cc2/glm5_2_nv 路径 IncompleteRead 首现 + 保护 gap 定位

**轮次**: R649
**角色**: HM2 (opc2_uname) 优化 HM2 nv_gw (40006)
**日期**: 2026-08-03 15:24 CST

## 改动
NOP, 不改码. 仅数据巡检 + 路径根因定位.

## 依据 (实测 30min DB 14:54-15:24 CST)
- cc2 (cc4101-primary/glm5_2_nv) 30min: 14 req = 13×200 + 1×502 (SR=92.9%)
- dsv4p_nv (hermes caller) 30min: 26 req 22×200+4×429 (SR=84.6%, 配额型持平 R647)
- 配置实测无漂移: nv_gw NVU_DISABLE_MS_FALLBACK=1, buffer 5key×90s=450s; cc4101 PRIMARY=glm5_2_nv, FALLBACK=dsv4p_nv40066(非ms_gw), STREAM_TOTAL=470

## 根因定位 (cc2 路径 502)
- 日志铁证: `[ERR] NV-ANTH collect IncompleteRead after 34382ms: IncompleteRead(613 bytes read)` (handlers.py:1813)
- 路径 = cc4101-primary + 非流式请求 → execute_request **成功**拿 NVCF 流 → _collect_stream_to_anth (handlers.py:967) 读流 → **34s 后 NVCF 流中途断, 只读 613 bytes** → 直接落 502
- **保护 gap**: handlers.py:910 非流式 buffer 5key 重试只在 `not result.success` (execute_request 失败) 时触发, 这里 execute_request 成功但 collect 读流中断 → 落在盲区; ms_gw fallback (handlers.py:1858) 因 NVU_MS_FALLBACK_ENABLED=0 也不触发
- tier 层 RemoteDisconnected×N + SSLEOFError×N (k2/k3/k4/k5) 都被正确 mode→advance + 5-10s 短惩罚处理 (KeyManager mark_transport_error 生效), 未冻结 key

## 验证
- deadline 链 6h: stream_total_deadline=0 (健康铁证)
- /health ok: nv_num_keys=5, nv_default_model=glm5_2_nv
- 容器: nv_gw Up 9min, cc4101 Up 8min, dsv4p_nv40066/nv_gw_stable/ms_gw/logs_db 均 Up
- cc2 13 例成功 avg 46s max 101s (NVCF 慢但能完成)

## 保护 gap 分析 (待数据积累后改)
**为何不改**:
1. 单例不足以支撑���等复杂度改动 (collect 中断后重试需重建 conn + 重发 NVCF, 需保证 oai_body 幂等)
2. R644-R648 IncompleteRead 都在 dsv4p/hermes 路径单发, 本轮是 cc2/glm5_2_nv 路径首现, 未达"持续模式"阈值
3. 改 collect 重试逻辑风险高于收益 (当前 13/14=92.9% 实际可用, 改动可能引入新 race)

**阈值**: 若 cc2 路径 IncompleteRead 连续 3 轮单发 或 单轮 >=2/30min → 评估在 handlers.py:1810 catch IncompleteRead 后触发 buffer 5key 重试 (类似 :910 的非流式 retry, 但入口条件改为 collect 中断)

## 下一步
- 本轮 NOP, 链路实测健康 (cc2 13/14=92.9% 实际可用, 1 例非持续, deadline 链 0 触发, 配额型故障非 nv_gw 可改)
- 持续观察点:
  1. cc2 路径 IncompleteRead 连续性 (R649 首现)
  2. dsv4p_nv 配额型 429 全挂 (24h+ 持续, NVCF 无 retry-after 头)
  3. deadline 链健康 (6h=0)
- 建议维持: 联系 NVCF 侧评估 dsv4p_nv 账户配额扩容 / 提供 retry-after 头 / 慢响应根因
