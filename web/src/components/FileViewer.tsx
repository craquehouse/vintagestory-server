/**
 * FileViewer component for displaying JSON configuration file contents.
 *
 * Displays formatted JSON content in a read-only viewer.
 * Handles loading, empty, and error states.
 * Supports optional word wrap toggle for long lines.
 *
 * Story 6.6: File Manager UI - AC: 2, 3, 4
 * Polish UI-022: Word wrap support
 */

import { AlertCircle, FileText, WrapText } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { Skeleton } from '@/components/ui/skeleton';

/**
 * Props for the FileViewer component.
 */
export interface FileViewerProps {
  /**
   * The filename being viewed (for display purposes).
   */
  filename: string | null;
  /**
   * The JSON content to display.
   */
  content: unknown;
  /**
   * Whether the content is loading.
   */
  isLoading?: boolean;
  /**
   * Error message if content failed to load.
   */
  error?: string | null;
  /**
   * Whether word wrap is enabled.
   */
  wordWrap?: boolean;
  /**
   * Callback when word wrap toggle is clicked.
   */
  onWordWrapChange?: (enabled: boolean) => void;
  /**
   * Additional CSS class names.
   */
  className?: string;
}

/**
 * Component for displaying JSON configuration file contents.
 *
 * @example
 * <FileViewer
 *   filename="serverconfig.json"
 *   content={{ ServerName: "My Server", Port: 42420 }}
 * />
 */
export function FileViewer({
  filename,
  content,
  isLoading = false,
  error = null,
  wordWrap = false,
  onWordWrapChange,
  className,
}: FileViewerProps) {
  // Loading state
  if (isLoading) {
    return (
      <div className={className} data-testid="file-viewer-loading">
        <div className="space-y-2 p-4">
          <Skeleton className="h-4 w-3/4" />
          <Skeleton className="h-4 w-1/2" />
          <Skeleton className="h-4 w-5/6" />
          <Skeleton className="h-4 w-2/3" />
          <Skeleton className="h-4 w-4/5" />
          <Skeleton className="h-4 w-1/2" />
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className={className} data-testid="file-viewer-error">
        <div className="flex flex-col items-center justify-center p-6 text-center">
          <AlertCircle className="h-12 w-12 text-destructive" />
          <p className="mt-2 font-medium text-destructive">
            Failed to load file
          </p>
          <p className="mt-1 text-sm text-muted-foreground">
            {error}
          </p>
        </div>
      </div>
    );
  }

  // No file selected state
  if (!filename) {
    return (
      <div className={className} data-testid="file-viewer-empty">
        <div className="flex flex-col items-center justify-center p-6 text-center">
          <FileText className="h-12 w-12 text-muted-foreground/50" />
          <p className="mt-2 text-sm text-muted-foreground">
            Select a file to view its contents
          </p>
        </div>
      </div>
    );
  }

  // Content display
  const formattedContent = JSON.stringify(content, null, 2);

  return (
    <div className={cn('flex flex-col', className)} data-testid="file-viewer">
      <div className="border-b px-4 py-2 bg-muted/30 flex items-center justify-between">
        <span className="text-sm font-medium text-muted-foreground">
          {filename}
        </span>
        {onWordWrapChange && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onWordWrapChange(!wordWrap)}
            className={cn(
              'h-7 w-7 p-0',
              wordWrap && 'bg-accent text-accent-foreground'
            )}
            title={wordWrap ? 'Disable word wrap' : 'Enable word wrap'}
            data-testid="file-viewer-wrap-toggle"
          >
            <WrapText className="h-4 w-4" />
          </Button>
        )}
      </div>
      <div className="flex-1 overflow-auto p-4">
        <pre
          className={cn(
            'font-mono text-sm',
            wordWrap
              ? 'whitespace-pre-wrap break-words'
              : 'whitespace-pre overflow-x-auto'
          )}
          data-testid="file-viewer-content"
        >
          {formattedContent}
        </pre>
      </div>
    </div>
  );
}
