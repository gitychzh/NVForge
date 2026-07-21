# R2200 (HM2→HM1): KEY_COOLDOWN_S 12→10 (-2s)

## 数据 (6h 窗口, HM1)

| Metric | Value |
|---|---|
| 总请求 | 32 |
| 成功 | 23 (71.87%) |
| Zombie (200空) | 9 (28.13%) |
| ATE | 0 |
| 429 cycling | 87.5% (28/32 key_cycle_429s≥1) |
| Peer-FB | 0 |
| OK avg latency | 20,139ms (↑ from R2198 13,790ms, TIER=1更快轮转到慢K3/K4) |
| OK min/max | 5,755ms / 93,401ms |

**Duration distribution**: 5-10s:9, 10-15s:10, 15-20s:6, 20-25s:2, 25-30s:1, 30-40s:1, >40s:3

**Key cycle breakdown**: key_cycle_429s=0:4, =1:19, =2:5, =3:3, =6:1

**Per-key latency (glm5_2_nv OK)**: K0:13.4s (4OK), K1:11.5s (4OK), K2:11.9s (3OK), K3:26.4s (3OK), K4:31.4s (6OK)

**Tier attempts**: glm5_2_nv: pexec_success=28, pexec_SSLEOFError=7, pexec_429=5, pexec_timeout=4

**模型**: 28 glm5_2_nv + 4 dsv4p_nv (3OK/1err)

## 诊断

- 9 zombie 全为 glm5_2_nv NVCF pexec 返回空 200, gateway 转 502, 非配置可控
- 87.5% key_cycle_429s: KEY_COOLDOWN_S=12 远低于 60s NVCF 窗口, 每请求首 key 必冷, 良性
- 0 ATE 连续第 15 轮无 ATE ★
- 0 peer-fallback 事件: 无 ATE 触发 peer-fb
- **OK 延迟回退**: 20,139ms vs R2198 13,790ms (↑46%), TIER_COOLDOWN_S=1 导致更快轮转到慢键 K3(26.4s)/K4(31.4s), 拉高平均延迟
- K3/K4 慢: HM1 的 K3/K4 走 SOCKS5 mihomo 代理, 与直连 K0-K2 有 ~15-20s 延迟差
- TIER_COOLDOWN=1 已到极限, 继续 KEY 交替缩小

## 改动

**KEY_COOLDOWN_S 12→10 (-2s)**

交替 TIER→KEY 模式 (R2197 TIER 4→2, R2198 KEY 14→12, R2199 TIER 2→1, R2200 KEY 12→10)

**预算**: KEY+TIER+GLM5_2 = 10+1+28 = 39 << 153 BUDGET (114s 余量)

**429 风险**: 已 87.5% cycling, KEY_COOLDOWN_S 变化不影响 429 率 (远低于 60s NVCF 窗口, 属于良性冷启动)

**单参数**: 铁律只改 HM1 不改 HM2 ✓

## 验证

- `docker exec nv_gw env | grep KEY_COOLDOWN_S` → KEY_COOLDOWN_S=10 ✓
- `docker exec nv_gw env | grep TIER_COOLDOWN_S` → TIER_COOLDOWN_S=1 ✓
- `curl /health` → status=ok ✓
- Container 重启确认: `docker compose -f /opt/cc-infra/docker-compose.yml stop nv_gw && up -d nv_gw` ✓
- Line 500 (nv_gw), line 186 (ms_gw untouched) ✓

## ⏳ 轮到HM1优化HM2
