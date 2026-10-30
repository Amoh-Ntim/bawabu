import assert from "node:assert/strict";
import { mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { test } from "node:test";
import { isValidServiceUrl, loadConfig } from "./config.js";

test("service URLs must be https, except on this machine", () => {
  assert.ok(isValidServiceUrl("https://amoh-ntim--bawabu.modal.run"));
  assert.ok(isValidServiceUrl("http://127.0.0.1:8787"));
  assert.ok(isValidServiceUrl("http://localhost:8787/"));
  assert.ok(!isValidServiceUrl("http://bawabu.example"));
  assert.ok(!isValidServiceUrl("http://localhost.evil.example"));
  assert.ok(!isValidServiceUrl("ftp://x"));
});

test("a config with a plain-http service URL is rejected", () => {
  const path = join(mkdtempSync(join(tmpdir(), "bawabu-")), "bawabu.json");
  writeFileSync(path, JSON.stringify({ mode: "block", serviceUrl: "http://bawabu.example", allowlist: [] }));
  assert.throws(() => loadConfig(path), /https/);
});

test("openWeights defaults to false and must be a boolean", () => {
  const dir = mkdtempSync(join(tmpdir(), "bawabu-ow-"));
  const path = join(dir, "bawabu.json");
  writeFileSync(path, JSON.stringify({ mode: "block", serviceUrl: null }));
  assert.equal(loadConfig(path).openWeights, false);
  writeFileSync(path, JSON.stringify({ openWeights: true }));
  assert.equal(loadConfig(path).openWeights, true);
  writeFileSync(path, JSON.stringify({ openWeights: "yes" }));
  assert.throws(() => loadConfig(path), /openWeights/);
});
