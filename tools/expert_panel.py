#!/usr/bin/env python3
"""专家评审委员会 — 盲审回合（streaming 版本）

4个模型并行评审双机模型链路优化方向。
所有 nv_gw API 调用改为 stream=True，用 SSE 解析累积 content 和
reasoning_content，规避 DS V4 Pro 502 / MiniMax M3 超时（NVCF 只支持 streaming）。

可复用入口：call_model_streaming(model_id, prompt, max_tokens=8192, timeout=180)
"""
import json
import time
import concurrent.futures
import urllib.request

API_URL = "http://127.0.0.1:40006/v1/chat/completions"
API_KEY = "nv-gw-token"

EXPERTS = {
    "glm5_2_nv": {
        "role": "架构师",
        "focus": "技术选型、模块划分、整体设计",
        "questions": "1. 当前架构的核心问题（按严重程度排序）\n2. 对每个优化方向的评估（支持/反对/有条件支持，附理由）\n3. 你认为缺失的优化方向（如果有的话）\n4. 优先级排序：先做什么，后做什么",
    },
    "dsv4p_nv": {
        "role": "安全与逻辑审查官",
        "focus": "找漏洞、边界条件、风险点",
        "questions": "1. 当前配置中的风险点\n2. 对每个优化方向的风险评估\n3. 缺失的安全措施\n4. 最危险的3个问题（按故障概率排序）",
    },
    "kimi_nv": {
        "role": "完整性检查员",
        "focus": "扫遗漏、需求覆盖度、文档审阅",
        "questions": "1. 材料中遗漏了哪些关键信息\n2. 优化方向中遗漏的场景\n3. 双机差异中未提到但可能重要的点\n4. 哪些方向描述不够清晰",
    },
    "minimax_m3_nv": {
        "role": "可行性评估专家",
        "focus": "实施难度、成本、是否过度设计",
        "questions": "1. 每个优化方向的实施难度（低/中/高）和预估工作量\n2. 哪些方向有过度设计风险\n3. 哪些方向应立即执行（低成本高收益）\n4. 建议的分阶段实施计划",
    },
}


def call_model_streaming(model_id, prompt, max_tokens=8192, timeout=180):
    """流式调用单个模型，返回累积的 content / reasoning_content。

    用 SSE 解析 nv_gw 的 streaming response：
      data: {"choices":[{"delta":{"content":"...","reasoning_content":"..."}}], ...}
      data: [DONE]

    返回 dict：
      model / content / reasoning_content / finish_reason / elapsed_s / usage / error
    流式调用等价于非流式的最终结果（流结束时返回完整 content）。
    """
    body = json.dumps({
        "model": model_id,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "stream": True,
    }).encode()

    req = urllib.request.Request(API_URL, data=body, headers={
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
    })

    start = time.time()
    content_parts = []
    reasoning_parts = []
    finish_reason = None
    usage = {}

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            for raw in resp:
                # SSE 行：跳过空行和注释行
                line = raw.decode("utf-8", errors="replace").rstrip("\n").rstrip("\r")
                if not line:
                    continue
                if line.startswith(":"):  # SSE comment / heartbeat
                    continue
                if not line.startswith("data:"):
                    continue
                data_str = line[len("data:"):].lstrip()
                if data_str == "[DONE]":
                    break
                try:
                    chunk = json.loads(data_str)
                except json.JSONDecodeError:
                    # 偶发不完整 chunk，跳过
                    continue
                choices = chunk.get("choices") or []
                if choices:
                    delta = choices[0].get("delta", {}) or {}
                    if delta.get("content"):
                        content_parts.append(delta["content"])
                    if delta.get("reasoning_content"):
                        reasoning_parts.append(delta["reasoning_content"])
                    if choices[0].get("finish_reason"):
                        finish_reason = choices[0]["finish_reason"]
                if chunk.get("usage"):
                    usage = chunk["usage"]

        elapsed = time.time() - start
        content = "".join(content_parts)
        reasoning = "".join(reasoning_parts)
        return {
            "model": model_id,
            "content": content,
            "reasoning_content": reasoning,
            "reasoning_preview": reasoning[:300] if reasoning else None,
            "finish_reason": finish_reason or "?",
            "elapsed_s": round(elapsed, 1),
            "usage": usage,
            "error": None,
        }
    except Exception as e:
        elapsed = time.time() - start
        return {
            "model": model_id,
            "content": "".join(content_parts),
            "reasoning_content": "".join(reasoning_parts),
            "reasoning_preview": None,
            "finish_reason": finish_reason,
            "elapsed_s": round(elapsed, 1),
            "usage": usage,
            "error": str(e),
        }


def _build_prompt(expert_cfg, material):
    return f"""你是{expert_cfg['role']}，专注于{expert_cfg['focus']}。

请审阅以下双机模型链路现状材料，回答：
{expert_cfg['questions']}

要求：直接给结论，不要废话。每个观点不超过3句话。

=== 评审材料 ===
{material}"""


def run_review(material_path="/tmp/expert_review_material.md", max_tokens=8192, timeout=180):
    """读取材料，4 模型并行盲审，打印结果并保存 JSON。"""
    with open(material_path) as f:
        material = f.read()

    print("开始4模型并行盲审（streaming）...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = {
            executor.submit(
                call_model_streaming,
                model_id,
                _build_prompt(cfg, material),
                max_tokens,
                timeout,
            ): model_id
            for model_id, cfg in EXPERTS.items()
        }
        results = []
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            results.append(result)
            status = "✅" if result.get("content") else "❌"
            print(f"  {status} {result['model']} — {result['elapsed_s']}s — finish={result.get('finish_reason','ERR')}")

    # 按 EXPERTS 顺序排序输出
    results.sort(key=lambda x: list(EXPERTS.keys()).index(x["model"]))

    print("\n" + "=" * 80)
    for r in results:
        print(f"\n=== {r['model']} — {EXPERTS[r['model']]['role']} ({r['elapsed_s']}s) ===")
        if r.get("error"):
            print(f"ERROR: {r['error']}")
        else:
            print(r.get("content", "NO CONTENT"))
            if r.get("reasoning_preview"):
                print(f"\n[reasoning: {r['reasoning_preview']}...]")
            print(f"\n[finish={r.get('finish_reason')} usage={r.get('usage')}]")

    with open("/tmp/expert_review_results.json", "w") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n结果已保存到 /tmp/expert_review_results.json")
    return results


def _self_test():
    """--test：4 模型 streaming 调用一个最小 prompt，验证链路通畅。"""
    MODELS = ["glm5_2_nv", "dsv4p_nv", "kimi_nv", "minimax_m3_nv"]
    PROMPT = "你是测试专家。请回答：1+1=?。只回答数字。"
    print("self-test: 4 模型 streaming 最小 prompt 调用...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
        futures = {ex.submit(call_model_streaming, m, PROMPT, 200, 60): m for m in MODELS}
        ok = 0
        for f in concurrent.futures.as_completed(futures):
            m = futures[f]
            try:
                r = f.result()
                if r.get("content"):
                    ok += 1
                    print(f"  ✅ {m}: OK — {r['content'][:30]!r} — {r['elapsed_s']}s")
                else:
                    print(f"  ❌ {m}: FAIL — {r.get('error')}")
            except Exception as e:
                print(f"  ❌ {m}: EXCEPTION — {e}")
    print(f"\nself-test 结果: {ok}/{len(MODELS)} 成功")
    return ok == len(MODELS)


if __name__ == "__main__":
    import sys
    if "--test" in sys.argv:
        ok = _self_test()
        sys.exit(0 if ok else 1)
    run_review()
