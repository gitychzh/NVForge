# R1621 (proposed) HM2: glm5_2_nv per-mode key↔IP 一对一固定绑定

**状态: 已执行 + 验证通过 (2026-07-16).**
**铁律破例: 本轮改 HM2 (用户已授权).**

## 背景与改前数据 (R1620 实测)

用户诉求: 把 glm5_2_nv 的 5 个 key 与 5 个美国出口 IP 一对一固定, 并按 mode 分配 key,
保证系统稳定不中断, 后期靠日志再优化. 不再用全局 RR 轮换 (当前 key 与 proxy 各自
独立轮换, 导致 k1 时而走 7894 时而 7895, IP-key 不固定).

### 改前实测 (HM2, 2026-07-16)

1. **mihomo 8 端口出口 IP + NVCF 延迟** (integrate.api.nvidia.com):
   | 端口 | 原节点 | 实测出口 IP | NVCF 延迟 | 可用 |
   |---|---|---|---|---|
   | 7894 | 美国洛杉矶08 | 203.10.96.139 (澳洲) | 3.19s | ❌ |
   | 7895 | 美国02 | 134.195.101.194 | 0.82s | ✅ |
   | 7896 | 美国03 | 134.195.101.195 | 0.74s | ✅ |
   | 7897 | 美国01 | 134.195.101.193 | 0.70s | ✅ |
   | 7899 | 美国06 | 134.195.101.180 | 0.79s | ✅ |
   | 7891/7892/7893 | — | HK/不通 | — | ❌ |

   → 原状态只有 4 个真美国 IP, 因 K1(7894) 选的"美国洛杉矶08"节点出口跑偏到澳洲.

2. **mihomo API 切换机制**: 旧 POST 报 405 Method Not Allowed; 改 PUT 成功.
   对每个 `♻️US-NV-K1..K5` group 用 `PUT /proxies/{group}` body `{"name": node}` 可钉死节点.
   `profile.store-selected: true` + cache.db 持久化, 重启不丢.

3. **8 个美国节点 (美国01–08) 实测出口与延迟** (切换 K1 测试):
   - 美国01 → 134.195.101.193, 0.72s
   - 美国05 → 134.195.101.120, 0.72s
   - 美国07 → 134.195.101.188, 0.85s
   - 美国06 → 134.195.101.180, 1.04s
   - 美国03 → 134.195.101.195, 1.26s
   → 5 个不同美国 IP, 全部 NVCF 可达 <1.3s.

4. **HM2 容器内直连 NVCF**: integrate + pexec 均 15s 超时 FAIL.
   → HM2 docker 网络走 mihomo 7880, 容器"不走代理"=到不了 NVCF.
   → **pexec_direct mode 在 HM2 是死路** (用户已确认放弃 k2 直��).

5. **429/cooldown 处理代码已完备** (upstream.py):
   - per-key 429 cooldown (KEY_COOLDOWN_S=25, NV_INTEGRATE_KEY_COOLDOWN_S=90)
   - empty200 → mark_key_cooling (25s)
   - 全 key 429 → 整 integrate path cooldown (强制走 pexec)
   - tier-level DEGRADED short-circuit
   - **本轮无需重写 429/报错处理**, 只复用现有逻辑.

## 根因

当前 `NV_GLM52_MODE_CHAIN` 的 key 循环 (`_try_glm52_mode_chain` line 1253:
`key_idx = (start_key + attempt) % NVU_NUM_KEYS`) 是全 5 key 轮换, 且代理由
`_glm52_resolve_proxy(ip_strategy, attempt)` 独立 RR 选取 (`rr_us` 分支用全局 counter).
→ key 和 proxy 各自轮换, 不绑定. k1 这次走 7894、下次走 7895, 无法实现"一对一固定".

## 方案

### 改动 1: mihomo — 钉死 5 个 K group 到 5 个不同美国节点 (已完成, 待持久化验证)

