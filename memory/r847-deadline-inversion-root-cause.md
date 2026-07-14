---
name: r847-deadline-inversion-root-cause
description: R847 upstream stream interrupted 真根因=cc4101 stall-watcher IDLE_GAP(60s) 先于 nv_gw TOTAL_DEADLINE(90s) 触发致 content_filter chunk 迟到被丢; 修 IDLE_GAP 60→100s; 我(HM1)不卡因走 legacy_cc_1→glm5.1纯MS不经nv_gw
metadata: 
  node_type: memory
  type: project
  originSessionId: 3c8d8f5f-50f9-4f31-9c0c-b1eae74a0183
---

# R847: upstream stream interrupted 真根因 = deadline 倒挂

## 真根因 (时序铁证, 2026-07-14 req=51a4127b 18:15)
- nv_gw passthrough idle deadline = **90s** (ttfb 后绝对, `NVU_STREAM_TOTAL_DEADLINE_S`, 不随真内容刷新)
- cc4101 stall-watcher IDLE_GAP = **60s** (无真内容间隙, `CC4101_STREAM_IDLE_GAP_S`)
- 60s < 90s → **cc4101 永远先兜底**: cc4101 在 ttfb 后 60s 就 raise `stream_idle_stall` → `interrupted=True` → emit "upstream stream interrupted" → 返回. 此时 nv_gw 还没到 90s, 还没发 content_filter err_chunk → **chunk 永远迟到被丢**.
- 时序: 18:15:41 nv_gw 发 content_filter chunk, 但 cc4101 last_progress_time 仍老化到 60s 才在 18:15:47 报 IDLE-STALL → 证明 cc4101 没收到/没解析那个 chunk.

## 为什么 R846 Fix5/6 没治住
Fix5(cc4101 malformed 兜底提取 content_filter) + Fix6(nv_gw 前置 \n\n) 只在 **nv_gw 先发、cc4101 后兜底** 场景生效(如 16:30 zombie=True 那类, nv_gw ttfb 前判空僵尸先发 chunk). 走 idle-deadline 路径时 nv_gw 90s > cc4101 60s, cc4101 先返回, Fix5/6 够不着.

## 修复 R847 (已应用, bind mount 宿主源码)
`/opt/cc-infra/proxy/cc4101/gateway/config.py`: `CC4101_STREAM_IDLE_GAP_S` 60s → **100s**.
- 100s > nv_gw 90s → nv_gw 先兜底先发 content_filter chunk, cc4101 后兜底(100s)才能收到 → 走 ZOMBIE-CONTENT-FILTER→api_error 502 正确路径.
- 副作用: 真静默场景多等 40s; 正常长请求不受影响(真内容持续刷新 last_progress_time 不触发 IDLE_GAP).
- 不动的: cc4101 TOTAL_DEADLINE=360s(兜纯挂死), nv_gw TOTAL=90s(上游侧).
- live 验证: IDLE_GAP=100.0 TOTAL=360.0 POLL=30.0.

## 为什么我自己(HM1 本地 CC)不卡 — 系统性对比
- 我走 `legacy_cc_1`(40001)→`legacy_ms_litellm`(41001, **glm5.1 纯 MS baseline**), **不经过 nv_gw**.
- HM2 cc4101 走 `nv_gw`(40006)→glm5_2_nv(NVCF).
- 我链路无 stall-watcher / 无双层 deadline 倒挂结构 → 不会合成 "upstream stream interrupted" 这个 cc4101 特有错误.
- **你卡、我不卡的根本原因 = 链路结构差异, 不是配置问题.**

## 关联
- [[r846-stream-interrupted-fix]] — R846 三层根因(OSError bug + total_deadline 误杀 + content_filter 被 malformed 吞), R847 是其第四层(idle deadline 倒挂), Fix5/6 的前提条件未满足.
- [[r845-cc4101-stall-watcher-b2-b5-fix]] — stall-watcher 双门槛设计, IDLE_GAP 即此处调.
- [[cc-chain-layout-hm2]] — HM2 链路 cc4101→nv_gw/ms_gw.
EOF