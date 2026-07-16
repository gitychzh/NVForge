# R1621c HM2: glm5_2_nv key 干净 RR 轮流 (修双 advance + counter 共用 bug)

**状态: 已执行 + 验证通过 (2026-07-16).** 修 R1621b 的两个 RR 调度 bug.

## 用户指出的逻辑核对

用户问: "即使不故障也正常轮流, 故障时重复上一请求用下一 key, 不故障往下一 key 是新请求, 对吗?"
→ 逻辑方向对, 但实测发现两个 bug 导致不故障时 key 顺序跳位.

## Bug 1: 双 advance (upstream.py `_try_glm52_mode_chain`)

R1621b 代码:
```
start_key = _next_nv_key(tier_model)   # advance 1 (返回当前 + counter+=1)
... 成功 ...
_next_nv_key(tier_model)                # advance 2 (成功又 counter+=1)
```
→ 每次成功请求 counter 跳 2, key 顺序变 k1→k3→k5→k2→k4 (跳着走, 非顺序轮流).
实测: 清 counter 后 6 req 顺序 = k2,k4,k1,k3,k5,k2 (跳位).

**修正**: `start_key = _peek_nv_key(tier_model)` (只 peek 不 advance), 成功后才 `_next_nv_key`.
→ 不故障: reqA k1 成功 advance→k2, reqB k2 成功 advance→k3... 干净 k1→k2→k3→k4→k5.

## Bug 2: glm5_2_nv counter 共用 dsv4p (rr_counter.py)

`_TIER_RR_KEYS` 只映射 kimi_nv/dsv4p_nv, **没 glm5_2_nv** → 走默认 "nv_dsv4p".
glm5_2_nv 和 dsv4p_nv 共用同一 counter (值 19666), dsv4p 请求也 advance 这个 counter,
导致 glm5_2_nv 的 key 轮换被 dsv4p 流量干扰.

**修正**: `_TIER_RR_KEYS` 加 `"glm5_2_nv": "nv_glm5_2"` (独立 counter).

## 验证 (改后必有数据)

清 `nv_glm5_2` counter=0, force-recreate, 发 6 req, DB 时间正序:
```
k1 integrate → k2 pexec → k3 integrate → k4 pexec → k5 integrate → k1 integrate
```
→ **干净顺序轮流 k1→k2→k3→k4→k5→k1**, mode integrate/pexec 交替.
→ 不故障时每新请求往下一 key; 故障时同请求内 attempt+1 换下一 key 重试.

## 改动
- rr_counter.py: `_TIER_RR_KEYS` 加 `"glm5_2_nv": "nv_glm5_2"`. 备份 .bak.R1621c.
- upstream.py: line 1250 `start_key = _peek_nv_key(...)` (原 `_next_nv_key`); 成功分支注释更新.
  备份 .bak.R1621c.
- 部署: force-recreate nv_gw + 清 rr_counter.json `nv_glm5_2`=0.

## 回滚
- rr_counter.py: `cp gateway/rr_counter.py.bak.R1621c gateway/rr_counter.py`
- upstream.py: `cp gateway/upstream.py.bak.R1621c gateway/upstream.py`
- 重启: `docker compose up -d --force-recreate nv_gw`

## 铁律
破"只改 HM1 不改 HM2" — 用户授权. 关联 R1621/R1621b.
