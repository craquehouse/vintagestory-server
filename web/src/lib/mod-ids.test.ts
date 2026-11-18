import { describe, it, expect } from 'vitest';
import {
  entryModIds,
  findInstalledModByIds,
  findInstalledModForEntry,
  versionChoices,
} from './mod-ids';

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
    expect(
      findInstalledModForEntry(mods, { slug: 'vsinstrumentsbase', releases: instrumentsReleases })
    ).toBe(mods[0]);
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

  it('matches an installed mod ID without case (Story 17.4)', () => {
    const mods = installed('VSInstrumentsBase');
    expect(findInstalledModForEntry(mods, entry)).toBe(mods[0]);
  });

  it('returns undefined when the installed list is empty or not loaded', () => {
    expect(findInstalledModForEntry([], entry)).toBeUndefined();
    expect(findInstalledModForEntry(undefined, entry)).toBeUndefined();
  });
});

describe('findInstalledModByIds (Story 17.4)', () => {
  const instrumentsIds = ['instruments', 'vsinstruments', 'vsinstrumentsbase'];

  it('finds an installed mod whose ID is any of the IDs', () => {
    const mods = installed('othermod', 'vsinstrumentsbase');
    expect(findInstalledModByIds(mods, instrumentsIds)).toBe(mods[1]);
  });

  it('lets the first matching ID win', () => {
    const mods = installed('vsinstrumentsbase', 'vsinstruments');
    expect(findInstalledModByIds(mods, instrumentsIds)).toBe(mods[1]);
    expect(findInstalledModByIds(mods, ['vsinstrumentsbase', 'vsinstruments'])).toBe(mods[0]);
  });

  it('matches without case', () => {
    const mods = installed('VSInstrumentsBase');
    expect(findInstalledModByIds(mods, ['vsinstrumentsbase'])).toBe(mods[0]);
    expect(findInstalledModByIds(installed('carryon'), ['CarryOn'])).toEqual({
      slug: 'carryon',
      version: '1.0.0',
    });
  });

  it('returns undefined when nothing matches', () => {
    expect(findInstalledModByIds(installed('smithingplus'), instrumentsIds)).toBeUndefined();
  });

  it('returns undefined for no IDs', () => {
    expect(findInstalledModByIds(installed('instruments'), [])).toBeUndefined();
  });

  it('returns undefined when the installed list is empty or not loaded', () => {
    expect(findInstalledModByIds([], instrumentsIds)).toBeUndefined();
    expect(findInstalledModByIds(undefined, instrumentsIds)).toBeUndefined();
  });
});

describe('versionChoices (Story 17.2)', () => {
  const release = (modidstr: string, version: string, fileId: number | null = 1) => ({
    modidstr,
    version,
    fileId,
  });

  it('lists only the releases of that exact mod ID, newest first', () => {
    const releases = [
      release('vsinstrumentsbase', '2.0.7'),
      release('vsinstrumentsbase', '1.0.1'),
      release('instruments', '1.2.2'),
      release('Instruments', '1.2.1'),
      release('instruments', '1.0.1'),
    ];

    expect(versionChoices(releases, 'instruments')).toEqual([
      { version: '1.2.2', installable: true },
      { version: '1.0.1', installable: true },
    ]);
  });

  it('keeps the first listing of a repeated version', () => {
    const releases = [release('demo', '1.0.0', null), release('demo', '1.0.0', 7)];

    expect(versionChoices(releases, 'demo')).toEqual([{ version: '1.0.0', installable: false }]);
  });

  it('marks a release without a positive file ID as not installable', () => {
    const releases = [
      release('demo', '3.0.0', null),
      release('demo', '2.0.0', 0),
      release('demo', '1.0.0', 5),
    ];

    expect(versionChoices(releases, 'demo')).toEqual([
      { version: '3.0.0', installable: false },
      { version: '2.0.0', installable: false },
      { version: '1.0.0', installable: true },
    ]);
  });

  it('returns nothing for an unknown mod ID', () => {
    expect(versionChoices([release('demo', '1.0.0')], 'other')).toEqual([]);
  });
});
