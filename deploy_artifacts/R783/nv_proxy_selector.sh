#!/usr/bin/env bash
# nv_proxy_selector.sh — 确保 mihomo 5 个 NV group (♻️US-NV-K1..K5) 各指向不同美国节点
#
# 背景: R782 发现 5 个 group 全指向同一节点 → 5 key 共享 IP → same-IP rate limit 风险。
# mihomo 有 store-selected:true 会持久化 selector 选择, 但 cache.db 丢失或手动误操作
# 后会回退到默认 (可能同节点). 本脚本作为兜底, 确保 5 group 各走不同节点。
#
# 用法:
#   ./nv_proxy_selector.sh          # 选 5 个不同美国节点 (按列表顺序前 5 个能通的)
#   ./nv_proxy_selector.sh --check  # 只检查当前状态, 不切换
#
# 设计 (参考 config.yaml 注释原意):
#   - 从 nv-us-provider 的美国节点列表里挑 5 个能通的 (出口 IP 各异)
#   - 每个 NV group 分配一个, K1→group1, K2→group2, ...
#   - 优先 Hysteria2 协议节点 (美国01-08, 134.195.101.x 段, 实测对 NVCF 稳定)
#
# 部署: @reboot 或手动跑一次. mihomo store-selected 会把结果持久化.

set -euo pipefail

SECRET="${MIHOMO_SECRET:-set-your-secret}"
API="${MIHOMO_API:-http://127.0.0.1:9090}"
GROUPS=("♻️US-NV-K1" "♻️US-NV-K2" "♻️US-NV-K3" "♻️US-NV-K4" "♻️US-NV-K5")
PORTS=(7894 7895 7896 7897 7899)
# 候选节点 (按优先级, 实测 134.195.101.x 段对 NVCF 稳定)
CANDIDATES=(
  "🇺🇸美国01-0.1倍 | 电信联通移动推荐"
  "🇺🇸美国02-0.1倍 | 电信联通移动推荐"
  "🇺🇸美国03-0.1倍 | 电信联通移动推荐"
  "🇺🇸美国04-0.1倍 | 电信联通移动推荐"
  "🇺🇸美国05-0.1倍 | 电信联通移动推荐"
  "🇺🇸美国06-0.1倍 | 电信联通移动推荐"
  "🇺🇸美国07-0.1倍 | 电信联通移动推荐"
  "🇺🇸美国08-0.1倍 | 电信联通移动推荐"
)

api_put() {
  local group="$1" node="$2"
  curl -s -o /dev/null -w "%{http_code}" -X PUT \
    -H "Authorization: Bearer $SECRET" -H "Content-Type: application/json" \
    "$API/proxies/$group" -d "{\"name\":\"$node\"}"
}

get_ip() {
  local port="$1"
  curl -s --max-time 6 -x socks5h://127.0.0.1:$port https://api.ipify.org 2>/dev/null || echo ""
}

echo "[$(date '+%H:%M:%S')] NV proxy selector — ensuring 5 groups on different US nodes"

if [[ "${1:-}" == "--check" ]]; then
  echo "当前状态:"
  for i in 0 1 2 3 4; do
    now=$(curl -s --max-time 5 -H "Authorization: Bearer $SECRET" "$API/proxies" 2>/dev/null \
      | python3 -c "import sys,json;d=json.load(sys.stdin);print(d.get('proxies',{}).get('${GROUPS[$i]}',{}).get('now',''))" 2>/dev/null)
    ip=$(get_ip "${PORTS[$i]}")
    echo "  ${GROUPS[$i]} (port ${PORTS[$i]}) -> $now | IP=${ip:-FAIL}"
  done
  exit 0
fi

# 选 5 个能通且 IP 各异的节点
assigned=()
used_ips=()
node_idx=0
for gi in 0 1 2 3 4; do
  assigned_node=""
  while [ $node_idx -lt ${#CANDIDATES[@]} ]; do
    node="${CANDIDATES[$node_idx]}"
    node_idx=$((node_idx+1))
    # 临时切到该节点测 IP
    api_put "${GROUPS[$gi]}" "$node" >/dev/null || true
    sleep 1
    ip=$(get_ip "${PORTS[$gi]}")
    if [ -n "$ip" ] && [[ ! " ${used_ips[@]} " =~ " ${ip} " ]]; then
      assigned_node="$node"
      used_ips+=("$ip")
      echo "  ${GROUPS[$gi]} (port ${PORTS[$gi]}) -> $node | IP=$ip"
      break
    fi
    echo "  (skip $node: IP=${ip:-FAIL} 不可用或重复)"
  done
  if [ -z "$assigned_node" ]; then
    echo "  ${GROUPS[$gi]} (port ${PORTS[$gi]}) -> 未找到可用节点!" >&2
  fi
done

echo "[$(date '+%H:%M:%S')] 完成. mihomo store-selected 会持久化此选择."
