"""Prompts for LLM-based policy extraction."""

POLICY_EXTRACTION_PROMPT = """You are analyzing a lender's credit policy document. Extract the following information in JSON format:

1. Lender Information:
   - name (string): The lender's name
   - description (string): Brief description of the lender
   - min_loan_amount (number): Minimum loan amount in dollars
   - max_loan_amount (number): Maximum loan amount in dollars
   - excluded_states (array): State codes where lender doesn't operate (e.g., ["CA", "NV", "ND", "VT"])
   - excluded_industries (array): Industries the lender doesn't serve (e.g., ["Cannabis", "Gambling"])

2. Programs/Tiers (array of programs):
   Each program should have:
   - program_name (string): Full name of the program/tier
   - program_code (string): Short code (e.g., "A", "B", "Medical A+", "Tier 1")
   - credit_tier (string): Credit tier classification (e.g., "A", "B", "C", "D")
   - min_fit_score (number): Minimum fit score 0-100 (default 60 if not specified)
   - description (string): Brief description of the program
   - eligibility_conditions (object): Program-specific requirements that determine if this program applies
     Examples:
     - {{"requires_paynet": true}} - Program requires PayNet score
     - {{"legal_structure": ["Corp", "LLC"]}} - Only for certain business structures
     - {{"industry": ["Medical", "Healthcare"]}} - Industry-specific programs
     - {{"equipment_type": ["Medical Equipment"]}} - Equipment-specific programs
     NOTE: These are checked BEFORE rule evaluation to select the right program
   - rate_metadata (object): Rate tables and adjustments
     Structure:
     - base_rates (array): [{{"min_amount": 10000, "max_amount": 50000, "min_term": 12, "max_term": 60, "rate": 7.25}}]
     - adjustments (array): [{{"condition": "equipment_age > 15", "delta": 0.5, "description": "Aged equipment"}}]
     NOTE: Rates should be stored as numbers (e.g., 7.25 for 7.25%)

3. Rules for each program (array):
   Each rule should have:
   - rule_type (string): One of these types:
     * "min_fico" - Minimum FICO score requirement
     * "min_paynet" - Minimum PayNet score requirement
     * "credit_tier" - Combined credit tier requirements
     * "time_in_business" - Years in business requirement
     * "min_revenue" - Minimum annual revenue requirement
     * "legal_structure" - Business structure requirements
     * "loan_amount_range" - Loan amount limits
     * "loan_term_range" - Loan term limits
     * "equipment_type" - Equipment type restrictions
     * "equipment_age" - Maximum equipment age
     * "equipment_condition" - Required equipment condition
     * "state_restriction" - State-level restrictions (rule-specific, not lender-level)
     * "industry_restriction" - Industry-level restrictions (rule-specific, not lender-level)
   - rule_name (string): Descriptive name for the rule
   - criteria (object): Rule-specific configuration, structure depends on rule_type
     Examples by rule_type:
     * min_fico: {{"min_score": 650}}
     * min_paynet: {{"min_score": 75}}
     * credit_tier: {{"allowed_tiers": ["A", "B"]}}
     * time_in_business: {{"min_years": 2}}
     * min_revenue: {{"min_amount": 100000}}
     * legal_structure: {{"allowed_structures": ["LLC", "Corp"]}}
     * loan_amount_range: {{"min_amount": 10000, "max_amount": 500000}}
     * loan_term_range: {{"min_months": 12, "max_months": 84}}
     * equipment_type: {{"allowed_types": ["Construction Equipment", "Medical Equipment"]}}
     * equipment_age: {{"max_years": 15}}
     * equipment_condition: {{"allowed_conditions": ["New", "Used"]}}
     * state_restriction: {{"excluded_states": ["CA", "NY"]}}
     * industry_restriction: {{"excluded_industries": ["Cannabis", "Gambling"]}}
   - weight (number): Scoring weight, typically 1.0 (higher = more important)
   - is_mandatory (boolean):
     * true = Hard requirement (must pass)
     * false = Guideline or soft requirement (preferred but not required)
     NOTE: Words like "guidelines", "preferred", "subject to lender discretion" indicate is_mandatory: false

CRITICAL EXTRACTION RULES:
1. **Lender-level vs Program-level vs Rule-level**:
   - Lender-level exclusions: States/industries where lender NEVER operates → excluded_states, excluded_industries
   - Program eligibility: Conditions that determine which program to use → eligibility_conditions
   - Rule-level: Specific criteria within a program → rules array

2. **Rate Information**:
   - Rate tables and adjustments go in rate_metadata, NOT in rules
   - Store rates as numbers (7.25, not "7.25%" or "0.0725")

3. **Hard vs Soft Requirements**:
   - "Must", "Required", "Minimum" = is_mandatory: true
   - "Guideline", "Preferred", "Subject to approval", "May consider" = is_mandatory: false

4. **Program Selection Logic**:
   - If document says "For PayNet deals only" or "Corp only" → put in eligibility_conditions
   - If it's a scoring criterion → put in rules

5. **Extract ALL programs/tiers** mentioned in the document, even if brief

6. **Default Values**:
   - min_fit_score: 60 (if not specified)
   - weight: 1.0 (if not specified)
   - is_mandatory: true (for explicit requirements), false (for guidelines)

Document content:
{content}

Return ONLY valid JSON matching this structure. Do not include any explanatory text outside the JSON.

Expected JSON structure:
{{
  "lender": {{
    "name": "string",
    "description": "string",
    "min_loan_amount": number,
    "max_loan_amount": number,
    "excluded_states": ["string"],
    "excluded_industries": ["string"]
  }},
  "programs": [
    {{
      "program_name": "string",
      "program_code": "string",
      "credit_tier": "string",
      "min_fit_score": number,
      "description": "string",
      "eligibility_conditions": {{}},
      "rate_metadata": {{
        "base_rates": [],
        "adjustments": []
      }},
      "rules": [
        {{
          "rule_type": "string",
          "rule_name": "string",
          "criteria": {{}},
          "weight": number,
          "is_mandatory": boolean
        }}
      ]
    }}
  ]
}}
"""

POLICY_VALIDATION_PROMPT = """Review the following extracted lender policy data and check for:
1. Missing required fields
2. Invalid data types or values
3. Inconsistencies or contradictions
4. Potential extraction errors

Extracted data:
{extracted_data}

Return a JSON object with:
{{
  "valid": boolean,
  "errors": [
    {{
      "field": "string (dot notation path)",
      "message": "string (error description)",
      "severity": "error|warning"
    }}
  ],
  "suggestions": [
    "string (improvement suggestions)"
  ]
}}
"""

POLICY_ENHANCEMENT_PROMPT = """Given the following partially extracted lender policy, fill in any missing standard fields and improve the structure:

Current extraction:
{extracted_data}

PDF content for reference:
{pdf_content}

Return the enhanced JSON with:
1. Filled standard fields (excluded_states, excluded_industries if missing)
2. Improved rule categorization
3. Better structured rate_metadata
4. Consistent program codes

Return ONLY the enhanced JSON, no explanatory text.
"""
