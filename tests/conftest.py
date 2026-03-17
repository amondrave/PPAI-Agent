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

        yield resource
