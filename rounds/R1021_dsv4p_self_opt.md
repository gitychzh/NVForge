# R1021: RemoteDisconnected 风暴加剧 (SR 47%) — 远程瞬断继续主导, 无参数修改 (恢复观察轮)

> 时间: 2026-08-05 07:55 BJT (23:55 UTC)
> 容器: dsvf0731_nv40666 (端口 40666, HM2, DeepSeek V4 flash via NVCF)
> 状态: **恢复观察轮 (无参数修改)** — RemoteDisconnected 远程瞬断绑架 SR, 无本容器可解参数
> Fallback: hm4104 持续 fallback 到 dsv4f0731_ms (primary 502/超时触发)

## 1. 背景 (改前必有数据)

R1020 为恢复观察轮 (SR 82.8%, 529 风暴收敛)。本轮 30min 窗口显示残余
RemoteDisconnected 风暴**加剧**, SR 跌破 50%, 主导错误仍为 `NVCFPexecRemoteDisconnected`。

### 30min 窗口 (注入 context) — nv_requests
- 总量 17, 200=8, 502=9, **SR=47.0%** (R1020 同窗 82.8% → 显著下降)
- Avg/P50/P95: 65056ms / 66860ms / 142393ms
- fallback_occurred 高 (primary 502/超时触发)

### 30min tier_attempts 失败细分 (20 次 key 尝试)
- **NVCFPexecRemoteDisconnected: 17 (85%, 绝对主导)**
- 529_nv_overloaded: 1
- empty_200: 2
- all_tiers_exhausted: 0 (直接计数层)

### 容器日志交叉验证 (dle scog near 07:45-07:54)
- 每个 tier 尝试全部 5 key, **每一 key 均 SSLEOFError (UNEXPECTED_EOF_WHILE_READING, ~5s)**
  或 `Remote end closed connection without response` (35-45s per key)
- 出口分布: k1→7897, k2→7904, k3→7894, k4→7896, k5→7895 — **5 个不同 mihomo 出口全中招**
- 2 连续 conn error → fast-break (节省后续 key), 单 tier 烧 35-142s

## 2. 决策: 无参数修改 (恢复观察轮)

**依据:**
1. **主导错误 RemoteDisconnected 17/20 (85%)** — 远程段在 read-stage 直接断开连接
   (SSL EOF / Remote end closed), 5 个不同 mihomo 出口(k1-k5)全部均匀命中, 非单 key/单出口问题。
2. **远程瞬断非 timeout/cooldown/budget/fastbreak 可消除** — per_attempt_timeout 已按
   budget 精确分配, connect reserve 已生效, key 轮转已尽, CONN_ERR_FAST_BREAK=2 已省 budget。
3. **5 key 全中招 = 出口级/远程级, 非 proxy 配置问题** — 所有 5 个 HM2 mihomo 出口
   (7894/7895/7896/7897/7904) 均 SSLEOFError, 证实为 NVCF 上游或 mihomo 到 NVCF 链路瞬断。
4. **R1017 revert + R1018-R1020 连续确认已达参数优化极限** — 本容器可调参数在此错误模式下
   无用武之地, 无单一参数可将远程瞬断转化为成功。
5. **改前必有数据**: 无任何数据支持改动可提升 SR (错误为远程 VLESS 连接被 NVCF 侧 reset)。

## 3. 当前状态 (30min 主指标)

- 30min SR: **47.0%** (8/17), 较 R1020 82.8% 显著下降 (远程风暴加剧)
- Avg/P50/P95: 65056ms / 66860ms / 142393ms
- 错误: RemoteDisconnected=17/20 (85%), 529=1, empty_200=2
- 429: 0 (keymgr 429 cooldown 为残余衰减, 非本轮主导)
- upstream: pexec 17/200=8, integrate 0
- fallback: hm4104 持续 fallback 到 ms_gw (primary 502/超时触发)

## 4. 上次修改效果 (R1020 观察轮 / R1017 revert integrate lane)

- 529_nv_overloaded 保持低位 (1/20), 账户级风暴未复发
- integrate upstream 保持归零, 5-key pexec 池冗余完整
- 但 RemoteDisconnected 从 R1020 的 22/30min 升至本轮 17/20 (85%) — **远程瞬断成为新的主导**
- SR: 88.9% → 82.8% → 47.0% — 单调下降, 但全部由远程瞬断驱动, 非本容器参数劣化

## 5. 下一步建议

1. **若 RemoteDisconnected 持续高位 (>70%)**: 无本容器参数可解, 属 NVCF 上游/mihomo 出口到
   NVCF 的远程瞬断。评估是否需:
   - 额外的 NVCF egress IP 池 (HM2 当前 5 出口 134.195.101.197/193/195/180 全中招)
   - 或冗余 NVCF key / 备用 upstream provider
2. **若 hm4104 持续 fallback**: 主链路已不稳定, 容忍 fallback 到 dsv4f0731_ms 是当前最稳
   路径, 不建议强行回主。
3. **下一轮**: 若 SR≥95% 且 RemoteDisconnected 下降 → NOP; 若 RemoteDisconnected 仍主导
   (>70%) 且 SR<80% → 维持观察, 等待远程侧恢复; 若出现单 key 劣化 (非均匀分布) → 才考虑
   key 级参数调整。

## 验证清单
- [x] /health 未改动 (无参数修改, 无需重启)
- [x] 数据完整: 30min SR/延迟/错误分布/fallback 均已采集
- [x] 决策数据驱动: 17/20 RemoteDisconnected 均匀跨 5 key 5 出口 → 远程瞬断, NOP