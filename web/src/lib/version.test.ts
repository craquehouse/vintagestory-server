import { readFileSync } from "fs";
import path from "path";
import { APP_VERSION } from "./version";

describe("APP_VERSION", () => {
  it("is the version in package.json", () => {
    const pkg = JSON.parse(
      readFileSync(path.resolve(import.meta.dirname, "../../package.json"), "utf8")
    ) as { version: string };

    expect(APP_VERSION).toBe(pkg.version);
  });
});
