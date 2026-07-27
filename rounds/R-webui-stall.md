# R-webui-stall: cloudcli webui SDK watchdog 600s→900s 对齐 nv_gw buffer 层 (HM2)

## 时间
2026-07-27 18:25 CST

## 现象
cloudcli webui session 867ef8fb (衍生 session 1d7b2d90) 卡死, CC 报错:
- "The user doesn't want to proceed with this tool use. The tool use was rejected"
- "API Error: The operation timed out."

## 根因链 (4层叠加)
1. **NVCF Remote end closed**: glm5_2_nv 5 key 全部 "Remote end closed connection without response" (k2/k5 失败, k3 第三次成功 117s). NVCF function/account 级间歇故障.
2. **nv_gw buffer 层 4key 重试**: 4×150s=600s 最大预算, NVCF 降期时全部耗完.
3. **cc4101 STREAM_TOTAL_DEADLINE_S=800s**: 在 nv_gw buffer 还在重试时 cc4101 等.
4. **cloudcli-webui SDK watchdog 600s** ← **根因**: watchdog 600s < nv_gw buffer 600s, NVCF 重试期间 SDK 无数据 → watchdog 到点 interrupt() 中断 session → claude --resume 新 session 同样超时 → 死循环.

## 关键数据
- cc_requests last 1h: 345×200 / 114×stream_total_deadline(24%) / 7×client_gone / 1×server_5xx
- stream_total_deadline hourly: 08h=8, 09h=5, 10h=11, 11h=19, 12h=14, 13h=11, 14h=20, 15h=12, 16h=10, 17h=9, 18h=4
- 11h-14h 峰值(19-20 stalls/h) = NVCF 最严重降期
- cc2-resume 35 consecutive setsid failures since 09:01 (NVCF 降期时 claude 起不来)
- NVCF 已恢复 (18:35 实测 8/8 200, 6-23s)

## 改了什么
1. `~/.config/systemd/user/cloudcli-webui.service.d/R2258-watchdog-600s.conf`:
   `CLAUDE_STREAM_IDLE_TIMEOUT_MS=600000` → `900000` (600s→900s)
   - 对齐: watchdog 900s > cc4101 deadline 800s + 100s flush 余量
   - 覆盖: nv_gw buffer 4×150=600s + cc4101 flush 时间

2. 停止并清理卡死进程:
   - kill webui session 867ef8fb 衍生进程 (3832609, 3832611)
   - kill cc2-resume claude 进程 (3831231, 3831232)
   - stop cc2-resume.timer + cc2-resume.service (NVCF 降期时空转)

3. 恢复:
   - NVCF 恢复后 re-enable cc2-resume.timer

## 超时层级对齐 (改后)
| 层 | 参数 | 旧值 | 新值 | 关系 |
|----|------|------|------|------|
| cloudcli-webui SDK | CLAUDE_STREAM_IDLE_TIMEOUT_MS | 600s | **900s** | > cc4101 deadline |
| cc2-resume SDK | CLAUDE_STREAM_IDLE_TIMEOUT_MS | 850s | 850s (不动) | > cc4101 deadline |
| cc4101 | CC4101_STREAM_TOTAL_DEADLINE_S | 800s | 800s (不动) | > nv_gw buffer |
| nv_gw buffer | NVU_BUFFER_TOTAL_DEADLINE_S | 600s | 600s (不动) | = 4×150s stairs |
| nv_gw buffer | NVU_BUFFER_TIMEOUT_STAIRS | 150×4 | 150×4 (不动) | per-key timeout |

不变: cc4101 deadline 800s 和 cc2-resume 850s 本就合理, 只 webui watchdog 600s 是短板.

## 验证
- cloudcli-webui restart OK, `CLAUDE_STREAM_IDLE_TIMEOUT_MS=900000` 生效 ✓
- nv_gw /health OK ✓
- E2E glm5_2_nv 200 OK (6s, 非流式) ✓
- NVCF glm5_2_nv last 10min: 8/8 200 (6-23s) ✓
- cc2-resume.timer re-enabled ✓

## 回滚
- watchdog: `sed -i 's/900000/600000/' ~/.config/systemd/user/cloudcli-webui.service.d/R2258-watchdog-600s.conf && systemctl --user daemon-reload && systemctl --user restart cloudcli-webui`

## 关键认知
1. webui watchdog 600s 是全链路最短板 — 比 nv_gw buffer 最大预算(600s)还短, NVCF 降期重试时必被 interrupt
2. cc2-resume.sh 早已设 850s (R-deadline650 注释), 但 webui systemd drop-in 漏改 (R2258 只改了 default→600, 没有进一步调)
3. NVCF "Remote end closed" 是 function/account 级间歇故障, 非 key/IP 级, 重试可恢复 (本轮 k3 第三次成功)
4. cc2-resume 在 NVCF 降期时空转 (setsid 失败→降级→timeout 840s→下轮再来), 应在 NVCF 严重降期时手动暂停
