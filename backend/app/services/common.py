"""Small helpers shared by the services."""

LIKE_ESCAPE = "\\"


def contains_pattern(search: str) -> str:
    """A LIKE pattern matching `search` anywhere, with `%` and `_` taken literally.

    Use with `column.ilike(contains_pattern(s), escape=LIKE_ESCAPE)`.
    """
    escaped = (
        search.replace(LIKE_ESCAPE, LIKE_ESCAPE * 2)
        .replace("%", LIKE_ESCAPE + "%")
        .replace("_", LIKE_ESCAPE + "_")
    )
    return f"%{escaped}%"
