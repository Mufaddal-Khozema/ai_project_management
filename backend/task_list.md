# Backend Route Task List

Routes derived from scanning `website/` frontend pages.

---

## 1. Health & System

- [x] **GET /api/health** — Health check (from `system` domain reference)

## 2. Authentication

- [x] **POST /api/auth/email/send-otp** — Send 6-digit OTP to email (from `/signup` email flow)
- [x] **POST /api/auth/email/verify-otp** — Verify OTP code, return verification token (from `/signup` OTP step)
- [x] **POST /api/auth/social/google** — Google OAuth login/register (handled by `POST /api/auth/social/{provider}`)
- [x] **POST /api/auth/social/github** — GitHub OAuth login/register (handled by `POST /api/auth/social/{provider}`)
- [x] **POST /api/auth/refresh** — Refresh access token
- [ ] **POST /api/auth/login** — Email/password sign-in (from `/signup` "Sign in" link)

## 3. User / Account

- [ ] **POST /api/users** — Create account (from `/signup` identity step: full name, email, company, password)
- [x] **GET /api/users/me** — Get current user profile
- [ ] **PUT /api/users/me** — Update profile

## 4. Workspace & Onboarding

- [ ] **POST /api/workspaces** — Create workspace (from `/signup` success → redirect to dashboard)
- [ ] **GET /api/workspaces** — List user's workspaces
- [ ] **GET /api/workspaces/{id}** — Get workspace details
- [ ] **PUT /api/workspaces/{id}** — Update workspace settings
- [ ] **POST /api/onboarding/survey** — Submit onboarding survey (company name, role, team size, source)
- [ ] **POST /api/onboarding/platforms/communication** — Set primary communication platform (Slack, Teams, Discord, etc.)
- [ ] **POST /api/onboarding/platforms/pm** — Set primary project management platform (Jira, Asana, Linear, etc.)

## 5. Subscription & Payments

- [ ] **GET /api/payments/plans** — List available pricing plans (Starter $49, Professional $149, Enterprise Custom)
- [ ] **POST /api/payments/subscribe** — Start free trial / subscribe to plan (from `/signup` payment step)
- [ ] **POST /api/payments/cancel** — Cancel subscription
- [ ] **GET /api/payments/invoices** — List invoices

## 7. Admin (Future)

- [ ] **GET /api/admin/users** — List users (admin)
- [ ] **GET /api/admin/workspaces** — List workspaces (admin)
- [ ] **GET /api/admin/dashboard** — Admin dashboard stats
