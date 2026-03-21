from __future__ import annotations

from typing import Any

import boto3


def get_dynamodb_resource(region: str = "us-east-1", endpoint_url: str | None = None) -> Any:
    kwargs: dict[str, Any] = {"region_name": region}
    if endpoint_url:
        # LocalStack or any DynamoDB-compatible local endpoint
        kwargs["endpoint_url"] = endpoint_url
    return boto3.resource("dynamodb", **kwargs)


def table_name(prefix: str, name: str) -> str:
    return f"{prefix}-{name}"
