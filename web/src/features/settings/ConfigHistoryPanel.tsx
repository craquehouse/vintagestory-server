/**
 * ConfigHistoryPanel: a config file's earlier versions, compared and restored
 * (Story 23.7, FR324, Epic 23 ADR-8).
 *
 * Lists the versions kept by saves (newest first); a chosen version is compared with the
 * current text (side by side from `md`, unified below) or shown alone, and can be restored
 * while the game server is stopped. Restoring goes through the API's save rules, and the
 * current text is kept as a new earlier version.
 */

import { useId, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { ApiError } from '@/api/errors';
import { queryKeys } from '@/api/query-keys';
import { toast } from 'sonner';
import { ArrowLeft, History, RotateCcw, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { LazyCodeView } from '@/components/code-view/LazyCodeView';
import { LazyRevisionCompare } from '@/components/code-view/LazyRevisionCompare';
import { useMediaQuery } from '@/hooks/use-media-query';
import {
  useConfigHistory,
  useConfigRevision,
  useRestoreConfigRevision,
} from '@/hooks/use-config-files';
import type { ConfigRevision } from '@/api/types';
import { ServerNotStoppedNote } from './ConfigFileEditor';
import { ConfirmDialog } from './ConfirmDialog';

// Story 24.6 review: moved to lib/ for the unused-files notice; re-exported for callers
import { relativeTime } from '@/lib/relative-time';

export { relativeTime };

/** "512 B", "1.5 KiB". */
export function formatSize(bytes: number): string {
  return bytes < 1024 ? `${bytes} B` : `${(bytes / 1024).toFixed(1)} KiB`;
}

function localTime(iso: string): string {
  return new Date(iso).toLocaleString();
}

export interface ConfigHistoryPanelProps {
  path: string[];
  displayPath: string;
  /** The file's current text and version (from the read). */
  currentText: string;
  currentVersion: string;
  serverStopped: boolean;
  wordWrap: boolean;
  onClose: () => void;
}

export function ConfigHistoryPanel({
  path,
  displayPath,
  currentText,
  currentVersion,
  serverStopped,
  wordWrap,
  onClose,
}: ConfigHistoryPanelProps) {
  const [chosen, setChosen] = useState<ConfigRevision | null>(null);
  const [showAlone, setShowAlone] = useState(false);
  const [confirmRestore, setConfirmRestore] = useState(false);
  const [restoreError, setRestoreError] = useState<string | null>(null);
  // Story 23.7 review M-1: a version refused as changed on disk can be reloaded and retried
  const [restoreChanged, setRestoreChanged] = useState(false);
  const queryClient = useQueryClient();
  const serverNoteId = useId();
  const wide = useMediaQuery('(min-width: 768px)');
  const history = useConfigHistory(path, true);
  const revision = useConfigRevision(path, chosen?.id ?? null);
  const restore = useRestoreConfigRevision();

  const revisions = history.data?.data.revisions ?? [];
  const revisionText = revision.data?.data.text;

  const handleRestore = async () => {
    if (!chosen) return;
    setConfirmRestore(false);
    setRestoreError(null);
    setRestoreChanged(false);
    try {
      await restore.mutateAsync({ path, revision: chosen.id, version: currentVersion });
      toast.success(`Restored ${displayPath}`);
      onClose();
    } catch (error) {
      setRestoreChanged(error instanceof ApiError && error.code === 'CONFIG_FILE_CHANGED');
      setRestoreError(error instanceof Error ? error.message : 'The version could not be restored');
    }
  };

  return (
    <div className="flex h-full flex-col" data-testid="config-history-panel">
      <div className="flex items-center justify-between gap-2 border-b bg-muted/30 px-4 py-2">
        <span className="flex min-w-0 items-center gap-2 text-sm font-medium text-muted-foreground">
          {chosen ? (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="min-h-11 md:min-h-8"
              onClick={() => {
                setChosen(null);
                setShowAlone(false);
                setRestoreError(null);
              }}
              data-testid="config-history-back"
            >
              <ArrowLeft className="h-4 w-4" aria-hidden="true" />
              Versions
            </Button>
          ) : (
            <History className="h-4 w-4 shrink-0" aria-hidden="true" />
          )}
          <span className="truncate">Earlier versions of {displayPath}</span>
        </span>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          className="min-h-11 md:min-h-8"
          onClick={onClose}
          aria-label="Close history"
          data-testid="config-history-close"
        >
          <X className="h-4 w-4" aria-hidden="true" />
        </Button>
      </div>

      {!chosen ? (
        <div className="flex-1 overflow-auto p-2">
          {history.isLoading ? (
            <div className="space-y-2 p-2">
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
            </div>
          ) : history.error ? (
            <p className="p-2 text-sm text-destructive">{history.error.message}</p>
          ) : revisions.length === 0 ? (
            <p className="p-2 text-sm text-muted-foreground" data-testid="config-history-empty">
              No earlier versions. Versions are kept when the file is saved here.
            </p>
          ) : (
            <ul className="space-y-1" data-testid="config-history-list">
              {revisions.map((item) => (
                <li key={item.id}>
                  <button
                    type="button"
                    className="flex min-h-11 w-full flex-wrap items-center justify-between gap-x-4 rounded-md px-3 py-2 text-left text-sm hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                    onClick={() => setChosen(item)}
                    data-testid={`config-history-item-${item.id}`}
                  >
                    <span className="font-medium">{localTime(item.savedAt)}</span>
                    <span className="text-muted-foreground">
                      {relativeTime(item.savedAt)} · {item.savedBy} · {formatSize(item.size)}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      ) : (
        <div className="flex min-h-0 flex-1 flex-col">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b px-4 py-2 text-sm">
            <span className="text-muted-foreground">
              Saved {localTime(chosen.savedAt)} ({relativeTime(chosen.savedAt)})
              {showAlone ? '' : ' · left: this version, right: the file now'}
            </span>
            <div className="flex items-center gap-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="min-h-11 md:min-h-8"
                onClick={() => setShowAlone(!showAlone)}
                data-testid="config-history-toggle"
              >
                {showAlone ? 'Compare with the file now' : 'Show this version'}
              </Button>
              <Button
                type="button"
                size="sm"
                className="min-h-11 md:min-h-8"
                disabled={!serverStopped || revisionText === undefined || restore.isPending}
                aria-describedby={serverStopped ? undefined : serverNoteId}
                onClick={() => setConfirmRestore(true)}
                data-testid="config-history-restore"
              >
                <RotateCcw className="h-4 w-4" aria-hidden="true" />
                Restore
              </Button>
            </div>
          </div>
          {!serverStopped && (
            <div className="border-b px-4 py-1.5">
              <ServerNotStoppedNote id={serverNoteId} />
            </div>
          )}
          {restoreError && (
            <p
              className="border-b px-4 py-1.5 text-sm text-destructive"
              data-testid="config-history-error"
            >
              {restoreError}
              {restoreChanged && (
                <>
                  {' '}
                  <button
                    type="button"
                    className="min-h-11 px-1 underline underline-offset-2 md:min-h-0 md:px-0"
                    onClick={() => {
                      setRestoreError(null);
                      setRestoreChanged(false);
                      void queryClient.invalidateQueries({
                        queryKey: queryKeys.config.file(path.join('/')),
                      });
                    }}
                    data-testid="config-history-reload"
                  >
                    Reload the file
                  </button>
                </>
              )}
            </p>
          )}
          <div className="min-h-0 flex-1">
            {revisionText === undefined ? (
              revision.error ? (
                <p className="p-4 text-sm text-destructive">{revision.error.message}</p>
              ) : (
                <Skeleton className="m-4 h-24" />
              )
            ) : showAlone ? (
              <LazyCodeView
                value={revisionText}
                readOnly
                wordWrap={wordWrap}
                ariaLabel={`Version from ${localTime(chosen.savedAt)}`}
                data-testid="config-history-version"
              />
            ) : (
              <LazyRevisionCompare
                original={revisionText}
                current={currentText}
                split={wide}
                wordWrap={wordWrap}
                data-testid="config-history-compare"
              />
            )}
          </div>
        </div>
      )}

      <ConfirmDialog
        open={confirmRestore}
        title="Restore this version?"
        description={`Replace the current file with the version from ${chosen ? localTime(chosen.savedAt) : ''}? The current text is kept in the history.`}
        confirmLabel="Restore"
        cancelLabel="Cancel"
        onConfirm={handleRestore}
        onCancel={() => setConfirmRestore(false)}
        data-testid="config-history-restore-dialog"
      />
    </div>
  );
}
