"""Repository references in project cards, shared by build.py and discover.py."""

from __future__ import annotations

import re

# Own repository in a card's 'source', used for releases when 'releases' is not set.
OWN_REPO = re.compile(r"^https://github\.com/(Asofwar/[A-Za-z0-9._-]+?)(?:\.git)?(?:[/#?]|$)", re.IGNORECASE)
# Any GitHub repository URL; a trailing .git is not part of the name.
ANY_REPO = re.compile(r"^https://github\.com/([^/]+/[^/#?]+?)(?:\.git)?(?:[/#?]|$)")


def releases_repo(p: dict) -> tuple[str | None, bool]:
    """Repository to read releases from and whether a 404 there is acceptable.

    'releases' as a string is used as is (404 fails the build); false turns releases off;
    null or a missing key falls back to the card's own GitHub 'source' (404 tolerated).
    """
    value = p.get("releases")
    if isinstance(value, str) and value:
        return value, False
    if value is False:
        return None, False
    source = p.get("source")
    if value is None and isinstance(source, str):
        m = OWN_REPO.match(source)
        if m:
            return m.group(1), True
    return None, False


def repo_of(url: object) -> str | None:
    """'owner/repo' in lower case from a GitHub URL, or None."""
    m = ANY_REPO.match(url) if isinstance(url, str) else None
    return m.group(1).lower() if m else None
