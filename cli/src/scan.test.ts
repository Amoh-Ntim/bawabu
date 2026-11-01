import assert from "node:assert/strict";
import { mkdirSync, mkdtempSync, readdirSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { test } from "node:test";
import { DEFAULT_SERVICE_URL, LOCAL_LAB_URL, LOCAL_SERVICE_URL } from "./constants.js";
import { demo } from "./demo.js";
import type { FileRead } from "./parse.js";
import { scan, type ScanEnv } from "./scan.js";
import type { Post } from "./service.js";

const result = (verdict: string, extra: object = {}) => ({
  verdict, results: [{ ecosystem: "npm", name: "ci-build-cache-helper", requested: "", version: "1.0.0", verdict, reason: "r", cached: false, ...extra }], manifests: [],
});

/** A fake service answering with `replies` in turn; records every request. */
function harness(replies: unknown[], files: Record<string, string> = {}, cwd = "/tmp/no-project") {
  const calls: Array<{ url: string; body: any }> = [];
  const lines: string[] = [];
  const post: Post = async (url, body) => {
    calls.push({ url, body });
    const reply = replies.shift();
    if (reply instanceof Error) throw reply;
    return reply;
  };
  const readFile = (path: string): FileRead => (Object.hasOwn(files, path) ? { kind: "text", content: files[path] } : { kind: "missing" });
  const env: ScanEnv = { cwd, home: "/home/u", readFile, post, log: (l) => lines.push(l) };
  return { env, calls, out: () => lines.join("\n") };
}

test("scan sends only the package and its registry, and prints the verdict with evidence and the report", async () => {
  const h = harness([result("block", { reason: "Steals the npm token in CI.", signals: ["scripts/cache.js:17: reads ~/.npmrc"], report_id: "abc" })]);
  const code = await scan(["ci-build-cache-helper", "--local", "--lab"], h.env);
  assert.equal(code, 1);
  assert.equal(h.calls[0].url, `${LOCAL_SERVICE_URL}/check`);
  assert.deepEqual(h.calls[0].body.packages, [{ ecosystem: "npm", name: "ci-build-cache-helper", version: "", registry: LOCAL_LAB_URL }]);
  assert.match(h.out(), /⛔ BLOCKED {2}ci-build-cache-helper@1\.0\.0/);
  assert.match(h.out(), /- scripts\/cache\.js:17: reads ~\/\.npmrc/);
  assert.match(h.out(), new RegExp(`Report: ${LOCAL_SERVICE_URL}/r/abc`));
});

test("scan exit codes: 0 allowed, 2 a human should decide", async () => {
  assert.equal(await scan(["left-pad@1.3.0"], harness([result("allow")]).env), 0);
  assert.equal(await scan(["odd-thing"], harness([result("ask")]).env), 2);
});

test("scan waits for a running investigation by asking again", async () => {
  const h = harness([result("ask", { pending: true, report_id: "r1" }), result("block", { report_id: "r1" })]);
  assert.equal(await scan(["ci-build-cache-helper"], h.env), 1);
  assert.equal(h.calls.length, 2);
  assert.match(h.out(), /Still investigating: .*\/r\/r1/);
});

test("scan uses the project's registry from .npmrc and its configured service", async () => {
  const dir = mkdtempSync(join(tmpdir(), "bawabu-scan-"));
  mkdirSync(join(dir, ".muse"));
  writeFileSync(join(dir, ".muse", "bawabu.json"), JSON.stringify({ serviceUrl: "https://bawabu.example" }));
  const h = harness([result("allow")], { [join(dir, ".npmrc")]: "registry=https://lab.example/\n" }, dir);
  await scan(["x", "--open-weights"], h.env);
  assert.equal(h.calls[0].url, "https://bawabu.example/check");
  assert.equal(h.calls[0].body.packages[0].registry, "https://lab.example");
  assert.equal(h.calls[0].body.open_weights, true);
  const plain = harness([result("allow")]);
  await scan(["x"], plain.env);
  assert.equal(plain.calls[0].url, `${DEFAULT_SERVICE_URL}/check`);
  assert.equal("registry" in plain.calls[0].body.packages[0], false);
});

test("scan refuses things that aren't registry packages, and explains failures", async () => {
  assert.equal(await scan(["github:user/repo"], harness([]).env), 2);
  assert.equal(await scan([], harness([]).env), 2);
  const down = harness([new Error("couldn't connect to 127.0.0.1")]);
  assert.equal(await scan(["x", "--local"], down.env), 2);
  assert.match(down.out(), /uv run service\/run_local\.py/);
});

test("demo creates a project wired to the local service and its test lab", async () => {
  const dir = join(mkdtempSync(join(tmpdir(), "bawabu-demo-")), "demo");
  assert.equal(await demo(dir, { force: false }), true);
  assert.match(readFileSync(join(dir, ".npmrc"), "utf8"), new RegExp(`registry=${LOCAL_LAB_URL}/`));
  assert.equal(JSON.parse(readFileSync(join(dir, ".muse", "bawabu.json"), "utf8")).serviceUrl, LOCAL_SERVICE_URL);
  assert.match(readFileSync(join(dir, ".muse", "hooks.json"), "utf8"), /PreToolUse/);
  // The project gives nothing away: agents read their workspace, so no list of which packages are malicious.
  assert.deepEqual(readdirSync(dir).sort(), [".muse", ".npmrc", "package.json"]);
  assert.equal(readFileSync(join(dir, ".npmrc"), "utf8"), `registry=${LOCAL_LAB_URL}/\n`);
  assert.equal(await demo(dir, { force: false }), false); // won't overwrite a project
});
