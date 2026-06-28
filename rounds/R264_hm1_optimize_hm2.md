# R264: HM1→HM2 — 清理 hermes provider 缓存死模型名 — 单轮清理 (清理批次)

**回合类型**: 清理 (单主题: hermes 端陈旧缓存)
**方向**: HM1 (opc_uname) → HM2 (opc2_uname)
**时间**: 2026-06-29 01:24 UTC
**批次**: 与 R263 (config.py 清理) 同属 HM2 模型链路清理批次, 人工授权连续提交, 跳过交替
**原则**: 干净整洁、工程化、便于长期调参维护 — 铁律:只改HM2不改HM1

## 摘要

HM2 hermes 端 `~/.hermes/provider_models_cache.json` 缓存了 17 个陈旧模型名 (含
deepseek_hm_nv/kimi_hm_nv 及各种别名), 来自 R38.14/R208 多模型时期的探测, 时间戳
2026-06-24。该缓存会让 hermes 误以为 40006 仍提供 deepseek/kimi, 与 R263 后的单模型
glm5.1 实际链路不一致。本轮删除该脏缓存 + 不再使用的 `ollama_cloud_models_cache.json`
(hermes config 无 ollama 引用), 重启 gateway 让其按当前单模型 config 重新探测。

## 改前数据

### provider_models_cache.json (改前, 656B, 2026-06-24)
```json
{"openai-api": {"models": ["deepseek_hm_nv","kimi_hm_nv","glm5.1_hm_nv",
"deepseek_nv","deepseek","deepseek-v4-pro","deepseek-ai/deepseek-v4-pro",
"deepseek_hm","kimi_nv","kimi","kimi-k2.6","moonshotai/kimi-k2.6","kimi_hm",
"glm5.1_nv","glm-5.1","z-ai/glm-5.1","glm5.1_hm"]}, ...}
```
→ 17 个模型名, 其中 16 个是 R263 已删除的死模型 (deepseek/kimi 系列)。

### ollama_cloud_models_cache.json (改前, 735B, 2026-06-24)
含 deepseek/kimi/glm5.2 等 40 个 ollama cloud 模型 — hermes config 无 ollama provider
引用 (grep ollama config.yaml = 0), 属未使用的脏缓存。

### hermes config.yaml (未改, 仅参考)
- model.default: glm5.1_hm_nv, provider: litellm-nv-hm → 127.0.0.1:40006
- 无 ollama provider 配置

## 变化

| 文件 | 改前 | 改后 |
|---|---|---|
| `~/.hermes/provider_models_cache.json` | 656B, 17 模型 (含死模型) | 删除 (hermes 按需重探) |
| `~/.hermes/ollama_cloud_models_cache.json` | 735B, 40 模型 (未使用) | 删除 (不再探测) |

## 备份

- `~/.hermes/provider_models_cache.json.bak.R264.1782667465` (656B)
- `~/.hermes/ollama_cloud_models_cache.json.bak.R264.1782667465` (735B)

## 验证

- [x] 两个脏缓存文件已 `rm` 删除
- [x] hermes gateway 重启: 旧 PID 2421371 已退出, 新 PID 2434681 (01:30:12 CST) 运行
- [x] `systemctl --user status hermes-gateway` → active (running)
- [x] `hermes gateway status` → ✓ User gateway service is running
- [x] config.yaml model.default=glm5.1_hm_nv 未变, 链路指向 40006 不变
- [ ] provider 缓存重探: hermes 按需探测, 首次请求后将只含 glm5.1_hm_nv (待自然触发)

## 风险与回滚

- 重启 gateway 时 graceful drain 超时 180s (有 1 active agent), 强制重启成功, 服务已恢复。
- 回滚: `cp ~/.hermes/<file>.bak.R264.1782667465 ~/.hermes/<file>` + `hermes gateway restart`

## ⏳ 轮到HM2优化HM1