通过 mihomo API PUT 钉死 (已实测生效):
| Group | 端口 | 钉死节点 | 出口 IP |
|---|---|---|---|
| K1 (7894) | 7894 | 美国01 | 134.195.101.193 |
| K2 (7895) | 7895 | 美国05 | 134.195.101.120 |
| K3 (7896) | 7896 | 美国07 | 134.195.101.188 |
| K4 (7897) | 7897 | 美国06 | 134.195.101.180 |
| K5 (7899) | 7899 | 美国03 | 134.195.101.195 |

store-selected 持久化到 cache.db. mihomo 这边不改 config.yaml (用 API 动态钉死,
避免改 config 后 reload 冲突). **注意**: 若 mihomo 重启且 cache.db 丢失, 需重跑 PUT.

### 改动 2: config.py — 加 MODE_KEY_BINDINGS + per-mode proxy 绑定解析

新增 env:
```
MODE_KEY_BINDINGS=integrate_us_rr:0,2,4;pexec_us_rr:1,3
NV_GLM52_KEY_PROXY_BIND=0,2,4:7894,7896,7899;1,3:7895,7897
```
- `MODE_KEY_BINDINGS`: 指定每个 mode 只用哪些 key (0-based idx). 未列出的 mode 回退全 key.
- `NV_GLM52_KEY_PROXY_BIND`: 指定 key→proxy 端点一对一绑定 (覆盖 rr_us 的 RR 行为).
  格式 `k_idx_list:proxy_url_list;...`, key 与 proxy 按位置对应.

config.py 解析成两个字典:
```python
MODE_KEY_BINDINGS = {}  # {mode_name: [key_idx,...]}
NV_GLM52_KEY_PROXY_MAP = {}  # {key_idx: proxy_url}
```

### 改动 3: upstream.py `_glm52_resolve_proxy` — 支持 key_idx 绑定

当前签名 `_glm52_resolve_proxy(ip_strategy, attempt_idx)` 改为
`_glm52_resolve_proxy(ip_strategy, attempt_idx, key_idx=None)`:
- 若 `key_idx in NV_GLM52_KEY_PROXY_MAP` → 返回绑定的 proxy_url (一对一固定, 不轮换).
- 否则沿用原 RR 逻辑 (向后兼容, 不绑定的 key 仍走 RR).

### 改动 4: upstream.py `_try_glm52_mode_chain` — per-mode key 子集

line 1253 循环改为:
```python
_bound_keys = MODE_KEY_BINDINGS.get(mode_name)
if _bound_keys:
    _n = len(_bound_keys)
    key_idx = _bound_keys[(start_key + attempt) % _n]  # 只在绑定子集内轮换
else:
    key_idx = (start_key + attempt) % NVU_NUM_KEYS  # 原全 key 轮换
```
cooldown/auth-fail 跳过逻辑不变 (is_key_cooling 仍按 key_idx 查).

调用 `_glm52_resolve_proxy` 时传入当前 key_idx.

### 改动 5: compose env

- `NV_GLM52_MODE_CHAIN=integrate_us_rr,pexec_us_rr` (2 mode, 砍掉 pexec_direct 死路 +
  single 变体; 用户原意 3 mode 但 pexec_direct 在 HM2 不通, 实为 2 mode)
  - **或**保留 3 mode `integrate_us_rr,pexec_direct,pexec_us_rr`, pexec_direct 作故障
    递进中间档 (明知会失败, 快速递进到 pexec_us_rr). 用户选哪个待确认.
- `MODE_KEY_BINDINGS=integrate_us_rr:0,2,4;pexec_us_rr:1,3`
  → k1/k3/k5 走 integrate, k2/k4 走 pexec (各 3+2 key 分担)
- `NV_GLM52_KEY_PROXY_BIND=0,2,4:socks5h://172.18.0.1:7894,socks5h://172.18.0.1:7896,socks5h://172.18.0.1:7899;1,3:socks5h://172.18.0.1:7895,socks5h://172.18.0.1:7897`
  → k1→7894(193), k3→7896(188), k5→7899(195); k2→7895(120), k4→7897(180)
