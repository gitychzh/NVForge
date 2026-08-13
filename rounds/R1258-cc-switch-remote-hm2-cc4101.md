# R1258: CC 模型链路切换至远程 HM2 cc4101 + mihomo 订阅更新

## 摘要

HM1 的 CC 链路从本地 `127.0.0.1:4101` (cc4101) 切换至远程 HM2 `100.109.57.26:4101` (cc4101)。
同时更新 HM2 mihomo 代理订阅 URL (旧订阅已过期), 重新选择 5 个最优美国 IP 用于 NVCF pexec。

## 变更内容

### 1. HM2 mihomo 订阅更新
- 旧订阅 URL: `https://dash.xn--cp3a08l.com/api/v1/pq/f36ac84aef68421fa5e73ac59aa78b8d` (已过期, 返回 "token is error")
- 新订阅 URL: `https://dash.pqjc.site/api/v1/pq/ad4978e7f9844ad86d770a863f61ad4b`
- 新订阅返回 base64 编码的 v2ray 格式 (vless:// + hysteria2:// URI), 非直接 YAML
- 编写 Python 转换脚本 `/tmp/sub_to_yaml.py` 将 v2ray URI 转为 mihomo YAML proxy 列表
- 转换结果: 69 个代理节点 (28 个美国节点)

### 2. HM2 NVCF 美国节点选择
对 29 个美国节点进行 NVCF health-check (url=https://api.nvcf.nvidia.com/v1/models):

| 排名 | 延迟 | 节点名 | 类型 | 出口 IP |
|------|------|--------|------|---------|
| 1 | 262ms | 美国圣何塞01 \| 三网推荐 | vless reality | 134.195.101.193 |
| 2 | 265ms | 美国圣何塞04 \| 三网推荐 | vless reality | 134.195.101.197 |
| 3 | 292ms | 美国圣何塞07 \| 三网推荐 | vless reality | 134.195.101.188 |
| 4 | 349ms | 美国圣何塞03 \| 三网推荐 | vless reality | 134.195.101.195 |
| 5 | 381ms | 美国圣何塞06 \| 三网推荐 | vless reality | 134.195.101.180 |

- hysteria2 节点 (0.1倍) 全部对 NVCF 超时
- vless ws+tls 节点 (合适下载使用 0.01倍) 可达但带宽极低
- vless reality 节点 (三网推荐) 性能最佳, 5 个唯一出口 IP

### 3. mihomo proxy group filter 更新
- K1-K5 filter 从 "美国0X-0.1倍" (hysteria2, 全超时) 改为 "美国圣何塞0X.*三网" (reality, 可用)
- DSV K1-K5 手动选择 reality 节点 (圣何塞02/05, 洛杉矶08)

### 4. CC settings.json 切换
- `ANTHROPIC_BASE_URL`: `http://127.0.0.1:4101` → `http://100.109.57.26:4101`
- `NO_PROXY`: 增加 `100.109.0.0/16` (确保 tailscale 流量不走 HTTP proxy)
- `.bashrc`/`.profile` stale `ANTHROPIC_BASE_URL=40001` → `4101`

## 验证

### NVCF 连通性 (HM2 本地)
- 5 个 NV proxy 端口 (7894-7899) 全部 HTTP 401 (NVCF 可达, 401=需 API key, nv_gw 已配置)
- 5 个 DSV proxy 端口 (7900-7904) 同样可达

### 模型链路 E2E (HM2 本地)
- nv_gw /v1/chat/completions: SUCCESS ("Hello" from z-ai/glm-5.2)
- cc4101 /v1/messages (non-stream): SUCCESS ("Hello." model=glm5_2_nv stop=end_turn)
- cc4101 /v1/messages (stream): SUCCESS (完整 anthropic SSE 事件流)
- ms_gw fallback (stream): SUCCESS (ZhipuAI/GLM-5.2 reasoning_content)

### HM1 → HM2 远程链路
- HM1→HM2:4101 /health: HTTP 200 in 37ms (tailscale)
- HM1→HM2:4101 /v1/messages (non-stream): SUCCESS ("Hello!" model=glm5_2_nv)
- HM1→HM2:4101 /v1/messages (stream): SUCCESS (完整 SSE, "1,2,3,4,5")

## 已知问题
- NVCF 账户级 429 rate limit (旧订阅过期期间大量超时重试导致)
- 重启 nv_gw 后 429 清除, Key3 立即恢复, 其余 key 逐步恢复
- buffer_stream.py 有 _log() 参数数量 bug (TypeError: _log() takes 2 positional arguments but 3 were given)

## 参数快照
- HM2 mihomo config: `~/.config/mihomo/config.yaml` (R1258 backup: `.bak.R1258`)
- HM2 nv_gw: NV_GLM52_RR_US_PROXIES = [7901, 7894, 7897, 7896, 7899] (未变)
- HM1 CC settings: `~/.claude/settings.json` (R1258 backup: `.bak.R1258`)
