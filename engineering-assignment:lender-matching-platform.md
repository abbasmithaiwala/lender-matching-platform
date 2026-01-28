# **Engineering Assignment: Lender Matching Platform**

## **Overview**

Build a loan underwriting and lender matching system that evaluates business loan applications against multiple lenders' credit policies. Focus should also be on making it extensible so that it’s easy to edit existing criteria and easy to add more kinds of policy checks.

**Time Limit:** 48 hours from receipt


## **Business Context**

You have been provided with [5 PDF documents](https://drive.google.com/drive/folders/1rypR66em2Qpdr9bCJZzsonkOYWGvn0Uo?usp=sharing) containing real equipment finance lender guidelines. Your task is to build a system that:

- Parses and normalizes these lender policies into a structured format

- Evaluates loan applications against each lender's criteria

- Identifies the best matching lenders with clear reasoning

- Easy to add and edit more checks/guidelines/rules for specific lenders.

- A well defined workflow or process to support adding more lenders. We receive new lender guidelines that we want to support in the form of PDFs


## **Technical Requirements**

### **Recommended Stack** 

This is what we use at Kaaj, you are free to use whatever you want

- **Backend:** Python with [FastAPI](https://fastapi.tiangolo.com/) 

- **Workflow Orchestration (optional, you can ignore but good to have):** Python + [Hatchet](https://hatchet.run/) 

- **Frontend:** React with [TypeScript](https://www.typescriptlang.org/) (you can use Tailwind framework)

- **Database:** [PostgreSQL](https://www.postgresql.org/)


### **Core Functionality**

#### **1. Lender Policy Management**

- Design a normalized schema to represent lender credit policies

- Support key criteria provided by the lender: FICO scores limits, PayNet scores limits, minimum time in business requirements, min/max loan amounts, equipment types, geographic restrictions, industry exclusions, and try to incorporate any other features you think are important

- A system to edit existing rules, add more rules. It should also support adding more lenders.


#### **2. The core flow**

Design a workflow that:

- Validates application completeness

- Derives necessary features (e.g., equipment age, business type)

- Ranks matches by fit score

- Persists results

Demonstrate proper use of Hatchet features including parallelization and retry logic.


#### **3. Matching Engine**

For each lender, determine:

- Eligibility (yes/no)

- Best matching program/tier if eligible

- Specific reasons for rejection if ineligible

- Fit score (0-100) for ranking


#### **4. User Interface**

Build a web application with:

- Loan application form that gets all required input from users

- Application detail view

- Results display showing matched/unmatched lenders with reasoning

  - Show detailed view of which criterias met and didn’t meet and why. Ex: Credit score criteria not met because minimum required score is 700 but the borrower’s score is 600

- Basic lender policy screen to view all the policies and potentially edit/add more policies


## **Data Model Considerations**

Design models for at minimum:

- Borrower/Business (industry, state, years in business, revenue)

- Personal Guarantor (FICO, credit history flags)

- Business Credit (PayNet score, trade lines)

- Loan Request (amount, term, equipment details)

- Lender Policies (programs, criteria, restrictions)

- Match Results


## **API Specification**

Implement RESTful endpoints for:

- CRUD operations on loan applications

- Lender policy management

- Underwriting run initiation and status

- Match results retrieval


## **Evaluation Criteria**

Your submission will be evaluated on:

1. **System Architecture** - Clean separation of concerns, appropriate abstractions

2. **Extensibility -** How easy it is to edit the policies after creating it the first time

3. **Policy Modeling** - How well you normalize and structure the lender requirements

4. **Matching Logic** - Accuracy and clarity of eligibility decisions

5. **User Experience** - Intuitive UI with good feedback mechanisms

6. **Code Quality** - TypeScript usage, error handling, testing approach


## **Deliverables**

1. Complete source code with setup instructions on github

2. README with:

   - Local development setup steps

   - Architecture overview

   - API documentation

3. `DECISIONS.md` documenting:

   - Which lender requirements you prioritized

   - Simplifications made and why

   - What you would add with more time


## **Provided Resources**

- [5 PDF files containing lender guidelines:](https://drive.google.com/drive/folders/1rypR66em2Qpdr9bCJZzsonkOYWGvn0Uo?usp=drive_link)

  1. Stearns Bank - Equipment Finance Credit Box

  2. Apex Commercial Capital - Broker Guidelines

  3. Advantage+ Financing - Broker ICP ($75K non-trucking)

  4. Citizens Bank - 2025 Equipment Finance Program

  5. Falcon Equipment Finance - Rates & Programs


## **Notes**

- Focus on demonstrating technical competence over feature completeness

- Make reasonable assumptions where requirements are ambiguous

- Document any significant design decisions

- Include at least basic tests for critical matching logic


## **Questions?**

If you need clarification on requirements, please reach out within the first 12 hours of receiving this assignment.
