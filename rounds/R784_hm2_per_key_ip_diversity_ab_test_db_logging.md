# R784: HM2 per-key IP 多样性 A/B + DB egress_ip 长期分析

## 摘要

R783 把 5 个 NV group 各切到不同美国节点 (134.195.101.x), 但用户要求进一步做 IP
多样性 A/B 对照: **K2 走本地电信直连 (218.93.250.242), K4 走"日本"CMI 中转节点
(103.62.49.162), K1/K3/K5 保持美国 mihomo 三 IP**, 长期观察哪种 IP 最稳定最快。

为此 nv_gw 需把每次请求的 **出口 IP + route 标签** 写入 DB, 否则无法做 IP 维度分析。
本轮给 `nv_requests` / `nv_tier_attempts` 加 `egress_ip` + `egress_route` 列, 并在
upstream/handlers/db 三层透传 per-attempt egress 信息。

## 改前数据 (铁律: 改前必有数据)

### 1. HM2 出口 IP 全景 (技术调查)
| 路径 | 出口 IP | 备注 |
|---|---|---|
| HM2 宿主直连 (电信) | 218.93.250.242 | 与 HM1 同出口 (tailscale 同网段) |
| mihomo 7894 (K1) | 134.195.101.193 | 美国 Hysteria2 |
| mihomo 7895 (K2) | 134.195.101.194 | 美国 |
| mihomo 7896 (K3) | 134.195.101.195 | 美国 |
| mihomo 7897 (K4) | 103.62.49.162 | "日本东京06" CMI 中转 (非真日本) |
| mihomo 7899 (K5) | 134.195.101.180 | 美国 |

**关键发现**: HM2 没有真实日本 IP。所有 mihomo "日本东京/AWS日本" 节点出口都是
CMI 中转 103.62.49.x; HM1/HM2 宿主直连都是中国电信 218.93.250.242 (同一出口)。
用户确认 K4 用 CMI 中转"日本"节点 (103.62.49.162) 满足"日本节点"语义。

### 2. 改前 DB 缺 egress_ip 字段
```
nv_requests 列: ... nv_key_idx, litellm_model, ... (无 egress_ip/egress_route)
```
无法做 IP 维度分析 — 只有 key 维度, 但同一 key 可能换 IP (mihomo 切节点), 无法
追溯具体走哪个 IP。

### 3. 各 IP 当前成功率 (改前 30min, 全走美国 mihomo)
| key | IP | total | ok | avg_ms |
|---|---|---|---|---|
| K1 | 134.195.101.193 | 6 | 6 | 9347 |
| K2 | 134.195.101.194 | 6 | 6 | 27375 |
| K3 | 134.195.101.195 | 0 | 0 | — (403) |
| K4 | 103.62.49.162 | 9 | 9 | 19854 |
| K5 | 134.195.101.180 | 10 | 10 | 21029 |

## 改动

### 1. DB schema (logs_db, HM2)
```sql
ALTER TABLE nv_requests ADD COLUMN egress_ip text;
ALTER TABLE nv_requests ADD COLUMN egress_route text;
ALTER TABLE nv_tier_attempts ADD COLUMN egress_ip text;
ALTER TABLE nv_tier_attempts ADD COLUMN egress_route text;
CREATE INDEX idx_nv_req_egress_ts ON nv_requests (egress_ip, ts DESC) WHERE egress_ip IS NOT NULL;
CREATE INDEX idx_nv_att_egress_ts ON nv_tier_attempts (egress_ip, ts DESC) WHERE egress_ip IS NOT NULL;
```

### 2. config.py: egress_info_for_key(key_idx) → (route, ip)
```python
NVU_EGRESS_IPS = [os.environ.get(f"NVU_EGRESS_IP{i}", "") for i in range(1,6)]

def egress_info_for_key(key_idx):
    # proxy_url 空 → "direct"; 非空 → "mihomo-<port>"
    # ip 从 NVU_EGRESS_IP<n> env 取 (配置时硬编码, 运行时不解析代理出口)
    ...
```
- route: 人类可读标签 ("direct" / "mihomo-7894" 等)
- ip: 从 env NVU_EGRESS_IP<n> 取 (IP 变化时改 env 不改代码)

### 3. upstream.py: per-attempt + result 透传 egress
- `UpstreamResult` 加 `egress_route` / `egress_ip` 字段
- 13 处 `key_cycle_attempts.append({...})` 全部加 `"egress_route"` / `"egress_ip"` 字段
  (用 `egress_info_for_key(key_idx)[0]/[1]`)
- 2 处 success 赋值 (integrate + pexec) 加 `result.egress_route, result.egress_ip = egress_info_for_key(key_idx)`
- import block 加 `egress_info_for_key`

### 4. handlers.py: metrics 接收 result.egress
```python
metrics["egress_route"] = result.egress_route
metrics["egress_ip"] = result.egress_ip
```

### 5. db.py: INSERT 加 egress_ip/egress_route
- `nv_requests` INSERT 列 + `_build_request_row` return 末尾加 `egress_ip, egress_route`
- `nv_tier_attempts` INSERT 列 + attempt_rows 构造加 `egress_route, egress_ip`
- ON CONFLICT UPDATE 也加 egress_ip/egress_route

