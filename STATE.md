# STATE.md — cc2 自优化 nv_gw 链路 (HM2)

> 当前轮: **R970 (NOP 巡检轮/不改码 — cc2 主链路连续第 78 轮 100% 干净; 坏请求 3: 502 zombie_empty_completion ×2 + 502 all_tiers_exhausted ×1 全属 hermes 线 + fid 52e1ddb6, 双重归属非 cc2 范围; fallback 0 次)**
> cc4101-primary (主 nv_gw:40006) 实时 30min = **119/119 = 100% SR, 0 bad** (live 复核);
> cc4101-primary 专属错误 = **0 rows** (119 request 全 200);
> 容器: nv_gw Up 9h, cc4101 Up 9h, dsv4p_nv40066 Up 2d, nv_gw_stable Up 5d
> 上轮: R968 (NOP, 主链 125/125=100%)

## 本轮 (R970) 改动 + 依据 + 验证

### 改动: 无 (NOP。cc2 主链路连续 78 轮 100% 干净, 主专属错误 0 行; bad 请求全属 hermes+已知坏 fid 非 cc2)

### 依据 (注入轮前链路分析 ≈2026-08-07 12:56 CST + live 复核 bad 归属/fallback)

- 30min cc4101-primary (主 nv_gw:40006) = **119/119 全 200 = 100% SR, 0 bad** (live re-pull)。
- 总 nv_requests 30min = 148 req, dsv4f0731_nv SR=98.0% (145/148)。
- 3 个 bad (非 200) = **均 `caller=hermes` + `fid=52e1ddb6`** (已知坏 fid, hermes 宿主越界
  容器): `502 zombie_empty_completion ×2` + `502 all_tiers_exhausted ×1`, caller+fid
  双重归属 hermes, non cc2 主链。
- fallback (cc_requests 30min) = **0 次** (120 req, fb=0; 全 status=200, SR=100%)。
- nv_tier_attempts 30min (per-key): pexec_success 25/23/24/24/25 (k0-k4) +
  NVCFPexecRemoteDisconnected k0×4,k1×2,k2×5,k3×5,k4×5 + 529_nv_overloaded k1×1 +
  empty_200 k2×1 — 全瞬态被多 key round-robin + func_health + buffer 吸收, 全部 resolve 为 200。
- buffer 日志 (nv_gw): 一条 NV-BUFFER-EXEC-FAIL (req 91ff4cf9, attempt1 key 主干 all_keys_exhausted)
  → 5s backing off → attempt2 重试; 其余 cc4101-primary 全 attempt=1 成功流
  (success_tool_call 3550ms/13s), 无错误噪声。

### 本轮数据

| 指标 | 值 | 状态 |
|---|---|---|
| 主 nv_gw(40006) cc4101-primary | **119/119 = 100% SR, 0 bad** (live re-pull) | ✅ |
| 主链专属错误 (caller=cc4101-primary) | **0 rows** | ✅ |
| 唯一 bad (非 200) | 502 zombie_empty_completion ×2 + 502 all_tiers_exhausted ×1 (均 caller=hermes, fid=52e1ddb6) | ⚠️ 越界 |
| bad caller 归属 | 全 caller=hermes + fid=52e1ddb6; cc2 primary 0 条 | ✅ 隔离 |
| fallback (cc_requests) | 0 次 (120 req 全 200) | ✅ |
| tier 瞬态错误 | RemoteDisconnected 19 / 529 1 / empty_200 1, 全被吸收 | ✅ |
| 全局 nv_requests SR | 145/148 = 98.0% (dsv4f0731_nv) | ✅ |

### 验证
- 30min nv_requests cc4101-primary = 119/119 (0 bad)。
- bad 分组 (caller+fid 归属): 502 zombie_empty_completion ×2 + 502 all_tiers_exhausted ×1
  均 caller=hermes + fid=52e1ddb6, cc2 主链 0 bad。
- cc_requests fallback = 0 次 (120 req 全 200, SR=100%)。
- docker logs nv_gw buffer 段: 唯一 execute_failed req 91ff4cf9 被 buffer 5s 退避→attempt2 重试吸收,
  无 WAIT-/KEYMGR- 错误噪声, cc4101-primary 全 attempt=1 成功流。
- 容器全 upstream: nv_gw Up 9h, cc4101 Up 9h, dsv4p_nv40066 Up 2d。

### 关键判断
cc2 主链路连续第 **78** 轮 (R893-R970) 100% SR 干净, 且主链专属错误 0 rows。
3 个 bad 请求 100% 属 hermes (caller+fid 双重归属 502 zombie_empty_completion +
all_tiers_exhausted, 均落在已知坏 fid 52e1ddb6 上), fallback 0 次, 无新 cc2 主链错误类,
无持久 key 疲劳。
**不改码**: ①主链 SR 100% + 专属错误 0 行, 无优化需求; ②坏请求全属 hermes 越 cc2 范围;
③多 key round-robin (dsv4f0731_nv 为首) + func_health + buffer 已达稳态, 瞬态错误全被吸收。

## 修复链 (沿用, R827+R828+R829+R833+R813 + R869+R876+R891)
1. glm5_2_nv 全 key 疲劳 → R829/R833 fail-fast + cc4101 动态 primary → dsv4f0731_nv
2. dsv4f0731_nv 一次成功 (主链已用健康模型), 用户无感知
3. 多 tier round-robin + func_health fid 健康选择自适应吸收底层跨 key/fid 瞬态失败
4. 坏 fid 52e1ddb6 (hermes 宿主) 与主链健康 fid 容器+候选池双层隔离