# Lender Matching Platform

An intelligent loan underwriting system with AI-powered PDF policy extraction for equipment finance and business lending.

## Current Implementation

This project currently implements **AI-powered lender policy extraction from PDFs** with an admin review interface.

### ✅ Implemented Features

#### 1. PDF Policy Extraction
- Upload lender policy PDFs (max 10MB)
- Automatic extraction using Claude 3.5 Sonnet via OpenRouter API
- Extracts: lender info, programs/tiers, underwriting rules, rate metadata
- Single LLM call for efficient extraction

#### 2. Policy Review & Editing Interface
- Interactive review of extracted data
- Inline field validation with red asterisks (*) for required fields
- Direct error messages on each field
- Visual warnings for missing rate tables and rules
- Edit lender information, programs, and rules
- Manual "Save Changes" button (no auto-save)

#### 3. Policy Approval Workflow
- Review extracted data before saving to database
- Edit and correct extraction errors
- Approve to create lender, programs, and rules in database
- Works even with validation warnings (user decides)

#### 4. Backend API
- RESTful API built with FastAPI
- PDF upload and extraction endpoint
- Policy CRUD operations (Create, Read, Update, Delete)
- Database persistence with PostgreSQL

#### 5. Database Schema
- **Lenders**: Company profiles with loan constraints
- **Policy Programs**: Tiers/programs within each lender
- **Policy Rules**: Underwriting rules with flexible JSON criteria
- Support for 12+ rule types (FICO, revenue, loan amount, equipment, etc.)

## Tech Stack

### Backend
- **FastAPI** 0.115.6 - Modern async Python web framework
- **PostgreSQL** 15 - Primary database
- **SQLAlchemy** 2.0 - Async ORM
- **Alembic** - Database migrations
- **Pydantic** - Data validation
- **pypdf & pdfplumber** - PDF parsing
- **OpenAI SDK** - LLM integration (OpenRouter compatible)

### Frontend
- **React** 19 with **TypeScript** 5.9
- **Vite** 7 - Build tool
- **Tailwind CSS** 4 - Styling
- **Radix UI** - Headless UI components
- **Axios** - HTTP client
- **Lucide React** - Icons

## Quick Start

### 1. Backend Setup

```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Create .env file
cat > .env << EOF
DATABASE_URL=postgresql://postgres:postgres@localhost:5433/lender_platform
ENVIRONMENT=development
LOG_LEVEL=INFO
CORS_ORIGINS=http://localhost:5173,http://localhost:5174

# OpenRouter Configuration
OPENROUTER_API_KEY=your_openrouter_api_key_here
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_MODEL=anthropic/claude-3.5-sonnet
EOF

# Start PostgreSQL (Docker)
docker-compose up -d

# Run migrations
alembic upgrade head

# Start server
uvicorn app.main:app --reload --port 8000
```

Backend runs at: **http://localhost:8000**

API docs: **http://localhost:8000/api/docs**

### 2. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start dev server
npm run dev
```

Frontend runs at: **http://localhost:5173**

## How to Use

### Extract Lender Policies from PDF

1. Navigate to the Policy Extraction page
2. Click "Upload PDF" or drag & drop a lender policy PDF
3. Wait for extraction (usually 10-20 seconds)
4. Review the extracted data:
   - **Lender Information**: Name, loan ranges, exclusions
   - **Programs**: Different tiers/programs offered
   - **Rules**: Underwriting criteria for each program
5. Fix any issues:
   - Red borders show required fields
   - Yellow warnings show missing rate data or rules
   - Edit directly in the form
6. Click "Save Changes" to update
7. Click "Approve & Save" to persist to database

### Field Validation

Required fields are marked with a red asterisk (*):
- **Lender Name** *
- **Min Loan Amount** * (typical: $10,000)
- **Max Loan Amount** * (typical: $5,000,000)
- **Program Name** *
- **Program Code** * (e.g., "A", "Tier 1")
- **Credit Tier** * (e.g., "A", "B", "C")
- **Rule Name** *
- **Rule Type** * (e.g., "min_fico")
- **Rule Criteria** * (JSON format)

## API Endpoints

### Policy Extraction
```
POST   /api/v1/policy-extraction/upload        # Upload & extract PDF
GET    /api/v1/policy-extraction               # List extractions
GET    /api/v1/policy-extraction/{id}          # Get extraction
PUT    /api/v1/policy-extraction/{id}          # Update extraction
POST   /api/v1/policy-extraction/{id}/approve  # Approve & save to DB
DELETE /api/v1/policy-extraction/{id}          # Delete extraction
```

### Lenders
```
POST   /api/v1/lenders           # Create lender
GET    /api/v1/lenders           # List lenders
GET    /api/v1/lenders/{id}      # Get lender
PUT    /api/v1/lenders/{id}      # Update lender
DELETE /api/v1/lenders/{id}      # Delete lender
```

### Programs & Rules
```
POST   /api/v1/policies/lenders/{id}/programs     # Add program
GET    /api/v1/policies/programs/{id}             # Get program
PUT    /api/v1/policies/programs/{id}             # Update program
DELETE /api/v1/policies/programs/{id}             # Delete program

