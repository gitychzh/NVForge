# R851 — cc2 NOP 巡检轮 — 近窗 cc4101-primary SR=100% (57×200 零错误)

- **时间**: 2026-08-07 04:22 CST
- **容器**: nv_gw (40006) Up, cc4101 (4101) Up, primary=dsv4f0731_nv (自适应轮转持有)
- **判定**: NOP — 近窗全净, 修复链充分, 不改码

## 本轮数据 (实时拉取, DB UTC 对齐)

**最近 15min cc4101-primary (cc2 路径): 57/57 = 100% SR, 零错误.**

buffer 日志 (20min, warn: 实测全走 dsv4f0731_nv):
- 每条 attempt=1/5 一次成功: 6s / 10s / 1s / 12s / 7s
- verdict 均 success_tool_call 或 success_text, input 66-838c
- **零 buffer_exhausted, 零 WAIT, 零 529**

| 指标 | 值 | 状态 |
|---|---|---|
| **最近 15min cc4101-primary SR** | **100% (57×200, 零错误)** | ✅ |
| **primary 目标 tier** | **dsv4f0731_nv** | ✅ |
| **buffer (近窗)** | attempt=1/5 一次成功, 1-12s, 零 buffer_exhausted | ✅ |
| **fallback (ms_gw 层)** | 近窗 0 次 | ✅ |

## 30min 硬窗口残留 (早期风暴旧痕, 非当前)

30min cc4101-primary: buffer_exhausted×4 (avg 199s) + client_gone_pre_attempt×2.
30min cc4101-primary × model: dsv4f0731_nv SR=95.0% (96/101), glm5_2_nv 502×2.
→ 全为窗口早期 glm5_2_nv 风暴残留, 最近 20min 逐分钟全 200 (零非 200), 与 R844-R850 同型.
glm5_2_nv 仍处退化, 故 cc4101 自适应轮转 pinned dsv4f0731_nv — 这是修复链设计意图.

## 修复链 (沿用, R827+R828+R829+R833+R813)
1. glm5_2_nv 持续疲劳 → R829/R833 fail-fast + cc4101 动态 primary → dsv4f0731_nv
2. dsv4f0731_nv 1-12s 一次成功, 用户无感知
3. dsv4p/dsv4f/glm5_2_nv 多 tier round-robin 自适应吸收底层跨 key 瞬态失败

## 健康检查
- `curl localhost:40006/health` → ok ✅ (nv_gw, passthrough, 5 keys)
- `curl localhost:4101/health` → ok ✅ (cc4101, primary=dsv4f0731_nv)

## 结论
近窗 15min 全净, 无新错误类型, 无回潮. 修复链充分, **不改码**.