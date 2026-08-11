def resolve_client_id(request, data: dict | None = None) -> str | None:
    """
    Resolve the local app install identifier from body fields or headers.
    """
    data = data or {}

    for key in ('user_id', 'device_id', 'client_id'):
        value = data.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text

    if request is None:
        return None

    for header in ('X-User-Id', 'X-Device-Id', 'Device-Id'):
        text = (request.headers.get(header) or '').strip()
        if text:
            return text

    return None
