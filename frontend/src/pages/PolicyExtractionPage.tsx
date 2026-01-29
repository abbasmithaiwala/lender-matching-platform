import { useReducer } from 'react';
import { ArrowLeft, ArrowRight, Check, HelpCircle } from 'lucide-react';
import { PDFUploader } from '../components/admin/PDFUploader';
import { ExtractedPolicyReview } from '../components/admin/ExtractedPolicyReview';
import { policyExtractionService } from '../services/policyExtractionService';
import type { ExtractionResult, ExtractedLender, ExtractedProgram } from '../types/policy-extraction';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

interface ApiError {
  response?: {
    data?: {
      detail?: string;
    };
  };
  message?: string;
}

interface PageState {
  isUploading: boolean;
  uploadError: string | null;
  extraction: ExtractionResult | null;
  isApproving: boolean;
  approvalSuccess: boolean;
  approvalMessage: string;
}

type PageAction =
  | { type: 'UPLOAD_START' }
  | { type: 'UPLOAD_SUCCESS'; payload: ExtractionResult }
  | { type: 'UPLOAD_ERROR'; payload: string }
  | { type: 'UPDATE_EXTRACTION'; payload: ExtractionResult }
  | { type: 'APPROVE_START' }
  | { type: 'APPROVE_SUCCESS'; payload: string }
  | { type: 'APPROVE_ERROR' }
  | { type: 'DELETE_SUCCESS' }
  | { type: 'RESET' };

const initialState: PageState = {
  isUploading: false,
  uploadError: null,
  extraction: null,
  isApproving: false,
  approvalSuccess: false,
  approvalMessage: '',
};

function pageReducer(state: PageState, action: PageAction): PageState {
  switch (action.type) {
    case 'UPLOAD_START':
      return {
        ...state,
        isUploading: true,
        uploadError: null,
        extraction: null,
        approvalSuccess: false,
      };
    case 'UPLOAD_SUCCESS':
      return {
        ...state,
        isUploading: false,
        extraction: action.payload,
      };
    case 'UPLOAD_ERROR':
      return {
        ...state,
        isUploading: false,
        uploadError: action.payload,
      };
    case 'UPDATE_EXTRACTION':
      return {
        ...state,
        extraction: action.payload,
      };
    case 'APPROVE_START':
      return {
        ...state,
        isApproving: true,
      };
    case 'APPROVE_SUCCESS':
      return {
        ...state,
        isApproving: false,
        approvalSuccess: true,
        approvalMessage: action.payload,
      };
    case 'APPROVE_ERROR':
      return {
        ...state,
        isApproving: false,
      };
    case 'DELETE_SUCCESS':
      return {
        ...state,
        extraction: null,
        uploadError: null,
      };
    case 'RESET':
      return {
        ...initialState,
      };
    default:
      return state;
  }
}

