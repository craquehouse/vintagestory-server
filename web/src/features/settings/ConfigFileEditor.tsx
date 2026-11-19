/**
 * ConfigFileEditor: edit a config file's text and save it (Story 23.5, FR319).
 *
 * Epic 23 ADR-5: a CodeMirror editor with the file's text; the text is checked by the API
 * once on opening and 500 ms after typing stops, and the status line shows "Valid" or the
 * error with a button that moves the cursor to it. Save sends the text with the version
 * of the file it was edited from; a refusal keeps the text and explains it. Only while
 * the game server is stopped (the API refuses otherwise).
 */

import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router';
import { toast } from 'sonner';
import { AlertCircle, CheckCircle2, Loader2, Pencil } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { LazyCodeView, type CodeViewHandle } from '@/components/code-view/LazyCodeView';
import { ApiError } from '@/api/errors';
import { parseErrorFromApiError } from '@/api/config';
import type { ConfigParseError } from '@/api/types';
import { useConfigTextCheck, useSaveConfigFile } from '@/hooks/use-config-files';
import { cn } from '@/lib/utils';
import { clearDraft, setDraft } from './config-drafts';
import { ConfirmDialog } from './ConfirmDialog';

export const SERVER_NOT_STOPPED_TEXT =
  'Stop the game server to edit files: the game can overwrite changes made while it runs.';

/** "line L, column C" when the position is known. */
function position(error: ConfigParseError): string | null {
  return error.line !== null && error.column !== null
    ? `line ${error.line}, column ${error.column}`
    : null;
}

/** The line under the Edit button or the editor while the server is not stopped (AC 5). */
export function ServerNotStoppedNote({ id }: { id?: string }) {
  return (
    <p id={id} className="text-xs text-muted-foreground" data-testid="config-editor-server-note">
      {SERVER_NOT_STOPPED_TEXT}{' '}
      <Link to="/" className="underline underline-offset-2 hover:text-foreground">
        Go to the server controls
      </Link>
    </p>
  );
}

export interface EditFileButtonProps {
  disabled: boolean;
  resume: boolean;
  describedBy?: string;
  onClick: () => void;
}

/** The viewer header's Edit button (Story 23.5). */
export function EditFileButton({ disabled, resume, describedBy, onClick }: EditFileButtonProps) {
  return (
    <Button
      type="button"
      variant="outline"
      size="sm"
      className="min-h-11 md:min-h-8"
      disabled={disabled}
      aria-describedby={describedBy}
      onClick={onClick}
      data-testid="file-viewer-edit"
    >
      <Pencil className="h-4 w-4" aria-hidden="true" />
      {resume ? 'Resume editing' : 'Edit'}
    </Button>
  );
}

export interface ConfigFileEditorProps {
  /** Directory names then the file name. */
  path: string[];
  /** The path as shown, e.g. `ModConfig/x.json`. */
  displayPath: string;
  /** The file's text as read. */
  initialText: string;
  /** The version of the file as read. */
  version: string;
  /** Text to start from instead of the file's (a kept draft). */
  draft?: string;
  serverStopped: boolean;
  /** Edit mode ends: after a save (true), or a cancel or reload (false). */
  onDone: (saved: boolean) => void;
  onDirtyChange: (dirty: boolean) => void;
  /** Cancel with unsaved changes: the panel asks before discarding. */
  onRequestCancel: () => void;
  /** Reload the file after a conflict (the panel refetches the read). */
  onReload: () => void;
}

