/**
 * FileList component for displaying a list of configuration files and directories.
 *
 * Displays a list of file/directory names with selection support.
 * Handles loading, empty, and error states.
 *
 * Story 6.6: File Manager UI - AC: 1, 4, 5
 * Story 9.7: Dynamic File Browser - Directory support
 */

import { File, Folder, FolderOpen } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Skeleton } from '@/components/ui/skeleton';

/**
 * Represents an item in the file list (file or directory).
 */
export interface FileListItem {
  name: string;
  type: 'file' | 'directory';
}

/**
 * Props for the FileList component.
 */
export interface FileListProps {
  /**
   * List of file names to display (legacy support).
   */
  files?: string[];
  /**
   * List of items (files and directories) to display.
   * Takes precedence over `files` if both are provided.
   */
  items?: FileListItem[];
  /**
   * Currently selected item name (if any).
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
   * Callback when a directory is selected (Story 9.7).
   */
  onSelectDirectory?: (dirname: string) => void;
  /**
   * Additional CSS class names.
   */
  className?: string;
}

/**
 * Component for displaying a list of configuration files and directories.
 *
 * @example
 * <FileList
 *   files={['serverconfig.json', 'worldconfig.json']}
 *   selectedFile="serverconfig.json"
 *   onSelectFile={(file) => setSelectedFile(file)}
 * />
 *
 * @example
 * // With directories (Story 9.7)
 * <FileList
 *   items={[
 *     { name: 'ModConfigs', type: 'directory' },
 *     { name: 'serverconfig.json', type: 'file' },
 *   ]}
 *   selectedFile={selectedFile}
 *   onSelectFile={(file) => setSelectedFile(file)}
 *   onSelectDirectory={(dir) => navigateToDir(dir)}
 * />
 */
export function FileList({
  files,
  items,
  selectedFile,
  isLoading = false,
  onSelectFile,
  onSelectDirectory,
  className,
}: FileListProps) {
  // Convert files to items format if items not provided
  const displayItems: FileListItem[] =
    items ?? (files?.map((f) => ({ name: f, type: 'file' as const })) ?? []);

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
  if (displayItems.length === 0) {
    return (
      <div
        className={className}
        data-testid="file-list-empty"
        role="status"
        aria-label="No configuration files available"
      >
        <div className="flex flex-col items-center justify-center p-6 text-center">
          <FolderOpen
            className="h-12 w-12 text-muted-foreground/50"
            aria-hidden="true"
          />
          <p className="mt-2 text-sm text-muted-foreground">
            No configuration files found
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className={className} data-testid="file-list">
      <ul
        className="space-y-1 p-2"
        role="listbox"
        aria-label="Configuration files"
      >
        {displayItems.map((item) => {
          const isSelected = item.name === selectedFile;
          const isDirectory = item.type === 'directory';
          const Icon = isDirectory ? Folder : File;

          return (
            <li key={item.name}>
              <button
                type="button"
                role="option"
                aria-selected={isSelected}
                data-testid={`file-item-${item.name}`}
                className={cn(
                  'flex w-full items-center gap-2 rounded-md px-3 py-2 text-left text-sm transition-colors',
                  'hover:bg-accent hover:text-accent-foreground',
                  'focus:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                  isSelected && 'bg-accent text-accent-foreground font-medium',
                  isDirectory && 'text-primary'
                )}
                onClick={() => {
                  if (isDirectory && onSelectDirectory) {
                    onSelectDirectory(item.name);
                  } else if (!isDirectory) {
                    onSelectFile(item.name);
                  }
                }}
              >
                <Icon className="h-4 w-4 shrink-0" />
                <span className="truncate">{item.name}</span>
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
