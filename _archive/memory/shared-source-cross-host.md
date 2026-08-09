---
name: shared-source-cross-host
description: "ms_gw的upstream.py两机已分叉不同源(2026-07-08确认);HM1/HM2各自独立演进;勿假设共享"
metadata:
  node_type: memory
  type: project
  originSessionId: 0406d561-48f4-457a-9d92-47a11ace0901
---

**2026-07-08 R822 确认:** HM1 与 HM2 的 ms_gw `upstream.py` **已分叉, 不再同源**.
- HM1 (本机): `/opt/cc-infra/proxy/ms-gw/gateway/upstream.py` md5=a9cc85e9 (23475B)
- HM2 (远程): md5=ff5e4a52 (25781B, 容器内挂载一致)
两机各自独立演进, HM2 改得更频繁 (有 R784/R797/R814 等 bak). HM1 有独有逻辑 (FALLBACK_GRAPH 跨 model fallback, glm5_1_nv tier, integrate cooldown).

**历史 (已过时, 仅供参考):** 早期 (R784 前) 两机可能共享同一份, R794 时 HM1 曾落后 HM2 (缺 egress IP 改动), 当时用 `ADD COLUMN IF NOT EXISTS` 幂等回补 schema. 但至今两机 ms_gw upstream.py 已实质分叉.

**How to apply:** 改 HM2 的 ms_gw 源码 (upstream.py/db.py/schema) **不会**直接影响 HM1, 因已不同源. 但仍应外科式 patch (备份 .bak.preXXX + 精确替换 anchor), 不整覆盖, 以便回滚. 改完只重启 HM2 的 ms_gw 容器. cc4101 源码则一直是 HM2 独有 (cc4101 只在 HM2). 相关 [[host-roles-and-self-positioning]] [[cross-host-collab-roles]]
