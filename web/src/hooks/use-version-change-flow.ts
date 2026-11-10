/**
 * Version change flow with confirmation (Story 14.3).
 *
 * Calls PUT /mods/{slug}/version without confirmation first. When the API answers
 * 409 MOD_CONFIRMATION_REQUIRED, the flow holds a confirmation with the reasons for
 * VersionChangeConfirmDialog; confirming retries with `confirm: true`, cancelling
 * makes no further request. Success and failure are reported with toasts.
 */

import { useCallback, useState } from 'react';
import { toast } from 'sonner';
import { ApiError } from '@/api/errors';
import { useChangeModVersion } from '@/hooks/use-mods';
import type { VersionChangeReason } from '@/api/types';

/** An update offered by the update check, or a switch picked by the user. */
export type VersionChangeKind = 'update' | 'switch';

export interface VersionChangeRequest {
  slug: string;
  /** Display name for toasts and the dialog */
  name: string;
  version: string;
  installedVersion: string;
  kind: VersionChangeKind;
}

export interface VersionChangeConfirmation extends VersionChangeRequest {
  /** Known reasons from the API; empty when it sent none this UI recognizes */
  reasons: VersionChangeReason[];
}

const KNOWN_REASONS = new Set<string>(['not_verified', 'incompatible', 'prerelease', 'older']);

const RESTART_REQUIRED = 'A server restart is required for changes to take effect.';

/** Reasons from a confirmation-required error, or null for any other error. */
function confirmationReasons(error: unknown): VersionChangeReason[] | null {
  if (!(error instanceof ApiError) || error.code !== 'MOD_CONFIRMATION_REQUIRED') {
    return null;
  }
  const raw = error.details?.reasons;
  if (!Array.isArray(raw)) return [];
  return raw.filter(
    (reason): reason is VersionChangeReason =>
      typeof reason === 'string' && KNOWN_REASONS.has(reason)
  );
}

export function useVersionChangeFlow() {
  // mutateAsync, not mutate: TanStack runs per-call mutate callbacks only for the
  // latest call, so a second change started before the first settles would drop
  // the first one's toast or confirmation.
  const { mutateAsync } = useChangeModVersion();
  const [confirmation, setConfirmation] = useState<VersionChangeConfirmation | null>(null);
  const [pendingSlugs, setPendingSlugs] = useState<ReadonlySet<string>>(new Set());

  const setPending = useCallback((slug: string, pending: boolean) => {
    setPendingSlugs((current) => {
      const next = new Set(current);
      if (pending) next.add(slug);
      else next.delete(slug);
      return next;
    });
  }, []);

  const run = useCallback(
    async (request: VersionChangeRequest, confirm: boolean) => {
      const verb = request.kind === 'update' ? 'update' : 'switch';
      setPending(request.slug, true);
      try {
        const response = await mutateAsync({
          slug: request.slug,
          version: request.version,
          confirm,
        });
        const result = response.data;
        if (!result.changed) {
          toast.info(`${request.name} is already at v${result.version}`);
          return;
        }
        const done = request.kind === 'update' ? 'Updated' : 'Switched';
        toast.success(`${done} ${request.name} to v${result.version}`, {
          description: result.pendingRestart ? RESTART_REQUIRED : undefined,
        });
      } catch (error) {
        // A confirmed retry that asks again is reported as an error, not reopened.
        const reasons = confirm ? null : confirmationReasons(error);
        if (reasons) {
          setConfirmation({ ...request, reasons });
          return;
        }
        const message = error instanceof Error ? error.message : 'An unexpected error occurred';
        toast.error(`Failed to ${verb} ${request.name}`, { description: message });
      } finally {
        setPending(request.slug, false);
      }
    },
    [mutateAsync, setPending]
  );

  /** Start an update or switch; may open the confirmation instead of changing. */
  const start = useCallback(
    (request: VersionChangeRequest) => {
      setConfirmation(null);
      void run(request, false);
    },
    [run]
  );

  /** Retry the held change with `confirm: true`. */
  const confirm = useCallback(() => {
    if (!confirmation) return;
    setConfirmation(null);
    void run(confirmation, true);
  }, [confirmation, run]);

  /** Drop the held change without a request. */
  const cancel = useCallback(() => setConfirmation(null), []);

  /** Whether a change for this mod is in flight. */
  const isPending = useCallback((slug: string) => pendingSlugs.has(slug), [pendingSlugs]);

  return { start, confirm, cancel, confirmation, isPending };
}
