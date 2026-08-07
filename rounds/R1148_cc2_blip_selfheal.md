# R1148 cc2 — transient DEGRADED-fid + all-key egress storm, self-healed (恢复期 NOP)

## 结论: 不改码 — 已自愈的瞬时 egress/DEGRADED 风暴, 非配置回归

本轮与 R1145-R1147 的静稳 NOP 不同: 30min 窗口内出现 **6 次 cc2-primary 失败 (502)**
(`all_tiers_exhausted` × 5 + `buffer_exhausted` × 1, avg_dur 219662ms), 主链 SR 由 R1147 的 100%
降至 **95.8% (113/118)**。但逐层拉日志确认这是**瞬时过境事件已自愈**, 非 nv_gw/cc4101 配置根因,
**无码可改**。当前最新 5min 已回落 100% SR = 0 错误 (16 行全 200)。

## 依据 (本 session 实查 2026-08-08)

### 表面 (30min nv_requests 实查)
- cc2-primary: 200|113, 502|6, avg_dur 219662ms。
- 错误分类: `all_tiers_exhausted` × 5 + `buffer_exhausted` × 1。6 个失败 request_id:
  acdcf33a(buffer_exhausted,130.9s) / 82ee78ae(93.7s) / c262f96c(340.5s) / abe467e0(308.6s) /
  ab59c732(259.0s) / 9731043f(185.3s) — 分散在 17:47-18:02 UTC (= 01:47-02:02 CST)。
- **per-min 分布**: 502 各 1 次于 17:47/17:49/17:54/17:58/18:01/18:02, 非单 burst, 是一段持续 ~15min 的降级带。

### Tier 层根因 (nv_gw 日志实查) — 关键
- **TRIGGER**: `[NV-NONCYCLE-ERR] 01:47:54 fid=281478d0-f307 resp.status=400 "DEGRADED function cannot be invoked"`
  → `[NV-TIER-DEGRADED]` 标记 DEGRADED cooldown 60s。NVCF 侧把 ds麒麟 dsv4f0731_nv 当前 fid **281478d0-f307**
  瞬时标为 DEGRADED (3 次 DEGRADED 事件)。
- **风暴**: `NV-KEYMGR transport_err type=RemoteDisconnected penalty=5s` 在 01:46→02:05 **横扫全部 5 key**
  (k1-k5, 对应 7901/7894/7897/7896/7899 5 个 egress 代理同时掉连), 另见 1 次 `SSLEOFError penalty=10s`。
  → 25 次 `[NV-GLM52-CHAIN-FAIL] all 5 keys + modes exhausted`。
- **`NV-TIER-FAIL` 全是 `429=0, empty200=0`** (01:51/01:55/01:58/02:00: other=2~4, timeout 至多 1)
  → **绝非 KeyManager 429/cooldown 瓶颈**, 是 egress 传输层瞬时失败 + DEGRADED fid 400。
  → 现有 KeyManager/cooldown/buffer 配置**不是根因**, 无参数可调。
- **fid 迁移注意**: 当前 pexec 实际走 **281478d0-f307** (87 次 pexec_success), 而 **52e1ddb6** (R1147 STATE 记的
  主 fid) 只剩 4× RemoteDisconnected + 1× 500_nv_error 尾误 — 主 fid 已切换到 281478d0-f307。

### 自愈确认 (nv_gw 日志 + DB 实查)
- 02:05 后 buffer 全 `[NV-BUFFER-VERDICT] attempt=1 success_tool_call → [NV-BUFFER-SUCCESS]` direct flush
  (5-13s/req), 无 exhaust/无 WAIT。b3abed35 在风暴峰值尝试 3 次后最终 attempt-3 成功 (93786ms, 1602b) 也证明
  buffer 自愈机制发挥。
- **最新 5min (实查): cc2-primary 200|16 = 0 非-200, 100% SR** — 降级带已完全过境。
- 容器: nv_gw:40006 ok, dsv4p_nv40066:40066 ok, 稳定未重启。

## 改动: 无 (NOP)

瞬时 egress/DEGRADED 风暴已自愈, 且 `429=0` 排除 key-cooldown 根因。此事件与
[[ssleof-error-transient-egress-blip]] (R1077 闭合) 同类 = 多 key egress 过境抖动 + 单字瞬时 fid DEGRADED
标记, 非配置漂移。改码会让健康链去对冲一个已过境瞬时, 得不偿失。

## 数据 (相对上轮 R1147)

| 指标 | R1147 | R1148 (30min) | 判断 |
|---|---|---|---|
| cc2 主链 SR | 100% (124/124) | 95.8% (113/118) | 过境降级 |
| surface 错误 | 空 | all_tiers_exhausted 5 + buffer_exhausted 1 | 风暴带 |
| 最新 5min SR | — | **100% (16/16), 0 错** | ✅ 已自愈 |
| fallback | 0% | f\|119 (未走 ms) | ✅ |
| tier 主错误 | RD 6× + 500/empty | RD 横扫全 key + SSLEOF + DEGRADED | 过境 |
| buffer | 全 attempt-1 | 风暴期 attempt-2/3 自愈, 过后全 attempt-1 | 自愈生效 |

## 下一步

- **NOP 巡检轮收尾**。本轮不追加改码; 已记录为一次自愈的瞬时 DEGRADED+egress 风暴。
- **触发更码信号 (仅当复发且未自愈)**:
  (1) 同样 6×/30min all_tiers_exhausted **连续两轮**出现且非单窗口 → 查 mihomo 7901/7894/7897/7896/7899
  线路质量;
  (2) `DEGRADED function cannot be invoked` 对 281478d0-f307 **持续复发** (fid 侧问题, 若固发考虑切回
  b1b22d03/换 fid, 需先拉 per-key fid 分布铁证);
  (3) 风暴期内若 buffer 无法 attempt 内自愈 (净 502 持续) → 才考虑 k0-k4 多 fid 冗余绑定。
- 注: cc4101 FALLBACK_UPSTREAM_URL 仍指 ms_gw:40007 (历史残留), 但 fallback=0% 从未走, 铁律 4 不主动改。