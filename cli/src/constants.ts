export const VERSION = "0.1.0";

/** Muse kills the hook after this long, and a killed hook lets the command run, so we must never reach it. */
export const HOOK_TIMEOUT_SECONDS = 180;

/** `bawabu check` gives up and blocks well before Muse's timeout. */
export const CHECK_DEADLINE_SECONDS = 150;

/** Inside .muse/ so the agent can't edit it without a human approving each write. */
export const CONFIG_RELATIVE_PATH = ".muse/bawabu.json";