POST   /api/v1/policies/programs/{id}/rules       # Add rule
GET    /api/v1/policies/rules/{id}                # Get rule
PUT    /api/v1/policies/rules/{id}                # Update rule
DELETE /api/v1/policies/rules/{id}                # Delete rule
```

## Project Structure

```
kaaj-assignment/
├── backend/
│   ├── app/
│   │   ├── api/v1/endpoints/
│   │   │   ├── policy_extraction.py    # PDF extraction API
│   │   │   ├── lenders.py              # Lender CRUD
│   │   │   └── policies.py             # Programs & rules
│   │   ├── services/
│   │   │   └── pdf_parser/
│   │   │       ├── policy_extractor.py # Main extraction logic
│   │   │       ├── pdf_reader.py       # PDF parsing
│   │   │       ├── llm_extractor.py    # OpenRouter integration
│   │   │       └── prompts.py          # LLM prompts
│   │   ├── models/
│   │   │   ├── domain/                 # SQLAlchemy models
│   │   │   └── schemas/                # Pydantic schemas
│   │   └── repositories/               # Data access layer
│   └── requirements.txt
│
└── frontend/
    ├── src/
    │   ├── pages/
    │   │   └── PolicyExtractionPage.tsx
    │   ├── components/admin/
    │   │   ├── PDFUploader.tsx
    │   │   ├── ExtractedPolicyReview.tsx
    │   │   └── PolicyEditor.tsx        # Edit policies with validation
    │   └── services/
    │       └── policyExtractionService.ts
    └── package.json
```

## Database Schema

### Lenders
```sql
CREATE TABLE lenders (
    id UUID PRIMARY KEY,
    name VARCHAR NOT NULL,
    description TEXT,
    min_loan_amount NUMERIC,
    max_loan_amount NUMERIC,
    excluded_states TEXT[],
    excluded_industries TEXT[],
    is_active BOOLEAN DEFAULT true
);
```

### Policy Programs
```sql
CREATE TABLE policy_programs (
    id UUID PRIMARY KEY,
    lender_id UUID REFERENCES lenders(id),
    program_name VARCHAR NOT NULL,
    program_code VARCHAR NOT NULL,
    credit_tier VARCHAR NOT NULL,
    min_fit_score NUMERIC DEFAULT 60,
    description TEXT,
    eligibility_conditions JSONB,
    rate_metadata JSONB
);
```

### Policy Rules
```sql
CREATE TABLE policy_rules (
    id UUID PRIMARY KEY,
    program_id UUID REFERENCES policy_programs(id),
    rule_type VARCHAR NOT NULL,
    rule_name VARCHAR NOT NULL,
    criteria JSONB NOT NULL,
    weight NUMERIC DEFAULT 1.0,
    is_mandatory BOOLEAN DEFAULT true
);
```

## Supported Rule Types

The system supports flexible rule types with JSON criteria:

- `min_fico` - Minimum FICO score: `{"min_score": 650}`
- `min_paynet` - Minimum PayNet score: `{"min_score": 75}`
- `credit_tier` - Credit tier: `{"allowed_tiers": ["A", "B"]}`
- `time_in_business` - Years in business: `{"min_years": 2}`
- `min_revenue` - Minimum revenue: `{"min_amount": 100000}`
- `legal_structure` - Business structure: `{"allowed_structures": ["LLC", "Corp"]}`
- `loan_amount_range` - Loan amount limits: `{"min_amount": 10000, "max_amount": 500000}`
- `loan_term_range` - Term limits: `{"min_months": 12, "max_months": 84}`
- `equipment_type` - Equipment restrictions: `{"allowed_types": ["Medical Equipment"]}`
- `equipment_age` - Max age: `{"max_years": 15}`
- `state_restriction` - State exclusions: `{"excluded_states": ["CA", "NY"]}`
- `industry_restriction` - Industry exclusions: `{"excluded_industries": ["Cannabis"]}`

## Configuration

### Required Environment Variables

Create a `.env` file in the `backend/` directory:

```env
# Database
DATABASE_URL=postgresql://user:password@host:port/database

# Environment
ENVIRONMENT=development
LOG_LEVEL=INFO

# CORS (add your frontend port)
CORS_ORIGINS=http://localhost:5173,http://localhost:5174

# OpenRouter API (required for PDF extraction)
OPENROUTER_API_KEY=your_api_key_here
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_MODEL=anthropic/claude-3.5-sonnet
```

## Recent Updates

### Latest Changes
- ✅ Disabled noisy LLM validation warnings
- ✅ Added inline field validation with asterisks
- ✅ Removed separate validation warnings section
- ✅ Added contextual warnings for missing rate data
- ✅ Fixed infinite loop in policy editor (removed auto-save)
- ✅ Fixed double-formatting bug in validation prompts
- ✅ Improved extraction prompts for better rate data capture
- ✅ Added safety checks for loan amount defaults

## Troubleshooting

**CORS Errors**
- Add your frontend port to `CORS_ORIGINS` in backend `.env`
- Restart backend server

**PDF Extraction Fails**
- Check `OPENROUTER_API_KEY` is valid
- Ensure PDF is under 10MB
- Check backend logs for detailed errors

**Database Connection Fails**
- Verify PostgreSQL is running: `docker-compose ps`
- Check `DATABASE_URL` in `.env`
- Ensure port 5433 is available

**Infinite PUT Requests**
- This was fixed - make sure you have the latest code
- The policy editor now only saves on button click

## Next Steps (Not Yet Implemented)

- Loan application creation and management
- Lender matching and underwriting workflow
- Fit score calculation and ranking
- Match results dashboard
- Application status tracking

---

**Current Status**: PDF extraction and policy management fully functional ✅
