/**
 * FileViewer component for displaying JSON configuration file contents.
 *
 * Displays formatted JSON content in a read-only viewer.
 * Handles loading, empty, and error states.
 * Supports optional word wrap toggle for long lines.
 * Applies syntax highlighting for JSON files.
 *
 * Story 6.6: File Manager UI - AC: 2, 3, 4
 * Story 9.6: JSON Syntax Colorization - AC: 1, 2, 3, 4
 * Polish UI-022: Word wrap support
 * Story 23.1: a file that cannot be parsed shows a warning and, for Admin, its text
 * Story 23.5: a file that parsed is shown to Admin as its text, with its comments, in a
 * read-only code view; the header takes actions (the Edit button)
 */

import type { ReactNode } from 'react';
import { AlertCircle, AlertTriangle, FileText, WrapText } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { Skeleton } from '@/components/ui/skeleton';
import { highlightJson, isJsonFile } from '@/lib/json-highlighter';
import type { ConfigParseError } from '@/api/types';
import { LazyCodeView } from '@/components/code-view/LazyCodeView';

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
   * Why the file did not parse (Story 23.1). When set, the warning and the text are
   * shown instead of `content`.
   */
  parseError?: ConfigParseError | null;
  /**
   * The file's text, which only an Admin key receives (Story 23.1).
   */
  text?: string;
  /**
   * Buttons shown in the header before the word-wrap toggle (Story 23.5: Edit).
   */
  actions?: ReactNode;
  /**
   * Additional CSS class names.
   */
  className?: string;
}

/** The warning's text: the message, and the position when it is known. */
function parseErrorText(parseError: ConfigParseError): string {
  const position =
    parseError.line !== null && parseError.column !== null
      ? ` (line ${parseError.line}, column ${parseError.column})`
      : '';
  return `This file could not be parsed: ${parseError.message}${position}`;
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
  parseError = null,
  text,
  actions,
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
          <p className="mt-2 font-medium text-destructive">Failed to load file</p>
          <p className="mt-1 text-sm text-muted-foreground">{error}</p>
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
          <p className="mt-2 text-sm text-muted-foreground">Select a file to view its contents</p>
        </div>
      </div>
    );
  }

  const preClass = cn(
    'font-mono text-sm',
    wordWrap ? 'whitespace-pre-wrap break-words' : 'whitespace-pre overflow-x-auto'
  );

  let body: ReactNode;
  if (parseError) {
    // Story 23.1 (Epic 23 ADR-2 decision 3): the warning, then the text for Admin
    body = (
      <>
        <div
          role="alert"
          className="mb-4 flex items-start gap-2 rounded-md border border-warning/20 bg-warning/10 p-3 text-sm text-warning"
          data-testid="file-viewer-parse-error"
        >
          <AlertTriangle className="mt-0.5 h-4 w-4 flex-shrink-0" aria-hidden="true" />
          <span>{parseErrorText(parseError)}</span>
        </div>
        {typeof text === 'string' ? (
          <pre className={preClass} data-testid="file-viewer-raw">
            {text}
          </pre>
        ) : (
          <p className="text-sm text-muted-foreground">
            The text of a file that cannot be parsed is shown only to an Admin key.
          </p>
        )}
      </>
    );
  } else if (typeof text === 'string') {
    // Story 23.5 (Epic 23 ADR-5 decision 7): Admin sees the text with its comments
    body = (
      <LazyCodeView
        value={text}
        readOnly
        wordWrap={wordWrap}
        ariaLabel={`Text of ${filename}`}
        data-testid="file-viewer-code"
      />
    );
  } else {
    // Apply JSON syntax highlighting for .json files, plain text otherwise
    const isJson = isJsonFile(filename);

    // Safely serialize content - handles non-serializable data gracefully
    let renderedContent: ReactNode;
    try {
      renderedContent = isJson ? highlightJson(content) : JSON.stringify(content, null, 2);
    } catch {
      // Fallback for non-serializable content (circular refs, functions, etc.)
      renderedContent = String(content);
    }
    body = (
      <pre className={preClass} data-testid="file-viewer-content">
        {renderedContent}
      </pre>
    );
  }

  return (
    <div className={cn('flex flex-col', className)} data-testid="file-viewer">
      <div className="border-b px-4 py-2 bg-muted/30 flex items-center justify-between">
        <span className="min-w-0 truncate text-sm font-medium text-muted-foreground">
          {filename}
        </span>
        <div className="flex shrink-0 items-center gap-2">
          {actions}
          {onWordWrapChange && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onWordWrapChange(!wordWrap)}
              className={cn('h-7 w-7 p-0', wordWrap && 'bg-accent text-accent-foreground')}
              title={wordWrap ? 'Disable word wrap' : 'Enable word wrap'}
              data-testid="file-viewer-wrap-toggle"
            >
              <WrapText className="h-4 w-4" />
            </Button>
          )}
        </div>
      </div>
      <div className="flex-1 overflow-auto p-4">{body}</div>
    </div>
  );
}
