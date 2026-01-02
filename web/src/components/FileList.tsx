/**
 * FileList component for displaying a list of configuration files.
 *
 * Displays a list of file names with selection support.
 * Handles loading, empty, and error states.
 *
 * Story 6.6: File Manager UI - AC: 1, 4, 5
 */

import { File, FolderOpen } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Skeleton } from '@/components/ui/skeleton';

/**
 * Props for the FileList component.
 */
export interface FileListProps {
  /**
   * List of file names to display.
   */
  files: string[];
  /**
   * Currently selected file name (if any).
   */
  selectedFile: string | null;
  /**
   * Whether the file list is loading.
   */
  isLoading?: boolean;
  /**
   * Callback when a file is selected.
   */
  onSelectFile: (filename: string) => void;
  /**
   * Additional CSS class names.
   */
  className?: string;
}

/**
 * Component for displaying a list of configuration files.
 *
 * @example
 * <FileList
 *   files={['serverconfig.json', 'worldconfig.json']}
 *   selectedFile="serverconfig.json"
 *   onSelectFile={(file) => setSelectedFile(file)}
 * />
 */
export function FileList({
  files,
  selectedFile,
  isLoading = false,
  onSelectFile,
  className,
}: FileListProps) {
  // Loading state
  if (isLoading) {
    return (
      <div className={className} data-testid="file-list-loading">
        <div className="space-y-2 p-2">
          <Skeleton className="h-8 w-full" />
          <Skeleton className="h-8 w-full" />
          <Skeleton className="h-8 w-3/4" />
        </div>
      </div>
    );
  }

  // Empty state
  if (files.length === 0) {
    return (
      <div
        className={className}
        data-testid="file-list-empty"
        role="status"
        aria-label="No configuration files available"
      >
        <div className="flex flex-col items-center justify-center p-6 text-center">
          <FolderOpen className="h-12 w-12 text-muted-foreground/50" aria-hidden="true" />
          <p className="mt-2 text-sm text-muted-foreground">
            No configuration files found
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className={className} data-testid="file-list">
      <ul className="space-y-1 p-2" role="listbox" aria-label="Configuration files">
        {files.map((filename) => {
          const isSelected = filename === selectedFile;
          return (
            <li key={filename}>
              <button
                type="button"
                role="option"
                aria-selected={isSelected}
                data-testid={`file-item-${filename}`}
                className={cn(
                  'flex w-full items-center gap-2 rounded-md px-3 py-2 text-left text-sm transition-colors',
                  'hover:bg-accent hover:text-accent-foreground',
                  'focus:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                  isSelected && 'bg-accent text-accent-foreground font-medium'
                )}
                onClick={() => onSelectFile(filename)}
              >
                <File className="h-4 w-4 shrink-0" />
                <span className="truncate">{filename}</span>
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
