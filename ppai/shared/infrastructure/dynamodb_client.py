from __future__ import annotations

from typing import Any

import boto3


def get_dynamodb_resource(region: str = "us-east-1") -> Any:
    return boto3.resource("dynamodb", region_name=region)


def table_name(prefix: str, name: str) -> str:
    return f"{prefix}-{name}"
