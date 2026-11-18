/**
 * Version comparison shared by the installed mods table, the Version page table, the
 * Version page's "newer" mark and update offers, and the server version dialog's
 * upgrade/downgrade decision (Epic 21 ADR-8).
 *
 * Readable versions are ordered by Semantic Versioning 2.0.0 precedence (section 11):
 * numeric core parts, then a release above its pre-releases, then pre-release
 * identifiers one by one. Build metadata (`+...`) is ignored.
 *
 * Loose input: a leading `v` or `V` is ignored and a missing core part counts as 0, so
 * `1.2` reads as `1.2.0` and `v1.0.0` as `1.0.0`. Strings with no version shape (`beta`,
 * an empty string, `1.0.0 hotfix`, malformed versions) come after every readable one and
 * are ordered among themselves by a numeric-aware collation. When two strings have equal
 * precedence, the plain strings decide, so the order is total and the same for every
 * input order. The function never throws.
 */

const VERSION_PATTERN =
  /^v?(\d+(?:\.\d+)*)(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?(?:\+[0-9A-Za-z.-]+)?$/i;

const NUMERIC_IDENTIFIER = /^\d+$/;

// An explicit locale, so the order of unreadable strings does not depend on the browser's
const unreadableCollator = new Intl.Collator('en', { numeric: true });

interface ParsedVersion {
  core: number[];
  prerelease: string[];
}

function parseVersion(value: string): ParsedVersion | null {
  const match = VERSION_PATTERN.exec(value);
  if (!match) return null;
  return {
    core: match[1].split('.').map(Number),
    prerelease: match[2] ? match[2].split('.') : [],
  };
}

function sign(value: number): number {
  return value < 0 ? -1 : value > 0 ? 1 : 0;
}

function compareStrings(a: string, b: string): number {
  return a < b ? -1 : a > b ? 1 : 0;
}

function compareIdentifiers(a: string, b: string): number {
  const aNumeric = NUMERIC_IDENTIFIER.test(a);
  const bNumeric = NUMERIC_IDENTIFIER.test(b);
  if (aNumeric && bNumeric) return sign(Number(a) - Number(b));
  if (aNumeric) return -1;
  if (bNumeric) return 1;
  return compareStrings(a, b);
}

function comparePrecedence(a: ParsedVersion, b: ParsedVersion): number {
  const coreLength = Math.max(a.core.length, b.core.length);
  for (let i = 0; i < coreLength; i++) {
    const diff = sign((a.core[i] ?? 0) - (b.core[i] ?? 0));
    if (diff !== 0) return diff;
  }

  // A release is greater than any of its pre-releases
  if (a.prerelease.length === 0 || b.prerelease.length === 0) {
    return sign(b.prerelease.length - a.prerelease.length);
  }

  const shared = Math.min(a.prerelease.length, b.prerelease.length);
  for (let i = 0; i < shared; i++) {
    const diff = compareIdentifiers(a.prerelease[i], b.prerelease[i]);
    if (diff !== 0) return diff;
  }
  return sign(a.prerelease.length - b.prerelease.length);
}

/**
 * Compare two version strings by precedence only: unlike `compareVersions`, two strings
 * that name the same version (`1.0.0`, `v1.0.0`, `1.0.0+build`, `01.0.0`, `1.0`) give 0.
 * Use it to ask "is this the same version?"; use `compareVersions` to sort.
 *
 * @returns -1 if `a` has lower precedence than `b`, 1 if higher, 0 if equal
 */
export function compareVersionPrecedence(a: string, b: string): number {
  const parsedA = parseVersion(a);
  const parsedB = parseVersion(b);

  if (parsedA && parsedB) return comparePrecedence(parsedA, parsedB);
  if (parsedA) return -1;
  if (parsedB) return 1;
  return sign(unreadableCollator.compare(a, b));
}

/**
 * Compare two version strings for sorting: by precedence, then by the plain strings, so
 * the order is total.
 *
 * @returns -1 if `a` comes before `b`, 1 if after, 0 only if the strings are identical
 */
export function compareVersions(a: string, b: string): number {
  const result = compareVersionPrecedence(a, b);
  return result !== 0 ? result : compareStrings(a, b);
}
