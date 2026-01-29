import { useState, useCallback } from 'react';
import { Upload, FileText, X } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

interface PDFUploaderProps {
  onFileSelect: (file: File) => void;
  isUploading?: boolean;
  error?: string | null;
}

export function PDFUploader({ onFileSelect, isUploading, error }: PDFUploaderProps) {
  const [dragActive, setDragActive] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setDragActive(false);

      if (e.dataTransfer.files && e.dataTransfer.files[0]) {
        const file = e.dataTransfer.files[0];
        if (file.type === 'application/pdf') {
          setSelectedFile(file);
          onFileSelect(file);
        } else {
          alert('Please upload a PDF file');
        }
      }
    },
    [onFileSelect]
  );

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      e.preventDefault();
      if (e.target.files && e.target.files[0]) {
        const file = e.target.files[0];
        if (file.type === 'application/pdf') {
          setSelectedFile(file);
          onFileSelect(file);
        } else {
          alert('Please upload a PDF file');
        }
      }
    },
    [onFileSelect]
  );

  const handleRemove = useCallback(() => {
    setSelectedFile(null);
  }, []);

  return (
    <div className="w-full space-y-4">
      {!selectedFile ? (
        <label
          htmlFor="file-upload"
          className={cn(
            "relative flex flex-col items-center justify-center w-full h-64 rounded-lg border-2 border-dashed cursor-pointer transition-colors duration-200",
            dragActive
              ? "border-primary bg-primary/5"
              : "border-muted-foreground/25 hover:border-primary/50 hover:bg-muted/50",
            isUploading && "opacity-50 pointer-events-none"
          )}
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
        >
          <input
            type="file"
            id="file-upload"
            className="hidden"
            accept=".pdf"
            onChange={handleChange}
            disabled={isUploading}
          />

          <div className="flex flex-col items-center justify-center pt-5 pb-6 px-4 text-center">
            <div className="mb-4 p-4 rounded-full bg-muted">
              <Upload className="w-8 h-8 text-muted-foreground" />
            </div>
            <p className="mb-2 text-lg font-medium text-foreground">
              Drop PDF here or click to upload
            </p>
            <p className="text-sm text-muted-foreground">
              Upload lender policy PDF for automatic extraction
            </p>
            <p className="text-xs text-muted-foreground mt-4">
              Maximum file size: 10MB
            </p>
          </div>
        </label>
      ) : (
        <Card className="bg-green-50 border-green-200">
          <CardContent className="p-4 flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <div className="p-2 bg-green-100 rounded-full">
                <FileText className="w-6 h-6 text-green-600" />
              </div>
              <div>
                <p className="font-medium text-gray-900">{selectedFile.name}</p>
                <p className="text-sm text-gray-500">
                  {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
                </p>
              </div>
            </div>
            {!isUploading && (
              <Button
                variant="ghost"
                size="icon"
                onClick={handleRemove}
                className="text-gray-500 hover:text-red-600 hover:bg-red-50"
              >
                <X className="w-5 h-5" />
              </Button>
            )}
          </CardContent>
        </Card>
      )}

      {error && (
        <div className="rounded-md bg-destructive/15 p-4 text-sm text-destructive font-medium border border-destructive/20">
          {error}
        </div>
      )}

      {isUploading && (
        <Card className="border-blue-200 bg-blue-50">
          <CardContent className="p-4">
            <div className="flex items-center space-x-3">
              <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-600"></div>
              <p className="text-sm font-medium text-blue-700">Extracting policy data from PDF...</p>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
