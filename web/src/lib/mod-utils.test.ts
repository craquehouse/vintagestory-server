/**
 * Mod utility function tests.
 *
 * VSS-195: Tests for isValidSlug and detectSlugOrUrl.
 */

import { describe, it, expect } from 'vitest';
import { isValidSlug, detectSlugOrUrl } from './mod-utils';

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

  describe('edge cases', () => {
    it('returns true for uppercase letters', () => {
      expect(isValidSlug('MODNAME')).toBe(true);
    });

    it('returns true for mixed case', () => {
      expect(isValidSlug('ModName123')).toBe(true);
    });

    it('returns true for single character', () => {
      expect(isValidSlug('a')).toBe(true);
    });

    it('returns true for single number', () => {
      expect(isValidSlug('1')).toBe(true);
    });

    it('returns true for single underscore', () => {
      expect(isValidSlug('_')).toBe(true);
    });

    it('returns true for single hyphen', () => {
      expect(isValidSlug('-')).toBe(true);
    });

    it('returns true for slug starting with number', () => {
      expect(isValidSlug('123mod')).toBe(true);
    });

    it('returns true for slug starting with underscore', () => {
      expect(isValidSlug('_privatemod')).toBe(true);
    });

    it('returns true for slug starting with hyphen', () => {
      expect(isValidSlug('-mod')).toBe(true);
    });

    it('returns true for slug with multiple consecutive underscores', () => {
      expect(isValidSlug('mod__name')).toBe(true);
    });

    it('returns true for slug with multiple consecutive hyphens', () => {
      expect(isValidSlug('mod--name')).toBe(true);
    });

    it('returns false for slug with forward slash', () => {
      expect(isValidSlug('mod/name')).toBe(false);
    });

    it('returns false for slug with backslash', () => {
      expect(isValidSlug('mod\\name')).toBe(false);
    });

    it('returns false for slug with parentheses', () => {
      expect(isValidSlug('mod(name)')).toBe(false);
    });

    it('returns false for slug with brackets', () => {
      expect(isValidSlug('mod[name]')).toBe(false);
    });

    it('returns false for slug with plus sign', () => {
      expect(isValidSlug('mod+name')).toBe(false);
    });

    it('returns false for slug with equals sign', () => {
      expect(isValidSlug('mod=name')).toBe(false);
    });

    it('returns false for slug with unicode characters', () => {
      expect(isValidSlug('modñame')).toBe(false);
    });

    it('returns false for slug with emoji', () => {
      expect(isValidSlug('mod🎮name')).toBe(false);
    });

    it('returns false for whitespace-only after trim', () => {
      expect(isValidSlug('\t\n\r')).toBe(false);
    });

    it('returns true for very long slug with valid characters', () => {
      const longSlug = 'a'.repeat(1000);
      expect(isValidSlug(longSlug)).toBe(true);
    });
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

  describe('edge cases', () => {
    it('detects slug with numbers', () => {
      expect(detectSlugOrUrl('mod123')).toBe('mod123');
    });

    it('detects slug starting with number', () => {
      expect(detectSlugOrUrl('123mod')).toBe('123mod');
    });

    it('detects slug with multiple underscores', () => {
      expect(detectSlugOrUrl('my__mod')).toBe('my__mod');
    });

    it('detects slug with multiple hyphens', () => {
      expect(detectSlugOrUrl('my--mod')).toBe('my--mod');
    });

    it('detects mixed case and lowercases it', () => {
      expect(detectSlugOrUrl('MyModName')).toBe('mymodname');
    });

    it('returns null for URL with trailing slash', () => {
      // Trailing slash creates empty segment, not matched by URL pattern
      expect(detectSlugOrUrl('https://mods.vintagestory.at/modname/')).toBeNull();
    });

    it('returns null for URL with port number', () => {
      // Port number breaks the URL pattern match
      expect(detectSlugOrUrl('https://mods.vintagestory.at:443/modname')).toBeNull();
    });

    it('handles URL with multiple query params', () => {
      expect(detectSlugOrUrl('https://mods.vintagestory.at/modname?a=1&b=2')).toBe(
        'modname'
      );
    });

    it('returns null for URL with wrong domain (contains slash)', () => {
      // Contains slash, not a plain slug, and doesn't match URL pattern
      expect(detectSlugOrUrl('https://example.com/modname')).toBeNull();
    });

    it('detects slug from partial domain match', () => {
      // URL pattern matches anywhere in string, so this matches
      expect(detectSlugOrUrl('notmods.vintagestory.at/modname')).toBe('modname');
    });

    it('detects slug from URL with www subdomain', () => {
      // URL pattern matches anywhere in string, so this matches
      expect(detectSlugOrUrl('https://www.mods.vintagestory.at/modname')).toBe(
        'modname'
      );
    });

    it('returns null for input with tab character', () => {
      expect(detectSlugOrUrl('mod\tname')).toBeNull();
    });

    it('returns null for input with newline', () => {
      expect(detectSlugOrUrl('mod\nname')).toBeNull();
    });

    it('handles leading/trailing tabs by trimming', () => {
      expect(detectSlugOrUrl('\tmodname\t')).toBe('modname');
    });

    it('handles leading/trailing newlines by trimming', () => {
      expect(detectSlugOrUrl('\nmodname\n')).toBe('modname');
    });

    it('returns null for unicode characters', () => {
      expect(detectSlugOrUrl('modñame')).toBeNull();
    });

    it('returns null for emoji', () => {
      expect(detectSlugOrUrl('mod🎮')).toBeNull();
    });

    it('returns null for slash-separated terms', () => {
      expect(detectSlugOrUrl('mod/name')).toBeNull();
    });

    it('returns null for parentheses', () => {
      expect(detectSlugOrUrl('mod(name)')).toBeNull();
    });

    it('returns null for brackets', () => {
      expect(detectSlugOrUrl('mod[name]')).toBeNull();
    });

    it('returns null for plus sign', () => {
      expect(detectSlugOrUrl('mod+plus')).toBeNull();
    });

    it('returns null for equals sign', () => {
      expect(detectSlugOrUrl('mod=name')).toBeNull();
    });

    it('detects single character slug', () => {
      expect(detectSlugOrUrl('a')).toBe('a');
    });

    it('detects single number slug', () => {
      expect(detectSlugOrUrl('1')).toBe('1');
    });

    it('detects single underscore', () => {
      expect(detectSlugOrUrl('_')).toBe('_');
    });

    it('detects single hyphen', () => {
      expect(detectSlugOrUrl('-')).toBe('-');
    });

    it('detects slug starting with underscore', () => {
      expect(detectSlugOrUrl('_privatemod')).toBe('_privatemod');
    });

    it('detects slug starting with hyphen', () => {
      expect(detectSlugOrUrl('-mod')).toBe('-mod');
    });

    it('handles very long valid slug', () => {
      const longSlug = 'a'.repeat(1000);
      expect(detectSlugOrUrl(longSlug)).toBe(longSlug);
    });

    it('handles very long URL', () => {
      const longSlug = 'a'.repeat(100);
      expect(detectSlugOrUrl(`https://mods.vintagestory.at/${longSlug}`)).toBe(
        longSlug
      );
    });

    it('returns null for URL without slug path', () => {
      expect(detectSlugOrUrl('https://mods.vintagestory.at/')).toBeNull();
    });

    it('returns null for URL with only query params', () => {
      expect(detectSlugOrUrl('https://mods.vintagestory.at/?query=value')).toBeNull();
    });

    it('returns null for URL with only hash', () => {
      expect(detectSlugOrUrl('https://mods.vintagestory.at/#section')).toBeNull();
    });

    it('returns null for URL with uppercase domain', () => {
      // Regex is case-sensitive for domain, doesn't match uppercase domain
      expect(detectSlugOrUrl('https://MODS.VINTAGESTORY.AT/modname')).toBeNull();
    });

    it('handles URL with mixed case slug', () => {
      expect(detectSlugOrUrl('https://mods.vintagestory.at/ModName')).toBe('modname');
    });

    it('returns null for search query with special delimiter', () => {
      expect(detectSlugOrUrl('search:term')).toBeNull();
    });

    it('returns null for at-mention style', () => {
      expect(detectSlugOrUrl('@username')).toBeNull();
    });

    it('returns null for hashtag style', () => {
      expect(detectSlugOrUrl('#hashtag')).toBeNull();
    });
  });
});
