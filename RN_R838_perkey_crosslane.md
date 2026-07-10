# R838: nv_gw per-key 跨链路调度 — HM2 自改 (2026-07-10)

**作者**: opc2_uname (HM2)
**类型**: HM2 自改 HM2 (per-key 跨链路新能力, 用户方案驱动)
**铁律**: 本轮只改 HM2, HM1 待 HM2 调好后下轮同步

## 用户方案
"极度不稳定, 今天这种模式稳明天另一种稳" → 需数据多样性 (链路分散), 非单选最优:
1. kimi_nv: K1-4 pexec_direct + K5 integrate_us
2. dsv4p_nv: K1-4 pexec_direct + K5 integrate_us
3. glm5_2_nv: 全 5 key 走不同美国 IP 的 integrate_us
4. minimax_m3_nv: K1-4 pexec_direct + K5 integrate_us/p7899 (HM1 事, HM2 无此 tier)

## 关键发现: kimi integrate 不可行
5key 全测: kimi-k2.6 在 integrate 端点 **5 key 全 404** (`Function 23d4f03a: Not found for account`).
dsv4p/minimax 在 integrate 端点 5 key 全 200. 故 NV_KEY_INTEGRATE_KEYS=dsv4p_nv:5 (仅 dsv4p).

## 代码改动 (3 处)
1. config.py: 加 NV_KEY_INTEGRATE_KEYS (per-model 格式 `dsv4p_nv:5`) + NV_KEY_INTEGRATE_PROXY_URLS + nv_key_integrate_keys_for() 函数. 旧纯数字格式向后兼容.
2. upstream.py _try_integrate_keys: 加 key_filter 参数, 循环遍历 _filter_keys 而非全 5 key; proxy_url 优先 NV_KEY_INTEGRATE_PROXY_URLS.
3. upstream.py dispatch (R572 块前): 新增 R838 per-key 分支 (tier_model not in NV_INTEGRATE_MODELS and _r838_keys), 失败回退 pexec (与 R572 elif 互斥).
4. egress 记录修正: 用实际 proxy_url 算 egress_route (key_filter 模式记真实端口).

## env (docker-compose.yml)
- NV_KEY_INTEGRATE_KEYS=dsv4p_nv:5
- NV_KEY_INTEGRATE_PROXY_URLS=socks5h://172.18.0.1:7897 (测速最快)
- NV_INTEGRATE_PROXY_URLS=7894,7895,7896,7897,7899 (5 美国出口轮换, 方案3)
- NV_INTEGRATE_MODELS=glm5_2_nv 不变
- NVU_PROXY_URL1-5= 全空 (K1-4 pexec_direct)

## 验证 (DB 铁证)
- dsv4p K5: 15 次 nv_integrate via 7897 + pexec fallback ✅
- glm5.2: K0→7894, K1→7895, K2→7896, K3→7897, K4→7899 各走不同 IP ✅
- kimi: 全 nvcf_pexec, 无 integrate 404 往返 ✅

## 回滚
删 NV_KEY_INTEGRATE_KEYS env → 完全回退 per-model 行为. 备份 .bak.preR838.
