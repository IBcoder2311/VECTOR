import hmac
import hashlib
import json
import time

from typing import Any
from urllib.parse import parse_qsl


def validate_max_init_data(
    init_data: str,
    bot_token: str,
    max_age_seconds: int = 3600,
) -> dict[str, Any] | None:

    try:
        pairs = parse_qsl(
            init_data,
            keep_blank_values=True,
            strict_parsing=True,
        )
    except ValueError:
        return None

    if not pairs:
        return None

    if len(pairs) != len({key for key, _ in pairs}):
        return None

    params = dict(pairs)

    received_hash = params.pop("hash", None)

    if not received_hash:
        return None

    try:
        auth_date = int(params["auth_date"])
    except (KeyError, ValueError):
        return None

    current_time = int(time.time())

    if current_time - auth_date > max_age_seconds:
        return None

    if auth_date > current_time + 30:
        return None

    data_check_string = "\n".join(
        f"{key}={value}"
        for key, value in sorted(params.items())
    )

    secret_key = hmac.new(
        key=b"WebAppData",
        msg=bot_token.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).digest()

    calculated_hash = hmac.new(
        key=secret_key,
        msg=data_check_string.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(calculated_hash, received_hash):
        return None

    try:
        user = json.loads(params["user"])
    except (KeyError, json.JSONDecodeError):
        return None

    if not isinstance(user, dict) or not isinstance(user.get("id"), int):
        return None

    params["user"] = user
    params["auth_date"] = auth_date

    return params