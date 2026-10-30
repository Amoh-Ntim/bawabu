import assert from "node:assert/strict";
import { test } from "node:test";
import { cleanRegistry, npmRegistries } from "./npmrc.js";
import type { FileRead } from "./parse.js";
import { checkRequest } from "./service.js";

const files = (map: Record<string, string>) => (path: string): FileRead =>
  Object.hasOwn(map, path) ? { kind: "text", content: map[path] } : { kind: "missing" };

test("the project's .npmrc wins over the user's, and the public npm sends nothing", () => {
  const read = files({
    "/work/app/.npmrc": "registry=https://lab.example/\n//lab.example/:_auth=c2VjcmV0\n",
    "/home/u/.npmrc": "registry=https://other.example\n",
  });
  assert.equal(npmRegistries("/work/app", "/home/u", read)("left-pad"), "https://lab.example");
  assert.equal(npmRegistries("/elsewhere", "/home/u", read)("left-pad"), "https://other.example");
  assert.equal(npmRegistries("/x", "/nohome", files({ "/x/.npmrc": "registry=https://registry.npmjs.org/" }))("a"), null);
  assert.equal(npmRegistries("/x", "/nohome", files({}))("a"), null);
});

test("a parent folder's .npmrc counts (monorepo packages)", () => {
  const read = files({ "/repo/.npmrc": "registry=https://lab.example" });
  assert.equal(npmRegistries("/repo/packages/web", "/home/u", read)("x"), "https://lab.example");
});

test("scoped registries apply to their scope only", () => {
  const read = files({ "/w/.npmrc": "@acme:registry=https://npm.acme.example/\nregistry=https://registry.npmjs.org/" });
  const lookup = npmRegistries("/w", "/h", read);
  assert.equal(lookup("@acme/ui"), "https://npm.acme.example");
  assert.equal(lookup("@other/ui"), null);
  assert.equal(lookup("react"), null);
});

test("credentials in a registry URL are never sent, and odd values are ignored", () => {
  assert.equal(cleanRegistry("https://user:pass@lab.example/npm/?token=abc"), "https://lab.example/npm");
  assert.equal(cleanRegistry("file:///etc/passwd"), null);
  const read = files({ "/w/.npmrc": "registry=${NPM_REGISTRY}\n; registry=https://commented.example\n" });
  assert.equal(npmRegistries("/w", "/h", read)("x"), null);
});

test("the check request carries the registry for npm packages only", () => {
  const installs = [
    { manager: "npm", action: "add" as const, command: "npm i a", packages: [{ ecosystem: "npm" as const, name: "a", version: "", source: "registry" as const, raw: "a" }] },
    { manager: "pip", action: "add" as const, command: "pip install b", packages: [{ ecosystem: "pypi" as const, name: "b", version: "", source: "registry" as const, raw: "b" }] },
  ];
  const body = checkRequest(installs, () => "https://lab.example");
  assert.deepEqual(body.packages, [
    { ecosystem: "npm", name: "a", version: "", registry: "https://lab.example" },
    { ecosystem: "pypi", name: "b", version: "" },
  ]);
  assert.deepEqual(checkRequest(installs).packages[0], { ecosystem: "npm", name: "a", version: "" });
});
