# R1003 cc2 NOP inspection round — cc2 主链路连续第 111 轮 100% 干净

- **轮号**: R1003 (自 R893 起连续第 111 轮 cc2 主链 100% SR 干净)
- **时间**: 2026-08-07 15:29 CST
- **判定**: **NOP 巡检轮, 不改码**
- **容器**: nv_gw Up 12h, cc4101 Up 12h, /health 全 200

## 链路数据 (live re-pull 2026-08-07 + 注入轮前链路分析)

### 主链 SR (nv_requests, caller=cc4101-primary, 30min live)
| status | count |
|---|---|
| 200 | **109** |

→ **109/109 = 100% SR, 0 bad**

### 主链专属错误 (caller=cc4101-primary, status!=200, 30min)
```
 error_type | count
------------+-------
(0 rows)
```
→ **0 rows**, 主链无任何非 200 请求。

### cc_requests (30min, fallback 计数)
| upstream_used | total | ok | fb |
|---|---|---|---|
| primary | 1979 | 1979 | **0** |
| fallback | 5 | 0 | 0 |

→ cc2 主链 primary 全 200, **fallback = 0 次**。5 条 upstream_used=fallback 的 0-ok 记录为非主链调用者 (hermes 线越界宿主 fid 52e1ddb6 泄漏), host 分离保持。

### buffer 日志 (docker logs nv_gw --since 30m)
- 全 **attempt=1 一次成功**: `[NV-BUFFER-SUCCESS] ... flushed Xb after 1 attempt(s)`。
- 无 BUFFER-/WAIT- 停滞, 无 WAITQUEUE 阻塞, 全 8-12s 内一次直达。

### 注入轮前链路分析摘要
- 30min cc4101-primary|dsv4f0731_nv|200 = 106 (注入时刻) → live re-pull 后 109。
- 总 bad (nv_requests 非 200) = 5 条, 全属 **hermes|dsv4f0731_nv|502** (zombie_empty_completion ×3 + all_tiers_exhausted ×2), 主链 0。
- top error (全 caller) = zombie_empty_completion ×3, 归属 hermes 非主链。
- nv_tier_attempts per-key: RemoteDisconnected+Timeout 少量散布 k0-k4, 全部被 multi-key round-robin + func_health + buffer 吸收, 无持久 key 疲劳。

## 判定: NOP (不改码)

**理由**:
1. 主链 SR 100% (109/109), 专属错误 0 rows, fallback 0 → 无优化需求。
2. 本轮 bad 全属 hermes 越界宿主 (fid 52e1ddb6 泄漏), 主链无根因可查。
3. multi-key round-robin + func_health + buffer (attempt=1 全成功) 已达稳态, 无参数可调。
4. 连续 111 轮 (R893-R1003) 干净, 改动反而引入风险。

## 下一步
- 保持 NOP 观察; 主链首代 dsv4f0731_nv。
- 继续确认 hermes 越界 bad 与主链 host 隔离保持。