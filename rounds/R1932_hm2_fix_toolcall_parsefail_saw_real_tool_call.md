# R1932 (HM2): nv_gw oai_to_anth finish() — 补读 saw_real_tool_call flag, 根治 CC SDK "tool call could not be parsed (retry also failed)" session 中断

**铁律遵守**: 改前必有数据 / 改后必有验证 / 聚焦 nv_gw(40006) / 所有修改写入仓库 / 只改 HM2 不改 HM1 / 改 .py 必须 restart 非 up-d / UTF-8 no BOM

## 现象 (数据)

远程 cc2 (HM2 自优化 session 1981f9e3) 报重大 bug:
```
The model's tool call could not be parsed (retry also failed).
```
2 天窗口: 132 次 "malformed, retry" (分支 A, 重试成功) + 3 次 "retry also failed" → session 中断 (分支 B)。

## 根因 (深度定位)

**单根因, 双分支表现** (非两个 bug):
NVCF (glm5.2 integrate/pexec) SSL jitter 后返"半响应": 前导 text/reasoning + `finish_reason=tool_calls` chunk + **没有任何带 id+args 的真 tool_call delta** → 断流。

转换器 (`/app/gateway/format/oai_to_anth.py`) 漏洞链:
1. `feed_chunk` line 254-255: 收到 `finish_reason=tool_calls` chunk → `pending_stop_reason = "tool_use"` (仅看 finish_reason, 不看是否真有 tool_call delta)
2. `saw_real_tool_call` flag (line 74 init=False, line 166 set=True) **存在但 finish() 从不读它** — line 166 只在 `tc.get("id") AND _fn.get("arguments")` 同时非空时置真
3. handlers.py line 1300 僵尸检测镜像同条件 (saw_tool_calls 也要求 args 非空) → 命中 zombie
4. `finish(zombie=True)`: `final_stop = pending_stop_reason or "end_turn"` = **"tool_use"** → 发 `message_delta(stop_reason=tool_use)` 给 CC
5. CC SDK 看到 `stop_reason=tool_use` 但找不到 tool_use block → "could not be parsed" → malformed retry (分支 A) 或 retry-also-failed 中断 (分支 B)

**为什么 R1839 没触发**:
`_detect_bad_tool_args()` (line 325-345) 返回 `[]` 因为:
- `tool_ids_order` 空 (完全没发 tool_call delta) → 直接 `return []`
- 或有 id 但 args 为空 → `json.loads("{}")` 成功 → 不算畸形 → `return []`

R1839 只兜"有 tool_use block 但 args 畸形", 兜不住"声明 tool_calls 但压根没发 tool_use block"。saw_real_tool_call flag 早已为此设计 (line 74/166), 只是 finish() 漏读。

**铁证 req=176c8878** (serve cc2 L42 @11:56:07.456):
| field | value |
|---|---|
| ts | 2026-07-19 11:55:48 |
| finish_reason | tool_calls |
| status | 502 |
| output_tokens | 222 (全 reasoning) |
| error_type | zombie_empty_completion |
| ttfb_ms | 18981 (≈ L41→L42 19.4s 差) |
| upstream_type | nvcf_pexec key1 |

cc2 L42 content = 纯前导文 ("你说 cloudcli 没清除, 我正要重新核对…"), **无 tool_use block**, 但 stop_reason=tool_use → SDK 抛 malformed。

## 改动

文件: `/opt/cc-infra/proxy/nv-gw/gateway/format/oai_to_anth.py` (bind-mounted)
- 僵尸路径 (finish line ~397): `final_stop = pending_stop_reason or "end_turn"` 之后加:
  ```python
  if self.pending_stop_reason == "tool_use" and not self.saw_real_tool_call:
      final_stop = "end_turn"
  ```
- 正常完成路径 (finish line ~436): 同款检查
- backup: `oai_to_anth.py.bak.R1932` (in-container)

镜像 R1839 模式, 补 finish() 漏读的 saw_real_tool_call flag。与 R1839 互补:
- R1839 兜 "有 block 但 args 畸形" (json.loads 失败)
- R1932 兜 "声明 tool_calls 但压根没发 block" (saw_real_tool_call=False)
正常 tool_call (id+args 齐全) saw_real_tool_call=True, **不受影响**。

## 验证

1. **py_compile**: in-container `python3 -m py_compile` OK
2. **restart** (非 up-d, 铁律): `docker compose restart nv_gw` → health OK, Listening 日志, StartedAt fresh
3. **E2E 流式** (经 cc4101→nv_gw /v1/messages, 真 NVCF 请求):
   `chunks=23 text=True tool_use=False stop=end_turn msg_stop=True` — 正常路径完整
4. **单元测试 3 组** (docker exec python3):
   - TEST1 半响应无 tool_call delta (zombie path): stop=**end_turn** (修复前=tool_use) ✓
   - TEST2 真 tool_call (id+args): stop=**tool_use** saw_real_tool_call=True (无回归) ✓
   - TEST3 空 args tool_call (R1839 漏检 case): stop=**end_turn** (修复前=tool_use) ✓

## 预期效果

- 分支 B (3 次/2d session 中断) → 0 (stop_reason=end_turn, SDK 不走 tool_use 解析)
- 分支 A (132 次/2d malformed retry) → 0 (同上, 不再误导 SDK 找 tool_use block)
- 正常 tool_call 链路不受影响

## 24h 观测清单

- [ ] cc2 jsonl 无新增 "could not be parsed (retry also failed)"
- [ ] cc2 jsonl 无新增 "malformed and could not be parsed. Please retry"
- [ ] nv_requests: zombie_empty_completion 仍正常记录 (未影响 zombie 检测本身, 只改 finish 输出)
- [ ] 正常 tool_call 请求 (hermes/openclaw) 仍 stop_reason=tool_use 正常解析

## 关联

- R1839 bug8 降级 (畸形 args → end_turn) — 互补, R1932 补 saw_real_tool_call 维度
- R1771 mid-response graceful end — R1932 修复的正是 R1771 graceful end 里 stop_reason 误报 tool_use 的子问题
- R1716 peek barrier — peek 通过后 NVCF 仍可能发半响应 (声明 tool_calls 不发 block), R1932 兜住
