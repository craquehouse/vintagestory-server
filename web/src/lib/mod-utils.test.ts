/**
 * Mod utility function tests.
 *
 * VSS-195: Tests for extractSlug, isValidSlug, and detectSlugOrUrl.
 */

import { describe, it, expect } from 'vitest';
import { extractSlug, isValidSlug, detectSlugOrUrl } from './mod-utils';

describe('extractSlug', () => {
  describe('URL extraction', () => {
    it('extracts slug from full URL with https', () => {
      expect(extractSlug('https://mods.vintagestory.at/smithingplus')).toBe(
        'smithingplus'
      );
    });

    it('extracts slug from full URL with http', () => {
      expect(extractSlug('http://mods.vintagestory.at/carrycapacity')).toBe(
        'carrycapacity'
      );
    });

    it('extracts slug from URL without protocol', () => {
      expect(extractSlug('mods.vintagestory.at/newmod')).toBe('newmod');
    });

    it('extracts slug from URL with query parameters', () => {
      expect(extractSlug('mods.vintagestory.at/modname?tab=files')).toBe(
        'modname'
      );
    });

    it('extracts slug from URL with hash fragment', () => {
      expect(extractSlug('mods.vintagestory.at/modname#downloads')).toBe(
        'modname'
      );
    });

    it('extracts slug from URL with both query and hash', () => {
      expect(extractSlug('https://mods.vintagestory.at/modname?tab=files#section')).toBe(
        'modname'
      );
    });

    it('handles URL with slug containing underscores', () => {
      expect(extractSlug('https://mods.vintagestory.at/expanded_foods')).toBe(
        'expanded_foods'
      );
    });
  });

  describe('plain slug extraction', () => {
    it('returns slug as-is when already a plain slug', () => {
      expect(extractSlug('smithingplus')).toBe('smithingplus');
    });

    it('converts slug to lowercase', () => {
      expect(extractSlug('SmithingPlus')).toBe('smithingplus');
    });

    it('trims whitespace', () => {
      expect(extractSlug('  smithingplus  ')).toBe('smithingplus');
    });

    it('handles slugs with underscores', () => {
      expect(extractSlug('expanded_foods')).toBe('expanded_foods');
    });

    it('handles slugs with hyphens', () => {
      expect(extractSlug('my-cool-mod')).toBe('my-cool-mod');
    });
  });

  describe('path extraction', () => {
    it('extracts slug from simple path', () => {
      expect(extractSlug('/smithingplus')).toBe('smithingplus');
    });

    it('extracts slug from deeply nested path', () => {
      expect(extractSlug('/foo/bar/baz/modname')).toBe('modname');
    });

    it('returns null for path with trailing slash', () => {
      expect(extractSlug('modname/')).toBeNull();
    });

    it('returns null for root path only', () => {
      expect(extractSlug('/')).toBeNull();
    });
  });

  describe('invalid input handling', () => {
    it('returns null for empty string', () => {
      expect(extractSlug('')).toBeNull();
    });

    it('returns null for whitespace only', () => {
      expect(extractSlug('   ')).toBeNull();
    });

    it('returns null for input with spaces', () => {
      expect(extractSlug('hello world')).toBeNull();
    });

    it('returns null for special characters', () => {
      expect(extractSlug('@#$%^&')).toBeNull();
    });

    it('returns null for input with dots (not a URL)', () => {
      expect(extractSlug('some.search.terms')).toBeNull();
    });
  });
});

describe('isValidSlug', () => {
  it('returns true for simple slug', () => {
    expect(isValidSlug('smithingplus')).toBe(true);
  });

  it('returns true for slug with underscore', () => {
    expect(isValidSlug('expanded_foods')).toBe(true);
  });

  it('returns true for slug with hyphen', () => {
    expect(isValidSlug('my-mod')).toBe(true);
  });

  it('returns true for slug with numbers', () => {
    expect(isValidSlug('mod123')).toBe(true);
  });

  it('returns false for slug with spaces', () => {
    expect(isValidSlug('my mod')).toBe(false);
  });

  it('returns false for slug with special characters', () => {
    expect(isValidSlug('mod@name')).toBe(false);
  });

  it('returns false for empty string', () => {
    expect(isValidSlug('')).toBe(false);
  });

  it('handles whitespace by trimming', () => {
    expect(isValidSlug('  smithingplus  ')).toBe(true);
  });

  it('returns false for slug with dots', () => {
    expect(isValidSlug('mod.name')).toBe(false);
  });
});

describe('detectSlugOrUrl', () => {
  describe('URL detection', () => {
    it('detects and extracts slug from https URL', () => {
      expect(detectSlugOrUrl('https://mods.vintagestory.at/smithingplus')).toBe(
        'smithingplus'
      );
    });

    it('detects and extracts slug from http URL', () => {
      expect(detectSlugOrUrl('http://mods.vintagestory.at/carrycapacity')).toBe(
        'carrycapacity'
      );
    });

    it('detects and extracts slug from URL without protocol', () => {
      expect(detectSlugOrUrl('mods.vintagestory.at/primitivesurvival')).toBe(
        'primitivesurvival'
      );
    });

    it('handles URL with query parameters', () => {
      expect(detectSlugOrUrl('mods.vintagestory.at/modname?tab=files')).toBe(
        'modname'
      );
    });

    it('handles URL with hash fragment', () => {
      expect(detectSlugOrUrl('mods.vintagestory.at/modname#section')).toBe(
        'modname'
      );
    });
  });

  describe('slug detection', () => {
    it('detects single-word slug', () => {
      expect(detectSlugOrUrl('smithingplus')).toBe('smithingplus');
    });

    it('detects slug with underscore', () => {
      expect(detectSlugOrUrl('expanded_foods')).toBe('expanded_foods');
    });

    it('detects slug with hyphen', () => {
      expect(detectSlugOrUrl('my-mod')).toBe('my-mod');
    });

    it('lowercases the slug', () => {
      expect(detectSlugOrUrl('SmithingPlus')).toBe('smithingplus');
    });

    it('trims whitespace', () => {
      expect(detectSlugOrUrl('  smithingplus  ')).toBe('smithingplus');
    });
  });

  describe('search query detection (returns null)', () => {
    it('returns null for multi-word search', () => {
      expect(detectSlugOrUrl('carry capacity')).toBeNull();
    });

    it('returns null for search with multiple words', () => {
      expect(detectSlugOrUrl('primitive survival mod')).toBeNull();
    });

    it('returns null for empty string', () => {
      expect(detectSlugOrUrl('')).toBeNull();
    });

    it('returns null for whitespace only', () => {
      expect(detectSlugOrUrl('   ')).toBeNull();
    });

    it('returns null for special characters that are not valid slug chars', () => {
      expect(detectSlugOrUrl('mod@name')).toBeNull();
    });

    it('returns null for search with dots (not a URL)', () => {
      expect(detectSlugOrUrl('some.search.terms')).toBeNull();
    });
  });
});
