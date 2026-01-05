/**
 * FileManagerPanel component for browsing and viewing configuration files.
 *
 * Composes FileList and FileViewer in a split layout with selection state.
 * Uses hooks to fetch file list and content from the API.
 *
 * Story 6.6: File Manager UI - AC: 1, 2, 3, 4, 5
 * Story 9.7: Dynamic File Browser - Directory navigation
 */

import { useState, useMemo } from 'react';
import { AlertCircle, ChevronLeft } from 'lucide-react';
import { cn } from '@/lib/utils';
import { FileList, type FileListItem } from '@/components/FileList';
import { FileViewer } from '@/components/FileViewer';
import {
  useConfigFiles,
  useConfigFileContent,
  useConfigDirectories,
} from '@/hooks/use-config-files';
import { Button } from '@/components/ui/button';

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
 * Supports directory navigation (Story 9.7).
 *
 * @example
 * <FileManagerPanel />
 */
export function FileManagerPanel({ className }: FileManagerPanelProps) {
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [wordWrap, setWordWrap] = useState(false);
  // Story 9.7: Current directory path (null = root)
  const [currentDirectory, setCurrentDirectory] = useState<string | null>(null);

  // Fetch directories (Story 9.7)
  const { data: directoriesData, isLoading: isLoadingDirectories } =
    useConfigDirectories();

  // Fetch file list (with directory support - Story 9.7)
  const {
    data: filesData,
    isLoading: isLoadingFiles,
    error: filesError,
  } = useConfigFiles(currentDirectory ?? undefined);

  // Fetch selected file content
  const {
    data: contentData,
    isLoading: isLoadingContent,
    error: contentError,
  } = useConfigFileContent(selectedFile);

  // Combine directories and files into items list
  const items = useMemo<FileListItem[]>(() => {
    const result: FileListItem[] = [];

    // Only show directories at root level
    if (!currentDirectory && directoriesData?.data?.directories) {
      // Filter hidden directories by default
      const visibleDirs = directoriesData.data.directories.filter(
        (d) => !d.startsWith('.')
      );
      for (const dir of visibleDirs) {
        result.push({ name: dir, type: 'directory' });
      }
    }

    // Add files
    if (filesData?.data?.files) {
      for (const file of filesData.data.files) {
        result.push({ name: file, type: 'file' });
      }
    }

    return result;
  }, [currentDirectory, directoriesData, filesData]);

  // Handle file selection
  const handleSelectFile = (filename: string) => {
    // If in a subdirectory, prepend the directory path
    const fullPath = currentDirectory
      ? `${currentDirectory}/${filename}`
      : filename;
    setSelectedFile(fullPath);
  };

  // Handle directory navigation (Story 9.7)
  const handleSelectDirectory = (dirname: string) => {
    setCurrentDirectory(dirname);
    setSelectedFile(null); // Clear selection when changing directories
  };

  // Handle back navigation (Story 9.7)
  const handleNavigateBack = () => {
    setCurrentDirectory(null);
    setSelectedFile(null);
  };

  // Combined loading state
  const isLoading =
    isLoadingFiles || (!currentDirectory && isLoadingDirectories);

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

  return (
    <div
      className={cn('flex h-[500px] rounded-lg border bg-card', className)}
      data-testid="file-manager-panel"
    >
      {/* File List - Left Side */}
      <div className="w-56 shrink-0 border-r flex flex-col">
        {/* Back button when in subdirectory (Story 9.7) */}
        {currentDirectory && (
          <div className="border-b p-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={handleNavigateBack}
              className="w-full justify-start gap-2"
              data-testid="file-manager-back"
            >
              <ChevronLeft className="h-4 w-4" />
              <span className="truncate">{currentDirectory}</span>
            </Button>
          </div>
        )}
        <FileList
          items={items}
          selectedFile={selectedFile}
          isLoading={isLoading}
          onSelectFile={handleSelectFile}
          onSelectDirectory={handleSelectDirectory}
          className="flex-1 overflow-auto"
        />
      </div>

      {/* File Viewer - Right Side */}
      <div className="flex-1 min-w-0">
        <FileViewer
          filename={selectedFile}
          content={contentData?.data?.content ?? null}
          isLoading={isLoadingContent}
          error={contentError?.message ?? null}
          wordWrap={wordWrap}
          onWordWrapChange={setWordWrap}
          className="h-full"
        />
      </div>
    </div>
  );
}
