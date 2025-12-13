from typing import List

INDIA_CITIES = ["Bengaluru", "Mumbai", "Pune", "Delhi", "Hyderabad", "Chennai"]


def generate_queries(keywords: List[str], india_mode: bool, max_queries: int, variants: int) -> List[str]:
    """Generate bounded list of query terms for search-driven sources."""
    if not keywords:
        return []
    base = keywords[: max_queries]  # top keywords
    queries: List[str] = []
    for kw in base:
        normalized = kw.strip()
        if not normalized:
            continue
        queries.append(normalized)
        if len(queries) >= max_queries:
            break
        if variants >= 2:
            queries.append(f"{normalized} engineer")
        if variants >= 3:
            queries.append(f"{normalized} developer")
    if india_mode:
        # add one city variant if room
        for city in INDIA_CITIES:
            if len(queries) >= max_queries:
                break
            queries.append(f"{keywords[0]} {city}")
    # ensure bounded
    unique_ordered = []
    seen = set()
    for q in queries:
        if q not in seen:
            unique_ordered.append(q)
            seen.add(q)
        if len(unique_ordered) >= max_queries:
            break
    return unique_ordered
