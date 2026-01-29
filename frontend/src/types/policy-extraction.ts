// TypeScript types for policy extraction

export interface ExtractedLender {
  name: string;
  description?: string;
  min_loan_amount: number;
  max_loan_amount: number;
  excluded_states?: string[];
  excluded_industries?: string[];
}

export interface RateTable {
  min_amount?: number;
  max_amount?: number;
  min_term?: number;
  max_term?: number;
  rate: number;
}

export interface RateAdjustment {
  condition: string;
  delta: number;
  description?: string;
}

export interface RateMetadata {
  base_rates?: RateTable[];
  adjustments?: RateAdjustment[];
}

export interface ExtractedRule {
  rule_type: string;
  rule_name: string;
  criteria: Record<string, unknown>;
  weight?: number;
  is_mandatory?: boolean;
}

export interface ExtractedProgram {
  program_name: string;
  program_code: string;
  credit_tier: string;
  min_fit_score?: number;
  description?: string;
  eligibility_conditions?: Record<string, unknown>;
  rate_metadata?: RateMetadata;
  rules?: ExtractedRule[];
}

export interface ExtractedPolicyData {
  lender: ExtractedLender;
  programs: ExtractedProgram[];
}

export interface ValidationError {
  field: string;
  message: string;
  severity: 'error' | 'warning';
}

export interface ValidationResult {
  valid: boolean;
  errors?: ValidationError[];
  suggestions?: string[];
}

export interface ExtractionMetadata {
  pdf_characters: number;
  programs_count: number;
  total_rules: number;
  enhanced: boolean;
  validated: boolean;
}

export interface PDFMetadata {
  title?: string;
  author?: string;
  subject?: string;
  creator?: string;
  producer?: string;
  creation_date?: string;
  modification_date?: string;
  page_count: number;
}

export interface ExtractionResult {
  extraction_id: string;
  status: 'success' | 'failed' | 'processing';
  pdf_filename: string;
  pdf_metadata?: PDFMetadata;
  extracted_data?: ExtractedPolicyData;
  validation?: ValidationResult;
  extraction_metadata?: ExtractionMetadata;
  error?: string;
  error_type?: string;
  created_at: string;
}

export interface ExtractionListItem {
  extraction_id: string;
  pdf_filename: string;
  status: string;
  lender_name?: string;
  programs_count: number;
  created_at: string;
  approved: boolean;
}

export interface ExtractionListResponse {
  extractions: ExtractionListItem[];
  total: number;
}

export interface ApprovalResponse {
  success: boolean;
  message: string;
  lender_id?: string;
  program_ids?: string[];
}

export interface UpdateLenderRequest {
  name?: string;
  description?: string;
  min_loan_amount?: number;
  max_loan_amount?: number;
  excluded_states?: string[];
  excluded_industries?: string[];
}

export interface UpdateExtractionRequest {
  lender?: UpdateLenderRequest;
  programs?: ExtractedProgram[];
}
