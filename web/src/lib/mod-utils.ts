/**
 * Mod-related utility functions.
 *
 * VSS-195: Extracted from ModLookupInput for reuse in BrowseTab search.
 */

/**
 * Pattern to match VintageStory mod database URLs.
 * Captures the slug portion, stopping at query params (?) or hash (#).
 *
 * Examples:
 * - https://mods.vintagestory.at/smithingplus → captures "smithingplus"
 * - mods.vintagestory.at/modname?tab=files → captures "modname"
 */
const MODDB_URL_PATTERN = /mods\.vintagestory\.at\/([a-zA-Z0-9_-]+)(?:[?#]|$)/;

/**
 * Valid slug character pattern.
 * Slugs can contain: letters, numbers, underscores, hyphens.
 */
const VALID_SLUG_PATTERN = /^[a-zA-Z0-9_-]+$/;

/**
 * Checks if a string looks like a mod slug (valid characters only).
 *
 * Valid slug characters: letters (a-z, A-Z), numbers (0-9), underscores (_), hyphens (-).
 *
 * @param input - String to check
 * @returns true if input matches slug pattern (non-empty, valid chars only)
 */
export function isValidSlug(input: string): boolean {
  return VALID_SLUG_PATTERN.test(input.trim());
}

/**
 * Extracts a mod slug from a URL or returns the input as-is if it's already a slug.
 *
 * Handles:
 * - Full URLs: https://mods.vintagestory.at/smithingplus
 * - URLs with query params: mods.vintagestory.at/modname?tab=files
 * - Protocol-less URLs: mods.vintagestory.at/smithingplus
 * - Plain slugs: smithingplus
 *
 * @param input - User input (slug or URL)
 * @returns Extracted slug (lowercase), or null if input is invalid
 *
 * @example Valid inputs:
 * extractSlug('smithingplus') // => 'smithingplus'
 * extractSlug('SmithingPlus') // => 'smithingplus'
 * extractSlug('https://mods.vintagestory.at/smithingplus') // => 'smithingplus'
 * extractSlug('mods.vintagestory.at/modname?tab=files') // => 'modname'
 *
 * @example Invalid inputs:
 * extractSlug('hello world') // => null (contains space)
 * extractSlug('@#$%') // => null (invalid characters)
 * extractSlug('') // => null (empty)
 */
export function extractSlug(input: string): string | null {
  const trimmed = input.trim();

  if (!trimmed) {
    return null;
  }

  // Handle full URLs with or without protocol
  const urlMatch = trimmed.match(MODDB_URL_PATTERN);
  if (urlMatch) {
    return urlMatch[1].toLowerCase();
  }

  // Handle paths like "/modname" or "some/path/modname"
  if (trimmed.includes('/')) {
    const parts = trimmed.split('/');
    const lastPart = parts[parts.length - 1];
    // Only return if it looks like a valid slug (non-empty)
    if (lastPart && isValidSlug(lastPart)) {
      return lastPart.toLowerCase();
    }
    return null;
  }

  // Check if it's a valid slug directly
  if (isValidSlug(trimmed)) {
    return trimmed.toLowerCase();
  }

  return null;
}

/**
 * Detects if input looks like a mod slug or URL (not a search query).
 *
 * Returns the extracted slug if the input appears to be a direct mod reference,
 * or null if it looks like a regular search query.
 *
 * Detection heuristics:
 * - Contains mods.vintagestory.at URL pattern
 * - Is a single word matching slug pattern (no spaces, valid chars: a-zA-Z0-9_-)
 *
 * @param input - User input from search field
 * @returns Extracted slug or null if input is a search query
 */
export function detectSlugOrUrl(input: string): string | null {
  const trimmed = input.trim();

  if (!trimmed) {
    return null;
  }

  // Check for URL pattern first
  const urlMatch = trimmed.match(MODDB_URL_PATTERN);
  if (urlMatch) {
    return urlMatch[1].toLowerCase();
  }

  // If it has spaces, it's a search query
  if (trimmed.includes(' ')) {
    return null;
  }

  // Single word - check if it looks like a slug
  // Must be all valid slug characters
  if (isValidSlug(trimmed)) {
    return trimmed.toLowerCase();
  }

  return null;
}
