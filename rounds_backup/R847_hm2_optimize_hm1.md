# R847: HM2→HM1 — NOP + 三轮总结 (R845/R846 持续有效, 链路 100% SR)

**Date**: 2026-07-08 04:25 UTC
**Author**: opc2_uname (HM2)
**Target**: HM1 (100.109.153.83) nv_gw
**Type**: NOP (zero parameter change, zero code change, zero container restart)

---

## 本轮决策: NOP

改前数据 (近 20min):
| 指标 | 值 |
|------|-----|
| SR | 100% (1/1, 测试请求 04:14) |
| tier_attempts 错误 | 0 |
| METRICS-ERR / NV-RR WARN | 0 (R845/R846 防护就位无触发) |
| rr_counter.json | {nv_dsv4p:2145, nv_kimi:13, nv_glm5_2:1} — R846 独立性持续 |
| health | ok (Up 11min healthy) |

链路超健康, 静默 except 审计已完成 (R846), 无新数据支撑的优化点.
**铁律1: 改前必有数据 → 数据说健康 → 不改.**

---

## 三轮总结

### R845 (03:41 UTC) — 修复 metrics gap (8h 数据盲区)
**根因**: `logger._log_metrics` 两个 `except Exception: pass` 静默吞异常 +
db worker 无自愈. worker alive 但 queue=0 (03:33:44 后 `_log_metrics` 不被调用),
JSONL+DB 同停 8h, proxy log 正常, 03:36 重启未恢复.

**改动** (4编辑点, 2文件):
1. `logger.py` `_log_metrics` JSONL try: `pass` → `print [METRICS-ERR]`
2. `logger.py` `_log_metrics` enqueue try: `pass` → `print [METRICS-ERR]`
3. `db.py` `_worker_loop` `_flush_batch` 包 try/except (防 worker 死亡)
4. `db.py` `enqueue_metrics` 加 worker 自愈 (is_alive 检测重启)

**验证**: 重启后手动 `_log_metrics` → JSONL+DB 入库 ✓; 真实 openclaw 04:03 批次
3 条入库 ✓; 测试请求 04:14 入库 ✓. 8h gap 修复, 可见性+自愈就位.

### R846 (04:00 UTC) — 修 rr_counter glm5_2_nv 漏映射
**根因**: `rr_counter.py` 注释说"三模型独立 counter", 但 `_TIER_RR_KEYS` 只映射
kimi_nv/dsv4p_nv, **glm5_2_nv 漏**. `_next_nv_key` fallback `nv_dsv4p` →
glm5_2_nv 与 dsv4p_nv **共享 counter** (rr_counter.json nv_dsv4p=2145 印证).
R845 同类静默瑕疵.

**改动** (2编辑点, 1文件):
1. `_TIER_RR_KEYS` 补 `"glm5_2_nv": "nv_glm5_2"`
2. `_next_nv_key` fallback 加一次性 `[NV-RR] WARN` 告警 (防未来遗漏)

**验证**: 真实请求后 `rr_counter.json = {nv_dsv4p:2145, nv_kimi:13, nv_glm5_2:1}`,
**nv_dsv4p 未被推进** = glm5_2_nv 独立性确认 ✓.

### R847 (04:25 UTC) — NOP + 总结
零改动. 验证 R845/R846 持续有效, 无告警无错误.

---

## 三轮累计改动

| 文件 | 改动 | 性质 |
|------|------|------|
| `gateway/logger.py` | 2处 except 可见性 | bugfix + 防护 |
| `gateway/db.py` | worker guard + 自愈 | bugfix + 防护 |
| `gateway/rr_counter.py` | glm5_2_nv 映射 + fallback 告警 | bugfix + 防护 |

**主题**: 修复两类"静默吞异常/静默 fallback"瑕疵 (R845 metrics gap 8h + R846
counter 共享), 并为同类添加可见性/自愈防护. 均有数据支撑, 零参数盲调, 零性能回归.

## 备份

- `logger.py.bak.R845`, `db.py.bak.R845`, `rr_counter.py.bak.R846` (HM1)
- round 文件备份到 `/home/opc2_uname/cc_ps/NVForge/rounds_backup/` (防 hermes 自动化 reset)

## 注意事项 (告知)

1. **HM1 代码改动已部署并验证** — 实际优化效果已落地.
2. **hermes 自动化进程在反复 `git reset --hard origin/main`** — 本地未 push 的
   commit 会被丢弃 (R846 前次 660f464 已被丢, 已 re-commit 为 cd1fc20 并备份).
3. **R845 commit (0a6b71c) 已被自动化带 push 到 origin/main** — 非本 session 所为,
   无法撤回 (force push 会破坏远程历史). R846/R847 仅本地 commit, 未 push.
4. 未 push 的 R846/R847 可能被下次自动化 reset 覆盖, 已备份到 scratch base.

## 回滚预案 (如需)

```bash
ssh -p 222 opc_uname@100.109.153.83 'cd /opt/cc-infra/proxy/nv-gw/gateway && \
  cp logger.py.bak.R845 logger.py && cp db.py.bak.R845 db.py && \
  cp rr_counter.py.bak.R846 rr_counter.py && docker restart nv_gw'
```
