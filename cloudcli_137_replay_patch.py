#!/usr/bin/env python3
"""Patch cloudcli 1.37.0 on HM2 — replay 4 patches from 1.36.3.

Patches:
  1. R2254: idle-stream watchdog (claude-runtime.provider.js)
  2. R-nopasswd: platform mode skip password (auth.service.js)
  3. R-autologin: bootstrap token injection (dist/index.html)
  4. R-font-restore v2: system sans-serif + chat fullwidth (dist/index.html + sw.js CACHE bump)
"""
import sys, os, re

CD = os.path.expanduser("~/.npm-global/lib/node_modules/@cloudcli-ai/cloudcli")
errors = []

def patch_file(path, old, new, label):
    full = os.path.join(CD, path)
    with open(full, "r", encoding="utf-8") as f:
        content = f.read()
    count = content.count(old)
    if count == 0:
        print(f"[SKIP] {label}: anchor not found in {path} (already patched?)")
        return False
    if count > 1:
        print(f"[WARN] {label}: anchor found {count} times in {path}, patching first occurrence")
    content = content.replace(old, new, 1)
    with open(full, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"[OK]   {label}: patched {path}")
    return True

# ─── Patch 1: R2254 idle-watchdog (claude-runtime.provider.js) ───────────────
RUNTIME = "dist-server/server/modules/providers/list/claude/claude-runtime.provider.js"

# 1a. Inject STREAM_IDLE_TIMEOUT_MS constant after TOOLS_REQUIRING_INTERACTION
old_const = "const TOOLS_REQUIRING_INTERACTION = new Set(['AskUserQuestion', 'ExitPlanMode']);"
new_const = old_const + """
// R2254: idle-stream watchdog. If the SDK async generator produces no message for this many
// milliseconds, the upstream LLM stream is considered hung (observed: NVCF glm5.2 TTFB >60s
// -> cc4101 RST -> SDK generator stalls on the next `await` forever, process zombies in ep_poll).
// On timeout we call queryInstance.interrupt() so the generator throws/ends and the normal
// completion/error cleanup runs. 0 = disabled (legacy behavior). Default 120s covers normal
// glm5.2 TTFB (p99 ~66s) with margin; raise via env if false-positive interrupts appear.
const STREAM_IDLE_TIMEOUT_MS = parseInt(process.env.CLAUDE_STREAM_IDLE_TIMEOUT_MS, 10) || 120000;"""
patch_file(RUNTIME, old_const, new_const, "R2254-const")

# 1b. Replace `for await (const message of queryInstance) {` with while+idle-race
old_for = """        for await (const message of queryInstance) {
            // Capture session ID from first message"""
new_for = """        let _streamIdleTimedOut = false;
        while (!_streamIdleTimedOut) {
            let _idleTimer = null;
            const _idlePromise = new Promise((resolve) => {
                _idleTimer = setTimeout(() => resolve('__idle_timeout__'), STREAM_IDLE_TIMEOUT_MS);
            });
            const _next = Promise.race([queryInstance.next().then(m => ({ done: m.done, value: m.value })), _idlePromise]);
            const _result = await _next;
            if (_result === '__idle_timeout__') {
                _streamIdleTimedOut = true;
                console.error(`[R2254-WATCHDOG] session ${capturedSessionId || sessionId || 'NEW'} idle ${STREAM_IDLE_TIMEOUT_MS}ms, calling interrupt() (upstream stream stall)`);
                try { await queryInstance.interrupt(); } catch (e) { console.error('[R2254-WATCHDOG] interrupt() threw:', e?.message || e); }
                clearTimeout(_idleTimer);
                break;
            }
            clearTimeout(_idleTimer);
            if (_result.done) break;
            const message = _result.value;

            // Capture session ID from first message"""
patch_file(RUNTIME, old_for, new_for, "R2254-for-await")

# ─── Patch 2: R-nopasswd (auth.service.js) ──────────────────────────────────
AUTH_SVC = "dist-server/server/modules/auth/auth.service.js"

# 2a. getStatus() — return token in platform mode
old_status = """        getStatus() {
            return {
                needsSetup: !dependencies.users.hasUsers(),
                isAuthenticated: false,
            };
        },"""
new_status = """        getStatus() {
            // R-nopasswd: platform mode mints a token for the first user so the SPA
            // can skip the login page entirely (backend already bypasses auth here).
            if (IS_PLATFORM && dependencies.users.hasUsers()) {
                const u = dependencies.users.getUserByUsername('admin') || dependencies.users.getFirstUser();
                const token = u ? dependencies.generateToken(u) : null;
                return { needsSetup: false, isAuthenticated: true, token };
            }
            return {
                needsSetup: !dependencies.users.hasUsers(),
                isAuthenticated: false,
            };
        },"""

# Need to import IS_PLATFORM — check if it's available
# auth.service.js receives dependencies, IS_PLATFORM is in auth.middleware.js
# We'll inject it via the service factory or use process.env directly
# Actually simpler: just use process.env.VITE_IS_PLATFORM === 'true' inline
new_status = """        getStatus() {
            // R-nopasswd: platform mode mints a token for the first user so the SPA
            // can skip the login page entirely (backend already bypasses auth here).
            const _IS_PLATFORM = process.env.VITE_IS_PLATFORM === 'true';
            if (_IS_PLATFORM && dependencies.users.hasUsers()) {
                const users = dependencies.users;
                let u = null;
                try { u = users.getUserByUsername('admin'); } catch(e) {}
                if (!u) { u = users.getFirstUser ? users.getFirstUser() : null; }
                const token = u ? dependencies.generateToken(u) : null;
                return { needsSetup: false, isAuthenticated: true, token };
            }
            return {
                needsSetup: !dependencies.users.hasUsers(),
                isAuthenticated: false,
            };
        },"""
