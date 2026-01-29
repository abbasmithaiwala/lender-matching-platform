import axios from 'axios';
import type {
  ExtractionResult,
  ExtractionListResponse,
  ApprovalResponse,
  UpdateExtractionRequest,
} from '../types/policy-extraction';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
const BASE_PATH = '/api/v1/policy-extraction';

export const policyExtractionService = {
  /**
   * Upload a PDF file and extract policies
   */
  async uploadAndExtract(
    file: File,
    options?: { enhance?: boolean; validate?: boolean }
  ): Promise<ExtractionResult> {
    const formData = new FormData();
    formData.append('file', file);

    const params = new URLSearchParams();
    if (options?.enhance !== undefined) {
      params.append('enhance', String(options.enhance));
    }
    if (options?.validate !== undefined) {
      params.append('validate_extraction', String(options.validate));
    }

    const response = await axios.post<ExtractionResult>(
      `${API_BASE_URL}${BASE_PATH}/upload?${params.toString()}`,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    );

    return response.data;
  },

  /**
   * List all extractions
   */
  async listExtractions(): Promise<ExtractionListResponse> {
    const response = await axios.get<ExtractionListResponse>(
      `${API_BASE_URL}${BASE_PATH}`
    );
    return response.data;
  },

  /**
   * Get extraction by ID
   */
  async getExtraction(extractionId: string): Promise<ExtractionResult> {
    const response = await axios.get<ExtractionResult>(
      `${API_BASE_URL}${BASE_PATH}/${extractionId}`
    );
    return response.data;
  },

  /**
   * Update extraction data
   */
  async updateExtraction(
    extractionId: string,
    data: UpdateExtractionRequest
  ): Promise<ExtractionResult> {
    const response = await axios.put<ExtractionResult>(
      `${API_BASE_URL}${BASE_PATH}/${extractionId}`,
      data
    );
    return response.data;
  },

  /**
   * Approve extraction and save to database
   */
  async approveExtraction(extractionId: string): Promise<ApprovalResponse> {
    const response = await axios.post<ApprovalResponse>(
      `${API_BASE_URL}${BASE_PATH}/${extractionId}/approve`
    );
    return response.data;
  },

  /**
   * Delete extraction
   */
  async deleteExtraction(extractionId: string): Promise<void> {
    await axios.delete(`${API_BASE_URL}${BASE_PATH}/${extractionId}`);
  },
};
