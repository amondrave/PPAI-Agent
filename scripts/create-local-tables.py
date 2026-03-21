#!/usr/bin/env python3
"""Create DynamoDB tables in LocalStack for local development.

Run via docker-compose (automatic) or manually:
    AWS_ACCESS_KEY_ID=test AWS_SECRET_ACCESS_KEY=test \
    DYNAMODB_ENDPOINT_URL=http://localhost:4566 \
    python scripts/create-local-tables.py
"""
import os
import sys

import boto3
from botocore.exceptions import ClientError

ENDPOINT = os.environ.get("DYNAMODB_ENDPOINT_URL", "http://localhost:4566")
REGION = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
PREFIX = os.environ.get("DYNAMODB_TABLE_PREFIX", "ppai")

client = boto3.client(
    "dynamodb",
    region_name=REGION,
    endpoint_url=ENDPOINT,
    aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID", "test"),
    aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY", "test"),
)

TABLES = [
    # UOW-01: ppai-tasks
    {
        "TableName": f"{PREFIX}-tasks",
        "KeySchema": [
            {"AttributeName": "userId", "KeyType": "HASH"},
            {"AttributeName": "taskId", "KeyType": "RANGE"},
        ],
        "AttributeDefinitions": [
            {"AttributeName": "userId", "AttributeType": "S"},
            {"AttributeName": "taskId", "AttributeType": "S"},
            {"AttributeName": "status", "AttributeType": "S"},
        ],
        "GlobalSecondaryIndexes": [
            {
                "IndexName": "userId-status-index",
                "KeySchema": [
                    {"AttributeName": "userId", "KeyType": "HASH"},
                    {"AttributeName": "status", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            }
        ],
        "BillingMode": "PAY_PER_REQUEST",
    },
    # UOW-01: ppai-events
    {
        "TableName": f"{PREFIX}-events",
        "KeySchema": [
            {"AttributeName": "userId", "KeyType": "HASH"},
            {"AttributeName": "timestamp#eventId", "KeyType": "RANGE"},
        ],
        "AttributeDefinitions": [
            {"AttributeName": "userId", "AttributeType": "S"},
            {"AttributeName": "timestamp#eventId", "AttributeType": "S"},
        ],
        "BillingMode": "PAY_PER_REQUEST",
    },
    # UOW-01: ppai-dedup
    {
        "TableName": f"{PREFIX}-dedup",
        "KeySchema": [
            {"AttributeName": "userId#exactTextHash", "KeyType": "HASH"},
        ],
        "AttributeDefinitions": [
            {"AttributeName": "userId#exactTextHash", "AttributeType": "S"},
        ],
        "BillingMode": "PAY_PER_REQUEST",
    },
    # UOW-02: ppai-cycles
    {
        "TableName": f"{PREFIX}-cycles",
        "KeySchema": [
            {"AttributeName": "cycleId", "KeyType": "HASH"},
        ],
        "AttributeDefinitions": [
            {"AttributeName": "cycleId", "AttributeType": "S"},
            {"AttributeName": "userId", "AttributeType": "S"},
            {"AttributeName": "date", "AttributeType": "S"},
        ],
        "GlobalSecondaryIndexes": [
            {
                "IndexName": "userId-date-index",
                "KeySchema": [
                    {"AttributeName": "userId", "KeyType": "HASH"},
                    {"AttributeName": "date", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            }
        ],
        "BillingMode": "PAY_PER_REQUEST",
    },
]


def create_table(definition: dict) -> None:
    name = definition["TableName"]
    try:
        client.create_table(**definition)
        print(f"  ✓ {name}")
    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceInUseException":
            print(f"  ~ {name} (ya existe)")
        else:
            print(f"  ✗ {name}: {e}", file=sys.stderr)
            raise


def main() -> None:
    print(f"Conectando a DynamoDB en {ENDPOINT}...")
    print(f"Creando tablas con prefijo '{PREFIX}':\n")
    for table_def in TABLES:
        create_table(table_def)
    print("\n✅ Tablas listas. LocalStack está lista para usar.")


if __name__ == "__main__":
    main()
