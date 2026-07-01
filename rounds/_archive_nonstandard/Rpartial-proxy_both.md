# Rpartial-proxy: 两机部分key保留mihomo代理(修正全直连决策)

**轮次**: HM1自改(本机,用户授权) + HM1改HM2(对端,符合铁律)
**时间**: 2026-06-30 17:15-17:17 CST

## 背景: 修正Rmihomo-remove的错误
Rmihomo-remove 误判HM1直连出口=日本IP(103.62.49.138), 实测纠正:
- HM1真实直连出口=218.93.250.242(中国南京电信), 与HM2同
- 103.62.49.138是mihomo某个海外节点, 非HM1直连
- 结论: 两机直连出口都是中国IP, 全直连依赖"NVCF当前不封中国IP"这个脆弱前提
- 用户决策: 两机各保留2把key走mihomo海外代理作冗余, 其余直连享低延迟

## 改动

### HM1 (本机, 授权自改)
- key1(idx0/URL1) → mihomo 7894 (出口 134.195.101.193 美国)
- key3(idx2/URL3) → mihomo 7896 (出口 134.195.101.194 美国)
- key2/4/5 → 直连 (出口 218.93.250.242 中国南京电信)
- 部署: 17:15:27 CST, docker compose up -d hm40006 (Recreated)

### HM2 (对端, 铁律HM1改HM2)
- key2(idx1/URL2) → mihomo 7895 (出口 134.195.101.188 美国)
- key4(idx3/URL4) → mihomo 7897 (出口 134.195.101.194 美国)
- key1/3/5 → 直连 (出口 218.93.250.242 中国南京电信)
- 部署: 17:17:07 CST, docker compose up -d hm40006 (Recreated)

## 流量走向验证(真实请求+日志铁证)

### HM1 (hm40006日志原文)
- k1 → NVCF pexec via http://host.docker.internal:7894  (代理)
- k2 → NVCF pexec DIRECT                                  (直连)
- k3 → NVCF pexec via http://host.docker.internal:7896  (代理)
- k4 → NVCF pexec DIRECT                                  (直连)
- k5 → NVCF pexec DIRECT                                  (直连)

### HM2 (hm40006日志原文 + 源码逻辑)
HM2日志格式无DIRECT字样, 空URL打印"via "(空). 源码upstream.py:72-75铁证:
  if not proxy_url or proxy_url.strip() == "":
      conn = http.client.HTTPSConnection(nvcf_host, 443, timeout=timeout)
      return conn   # 直连, 不经mihomo
- k1 → via (空) = 直连
- k2 → via http://host.docker.internal:7895  (代理)
- k3 → via (空) = 直连
- k4 → via http://host.docker.internal:7897  (代理)
- k5 → via (空) = 直连

## DB交叉验证(部署后请求全200)
- HM1: 17:17:28 5把key(idx0-4)各1请求全200
- HM2: 17:18:29-17:19:13 多请求全200, 5把key覆盖

## 容器env确认
- HM1: URL1=7894, URL2=空, URL3=7896, URL4=空, URL5=空 ✅
- HM2: URL1=空, URL2=7895, URL3=空, URL4=7897, URL5=空 ✅

## 设计理由
- 两机直连出口同为中国IP, 若NVCF未来封中国IP, 直连key会同时受影响
- 各保留2把海外代理key(美国IP)作冗余, 确保部分流量仍可达NVCF
- 直连享低延迟(无SOCKS5跳转), 代理享IP多样性, 平衡性能与鲁棒性
- 两机代理key编号错开(HM1=k1/k3, HM2=k2/k4), 避免同端口同出口IP叠加限流
