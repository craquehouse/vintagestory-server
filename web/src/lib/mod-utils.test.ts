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

  describe('edge cases', () => {
    it('extracts slug from uppercase domain via path extraction', () => {
      // URL pattern is case-sensitive for domain, falls through to path extraction
      expect(extractSlug('https://MODS.VINTAGESTORY.AT/smithingplus')).toBe(
        'smithingplus'
      );
    });

    it('handles URL with mixed case slug', () => {
      expect(extractSlug('https://mods.vintagestory.at/SmithingPlus')).toBe(
        'smithingplus'
      );
    });

    it('returns null for URL with trailing slash after slug', () => {
      // Trailing slash creates empty path segment, which is invalid
      expect(extractSlug('https://mods.vintagestory.at/smithingplus/')).toBeNull();
    });

    it('extracts slug with numbers', () => {
      expect(extractSlug('mod123')).toBe('mod123');
    });

    it('extracts slug starting with number', () => {
      expect(extractSlug('123mod')).toBe('123mod');
    });

    it('extracts slug with mixed underscores and hyphens', () => {
      expect(extractSlug('my_cool-mod')).toBe('my_cool-mod');
    });

    it('handles path with multiple slashes', () => {
      expect(extractSlug('//mods//smithingplus')).toBe('smithingplus');
    });

    it('handles path with empty segments', () => {
      expect(extractSlug('/foo//bar///modname')).toBe('modname');
    });

    it('returns null for path with invalid slug characters in final segment', () => {
      expect(extractSlug('/path/to/mod name')).toBeNull();
    });

    it('returns null for path with special chars in final segment', () => {
      expect(extractSlug('/path/to/@invalid')).toBeNull();
    });

    it('extracts slug from URL with port via path extraction', () => {
      // Port breaks URL pattern match, falls through to path extraction
      expect(extractSlug('https://mods.vintagestory.at:443/smithingplus')).toBe(
        'smithingplus'
      );
    });

    it('extracts slug from path even when domain does not match', () => {
      // URL pattern doesn't match, falls through to path extraction
      expect(extractSlug('https://otherdomain.com/modname')).toBe('modname');
    });

    it('extracts slug from path when partial domain match', () => {
      // URL pattern doesn't match exactly, falls through to path extraction
      expect(extractSlug('notmods.vintagestory.at/modname')).toBe('modname');
    });

    it('extracts slug from URL with www subdomain via path extraction', () => {
      // URL pattern doesn't match www., falls through to path extraction
      expect(extractSlug('https://www.mods.vintagestory.at/smithingplus')).toBe(
        'smithingplus'
      );
    });

    it('returns null for single slash', () => {
      expect(extractSlug('/')).toBeNull();
    });

    it('returns null for multiple slashes only', () => {
      expect(extractSlug('///')).toBeNull();
    });

    it('handles tab characters by trimming', () => {
      expect(extractSlug('\tsmithingplus\t')).toBe('smithingplus');
    });

    it('handles newline characters by trimming', () => {
      expect(extractSlug('\nsmithingplus\n')).toBe('smithingplus');
    });

    it('returns null for slug with newline in middle', () => {
      expect(extractSlug('smith\ningplus')).toBeNull();
    });

    it('returns null for unicode characters', () => {
      expect(extractSlug('modñame')).toBeNull();
    });

    it('returns null for emoji', () => {
      expect(extractSlug('mod🎮')).toBeNull();
    });

    it('handles very long valid slug', () => {
      const longSlug = 'a'.repeat(1000);
      expect(extractSlug(longSlug)).toBe(longSlug);
    });

    it('handles very long URL with valid slug', () => {
      const longSlug = 'a'.repeat(100);
      expect(extractSlug(`https://mods.vintagestory.at/${longSlug}`)).toBe(longSlug);
    });

    it('returns null for path ending with invalid characters', () => {
      expect(extractSlug('/path/mod@')).toBeNull();
    });

    it('extracts slug from path with valid trailing segment', () => {
      expect(extractSlug('/invalid@path/valid-slug')).toBe('valid-slug');
    });

    it('handles single underscore slug', () => {
      expect(extractSlug('_')).toBe('_');
    });

    it('handles single hyphen slug', () => {
      expect(extractSlug('-')).toBe('-');
    });

    it('handles single character slug', () => {
      expect(extractSlug('a')).toBe('a');
    });

    it('handles single number slug', () => {
      expect(extractSlug('1')).toBe('1');
    });

    it('returns null for URL with query param but no slug', () => {
      expect(extractSlug('https://mods.vintagestory.at/?query=value')).toBeNull();
    });

    it('returns null for URL with hash but no slug', () => {
      expect(extractSlug('https://mods.vintagestory.at/#section')).toBeNull();
    });

    it('handles URL with multiple query parameters', () => {
      expect(extractSlug('https://mods.vintagestory.at/modname?tab=files&sort=date')).toBe(
        'modname'
      );
    });

    it('handles URL with complex query string', () => {
      expect(extractSlug('https://mods.vintagestory.at/modname?a=1&b=2&c=3#hash')).toBe(
        'modname'
      );
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
