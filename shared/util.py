def deep_update(left, right):
    """
    Update a dictionary recursively in-place.
    """
    for key, value in right.items():
        if isinstance(value, dict) and value:
            returned = deep_update(left.get(key, {}), value)
            left[key] = returned
        else:
            left[key] = right[key]
    return left
