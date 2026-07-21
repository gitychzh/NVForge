# R2180 (HM2): nv_gw 自反馈观测过滤器 marker+prefix 老化修复

## 摘要
修复 NV-TOOLCALL-JSON-BAD 自反馈观测过滤器的 marker/prefix 老化. 旧 marker `# R18` 只匹配
R18xx 轮号, 轮号进 R21xx 后失效; 旧 prefix 没覆盖 Write 工具的 `{"file_path": "` 前缀
(cc2 改用 Write 写 STATE/round 后模型生成的 args 前缀). 6h 实测 8 命中全漏网打印 (R2174-R2179
每轮 8 行噪音). 本次更新 marker 用通用文本 + prefix 加 file_path.

## 背景 (协助 cc2 验证待处理 BUG 时发现)
cc2 在 R2174-R2179 把 [NV-TOOLCALL-JSON-BAD] 标记为"良性噪音"但没真正查根因. 协助深挖发现:
1. 8 个命中全是 cc2/openclaw2 自反馈 (写自己 STATE/round 文件时模型生成畸形 tool_call args).
2. R1839 真降级机制 (_detect_bad_tool_args + finish 强制 end_turn) 完全生效 — 8 rid 全
   [NV-TOOLCALL-JSON-DOWNGRADE] final_stop=end_turn, CC SDK 不走 tool_use args 解析路径,
   session 不中断. DB 确认 8 rid 全 status=200.
3. cc2 jsonl 的 "could not be parsed" 是 cc2 自己 Write 工具的 tool_use_error (收到畸形
   tool_use block 执行时 JSON 解析失败), 非 CC SDK 中断 session. cc2 收到 error 后继续工作 rc=0.
4. 唯一真问题: 观测过滤器 R1832/R1836 老化, 8 命中全漏网每轮打印噪音.

## 数据 (改前 6h)
- [NV-TOOLCALL-JSON-BAD] 命中 8 个 rid (629fc260/030c792b/5ea1eb99/4af5c89a/8b34d933/
  8fcc2190/9bd8868a/9d17f5e3), 全自反馈类, 全被 R1839 降级兜住 (DOWNGRADE 11 次).
- 过滤漏网根因 (python 验证):
  - marker `# R18` 对 R21xx 轮号 marker_match=False → 漏网
  - prefix 没覆盖 `{"file_path": "` (Write 工具) → 漏网
  - 8/8 全漏网打印.

## 改动 (nv_gw format/oai_to_anth.py, bind-mount)
`_tc_json_bad_check` 内 SELF_FB_MARKERS / SELF_FB_PREFIXES (L301-307):
- 旧: `SELF_FB_MARKERS = ("# cc2 自优化交接棒 STATE", "# R18")`
       `SELF_FB_PREFIXES = ('{"content": "#', '{"command": "')`
- 新: `SELF_FB_MARKERS = ("cc2 自优化", "hm2_cc2", "openclaw2 自优化", "交接棒 STATE", "STATE.md", "hm2_oc2")`
       `SELF_FB_PREFIXES = ('{"content": "#', '{"command": "', '{"file_path": "')`

设计: marker 改用通用文本 (非轮号, 永不失效); prefix 加 Write 工具的 file_path. R1839 真降级
已兜住真危害, 此处纯观测噪音过滤, 让未来真非自反馈畸形 tool_call 能立刻凸显.

## 验证
- AST 语法 OK, nv_gw restart 成功, /health OK
- 新过滤器对 8 个真实 frag 本地验证全过滤✅ (逻辑测试)
- 容器内确认 R2180 标记加载 (grep 命中)
- nv_gw restart 期间 cc2 不受影响 (走 cc4101, cc4101 透传 nv_gw, 短暂重启 cc4101 fallback ms_gw 兜住)
- 待跑: 下一轮 cc2 自反馈时 [NV-TOOLCALL-JSON-BAD] 噪音应归零 (被新过滤器吃掉)

## 铁律合规
- 改前有数据: 6h 8 命中 + 过滤漏网根因 python 验证
- 改后有验证: AST + restart + /health + 新过滤器逻辑验证 + 待跑噪音归零
- 聚焦: nv_gw (40006) 源码, 有 R1832/R1836 先例 (同文件同过滤器)
- 入库: deploy_artifacts/R2180_nv_gw_selffb_filter_refresh/ + 本 round
- HM2 only (nv_gw bind-mount, restart)

## 关联
- R1826 bug8 观测器 (本过滤器的起源)
- R1832/R1836 前缀法过滤 (本次老化修复的对象)
- R1839 bug8 真降级 (_detect_bad_tool_args, 兜住真危害, 本次未动)
- R1932/R1933 parse-fail 根治 (CC SDK 侧, 与本观测器互补)

## 注
本 BUG 不影响撤 40007 目标 (自反馈类不走 ms_gw fallback). 协助 cc2 验证待处理 BUG 时发现并修复.
cc2 自优化继续自由跑.
