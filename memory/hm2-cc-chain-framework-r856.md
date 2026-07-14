---
name: hm2-cc-chain-framework-r856
description: 远程HM2 CC链路完整框架(cc4101/opclaw4103→nv_gw/ms_gw) + 已挖BUG清单(mode_idx卡死/死env/cooldown=0)
metadata: 
  node_type: memory
  type: project
  originSessionId: 3c8d8f5f-50f9-4f31-9c0c-b1eae74a0183
---

# HM2 CC 链路框架(R856, 2026-07-15 核实)

## 链路全景
```
Claude Code(CLI)  ──→ cc4101(4101)     ──→ nv_gw(40006) ──→ NVCF(glm5_2_nv/z-ai/glm-5.2)
                          │(无fallback,R854删)        ├─ pexec: NVU_PROXY_URL1-5 全空=容器直连
                          │                            └─ integrate: NV_INTEGRATE_PROXY_URLS=7894-7899(mihomo美国)
openclaw(飞书)   ──→ opclaw4103(4103)  ──→ nv_gw(40006) [PRIMARY]
                          │  + fallback ──→ ms_gw(40007) [FALLBACK=glm5_2_ms, ModelScope]
                          └ FALLBACK_ENABLED=1, R842c content_filter切fallback
```

## 两套入口的差异(关键设计)
| | cc4101(4101, CC链路) | opclaw4103(4103, 飞书链路) |
|---|---|---|
| primary | nv_gw glm5_2_nv | nv_gw glm5_2_nv |
| fallback | **无**(R851删,R854确认) | **有** ms_gw glm5_2_ms |
| circuit | 有(5次OPEN→fast-fail 503) | 有(三态+R842c content_filter) |
| 含义 | nv_gw全挂=CC裸奔报错 | nv_gw挂→自动切ms_gw ModelScope兜底 |
本机HM1不受影响(走legacy_cc_1→legacy_ms_litellm纯ModelScope,不经nv_gw/integrate)。

## nv_gw 内部机制(5 key + 双通道 + mode chain)
- **5 NV key**(NVU_KEY1-5), 同tenant同function(3b9748d8 glm5_2).
- **双通道**:
  - pexec: NVU_PROXY_URL1-5 全空=容器宿主直连(无mihomo).
  - integrate: 走 NV_INTEGRATE_PROXY_URLS=socks5h://172.18.0.1:7894,7895,7896,7897,7899 (5美国mihomo口).
- **dsv4p_nv**: 用 R838B per-key 机制(NV_KEY_INTEGRATE_KEYS=dsv4p_nv:5 → key idx=4即k5走integrate,k1-4走pexec). RR正常轮转(测:k1-4各8-11次,k5单独integrate).
- **glm5_2_nv**: 用 R839 mode chain(NV_GLM52_MODE_CHAIN=integrate_us_rr,pexec_us_rr,pexec_us_single,integrate_us_single). 4 mode. idx持久化在 /app/logs/glm52_mode_idx.json.

## ⭐ 已挖 BUG 清单

### BUG1: mode_idx 卡死在 3(integrate_us_single 单IP 7894) — 真 bug, 放大器
- 24h实测: start_mode_idx=3 出现 **109次**(vs idx=0 只47次); mode **3→3 出现43次**(advance卡死因 min(3+1,3)=3).
- 危害: idx=3=integrate_us_single=固定走7894单IP. 7894坏时每请求先撞坏IP,因advance 3→3不前进,要全5key+全mode在同请求失败才reset(R844逃逸阀). 24h CHAIN-FAIL=6/RESET=6(3.75%全失败率).
- 根因: "mode只往前递进不回退"设计 + 成功时save保持当前idx → 一旦advance到末尾就永久卡,部分失败不reset.
- speedtest cron(2:00/14:00)推荐integrate_us_single第一(小请求5次3.56s最快),但那是瞬时测速不代表长请求稳定;且cron不自动改env,需手动.

### BUG2: cc4101 死env 残留(清理bug)
- env仍有 FALLBACK_UPSTREAM_MODEL=glm5_2_ms / FALLBACK_UPSTREAM_URL=ms_gw:40007 / FALLBACK_UPSTREAM_TOKEN.
- 但 config.py 完全不引用FALLBACK_UPSTREAM_*(R851删干净). 死配置,不影响功能,但误导排查(看env以为有fallback).

### BUG3: NV_INTEGRATE_KEY_COOLDOWN_S=0(env覆盖) — 429不冷却
- config默认90s, env设0 → integrate 429的key不冷却,限流key立即重试. 可能加速撞限流.

### BUG4: NV_KEY_INTEGRATE_PROXY_URLS 只配1个
- =socks5h://172.18.0.1:7897 单口. dsv4p_nv的k5 per-key integrate全挤7897单端口(egress 134.195.101.193单IP), 无IP多样性.

### BUG5: NV_INTEGRATE_MODELS=空(env覆盖)
- config默认"dsv4p_nv", env设空→ NV_INTEGRATE_MODELS=[""]. dsv4p_nv不在此列表→不走R572全key integrate. 实测dsv4p_nv走的是R838B per-key(k5单key). 可能是有意(改用per-key)但env覆盖成空属配置漂移, 与config默认意图冲突.

### 非BUG(已排除的误判)
- "RR peek永远k5"不是bug: R838B-LANE日志只在peek命中k5(idx=4 in [4])时才打,peek=k1-4走pexec不打此日志. counter正常轮转(已验证key分布均匀).
- integrate对glm5.2 chat地理限制(日本超时)是NVCF行为非bug,见[[glm52-integrate-geo-restriction-confirmed]].

相关 [[glm52-integrate-geo-restriction-confirmed]] [[r854-disable-thinking-injection]] [[cc-chain-layout-hm2]] [[r839-glm52-mode-chain]] [[glm52-stability-deeptest-r843]]
