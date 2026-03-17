resource "aws_cloudwatch_log_group" "bot" {
  name              = "/ppai/bot"
  retention_in_days = 90

  tags = { Name = "ppai-bot-logs" }
}

resource "aws_cloudwatch_log_group" "apigw" {
  name              = "/ppai/apigw"
  retention_in_days = 90

  tags = { Name = "ppai-apigw-logs" }
}
