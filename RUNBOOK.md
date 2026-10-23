# Chitties – Enterprise Chit Fund Platform Operations Runbook

## 1. System Architecture Overview

**Chitties** is an enterprise-grade multi-tenant Chit Fund platform engineered strictly under the statutory framework of the **Chit Funds Act, 1982 (Central Act No. 40 of 1982)**.

### Architectural Stack
- **Backend**: FastAPI (Python 3.12/3.14), SQLAlchemy 2.0 ORM, Pydantic V2, PostgreSQL 18 with connection pooling and row-level locking (`with_for_update()`).
- **Frontend**: Vite 6, React 18, Tailwind CSS, Lucide icons, native WebSockets client.
- **Security**: In-memory rate limiting, enterprise security headers (`HSTS`, `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`), JWT authentication with live SMTP email verification.
- **Deployment**: Local execution during active development (Production Docker containerization & orchestration will be configured at final project completion).

---

## 2. Quickstart & Local Execution

### 2.1 Backend Local Startup
```bash
# 1. Activate Virtual Environment
cd D:\Chitties\backend
venv\Scripts\activate

# 2. Run Database Migrations
alembic upgrade head

# 3. Start Uvicorn ASGI Server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
API Documentation is live at: `http://localhost:8000/docs`

### 2.2 Frontend Local Startup
```bash
cd D:\Chitties\frontend
npm install
npm run dev
```
Web Application is live at: `http://localhost:5173`

---

## 3. Demo Credentials & 1-Click Access

The platform features built-in demo seed profiles allowing instant one-click testing without manual form filling:

| Role | Email | Password | Access Scope |
| :--- | :--- | :--- | :--- |
| **Super Admin** | `superadmin@chitties.io` | `ApexPass@2026` | Global multi-tenant administration & tenant creation |
| **Org Admin** | `admin@apexchits.com` | `ApexPass@2026` | Full organization management, schemes, branches, compliance |
| **Branch Manager** | `manager.hyd@apexchits.com` | `ApexPass@2026` | Local branch subscribers, auctions, payments, payouts |
| **Subscriber 1** | `rajesh.subscriber@example.com` | `ApexPass@2026` | Personal tickets, auction chamber bidding, receipt ledger |
| **Subscriber 2** | `priya.subscriber@example.com` | `ApexPass@2026` | Personal tickets, live bidding, payout claims |

---

## 4. Production Deployment (Docker Compose)
*(Deferred – Docker configurations will be added upon project completion).*

When ready for containerized deployment, the multi-service Docker configuration (`docker-compose.prod.yml`, `backend/Dockerfile`, and `frontend/Dockerfile`) will be set up to orchestrate PostgreSQL 18, FastAPI Backend, and Nginx Frontend.

---

## 5. Daily Operations & Regulatory Workflow

### 5.1 Circle Launch & Section 20 Compliance
1. Create Chit Scheme (defining total chit value, duration, monthly installment, commission).
2. Launch Chit Group (`ENROLLING` status) and onboard 100% KYC-verified members.
3. **Mandatory Step**: Under Section 20 of the Chit Funds Act 1982, the foreman must lodge a **100% aggregate chit value security deposit** (FDR / Bank Guarantee) in an approved bank.
4. Org Admin verifies and pledges the lien.
5. Transition group to `ACTIVE` -> Installment obligations are automatically generated for all tickets.

### 5.2 Conducting Live Reverse Auctions
1. On the scheduled auction day, navigate to **Auctions & Bidding** -> Click **Start Auction Room**.
2. Subscribers enter the live chamber and submit discount bids.
3. The platform validates bidding bounds (5% minimum to 30% statutory ceiling) and strictly applies **Monotonic First-Come, First-Served (FCFS)** tie-breaking.
4. Click **Close & Settle Round**:
   - The winner is declared and marked `PRIZED`.
   - 5% Foreman Commission and Total Dividend Pool are calculated.
   - Non-prized members receive their dividend discount credit automatically on next month's dues.

### 5.3 Prize Money Disbursements & Collateral
1. Navigate to **Payouts & Sureties**.
2. Winner lodges required collateral documents (Personal Guarantor, Salary Certificate, or Property Mortgage).
3. Branch Manager or Org Admin inspects and marks sureties as `VERIFIED`.
4. Enter Bank UTR / Cheque reference and click **Confirm & Disburse Prize Funds**:
   - Any outstanding ticket arrears are automatically deducted and settled.
   - Digital receipts are logged for auditability.

### 5.4 Statutory Form XIV Filing
1. Navigate to **Compliance & Audit** -> **Statutory Filings & Form XIV**.
2. Click **View Form XIV** for the concluded auction round.
3. Verify legal minutes, prized subscriber details, and dividend breakdown.
4. Click **Print Statutory Form XIV** for physical/digital submission to the Sub-Registrar of Chits within 60 days.
5. Record the official Registrar Acknowledgment Number.

---

## 6. Automated Database Backup & Disaster Recovery

Run the backup script directly or schedule via cron:

```bash
# Execute manual zero-downtime backup
python scripts/backup_db.py
```
- Archives are compressed with Gzip in `backups/chitties_backup_YYYYMMDD_HHMMSS.sql.gz`.
- Cryptographic SHA-256 integrity checksums are generated automatically.
- Archives older than 30 days are automatically rotated and pruned.

To restore a backup:
```bash
gunzip -c backups/chitties_backup_20261016_120000.sql.gz | psql -U postgres -d chitties_db
```

---

## 7. Troubleshooting & Health Probes

- **Deep Health Probe**: `GET /health` measures active database roundtrip latency.
- **Rate Limit Reset**: If throttled with `429 Too Many Requests`, check `Retry-After` header.
- **WebSocket Reconnection**: Live auction room includes automatic heartbeat detection and reconnection logic.
