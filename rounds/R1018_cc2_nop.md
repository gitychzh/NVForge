# R1018: cc2 self-opt — NOP (cc2 主链 128/128=100% 干净, 错误全属 hermes 越界; fallback 0)

日期: 2026-08-07 ~16:30 (BJT)

## 1. 数据 (30min 窗口, live 复核)

### cc2 主链 (cc4101-primary @ nv_gw:40006)
- **SR = 100% (128/128)**, 0 bad
- **cc4101-primary 专属错误 (caller=cc4101-primary, status!=200) = 0 rows**
- 主链当前首代模型 = **dsv4f0731_nv**, 无 tier 降级/无 key 疲劳

### nv_requests 30min (所有 caller)
| caller | status | count |
|---|---|---|
| cc4101-primary | 200 | 128 |
| hermes | 200 | 17 |
| hermes | 502 | 4 |

- 30min 总 SR = 97.3% (146/150); 4 条 bad 全属 **hermes** (越界宿主), 主链 0 bad

### 错误归属 (caller=hermes)
| error_type | count |
|---|---|
| all_tiers_exhausted | 2 |
| NVStream_IncompleteRead | 1 |
| stream_absolute_cap | 1 |

→ 4 条 bad 全属 **hermes**, 经 caller 铁证与主链 host 分离完全干净

### fallback (cc_requests 30min)
- **128 request, fallback 0 次 (0.0%)**

### 容器健康
- nv_gw Up 13h, cc4101 Up 13h, dsv4p_nv40066 Up 2d; /health 全 200

## 2. 判断
- cc2 主链 (cc4101-primary@nv_gw:40006) **128/128 = 100% SR, 专属错误 0 rows**。
- 本轮 all_tiers_exhausted 2 / NVStream_IncompleteRead 1 / stream_absolute_cap 1 全归因 hermes (越界宿主),
  主链 host 分离干净, 无泄漏。fallback 0 次 (0.0%)。
- 无新 cc2 主链错误类, 无持久 key 疲劳, multi-key rr + func_health + buffer (attempt=1 全成功) 仍完全吸收瞬态错误。
- 达到稳态, 无根因可查, 参数无可调。

## 3. 行动
- **NOP (不改码)**。round 文件 + STATE.md 同步入仓库。

## 4. 下一步
- 保持 NOP 观察, 主链 dsv4f0731_nv 为首代, 无需参数改动。
- 持续确认 hermes 越界 bad (502) 与主链 host 隔离 (caller JOIN) 保持干净。