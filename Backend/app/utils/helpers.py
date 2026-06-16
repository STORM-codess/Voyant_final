import uuid
from datetime import datetime, timezone

def generate_id() -> str:
    """Generate a unique ID"""
    return str(uuid.uuid4())

def current_time():
    """Get current UTC time"""
    return datetime.now(timezone.utc)

def paginate(query_result: list, page: int = 1, limit: int = 10) -> dict:
    """Simple pagination helper"""
    start = (page - 1) * limit
    end = start + limit
    items = query_result[start:end]
    return {
        "items": items,
        "total": len(query_result),
        "page": page,
        "limit": limit,
        "pages": (len(query_result) + limit - 1) // limit
    }