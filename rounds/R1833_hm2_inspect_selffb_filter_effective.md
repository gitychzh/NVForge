# R1833 (HM2 cc2): 巡检轮 — bug8 自反馈过滤生效确认 (restart 后纯净窗 0 命中); SR 95.0% 边缘稳

- **性质**: 巡检轮, **不改代码不 restart** (无 nv_gw config 可改依据, 硬改违反铁律)
- **依据**: STATE R1832 "下一轮该做什么" — 拉 30min 确认链路仍稳 + grep NV-TOOLCALL-JSON-BAD
  验证自反馈过滤是否生效 (预期 0)
- **本轮关键收获**: R1832 加的 SELF_FB_MARKERS 过滤**生效确认** — restart (04:26 UTC) 后纯净
  12min 窗内 bug8 命中 **0** (对比 restart 前的 1 条历史残留命中, 是 R1827 代码于 04:12 产生的,
  docker logs --since 30min 把它包进窗内造成"看似命中"假象)。

## 改前数据 (30min 窗, 当前 04:38 CST)
- **30min SR = 57/60 = 95.0%** (200:57, 502:3), 比 R1832 95.8% 略低 0.8pp, **仍在 95% 安全线
  边缘**, 非破线非恶化。
  - error 3 条: stream_first_byte_timeout 2 (设计内故障递进 peek path, 走 ms 重放用户拿内容)
    + stream_absolute_cap 1 (R1797 cap=150 留作 pexec 偶发真 hang 兜底, 设计内)。
  - tier: pexec_success 42 / pexec_empty_200 2 / IntegrateTimeout 1 / pexec_SSLEOFError 1
    (key 偶发早期断, 5 key 各 ≤1 非系统性) / pexec_timeout 1。无 all_tiers_exhausted 无
    content_filter。
  - **pexec elapsed 仍自愈**: max=43608ms (~44s) / avg=11848ms (~12s) / **≥60s 0 条**。
    分布 <5s 8 / 5-15s 23 / 15-30s 11 / 30-60s 1。对比 R1831 max 288s/avg 38s/6 条 ≥60s,
    NVCF pexec 首字节持续自愈状态, 非恶化。
- **fallback 30min = 5 SKIP-CIRCUIT** (注意时间戳分布): 04:07/04:15/04:18 (这 3 条在 R1832
  restart 04:26 之前, 历史残留) + 04:28/04:32 (restart 后真实窗内 2 条)。**restart 后纯净
  12min 窗内 fallback = 2**, 比 R1832 窗内 2 持平, bug3 仍低位抖动非恶化。全 FALLBACK-OK 0 中断。
  - 5 rid (7cdea1ae/51333269/b6e4a1e3/d6532fde/3265cc53) 在 nv_requests 全 **0 rows** =
    未到 nv_gw 写库 = cc4101 75s 抢断甩 ms, 是 cc4101 侧 bug3 非 nv_gw config 可控。
- **NV-ANTH-BREAKER-FAIL = 1 条** (req=f6ce4ccf): err=stream_absolute_cap 软挂记录, nv_breaker
  state=(CLOSED, 1, 0) 未 OPEN。这是 nv_breaker 设计内的"记录软挂但不 OPEN", 合法。非恶化。
- **bug8 观测层关键结论**:
  - `docker logs nv_gw --since 30min | grep -c NV-TOOLCALL-JSON-BAD` = 1, **但带时间戳查到命中
    是 2026-07-18T20:12:03Z = 04:12 CST, 在 R1832 restart (04:26 UTC) 之前 14 分钟**。
  - **restart 后纯净 12min 窗 (04:26 UTC+) grep = 0** → R1832 加的 SELF_FB_MARKERS 过滤
    **生效确认**: 自反馈不再 dump。那 1 条历史命中是 R1827 代码产生的, docker logs 滞留。
  - 命中内容仍是 rid=791d66bf (frag = STATE.md 全文, `{"content": "# cc2 自优化交接棒 STATE`
    前缀 + `# R18` marker 都满足过滤条件), 印证 R1832 过滤逻辑正确 (模拟测试 would_filter=True),
    md5 宿主/容器一致 9f27f4556 确认跑的是改后代码。**bug8 普通流量连续第 5 轮零真畸形**。

## 决策 (不改代码)
SR 95.0% 在线边但不破线 + pexec 自愈持续 + bug8 自反馈过滤生效 + fallback 低位 0 中断 +
nv_breaker 软挂 1 条未 OPEN + env 无漂移 → 链路稳, 无 nv_gw config 可改依据 (UPSTREAM_TIMEOUT=66
/ TIER_TIMEOUT_BUDGET_S=180 / NVU_TIER_BUDGET_GLM5_2_NV=120 均合理值)。硬改违反"改前必有数据,
改后必有验证"铁律 → 巡检轮不动。

## 验证 (无需 restart, 仅观测)
- /health ok (passthrough / 5 keys / pexec_models kimi_nv/dsv4p_nv/glm5_2_nv)。
- nv_gw StartedAt = 2026-07-18T20:26:21Z (R1832 restart 后, 本轮未再 restart)。
- docker ps: nv_gw Up, ms_gw Up 40h (热备未碰), cc4101 Up 13h。
- md5 宿主/容器一致 9f27f4556 (R1832 改动确认在位)。
- env 无漂移 (本轮未碰 compose env / 源码)。
- **0 中断** (本轮无 restart, 全程 cc4101→nv_gw 直连)。

## 下轮 (R1834) 该做什么
1. 读本 STATE (R1833 巡检确认 R1832 自反馈过滤生效, restart 后窗 0 命中)。
2. 拉 30min 数据继续确认链路稳 (SR ≥95% / fallback 低位 / pexec max <60s)。若 SR 持续 ≥95%
   + bug8 restart 后窗连续第 6 轮零真畸形 → bug8 进入"真安静期", 可按 R1831 STATE 第 5 条
   考虑降低观测层开销 (采样校验: 每 N 个请求校验 1 次 args JSON 而非每个都 json.loads), 但不急。
3. **重点验证**: `docker logs nv_gw --since <N>m | grep NV-TOOLCALL-JSON-BAD` 若有命中, 必须
   `docker logs nv_gw -t` 带时间戳确认是否在 R1832 restart (04:26 UTC) 之后 — 之后的命中才是
   R1832 过滤之后的真实漏网 (必是真畸形 → 按 STATE R1832 "下一轮第 3 条" 方案 C 设计降级);
   之前的命中是 R1827 历史残留 docker logs 滞留, 不算。
4. bug3 仍 cc4101 侧非 nv_gw 可控, 保持现状; 仅当 fallback 持续多轮窗内 ≥4 + pexec max 持续
   ≥200s 才算恶化。当前偶发非恶化。
5. commit+push R1834 + 覆写 STATE。
