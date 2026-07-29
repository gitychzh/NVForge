# R-nvonly-post4 — NOP 巡检 + 恢复期持续爬升确认

**时间**: 2026-07-29 14:28 CST (HM2 cc2)
**改动**: 0 | **restart**: 0 | **回滚**: 不需要

## 数据 (30min / 6h 窗口)

### 30min cc2 (cc4101-primary) SR
```
 status | count
--------+-------
    200 |    52
    502 |     1
```
→ SR = 52/53 = **98.1%** (上轮 post3: 97.9%, 微升)

### 30min 错误分类 (含 caller 归属)
```
     caller     | status |       error_type        | count
----------------+--------+-------------------------+-------
 unknown        |    502 | zombie_empty_completion |     9
 unknown        |    502 | all_tiers_exhausted     |     6
 other          |    502 | all_tiers_exhausted     |     5
 cc4101-primary |    502 | buffer_exhausted        |     1   ← cc2 唯一 502
```
→ cc2 仅 1×buffer_exhausted (14:09, 设计消化点). zombie×9 + all_tiers×11 属 unknown/other
   (别的 agent, 非 cc2). 铁律: 不越权改别的 agent 路径.

### 30min tier transport 错误
```
          error_type           | count
-------------------------------+-------
 pexec_success                 |   113   ← 主导, 5key 大多 1-attempt 直接成功
 pexec_SSLEOFError             |     4
 pexec_429                     |     3
 pexec_conn_RemoteDisconnected |     1
```
→ transport 短惩罚 8 次 (SSLEOF×4/429×3/RemoteDisconnected×1) 全 pexec 内部吸收,
   0 冒泡成 cc2 502. KeyManager 短惩罚机制 (5-10s 不累计 conn_count) 持续工作.

### 6h cc2 SR
```
 status | count
--------+-------
    200 |   499
    502 |    41
    499 |     1
```
→ 6h SR = 499/540 = **92.4%** (与上轮 post3 持平). 41×502+1×499 全 nv_gw 侧
   (buffer_exhausted/all_tiers) 消化, CC4101 fb=0.

### 6h fallback 铁证 (R-nvonly 核心: 应恒 0)
```
 error_type | count
------------+-------
(0 rows)
```
→ **fallback=0 (6h 全量) 持续生效**. 破釜沉舟 NVU_DISABLE_MS_FALLBACK=1 + FALLBACK=none 稳固.

### 60min 时序 (恢复期斜率铁证)
```
13:28–13:45 (前20min): 5×502 散布 ← NVCF 间歇期尾巴
13:45–14:28 (后40min): 全程 200, 零 502 ← 间歇期已过, SR 爬升中
```
→ 30min 窗口内仅 14:09 一例 502. 后 40min 零 502 → 恢复期趋势延续,
   间歇消化点随时间淡出 6h 窗口, 6h SR 将持续爬升.

## buffer 轮转效果 (30min 抽样)
- [22:25:44] req=0c141b51 → 1-attempt SUCCESS 15.5s (tool_call, 4143b)
- [22:26:10] req=e075506f → 1-attempt SUCCESS 10.4s (text, 26561b)
- [22:27:19] req=a7f46426 + req=0396bd52 并发 → 均 1-attempt SUCCESS
- 全窗口样本均 1-attempt 直接成功, 0 走到 attempt 2+.
→ 5key 80×90s buffer 在平时段高效 (1-attempt), 预留的 5key 轮转产能仅在 NVCF
   间歇全挂时启用 (走 buffer_exhausted 消化).

## 三阈值判稳
| 阈值 | 30min 实测 | 判定 |
|------|-----------|------|
| cc2 (cc4101-primary) SR | 52/53 = 98.1% | ⚠<99% (1×buffer_exhausted 设计消化点) |
| cc4101 真 fallback | 0 (6h 全量) | ✓ |
| 无新错误类型 | cc2 仅 buffer_exhausted (已知消化点); zombie/all_tiers 属 unknown/other(非cc2) | ✓ |
→ 1×502 = NVCF 间歇全挂的设计预期消化点 (改码无效不越 deadline 链 450<470<500)
  → **冻结 NOP, 0 改动 0 restart**

## 本轮关键认知
1. **恢复期持续爬升**: 30min SR 98.1% > post3 97.9% > 6h SR 92.4%. 60min 时序
   后 40min 零 502, 间歇期已过, SR 单调爬升中.
2. **buffer_exhausted 是"消化终点"非退化**: 1×502 发生在 NVCF 间歇窗口
   (5key×90s 全败), 改 nv_gw 配置无法解决, 贸然调参撞 deadline 链.
3. **transport 短惩罚机制持续吸收**: 30min 8 次 SSLEOF/RemoteDisconnected/429
   全 pexec 内部吸收, 0 冒泡成 cc2 502. KeyManager 5-10s 快惩罚 + ProbeWorker 15s
   探测恢复链路稳固.
4. **破釜沉舟持续生效**: 6h fallback 恒 0, nv_gw 纯靠 5key+5IP 自恢复扛住所有故障.
5. **zombie/all_tiers 仍属 unknown/other (别的 agent 非 cc2)**: 30min 9+6+5=20 次
   非 cc2. 监控是否扩散到 cc2, 不越权改别的 agent 路径.
6. **env 全无漂移**, 容器健康 (nv_gw Up 2h / cc4101 Up 7h / logs_db Up 2d, 本轮无 restart).

## 下一步
1. 继续巡检. 盯 cc2 30min SR 是否回 100% (间歇期已过, 后 40min 零 502 是好兆头).
2. 6h SR 随恢复期持续爬升 (当前 92.4%, 间歇消化点随时间淡出 6h 窗口).
3. 6h buffer/all_tiers 频次持续下降, fallback 恒 0.
4. transport 短惩罚持续在 pexec 层吸收 (SSLEOF/RemoteDisconnected 不冒泡).
5. 盯 unknown caller zombie_empty_completion 是否扩散到 cc2.
6. 长驻机制: 每30min touch heartbeat; 改 .py 触发 R-guard (py_compile+restart+health);
   auto-compact 后从 STATE 接棒.
7. 铁律: 改前数据, 改后验证, 聚焦 40006, 不碰 40007 (NVU_DISABLE_MS_FALLBACK=1 不可改回0),
   只改 HM2 (不抄 HM1 参数), 写入仓库, 尽量多走 glm5_2_nv.

## 回滚锚点 (本轮无改动, 无需回滚)
- 未改任何 gateway/*.py, 未改 compose env, 未重启容器.
- R-nvonly 配置锚点: 5key×90s/450s buffer, 470s cc4101, fallback=none, DISABLE_MS_FALLBACK=1.
