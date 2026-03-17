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

    portMappings = [{
      containerPort = 8443
      protocol      = "tcp"
    }]

    environment = [
      { name = "TELEGRAM_BOT_TOKEN", value = var.telegram_bot_token },
      { name = "DYNAMODB_TABLE_PREFIX", value = var.table_prefix },
      { name = "AWS_REGION", value = var.aws_region },
      { name = "ACTIVE_TASK_LIMIT", value = "50" },
      { name = "DEDUP_WINDOW_SECONDS", value = "300" },
      { name = "RATE_LIMIT_PER_MINUTE", value = "10" },
    ]

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = var.log_group_name
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "bot"
      }
    }

    healthCheck = {
      command     = ["CMD-SHELL", "python -c \"import socket; s=socket.create_connection(('localhost',8443),timeout=3); s.close()\""]
      interval    = 30
      timeout     = 5
      retries     = 3
      startPeriod = 10
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
    subnets          = var.private_subnet_ids
    security_groups  = [var.ecs_security_group_id]
    assign_public_ip = false
  }

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  tags = { Name = "ppai-bot-service" }
}
