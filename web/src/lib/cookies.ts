/**
 * Cookie utility functions for client-side preference storage.
 *
 * Provides simple wrappers around document.cookie with proper encoding
 * and sensible defaults for SameSite and path settings.
 */

/**
 * Get a cookie value by name.
 *
 * @param name - Cookie name to retrieve
 * @returns Cookie value or null if not found
 */
export function getCookie(name: string): string | null {
  if (typeof document === "undefined") return null;

  const cookies = document.cookie.split("; ");
  for (const cookie of cookies) {
    const [cookieName, ...valueParts] = cookie.split("=");
    if (cookieName === name) {
      return decodeURIComponent(valueParts.join("="));
    }
  }
  return null;
}

/**
 * Set a cookie with optional max-age.
 *
 * @param name - Cookie name
 * @param value - Cookie value (will be URI encoded)
 * @param maxAge - Max age in seconds (default: 1 year)
 */
export function setCookie(
  name: string,
  value: string,
  maxAge: number = 31536000
): void {
  if (typeof document === "undefined") return;

  const encodedValue = encodeURIComponent(value);
  document.cookie = `${name}=${encodedValue}; path=/; max-age=${maxAge}; SameSite=Lax`;
}

/**
 * Delete a cookie by setting its max-age to 0.
 *
 * @param name - Cookie name to delete
 */
export function deleteCookie(name: string): void {
  if (typeof document === "undefined") return;

  document.cookie = `${name}=; path=/; max-age=0; SameSite=Lax`;
}
