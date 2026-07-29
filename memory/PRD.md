# RUI Explorer — PRD

## Problem statement (original, IT)
"Costruiscimi il miglior tool semplice possibile con questi database presi dal sito ufficiale IVASS Italia. Il portale RUI è il portale di consultazione di broker assicurativi e riassicurativi così come agenti." + Follow-up: "aggiorna lo strumento con l'obiettivo di avere una scheda intermediario/agente la più completa possibile. Inoltre proponi anche un prezzo e metodo di pagamento. Rimani dentro 10 crediti massimi di utilizzo."

## User choices
- Ricerca avanzata + dashboard statistiche + ricerca per nome/RUI/città/provincia/sezione/compagnia + scheda dettaglio + mappa tipo "Google Maps degli agenti".
- Assistente AI in linguaggio naturale (Gemini via EMERGENT_LLM_KEY).
- Pubblico con consultazioni gratuite poi login (Google + email/password).
- Design: unico, avanguardia, professionale, pulito.

## Architecture
- FastAPI (`/app/backend/server.py`) + MongoDB + React (CRA + TanStack Query + Leaflet + framer-motion + shadcn).
- Data ingested from IVASS RUI public dataset: `intermediari` (224,469), `sedi`, `mandati`, `websites` denormalized; enrichment collections: `collaboratori` (312,985), `cariche` (19,882), `collab_accessori`, `resp_distrib`. Geocoding via ISTAT comuni coordinates (Italy-bounds sanity filter).
- Ingestion scripts: `/app/scripts/ingest_rui.py`, `/app/scripts/enrich_rui.py`.

## Auth
- Unified session-token cookie (`session_token`) for BOTH email/password (bcrypt) and Emergent Google OAuth.
- Freemium: guests get 3 free searches (guest_id cookie), then 402 → login gate. Registered users unlimited.

## Payments (Stripe)
- Flow B (BYOK) with pre-injected `STRIPE_API_KEY=sk_test_emergent` (TEST/DEMO mode), emergentintegrations StripeCheckout.
- Packages (server-side): `pro_monthly` €9.90, `pro_annual` €79.00.
- Endpoints: POST /api/payments/checkout, GET /api/payments/status/{id}, POST /api/webhook/stripe, GET /api/pricing.
- On paid → user `is_pro=true`. Pro unlocks full profile (collaboratori, responsabili/cariche) in the detail drawer.
- No automatic tax (custom-amount Flow B). Can be upgraded to managed payments / Stripe Tax on request.

## Implemented (2026-06)
- Advanced search + filters (section/province/city/mandate/only_active), pagination, light projection.
- Interactive Leaflet density map of Italy (799 clusters), marker → filter by comune.
- Detail drawer (bento): RUI, section, registration, birth, mini-map, sedi, mandati, websites, works_for, + Pro-gated collaboratori & responsabili/cariche, resp_distrib.
- AI natural-language assistant (Gemini) → structured filters + results + "apply filters".
- Statistics dashboard: KPIs, section pie, top-provinces bar, top mandate companies.
- Auth (email/password + Google), freemium gate.
- Pricing page + Stripe checkout + payment success/cancel pages + Pro badge.

## Dual-role auth + feedback (2026-06, VERIFIED)
- Role-aware registration: `role` = "user" | "intermediary". Intermediary must claim an existing RUI (validated against db.intermediari, else 400).
- Standard user (`/account`): profile card + "I miei feedback" list; can leave star reviews on any intermediary drawer (DrawerFeedback), owner cannot review own RUI.
- Intermediary (`/intermediary-dashboard`): stats (profile views, avg rating, review count, mandates), profile editor (bio/phone/public email/website/services), rating distribution + recent feedback.
- Endpoints: /my/intermediary, PUT /my/intermediary/profile, /intermediary/{rui}/feedback, /my/feedback.
- Verified: backend via curl (all pass) + frontend e2e testing_agent iteration_2 (9/9 pass). Fixed a critical missing `IdentificationBadge` import in Header.jsx that crashed intermediary sessions.

## MASTER admin console (2026-06, VERIFIED)
- Single MASTER admin account `flavio.cristiano@22gmbh.com` (role "admin"), seeded idempotently at startup from `MASTER_ADMIN_EMAIL`/`MASTER_ADMIN_PASSWORD` in backend/.env (password ensured to match env, self-heals null password).
- Audit log (`audit_log` collection): records login / login_failed / login_blocked / logout / register / admin_update_user / admin_delete_user with ip, user-agent, timestamp. (Searches intentionally NOT logged, per user choice.)
- `suspended` flag: blocks login (403) and invalidates active sessions; enforced in get_current_user.
- Admin page `/admin` (Admin.jsx), admin-only (redirects non-admins), header link visible only for admins. Tabs:
  - Panoramica: KPIs (utenti totali, intermediari rivendicati, PRO, sospesi), role distribution, activity events, platform data.
  - Utenti: searchable/filterable list (q/role/status), row → detail drawer with activity, sessions, feedback; actions: Concedi/Revoca PRO, Sospendi/Riattiva, Declassa a Utente, Elimina. MASTER account is self-protected (no actions, backend 400).
  - Log attività: audit events with event + text filters (email/IP/user id).
