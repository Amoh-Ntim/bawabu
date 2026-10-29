"""Popular package names: for "did you mean ...?" on made-up names, and for spotting lookalike (typosquat) names.

npm names come from the vendored popular_npm.py. The PyPI list (hugovk/top-pypi-packages) isn't redistributed
here, so it's fetched on first use and kept in memory.
"""

import itertools
import logging
import re
import string
from collections import Counter
from difflib import SequenceMatcher
from functools import lru_cache

import httpx

from .popular_npm import NAMES as NPM_NAMES

log = logging.getLogger(__name__)

PYPI_TOP_URL = "https://hugovk.github.io/top-pypi-packages/top-pypi-packages.min.json"
_ALPHABET = string.ascii_lowercase + string.digits + "-_."
_SEPARATORS = re.compile(r"[-_.@/]+")
# Very short names have too many one-letter neighbours to call any of them a lookalike.
_MIN_TYPO_LENGTH = 4
# How alike (0 to 1) a popular name must be to a corrected made-up name to be suggested.
_CLOSEST_RATIO = 0.8


def _key(name: str) -> str:
    """The name without separators, so react_dom, react.dom and reactdom all match react-dom."""
    return _SEPARATORS.sub("", name.lower())


def _edits1(word: str) -> set[str]:
    splits = [(word[:i], word[i:]) for i in range(len(word) + 1)]
    return set(itertools.chain(
        (a + b[1:] for a, b in splits if b),
        (a + b[1] + b[0] + b[2:] for a, b in splits if len(b) > 1),
        (a + c + b[1:] for a, b in splits if b for c in _ALPHABET),
        (a + c + b for a, b in splits for c in _ALPHABET),
    ))


class Popular:
    """A ranked list of names (rank 0 = most popular), indexed for lookalike search."""

    def __init__(self, names: list[str]) -> None:
        self.rank: dict[str, int] = {}
        for i, name in enumerate(names):
            self.rank.setdefault(name.lower(), i)
        self._keys = {name: _key(name) for name in self.rank}
        self._by_key: dict[str, list[str]] = {}
        for name, key in self._keys.items():
            self._by_key.setdefault(key, []).append(name)
        # Words used in popular names (react, date, picker, ...), for fixing misspelled words in made-up names.
        self._words = Counter(word for name in self.rank for word in _SEPARATORS.split(name) if word)

    def __contains__(self, name: str) -> bool:
        return name.lower() in self.rank

    def lookalike(self, name: str) -> str | None:
        """The most popular name one typo (or only separators) away from `name`, unless `name` is popular itself."""
        lowered = name.lower()
        if lowered in self.rank:
            return None
        candidates = set(self._by_key.get(_key(lowered), []))
        if len(lowered) >= _MIN_TYPO_LENGTH:
            candidates.update(c for c in _edits1(lowered) if c in self.rank)
        candidates.discard(lowered)
        return min(candidates, key=self.rank.__getitem__) if candidates else None

    def correct(self, name: str) -> str:
        """`name` with each misspelled word fixed to the most common popular-name word one typo away
        (react-datepickr -> react-datepicker, prisma-clinet -> prisma-client)."""
        fixed = []
        for word in (w for w in _SEPARATORS.split(name.lower()) if w):
            if word in self._words or len(word) < _MIN_TYPO_LENGTH:
                fixed.append(word)
            else:
                options = [c for c in _edits1(word) if c in self._words]
                fixed.append(max(options, key=self._words.__getitem__) if options else word)
        return "-".join(fixed)

    def closest(self, name: str) -> str | None:
        """The popular name most like `name`, if any is close enough; ties go to the more popular one."""
        key = _key(name)
        best: tuple[float, int, str] | None = None
        for candidate, candidate_key in self._keys.items():
            matcher = SequenceMatcher(None, key, candidate_key, autojunk=False)
            if matcher.real_quick_ratio() < _CLOSEST_RATIO or matcher.quick_ratio() < _CLOSEST_RATIO:
                continue
            ratio = matcher.ratio()
            if ratio >= _CLOSEST_RATIO and (best is None or (ratio, -self.rank[candidate]) > (best[0], -best[1])):
                best = (ratio, self.rank[candidate], candidate)
        return best[2] if best else None


@lru_cache
def npm() -> Popular:
    return Popular(NPM_NAMES)


_pypi: Popular | None = None


def pep503(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


async def for_ecosystem(client: httpx.AsyncClient, ecosystem: str) -> Popular | None:
    """None when the PyPI list can't be fetched right now; lookalike checks are skipped then."""
    global _pypi
    if ecosystem == "npm":
        return npm()
    if _pypi is None:
        try:
            response = await client.get(PYPI_TOP_URL, timeout=15)
            response.raise_for_status()
            _pypi = Popular([pep503(row["project"]) for row in response.json()["rows"]])
        except Exception:
            log.warning("couldn't fetch the popular PyPI list", exc_info=True)
            return None
    return _pypi


async def suggest(client: httpx.AsyncClient, ecosystem: str, name: str, popular: Popular | None) -> str | None:
    """A real package the agent probably meant, for a name that doesn't exist: a one-typo lookalike, else the
    closest popular name once misspelled words are fixed, else (npm only) npm's own search."""
    corrected = name
    if popular:
        if match := popular.lookalike(name):
            return match
        corrected = popular.correct(name)
        if match := popular.closest(corrected):
            return match
    if ecosystem != "npm":
        return None
    try:
        return await _search_npm(client, corrected)
    except Exception:
        log.warning("npm search failed for %s", name, exc_info=True)
        return None


async def _search_npm(client: httpx.AsyncClient, name: str) -> str | None:
    """npm's own search, for made-up names that aren't a simple typo: the most-downloaded close match."""
    text = _SEPARATORS.sub(" ", name).strip()
    response = await client.get("https://registry.npmjs.org/-/v1/search", params={"text": text, "size": 20})
    response.raise_for_status()
    best: tuple[str, int] | None = None
    for item in response.json().get("objects", []):
        candidate = item["package"]["name"]
        if candidate == name or SequenceMatcher(None, _key(candidate), _key(name)).ratio() < 0.7:
            continue
        weekly = (item.get("downloads") or {}).get("weekly", 0)
        if best is None or weekly > best[1]:
            best = (candidate, weekly)
    return best[0] if best else None
