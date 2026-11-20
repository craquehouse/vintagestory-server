/**
 * UnusedFilesNotice - Files in the mods folder the manager does not use (Story 24.6).
 *
 * For Admin keys only: a notice above the installed mods when the mods folder holds
 * leftover .tmp/.bak files, archives without a readable modinfo.json, or a second
 * archive of an installed mod (Epic 24 ADR-3). It expands to the list, each file with
 * a Delete that asks first. Renders nothing for other keys or when there are none.
 */

import { useState } from 'react';
import { toast } from 'sonner';
import { ChevronDown, FileWarning, Loader2, Trash2 } from 'lucide-react';
import { useIsAdmin } from '@/api/hooks/use-auth-me';
import type { UnusedFile } from '@/api/types';
import {
  AlertDialog,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { Button } from '@/components/ui/button';
import { relativeTime } from '@/lib/relative-time';
import { useDeleteUnusedFile, useUnusedFiles } from '@/hooks/use-mods';
import { cn } from '@/lib/utils';

/** "512 B", "1.5 KiB", "2.3 MiB". */
export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KiB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MiB`;
}

/** Why the manager does not use the file, in the admin's words. */
export function unusedReason(file: UnusedFile): string {
  switch (file.reason) {
    case 'leftover':
      return 'Leftover temporary or backup file';
    case 'unreadable':
      return 'Archive without a readable modinfo.json';
    case 'duplicate_mod_id':
      return file.installedAs
        ? `Another copy of a mod installed as ${file.installedAs}`
        : 'Another copy of an installed mod';
  }
}

export function UnusedFilesNotice() {
  const { isAdmin } = useIsAdmin();
  const { data, isError } = useUnusedFiles({ enabled: isAdmin });
  const { mutate: deleteFile, isPending: isDeleting } = useDeleteUnusedFile();
  const [expanded, setExpanded] = useState(false);
  const [toDelete, setToDelete] = useState<UnusedFile | null>(null);
  const files = isAdmin ? (data?.data?.files ?? []) : [];

  const handleConfirm = () => {
    if (!toDelete) return;
    const { name } = toDelete;
    deleteFile(name, {
      onSuccess: (response) => {
        toast.success(`Deleted ${name}`, {
          description: response.data.pendingRestart
            ? 'A server restart is required for the change to take effect.'
            : undefined,
        });
        setToDelete(null);
      },
      // As Story 21.4: the dialog stays open after a failure, with Delete enabled again
      onError: (error) => {
        toast.error(`Could not delete ${name}`, { description: error.message });
      },
    });
  };

  // Rendered even when the list is empty, so deleting the last file (which empties the
  // list at once) does not unmount the dialog while its DELETE runs (as Story 21.4)
  const dialog = (
    <AlertDialog
      open={!!toDelete}
      onOpenChange={(open) => !open && !isDeleting && setToDelete(null)}
    >
      <AlertDialogContent data-testid="unused-file-delete-dialog">
        <AlertDialogHeader>
          <AlertDialogTitle className="break-all">Delete {toDelete?.name}?</AlertDialogTitle>
          <AlertDialogDescription>
            {toDelete && `${unusedReason(toDelete)}. `}
            The file is deleted from the mods folder. This cannot be undone.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel disabled={isDeleting} data-testid="unused-file-delete-cancel">
            Cancel
          </AlertDialogCancel>
          {/* A plain button, not AlertDialogAction, which would close the dialog on click */}
          <Button
            variant="destructive"
            onClick={handleConfirm}
            disabled={isDeleting}
            data-testid="unused-file-delete-confirm"
          >
            {isDeleting ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Deleting...
              </>
            ) : (
              'Delete'
            )}
          </Button>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );

  if (isAdmin && isError) {
    return (
      <p className="text-sm text-muted-foreground" role="status" data-testid="unused-files-error">
        Could not check the mods folder for unused files.
      </p>
    );
  }

  if (files.length === 0) {
    return dialog;
  }

  const count = files.length;
  return (
    <section
      className="rounded-md border border-warning/40 bg-warning/10 text-sm"
      aria-labelledby="unused-files-heading"
      data-testid="unused-files-notice"
    >
      <button
        type="button"
        className="flex min-h-11 w-full items-center gap-2 px-3 py-2 text-left lg:min-h-0"
        aria-expanded={expanded}
        aria-controls="unused-files-list"
        onClick={() => setExpanded((value) => !value)}
        data-testid="unused-files-toggle"
      >
        <FileWarning className="h-4 w-4 shrink-0" aria-hidden="true" />
        <span id="unused-files-heading" className="flex-1">
          {count} {count === 1 ? 'file' : 'files'} in the mods folder {count === 1 ? 'is' : 'are'}{' '}
          not used
        </span>
        <ChevronDown
          className={cn('h-4 w-4 shrink-0 transition-transform', expanded && 'rotate-180')}
          aria-hidden="true"
        />
      </button>
      {/* Always rendered, so aria-controls always names an element */}
      <ul
        id="unused-files-list"
        className="divide-y border-t"
        hidden={!expanded}
        data-testid="unused-files-list"
      >
        {files.map((file) => (
          <li
            key={file.name}
            className="flex flex-wrap items-center justify-between gap-2 px-3 py-2"
            data-testid={`unused-file-${file.name}`}
          >
            <div className="min-w-0">
              <div className="break-all font-mono">{file.name}</div>
              <div className="text-muted-foreground">
                {formatFileSize(file.sizeBytes)} · modified{' '}
                <time dateTime={file.modifiedAt} title={new Date(file.modifiedAt).toLocaleString()}>
                  {relativeTime(file.modifiedAt)}
                </time>{' '}
                · {unusedReason(file)}
              </div>
            </div>
            <Button
              variant="outline"
              size="sm"
              className="max-lg:h-11"
              onClick={() => setToDelete(file)}
              aria-label={`Delete ${file.name}`}
              data-testid={`unused-file-delete-${file.name}`}
            >
              <Trash2 className="mr-2 h-4 w-4" aria-hidden="true" />
              Delete
            </Button>
          </li>
        ))}
      </ul>
      {dialog}
    </section>
  );
}
