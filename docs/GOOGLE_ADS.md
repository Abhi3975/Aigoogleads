# Google Ads integration

How the platform connects to Google Ads and how to verify it against a **test
account**.

## Architecture

```
POST /organizations/{org}/google-ads/connect   (admin)
      → returns Google authorization URL (adwords scope, offline access)
      → user consents in browser
GET  /integrations/google-ads/callback          (Google redirect)
      → verifies signed state + nonce cookie (CSRF)
      → exchanges code → refresh token
      → refresh token ENCRYPTED (Fernet) and stored per-organization
      → best-effort account sync

POST /organizations/{org}/google-ads/accounts/sync           list accessible accounts
GET  /organizations/{org}/google-ads/accounts                linked accounts
GET  .../accounts/{customer_id}/campaigns                    read campaigns
GET  .../accounts/{customer_id}/campaigns/metrics            read performance metrics
POST .../accounts/{customer_id}/campaigns          (admin)   create a (paused) test campaign
DELETE .../google-ads/connection                   (admin)   disconnect
```

- **Secure token storage** — refresh tokens are encrypted at rest with
  `ENCRYPTION_KEY`; never logged or returned.
- **Sync SDK, async app** — the google-ads SDK is synchronous and runs off the
  event loop via `run_in_threadpool`.
- **GAQL safety** — date ranges are validated against an allow-list; no
  untrusted interpolation into queries.

## Required configuration

Add to `backend/.env` (or the root `.env` for Docker):

```env
GOOGLE_CLIENT_ID=...            # OAuth client (Web application)
GOOGLE_CLIENT_SECRET=...
GOOGLE_ADS_OAUTH_REDIRECT_URI=http://localhost:8000/api/v1/integrations/google-ads/callback
GOOGLE_ADS_DEVELOPER_TOKEN=...  # from your Google Ads API Center
GOOGLE_ADS_LOGIN_CUSTOMER_ID=   # manager (MCC) account id, digits only (optional)
ENCRYPTION_KEY=...              # Fernet key: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

In the Google Cloud console, add the redirect URI above to the OAuth client's
**Authorized redirect URIs**, and add your Google account as a **test user** on
the OAuth consent screen.

## Verify against a test account

**Option A — quick connectivity script** (no web flow). You need an
adwords-scoped refresh token (e.g. from the google-ads `generate_user_credentials`
helper or OAuth playground):

```bash
cd backend
export GOOGLE_ADS_REFRESH_TOKEN=1//0...           # adwords scope
uv run python scripts/verify_google_ads.py         # lists accounts, campaigns, metrics
```

**Option B — full web flow** (exercises the real endpoints):

1. `make up` (or run the backend), then register/login to get an access token.
2. `POST /api/v1/organizations/{org}/google-ads/connect` → open the returned
   `authorization_url`, consent.
3. Google redirects to the callback, which stores the encrypted token and syncs
   accounts.
4. `GET .../accounts`, `.../campaigns`, `.../campaigns/metrics`.
5. `POST .../accounts/{customer_id}/campaigns` with `{"name": "...", "daily_budget": 20}`
   creates a **paused** Search campaign (safe — no spend).

## Test-account notes

- Use a **Google Ads test account** (created under a test manager account) so no
  real spend can occur. Test accounts don't serve ads and don't require an
  approved developer token for most calls.
- Campaigns are created **PAUSED** by default (`start_paused: true`).
