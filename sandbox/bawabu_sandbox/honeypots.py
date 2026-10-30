"""The bait planted in every sandbox run, and the paths we watch for.

A malicious install reaches for credentials: the npm token in ~/.npmrc, an SSH key, AWS keys, a
project .env. We plant *fake* ones whose only contents are unique canary strings. Reading such a
file is suspicious; sending its canary to a server is proof (it can only have come from the bait).

Each canary string is distinct, so when one shows up in a network request we know exactly which
secret leaked. The npm-token canary matches the test lab's fixtures (`npm_canary_7f3k9q`).
"""

from __future__ import annotations

from dataclasses import dataclass

# One canary per planted secret. Distinct, high-entropy, and easy to grep for.
NPM_TOKEN = "npm_canary_7f3k9q"
GITHUB_TOKEN = "ghp_canary9Qz1mX7bawabuK3tVpLs0rYwEdCn4"
SSH_KEY_MARK = "BAWABU-SSH-CANARY-4m2p8wq"
AWS_SECRET = "AWScanary/bawabu8rT2vL9xQ0mKpDe5nFhUa7Zy"
ENV_SECRET = "bawabu_env_canary_51nd0wq"

# Every distinct canary, for scanning network traffic. A hit on any of these is a leaked secret.
ALL_CANARIES: dict[str, str] = {
    "npm token (~/.npmrc)": NPM_TOKEN,
    "GitHub token ($GITHUB_TOKEN)": GITHUB_TOKEN,
    "SSH private key (~/.ssh/id_rsa)": SSH_KEY_MARK,
    "AWS secret key (~/.aws/credentials)": AWS_SECRET,
    "project secret (.env)": ENV_SECRET,
}


@dataclass(frozen=True)
class Bait:
    """A file to plant in the sandbox before the package runs."""

    path: str  # absolute path inside the sandbox
    contents: str


def planted_files(home: str = "/root", project: str = "/work/project") -> list[Bait]:
    """The fake secret files to write into the sandbox's lived-in home + project."""
    npmrc = f"//registry.npmjs.org/:_authToken={NPM_TOKEN}\nalways-auth=true\n"
    ssh_key = (
        "-----BEGIN OPENSSH PRIVATE KEY-----\n"
        f"{SSH_KEY_MARK}\n"
        "b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAAAMwAAAAtzc2gtZW\n"
        "(fake key — canary only, not a real credential)\n"
        "-----END OPENSSH PRIVATE KEY-----\n"
    )
    aws = f"[default]\naws_access_key_id = AKIACANARYBAWABU000\naws_secret_access_key = {AWS_SECRET}\n"
    env = f"# project secrets\nAPI_KEY={ENV_SECRET}\nDATABASE_URL=postgres://user:pass@db.internal/app\n"
    gitconfig = "[user]\n\tname = Alex Dev\n\temail = alex@example.com\n[init]\n\tdefaultBranch = main\n"
    bash_history = "ls\ngit status\nnpm run build\ncode .\nnpm test\ngit push\n"
    return [
        Bait(f"{home}/.npmrc", npmrc),
        Bait(f"{home}/.ssh/id_rsa", ssh_key),
        Bait(f"{home}/.aws/credentials", aws),
        Bait(f"{project}/.env", env),
        Bait(f"{home}/.gitconfig", gitconfig),
        Bait(f"{home}/.bash_history", bash_history),
    ]


def env_canaries() -> dict[str, str]:
    """Canary values exposed as environment variables, the way CI secrets appear to a build."""
    return {"NPM_TOKEN": NPM_TOKEN, "GITHUB_TOKEN": GITHUB_TOKEN}


# Paths whose being opened is a signal on its own (whether or not anything leaves).
SECRET_PATHS: tuple[str, ...] = (
    "/.npmrc",
    "/.ssh/",
    "/.aws/",
    "/.config/gh/",
    "/.docker/config.json",
    "/.netrc",
    "/.env",
    "/.git-credentials",
)


def is_secret_path(path: str) -> bool:
    """True if `path` looks like a credential store we planted or that real secrets live in."""
    p = path.rstrip("\x00")
    return any(marker in p for marker in SECRET_PATHS)
