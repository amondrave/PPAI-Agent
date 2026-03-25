import boto3
import pytest
from moto import mock_aws


@pytest.fixture()
def dynamodb_resource():
    with mock_aws():
        resource = boto3.resource("dynamodb", region_name="us-east-1")

        resource.create_table(
            TableName="ppai-tasks",
            KeySchema=[
                {"AttributeName": "userId", "KeyType": "HASH"},
                {"AttributeName": "taskId", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "userId", "AttributeType": "S"},
                {"AttributeName": "taskId", "AttributeType": "S"},
                {"AttributeName": "status", "AttributeType": "S"},
            ],
            GlobalSecondaryIndexes=[
                {
                    "IndexName": "userId-status-index",
                    "KeySchema": [
                        {"AttributeName": "userId", "KeyType": "HASH"},
                        {"AttributeName": "status", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                }
            ],
            BillingMode="PAY_PER_REQUEST",
        )

        resource.create_table(
            TableName="ppai-events",
            KeySchema=[
                {"AttributeName": "userId", "KeyType": "HASH"},
                {"AttributeName": "timestamp#eventId", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "userId", "AttributeType": "S"},
                {"AttributeName": "timestamp#eventId", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )

        resource.create_table(
            TableName="ppai-dedup",
            KeySchema=[
                {"AttributeName": "userId#exactTextHash", "KeyType": "HASH"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "userId#exactTextHash", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )

        # UOW-02: ExecutionCycle table
        resource.create_table(
            TableName="ppai-cycles",
            KeySchema=[
                {"AttributeName": "cycleId", "KeyType": "HASH"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "cycleId", "AttributeType": "S"},
                {"AttributeName": "userId", "AttributeType": "S"},
                {"AttributeName": "date", "AttributeType": "S"},
            ],
            GlobalSecondaryIndexes=[
                {
                    "IndexName": "userId-date-index",
                    "KeySchema": [
                        {"AttributeName": "userId", "KeyType": "HASH"},
                        {"AttributeName": "date", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                }
            ],
            BillingMode="PAY_PER_REQUEST",
        )

        # UOW-03: User nudge preferences table
        resource.create_table(
            TableName="ppai-preferences",
            KeySchema=[
                {"AttributeName": "userId", "KeyType": "HASH"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "userId", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )

        yield resource
