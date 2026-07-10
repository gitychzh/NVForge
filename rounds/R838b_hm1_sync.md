# R838b HM1 sync: nv_gw per-key 跨链路 RR 自然分散 — HM2→HM1 同步 (2026-07-10)

**作者**: opc_uname (HM1)
**类型**: HM2→HM1 同步 (HM2 R838/R838b 已验证, 本轮同步到 HM1)
**铁律**: HM2 先改验证 OK → 本轮同步 HM1. 不改 HM2.

## 背景
HM2 R838 (commit 4ccfe5e) + R838b (commit f0a18bc) 已在 HM2 验证 per-key 跨链路:
- R838 新能力: NV_KEY_INTEGRATE_KEYS env (per-model `dsv4p_nv:5`) + key_filter 参数
- R838b 修正: RR 自然分散 (peek 当前 RR key, 轮到 K5 才走 integrate, K1-4 走 pexec_direct)
用户核心诉求: "极度不稳定, 今天这模式稳明天另一种稳" → 数据多样性 (链路分散) 优先于单选最优.

## HM1 与 HM2 的差异
1. HM1 有 4 个 tier (kimi_nv/dsv4p_nv/glm5_2_nv/minimax_m3_nv), HM2 只 3 个 (无 minimax).
2. HM1 用 http://host.docker.internal:789X 协议 (HM2 用 socks5h://172.18.0.1:789X).
3. HM1 实测 5 端口 egress IP: 7894→193 7895→120 7896→194 7897→193(dup k1) 7899→197.
4. minimax_m3_nv: 用户方案4 K1-4 pexec_direct + K5 integrate_us. HM1 实测 minimax integrate 可用 (R833: 3.7s vs pexec 4.4s), 但为数据多样性 K1-4 故意走 pexec_direct, 仅 K5 走 integrate.

## HM1 配置 (docker-compose.yml nv_gw env)
- NV_INTEGRATE_MODELS: 从 R833 "glm5_2_nv,minimax_m3_nv" 改为 **仅 glm5_2_nv**
  (minimax 移出全 key integrate, 改入 NV_KEY_INTEGRATE_KEYS 仅 K5 integrate)
- NV_KEY_INTEGRATE_KEYS: "dsv4p_nv:5;minimax_m3_nv:5" (两个 model 的 K5 走 integrate)
- NV_KEY_INTEGRATE_PROXY_URLS: "http://host.docker.internal:7897" (K5 integrate 用, 对齐 HM2)
- NV_KEY_INTEGRATE_EGRESS_IPS: "134.195.101.193"
- NV_INTEGRATE_PROXY_URLS: 7894-7899 五端口 (glm5_2_nv 全 key integrate per-key 轮换)
- NV_INTEGRATE_EGRESS_IPS: 193,120,194,193,197

## 代码改动 (3 文件, 从 HM2 同步)
1. rr_counter.py: 加 `_peek_nv_key()` (read-only peek RR 位置, 不 advance)
2. config.py: 加 R827/R828/R838 block (NV_INTEGRATE_PROXY_URLS/EGRESS_IPS, _parse_nv_key_integrate,
   nv_key_integrate_keys_for(), NV_KEY_INTEGRATE_PROXY_URLS/EGRESS_IPS) + export _peek_nv_key + egress_info_for_integrate_key()
3. upstream.py: import block + _try_integrate_keys(key_filter=) 签名 + RR block key_filter aware +
   _filter_keys 循环 + proxy_url R827/R838 逻辑 + egress 实际 proxy_url + dispatch R838b peek 分支

HM1 保留自有: R830c (integrate fastbreak) + R835b (tier budget override) 未被覆盖, 兼容.

## 验证 (HM1 DB 铁证, 发真请求过 nv_gw 40006)
- **dsv4p_nv** (10 req 全 200): K0→pexec-7894 K1→pexec-7895 K2→pexec-7896 K3→pexec-7897 K4→integrate-7897 ✅ RR 自然分散
- **glm5_2_nv** (6 req 全 200): K0-4 全 nv_integrate, 5 端口 7894-7899 各不同美国 IP ✅
- **minimax_m3_nv** (7 req 全 200): K0-3→pexec K4→integrate-7897 ✅ 用户方案4 实现
- **kimi_nv** (6 req 全 200): 全 nvcf_pexec, 无 integrate (kimi integrate 全 404 不可用) ✅

## 回滚
删 R838b env (NV_KEY_INTEGRATE_KEYS/NV_KEY_INTEGRATE_PROXY_URLS/NV_KEY_INTEGRATE_EGRESS_IPS) +
NV_INTEGRATE_MODELS 回 "glm5_2_nv,minimax_m3_nv" + force-recreate. 备份 .bak.preR838_hm1.
