# R1154 — cc2 NOP 巡检 (瞬时 egress 复发第 2 burst, 自愈; NOP 不改码)

**日期**: 2026-08-08 (session 02:41 CST = 18:41 UTC)
**容器**: nv_gw `28 hours ago` / cc4101 `23 hours ago` 未重启
**主链 fid**: 281478d0-f307 稳定 (全 5 key pexec, 对 dsv4f0731_nv)

## 结论一句话
最新 5min **100% SR (12/12)**, 30min 整窗 cc4101-primary **97.9% SR (93/95)**;
2× 502 `buffer_exhausted` (18:34/18:36 UTC) 为**瞬时 egress 复发第 2 burst**, 隔 32min 自愈,
NOP 不改码, 属已知 transient-egress 模式非持续劣化。

## 本轮数据 (实查 + 注入)

### 30min cc4101-primary (注入 + 实查核)
- `200|93`, `502|2` → **SR=97.9%, 2× buffer_exhausted** (avg_dur ~34.8s, 各烧 ~31/39s)
- fallback: `f|200` + DB `fallback_actually_attempted=f` → **ms_gw 未走 (502 直返 SDK)**

### 30min 全链 (注入)
- dsv4f0731_nv SR **100%** (198/198, 含 hermes 线)
- tier: 全 5 key `pexec_success`, 仅 1× `NVCFPexecTimeout` (k3, 瞬时); **429=0, empty=0**
- buffer/wait 日志: (注入显示无) — 但 nv_gw 日志 40m 实测见下

### 60min nv_gw 日志深挖 (关键, 注入未覆盖)
`--since 60m` grep NV-BUFFER-EXHAUSTED 计 **8 次**, 分 **2 个孤立 burst**:
- **Burst 1 (17:47–18:02 UTC)**: 6× 502 — 即 **R1148/49 已知风暴带** (上几轮已闭环)
  - acdcf33a/82ee78ae/ab59c732/c262f96c/abe467e0/9731043f
- **Burst 2 (18:34–18:36 UTC)**: 2× 502 — **新发第 2 burst** (3a582e6c, 25c3a92b)
- 两 burst 均 `all_keys_exhausted`, 3 连续后 fail-fast, `trying ms_gw fallback` 亦返回非 200

### 90min per-min 趋势 (实查, 决定性)
- 17:13–17:45 (32min): **全 200** (~120 reqs 干净)
- 17:47–18:02: 6× 502 (风暴带)
- 18:03–18:33 (30min): **全 200** 干净
- 18:34, 18:36: 2× 502 (新 burst)
- 18:37–18:41 (now): **全 200** 干净 (最新 5min 12/12)

## 根因判断
2 个失败请求都是**超大请求 (input 80973/71105 chars ≈ 50-60K+ tokens)**, 10s 内全 5 key
`execute_failed`, 3 连败触发 fail-fast 短窗 (~35s)。两 burst 互为孤立、中间 30min 全干净、
当前 5min 全干净 → **与记忆 `ssleof-error-transient-egress-blip` (transient SSLEOFError 多 key
egress 抖动, NOP 自愈) 一致**, 非配置漂移。第 2 burst 是风暴过境后同源 egress 涟漪的再次闪现,
非持续劣化。

## 本轮改动: 无 (NOP)
不符改码触发条件 (无持续劣化, 最新 5min 100%, tier 无 429/empty, 无新错误类型,
buffer 当前全 attempt-1 direct flush 干净)。持续观察, 不因 2 点瞬时事件动码。

## 验证
最新 5min 12/12 = 100% SR; 容器 3 个 `/health` 全 ok; tier 无 429/empty;
buffer 当前日志全 `flush 1 attempt(s) success`。

## 下一步
维持静稳观察。**重点监控**: burst 2 是否只是单次复发。
若 **下一窗口 (30min) 内再次出现 ≥2× buffer_exhausted 或复现 3 burst/复发间隔 <30min**,
则按记忆指向深挖 mihomo 线路 (7900-7904, dsv4f0731_nv 5 US egress), 或考虑超大请求
(>70K chars) 的 buffer 首跳韧性。