- Endpoints: GET /admin/overview, GET /admin/users, GET /admin/users/{id}, PATCH /admin/users/{id}, DELETE /admin/users/{id}, GET /admin/activity.
- Verified: iteration_3 — backend 14/14 pytest pass, frontend 100% e2e.

## Admin PRO + PRO test accounts (2026-06, VERIFIED)
- Admins are PRO everywhere: `public_user` returns is_pro=true for role "admin", `has_pro()` gates backend. Auto-unlocks all current + future is_pro-gated features for admins (no per-feature change needed).
- Master seed now also ensures is_pro=true.
- `seed_test_accounts()` (idempotent, startup): `utente.pro@test.com` / `TestPro2026!` (user, PRO) and `intermediario.pro@test.com` / `TestPro2026!` (intermediary, PRO, RUI A000101292). Passwords reset on each restart.
- Verified via curl: admin is_pro true; both test accounts login; intermediary /my/intermediary OK; PRO PDF report download 200 for PRO user.

## Analytics & AI insights per profilo (2026-06, VERIFIED)
- Intermediary dashboard (`/intermediary-dashboard`): added portfolio analytics (mandati → elenco compagnie; collaboratori → conteggi per sezione + comuni; sedi → province coperte) and a "Indice di completezza profilo" (score % + checklist dei 5 campi editabili con suggerimenti). Completezza si ricalcola al salvataggio.
- User profile (`/account`): activity summary (recensioni rilasciate, voto medio dato, distribuzione stelle), "Cosa consulti di più" (top sezioni/province), "Cronologia consultazioni" (view history), + link che apre la scheda su `/?rui=`.
- View history: `view_history` collection (upsert per user+rui, viewed_at, views) popolata quando un utente loggato apre una scheda (non la propria).
- AI insights (Gemini via EMERGENT_LLM_KEY): GET /my/intermediary/insights (report performance) e GET /my/insights (messaggio personalizzato utente). In-memory TTL cache (10 min, chiave = user + hash dei fatti) per non ri-addebitare crediti ad ogni refresh.
- Endpoints: GET /my/intermediary (ora con analytics+completeness), /my/intermediary/insights, /my/stats, /my/insights.
- Helpers: compute_intermediary_analytics, compute_completeness, ai_text, cached_insight.
- Verified: iteration_4 — backend 6/6 pytest, frontend 100% e2e. Cache confirmed (5.5s→0.15s).

## Drawer visibility fix + PDF territorial context (2026-06, VERIFIED)
- Fixed a stacking bug where Leaflet's internal panes/controls (z-index up to 1000) escaped the map container and painted OVER the intermediary drawer, making the scheda appear invisible over the map. Fix: `isolate` (isolation:isolate) on the Portal map wrapper to contain Leaflet's z-indexes, and raised the drawer root to z-[66] (above the map and the AI button, below the freemium gate z-[70]). Verified via hit-test: drawer content now paints on top.
- PDF report (report.py) enriched: new "Contesto territoriale" section (n. intermediari nel comune e in provincia, di cui della stessa sezione, operativi in provincia — computed in compute_context_stats via count_documents) and a highlighted "Mandati operativi / Compagnie" summary listing the mandant companies. Verified by extracting a generated PDF.

## Benchmark competitivo intermediario (2026-06, VERIFIED)
- Nuova analisi avanzata nella dashboard intermediario: "Benchmark & concorrenza · provincia".
  - Posizionamento: rank #N su totale della stessa sezione in provincia + "superi il X% dei concorrenti" (per numero mandati).
  - Mandati tu vs mercato: i tuoi mandati vs media provinciale vs massimo, con barre; + concorrenti nel tuo comune.
  - Top 5 concorrenti in provincia+sezione per numero di mandati (nome, comune, n. mandati).
- Endpoint GET /my/intermediary/benchmark: usa count_documents + aggregate ($size mandati, $avg/$max, $expr rank) con allowDiskUse, scoped a provincia+sezione (veloce, ~0.15s). Indice composto (provincia, section) aggiunto.
- Nessun costo LLM aggiuntivo (pura aggregazione sui 224k record reali). Verificato via curl + screenshot.
- NOTA: integrazione OpenAI Chat Models NON implementata (utente ha cambiato richiesta verso analisi avanzate). Resta in backlog se richiesta.

## Verification status
- Backend: ALL endpoints verified via curl (search 224,469; map 799 clusters; enriched detail; stats; ai/search; register/login/me; checkout creates cs_test session; pricing). ✅
- Frontend rendering: verified via screenshots (portal search+map, pricing page). ✅
- Click-driven UI flows (drawer open, filter chips, AI panel, checkout button): implemented correctly (standard React handlers, no console errors, no intercepting overlays) but could NOT be exercised in the screenshot automation tool this session (tool failed to deliver click/input events to React across all attempts). Recommend verifying on the deployed production build.

## Known notes
- Preview (dev build) first page load can take ~10s per fresh browser context; production build is faster.

## Backlog / Next
- P1: Full end-to-end click-flow test on production; add CSV/PDF export for Pro users.
- P1: Migrate Stripe to Flow A (claimable sandbox) + Stripe Tax/managed payments for real go-live.
- P2: Collaborator search facet; saved searches; email alerts on registry changes.
- P2: Cache /map + /stats (Redis or in-process TTL) to speed first paint.
