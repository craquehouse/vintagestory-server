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
  const { mutate, isPending, variables } = useChangeModVersion();
  const [confirmation, setConfirmation] = useState<VersionChangeConfirmation | null>(null);

  const run = useCallback(
    (request: VersionChangeRequest, confirm: boolean) => {
      const verb = request.kind === 'update' ? 'update' : 'switch';
      mutate(
        { slug: request.slug, version: request.version, confirm },
        {
          onSuccess: (response) => {
            const result = response.data;
            if (!result.changed) {
              toast.info(`${request.name} is already at v${result.version}`);
              return;
            }
            const done = request.kind === 'update' ? 'Updated' : 'Switched';
            toast.success(`${done} ${request.name} to v${result.version}`, {
              description: result.pendingRestart ? RESTART_REQUIRED : undefined,
            });
          },
          onError: (error) => {
            const reasons = confirm ? null : confirmationReasons(error);
            if (reasons) {
              setConfirmation({ ...request, reasons });
              return;
            }
            toast.error(`Failed to ${verb} ${request.name}`, { description: error.message });
          },
        }
      );
    },
    [mutate]
  );

  /** Start an update or switch; may open the confirmation instead of changing. */
  const start = useCallback(
    (request: VersionChangeRequest) => {
      setConfirmation(null);
      run(request, false);
    },
    [run]
  );

  /** Retry the held change with `confirm: true`. */
  const confirm = useCallback(() => {
    if (!confirmation) return;
    setConfirmation(null);
    run(confirmation, true);
  }, [confirmation, run]);

  /** Drop the held change without a request. */
  const cancel = useCallback(() => setConfirmation(null), []);

  return {
    start,
    confirm,
    cancel,
    confirmation,
    /** Slug of the change in flight, if any */
    pendingSlug: isPending ? variables?.slug : undefined,
  };
}
