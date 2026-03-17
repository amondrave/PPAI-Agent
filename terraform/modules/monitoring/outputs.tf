output "log_group_bot_name" {
  value = aws_cloudwatch_log_group.bot.name
}

output "log_group_bot_arn" {
  value = aws_cloudwatch_log_group.bot.arn
}

output "log_group_apigw_arn" {
  value = aws_cloudwatch_log_group.apigw.arn
}
