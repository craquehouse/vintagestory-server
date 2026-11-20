import { describe, it, expect, beforeEach } from 'vitest';
import { clearAllDrafts, dropStaleDraft, getDraft, setDraft } from './config-drafts';

describe('config-drafts (Story 23.5)', () => {
  beforeEach(() => clearAllDrafts());

  it('returns a draft only for its version, without dropping it (review L-6)', () => {
    setDraft('x.json', { version: 'v1', text: 'draft' });

    expect(getDraft('x.json', 'v2')).toBeUndefined();
    expect(getDraft('x.json', 'v1')?.text).toBe('draft');
  });

  it('drops a draft made from another version when an edit starts', () => {
    setDraft('x.json', { version: 'v1', text: 'draft' });

    dropStaleDraft('x.json', 'v1');
    expect(getDraft('x.json', 'v1')).toBeDefined();

    dropStaleDraft('x.json', 'v2');
    expect(getDraft('x.json', 'v1')).toBeUndefined();
  });
});