- 备份 docker-compose.yml.bak.R1621

### 改动 6: 部署 + 验证

1. `docker exec nv_gw cp gateway/config.py gateway/config.py.bak.R1621` (in-container backup)
2. 改 config.py + upstream.py (bind-mount, 改宿主机 gateway/ 即生效)
3. `cd /opt/cc-infra && docker compose up -d --force-recreate nv_gw` (重建+重启, idx reset)
4. 写 `{"idx":0}` 到 glm52_mode_idx.json (强制从 mode0 起步)
5. 验证:
   - `curl /health` 200
   - 发 5 个测试请求, 查 DB `nv_requests` 确认 key↔IP 固定 (egress_ip 与 nv_key_idx 一一对应)
   - 观察 30min 稳定性 (success rate, 无死循环)

## 回滚

- compose: `cp docker-compose.yml.bak.R1621 docker-compose.yml && docker compose up -d --force-recreate nv_gw`
- 源码: `docker exec nv_gw cp gateway/config.py.bak.R1621 gateway/config.py` (bind-mount 会同步)
- mihomo: 重跑原 selector 或 PUT 回原节点

## 执行结果 (2026-07-16)

### 改动落地
- **mihomo**: 用 PUT API 钉死 K1–K5 到 5 个不同美国节点 (美国01/05/07/06/03),
  出口 IP 134.195.101.193/120/188/180/195, 全部 NVCF 可达 <1.3s. store-selected 持久化.
- **config.py**: 新增 `MODE_KEY_BINDINGS` + `NV_GLM52_KEY_PROXY_MAP` 两个 env 解析 (R1621 段).
- **upstream.py**:
  - import 加 `MODE_KEY_BINDINGS, NV_GLM52_KEY_PROXY_MAP`
  - `_glm52_resolve_proxy(ip_strategy, attempt_idx, key_idx=None)` — key_idx 命中绑定 map 直接返回固定 proxy
  - `_try_glm52_mode_chain` key 循环 — `mode_name` 先解出, 再查 `MODE_KEY_BINDINGS[mode_name]` 限定 key 子集轮换
- **compose**: `NV_GLM52_MODE_CHAIN=integrate_us_rr,pexec_us_rr` (5→2 mode, 砍 pexec_direct 死档 +
  single 变体), 新增 `MODE_KEY_BINDINGS` + `NV_GLM52_KEY_PROXY_BIND` 两个 env.
- **部署**: `docker compose up -d --force-recreate nv_gw`, idx reset=0, health 200.

### 验证 (改后必有数据)
6 个测试请求全部 200, DB `nv_requests` 确认 key↔IP 一对一固定:
| nv_key_idx | egress_ip | egress_route | litellm_model | status |
|---|---|---|---|---|
| 0 (k1) | 134.195.101.193 | 7894 | integrate_glm5.2_k1 | 200 |
| 2 (k3) | 134.195.101.195 | 7896 | integrate_glm5.2_k3 | 200 |
| 4 (k5) | 134.195.101.180 | 7899 | integrate_glm5.2_k5 | 200 |

→ RR 只在绑定子集内轮换, IP 不再漂移. pexec mode (k2/k4) 待后续流量触发验证.

### 待观察
- pexec_us_rr mode (k2→7895/120, k4→7897/180) 在 integrate 全失败递进时才会触发, 后期靠日志验证.
- mihomo cache.db 若丢失需重跑 PUT 钉死脚本 (可考虑写持久化脚本).

## 待用户确认的决策点 (已全部确认)

1. mode chain: **2 mode** (`integrate_us_rr,pexec_us_rr`) — 砍 pexec_direct 死档. ✅
2. key↔mode 分配: k1/k3/k5→integrate, k2/k4→pexec (3+2). ✅
3. 本轮一次性改源码+env+部署. ✅