### 6. docker-compose.yml (HM2)
```yaml
- NVU_PROXY_URL1=socks5h://172.17.0.1:7894   # K1 美国
- NVU_PROXY_URL2=                              # K2 直连电信 (空=direct)
- NVU_PROXY_URL3=socks5h://172.17.0.1:7896   # K3 美国
- NVU_PROXY_URL4=socks5h://172.17.0.1:7897   # K4 日本CMI (mihomo group 切日本东京06)
- NVU_PROXY_URL5=socks5h://172.17.0.1:7899   # K5 美国
# R784: per-key egress IP
- NVU_EGRESS_IP1=134.195.101.193   # K1 美国
- NVU_EGRESS_IP2=218.93.250.242    # K2 电信直连
- NVU_EGRESS_IP3=134.195.101.195   # K3 美国
- NVU_EGRESS_IP4=103.62.49.162     # K4 日本CMI
- NVU_EGRESS_IP5=134.195.101.180   # K5 美国
```

### 7. mihomo: ♻️US-NV-K4 切到"日本东京06-0.1倍 | 高速专线推荐"
- store-selected 持久化 (重启保留)
- 出口 103.62.49.162 (CMI 中转日本)

## 验证 (铁律: 改后必有验证)

### 1. egress_info_for_key 容器内运行
```
k1: route=mihomo-7894 ip=134.195.101.193
k2: route=direct      ip=218.93.250.242
k3: route=mihomo-7896 ip=134.195.101.195
k4: route=mihomo-7897 ip=103.62.49.162
k5: route=mihomo-7899 ip=134.195.101.180
```

### 2. kimi_nv 多次请求 (触发不同 key), DB 记录
```
nv_key_idx | egress_route | egress_ip     | status | duration_ms
-----------+--------------+---------------+--------+-------------
     4     | mihomo-7899  | 134.195.101.180 | 200  | 815
     3     | mihomo-7897  | 103.62.49.162   | 200  | 2122
     3     | mihomo-7897  | 103.62.49.162   | 200  | 2947
     1     | direct       | 218.93.250.242  | 200  | 1000   ← K2 直连成功!
     0     | mihomo-7894  | 134.195.101.193 | 200  | 1118
     4     | mihomo-7899  | 134.195.101.180 | 200  | 1105
     3     | mihomo-7897  | 103.62.49.162   | 200  | 1472
```

### 3. 按 egress_ip 汇总 (4 种 IP 全部 200 成功)
```
egress_ip     | egress_route | count | ok | avg_ms
--------------+--------------+-------+----+--------
103.62.49.162 | mihomo-7897  |  3    | 3  | 2180
134.195.101.180| mihomo-7899 |  2    | 2  | 960
134.195.101.193| mihomo-7894 |  1    | 1  | 1118
218.93.250.242| direct      |  1    | 1  | 1000
```
- **K2 电信直连 1000ms 成功** (与 HM1 直连一致, 证实电信直连对 NVCF pexec 可用)
- **K4 日本CMI 2180ms 成功** (CMI 中转节点对 NVCF 可用, 推翻 R705 "CMI 全 block" 判断)
- K1/K5 美国 mihomo 正常
- K3 未出现 (持续 403, 用户确认保持现状, 不调整)

## 预期效果 (长期 A/B)
- DB 持续记录每次请求的 egress_ip + route + status + duration
- 可按 IP 维度分析: 成功率、p50/p90 延迟、错误类型分布
- 4 种 IP 对照:
  - 美国三 IP (134.195.101.193/195/180) — 当前主力
  - 电信直连 (218.93.250.242) — K2, 最简 (无 mihomo 依赖)
  - 日本CMI (103.62.49.162) — K4, 中转节点
- 长期观察确定最稳定最快的 IP, 后续可调整其他 key 跟进

## 分析查询模板
```sql
-- 按 IP 汇总成功率 + 延迟 (任意时间窗口)
SELECT egress_ip, egress_route,
       count(*) AS total,
       count(*) FILTER (WHERE status=200) AS ok,
       round(100.0*count(*) FILTER (WHERE status=200)/count(*)) AS succ_pct,
       round(avg(duration_ms) FILTER (WHERE status=200)) AS avg_ms,
       round(percentile_cont(0.9) WITHIN GROUP (ORDER BY duration_ms) FILTER (WHERE status=200)) AS p90_ms
FROM nv_requests
WHERE ts > now() - interval 24 hours AND egress_ip IS NOT NULL
GROUP BY egress_ip, egress_route ORDER BY succ_pct DESC, avg_ms;
```

## 未做 / Follow-up
- **长期数据积累**: 需 24h+ 才能给出 IP 稳定性结论, 本轮只搭好基础设施
- **K3 仍 403**: HM2 美国节点对 K3 不友好, 用户确认不调整, 保持现状 (403 快速失败 + cooldown)
- **HM1 同步**: 用户明确暂不动 (HM1 仍全直连)
- **IP 变化时**: mihomo 切节点后出口 IP 变, 需更新 compose NVU_EGRESS_IP<n> env (route 标签不变)
- **egress_ip 字段未回填**: 历史 nv_requests 行 egress_ip 为 NULL, 只对新请求生效

## 回滚
```bash
# 代码 (bind-mount, 改完 docker restart nv_gw)
cd /opt/cc-infra/proxy/nv-gw/gateway
cp config.py.bak.R784 config.py
cp upstream.py.bak.R784 upstream.py
cp handlers.py.bak.R784 handlers.py
cp db.py.bak.R784 db.py
docker restart nv_gw
# compose
cd /opt/cc-infra && cp docker-compose.yml.bak.R784 docker-compose.yml
docker compose up -d nv_gw
# mihomo K4 切回美国节点 (可选)
# DB 列保留 (无害, 不回滚 schema)
```

## 不改的东西 (铁律: 聚焦)
- HM1 任何配置 (用户: 暂不动)
- K3 key 配置 (用户: 不调整, 与别的 key 无区别)
- ms_gw / 41xx 适配器 (不动)
- DB schema 不回滚 (egress_ip 列保留, 历史行 NULL 无害)
