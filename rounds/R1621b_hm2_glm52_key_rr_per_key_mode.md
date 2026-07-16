# R1621b HM2: glm5_2_nv 调度模型修正 — key RR 轮流 + 每 key 绑定自己的 mode

**状态: 已执行 + 验证通过 (2026-07-16).** 修正 R1621 的调度模型误解.

## R1621 的错误 (用户指出)

R1621 实现的是"mode 指针递进 + key 在 mode 子集内轮换":
- 当前 mode 固定 (如 integrate), 只在 k1/k3/k5 子集内轮换.
- k2/k4 (pexec) 只有在 integrate 全失败递进时才触发.

**用户真实意图**: 正常请求 RR 轮流 k1→k2→k3→k4→k5, 每 key 走自己绑定的 mode
(k1/k3/k5→integrate, k2/k4→pexec), 不是"故障才 fallback". 故障处理: 某 key 失败
→ cooldown 该 key → 跳下一 key(走它自己 mode), 全 5 key 失败才 all_keys_exhausted.

R1621 验证时 6 req 全走 integrate (k1/k3/k5), k2/k4 永不调用 → 暴露模型错误.

## R1621b 修正

### 改动 1: config.py — 反转绑定方向
- 删 `MODE_KEY_BINDINGS` (mode→keys 子集)
- 加 `KEY_MODE_BINDING` (key→mode_name), env `KEY_MODE_BINDING=0:integrate_us_rr;1:pexec_us_rr;...`
- `NV_GLM52_KEY_PROXY_MAP` (key→固定 proxy) 保留不变.

### 改动 2: upstream.py `_try_glm52_mode_chain` — 反转调度模型
旧循环 (mode 指针驱动):
```
mode_name = modes[mode_idx]  # 当前 mode 固定
key_idx = bound_keys[(start+attempt) % len]  # 在 mode 子集内轮换
故障 → mode_idx 递进
```
新循环 (key RR 驱动):
```
key_idx = (start_key + attempt) % NVU_NUM_KEYS  # 全 5 key 轮流
mode_name = KEY_MODE_BINDING[key_idx]  # 每 key 查自己 mode → _mode_lookup
故障 → cooldown 该 key + advance RR (不递进 mode 指针)
```
- `_mode_lookup = {m[0]: m for m in modes}` 建反查表.
- 未绑定 key → 用 mode_idx 指针兜底 (向后兼容).
- import 改 `KEY_MODE_BINDING`.

### 改动 3: compose env
- `MODE_KEY_BINDINGS=...` → `KEY_MODE_BINDING=0:integrate_us_rr;1:pexec_us_rr;2:integrate_us_rr;3:pexec_us_rr;4:integrate_us_rr`
- `NV_GLM52_MODE_CHAIN` / `NV_GLM52_KEY_PROXY_BIND` 不变.

### 改动 4: 部署 + 验证
- 备份: config.py.bak.R1621b / upstream.py.bak.R1621b / docker-compose.yml.bak.R1621b
- `docker compose up -d --force-recreate nv_gw` + idx reset=0
- health 200

## 验证 (改后必有数据)

10 个测试请求全 200, DB `nv_requests` (时间倒序) 确认:
| key | mode | egress_route | 端口 |
|---|---|---|---|
| k1 | integrate | 7894 | 193 |
| k2 | pexec | 7895 | — |
| k3 | integrate | 7896 | 195 |
| k4 | pexec | 7897 | — |
| k5 | integrate | 7899 | 180 |

→ **k1→k2→k3→k4→k5 轮流, mode 按 integrate/pexec/integrate/pexec/integrate 交替**
→ 每 key 永远走自己绑定的端口, IP 不漂移
→ 故障时 cooldown 该 key 跳下一 key (走它自己 mode), 不再"故障才 fallback"

## 回滚
- compose: `cp docker-compose.yml.bak.R1621b docker-compose.yml`
- 源码: `docker exec nv_gw cp gateway/config.py.bak.R1621b gateway/config.py` (同 upstream.py)
- 回到 R1621 原版: 用 .bak.R1621 (无 b)

## 铁律
破"只改 HM1 不改 HM2" — 用户授权. 关联 R1621.
