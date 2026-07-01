# Rmihomo-remove: HM1 全key改直连(去除mihomo)

**轮次**: HM1自改(用户授权破例, 非对端优化轮)
**时间**: 2026-06-30 16:27 CST (UTC 08:27)

## 改动
HM1 hm40006 compose: `HM_NV_PROXY_URL1/4/5` 从 mihomo 端口改为空。
- 改前: K1/K4/K5 via mihomo(7894/7897/7899, 美国IP 134.195.101.x), K2/K3 直连
- 改后: K1-K5 全部直连, 出口=HM1主机直连IP 103.62.49.138(日本东京,境外)

## 数据依据(部署前8h基线)
- 226请求, 成功率99.12%, p50=13095ms
- 代理(K0/K3/K4): 131req 全成功 / 直连(K1/K2): 93req 全成功
- 代理vs直连成功率无差异, 代理仅多0.5-0.9s p50延迟(SOCKS5跳转固有开销)

## 验证(部署后真实流量)
- 容器env: HM_NV_PROXY_URL1-5 全空 ✅
- 容器日志: `k2 → NVCF pexec DIRECT` / `k3 → NVCF pexec DIRECT` ✅
- 真实请求: 16:28:14 k2 200 698ms ✅
- /health: ok, deepseek_hm_nv ✅

## 对比基准
- mihomo时代: 3把代理key(美国IP) + 2把直连(日本IP)
- 全直连时代: 5把key共用日本IP(103.62.49.138)
- 关注点: NVCF对日本IP无风控(境外), 预期成功率持平/略升, 延迟略降

## 铁律
只改HM1本机(用户授权破例自改, 类似Rproxy/Reng). HM2 mihomo保留(其直连出口是中国电信IP 218.93.250.242, 需代理作NVCF风控保险).
