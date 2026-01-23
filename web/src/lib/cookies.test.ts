import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { getCookie, setCookie, deleteCookie } from "./cookies";

describe("cookies", () => {
  beforeEach(() => {
    // Clear all cookies before each test
    document.cookie.split(";").forEach((cookie) => {
      const name = cookie.split("=")[0].trim();
      if (name) {
        document.cookie = `${name}=; max-age=0; path=/`;
      }
    });
  });

  afterEach(() => {
    // Clean up test cookies
    document.cookie.split(";").forEach((cookie) => {
      const name = cookie.split("=")[0].trim();
      if (name) {
        document.cookie = `${name}=; max-age=0; path=/`;
      }
    });
  });

  describe("getCookie", () => {
    it("returns null for non-existent cookie", () => {
      expect(getCookie("nonexistent")).toBeNull();
    });

    it("returns cookie value when present", () => {
      document.cookie = "testCookie=testValue; path=/";
      expect(getCookie("testCookie")).toBe("testValue");
    });

    it("handles cookies with = in value", () => {
      document.cookie = "base64Cookie=abc=def=; path=/";
      expect(getCookie("base64Cookie")).toBe("abc=def=");
    });

    it("decodes URI-encoded values", () => {
      document.cookie = "encoded=%7B%22key%22%3A%22value%22%7D; path=/";
      expect(getCookie("encoded")).toBe('{"key":"value"}');
    });

    it("returns correct cookie when multiple exist", () => {
      document.cookie = "first=one; path=/";
      document.cookie = "second=two; path=/";
      document.cookie = "third=three; path=/";
      expect(getCookie("second")).toBe("two");
    });
  });

  describe("setCookie", () => {
    it("sets a cookie with default max-age", () => {
      setCookie("newCookie", "newValue");
      expect(getCookie("newCookie")).toBe("newValue");
    });

    it("sets a cookie with custom max-age", () => {
      setCookie("shortLived", "value", 3600);
      expect(getCookie("shortLived")).toBe("value");
    });

    it("URI-encodes special characters in value", () => {
      const jsonValue = '{"theme":"dark","fontSize":14}';
      setCookie("prefs", jsonValue);
      expect(getCookie("prefs")).toBe(jsonValue);
    });

    it("overwrites existing cookie with same name", () => {
      setCookie("updateMe", "original");
      setCookie("updateMe", "updated");
      expect(getCookie("updateMe")).toBe("updated");
    });
  });

  describe("deleteCookie", () => {
    it("deletes an existing cookie", () => {
      setCookie("toDelete", "value");
      expect(getCookie("toDelete")).toBe("value");

      deleteCookie("toDelete");
      expect(getCookie("toDelete")).toBeNull();
    });

    it("does nothing when deleting non-existent cookie", () => {
      // Should not throw
      deleteCookie("doesNotExist");
      expect(getCookie("doesNotExist")).toBeNull();
    });
  });

  describe("SSR compatibility", () => {
    it("getCookie returns null when document is undefined", () => {
      // Save original document
      const originalDocument = global.document;

      // Simulate SSR by removing document
      // @ts-expect-error - Intentionally testing SSR scenario
      delete global.document;

      expect(getCookie("any")).toBeNull();

      // Restore document
      global.document = originalDocument;
    });

    it("setCookie does nothing when document is undefined", () => {
      // Save original document
      const originalDocument = global.document;

      // Simulate SSR by removing document
      // @ts-expect-error - Intentionally testing SSR scenario
      delete global.document;

      // Should not throw
      setCookie("ssr-test", "value");

      // Restore document
      global.document = originalDocument;

      // Cookie should not exist (wasn't set during SSR)
      expect(getCookie("ssr-test")).toBeNull();
    });

    it("deleteCookie does nothing when document is undefined", () => {
      // Set a cookie first
      setCookie("ssr-delete-test", "value");
      expect(getCookie("ssr-delete-test")).toBe("value");

      // Save original document
      const originalDocument = global.document;

      // Simulate SSR by removing document
      // @ts-expect-error - Intentionally testing SSR scenario
      delete global.document;

      // Should not throw
      deleteCookie("ssr-delete-test");

      // Restore document
      global.document = originalDocument;

      // Cookie should still exist (wasn't deleted during SSR)
      expect(getCookie("ssr-delete-test")).toBe("value");
    });
  });
});
