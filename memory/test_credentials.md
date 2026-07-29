# Test Credentials — RUI Explorer

## App
Portale di consultazione del Registro Unico degli Intermediari (RUI) IVASS.
Frontend URL: https://ivass-broker-finder.preview.emergentagent.com

## Auth
Two methods coexist (unified session-token cookie `session_token`, also accepts `Authorization: Bearer <token>`):
1. Email/password (JWT-style, custom) — `/api/auth/register`, `/api/auth/login`
2. Google social login (Emergent-managed) — `/api/auth/google/session`

### Personal intermediary exploration account (Flavio)
- Email: `flaviojcristiano@gmail.com`
- Password: `Flavio2026!`  (funziona anche con "Continua con Google" sulla stessa email)
- role "intermediary", is_pro true, RUI `A000011682` (CAPECCHI ANGIOLO E RAG.CARLO S.A.S., Agenti, Arezzo AR) — 3 mandati, 2 collaboratori. Profilo inizialmente vuoto (completezza 0%) per esplorare l'editor.
- Seeded idempotently (seed_test_accounts). Diverso dal MASTER admin (flavio.cristiano@22gmbh.com).

### PRO test accounts (email/password) — con TUTTE le funzionalità PRO attive
- Utente PRO: `utente.pro@test.com` / `TestPro2026!` (role "user", is_pro true)
- Intermediario PRO: `intermediario.pro@test.com` / `TestPro2026!` (role "intermediary", is_pro true, RUI A000101292 = ABADA ETTORE)
- Seeded idempotently at startup (seed_test_accounts). Password reset to this value on every restart.

### Admin PRO note
- The MASTER admin (and any role "admin") is treated as PRO everywhere: `public_user` returns is_pro=true for admins and `has_pro()` gates backend PRO features. This auto-unlocks all current AND future is_pro-gated features for admins.

### MASTER admin account (email/password) — role "admin"
- email: `flavio.cristiano@22gmbh.com`
- password: `C6sn-9C0C-aBeA`
- Full admin console at `/admin`: overview stats, user management (view all, suspend/reactivate, grant/revoke PRO, demote role, delete), audit activity log.
- Seeded idempotently at backend startup from MASTER_ADMIN_EMAIL / MASTER_ADMIN_PASSWORD in backend/.env.
- MASTER account cannot be modified/deleted via the admin API (self-protection).

### Test user (email/password) — role "user"
- email: `mario.test@example.com`
- password: `test1234`
- Can leave feedback/reviews on intermediary cards; has an /account page.

### Test intermediary (email/password) — role "intermediary"
- email: `agente.demo@example.com`
- password: `test1234`
- Claimed RUI: `A000109352` (AICARDI OSCAR, sezione A - Agenti)
- Has /intermediary-dashboard with stats, profile editor, feedback list.

Registration is role-aware: POST /api/auth/register {name,email,password,role,rui_number}
- role: "user" | "intermediary"
- For intermediary, rui_number MUST exist in db.intermediari else 400 "Numero RUI non trovato".

## Freemium
- Guests get `FREE_SEARCH_LIMIT=3` free consultations (tracked by `guest_id` cookie), then HTTP 402 → login gate.
- Logged-in users: unlimited.

## Key endpoints (all under /api)
- GET  /search?q=&section=A,B&province=MI&city=&mandate=&only_active=&page=&limit=
- GET  /intermediary/{rui_number}
- GET  /map?<same filters>
- GET  /stats
- GET  /filters/provinces
- POST /ai/search {query}   (natural language → filters + results)
- POST /auth/register {name,email,password}
- POST /auth/login {email,password}
- POST /auth/google/session  (header X-Session-ID)
- GET  /auth/me
- POST /auth/logout
- GET  /usage

## Data
~224,469 intermediaries loaded from IVASS RUI public dataset. Sections: A=Agenti, B=Broker, C=Produttori, D=Banche, E=Collaboratori, U=Addetti fuori sede.
