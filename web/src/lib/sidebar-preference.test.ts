import { describe, expect, it } from 'vitest';
import {
  SIDEBAR_PREFERENCES,
  isSidebarCollapsed,
  isSidebarPreference,
  readSidebarPreference,
  type SidebarPreference,
} from './sidebar-preference';

describe('SIDEBAR_PREFERENCES', () => {
  it('lists the three values in the order UI Preferences shows them', () => {
    expect(SIDEBAR_PREFERENCES).toEqual(['auto', 'expanded', 'collapsed']);
  });
});

describe('isSidebarPreference', () => {
  it.each(['auto', 'expanded', 'collapsed'])('accepts %s', (value) => {
    expect(isSidebarPreference(value)).toBe(true);
  });

  it.each([[''], ['Auto'], [undefined], [true]])('rejects %j', (value) => {
    expect(isSidebarPreference(value)).toBe(false);
  });
});

describe('readSidebarPreference', () => {
  it('is auto for an empty object', () => {
    expect(readSidebarPreference({})).toBe('auto');
  });

  it('reads the old sidebarCollapsed: true as collapsed', () => {
    expect(readSidebarPreference({ sidebarCollapsed: true })).toBe('collapsed');
  });

  it('reads the old sidebarCollapsed: false as auto', () => {
    expect(readSidebarPreference({ sidebarCollapsed: false })).toBe('auto');
  });

  it('lets a valid sidebar win over sidebarCollapsed', () => {
    expect(readSidebarPreference({ sidebar: 'expanded', sidebarCollapsed: true })).toBe('expanded');
  });

  it.each<SidebarPreference>(['auto', 'expanded', 'collapsed'])(
    'returns the stored %s',
    (value) => {
      expect(readSidebarPreference({ sidebar: value })).toBe(value);
    }
  );

  it.each([['bogus'], [null], [1]])('is auto when sidebar is %j', (value) => {
    expect(readSidebarPreference({ sidebar: value })).toBe('auto');
  });

  it('falls back to the old key when sidebar is not valid', () => {
    expect(readSidebarPreference({ sidebar: 'bogus', sidebarCollapsed: true })).toBe('collapsed');
  });

  it.each([['true'], [1]])('counts only the boolean true, not %j', (value) => {
    expect(readSidebarPreference({ sidebarCollapsed: value })).toBe('auto');
  });
});

describe('isSidebarCollapsed', () => {
  it.each<[SidebarPreference, boolean, boolean]>([
    ['auto', false, true],
    ['auto', true, false],
    ['expanded', false, false],
    ['expanded', true, false],
    ['collapsed', false, true],
    ['collapsed', true, true],
  ])('%s with isLgUp %s is collapsed: %s', (preference, isLgUp, expected) => {
    expect(isSidebarCollapsed(preference, isLgUp)).toBe(expected);
  });
});
