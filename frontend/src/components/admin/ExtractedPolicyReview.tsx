import { CheckCircle, XCircle, AlertTriangle, FileText } from 'lucide-react';
import type { ExtractionResult, ExtractedLender, ExtractedProgram } from '../../types/policy-extraction';
import { PolicyEditor } from './PolicyEditor';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
interface ExtractedPolicyReviewProps {
  extraction: ExtractionResult;
  onApprove: () => void;
  onDiscard: () => void;
  onUpdate: (lender: ExtractedLender, programs: ExtractedProgram[]) => void;
  isApproving?: boolean;
}

export function ExtractedPolicyReview({
  extraction,
  onApprove,
  onDiscard,
  onUpdate,
  isApproving,
}: ExtractedPolicyReviewProps) {

  if (extraction.status === 'failed') {
    return (
      <Alert variant="destructive">
        <XCircle className="h-4 w-4" />
        <AlertTitle>Extraction Failed</AlertTitle>
        <AlertDescription>
          <div className="mt-2">
            <p className="mb-2">{extraction.error || 'Unknown error occurred'}</p>
            {extraction.error_type && (
              <p className="text-sm opacity-90">Error Type: {extraction.error_type}</p>
            )}
            <div className="mt-4">
              <Button onClick={onDiscard} variant="outline" className="bg-white/10 text-white hover:bg-white/20 border-white/20">
                Discard
              </Button>
            </div>
          </div>
        </AlertDescription>
      </Alert>
    );
  }

  if (!extraction.extracted_data) {
    return (
      <Alert className="border-yellow-200 bg-yellow-50 text-yellow-900">
        <AlertTriangle className="h-4 w-4 text-yellow-600" />
        <AlertTitle>No Data Extracted</AlertTitle>
        <AlertDescription>
          The extraction completed but no policy data was found.
        </AlertDescription>
      </Alert>
    );
  }

  const { lender, programs } = extraction.extracted_data;
  const validation = extraction.validation;
  const metadata = extraction.extraction_metadata;

  return (
    <div className="space-y-6">
      {/* Status Header */}
      <Card>
        <CardContent className="p-6">
          <div className="flex items-start justify-between">
            <div className="flex items-start space-x-4">
              <div className="mt-1 bg-green-100 p-2 rounded-full">
                <CheckCircle className="w-6 h-6 text-green-600" />
              </div>
              <div>
                <h2 className="text-xl font-bold text-gray-900">{lender.name}</h2>
                <div className="flex items-center space-x-2 text-gray-500 mt-1">
                  <FileText className="w-4 h-4" />
                  <span className="text-sm font-medium">{extraction.pdf_filename}</span>
                </div>

                <div className="flex flex-wrap gap-2 mt-3">
                  <Badge variant="secondary" className="font-normal">
                    {programs.length} programs
                  </Badge>
                  <Badge variant="secondary" className="font-normal">
                    {metadata?.total_rules || 0} total rules
                  </Badge>
                  {extraction.pdf_metadata && (
                    <Badge variant="secondary" className="font-normal">
                      {extraction.pdf_metadata.page_count} pages
                    </Badge>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* Extraction Metadata */}
          {metadata && (
            <div className="mt-6 pt-6 border-t grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <div>
                <p className="text-muted-foreground">Characters</p>
                <p className="font-medium">{metadata.pdf_characters.toLocaleString()}</p>
              </div>
              <div>
                <p className="text-muted-foreground">Enhanced</p>
                <p className="font-medium">{metadata.enhanced ? 'Yes' : 'No'}</p>
              </div>
              <div>
                <p className="text-muted-foreground">Validated</p>
                <p className="font-medium">{metadata.validated ? 'Yes' : 'No'}</p>
              </div>
              <div>
                <p className="text-muted-foreground">Status</p>
                <p className="font-medium text-green-600">Success</p>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Policy Editor */}
      <PolicyEditor lender={lender} programs={programs} onUpdate={onUpdate} />

      {/* Action Buttons */}
      <Card>
        <CardContent className="p-6 flex items-center justify-between">
          <div className="text-sm text-muted-foreground">
            Review the extracted data and make any necessary corrections before approving.
          </div>
          <div className="flex items-center space-x-3">
            <Button
              variant="outline"
              onClick={onDiscard}
              disabled={isApproving}
            >
              Discard
            </Button>
            <Button
              onClick={onApprove}
              disabled={isApproving}
              className="bg-green-600 hover:bg-green-700"
            >
              {isApproving ? (
                <>
                  <div className="mr-2 animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                  Approving...
                </>
              ) : (
                <>
                  <CheckCircle className="w-4 h-4 mr-2" />
                  Approve & Save
                </>
              )}
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
