/**
 * ModUpdateWebhookSetting - Set or clear the webhook for mod update alerts (Story 14.6).
 *
 * The URL is a secret: the API reports only whether one is configured, so the field
 * is never prefilled and shows only "Configured" or "Not configured".
 */

import { useState } from 'react';
import { Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useSetModUpdateWebhook } from '@/hooks/use-api-settings';

interface ModUpdateWebhookSettingProps {
  /** Whether a webhook is configured */
  configured: boolean;
}

function isHttpUrl(value: string): boolean {
  try {
    const url = new URL(value);
    return (url.protocol === 'http:' || url.protocol === 'https:') && url.hostname !== '';
  } catch {
    return false;
  }
}

export function ModUpdateWebhookSetting({ configured }: ModUpdateWebhookSettingProps) {
  const [url, setUrl] = useState('');
  const [error, setError] = useState<string | null>(null);
  const { mutate, isPending } = useSetModUpdateWebhook();

  const save = (value: string | null) => {
    mutate(value, {
      onSuccess: () => {
        setUrl('');
        toast.success(value ? 'Webhook saved' : 'Webhook removed');
      },
      onError: (err) => {
        toast.error('Update failed', { description: err.message });
      },
    });
  };

  const handleSave = () => {
    const value = url.trim();
    if (!isHttpUrl(value)) {
      setError('Enter an http or https URL');
      return;
    }
    setError(null);
    save(value);
  };

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <label htmlFor="mod_update_webhook_url" className="text-sm font-medium text-foreground">
          Webhook URL
        </label>
        <span
          className="text-sm text-muted-foreground"
          data-testid="mod-update-webhook-status"
        >
          {configured ? 'Configured' : 'Not configured'}
        </span>
        {isPending && <Loader2 className="h-3 w-3 animate-spin text-muted-foreground" />}
      </div>
      <div className="flex flex-wrap gap-2">
        <Input
          id="mod_update_webhook_url"
          type="url"
          autoComplete="off"
          spellCheck={false}
          placeholder={configured ? 'Enter a new URL to replace it' : 'https://discord.com/api/webhooks/…'}
          value={url}
          onChange={(e) => {
            setUrl(e.target.value);
            setError(null);
          }}
          aria-invalid={error !== null}
          aria-describedby="mod_update_webhook_url-desc"
          className="min-w-0 flex-1"
          data-testid="mod-update-webhook-input"
        />
        <Button
          onClick={handleSave}
          disabled={isPending || url.trim() === ''}
          data-testid="mod-update-webhook-save"
        >
          Save
        </Button>
        {configured && (
          <Button
            variant="outline"
            onClick={() => save(null)}
            disabled={isPending}
            data-testid="mod-update-webhook-clear"
          >
            Clear
          </Button>
        )}
      </div>
      {error && (
        <p className="text-xs text-destructive" role="alert">
          {error}
        </p>
      )}
      <p id="mod_update_webhook_url-desc" className="text-xs text-muted-foreground">
        Sends one message when a mod update becomes available. Discord webhooks are supported.
        The URL is stored on the server and never shown again.
      </p>
    </div>
  );
}
