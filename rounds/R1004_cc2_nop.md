# R1004 cc2 NOP inspection round — cc2 主链路连续第 112 轮 100% 干净

- **轮号**: R1004 (自 R893 起连续第 112 轮 cc2 主链 100% SR 干净)
- **时间**: 2026-08-07 15:33 CST
- **判定**: **NOP 巡检轮, 不改码**
- **容器**: nv_gw Up 17h, cc4101 Up 12h, /health 全 200

## 链路数据 (live re-pull 2026-08-07 + 注入轮前链路分析)

### 主链 SR (nv_requests, caller=cc4101-primary, 30min)
| status | count |
|---|---|
| 200 | **105** |

→ **105/105 = 100% SR, 0 bad**

### 主链专属错误 (caller=cc4101-primary, status!=200, 30min)
```
 error_type | count
------------+-------
(0 rows)
```
→ **0 rows**, 主链无任何非 200 请求。

### cc_requests (30min, fallback 计数)
| total | ok | fb |
|---|---|---|
| 108 | 108 | **0** |

→ cc2 主链 primary 全 200, **fallback = 0 次**。

### 全 caller bad 归属判定 (nv_requests 非 200, live re-pull)
```
 caller | status |  req    | error_type
--------+--------+---------+-------------------------
 hermes | 502 | f1442706 | all_tiers_exhausted
 hermes | 502 | 556047ef | zombie_empty_completion
 hermes | 502 | dedbc911 | all_tiers_exhausted
 hermes | 502 | b20bbea6 | all_tiers_exhausted
 hermes | 502 | 90642d3c | zombie_empty_completion
 hermes | 502 | 60266ff8 | zombie_empty_completion
(6 rows)
```
→ 6 条 502 **全属 hermes** (3 all_tiers_exhausted + 3 zombie_empty_completion), 主链 0; host 隔离保持。

### buffer 日志 (docker logs nv_gw --since 30m)
- 全 **attempt=1 一次成功**: `[NV-BUFFER-SUCCESS] ... flushed Xb after 1 attempt(s)`。
- verdict 全 success_text / success_tool_call (tool id+args True), elapsed 1-13s。
- 无 BUFFER-/WAIT- 停滞, 无 WAITQUEUE 阻塞。

### 注入轮前链路分析摘要
- 30min cc4101-primary|dsv4f0731_nv|200 = 105 (注入) → live re-pull 一致 105。
- 全模型 dsv4f0731_nv SR = 95.1% (116/122), bad 6 条全 hermes。
- top error = all_tiers_exhausted ×3 + zombie_empty_completion ×3, 归属 hermes 非主链。
- nv_tier_attempts per-key: RemoteDisconnected(+Timeout) 少量散布 k0-k4, 全被 multi-key round-robin + func_health + buffer 吸收, 无持久 key 疲劳。

## 判定: NOP (不改码)

**理由**:
1. 主链 SR 100% (105/105), 专属错误 0 rows, fallback 0 → 无优化需求。
2. 本轮 6 条 bad 全属 hermes 越界宿主 (fid 52e1ddb6 泄漏), 主链无根因可查。
3. multi-key round-robin + func_health + buffer (attempt=1 全成功) 已达稳态, 无参数可调。
4. 连续 112 轮 (R893-R1004) 干净, 改动反而引入风险。

## 下一步
- 保持 NOP 观察; 主链首代 dsv4f0731_nv。
- 继续确认 hermes 越界 bad 与主链 host 隔离保持。