/**
 * Unsaved config file edits, kept in memory while the app runs (Story 23.5).
 *
 * The app uses `BrowserRouter`, so leaving the Settings page cannot be blocked with
 * React Router's `useBlocker` (a data-router API). Instead an edit is kept here, by path
 * and by the version of the file it started from, and offered again ("Resume editing")
 * when the same file, unchanged on disk, is opened again. Never written to storage: a
 * config text can hold secrets. Gone when the browser tab is closed or reloaded.
 */

export interface ConfigDraft {
  /** The version of the file the edit started from. */
  version: string;
  text: string;
}

const drafts = new Map<string, ConfigDraft>();

/** The draft for a file, if it was made from this version. Pure: safe during render. */
export function getDraft(path: string, version: string | undefined): ConfigDraft | undefined {
  const draft = drafts.get(path);
  return draft && draft.version === version ? draft : undefined;
}

/**
 * Forget a draft made from another version of the file (Story 23.5 review L-6: eviction
 * happens when an edit starts, not during render).
 */
export function dropStaleDraft(path: string, version: string): void {
  const draft = drafts.get(path);
  if (draft && draft.version !== version) drafts.delete(path);
}

export function setDraft(path: string, draft: ConfigDraft): void {
  drafts.set(path, draft);
}

export function clearDraft(path: string): void {
  drafts.delete(path);
}

/** For tests: forget every draft. */
export function clearAllDrafts(): void {
  drafts.clear();
}
