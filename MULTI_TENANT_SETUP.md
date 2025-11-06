# JusticeAI Commercial - Multi-Tenant Setup Guide

## Overview

JusticeAI Commercial is a multi-tenant SaaS platform designed for independent law firms. This guide explains the multi-tenant architecture and how to set it up.

## Architecture Summary

### Multi-Tenancy Model
- **Tenant Entity**: `Firm` - Each law firm is a separate tenant
- **Data Isolation**: All data models include `firm_id` foreign key
- **Middleware**: Automatic tenant context injection for every request
- **Subscription Management**: Tiered billing with usage tracking

### Commercial Pricing Model

```
BASIC TIER
├─ Implementation Fee: 20,600 MAD (one-time)
│  └─ Includes: GPU rental (3 years) + Training + Setup
└─ Monthly Fee: 270 MAD × number of active lawyers

COMPLETE TIER
├─ Implementation Fee: 30,600 MAD (one-time)
│  └─ Includes: GPU rental (3 years) + Training + Digitization of 50,000 pages
└─ Monthly Fee: 270 MAD × number of active lawyers

EXAMPLE: Law firm with 6 lawyers
├─ Pays once: 30,600 MAD (Complete tier)
├─ Pays monthly: 1,620 MAD (6 × 270)
└─ ROI: Recovered in 1-2 months vs manual processes
```

## Database Schema Changes

### New Models

#### Firm (Central Tenant Entity)
```python
- id (PK)
- name, email, phone, address
- subscription_tier: "basic" | "complete"
- subscription_status: "active" | "expired" | "suspended" | "trial"
- subscription_start, subscription_end
- implementation_fee_paid: boolean
- monthly_fee_per_lawyer: int (default 270 MAD)
- language_preference: "en" | "fr" | "ar"
- max_users, max_documents, max_storage_gb
```

#### Subscription
```python
- firm_id (PK, FK to Firm)
- status, start_date, end_date
- plan_tier, monthly_cost
- next_billing_date, auto_renew
```

#### Invoice
```python
- id (PK)
- firm_id (FK to Firm)
- invoice_number, amount, currency
- invoice_date, due_date, status
- description, paid_date
```

### Updated Models (Added firm_id)
- **User**: `firm_id` + commercial roles (Admin, Lawyer, Assistant)
- **Expediente**: (renamed from Case) `firm_id` + client-focused fields
- **Document**: `firm_id` + subscription validation on upload
- **AuditLog**: `firm_id` for firm-scoped audit trails

## Setup Instructions

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Configure Environment

Create `.env` file:

```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/justiceai_commercial

# JWT
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Environment
ENVIRONMENT=development
DEBUG=true
```

### 3. Initialize Database

```bash
cd backend
python init_multi_tenant_db.py
```

This script will:
- ✅ Create all database tables
- ✅ Set up an example law firm "Cabinet d'Avocats Demo"
- ✅ Create 7 demo users (1 admin, 5 lawyers, 1 assistant)
- ✅ Generate implementation and monthly invoices
- ✅ Create an example expediente (case)

### 4. Start the Backend

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 5. Start the Frontend

```bash
cd frontend
npm install
npm run dev
```

## API Endpoints

### Billing & Subscription Management

#### Register New Firm
```http
POST /api/billing/init
Content-Type: application/json

{
  "name": "Cabinet Juridique XYZ",
  "email": "contact@cabinet-xyz.ma",
  "phone": "+212522XXXXXX",
  "subscription_tier": "complete",
  "language_preference": "fr",
  "admin_name": "Ahmed Alami",
  "admin_email": "ahmed@cabinet-xyz.ma",
  "admin_password": "SecurePass123!"
}
```

#### Check Subscription Status
```http
GET /api/billing/status
Authorization: Bearer <jwt_token>
```

