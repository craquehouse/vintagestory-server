/**
 * AddModDialog - install a mod from a file or a link (Story 28.4, Epic 28 ADR-6).
 *
 * Two tabs: "File" uploads a picked or dropped zip as the request body; "Link" has the
 * server download an https link. An installed mod with the same mod ID is offered a
 * replace; any other error shows the API's message and keeps the input.
 */

import { useState, type DragEvent } from 'react';
import { toast } from 'sonner';
import { FileArchive, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ApiError } from '@/api/errors';
import { useAddModFromFileOrLink } from '@/hooks/use-mods';
import type { ModSource } from '@/api/types';

type AddTab = 'file' | 'link';

interface InstalledConflict {
  slug: string;
  version: string;
  source: ModSource | null;
}

const SOURCE_LABELS: Record<ModSource, string> = {
  moddb: 'from the mod database',
  folder: 'found in the mods folder',
  upload: 'an uploaded file',
  url: 'installed from a link',
};

function conflictFrom(error: ApiError): InstalledConflict {
  const details = error.details ?? {};
  const source = details.source;
  return {
    slug: typeof details.slug === 'string' ? details.slug : '',
    version: typeof details.installed_version === 'string' ? details.installed_version : '',
    source: typeof source === 'string' && source in SOURCE_LABELS ? (source as ModSource) : null,
  };
}

interface AddModDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function AddModDialog({ open, onOpenChange }: AddModDialogProps) {
  const [tab, setTab] = useState<AddTab>('file');
  const [file, setFile] = useState<File | null>(null);
  const [url, setUrl] = useState('');
  const [dragging, setDragging] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [conflict, setConflict] = useState<InstalledConflict | null>(null);
  const { mutate, isPending } = useAddModFromFileOrLink();

  const clearOutcome = () => {
    setError(null);
    setConflict(null);
  };

  const handleOpenChange = (next: boolean) => {
    if (!next && isPending) return;
    if (!next) {
      setFile(null);
      setUrl('');
      setDragging(false);
      clearOutcome();
    }
    onOpenChange(next);
  };

  const chooseFile = (picked: File | null) => {
    setFile(picked);
    clearOutcome();
  };

  const handleDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setDragging(false);
    const dropped = event.dataTransfer.files[0];
    if (dropped) chooseFile(dropped);
  };

  const link = url.trim();
  const canInstall = !isPending && (tab === 'file' ? file !== null : link !== '');

  const install = (replace: boolean) => {
    // While the replace prompt shows, the only way on is "Replace it" (Story 28.4 review)
    if (conflict !== null && !replace) return;
    const request =
      tab === 'file' ? (file ? { file, replace } : null) : link ? { url: link, replace } : null;
    if (!request) return;
    clearOutcome();
    mutate(request, {
      onSuccess: (response) => {
        const { slug, version, replaced, pendingRestart } = response.data;
        toast.success(`${replaced ? 'Replaced' : 'Installed'} ${slug} ${version}`, {
          description: pendingRestart
            ? 'A server restart is required for the change to take effect.'
            : undefined,
        });
        handleOpenChange(false);
      },
      onError: (failure) => {
        if (failure instanceof ApiError && failure.code === 'MOD_ALREADY_INSTALLED' && !replace) {
          setConflict(conflictFrom(failure));
        } else {
          setError(failure.message);
        }
      },
    });
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent data-testid="add-mod-dialog">
        <DialogHeader>
          <DialogTitle>Add a mod from a file or a link</DialogTitle>
          <DialogDescription>
            For mods that are not on the mod database, or a build of one that is. The mod database
            is never asked about them, so they get no update offers.
          </DialogDescription>
        </DialogHeader>

        <Tabs
          value={tab}
          onValueChange={(value) => {
            setTab(value as AddTab);
            clearOutcome();
          }}
        >
          <TabsList className="w-full">
            <TabsTrigger value="file" className="min-h-11" data-testid="add-mod-tab-file">
              File
            </TabsTrigger>
            <TabsTrigger value="link" className="min-h-11" data-testid="add-mod-tab-link">
              Link
            </TabsTrigger>
          </TabsList>

          <TabsContent value="file" className="pt-2">
            <div
              className={`flex flex-col items-center gap-3 rounded-md border-2 border-dashed p-4 text-center ${
                dragging ? 'border-primary bg-muted' : 'border-muted-foreground/30'
              }`}
              onDragOver={(event) => {
                event.preventDefault();
                setDragging(true);
              }}
              onDragLeave={(event) => {
                // Leaving for a child of the zone is not leaving the zone
                if (event.currentTarget.contains(event.relatedTarget as Node | null)) return;
                setDragging(false);
              }}
              onDrop={handleDrop}
              data-testid="add-mod-drop"
            >
              <FileArchive className="h-6 w-6 text-muted-foreground" aria-hidden="true" />
              <p className="text-sm text-muted-foreground">
                Drop a mod's <code>.zip</code> here, or choose it.
              </p>
              <label className="w-full text-left text-sm font-medium" htmlFor="add-mod-file">
                Mod file
              </label>
              <Input
                id="add-mod-file"
                type="file"
                accept=".zip,application/zip"
                className="min-h-11"
                onChange={(event) => chooseFile(event.target.files?.[0] ?? null)}
                data-testid="add-mod-file-input"
              />
              {file && (
                <p className="w-full truncate text-left text-sm" data-testid="add-mod-file-name">
                  {file.name}
                </p>
              )}
            </div>
          </TabsContent>

          <TabsContent value="link" className="space-y-2 pt-2">
            <label className="text-sm font-medium" htmlFor="add-mod-url">
              Link to the mod's zip
            </label>
            <Input
              id="add-mod-url"
              type="url"
              inputMode="url"
              placeholder="https://github.com/owner/repo/releases/download/v1.0.0/mod.zip"
              className="min-h-11"
              value={url}
              onChange={(event) => {
                setUrl(event.target.value);
                clearOutcome();
              }}
              onKeyDown={(event) => {
                if (event.key === 'Enter' && canInstall) install(false);
              }}
              data-testid="add-mod-url-input"
            />
            <p className="text-xs text-muted-foreground">
              An https link the server downloads, such as a GitHub or Forgejo release asset or an S3
              link. Hosts on a private network are refused unless listed in
              VS_MOD_URL_PRIVATE_HOSTS.
            </p>
          </TabsContent>
        </Tabs>

        {error && (
          <p role="alert" className="text-sm text-destructive" data-testid="add-mod-error">
            {error}
          </p>
        )}
        {conflict && (
          <div
            role="alert"
            className="space-y-2 rounded-md border border-warning/50 p-3 text-sm"
            data-testid="add-mod-installed"
          >
            <p>
              {conflict.slug} {conflict.version} is already installed
              {conflict.source ? ` (${SOURCE_LABELS[conflict.source]})` : ''}. Replace it with this{' '}
              {tab === 'file' ? 'file' : 'download'}? It stays enabled or disabled as it is.
            </p>
            <Button
              variant="destructive"
              size="sm"
              className="min-h-11"
              onClick={() => install(true)}
              disabled={isPending}
              data-testid="add-mod-replace"
            >
              Replace it
            </Button>
          </div>
        )}

        <DialogFooter>
          <Button
            variant="outline"
            className="min-h-11"
            onClick={() => handleOpenChange(false)}
            disabled={isPending}
          >
            Cancel
          </Button>
          <Button
            className="min-h-11"
            onClick={() => install(false)}
            disabled={!canInstall || conflict !== null}
            data-testid="add-mod-install"
          >
            {isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />}
            {isPending ? 'Installing…' : 'Install'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