export function PolicyExtractionPage() {
  const [state, dispatch] = useReducer(pageReducer, initialState);

  const handleFileSelect = async (file: File) => {
    dispatch({ type: 'UPLOAD_START' });

    try {
      const result = await policyExtractionService.uploadAndExtract(file, {
        enhance: false,
        validate: false,
      });
      dispatch({ type: 'UPLOAD_SUCCESS', payload: result });
    } catch (error) {
      console.error('Upload failed:', error);
      const apiError = error as ApiError;
      const errorMessage =
        apiError.response?.data?.detail || 'Failed to extract policies from PDF. Please try again.';
      dispatch({ type: 'UPLOAD_ERROR', payload: errorMessage });
    }
  };

  const handleUpdate = async (lender: ExtractedLender, programs: ExtractedProgram[]) => {
    if (!state.extraction) return;

    try {
      const updated = await policyExtractionService.updateExtraction(state.extraction.extraction_id, {
        lender,
        programs,
      });
      dispatch({ type: 'UPDATE_EXTRACTION', payload: updated });
    } catch (error) {
      console.error('Update failed:', error);
      const apiError = error as ApiError;
      alert(apiError.response?.data?.detail || 'Failed to update extraction. Please try again.');
    }
  };

  const handleApprove = async () => {
    if (!state.extraction) return;

    dispatch({ type: 'APPROVE_START' });
    try {
      const response = await policyExtractionService.approveExtraction(state.extraction.extraction_id);
      dispatch({ type: 'APPROVE_SUCCESS', payload: response.message });

      // Reset after 3 seconds
      setTimeout(() => {
        dispatch({ type: 'RESET' });
      }, 3000);
    } catch (error) {
      console.error('Approval failed:', error);
      const apiError = error as ApiError;
      alert(
        apiError.response?.data?.detail || 'Failed to approve extraction. Please try again.'
      );
      dispatch({ type: 'APPROVE_ERROR' });
    }
  };

  const handleDiscard = async () => {
    if (!state.extraction) return;

    if (confirm('Are you sure you want to discard this extraction?')) {
      try {
        await policyExtractionService.deleteExtraction(state.extraction.extraction_id);
        dispatch({ type: 'DELETE_SUCCESS' });
      } catch (error) {
        console.error('Delete failed:', error);
        const apiError = error as ApiError;
        alert(apiError.response?.data?.detail || 'Failed to discard extraction. Please try again.');
      }
    }
  };

  const handleReset = () => {
    dispatch({ type: 'RESET' });
  };

  return (
    <div className="min-h-screen bg-muted/40 pb-20">
      {/* Header */}
      <div className="bg-background border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center space-x-4">
            {state.extraction && !state.approvalSuccess && (
              <Button
                variant="ghost"
                size="icon"
                onClick={handleReset}
                className="text-muted-foreground hover:text-foreground"
              >
                <ArrowLeft className="w-5 h-5" />
              </Button>
            )}
            <div>
              <h1 className="text-3xl font-bold text-foreground">Policy Extraction</h1>
              <p className="text-muted-foreground mt-1">
                Upload lender policy PDFs and review extracted data
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {state.approvalSuccess ? (
          // Success State
          <div className="max-w-md mx-auto mt-20">
            <Card className="border-green-200 bg-green-50 text-center shadow-lg">
              <CardContent className="pt-12 pb-12 flex flex-col items-center space-y-6">
                <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center animate-in zoom-in duration-300">
                  <Check className="w-10 h-10 text-green-600" />
                </div>
                <div className="space-y-2">
                  <h2 className="text-2xl font-bold text-green-900">
                    Lender Policy Approved!
                  </h2>
                  <p className="text-green-800 text-lg">{state.approvalMessage}</p>
                </div>
                <p className="text-sm text-green-600 animate-pulse">Redirecting to upload...</p>
              </CardContent>
            </Card>
          </div>
        ) : state.extraction ? (
          // Review State
          <ExtractedPolicyReview
            extraction={state.extraction}
            onApprove={handleApprove}
            onDiscard={handleDiscard}
            onUpdate={handleUpdate}
            isApproving={state.isApproving}
          />
        ) : (
          // Upload State
          <div className="max-w-3xl mx-auto space-y-8">
            <Card>
              <CardHeader>
                <CardTitle>Upload Lender Policy PDF</CardTitle>
                <CardDescription>
                  Upload a PDF file containing lender policy information. Our AI will automatically
                  extract lender details, programs, and rules for your review.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <PDFUploader
                  onFileSelect={handleFileSelect}
                  isUploading={state.isUploading}
                  error={state.uploadError}
                />

                {/* Instructions */}
                <div className="mt-8 p-4 bg-muted/50 rounded-lg border">
                  <h3 className="font-semibold mb-3 flex items-center gap-2">
                    <HelpCircle className="w-4 h-4" />
                    How it works:
                  </h3>
                  <ol className="space-y-3 text-sm text-muted-foreground">
                    {[
                      "Upload a lender policy PDF (max 10MB)",
                      "Our AI extracts lender information, programs, and rules",
                      "Review and edit the extracted data",
                      "Approve to save the policy to the database"
                    ].map((step, i) => (
                      <li key={i} className="flex items-start gap-3">
                        <span className="flex items-center justify-center w-5 h-5 rounded-full bg-primary/10 text-primary text-xs font-medium">
                          {i + 1}
                        </span>
                        <span>{step}</span>
                      </li>
                    ))}
                  </ol>
                </div>
              </CardContent>
            </Card>

            {/* Tips */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Tips for best results</CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="grid gap-3 sm:grid-cols-2">
                  {[
                    "Ensure the PDF is text-based, not a scanned image",
                    "PDFs with clear section headers work best",
                    "Review all extracted data before approving",
                    "You can edit any field before saving to the database"
                  ].map((tip, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm text-muted-foreground">
                      <ArrowRight className="w-4 h-4 text-primary shrink-0 mt-0.5" />
                      <span>{tip}</span>
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          </div>
        )}
      </div>
    </div>
  );
}
