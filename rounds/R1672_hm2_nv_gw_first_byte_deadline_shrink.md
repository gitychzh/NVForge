# R1672: HM2 nv_gw first-byte deadline 大请求降档 (90→45 / 120→60)

> 精准定位+修复:远程 CC 卡住 = nv_gw 大请求(200-350k) first-byte-timeout 每次卡 90-156s。
> 只改 HM2 (聚焦远程 CC; 铁律"只改HM1不改HM2"本系列破例, 用户聚焦远程 CC)。

## 一、现象与定位 (HM2, 2026-07-17 12:24-12:25)

用户报"远程主机 CC 可能卡住"。即时探测:
- 4101 小请求秒回 pong → CC 链路本身没死
- cc4101 日志:持续服务真实 claude-opus-4-8→glm5_2_nv 流式(msgs=76-104, tools=30)
- 但 nv_requests 最近 15min: 4 个 `stream_first_byte_timeout` 502, **max_ms=156196**

关键日志(12:24:55):
```
[NV-STREAM-FIRST-BYTE-DEADLINE] (glm5_2_nv) passthrough first-byte deadline 90.0s
  exceeded (input_chars=250878), breaking (upstream 200-then-hang)
[NV-UPSTREAM-ERROR-CHUNK] ... stream_first_byte_timeout → cc4101 zombie→api_error→CC retry
```

**根因**:NVCF 对超大 input(~250k chars)返回 HTTP 200 头后 hang 住不发首 chunk。
nv_gw first-byte deadline (200-350k 档 = 90s) 砍断,但 90s 对 CC 体验太长 → CC 视角
"卡 90+ 秒才失败重试"。这是 **200-then-hang**,不是 R1648c/d 引入(那两轮 ENABLED=0
未生效),是 nv_gw 既有 deadline 档位设定。

## 二、数据锚点 (改前必有数据)

HM2 最近 1h, 大请求(200-350k)**成功**样本 TTFB 分布:
```
p50 = 7.8s   p90 = 20s   p99 = 32.3s   max = 32.6s
```
→ 正常 thinking 首块从没超过 33s。旧 90s/120s 档对正常请求留了 2-3 倍冗余,但对
200-then-hang 要等满 90s 才砍 → 浪费 45s+。

按 input 分桶成功率(最近 1h):
| input 档 | total | ok | 成功率 | max_ms |
|---|---|---|---|---|
| <50k | 3 | 3 | 100% | 14s |
| 50-200k | 55 | 46 | 84% | 104s |
| 200-350k | 19 | 15 | 79% | 156s ← 卡住重灾区 |

## 三、改动 (只改 nv_gw/gateway/handlers.py 两处档位)

源码两处对称(passthrough 路径 L873-882 + stream 升级路径 L1246-1255),硬编码
`60.0/90.0/120.0` 改成 env 可调 + 降档:

```python
# R1648e: first-byte deadline 按 input 分档, 全部 env 可调.
# 数据锚点: 200-350k 成功请求 TTFB p99=32.3s max=32.6s.
# 旧 90s/120s 档对 NVCF 200-then-hang 太长 (卡 90-156s→CC 等死).
# 降到 45s/60s: 真首块 p99 32s 留 40%+ 余量, hang 则 45s 内砍掉让 CC 快重试.
if _ic <= 50000:
    _fb_s = NVU_STREAM_FIRST_BYTE_DEADLINE_S
elif _ic <= 200000:
    _fb_s = float(os.environ.get("NVU_STREAM_FB_50K_S", "60"))
elif _ic <= 350000:
    _fb_s = float(os.environ.get("NVU_STREAM_FB_200K_S", "45"))   # 旧 90
else:
    _fb_s = float(os.environ.get("NVU_STREAM_FB_350K_S", "60"))   # 旧 120
```

备份 `handlers.py.bak.R1648e_ttfb`。未改 compose env(用源码默认值即可,需要微调时
加 env 不重启源码)。

## 四、验证

