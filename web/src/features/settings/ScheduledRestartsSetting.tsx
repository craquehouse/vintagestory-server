/**
 * The daily restart times of the API Settings tab.
 *
 * Story 22.6: daily restart times (Epic 22 ADR-13 decision 1)
 *
 * A time is committed when its input loses focus or gets Enter, and Remove commits at
 * once; each commit saves the whole list through `onSave` (the panel's `handleSave`,
 * which shows the one toast). A list the API would refuse is not sent: the reason is
 * shown under the list instead, in the API's words (`lib/restart-times.ts`).
 */

import { Loader2, Plus, X } from 'lucide-react';
import { useCallback, useEffect, useRef, useState } from 'react';
import { MAX_RESTART_TIMES, MIN_RESTART_GAP_MINUTES } from '@/api/config';
import { ApiError } from '@/api/errors';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { restartTimesError, sortRestartTimes } from '@/lib/restart-times';

const SETTING_KEY = 'scheduled_restart_times';
const ERROR_ID = `${SETTING_KEY}-error`;
const DESCRIPTION_ID = `${SETTING_KEY}-desc`;

export interface ScheduledRestartsSettingProps {
  /** The saved restart times (`HH:MM`, server time). */
  times: readonly string[];
  /** Saves the whole list; rejects with the API's message on a failure. */
  onSave: (params: { key: string; value: string[] }) => Promise<unknown>;
}

interface Row {
  id: number;
  value: string;
  /** Added with Add time and not saved yet. */
  isNew: boolean;
}

interface Message {
  text: string;
  /** A client check's message, or the server's answer to a save. */
  source: 'client' | 'server';
}

/** Where the focus goes once a Remove has settled: a row's input, or Add time. */
type FocusTarget = number | 'add';

function isUnfilledNew(row: Row): boolean {
  return row.isNew && row.value === '';
}

/** The times the editor would send: every row with a value, and every saved row. */
function listFrom(rows: readonly Row[]): string[] {
  return rows.filter((row) => !isUnfilledNew(row)).map((row) => row.value);
}

function sameList(a: readonly string[], b: readonly string[]): boolean {
  const left = sortRestartTimes(a);
  const right = sortRestartTimes(b);
  return left.length === right.length && left.every((time, i) => time === right[i]);
}

