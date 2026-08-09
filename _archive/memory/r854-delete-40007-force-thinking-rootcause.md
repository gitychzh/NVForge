---
name: r854-delete-40007-force-thinking-rootcause
description: "R854 删除cc4101全部40007/glm5_2_ms/ms_gw fallback代码(nv_gw glm5_2_nv ONLY); 持续卡死真根因=nv_gw强制thinking注入(enable_thinking=True)即使config inject={}仍残留, restart后消失"
metadata: 
  node_type: memory
  type: project
  originSessionId: 3c8d8f5f-50f9-4f31-9c0c-b1eae74a0183
---

# R854 — 删40007 fallback + 持续卡死真根因(nv_gw强制thinking注入) (2026-07-14)

## 用户诉求
"把40007容器排除,cc4101里有关40007的ms的glm5.2相关代码删除,只用nv的glm5.2,缩小排查范围,仅排查cc4101与40006相关代码"

## R854 清理 (cc4101 四文件, 全部应用+restart OK)
彻底删除所有 40007/ms_gw/glm5_2_ms fallback 代码:
- **config.py**: 删 `FALLBACK_HEADER_TIMEOUT`, `FALLBACK_UPSTREAM_URL/MODEL/TOKEN`, `RETRY_PRIMARY_AFTER_FALLBACK`, `CC4101_TOTAL_BUDGET_S` 及相关注释. glm5_2_nv ONLY.
- **upstream.py**: 删 `from .config import FALLBACK_*`, 删 disabled fallback block (Stage 2), execute_request 简化为 primary-only (circuit OPEN → fast-fail 503). docstring/inline 注释全清.
- **handlers.py**: /health 删 `fallback` 字段 (现只返回 primary+port); metrics `fallback_triggered` 保留为 False (DB schema 兼容) 加注释; 删所有 "primary→fallback" 注释.
- **app.py**: 删 `FALLBACK_UPSTREAM_MODEL` import, startup banner 改 "upstream: nv_gw glm5_2_nv ONLY (R854)".
- 验证: `docker restart cc4101` → `/health` 无 fallback 字段, startup banner 确认. grep `FALLBACK|40007|glm5_2_ms|ms_gw` 仅剩描述性注释.

## ⭐ 持续卡死真根因 (不是cc4101, 是nv_gw)
cc4101 清理后探针仍返空(thinking-only, 0c text). 查 nv_gw 日志见 `[NV-INJECT-THINKING] body had no chat_template_kwargs → injected chat_template_kwargs={'enable_thinking': True}` —— **强制注入 thinking!**

但 config.py glm5_2 的 `inject` 早已是 `{}` (空, R797 期就停了强制thinking). 为什么还在注入?

**根因**: nv_gw 进程是早前重启的, 那时 config 的 inject 可能还非空, **进程内 nvcf_cfg 缓存了旧 inject dict** (NVCF_PEXEC_MODELS 在 import 时求值, 之后改 config 文件不重进程不生效). 后来 config 改成 `{}` 但 nv_gw **没restart**, 进程内仍是旧的 `{"chat_template_kwargs":{"enable_thinking":True}}` → 每个请求强制 thinking → GLM5.2 thinking 模式产出 4000c reasoning 但 0c content + finish=length 涨满 max_tokens → cc4101 R852c 抓 zombie → api_error → CC 重试 → 同样 thinking-only-empty → 死循环卡死.

**修复**: `docker restart nv_gw` 让进程重读 config, inject={} 生效. restart 后探针 3/3 正常返 text ('4', '你好呀！😊', '你好，很高兴...'), 无 NV-INJECT-THINKING 日志. CC-like 请求(tools+system+中等context) status=200 text完整 thinking=0c elapsed=8.1s.

## 教训 (可复用)
- **改 nv_gw/config.py 后必须 docker restart nv_gw** — Python 模块级常量在 import 时求值, 改文件不重启不生效. 进程内缓存旧值是最隐蔽的"配置没生效"陷阱.
- 判断强制thinking是否还活着: `docker logs nv_gw --since 2m | grep NV-INJECT-THINKING` 有输出=还在注入; 无输出=已停.
- GLM5.2 普通模式(无thinking) content 正常秒回; thinking 模式答案写进 reasoning_content 致 content 空 → 这就是 R852 系列修的"empty/filtered completion". **R852 是兜底, R854(停thinking注入)是根治**.

## 关联
- [[r852-empty-content-zombie-fix]] R852/R852b/R852c zombie 检测 — 兜底 thinking-only-empty.
- [[r853-read-timeout-root-cause]] R853 8min挂死底座 — 让 stall-watcher 能跑.
- 本轮彻底删 40007 后, cc4101 只剩 nv_gw glm5_2_nv 单链路; circuit OPEN 直接 fast-fail 503 (无 fallback).
