# Phase 4 follow-up — local viewer JWTs

Status: development authentication and a viewer-role gate implemented. This is not a production identity provider or a complete user-management system.

## Fundamentals
Authentication establishes the requesting identity; authorization checks its permissions. A bearer token grants access to whoever possesses it, so treat it as a secret. JWT is a signed claims format: its payload is readable, not encrypted.

Our development issuer signs tokens with HS256 and a random local secret. Claims include subject (sub), role, issuer (iss), audience (aud), issued-at (iat), not-before (nbf), and expiry (exp). The API verifies the signature using a fixed allowed algorithm, checks expected issuer/audience and required claims, rejects expired/future/invalid claims, then applies the role's permissions.

Three identity layers are distinct: aegis-dev is an AWS IAM identity; aegis_api is a PostgreSQL login; local-operator is the local HTTP token subject. Possessing one does not automatically grant access as the others.

## Why this comes now
Read-only database permissions prevent API writes, but did not restrict which HTTP clients could read event data. The new gate protects both event endpoints before we expand backend features. Health, readiness, and API documentation remain public on localhost for development and probes.

## Flow
Trusted local developer → development token issuer → viewer JWT → Authorization: Bearer header → signature/claim validation → events:read permission → existing SELECT-only repository.

## Files
- backend/auth.py: signing settings, strict claims, signature/claim verification, viewer permissions.
- backend/auth_cli.py: local-only viewer issuer; no HTTP token-creation endpoint exists.
- backend/api.py: security dependencies for list/detail and authenticated subject in request logs.
- scripts/init_local_env.py: generates missing ignored .env.auth with JWT_SECRET; preserves existing files.
- scripts/create_viewer_token.py: runs the local issuer and atomically saves output to .local/viewer-token.txt with private file/directory permissions. Tokens are not printed.
- tests/test_auth.py: authentication/authorization cases without real credentials or AWS calls.
- compose.yaml: only the API receives .env.auth; queue and import services do not receive the signing key.

## Policy
- Token lifetime: 15 minutes; the schema rejects lifetimes longer than that.
- Allowed signature algorithm: HS256, chosen by server code, never by trusting the token header.
- Expected issuer: aegisops-local; audience: aegisops-console.
- Current role: viewer with events:read. Unknown roles have no permissions and receive 403.
- Protected routes: GET /events and GET /events/{event_id}.
- Missing/invalid/expired credentials: 401 with WWW-Authenticate: Bearer.
- Valid credentials but insufficient role permission: 403.
- JWT_SECRET must be at least 32 bytes. No fallback/default signing key is embedded in application code; missing/short configuration fails startup.

## Commands and hands-on check
From the project root:

```sh
python3 scripts/init_local_env.py
docker compose build api
docker compose --profile api up -d api
python3 scripts/create_viewer_token.py
```

Open .local/viewer-token.txt privately in your editor. Open http://127.0.0.1:8000/docs, click Authorize, paste only the token into ViewerJWT, authorize, and execute GET /events. Never paste the token or signing key into chat, commit them, or include them in screenshots. If the token expires, rerun the helper and replace the value in Swagger.

Without authorization, GET /events should now return 401; this is expected. After viewer authorization it returns 200. A direct browser visit to /events does not automatically carry the Swagger UI's header. Use the Swagger Try it out action or an HTTP client with the bearer header.

The helper does not start the database or issue production identities. Its container uses the existing API environment but performs no database or AWS calls. The caller already controls this local project and its signing secret; the subject is a development label, not independently verified human identity.

## Verification
Eight auth tests added; total unit suite is 30 tests and passed. Cases include missing credentials before database access, valid viewer, 15-minute lifetime, expiration, malformed/wrong-signature tokens, wrong issuer/audience, missing claims, unsupported algorithm, excessive lifetime, invalid/extra claims, unknown role, public probes/docs, OpenAPI security declaration, and weak signing-key/naive-time rejection.
Existing API contract tests override the auth dependency to isolate routing behavior. The new auth tests do not override that dependency and exercise actual signing/verification. Live HTTP checks passed after the final pinned-image restart: public probes, 401 without token, 200 viewer, 403 unassigned role, authenticated detail, 422, and OpenAPI security. Generated a private viewer token without displaying it.

## Operational/security limits
This is a trusted-local-developer issuer, not OAuth/OIDC, Cognito, MFA login, refresh-token management, user provisioning, per-user revocation, or production key rotation. There is no public password/token endpoint. No API rate limiter or durable auth audit journal yet. Rotating the signing key and restarting the API invalidates old tokens; short expiry limits token lifetime but is not immediate revocation. Keep binding at 127.0.0.1. Production must replace this issuer with a proper identity provider and verified issuer keys, without accepting local signing tokens.

The API's database remains SELECT-only independently of HTTP authentication. A viewer token cannot grant database write privileges or remediation permissions.

## Interview takeaways
Explain 401 versus 403, signed versus encrypted, claims versus permissions, and the difference between a verified token issuer and a verified human. Never call this complete production identity management. Approval/operator roles will be defined when those workflows exist.

## Review questions (deferred)
1. Why is an event hash not a replacement for a signed access token?
2. Why must the server fix the JWT algorithm allow-list?
3. What does audience validation prevent?
4. How does a valid token still result in 403?
5. Why does token expiry not implement immediate revocation?
6. Which protections remain if a viewer token is leaked?

## References
- https://pyjwt.readthedocs.io/en/latest/usage.html
- https://pyjwt.readthedocs.io/en/latest/api.html
- https://fastapi.tiangolo.com/reference/security/
