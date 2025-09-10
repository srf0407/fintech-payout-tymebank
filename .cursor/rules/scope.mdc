# Project Scope: AI-Assisted Full-Stack Fintech App

## Overview
This project is a **full-stack fintech application** where users can log in using OAuth, create payout requests, and track the status of payouts.  
The backend simulates a third-party payments provider, including asynchronous webhook updates, retries, rate-limiting, and idempotency.  

**Goal:** Demonstrate the ability to design and build a secure, observable, reliable system with thoughtful error handling, logging, input validation, and modular architecture.

---

## Frontend Requirements
- **Public page**
  - OAuth login (GitHub or Google preferred)
- **Authenticated dashboard**
  - Display user profile (from OAuth provider)
  - Create payout (fields: amount + currency)
  - Paginated list of payouts with live status updates
- **Error handling**
  - Show user-friendly messages (no raw stack traces)
- **Tech Stack**
  - React with TypeScript

---

## Backend Requirements
- **Authentication**
  - OAuth 2.0 login
  - Use secure mechanisms: state, nonce, PKCE
- **API Endpoints**
  1. `POST /payouts`  
     - Create a payout  
     - Call a mock third-party API  
     - Enforce **idempotency**
  2. `GET /payouts?page=N`  
     - Return paginated list of payouts
  3. `POST /webhooks/payments`  
     - Accept asynchronous webhook updates  
     - Verify **HMAC or JWT signature**
- **Third-party API Simulation**
  - Mock API responses including:
    - retries for transient errors (429, 5xx)
    - rate limiting
    - webhooks
- **Business Logic**
  - Retry with **bounded exponential backoff + jitter**
  - Idempotent webhook handler
- **Database**
  - Store users and payouts (PostgreSQL recommended)
- **Observability**
  - Structured logs with correlation IDs
  - Metrics and operational hints in logs
- **Security**
  - Do not log secrets or PII
  - Input validation and sanitization
  - Rate-limit payout creation
  - Verify webhook timestamps (reject if too old)
  - Use `.env` and separate config (no secrets in source code)

---

## Deliverables
1. **Code repository**
   - Public Git repository
2. **Documentation**
   - `README.md` with setup, test, and usage instructions
   - OpenAPI spec for API
   - Postman collection or `.http` files for key flows
3. **Observability**
   - Logs demonstrating correlation IDs across boundaries
4. **Tests**
   - Minimal tests for:
     - Idempotent payout creation
     - Webhook signature and timestamp verification
5. **AI Usage**
   - `ai_usage.md` documenting:
     - Tools used
     - Key prompts and outputs
     - Mistakes and corrections
     - How outputs were validated

---

## Tech Stack
- **Backend:** FastAPI (Python)  
- **Frontend:** React with TypeScript  
- **Database:** PostgreSQL (or equivalent)  
- **Optional:** Stripe test mode (if available)  

---

## Constraints & Notes
- Do not simulate real money movement; focus on control flow.  
- Keep frontend and backend modular and testable.  
- Prioritize clarity, completeness, and engineering maturity.  
- The backend should be self-contained under `backend/app/`.  
- The frontend should be self-contained under `frontend/src/`.  
- Ensure secure handling of all sensitive data and API keys.

---

**End of Scope**
