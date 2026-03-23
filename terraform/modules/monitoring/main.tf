resource "aws_cloudwatch_log_group" "bot" {
  name              = "/ppai/bot"
  retention_in_days = 90

  tags = { Name = "ppai-bot-logs" }
}