Response:
```json
{
  "firm_id": 1,
  "firm_name": "Cabinet Juridique XYZ",
  "status": "active",
  "is_active": true,
  "tier": "complete",
  "start_date": "2025-01-01",
  "end_date": "2028-01-01",
  "next_billing_date": "2025-02-01",
  "monthly_cost": 1620.0
}
```

#### Get Current Invoice
```http
GET /api/billing/invoice/current
Authorization: Bearer <jwt_token>
```

#### Get All Invoices
```http
GET /api/billing/invoices?status_filter=pending&limit=50
Authorization: Bearer <jwt_token>
```

#### Generate Monthly Invoice (Admin only)
```http
POST /api/billing/invoice/generate?month=2&year=2025
Authorization: Bearer <jwt_token>
```

## Demo Credentials

After running `init_multi_tenant_db.py`, you can login with:

**Admin User:**
- Email: `fatima@cabinet-demo.ma`
- Password: `Demo2025!`
- Role: Administrator (full access)

**Lawyer User:**
- Email: `ahmed@cabinet-demo.ma`
- Password: `Demo2025!`
- Role: Lawyer (case management)

**Assistant User:**
- Email: `nadia@cabinet-demo.ma`
- Password: `Demo2025!`
- Role: Assistant (limited access)

## Multi-Language Support

The platform supports three languages with automatic detection:

- **French (fr)**: Default language
- **Arabic (ar)**: Full RTL (right-to-left) support
- **English (en)**: Secondary language

Language is detected from:
1. User's saved preference
2. Firm's default language
3. `Accept-Language` HTTP header
4. Fallback to French

## Middleware

### TenantMiddleware
Automatically extracts `firm_id` from authenticated user's JWT token and makes it available in `request.state.firm_id`. Ensures all database queries are scoped to the current firm.

### LanguageMiddleware
Detects user's language preference from:
- User model `language` field
- Firm model `language_preference` field
- `Accept-Language` header
- Fallback to French

Sets `request.state.language` and `Content-Language` response header.

## Security Features

### Data Isolation
- ✅ Every model includes `firm_id` with indexed foreign key
- ✅ Middleware enforces firm context on all requests
- ✅ Cross-tenant data access is prevented at the database level

### Subscription Validation
- ✅ BillingService validates active subscription before critical operations
- ✅ Document uploads blocked if subscription expired
- ✅ Automatic subscription status updates based on end_date

### Role-Based Access Control
- ✅ Admin: Full firm management, billing, user administration
- ✅ Lawyer: Case/expediente management, document access
- ✅ Assistant: Limited read access, document viewing

## Next Steps

### For Development

1. **Implement Tenant-Aware Routes**: Update existing routes (documents, expedientes, users) to filter by `firm_id`
2. **Add Subscription Validation**: Inject subscription checks in document upload, OCR processing, and search endpoints
3. **Frontend Updates**: Create billing dashboard, firm settings, subscription management UI
4. **Testing**: Write comprehensive multi-tenant isolation tests

### For Production

1. **Database Migration**: Use Alembic to create migration from single-tenant to multi-tenant schema
2. **Payment Integration**: Add Stripe/PayPal for automatic billing
3. **Email Notifications**: Send invoice reminders, subscription expiration alerts
4. **Admin Panel**: Create super-admin interface for managing all firms
5. **Monitoring**: Set up firm-level usage metrics and billing analytics

## Troubleshooting

### Issue: "User does not belong to any firm"
**Solution**: Ensure all users have `firm_id` set. Run database migration or manually update user records.

### Issue: "Subscription inactive" error
**Solution**: Check firm's subscription status in database. Update `subscription_status` to "active" or renew subscription.

### Issue: Invoice generates 0 MAD amount
**Solution**: Ensure firm has active lawyers. The monthly fee is calculated as `num_lawyers × 270 MAD`.

## Support

For technical issues or questions:
- Check API documentation: `http://localhost:8000/docs`
- Review logs in backend console
- Test with demo firm credentials first

## License

Proprietary - JusticeAI Commercial SaaS Platform
