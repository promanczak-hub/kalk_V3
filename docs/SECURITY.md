# Security Model — kalk_v3

> [!CAUTION]
> **Read this before changing anything in `auth_middleware.py`, the Supabase RLS policies, or the FE Supabase client.**
> The current security model is **deliberately permissive** for internal-tool deployment. Hardening it without coordinating BE + FE + DB will break the application.

---

## Current state (2026-05-19)

| Layer | Posture | Notes |
|---|---|---|
| **FastAPI app auth** | OPTIONAL — `AUTH_ENABLED=false` by default | `core/auth_middleware.py` enforces JWT only when `AUTH_ENABLED=true` |
| **App-level RBAC** | DEFINED but UNUSED | `require_role()` factory exists; **no route uses it** |
| **Supabase anon JWT** | USED EVERYWHERE | Frontend `supabaseClient.ts` ships anon key in browser; backend uses anon key for ~94 imports |
| **RLS policies** | UNKNOWN from code | DB-side; not audited in this pass |
| **Direct FE writes** | ALLOWED on `vehicle_synthesis` | 16+ call sites perform `update/delete/insert` directly via anon key (see §3) |
| **Rate limiting** | NONE | No middleware on hot endpoints (extraction, matrix builds, `/api/pdf-proxy`) |
| **Security headers** | BASELINE (added 2026-05-19) | `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `HSTS` |
| **PDF proxy** | HARDENED (added 2026-05-19) | https-only, host allow-list, 50 MB cap, content-type validation |
| **Prompt injection** | GUARDED (added 2026-05-19) | Prefix in `MASTER_PROMPT_V2` / `FALLBACK_STRUCTURED_PROMPT_FLASH` |

---

## 1. AUTH_ENABLED toggle — exposure analysis

[`backend/core/auth_middleware.py:22`](../backend/core/auth_middleware.py)

```python
AUTH_ENABLED: bool = os.environ.get("AUTH_ENABLED", "false").lower() == "true"
```

[`backend/main.py:33`](../backend/main.py):
```python
app = FastAPI(
    title="kalk_v3 API",
    version="3.0.0",
    dependencies=[Depends(get_current_user)],
)
```

**Behavior:**
- `get_current_user()` is wired as a global dependency.
- When `AUTH_ENABLED=false`: returns `None` immediately (line 73-74), all routes are **publicly callable**.
- When `AUTH_ENABLED=true`: returns the JWT-decoded `AuthUser` or raises 401.
- `require_role(*roles)` also short-circuits to allow when `AUTH_ENABLED=false` (line 107-108).
- **No route currently uses `require_role()`** — so even in "secure" mode, every authenticated user has equal privileges; there is no admin/operator/viewer differentiation in practice.

**Implication:** Flipping `AUTH_ENABLED=true` without first decorating sensitive routes with `require_role("admin")` would only verify the JWT signature — any authenticated user could still call `/api/extract/delete-vehicle`, `/api/control-center/*`, etc.

**Recommended hardening path** (in order):
1. **Add `require_role("admin")` to admin-only routes** before flipping the toggle:
   - `admin_routes.py` (cache invalidation, audit endpoints)
   - `control_center_routes.py` (POST/PUT — read can stay open)
   - `features_admin_routes.py`
   - `kalkulacje_routes.py` DELETE/duplicate endpoints
   - `extract_routes.py` `delete-vehicle`, `feedback`, HITL apply
2. **Verify all FE call sites attach the Bearer token.** Current `apiClient.ts` doesn't auto-attach Authorization — needs a session-token integration with Supabase Auth.
3. **Set `AUTH_ENABLED=true`** in staging, run smoke tests, then prod.
4. **Switch FE direct Supabase writes** (§3) to use the authenticated session client, not the anon key.

---

## 2. Anon Supabase JWT — exposure analysis

The anon JWT is **public by design** — it's a Supabase identifier that lets clients hit PostgREST. It carries no permissions on its own; access is gated by RLS.

[`frontend/src/lib/supabaseClient.ts`](../frontend/src/lib/supabaseClient.ts) ships it in the browser bundle (`VITE_SUPABASE_ANON_KEY`). This is correct.

Backend uses the same anon key (memory `backend_uses_anon_key_primary`, 94 imports). For a backend, this is unusual — backends typically use the **service role key** for trusted operations. Using anon means the backend is also subject to RLS as if it were a public client.

**Implication:** Tightening RLS to "deny-all-by-default" would break **both** FE and BE simultaneously. Any tightening needs:
1. RLS policy review — list every table and write the policy that the current code actually depends on
2. Some sites (e.g. matrix cache writes, control_center updates) probably need to switch to `get_admin_client()` (service-role)
3. Test plan covering every FE write path AND every BE fetch

---

## 3. Direct FE → Supabase writes (16+ call sites)

These bypass the FastAPI validation layer entirely. They work today because RLS isn't enforcing per-row ownership. They will break the moment RLS is tightened.

| File | Line | Operation |
|---|---|---|
| `useDocumentProcessing.ts` | 78 | `update` `vehicle_synthesis` |
| `useDocumentProcessing.ts` | 117-118 | `insert` `vehicle_synthesis` |
| `useDocumentProcessing.ts` | 175-176 | `update` `vehicle_synthesis` (error fallback) |
| `useDocumentProcessing.ts` | 260-261 | `insert` `vehicle_synthesis` |
| `useDocumentProcessing.ts` | 305 | `update` `vehicle_synthesis` |
| `useVehicleDataSync.ts` | 105-106 | `update` (bulk column updates) |
| `useVehicleDataSync.ts` | 150-151 | `update` `synthesis_data` |
| `useVehicleFinancing.ts` | 264-265 | `update` `synthesis_data` |
| `useVehicleMetaManager.ts` | 34-35, 69-70, 98-99, 140-141, 167-168, 194-195, 220-…| `update` `synthesis_data` (×7) |
| `useVehicleOptionsManager.ts` | 281-283 | `update` `synthesis_data` |
| `VehicleRowCard.tsx` | 605 | **`delete` `vehicle_synthesis`** (fallback when `/api/extract/delete-vehicle` fails) |
| `CalculationsHistoryPage.tsx` | 300-301 | `update` `synthesis_data` (remove `calculator_setup`) |

**Most concerning:** `VehicleRowCard.tsx:605` is a **delete fallback** when the API is unavailable. If RLS allows the anon key to delete any row in `vehicle_synthesis`, this is the broadest exposure: a compromised browser session can wipe the table.

**Recommended remediation (per direction):**
- **Short term:** Verify RLS at minimum requires `auth.role() = 'authenticated'` for `vehicle_synthesis` writes (this would still allow anon since we have no auth). Confirm with Supabase SQL Editor.
- **Medium term:** Move each write to a backend endpoint with input validation. Backend uses `get_admin_client()` when it needs to bypass user-row RLS.
- **Long term:** Pair the auth rollout (§1) with switching `supabaseClient.ts` to use the session-scoped client per logged-in user, then enforce per-row ownership via RLS `auth.uid() = owner_id`.

---

## 4. What was hardened in 2026-05-19 audit pass

- ✅ **Stripped tracebacks from HTTP 500 responses** in `extract_routes.py:1215` (information disclosure)
- ✅ **`/api/pdf-proxy` SSRF hardening** — https-only, host allow-list, 50 MB cap, timeouts
- ✅ **Prompt injection guard** added to extraction prompts
- ✅ **Hardcoded `postgres` password** in `add_insurance_params.py` replaced with env-var with explicit error
- ✅ **Security headers middleware** (`X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `HSTS`)
- ✅ **axios CVE upgrade** to 1.16.1 (SSRF, prototype pollution, CRLF injection)
- ✅ **`npm audit fix`** — 12 transitive vulns → 6 (remaining 6 all in `xlsx`, no upstream fix; library migration tracked separately)

## 5. What's still open

- ⚠️ `AUTH_ENABLED` toggle and the lack of `require_role()` enforcement (§1)
- ⚠️ Anon-key writes from FE (§3) and lack of RLS policy audit
- ⚠️ `xlsx` library proto pollution / ReDoS — needs library migration (e.g. SheetJS Pro, `exceljs`)
- ⚠️ No rate limiting (DoS risk on Vertex extraction and `/api/pdf-proxy`)
- ⚠️ Sensitive data potentially in logs (no PII scrubbing on `logger.exception` calls)
- ⚠️ File upload — no per-user quota, only MIME validation
