def sort_clause(sort: str | None, allowed: dict[str, str], default: str) -> str:
    if not sort:
        return default
    direction = "desc" if sort.startswith("-") else "asc"
    column = allowed.get(sort.lstrip("-+"))
    if column is None:
        return default
    return f"{column} {direction}"


def paginate(page: int, page_size: int) -> tuple[int, int]:
    return page_size, (page - 1) * page_size
