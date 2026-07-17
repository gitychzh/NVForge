# R1724 — HM2优化HM1: TIER_TIMEOUT_BUDGET_S 140→135 (-5s)

## 数据采集 (HM1)
- **6h窗口**: 60req/50OK(83.3%SR)/10 fail
  - glm5_2_nv: 57req/49OK(86.0%)/8 zombie (3-14s, GFP cadence)
  - dsv4p_nv: 3req/1OK(33.3%)/2 ATE 502 (69-70s, tiers_tried=1, 无 fallback)
- **Tier attempts (6h)**: 57 pexec_success (glm5_2_nv), 3 pexec_SSLEOFError, 1 pexec_429, 0 dsv4p_nv tier_attempts
- **ms_gw**: 5req, all glm5_2_ms, all OK
- **peer-fb**: 0 activity in logs, no TimeoutError
- **HM2 dsv4p_nv**: 127req/111OK(87.4%), K4 degraded (12/17=70.6%), 10 ATE+5 stream_first_byte_timeout
- **Last data**: 20:03 UTC (4h quiet gap, overnight)

## 分析
- dsv4p ATE: 2 fail at 69-70s, tiers_tried=1, neither peer-fb nor ms_gw triggered
  - ms_gw MODELMAP excludes dsv4p_nv (R1609: streaming sync defect)
  - peer-fb not triggering in logs → rescue path gap for dsv4p_nv
- Trimming trajectory: R1723 cut BUDGET_DSV4P 65→60, R1722 cut global 145→140
- Continue: 140→135 further trims waste from ATE failure path
  - dsv4p ATE→peer-fb: 60+125=185→cap 135, peer-fb gets 75s≥72(70+2) ✓ (+3s margin)
  - OK path: max_ok=51.8s, 135-51.8=83.2s headroom safe ✓
- 单参数, trimming trajectory continues

## 修改
- `TIER_TIMEOUT_BUDGET_S`: 140 → 135 (-5s)
- HM1 docker-compose.yml line 489
- 单参数; 铁律:只改HM1不改HM2

## 预算验证
| 路径 | 计算 | 约束 | 状态 |
|------|------|------|------|
| dsv4p ATE→peer-fb | 60+125=185→cap 135 | peer-fb 得 75s ≥ 72 (HM2 70+2) ✓ | ✅ |
| glm5_2 BIG_INPUT→peer-fb | 0+125=125 | < 135 ✓ | ✅ |
| OK path | max_ok=51.8s | < 135 safe (83s headroom) | ✅ |

## 验证
- `docker compose up -d nv_gw` → Started ✓
- `docker exec nv_gw env`: TIER_TIMEOUT_BUDGET_S=135 ✓
- `curl /health`: status=ok ✓
- 无漂移: compose=135, container=135 ✓
## ⏳ 轮到HM1优化HM2
