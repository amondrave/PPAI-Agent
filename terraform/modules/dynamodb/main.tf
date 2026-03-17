resource "aws_dynamodb_table" "tasks" {
  name         = "${var.table_prefix}-tasks"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "userId"
  range_key    = "taskId"

  attribute {
    name = "userId"
    type = "S"
  }

  attribute {
    name = "taskId"
    type = "S"
  }

  attribute {
    name = "status"
    type = "S"
  }

  global_secondary_index {
    name            = "userId-status-index"
    hash_key        = "userId"
    range_key       = "status"
    projection_type = "ALL"
  }

  deletion_protection_enabled = true

  tags = { Name = "${var.table_prefix}-tasks" }
}

resource "aws_dynamodb_table" "events" {
  name         = "${var.table_prefix}-events"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "userId"
  range_key    = "timestamp#eventId"

  attribute {
    name = "userId"
    type = "S"
  }

  attribute {
    name = "timestamp#eventId"
    type = "S"
  }

  deletion_protection_enabled = true

  tags = { Name = "${var.table_prefix}-events" }
}

resource "aws_dynamodb_table" "dedup" {
  name         = "${var.table_prefix}-dedup"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "userId#exactTextHash"

  attribute {
    name = "userId#exactTextHash"
    type = "S"
  }

  ttl {
    attribute_name = "expiresAt"
    enabled        = true
  }

  deletion_protection_enabled = true

  tags = { Name = "${var.table_prefix}-dedup" }
}
