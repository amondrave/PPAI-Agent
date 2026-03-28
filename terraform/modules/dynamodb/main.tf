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

  ttl {
    attribute_name = "ttl"
    enabled        = true
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

# UOW-03: User nudge preferences table
resource "aws_dynamodb_table" "preferences" {
  name         = "${var.table_prefix}-preferences"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "userId"

  attribute {
    name = "userId"
    type = "S"
  }

  server_side_encryption {
    enabled = true
  }

  deletion_protection_enabled = true

  tags = { Name = "${var.table_prefix}-preferences", Unit = "uow-03" }
}

# UOW-02: ExecutionCycle table
resource "aws_dynamodb_table" "cycles" {
  name         = "${var.table_prefix}-cycles"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "cycleId"

  attribute {
    name = "cycleId"
    type = "S"
  }

  attribute {
    name = "userId"
    type = "S"
  }

  attribute {
    name = "date"
    type = "S"
  }

  global_secondary_index {
    name            = "userId-date-index"
    hash_key        = "userId"
    range_key       = "date"
    projection_type = "ALL"
  }

  server_side_encryption {
    enabled = true
  }

  deletion_protection_enabled = true

  tags = { Name = "${var.table_prefix}-cycles", Unit = "uow-02" }
}

# ER1: User profile table
resource "aws_dynamodb_table" "user_profiles" {
  name         = "${var.table_prefix}-user-profiles"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "userId"

  attribute {
    name = "userId"
    type = "S"
  }

  server_side_encryption {
    enabled = true
  }

  deletion_protection_enabled = true

  tags = { Name = "${var.table_prefix}-user-profiles", Unit = "er1" }
}

# ER2: Calendar OAuth tokens table
resource "aws_dynamodb_table" "calendar_auth" {
  name         = "${var.table_prefix}-calendar-auth"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "userId"

  attribute {
    name = "userId"
    type = "S"
  }

  server_side_encryption {
    enabled = true
  }

  deletion_protection_enabled = true

  tags = { Name = "${var.table_prefix}-calendar-auth", Unit = "er2" }
}

# ER2: Time blocks table
resource "aws_dynamodb_table" "time_blocks" {
  name         = "${var.table_prefix}-time-blocks"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "userId"
  range_key    = "date#blockId"

  attribute {
    name = "userId"
    type = "S"
  }

  attribute {
    name = "date#blockId"
    type = "S"
  }

  deletion_protection_enabled = true

  tags = { Name = "${var.table_prefix}-time-blocks", Unit = "er2" }
}
