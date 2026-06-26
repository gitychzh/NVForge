#!/usr/bin/env python3
import os, sys, json, http.server, socketserver
from urllib.request import Request, urlopen, ProxyHandler as UProxyHandler, build_opener
from urllib.error import HTTPError, URLError
import time

LP = int(os.environ.get("LISTEN_PORT", "4000"))
LH = os.environ.get("LISTEN_HOST", "0.0.0.0")
UT = int(os.environ.get("UPSTREAM_TIMEOUT", 120))
AK = os.environ.get("LITELLM_API_KEY", "")
AB = os.environ.get("LITELLM_API_BASE", "https://integrate.api.nvidia.com/v1")
MN = os.environ.get("LITELLM_MODEL_NAME", "glm5.1_hm_nv")
SP = os.environ.get("SOCKS5_PROXY_URL", "")
CU = AB.rstrip("/") + "/chat/completions"

def _opener():
    if SP:
        return build_opener(UProxyHandler({"http": SP, "https": SP}))
    return build_opener()

class H(http.server.BaseHTTPRequestHandler):
    def log_message(self, f, *a):
        if "health" not in str(a[0]):
            sys.stderr.write("[%s] %s
" % (LP, f % a))
    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status":"ok","model":MN}).encode())
            return
        self.send_error(404)
    def do_POST(self):
        if self.path != "/v1/chat/completions":
            self.send_error(404); return
        cl = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(cl)
        try:
            data = json.loads(body)
        except json.JSONDecodeError as e:
            self.send_error(400, str(e)); return
        t0 = time.time()
        try:
            pl = json.dumps(data).encode()
            opener = _opener()
            hdr = {"Content-Type":"application/json","Authorization":"Bearer "+AK}
            req = Request(CU, data=pl, headers=hdr)
            resp = opener.open(req, timeout=UT)
            rb = resp.read()
            self.send_response(resp.status)
            self.send_header("Content-Type","application/json")
            self.end_headers()
            self.wfile.write(rb)
            ms = (time.time()-t0)*1000
            sys.stderr.write("[%s] %d %.0fms
" % (LP, resp.status, ms))
        except HTTPError as e:
            ms = (time.time()-t0)*1000
            eb = e.fp.read() if e.fp else b"{}"
            try:
                ej = json.loads(eb)
            except:
                ej = {"error": str(e)}
            self.send_response(e.code)
            self.send_header("Content-Type","application/json")
            self.end_headers()
            self.wfile.write(json.dumps(ej).encode())
            sys.stderr.write("[%s] %d %.0fms
" % (LP, e.code, ms))
        except Exception as e:
            ms = (time.time()-t0)*1000
            self.send_error(502, str(e))
            sys.stderr.write("[%s] 502 %.0fms %s
" % (LP, ms, e))

class S(socketserver.ThreadingMixIn, http.server.HTTPServer):
    allow_reuse_address = True
    daemon_threads = True

if __name__ == "__main__":
    srv = S((LH, LP), H)
    sys.stderr.write("[%s] === start ===
" % LP)
    sys.stderr.write("[%s] model=%s base=%s
" % (LP, MN, AB))
    sys.stderr.write("[%s] proxy=%s
" % (LP, SP or "direct"))
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        srv.shutdown()
