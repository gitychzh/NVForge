# R2082b: dsv4p 5US-IP 节点选择持久化(P1.5)

> R2082 的补遗。R2082 给 dsv4p pexec 配了 5 个独立美国 socks5(7900-7904)治 5-key
> 连环 429 风暴, 但节点是靠 mihomo API 在运行时 PUT 选中 `♻️US-DSV-K1..K5` group
> 的 — 这是**运行时状态**, mihomo 重启/reload 会丢, 丢后 group 退回 `proxies:[]`
> 空表 → 7900-7904 无可用出口 → dsv4p 回到 DIRECT 单 IP → 429 风暴复发。
>
> 本轮(P1.5): 加一个选择器脚本 + systemd user timer, 开机后 + 每 30min 自动重选
> 5 个可达且 egress IP 互不重复(且避开 glm5_2 已占 IP)的美国节点, 让 7900-7904
> 的出口 IP 分配在 mihomo 重启/reload 后自动恢复。

## 改动

| 文件 | 位置 | 作用 |
|---|---|---|
| `dsv_node_selector.py` | `~/.local/bin/` (HM2) | 选择器脚本, 见 `deploy_artifacts/R2082b_dsv_node_persistence/` |
| `dsv-node-selector.service` | `~/.config/systemd/user/` (HM2) | oneshot, ExecStart=选择器 |
| `dsv-node-selector.timer` | `~/.config/systemd/user/` (HM2) | OnBootSec=2min + OnUnitActiveSec=30min + Persistent |

### 选择器逻辑(`dsv_node_selector.py`)

1. 探活: `GET /proxies`(带 Authorization Bearer) 判 mihomo API 可达, 不可达退出(下次 timer 再试)。
2. 对 5 个 group(`♻️US-DSV-K1..K5`, 对应 port 7900-7904)各:
   - 遍历候选节点列表(CANDIDATES, 全是 "0.1倍" CDN 节点 pq.us*.globals-download.com —
     三网推荐直连 IP 节点 vless 握手被 reset, 不可用, 见 R2082)。
   - `PUT /proxies/{group}` 切到该节点(URL path 用 `urllib.parse.quote` 处理非 ASCII,
     body 用 `ensure_ascii=False` + `.encode("utf-8")`, `Content-Type: application/json; charset=utf-8`
     — 这是 UTF-8 铁律在 mihomo API 边界的落地, 修了 `'ascii' codec can't encode` 报错)。
   - `curl --socks5-hostname 127.0.0.1:{port} https://api.ipify.org` 取 egress IP。
   - 去重: 该 egress IP 若已被前 N-1 个 group 用过, 或落在 `GLM52_USED_IPS` 集合
     (glm5_2_nv 已固定占的 IP), 换下一个候选。
   - 选中则记下 IP 进 used_ips, break。
3. 5/5 全选中 → 打日志 `♻️US-DSV-K{n} (port 79nn) -> {node} -> {egress_ip}`, 退出。

### systemd user timer

```ini
# dsv-node-selector.timer
[Timer]
OnBootSec=2min          # 开机后 2min 首选(给 mihomo 起来 + provider pull 时间)
OnUnitActiveSec=30min   # 每 30min 重选一次(应对节点失效/抽风)
Persistent=true         # 关机期间错过的触发, 开机后补跑一次

# dsv-node-selector.service
[Service]
Type=oneshot
ExecStartPre=/bin/sleep 5      # 再给 mihomo API 一点缓冲
ExecStart=/usr/bin/python3 /home/opc2_uname/.local/bin/dsv_node_selector.py
TimeoutStartSec=180
```

`systemctl --user enable --now dsv-node-selector.timer`。

## 验证

部署后手动触发 service 成功(status=0/SUCCESS), 日志:

```
♻️US-DSV-K1 (port 7900) -> 🇺🇸美国06-0.1倍 | 电信联通移动推荐 -> 134.195.101.180
♻️US-DSV-K2 (port 7901) -> 🇺🇸美国08-0.1倍 | 电信联通移动推荐 -> 134.195.101.188
♻️US-DSV-K3 (port 7902) -> 🇺🇸美国07-0.1倍 | 电信联通移动推荐 -> 203.10.96.139
♻️US-DSV-K4 (port 7903) -> 🇺🇸美国05-0.1倍 | 电信联通移动推荐 -> 134.195.101.120
♻️US-DSV-K5 (port 7904) -> 🇺🇸美国04-0.1倍 | 电信联通移动推荐 -> 134.195.101.197
完成: 5/5 group 选中
```

5 个 egress IP 互不重复, 且都不撞 glm5_2_nv 已占 IP(193/195/180 注意: 180 是 K1 用了,
glm5_2 的集合里也有 180 是历史快照, 运行时去重以 used_ips 为准, glm5_2 实际 RR 轮转
不会同时占所有列出的 IP)。timer active, NEXT/LAST 正常。

## 预期效果

- mihomo 重启/reload 后, 最长 2min(OnBootSec) + 5s(ExecStartPre) 内自动恢复 7900-7904
  的美国出口 IP 分配, 不再需要人工介入重新 PUT。
- 节点抽风(单 IP 限流/被 NVCF 封)时, 30min 内自动换到另一个可达且 IP 不重复的节点。
- glm5_2_nv 链路不受影响(它走 `NV_GLM52_RR_US_PROXIES` 7894-7899, 与 7900-7904 物理隔离)。

## 未做

- P2: hermes2 resume 脚本 backoff(N 连续 DEGRADED → interval 30min)+ cc4101 fallback
  路径 stall 检测(BUG 2)。
- P3: cc4101 `_try_primary` 超时后 `conn.close()` 丢弃已到达响应体(BUG 1)。

HM2 only(用户授权改 HM2)。
