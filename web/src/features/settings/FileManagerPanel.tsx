/**
 * FileManagerPanel component for browsing and viewing configuration files.
 *
 * Composes FileList and FileViewer in a split layout with selection state.
 * Uses hooks to fetch file list and content from the API.
 *
 * Story 6.6: File Manager UI - AC: 1, 2, 3, 4, 5
 * Story 9.7: Dynamic File Browser - Directory navigation
 * Story 16.7: File Browser Breadcrumbs - path segments replace the Back button
 */

import { useState, useMemo } from 'react';
import { AlertCircle } from 'lucide-react';
import { cn } from '@/lib/utils';
import { FileList, type FileListItem } from '@/components/FileList';
import { FileViewer } from '@/components/FileViewer';
import { PathBreadcrumb } from '@/components/PathBreadcrumb';
import {
  useConfigFiles,
  useConfigFileContent,
  useConfigDirectories,
} from '@/hooks/use-config-files';

/** Label of the breadcrumb root: the serverdata directory the API lists (Story 16.7). */
const ROOT_LABEL = 'serverdata';

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
 * Supports directory navigation (Story 9.7) with a breadcrumb of the current path
 * across the top of the panel (Story 16.7).
 *
 * @example
 * <FileManagerPanel />
 */
export function FileManagerPanel({ className }: FileManagerPanelProps) {
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [wordWrap, setWordWrap] = useState(false);
  // Story 9.7: Current directory path (null = root)
  const [currentDirectory, setCurrentDirectory] = useState<string | null>(null);

  // Fetch directories for the current path (Story 9.7 - nested directory support)
  const { data: directoriesData, isLoading: isLoadingDirectories } =
    useConfigDirectories(currentDirectory ?? undefined);

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

    // Show directories at any level (Story 9.7 - nested directory support)
    if (directoriesData?.data?.directories) {
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
  }, [directoriesData, filesData]);

  // Handle file selection
  const handleSelectFile = (filename: string) => {
    // If in a subdirectory, prepend the directory path
    const fullPath = currentDirectory
      ? `${currentDirectory}/${filename}`
      : filename;
    setSelectedFile(fullPath);
  };

  // Handle directory navigation (Story 9.7 - nested directory support)
  const handleSelectDirectory = (dirname: string) => {
    // Build full path by appending to current directory
    const newPath = currentDirectory
      ? `${currentDirectory}/${dirname}`
      : dirname;
    setCurrentDirectory(newPath);
    setSelectedFile(null); // Clear selection when changing directories
  };

  // Breadcrumb navigation to the root (null) or an ancestor of the current path (Story 16.7)
  const handleNavigate = (path: string | null) => {
    setCurrentDirectory(path);
    setSelectedFile(null);
  };

  const breadcrumb = (
    <PathBreadcrumb path={currentDirectory} rootLabel={ROOT_LABEL} onNavigate={handleNavigate} />
  );

  // Combined loading state
  const isLoading = isLoadingFiles || isLoadingDirectories;

  // Error state for file list
  if (filesError) {
    return (
      <div className={className} data-testid="file-manager-error">
        {/* Keep the breadcrumb so a failed subdirectory is not a dead end (Story 16.7) */}
        {currentDirectory && <div className="mb-2 px-1">{breadcrumb}</div>}
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
      className={cn('flex h-[500px] flex-col rounded-lg border bg-card', className)}
      data-testid="file-manager-panel"
    >
      {/* Current path across the panel (Story 16.7) */}
      <div className="min-w-0 border-b px-3 py-2" data-testid="file-manager-breadcrumb-bar">
        {breadcrumb}
      </div>

      <div className="flex min-h-0 flex-1">
        {/* File List - Left Side */}
        <div className="w-56 shrink-0 border-r flex flex-col">
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
    </div>
  );
}
