resource "aws_apigatewayv2_api" "webhook" {
  name          = "ppai-webhook"
  protocol_type = "HTTP"

  tags = { Name = "ppai-webhook-api" }
}

resource "aws_apigatewayv2_vpc_link" "ecs" {
  name               = "ppai-ecs-link"
  subnet_ids         = var.private_subnet_ids
  security_group_ids = [var.ecs_security_group_id]

  tags = { Name = "ppai-ecs-vpc-link" }
}

resource "aws_apigatewayv2_integration" "ecs" {
  api_id             = aws_apigatewayv2_api.webhook.id
  integration_type   = "HTTP_PROXY"
  integration_uri    = "http://placeholder:8443/{proxy}"
  integration_method = "ANY"
  connection_type    = "VPC_LINK"
  connection_id      = aws_apigatewayv2_vpc_link.ecs.id
}

resource "aws_apigatewayv2_route" "webhook" {
  api_id    = aws_apigatewayv2_api.webhook.id
  route_key = "POST /webhook/{proxy+}"
  target    = "integrations/${aws_apigatewayv2_integration.ecs.id}"
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.webhook.id
  name        = "$default"
  auto_deploy = true

  access_log_settings {
    destination_arn = var.log_group_apigw_arn
    format = jsonencode({
      requestId      = "$context.requestId"
      ip             = "$context.identity.sourceIp"
      requestTime    = "$context.requestTime"
      httpMethod     = "$context.httpMethod"
      routeKey       = "$context.routeKey"
      status         = "$context.status"
      protocol       = "$context.protocol"
      responseLength = "$context.responseLength"
      integrationError = "$context.integrationErrorMessage"
    })
  }

  tags = { Name = "ppai-webhook-stage" }
}
