/**
 * FileManagerPanel component for browsing and viewing configuration files.
 *
 * Composes FileList and FileViewer in a split layout with selection state.
 * Uses hooks to fetch file list and content from the API.
 *
 * Story 6.6: File Manager UI - AC: 1, 2, 3, 4, 5
 */

import { useState } from 'react';
import { AlertCircle } from 'lucide-react';
import { cn } from '@/lib/utils';
import { FileList } from '@/components/FileList';
import { FileViewer } from '@/components/FileViewer';
import { useConfigFiles, useConfigFileContent } from '@/hooks/use-config-files';

/**
 * Props for the FileManagerPanel component.
 */
export interface FileManagerPanelProps {
  /**
   * Additional CSS class names.
   */
  className?: string;
}

/**
 * Panel for browsing and viewing configuration files.
 *
 * Displays a file list on the left and file viewer on the right.
 * Manages file selection state and data fetching.
 *
 * @example
 * <FileManagerPanel />
 */
export function FileManagerPanel({ className }: FileManagerPanelProps) {
  const [selectedFile, setSelectedFile] = useState<string | null>(null);

  // Fetch file list
  const {
    data: filesData,
    isLoading: isLoadingFiles,
    error: filesError,
  } = useConfigFiles();

  // Fetch selected file content
  const {
    data: contentData,
    isLoading: isLoadingContent,
    error: contentError,
  } = useConfigFileContent(selectedFile);

  // Handle file selection
  const handleSelectFile = (filename: string) => {
    setSelectedFile(filename);
  };

  // Error state for file list
  if (filesError) {
    return (
      <div className={className} data-testid="file-manager-error">
        <div className="flex items-center gap-2 rounded-lg border border-destructive/50 bg-destructive/10 p-4">
          <AlertCircle className="h-5 w-5 text-destructive" />
          <div>
            <p className="font-medium text-destructive">Failed to load files</p>
            <p className="text-sm text-muted-foreground">
              {filesError.message || 'Unable to load configuration files'}
            </p>
          </div>
        </div>
      </div>
    );
  }

  const files = filesData?.data?.files ?? [];

  return (
    <div
      className={cn('flex h-[500px] rounded-lg border bg-card', className)}
      data-testid="file-manager-panel"
    >
      {/* File List - Left Side */}
      <div className="w-56 shrink-0 border-r">
        <FileList
          files={files}
          selectedFile={selectedFile}
          isLoading={isLoadingFiles}
          onSelectFile={handleSelectFile}
          className="h-full"
        />
      </div>

      {/* File Viewer - Right Side */}
      <div className="flex-1 min-w-0">
        <FileViewer
          filename={selectedFile}
          content={contentData?.data?.content ?? null}
          isLoading={isLoadingContent}
          error={contentError?.message ?? null}
          className="h-full"
        />
      </div>
    </div>
  );
}
