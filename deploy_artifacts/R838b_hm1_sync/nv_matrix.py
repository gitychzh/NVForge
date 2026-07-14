#!/usr/bin/env python3
"""NV 4模型 × (pexec/integrate) × (direct/5IP) × 3次 矩阵测试.
直打 NVCF/integrate 端点, 绕过 nv_gw 路由, 隔离每组合. 串行低并发.
自动从容器取 keys, 自动实测每端口 egress IP. 两机自适应."""
import json, time, urllib.request, urllib.error, ssl, subprocess, sys, os
from collections import defaultdict

_out = subprocess.check_output(["docker","exec","nv_gw","python3","-c",
    "from gateway.config import NVU_KEYS; print('|'.join(NVU_KEYS))"],
    text=True, stderr=subprocess.DEVNULL).strip()
KEYS = _out.split("|")
assert len(KEYS) >= 5, f"keys load failed: {len(KEYS)}"

MODELS = [
    ("kimi_nv",   "f966661c-790d-4f71-b973-c525fb8eafd4", "moonshotai/kimi-k2.6"),
    ("dsv4p_nv",  "74f02205-c7ba-438f-b81a-2537955bd7ec", "deepseek-ai/deepseek-v4-pro"),
    ("glm5_2_nv", "3b9748d8-1d85-40e8-8573-0eeaa63a4b63", "z-ai/glm-5.2"),
    ("minimax_m3_nv", "87ea0ddc-cff1-4bca-bf8b-3bd98a35ddd0", "minimaxai/minimax-m3"),
]
PORTS = ["direct", "7894", "7895", "7896", "7897", "7899"]
PEXEC_URL = "https://api.nvcf.nvidia.com/v2/nvcf/pexec/functions/{fid}"
INTEG_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
ctx = ssl.create_default_context()
https_h = urllib.request.HTTPSHandler(context=ctx)

def measure_egress(port):
    if port == "direct": return "(host-direct)"
    ph = urllib.request.ProxyHandler({"http":f"http://127.0.0.1:{port}","https":f"http://127.0.0.1:{port}"})
    op = urllib.request.build_opener(ph, https_h)
    try:
        with op.open(urllib.request.Request("https://api.ipify.org"), timeout=8) as r:
            return r.read().decode().strip()
    except Exception as e:
        return f"err:{str(e)[:20]}"

EGRESS_IP = {p: measure_egress(p) for p in PORTS}
print("=== egress IP map ===", flush=True)
for p, ip in EGRESS_IP.items(): print(f"  {p}: {ip}", flush=True)

def req_once(url, headers, body, port, timeout=60):
    if port == "direct":
        opener = urllib.request.build_opener(https_h)
    else:
        ph = urllib.request.ProxyHandler({"http":f"http://127.0.0.1:{port}","https":f"http://127.0.0.1:{port}"})
        opener = urllib.request.build_opener(ph, https_h)
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=headers, method="POST")
    t0 = time.time()
    try:
        with opener.open(req, timeout=timeout) as r:
            data = r.read(); code = r.status
            try:
                j = json.loads(data); ch = j.get("choices",[])
                content = ch[0].get("message",{}).get("content","") if ch else ""
                tok = j.get("usage",{}).get("total_tokens",0)
            except: content, tok = "", 0
            empty = (code==200 and len(str(content))<5 and tok==0)
            return code, round(time.time()-t0,2), len(str(content)), tok, empty
    except urllib.error.HTTPError as e:
        return e.code, round(time.time()-t0,2), 0, 0, False
    except Exception as e:
        return "ERR:"+str(e)[:40], round(time.time()-t0,2), 0, 0, False

N = 3
results = []
total = len(MODELS)*2*len(PORTS)*N
i = 0
for tier, fid, mid in MODELS:
    for ch_name in ["pexec","integrate"]:
        for port in PORTS:
            for rep in range(N):
                i += 1
                key = KEYS[rep % 5]
                url = PEXEC_URL.format(fid=fid) if ch_name=="pexec" else INTEG_URL
                body = {"model":mid, "messages":[{"role":"user","content":"Say hi briefly"}], "max_tokens":20}
                headers = {"Authorization":f"Bearer {key}","Content-Type":"application/json"}
                code, t, clen, tok, empty = req_once(url, headers, body, port)
                results.append({"tier":tier,"ch":ch_name,"port":port,"egress":EGRESS_IP[port],
                                 "rep":rep+1,"code":str(code),"t":t,"clen":clen,"tok":tok,"empty":empty})
                print(f"[{i}/{total}] {tier:14s} {ch_name:9s} {port:7s} r{rep+1}: {str(code):>6} {t:>5}s len={clen:>4} tok={tok:>4} empty={empty}", flush=True)

print("\n=== SUMMARY ===", flush=True)
agg = defaultdict(lambda:{"ok":0,"total":0,"empty":0,"err":0,"times":[]})
for r in results:
    k=f"{r['tier']}|{r['ch']}|{r['port']}({r['egress']})"
    agg[k]["total"]+=1
    if r["code"]=="200" and not r["empty"]: agg[k]["ok"]+=1; agg[k]["times"].append(r["t"])
    elif r["code"]=="200" and r["empty"]: agg[k]["empty"]+=1
    else: agg[k]["err"]+=1
for k in sorted(agg):
    v=agg[k]
    avg=round(sum(v["times"])/len(v["times"]),2) if v["times"] else 0
    print(f"  {k:52s} ok={v['ok']}/{v['total']} empty={v['empty']} err={v['err']} avg_ok={avg}s", flush=True)

json.dump({"egress_map":EGRESS_IP,"results":results}, open("/tmp/nv_matrix_results.json","w"), indent=1)
print("\nresults saved /tmp/nv_matrix_results.json", flush=True)
