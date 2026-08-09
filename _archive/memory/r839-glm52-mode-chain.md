---
name: r839-glm52-mode-chain
description: "R839 glm5_2_nv per-key-mode 动态递进链已部署 HM2; 2026-07-13 chain 改 integrate_us_rr 第一+删 pexec_direct; 源码 idx 越界自动回0"
metadata:
  node_type: memory
  type: project
  originSessionId: c3734594-fcf5-43ff-9b8d-e14d8c206a00
---

R839 (2026-07-11, HM2 已部署+全路径验证): glm5_2_nv per-key-mode 动态切换链.

**核心机制 (用户 Request 3+4, 动态递进非静态绑定):**
- "当前生效 mode" 是跨请求持久化的动态指针 (NOT per-key 静态绑定), 存 `LOG_DIR/glm52_mode_idx.json`, 初始 0=mode1 pexec_direct.
- 当前 key 用当前 mode 发请求.
- **故障 (429/timeout/empty200/连接错/5xx) → 换下一个 key + mode 递进到下一档** (mode_idx += 1, capped at len-1).
- **稳住 → 保持当前 mode (不递进), 下一个 key 继续用这个 mode**.
- mode 只往前递进不回退 (避免反复撞已知不稳的 mode).
- 全 key+全 mode 失败 → all_keys_exhausted → 落 R838b/R572/pexec `_try_tier_keys` 兜底 (现全 key pexec 直连).
- 后端整体恢复后由定时测速脚本 [[glm52-speedtest-cron]] (每天 02:00/14:00) 重排 `NV_GLM52_MODE_CHAIN` 顺序实现"软重置".

**5 模式 (递进序):** pexec_direct → pexec_us_rr → integrate_us_rr → pexec_us_single → integrate_us_single.
- channel (pexec/integrate) × ip_strategy (direct/rr_us/single_us).
- single_us 用 `NV_GLM52_SINGLE_US_PROXY=socks5h://172.18.0.1:7894` (7894→193 两机共有 IP).
- rr_us 用 `NV_GLM52_RR_US_PROXIES` (5 美国代理, fallback `NV_INTEGRATE_PROXY_URLS`).

**2026-07-13 chain 调整 (HM2 已生效):** 测速实证 integrate 最快最稳, pexec_direct 0/5 全死. 用户指令删 pexec_direct + integrate_us_rr 提第一.
- 新 chain: `NV_GLM52_MODE_CHAIN=integrate_us_rr,pexec_us_rr,pexec_us_single,integrate_us_single` (4 模式, 删 pexec_direct).
- compose: `/opt/cc-infra/docker-compose.yml` line 65. 备份 `docker-compose.yml.bak.pre-chain-fix.*`.
- recreate 时旧进程 stop 会把内存 idx flush 回旧值(=4), 新 chain len=4 → idx=4 越界.
- **源码越界保护 (upstream.py:1225-1226)**: `if mode_idx >= len(modes): mode_idx = 0`. 运行时自动回 0, 不 crash. 第一个请求从 idx=0 (integrate_us_rr) 起步, 成功后 save idx=0.
- 实测: recreate 后 idx 文件=4, 但首请求日志 `start_mode_idx=0 (=integrate_us_rr)` + SUCCESS, 测后 idx=0. ✓
- `glm52_reset_mode_idx()` 因 circular import (config↔glm52_mode_idx) 无法从 CLI 直调; 靠运行时越界保护或手写 idx 文件+不发请求直到 recreate 完成.

**HM2 改动文件:**
- `gateway/glm52_mode_idx.py` (新): 持久化 state machine (glm52_current_mode_idx/glm52_save_mode_idx/glm52_reset_mode_idx), mirrors rr_counter.py.
- `gateway/config.py`: `NV_GLM52_MODE_CHAIN` 解析器 `_parse_glm52_mode_chain` + `NV_GLM52_SINGLE_US_PROXY`/`NV_GLM52_RR_US_PROXIES`/`NV_GLM52_MODE_IDX_FILE` + re-export glm52_*.
- `gateway/upstream.py`: 新增 `_glm52_resolve_proxy` + `_glm52_single_attempt` (单次 fixed key+mode attempt) + `_try_glm52_mode_chain` (动态递进主循环); execute_request 加 R839 分支 (在 R838b/R572 之前, 互斥: tier_model=="glm5_2_nv" + NV_GLM52_MODE_CHAIN 非空 + path 未冷却).
- `docker-compose.yml`: `NV_INTEGRATE_MODELS=` 清空 (glm5_2_nv 移交 R839, 不再走 R572 全 key integrate); 加 `NV_GLM52_MODE_CHAIN=pexec_direct,pexec_us_rr,integrate_us_rr,pexec_us_single,integrate_us_single` + `NV_GLM52_SINGLE_US_PROXY=socks5h://172.18.0.1:7894` + `NV_GLM52_RR_US_PROXIES=...5美国`.
- 备份: `.bak.preR839` (config/upstream/compose).

**验证 (HM2, 全路径):**
1. pexec_direct mode1 k3 → 200 4.2s, mode held (稳住→保持) ✓
2. 二次 req mode_idx=0 (held) k5 (RR) → 200 2.4s ✓
3. 持久化跨重启: SIGKILL+start 加载 idx=2 → start_mode_idx=2 integrate_us_rr k4 → 200 via 7894 ✓
4. mode_idx=3 pexec_us_single → 200 via 7894 (single_us 解析 OK) ✓
5. **故障递进注入** (single proxy→dead 9999, mode_idx=3): k3 pexec_us_single conn-refused → `NV-GLM52-MODE-ADVANCE mode 3→4` + k4 integrate_us_single fail → 4→4 cap 循环 5 key → `NV-GLM52-CHAIN-FAIL` → `NV-GLM52-CHAIN-FALLBACK` → pexec 兜底 200 ✓
6. 恢复 mode_idx=0 + 单代理 7894 → production healthy 3/3 200.

**DB:** 成功 attempt 也写入 key_cycle_details (含 mode/channel/proxy), 可 `key_cycle_details->0->>'mode'` 查询. metrics 新增 `glm52_mode` (DB 无独立列, 落 key_cycle_details).

**待做:**
- HM1 同步 R839 (config+upstream+compose+glm52_mode_idx.py). 铁律: HM2 稳定后改 HM1. 两机 mode 定义+单 IP (7894→193) 一致; mihomo 端口→IP 映射可不同但 7894 两机都→193.
- HM1 同步 speedtest 脚本+cron ([[glm52-speedtest-cron]] 待做 HM1).

**回滚:** 删 `NV_GLM52_MODE_CHAIN` env + force-recreate → 回 R827/R572 全 key integrate (glm5_2_nv 加回 NV_INTEGRATE_MODELS). 备份 `.bak.preR839`.

相关: [[glm52-speedtest-cron]]