export function ScheduledRestartsSetting({ times, onSave }: ScheduledRestartsSettingProps) {
  const nextIdRef = useRef(0);
  const newId = useCallback(() => {
    nextIdRef.current += 1;
    return nextIdRef.current;
  }, []);

  /** Saved rows for `list` (sorted), keeping the ids of rows that show the same time. */
  const rowsFor = useCallback(
    (list: readonly string[], current: readonly Row[]): Row[] => {
      const available = current.filter((row) => !isUnfilledNew(row));
      return sortRestartTimes(list).map((value) => {
        const index = available.findIndex((row) => row.value === value);
        const id = index === -1 ? newId() : available.splice(index, 1)[0].id;
        return { id, value, isNew: false };
      });
    },
    [newId]
  );

  const [rows, setRowsState] = useState<Row[]>(() => rowsFor(times, []));
  // The rows as last set, read synchronously by a commit queued behind a save
  const rowsRef = useRef(rows);
  const setRows = useCallback((next: Row[]) => {
    rowsRef.current = next;
    setRowsState(next);
  }, []);

  const [message, setMessage] = useState<Message | null>(null);
  const [isPending, setIsPending] = useState(false);
  const [focusedId, setFocusedId] = useState<number | null>(null);

  // The saved list: the last list this editor saved, or the prop once it changes (the
  // prop can lag a save by a task, so a commit never compares with the prop alone)
  const savedRef = useRef<string[]>(sortRestartTimes(times));
  // A list whose save failed: not sent again until a row changes (controller decision 2)
  const failedRef = useRef<string[] | null>(null);
  // Set synchronously while a save is in flight, before a re-render disables the inputs
  const savingRef = useRef(false);
  // Commits and Removes that arrived during a save run after it (controller decision 1)
  const queueRef = useRef<Array<() => void>>([]);
  const focusTargetRef = useRef<FocusTarget | null>(null);
  const inputRefs = useRef(new Map<number, HTMLInputElement>());
  const addRef = useRef<HTMLButtonElement>(null);

  const timesKey = sortRestartTimes(times).join(',');
  // The prop's list the rows last took
  const appliedKeyRef = useRef(timesKey);

  useEffect(() => {
    // During a save the prop holds the hook's optimistic list, which is not saved yet; the
    // save itself sets the saved list, and a rollback changes the prop again
    if (savingRef.current) return;
    savedRef.current = timesKey === '' ? [] : timesKey.split(',');
  }, [timesKey]);

  // Follow a changed prop (the poll, the save's refetch, another tab) while no save is
  // pending, no message is shown and no time input has focus; keep a new row the admin
  // has not filled in (controller decision 4)
  useEffect(() => {
    if (isPending || message || focusedId !== null || timesKey === appliedKeyRef.current) {
      return;
    }
    appliedKeyRef.current = timesKey;
    const current = rowsRef.current;
    const list = timesKey === '' ? [] : timesKey.split(',');
    setRows([...rowsFor(list, current), ...current.filter(isUnfilledNew)]);
  }, [timesKey, isPending, message, focusedId, rowsFor, setRows]);

  // Move the focus once the inputs are enabled again (a disabled input cannot take it)
  useEffect(() => {
    const target = focusTargetRef.current;
    if (isPending || target === null) return;
    focusTargetRef.current = null;
    const input = target === 'add' ? undefined : inputRefs.current.get(target);
    if (input) {
      input.focus();
    } else {
      addRef.current?.focus();
    }
  }, [rows, isPending]);

  const runQueued = useCallback(() => {
    const next = queueRef.current.shift();
    next?.();
  }, []);

  const save = useCallback(
    async (list: string[]) => {
      const value = sortRestartTimes(list);
      savingRef.current = true;
      setIsPending(true);
      try {
        await onSave({ key: SETTING_KEY, value });
        savedRef.current = value;
        failedRef.current = null;
        setMessage(null);
        setRows([...rowsFor(value, rowsRef.current), ...rowsRef.current.filter(isUnfilledNew)]);
      } catch (err) {
        const text = err instanceof Error ? err.message : 'Failed to save restart times';
        setMessage({ text, source: 'server' });
        if (err instanceof ApiError && err.code === 'API_SETTING_NOT_APPLIED') {
          // Saved, but not applied: the list shown is the one saved
          savedRef.current = value;
          setRows([...rowsFor(value, rowsRef.current), ...rowsRef.current.filter(isUnfilledNew)]);
        } else {
          // Keep the rows as edited (AC 4)
          failedRef.current = value;
        }
      } finally {
        savingRef.current = false;
        setIsPending(false);
        runQueued();
      }
    },
    [onSave, rowsFor, setRows, runQueued]
  );

  // `rowsChanged`: a Remove; a blur or Enter only commits what the rows already show
  const commit = useCallback(
    (rowsChanged = false) => {
      if (savingRef.current) {
        queueRef.current.push(() => commit(rowsChanged));
        return;
      }
      const list = listFrom(rowsRef.current);
      if (sameList(list, savedRef.current)) {
        // Nothing to save. A client message goes; a server message goes only when a row
        // change brought back the saved list (controller decision 3)
        setMessage((shown) => (shown?.source === 'server' && !rowsChanged ? shown : null));
        return;
      }
      if (failedRef.current && sameList(list, failedRef.current)) return;
      const error = restartTimesError(list);
      if (error) {
        setMessage({ text: error, source: 'client' });
        return;
      }
      void save(list);
    },
    [save]
  );

  const handleChange = useCallback(
    (id: number, value: string) => {
      const next = rowsRef.current.map((row) => (row.id === id ? { ...row, value } : row));
      setRows(next);
      failedRef.current = null;
      if (!message) return;
      const list = listFrom(next);
      // A server message clears when the rows are the saved list again (controller
      // decision 3); a client message as soon as the list passes the checks
      if (
        sameList(list, savedRef.current) ||
        (message.source === 'client' && restartTimesError(list) === null)
      ) {
        setMessage(null);
      }
    },
    [message, setRows]
  );

  const remove = useCallback(
    (id: number) => {
      if (savingRef.current) {
        queueRef.current.push(() => remove(id));
        return;
      }
      const current = rowsRef.current;
      const index = current.findIndex((row) => row.id === id);
      if (index === -1) return;
      const removed = current[index];
      const next = current.filter((row) => row.id !== id);
      setRows(next);
      focusTargetRef.current = next[index]?.id ?? next[index - 1]?.id ?? 'add';
      failedRef.current = null;
      if (isUnfilledNew(removed)) return;
      commit(true);
    },
    [commit, setRows]
  );

  const add = useCallback(() => {
    const id = newId();
    setRows([...rowsRef.current, { id, value: '', isNew: true }]);
    focusTargetRef.current = id;
  }, [newId, setRows]);

  const isFull = rows.length >= MAX_RESTART_TIMES;
  const describedBy = message ? ERROR_ID : DESCRIPTION_ID;

  return (
    <div className="space-y-3">
      <div className="flex items-start gap-2">
        <p id={DESCRIPTION_ID} className="text-xs text-muted-foreground">
          Times are server time: the container&apos;s time zone (TZ), UTC unless set. Players are
          warned in chat 15, 5 and 1 minutes before each restart. A stopped server is not started. A
          time less than 15 minutes from now first runs the next day. Up to {MAX_RESTART_TIMES}{' '}
          times, at least {MIN_RESTART_GAP_MINUTES} minutes apart. Scheduled Jobs lists each one as
          scheduled_restart_HHMM, with its first warning as the next run, in your browser&apos;s
          time.
        </p>
        {isPending && (
          <Loader2
            className="h-3 w-3 shrink-0 animate-spin text-muted-foreground"
            aria-hidden="true"
          />
        )}
      </div>

      {rows.length === 0 ? (
        <p data-testid="scheduled-restarts-empty" className="text-sm text-muted-foreground">
          No restart is scheduled.
        </p>
      ) : (
        <ul aria-label="Restart times" className="space-y-2">
          {rows.map((row, i) => {
            const n = i + 1;
            return (
              <li key={row.id} className="flex items-center gap-2">
                <Input
                  ref={(el) => {
                    if (el) {
                      inputRefs.current.set(row.id, el);
                    } else {
                      inputRefs.current.delete(row.id);
                    }
                  }}
                  type="time"
                  step={60}
                  aria-label={`Restart time ${n}`}
                  aria-invalid={message ? true : undefined}
                  aria-describedby={describedBy}
                  data-testid={`restart-time-${n}`}
                  className="w-36 max-lg:h-11"
                  value={row.value}
                  disabled={isPending}
                  onChange={(e) => handleChange(row.id, e.target.value)}
                  onFocus={() => setFocusedId(row.id)}
                  onBlur={() => {
                    setFocusedId(null);
                    commit();
                  }}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault();
                      commit();
                    }
                  }}
                />
                {/* Not disabled while a save is pending: a Remove clicked then waits for
                    it and runs after (controller decision 1) */}
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="max-lg:size-11"
                  aria-label={
                    row.value ? `Remove restart time ${row.value}` : `Remove restart time ${n}`
                  }
                  data-testid={`remove-restart-time-${n}`}
                  onClick={() => remove(row.id)}
                >
                  <X className="h-4 w-4" aria-hidden="true" />
                </Button>
              </li>
            );
          })}
        </ul>
      )}

      {message && (
        <p id={ERROR_ID} role="alert" className="text-xs text-destructive">
          {message.text}
        </p>
      )}

      <div className="space-y-1">
        <Button
          ref={addRef}
          type="button"
          variant="outline"
          size="sm"
          className="max-lg:min-h-11"
          data-testid="add-restart-time"
          disabled={isPending || isFull}
          onClick={add}
        >
          <Plus className="h-4 w-4" aria-hidden="true" />
          Add time
        </Button>
        {isFull && (
          <p data-testid="scheduled-restarts-max" className="text-xs text-muted-foreground">
            At most {MAX_RESTART_TIMES} restart times.
          </p>
        )}
      </div>
    </div>
  );
}
