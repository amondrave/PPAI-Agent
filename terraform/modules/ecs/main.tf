resource "aws_ecs_cluster" "main" {
  name = "ppai-cluster"

  setting {
    name  = "containerInsights"
    value = "disabled"
  }

  tags = { Name = "ppai-cluster" }
}

resource "aws_ecs_task_definition" "bot" {
  family                   = "ppai-bot-task"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "256"
  memory                   = "512"
  execution_role_arn       = var.task_execution_role_arn
  task_role_arn            = var.task_role_arn

  container_definitions = jsonencode([{
    name      = "ppai-bot"
    image     = var.image_uri
    essential = true

    environment = [
      { name = "TELEGRAM_BOT_TOKEN", value = var.telegram_bot_token },
      { name = "DYNAMODB_TABLE_PREFIX", value = var.table_prefix },
      { name = "AWS_REGION", value = var.aws_region },
      { name = "ACTIVE_TASK_LIMIT", value = "50" },
      { name = "DEDUP_WINDOW_SECONDS", value = "300" },
      { name = "RATE_LIMIT_PER_MINUTE", value = "10" },
      { name = "GOOGLE_CLIENT_ID", value = var.google_client_id },
      { name = "GOOGLE_CLIENT_SECRET", value = var.google_client_secret },
      { name = "FERNET_ENCRYPTION_KEY", value = var.fernet_encryption_key },
      { name = "ANTHROPIC_API_KEY", value = var.anthropic_api_key },
    ]

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = var.log_group_name
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "bot"
      }
    }

  }])
}

resource "aws_ecs_service" "bot" {
  name            = "ppai-bot-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.bot.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.subnet_ids
    security_groups  = [var.ecs_security_group_id]
    assign_public_ip = true
  }

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  tags = { Name = "ppai-bot-service" }
}
