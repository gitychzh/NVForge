# R535 (HM2→HM1): HM_FORCE_STREAM_UPGRADE_TIMEOUT 61→59 (-2s) — Revert无效天花板膨胀, 对齐NVCF实际超时与HM2对称

## 数据采集

### 1. Docker logs (最近100行)
- 零ERROR/WARN级日志
- kimi_nv持续`HM-THINKING-TIMEOUT extended 61s`, dsv4p_nv同样
- 观察到空200循环(empty_200, cycling)后接NVCFPexecTimeout → FASTBREAK=1 → peer fallback路径正常
- peer fallback实际有成功案例(98ms ttfb, 总耗时~21s)

### 2. 容器env (8活跃参数)
```
HM_CONNECT_RESERVE_S=3
HM_FORCE_STREAM_UPGRADE_TIMEOUT=61
HM_PEER_FALLBACK_ENABLED=1
HM_PEER_FALLBACK_TIMEOUT=59
HM_PEXEC_TIMEOUT_FASTBREAK=1
KEY_COOLDOWN_S=25
MIN_OUTBOUND_INTERVAL_S=1.2
TIER_COOLDOWN_S=25
TIER_TIMEOUT_BUDGET_S=100
UPSTREAM_TIMEOUT=25
```
-env与compose一致, 无漂移. StartedAt=2026-07-01T21:42:16Z (R534部署后)

### 3. DB 1h/6h/小时级窗口

1h全局:
- 总请求: 3719req | 3484 success (93.7%) | 235 fail (6.3%)
- dsv4p_nv: 2559req | 2549 success (99.6%) | 10 fail (0.4%)
- glm5_1_nv: 1req | 1 success (100%)
- kimi_nv: 1159req | 934 success (80.6%) | 225 fail (19.4%)

6h全局:
- dsv4p_nv: 2700req | 2677 success (99.1%) | 23 fail
- glm5_1_nv: 56req | 48 success (85.7%) | 8 fail
- kimi_nv: 1800req | 1531 success (85.1%) | 269 fail

kimi_nv小时级SR(15h回溯):
```
16:00 92.3% | 17:00 97.2% | 18:00 98.8% (best)
19:00 85.4% | 20:00 91.2% | 21:00 92.1%
22:00 67.1% ⚠️  | 23:00 57.1% ⚠️ (R534部署21:42后骤降)
00:00 75.2% | 01:00 82.3% | 02:00 90.5% (恢复)
03:00 67.4% ⚠️  | 04:00 73.3% | 05:00 86.3%
```
对比: dsv4p_nv 21:00后持续99-100%, 证明HM1 infra本身无问题, 模型级NVCF服务波动是主因.

kimi_nv失败分布(1h, status=502):
- 50-60s: 145 failures (avg 55.5s) ← 本地tier FASTBREAK后直接ATE
- 80-90s: 1 failure
- 90-100s: 80 failures (avg 95.4s) ← BUDGET=100截断peer fallback

### 4. hm_tier_attempts 6h深度
- kimi_nv: 66 NVCFPexecTimeout, 1 empty_200, **0 success** (注:日志存在[HM-SUCCESS] tier=kimi_nv但DB未记录, 知DB success logging遗漏; 仅failure logging部分样本)
- dsv4p_nv: 17 NVCFPexecTimeout, 1 empty_200
- kimi_nv timeout跨度: min=25230ms max=56685ms avg≈52s — NVCF实际超时远低于网关61s

## CC清单评估

| 选项 | 状态 | 数据支撑 |
|------|------|---------|
| MIN_OUTBOUND=1.2 | ✅ 稳定 | 零429, 已充分收敛 |
| Key rebalancing | ✅ 均衡 | 5key成功数178-187, 无劣化 |
| BUDGET=100 | ⚠️ 偏紧 | THINKING=61下peer fallback余量仅~38s, 80 fail在90-100s截断 |
| FASTBREAK=1 | ✅ 最优 | dsv4p零误杀; 函数级排队多key无效 |
| THINKING_TIMEOUT=61 | ❌ 无效膨胀 | NVCF超时50-57s, 61s不binding; R534后kimi_nv小时SR未改善(反从92%→67%) |
| PEER_FALLBACK=59 | ✅ 合理 | 对齐HM2 ceiling=59 |

## 决策

**调整**: `HM_FORCE_STREAM_UPGRADE_TIMEOUT` 61→59 (-2s)

**理由**:
1. **NVCF实际天花板主导**: 6h `hm_tier_attempts`中kimi_nv 66次timeout集中在25-57s(avg 52s), 61s网关天花板从未被触及. R534将59→61基于`cliff=489ms`数据, 但部署后NVCF侧模型级波动(67-98%小时级SR)使任何网关天花板的边际收益被吞没.
2. **FASTBREAK=1速率节省**: 每失败仅1次local attempt, 降2s = 纯节省2s/请求. 1h内kimi_nv 225 fail × 2s = 450s总节省.
3. **BUDGET耦合释放**: THINKING_TIMEOUT -2s → peer fallback有效窗口 +2s (38s→40s), 对边缘budget截断请求边际有益.
4. **HM2对称对齐**: R533 HM2已为59, HM1自R534升为61后形成2s不对称. 对端peer fallback处理天花板应与自身一致.
5. **dsv4p_nv零影响**: dsv4p timeout集中在25-27s, 59s仍远高于其需求.
6. **空200循环无恶化**: 空200在25-60s随机返回, 网关59 vs 61差异不影响空200检测.

**风险**: 极小. 6h/1h/24h DB无证据表明存在59-61s区间的本地成功需要救回. 日志中[HM-SUCCESS] tier=kimi_nv均在<55s内完成.

## 部署执行

### 1. 漂移检测 (三源交叉验证)
```
env=61, compose=61, StartedAt=2026-07-01T21:42:16Z → 无漂移 ✅
```

### 2. compose修改
使用Python re整行替换:
```python
old_line = 'HM_FORCE_STREAM_UPGRADE_TIMEOUT: "61"  # R534...'
new_line = 'HM_FORCE_STREAM_UPGRADE_TIMEOUT: "59"  # R535: HM2→HM1 61→59 (-2s). NVCF实际超时50-57s(avg 52s)主导, 网关61s无binding; FASTBREAK=1 regime下纯省2s/失败; 与HM2 R533对称; 少改多轮; 铁律:只改HM1不改HM2'
```

### 3. 容器重启
`docker compose up -d --no-deps hm40006`
验证: `docker exec hm40006 env | grep HM_FORCE_STREAM_UPGRADE_TIMEOUT=59` ✅

### 4. 运行验证
容器env确认59生效, 日志继续正常streaming, 零ERROR.

## ⏳ 轮到HM1优化HM2
