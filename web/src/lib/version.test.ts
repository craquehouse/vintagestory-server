import { readFileSync } from "fs";
import path from "path";
import { APP_VERSION } from "./version";

const webRoot = path.resolve(import.meta.dirname, "../..");

describe("APP_VERSION", () => {
  it("is the version in package.json", () => {
    const pkg = JSON.parse(readFileSync(path.join(webRoot, "package.json"), "utf8")) as {
      version: string;
    };

    expect(APP_VERSION).toBe(pkg.version);
  });

  // Tests run with vitest.config.ts, so only this check catches a production build
  // (vite.config.ts) that no longer defines __APP_VERSION__ and would fail at runtime.
  it.each(["vite.config.ts", "vitest.config.ts"])("is defined from package.json in %s", (file) => {
    const config = readFileSync(path.join(webRoot, file), "utf8");

    expect(config).toContain("__APP_VERSION__: JSON.stringify(pkg.version)");
    expect(config).toContain("'package.json'");
  });
});
