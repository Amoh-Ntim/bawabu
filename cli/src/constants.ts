export const VERSION = "0.1.0";

/** Muse kills the hook after this long, and a killed hook lets the command run, so we must never reach it. */
export const HOOK_TIMEOUT_SECONDS = 180;

/** `bawabu check` gives up and blocks well before Muse's timeout. */
export const CHECK_DEADLINE_SECONDS = 150;

/** The hosted Bawabu service; `bawabu init --service <url>` points a project elsewhere. */
export const DEFAULT_SERVICE_URL = "https://amohntim123--bawabu.us-east.modal.run";

/** How long to wait for the service's verdict, inside the deadline above. */
export const SERVICE_TIMEOUT_SECONDS = 140;

/** Inside .muse/ so the agent can't edit it without a human approving each write. */
export const CONFIG_RELATIVE_PATH = ".muse/bawabu.json";

/** The service run on this machine with your own API keys (service/run_local.py), and its built-in test lab. */
export const LOCAL_SERVICE_URL = "http://127.0.0.1:8787";
export const LOCAL_LAB_URL = `${LOCAL_SERVICE_URL}/lab`;
