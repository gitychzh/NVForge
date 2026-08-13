# R1260: dsv4f0731_nv 超时治理 + force_stream_upgrade + 7896 IP 替换

**Date**: 2026-08-14
**Loop**: dsv4f0731 (self-opt)
**Container**: dsvf0731_nv40666 (HM2, port 40666)
**Scope**: HM2 only

## 问题根因 (改前数据)

系统性排查 dsv4f0731_nv 卡顿根因, 5 US IP × 5 key pexec 矩阵探测 (25 次):

1. **NVCF 推理本身慢**: dsv4f0731 生成时间 8-47s (简单 prompt) / 50-112s (thinking budget 1024 + 大上下文 avg 62-116K chars); glm5.2 仅需 6-12s
2. **UPSTREAM_TIMEOUT=45 / FORCE_STREAM_UPGRADE_TIMEOUT=55(默认) 杀掉 >55s 的请求**: 大量有效请求被超时杀掉 → all_tiers_exhausted
3. **fastbreak=3 + tier_budget=180s 只够 ~3 次 attempt** (55×3=165s), 大上下文请求几乎必然全超
4. **7896 IP (.188, 圣何塞07) 故障率最高**: pexec 探测 6 次中 3 次 TIMEOUT + 1 次 SSL EOF; mihomo health 显示 1041ms 延迟尖峰 + 1 次 0 (timeout)

## 修改内容 (4 项)

### 修改 1-3: 40666 容器 env (docker-compose.yml)

| 参数 | 旧值 | 新值 | 理由 |
|------|------|------|------|
| `UPSTREAM_TIMEOUT` | 45 | 120 | 覆盖 dsv4f0731 P99 推理时间 (实测 112s 成功) |
| `NVU_FORCE_STREAM_UPGRADE` | 0 | 1 | 非流式请求升级为流式上游, SSE 累积后以非流式 JSON 返回. 避免 read 超时杀完整响应 |
| `NVU_FORCE_STREAM_UPGRADE_TIMEOUT` | 55(默认) | 120 | 与 UPSTREAM_TIMEOUT 对齐, 给 thinking budget 1024 足够时间 |
| `NVU_PEXEC_TIMEOUT_FASTBREAK` | 3 | 5 | 连续 3 次 timeout 太激进, 5 次给更多 key 尝试机会 |
| `TIER_TIMEOUT_BUDGET_S` | 180 | 600 | UPSTREAM_TIMEOUT=120 × fastbreak=5 = 600s worst case |
| `NVU_TIER_BUDGET_DSV4F0731_NV` | 180 | 600 | 同上, 给 full 5-key 遍历预算 |

### 修改 4: mihomo K3 代理更换 (7896 端口)

- **旧**: `♻️US-NV-K3` filter=`美国圣何塞07.*三网` → 134.195.101.188 (高延迟, 频繁 timeout)
- **新**: `♻️US-NV-K3` filter=`美国圣何塞05.*三网` → 134.195.101.120
- 圣何塞07 移至 DSV-K5 (7904), 保持 5 IP 多样性
- 新 IP 实测: 3/3 pexec 成功, 3.7-19.9s (旧 IP: 2/3 成功, 45-58s + 1 timeout)

## 验证

1. **Health**: `curl http://localhost:40666/health` → OK, 5 keys, dsv4f0731_nv
2. **env 确认**: container 内 6 个参数全部正确生效
3. **E2E 测试 1** (简单 prompt): 200 OK, 112s, force_stream_upgrade accumulated 375c reasoning
4. **E2E 测试 2** (coding prompt): 200 OK, 248s (4 key 尝试: k3→504, k4→504, k5→empty200, k1→SUCCESS), force_stream accumulated 265c content + 1168c reasoning
5. **7896 新 IP pexec**: 3/3 成功 (3.7s, 9.7s, 19.9s)
6. **5 proxy IP**: 全部 US, 全部存活

## 5 US IP 最终状态

| Port | Key | Exit IP | Node |
|------|-----|---------|------|
| 7897 | key1 | .195 | 圣何塞01 |
| 7904 | key2 | .188 | 圣何塞07 (从 K3 移入) |
| 7894 | key3 | .193 | 圣何塞03 |
| 7896 | key4 | .120 | **圣何塞05 (新, 替换 .188)** |
| 7895 | key5 | .197 | 圣何塞06 |

## 预期效果

- dsv4f0731_nv SR 显著提升: 旧 55s timeout 杀 80%+ 有效请求 → 新 120s 覆盖 P99
- force_stream_upgrade 避免非流式 read 超时杀完整响应
- 600s tier budget 容许 full 5-key 遍历 (120s × 5 = 600s worst case)
- 7896 IP 换为更稳定节点, 减少 key4 失败率
- 副作用: 单请求最大延迟从 ~55s 提到 ~120s (可接受, 宁慢不挂)

## 改前备份

- `docker-compose.yml.bak.R1260-dsv4f0731-tuning`
- `~/.config/mihomo/config.yaml.bak.R1260`
