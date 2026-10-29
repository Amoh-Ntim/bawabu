# Bawabu test lab

Fixtures for testing Bawabu's detection, plus the tricky-but-legitimate packages that must **not** be
flagged. Each fixture reproduces the *shape* of a known supply-chain attack so Bawabu's checks, sandbox and
investigator can be measured against it. **None of them does anything harmful.**

## Safety model

These are test fixtures, not malware. Every "attack" fixture is deliberately inert:

- **Nothing can leave — this is the real guarantee.** Any "exfiltration" is an attempt to reach a host under
  a reserved domain (`.invalid` / `.example`, RFC 2606 / 6761) that can never resolve on the real internet.
  Inside the Step 5 sandbox a fake DNS + HTTP sink answers these and records the attempt; anywhere else the
  request simply fails. No fixture ever reaches a real host.
- **Secret paths are opened, not harvested.** A credential-grab fixture *opens* a canonical secrets path
  (`~/.npmrc`, `~/.ssh/id_rsa`) because that open is exactly the behaviour Bawabu's sandbox must detect
  (via `strace`). Opening a file read-only is harmless on its own, and since the only destination is a dead
  sink, the contents can never leave. In the Step 5 sandbox these paths hold **planted canaries**
  (`npm_canary_7f3k9q`), so even the bytes that are read are fake. A fixture prefers a harness-planted path
  from `$BAWABU_CANARY_NPMRC` when set.
- **Clearly labelled.** Every executable file starts with a `BAWABU TEST FIXTURE — harmless` banner.
- **Never public.** These names are published only to our private Verdaccio registry. They are never pushed
  to the real npm. (All names were checked to be unregistered, so a fixture can't shadow a real package.)

## Layout

- `packages/<name>/` — one npm package per folder: `package.json` + source.
- `manifest.json` — the catalogue: every package, the attack technique it mirrors, the verdict Bawabu should
  reach, and which layer should catch it. The eval harness (Step 11) reads this.
- `publish.sh` — publishes every package to the Verdaccio registry in `$BAWABU_REGISTRY`.

## The fixtures

Numbered to match plan.md section 9. Expected verdict is what Bawabu should ultimately return; the "caught by"
column names the layer that should be decisive.

See `manifest.json` for the machine-readable version.
