import re

def is_valid_email(email: str) -> bool:
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def is_valid_budget(budget_min: int, budget_max: int) -> bool:
    """Validate budget range"""
    if budget_min < 0 or budget_max < 0:
        return False
    if budget_min > budget_max:
        return False
    return True

def is_valid_group_size(size: int) -> bool:
    """Validate group size"""
    return 2 <= size <= 20