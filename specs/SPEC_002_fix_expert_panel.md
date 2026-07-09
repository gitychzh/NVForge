# SPEC-002: 修复专家评审委员会两个阻断问题

## 背景
首次专家评审测试（2026-07-10）发现两个阻断问题：
1. DS V4 Pro 和 MiniMax M3 在非流式+长prompt时 502/超时 — NVCF 只支持 streaming
2. OpenClaw 未注册 kimi_nv 和 minimax_m3_nv — 无法通过 sessions_spawn 使用

## 任务一：补注册模型到 OpenClaw 配置

修改 `~/.openclaw/openclaw.json`，在 `models.providers.nv_gw.models` 数组中添加两个模型：

### kimi_nv
```json
{
  "id": "kimi_nv",
  "name": "Kimi K2.6 (NVCF nvquery-kimi-k2_6 f966661c via nv_gw, thinking enabled)",
  "contextWindow": 131072,
  "reasoning": true,
  "compat": {
    "supportsReasoningEffort": true,
    "supportedReasoningEfforts": ["off", "low", "medium", "high"],
    "thinkingFormat": "reasoning_content"
  },
  "maxTokens": 32768
}
```

### minimax_m3_nv
```json
{
  "id": "minimax_m3_nv",
  "name": "MiniMax M3 (NVCF ai-minimax-m3 87ea0ddc via nv_gw, thinking enabled)",
  "contextWindow": 131072,
  "reasoning": true,
  "compat": {
    "supportsReasoningEffort": true,
    "supportedReasoningEfforts": ["off", "low", "medium", "high"],
    "thinkingFormat": "reasoning_content"
  },
  "maxTokens": 32768
}
```

同时在 `agents.defaults.models` 中添加这两个模型的 alias：
```json
"nv_gw/kimi_nv": {
  "alias": "Kimi K2.6 (NVCF nvquery-kimi-k2_6 f966661c via nv_gw, thinking enabled)"
},
"nv_gw/minimax_m3_nv": {
  "alias": "MiniMax M3 (NVCF ai-minimax-m3 87ea0ddc via nv_gw, thinking enabled)"
}
```

## 任务二：补注册 minimax_m3_nv 到 Hermes 配置

修改 `~/.hermes/config.yaml`，在 `providers.nv_gw.models` 下添加：
```yaml
      minimax_m3_nv:
        max_tokens: 32768
        supports_thinking: true
        supports_vision: false
```

## 任务三：修复专家评审脚本改 streaming 模式

现有脚本 `/tmp/expert_review.py` 使用非流式 `stream=False` 调用 nv_gw，导致 DS V4 Pro 502 和 MiniMax M3 超时。

修复为 streaming 模式：
1. 所有 API 调用改为 `stream=True`
2. 用 SSE 解析读取 streaming response，累积 content 和 reasoning_content
3. 流结束时返回完整的 content（等价于非流式的最终结果）
4. 保留并行调用4模型的 ThreadPoolExecutor 架构
5. 每个模型设 timeout=180s（streaming 首字节快，但总时间可能长）

修复后的脚本放到 `~/cc_ps/NVForge/NVForge/tools/expert_panel.py`（创建 tools/ 目录）。
同时保留一个可复用的 `call_model_streaming(model_id, prompt, max_tokens=8192, timeout=180)` 函数。

## 任务四：验证

### 4.1 验证模型注册
```bash
# 重启 OpenClaw 前先验证 JSON 合法
python3 -c "import json; json.load(open('/home/opc_uname/.openclaw/openclaw.json')); print('OK')"

# 重启 OpenClaw gateway
systemctl --user restart openclaw-gateway
sleep 3
systemctl --user status openclaw-gateway | head -5

# 验证模型已注册
curl -s http://127.0.0.1:18789/v1/models | python3 -c "
import sys, json
d = json.load(sys.stdin)
for m in d.get('data', []):
    print(m['id'])
" 2>/dev/null || echo "gateway API not available, check config manually"
```

### 4.2 验证 Hermes 配置
```bash
# Hermes 不需要重启（config 热加载），但验证 YAML 合法
python3 -c "import yaml; yaml.safe_load(open('/home/opc_uname/.hermes/config.yaml')); print('YAML OK')"
```

### 4.3 验证 streaming 评审脚本
```bash
cd ~/cc_ps/NVForge/NVForge/tools
python3 -c "
from expert_panel import call_model_streaming
import concurrent.futures

MODELS = ['glm5_2_nv', 'dsv4p_nv', 'kimi_nv', 'minimax_m3_nv']
PROMPT = '你是测试专家。请回答：1+1=?。只回答数字。'

with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
    futures = {ex.submit(call_model_streaming, m, PROMPT, 200, 60): m for m in MODELS}
    for f in concurrent.futures.as_completed(futures):
        m = futures[f]
        try:
            r = f.result()
            print(f'{m}: OK — {r.get(\"content\",\"\")[:30]} — {r.get(\"elapsed_s\")}s')
        except Exception as e:
            print(f'{m}: FAIL — {e}')
"
```

### 4.4 端到端验证
```bash
# 用修复后的脚本跑一次完整的4模型盲审
python3 ~/cc_ps/NVForge/NVForge/tools/expert_panel.py --test
```
（如果 expert_panel.py 有 --test 参数就跑，没有就跳过这步）

### 4.5 也可用 sessions_spawn 验证 OpenClaw 模型注册
在 OpenClaw 重启后，通过 sessions_spawn 用不同 model 参数 spawn 4个模型，各发一个简单任务验证。

## 约束

- 只改本机配置文件（openclaw.json, hermes config.yaml）
- 不改容器配置，不碰远程 opc2
- 不改 nv_gw 容器内部代码
- 修改 openclaw.json 前先备份：`cp ~/.openclaw/openclaw.json ~/.openclaw/openclaw.json.bak.$(date +%Y%m%d%H%M%S)`
- 修改 hermes config.yaml 前先备份：`cp ~/.hermes/config.yaml ~/.hermes/config.yaml.bak.$(date +%Y%m%d%H%M%S)`
- 重启 OpenClaw gateway 前验证 JSON 合法
- 所有修改写入 NVForge 仓库并 commit