patch_file(AUTH_SVC, old_status, new_status, "R-nopasswd-getStatus")

# 2b. login() — skip password check in platform mode
old_login_check = """            const user = dependencies.users.getUserByUsername(username);
            const validPassword = user
                ? await dependencies.comparePassword(password, user.password_hash)
                : false;
            if (!user || !validPassword) {
                throw new AppError('Invalid username or password', {
                    code: 'AUTH_INVALID_CREDENTIALS',
                    statusCode: 401,
                });
            }"""
new_login_check = """            // R-nopasswd: platform mode skips password verification entirely.
            const _IS_PLATFORM = process.env.VITE_IS_PLATFORM === 'true';
            if (_IS_PLATFORM) {
                const user = dependencies.users.getUserByUsername(username);
                if (!user) {
                    // fallback: try first user if username is non-empty
                    const first = dependencies.users.getFirstUser ? dependencies.users.getFirstUser() : null;
                    if (!first) {
                        throw new AppError('Platform mode: No user found in database', {
                            code: 'AUTH_NO_USER',
                            statusCode: 500,
                        });
                    }
                    dependencies.users.updateLastLogin(numericUserId(first.id));
                    return {
                        success: true,
                        user: { id: first.id, username: first.username },
                        token: dependencies.generateToken(first),
                    };
                }
                dependencies.users.updateLastLogin(numericUserId(user.id));
                return {
                    success: true,
                    user: { id: user.id, username: user.username },
                    token: dependencies.generateToken(user),
                };
            }
            const user = dependencies.users.getUserByUsername(username);
            const validPassword = user
                ? await dependencies.comparePassword(password, user.password_hash)
                : false;
            if (!user || !validPassword) {
                throw new AppError('Invalid username or password', {
                    code: 'AUTH_INVALID_CREDENTIALS',
                    statusCode: 401,
                });
            }"""
patch_file(AUTH_SVC, old_login_check, new_login_check, "R-nopasswd-login")

# ─── Patch 3+4: R-autologin + R-font-restore (index.html + sw.js) ───────────
INDEX = "dist/index.html"
SW = "dist/sw.js"

# 3. R-autologin: inject bootstrap script before SPA
old_title = "    <title>CloudCLI UI</title>"
new_title = """    <script>/* R-autologin: platform-mode bootstrap. If no auth-token in localStorage, fetch /api/auth/status (returns a token in platform mode) and stash it before the SPA runs, so the login page is skipped. */(function(){try{if(localStorage.getItem("auth-token"))return;var x=new XMLHttpRequest();x.open("GET","/api/auth/status",false);x.send();if(x.status===200){var d=JSON.parse(x.responseText);if(d&&d.token){localStorage.setItem("auth-token",d.token);}}}catch(e){}})();</script>

    <title>CloudCLI UI</title>"""
patch_file(INDEX, old_title, new_title, "R-autologin")

# 4. R-font-restore v2: system sans-serif + chat fullwidth
# Inject <style> after </title> (which is now after the autologin script)
old_style_anchor = "    <title>CloudCLI UI</title>\n"
new_style_with_font = """    <title>CloudCLI UI</title>
    <style>/* R-font-restore v2: system sans-serif + chat messages fill main pane (old 1.33.2 feel). */
html,body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif!important}
.font-serif{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif!important}
/* 1.36+ added max-w-[54.25rem] on chat message container -> centered narrow w/ big side margins. old 1.33.2 had none. kill it. */
.max-w-\\[54\\.25rem\\]{max-width:none!important}
</style>
"""
# Check if the title line still has the font style anchor
# After R-autologin, the title line is still there — inject style after it
full_index = os.path.join(CD, INDEX)
with open(full_index, "r", encoding="utf-8") as f:
    idx_content = f.read()

if ".font-serif" not in idx_content:
    # Find the title line and inject style after it
    idx_content = idx_content.replace(
        '    <title>CloudCLI UI</title>\n',
        new_style_with_font,
        1
    )
    with open(full_index, "w", encoding="utf-8") as f:
        f.write(idx_content)
    print("[OK]   R-font-restore: patched index.html with <style>")
else:
    print("[SKIP] R-font-restore: index.html already has font style")

# 5. sw.js CACHE_NAME bump to v6-r-fullwidth (force SW cache invalidation)
full_sw = os.path.join(CD, SW)
with open(full_sw, "r", encoding="utf-8") as f:
    sw_content = f.read()
if "claude-ui-v6-r-fullwidth" in sw_content:
    print("[SKIP] sw.js CACHE_NAME already v6")
else:
    sw_content = sw_content.replace(
        "const CACHE_NAME = 'claude-ui-v2';",
        "const CACHE_NAME = 'claude-ui-v6-r-fullwidth';",
        1
    )
    # Also handle if it was already at v5
    sw_content = sw_content.replace(
        "const CACHE_NAME = 'claude-ui-v5-r-fullwidth';",
        "const CACHE_NAME = 'claude-ui-v6-r-fullwidth';",
        1
    )
    with open(full_sw, "w", encoding="utf-8") as f:
        f.write(sw_content)
    print("[OK]   sw.js CACHE_NAME bumped to v6-r-fullwidth")

print("\n=== Patch summary ===")
print("All 4 patches replayed on cloudcli 1.37.0")
