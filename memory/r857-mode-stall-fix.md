---
name: r857-mode-stall-fix
description: R857 修 mode_idx 卡死(advance停滞reset0) + cc4101死env清理 + integrate 429冷却改回90s
metadata: 
  node_type: memory
  type: project
  originSessionId: 3c8d8f5f-50f9-4f31-9c0c-b1eae74a0183
---

# R857 修复(2026-07-15 01:13, 远程HM2 nv_gw/cc4101)

三处 bug 一起修, 故障注入验证 BUG1 真触发。

## BUG1: mode_idx 卡死在 3 → advance 停滞 reset 到 0 (upstream.py)
- 文件: /opt/cc-infra/proxy/nv-gw/gateway/upstream.py ~1280行 (`_try_glm52_mode_chain` 的 advance 处)
- 根因: `new_mode_idx = min(mode_idx+1, len(modes)-1)`, idx 到末尾(3)后 min(4,3)=3, advance 3→3 死循环. 24h 实测 43 次 3→3, start_mode_idx=3 出现 109 次. idx=3=integrate_us_single 固定 7894 单 IP, 坏时反复撞, 只有全5key+全mode在同请求失败才触发 R844 reset 逃逸阀.
- 修法: advance 赋值后 `if new_mode_idx == mode_idx:` (停滞) → `mode_idx=0; glm52_save_mode_idx(0); _log("NV-GLM52-MODE-STALL-RESET", ...)`. `else: mode_idx=new_mode_idx`. 循环上限仍 NVU_NUM_KEYS+2=7 有界. R844 全失败逃逸阀(1289行)保留.
- **故障注入验证成功**: 临时把 NV_GLM52_SINGLE_US_PROXY 改 59999 不通端口 + restart, 跑 glm5_2_nv: mode3 k3 via 59999 → 立即 fault → 日志先打 `MODE-ADVANCE mode 3→3`, **紧接着触发 `NV-GLM52-MODE-STALL-RESET ... reset mode_idx to 0 (=integrate_us_rr)`** → 下次 attempt 用 mode0(integrate_us_rr via 7895) 3.6s SUCCESS. mode_idx.json 从 {"idx":3} 变 {"idx":0}. 验证后改回 7894.
- 备份: upstream.py.preR857. 回退: `cp upstream.py.preR857 upstream.py && docker restart nv_gw`.

## BUG2: cc4101 死 env 清理 (docker-compose.yml)
- 文件: /opt/cc-infra/docker-compose.yml cc4101 服务段 172-175行
- 根因: env 有 FALLBACK_UPSTREAM_URL/TOKEN/MODE=glm5_2_ms, 但 cc4101 config.py R851 删干净不引用. 死配置误导排查(看env以为有fallback).
- 修法: 三行整行注释 `    # - FALLBACK_UPSTREAM_...` + 加 `# R857: cc4101 已删 fallback(R851/R854), 此3行死配置代码不读, 注释保留历史避免误导排查`. 不删留回退.
- 验证: `docker exec cc4101 env | grep -c FALLBACK_UPSTREAM` = 0.

## BUG3: NV_INTEGRATE_KEY_COOLDOWN_S 0→90 (docker-compose.yml)
- 文件: /opt/cc-infra/docker-compose.yml nv_gw 段 56行
- 根因: env=0, config 默认 90. 0 → integrate 429 限流的 key 不冷却立即重试, 加速撞限流.
- 修法: `NV_INTEGRATE_KEY_COOLDOWN_S=90`.
- 验证: `docker exec nv_gw env | grep NV_INTEGRATE_KEY_COOLDOWN` = 90.

## 执行
- 备份 upstream.py + docker-compose.yml (.preR857).
- 改 upstream.py(BUG1, 容器内 py_compile 语法 OK).
- 改 docker-compose.yml(BUG2+BUG3, yaml.safe_load 校验 OK).
- `cd /opt/cc-infra && docker compose up -d --force-recreate nv_gw cc4101`.
- 最终回归: ���实CC模拟(via cc4101 stream+system) 5/5 OK (2.5-10.4s), 0 fail.

## 未修的(留观察)
- BUG4: NV_KEY_INTEGRATE_PROXY_URLS 只1个(7897单口, dsv4p_nv k5 per-key无IP多样性) — 未动, 影响dsv4p_nv非glm5_2_nv.
- BUG5: NV_INTEGRATE_MODELS=空(env覆盖, dsv4p_nv改走R838B per-key) — 可能有意, 未动.
- cc4101 无 fallback(R854设计) — CC链路比飞书链路(opclaw4103有ms_gw fallback)脆弱, 但有意决策.

相关 [[hm2-cc-chain-framework-r856]] [[r839-glm52-mode-chain]] [[glm52-stability-deeptest-r843]] [[r844-opclaw4103-fallback-timeout-fix]]