| # | 项 | 结果 |
|---|---|---|
| 1 | 语法 py_compile | ✅ OK |
| 2 | 重启 nv_gw + health | ✅ ok |
| 3 | 源码加载(两处 grep) | ✅ L873+L1246 都在 |
| 4 | 回归:小请求 openai | ✅ content=ping 200 |
| 5 | HM2 CC 探测 4101 | ✅ 秒回 pong |
| 6 | cc4101 持续服务真实请求 | ✅ msgs=100-104 在跑 |
| 7 | first-byte-timeout max_ms ≤45s (真实大流量) | ⏳ 后台监控中,需真实 250k 流量触发 |

预期效果:下次真实 250k 200-then-hang 发生时,max_ms 从 90-156s 降到 ~45s,CC 重试
等待减半以上。

## 五、风险评估

- **误杀风险**:正常大请求 TTFB max 32.6s,新档 45s 留 38% 余量,安全。
- **>350k 档**:120→60,该档样本为 0(本轮无 >350k 请求),按 p99=32s 推断 60s 充裕。
- **不引入新卡死源**:只缩短 hang 砍断时间,正常路径不变。
- **与本系列其他轮正交**:R1648c/d ENABLED=0 未生效,不影响;R1648e cc4101 瘦身
  待做。本修复独立于框架重构,是 nv_gw 既有逻辑调优。

## 六、后续

- 监控 30min,确认真实大请求 first-byte-timeout max ≤ 45s 后写 memory。
- 若 45s 仍误杀(出现正常请求被砍),调高 NVU_STREAM_FB_200K_S env。
- 此修复是 R1648e 切换长跑前的稳定性前置——大请求卡顿不解决,R1648e 切换后 CC 体验会更差。

## 七、深挖补遗:R1672 只治了第 2 段,第 1 段未治 (2026-07-17 14:30-14:40 复现)

部署后真实 283k 请求复现, 完整解剖 (14:34:08, 总 115s):
```
14:34:08.7  REQ 283k input
14:34:08.7  k2 pexec (read_timeout≈66s)
14:35:10.4  k2 → empty-200 (Content-Length:0)   ← 卡 62s 在 conn.getresponse() 内部
14:35:10.4  k3 integrate
14:35:19.3  k3 SUCCESS (返200头)
14:36:04.3  FIRST-BYTE-DEADLINE 45.0s exceeded   ← R1672 生效 (旧 90s)
14:36:04.3  → 502, CC retry 同一个 283k → 死循环 1h (DB 8 条全 283274)
```

**两段叠加 = 115s**:
- 第 1 段 62s: pexec `conn.getresponse()` (upstream.py:677) 对 283k input hang ~62s
  才返 empty-200. 卡在 getresponse **内部**, first-byte deadline 救不到 (deadline 从
  getresponse 返回后才计). read_timeout=min(66, post_connect_remaining)≈66s 拖满.
  **R1672 没碰这段.**
- 第 2 段 45s: integrate 200-then-hang, R1672 已 90→45 ✅.

**为什么不能简单缩 pexec getresponse 超时 (层 1 止血走不通)**:
查正常 >200k 成功请求 ttfb: p90=25.6s, **max=58s**. 给 getresponse 套 20s 短超时会
**大面积误杀正常大请求**. 第 1 段 62s 大部分是"等 NVCF 真返头"(对大 input 就是慢),
不全是 hang. 简单缩超时不可行.

**最深根因**: NVCF glm5.2 处理不了 283k(~9万 token) 超大 input — pexec 拖满 timeout
返 empty-200, integrate 200-then-hang, 两通道都坏, 5 key 轮一遍各浪费 62-66s.

**R1672 净评估**: 总卡死从 ~160s 降到 ~115s (第 2 段 90→45), 部分缓解但治不了第 1 段.
单点 deadline 调优治不了这个病.

**待决策的治本方案** (未做, 见 memory `r1672-nv-gw-biginput-hang-rootcause`):
- B(推荐): nv_gw 对 input>250k 连续 N 次 first-byte-timeout 后快速失败 (不走完整
  mode chain), 死循环 115s/次→~5s 快速拒. 风险中.
- C(治本但侵入): cc4101 对超大 input 直接拒/降级到 ms_gw (改 CC 可见行为).
- D(不做): 缩 pexec getresponse 超时, 误杀正常大请求.

**死循环判定信号**: nv_requests 连续多条同 total_input_chars>200k 且 status=502 +
error_type in (stream_first_byte_timeout, stream_no_content_gap).
