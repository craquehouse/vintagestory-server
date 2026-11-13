import { describe, it, expect } from 'vitest';
import { entryModIds, findInstalledModForEntry } from './mod-ids';

/** Releases shaped like the Instruments entry (fixture mod_instruments.json): newest first. */
const instrumentsReleases = [
  { modidstr: 'vsinstrumentsbase' },
  { modidstr: 'vsinstrumentsbase' },
  { modidstr: 'vsinstruments' },
  { modidstr: 'vsinstruments' },
  { modidstr: 'instruments' },
  { modidstr: 'instruments' },
];

function installed(...slugs: string[]) {
  return slugs.map((slug) => ({ slug, version: '1.0.0' }));
}

describe('entryModIds', () => {
  it('lists each mod ID once, in release order (newest first)', () => {
    expect(entryModIds(instrumentsReleases)).toEqual([
      'vsinstrumentsbase',
      'vsinstruments',
      'instruments',
    ]);
  });

  it('drops empty mod IDs', () => {
    expect(entryModIds([{ modidstr: '' }, { modidstr: 'a' }, { modidstr: '' }])).toEqual(['a']);
  });

  it('returns an empty list for no releases', () => {
    expect(entryModIds([])).toEqual([]);
  });
});

describe('findInstalledModForEntry', () => {
  const entry = { slug: 'instruments', releases: instrumentsReleases };

  it('finds an installed mod whose ID is not the URL slug (last mod ID in the entry)', () => {
    const mods = installed('othermod', 'vsinstrumentsbase');
    expect(findInstalledModForEntry(mods, entry)).toBe(mods[1]);
  });

  it('finds an installed mod with a middle mod ID', () => {
    const mods = installed('vsinstruments');
    expect(findInstalledModForEntry(mods, { slug: 'vsinstrumentsbase', releases: instrumentsReleases })).toBe(
      mods[0]
    );
  });

  it('prefers the installed mod whose ID is the URL slug', () => {
    const mods = installed('vsinstrumentsbase', 'instruments');
    expect(findInstalledModForEntry(mods, entry)).toBe(mods[1]);
  });

  it('otherwise prefers the installed mod ID with the newest release', () => {
    const mods = installed('vsinstruments', 'vsinstrumentsbase');
    expect(findInstalledModForEntry(mods, entry)).toBe(mods[1]);
  });

  it('matches the URL slug when the releases carry no mod IDs', () => {
    const mods = installed('smithingplus');
    expect(
      findInstalledModForEntry(mods, { slug: 'smithingplus', releases: [{ modidstr: '' }] })
    ).toBe(mods[0]);
  });

  it('does not match an installed mod from another entry', () => {
    expect(findInstalledModForEntry(installed('smithingplus'), entry)).toBeUndefined();
  });

  it('compares mod IDs exactly', () => {
    expect(findInstalledModForEntry(installed('VSInstrumentsBase'), entry)).toBeUndefined();
  });

  it('returns undefined when the installed list is empty or not loaded', () => {
    expect(findInstalledModForEntry([], entry)).toBeUndefined();
    expect(findInstalledModForEntry(undefined, entry)).toBeUndefined();
  });
});