export function ConfigFileEditor({
  path,
  displayPath,
  initialText,
  version,
  draft,
  serverStopped,
  onDone,
  onDirtyChange,
  onRequestCancel,
  onReload,
}: ConfigFileEditorProps) {
  const [text, setText] = useState(draft ?? initialText);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [savedParseError, setSavedParseError] = useState<ConfigParseError | null>(null);
  const [conflict, setConflict] = useState(false);
  const [confirmReload, setConfirmReload] = useState(false);
  const editor = useRef<CodeViewHandle>(null);
  const save = useSaveConfigFile();
  const { check, isPending } = useConfigTextCheck(path, text, true);
  const dirty = text !== initialText;

  useEffect(() => {
    onDirtyChange(dirty);
  }, [dirty, onDirtyChange]);

  // Keep the edit in memory while it differs from the file (config-drafts.ts)
  useEffect(() => {
    if (dirty) setDraft(displayPath, { version, text });
    else clearDraft(displayPath);
  }, [dirty, displayPath, version, text]);

  // The browser's leave-page prompt while there are unsaved changes (ADR-5 decision 6)
  useEffect(() => {
    if (!dirty) return;
    const warn = (event: BeforeUnloadEvent) => {
      event.preventDefault();
      event.returnValue = '';
    };
    window.addEventListener('beforeunload', warn);
    return () => window.removeEventListener('beforeunload', warn);
  }, [dirty]);

  const handleChange = (next: string) => {
    setText(next);
    setSavedParseError(null);
    setSaveError(null);
  };

  const parseError = savedParseError ?? (check && !check.valid ? check.parseError : null);
  const canSave =
    serverStopped && dirty && check?.valid === true && !isPending && !save.isPending && !conflict;

  const handleSave = async () => {
    setSaveError(null);
    try {
      await save.mutateAsync({ path, text, version });
      clearDraft(displayPath);
      toast.success(`Saved ${displayPath}`);
      onDone(true);
    } catch (error) {
      const invalid = parseErrorFromApiError(error);
      if (invalid) {
        setSavedParseError(invalid);
      } else if (error instanceof ApiError && error.code === 'CONFIG_FILE_CHANGED') {
        setConflict(true);
      } else {
        setSaveError(error instanceof Error ? error.message : 'The file could not be saved');
      }
    }
  };

  const handleCancel = () => {
    if (dirty) onRequestCancel();
    else {
      clearDraft(displayPath);
      onDone(false);
    }
  };

  const errorPosition = parseError ? position(parseError) : null;

  return (
    <div className="flex h-full flex-col" data-testid="config-file-editor">
      <div className="flex items-center justify-between gap-2 border-b bg-muted/30 px-4 py-2">
        <span className="min-w-0 truncate text-sm font-medium text-muted-foreground">
          {displayPath}
        </span>
        <div className="flex shrink-0 items-center gap-2">
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="min-h-11 md:min-h-8"
            onClick={handleCancel}
            data-testid="config-editor-cancel"
          >
            Cancel
          </Button>
          <Button
            type="button"
            size="sm"
            className="min-h-11 md:min-h-8"
            disabled={!canSave}
            onClick={handleSave}
            data-testid="config-editor-save"
          >
            {save.isPending && <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />}
            Save
          </Button>
        </div>
      </div>

      <div className="min-h-0 flex-1">
        <LazyCodeView
          ref={editor}
          value={text}
          onChange={handleChange}
          ariaLabel={`Edit ${displayPath}`}
          data-testid="config-editor-text"
        />
      </div>

      <div className="space-y-1 border-t px-4 py-2 text-sm">
        <div role="status" aria-live="polite" data-testid="config-editor-status">
          {isPending ? (
            <span className="text-muted-foreground">Checking...</span>
          ) : parseError ? (
            <span className="flex flex-wrap items-center gap-1 text-destructive">
              <AlertCircle className="h-4 w-4" aria-hidden="true" />
              {parseError.message}
              {errorPosition && parseError.line !== null && parseError.column !== null && (
                <button
                  type="button"
                  className="underline underline-offset-2"
                  onClick={() => editor.current?.goTo(parseError.line!, parseError.column!)}
                  data-testid="config-editor-goto"
                >
                  {errorPosition}
                </button>
              )}
            </span>
          ) : check?.valid ? (
            <span className="flex items-center gap-1 text-success">
              <CheckCircle2 className="h-4 w-4" aria-hidden="true" />
              Valid
            </span>
          ) : null}
        </div>
        {!serverStopped && <ServerNotStoppedNote />}
        {conflict && (
          <p className={cn('text-destructive')} data-testid="config-editor-conflict">
            The file changed on disk since you opened it.{' '}
            <button
              type="button"
              className="underline underline-offset-2"
              onClick={() => setConfirmReload(true)}
              data-testid="config-editor-reload"
            >
              Reload
            </button>
          </p>
        )}
        {saveError && (
          <p className="text-destructive" data-testid="config-editor-error">
            {saveError}
          </p>
        )}
      </div>

      <ConfirmDialog
        open={confirmReload}
        title="Reload the file?"
        description="Discard your changes and load the file as it is now?"
        confirmLabel="Discard and reload"
        cancelLabel="Keep editing"
        onConfirm={() => {
          setConfirmReload(false);
          clearDraft(displayPath);
          onReload();
        }}
        onCancel={() => setConfirmReload(false)}
        data-testid="config-editor-reload-dialog"
      />
    </div>
  );
}
