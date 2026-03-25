output "tasks_table_arn" {
  value = aws_dynamodb_table.tasks.arn
}

output "events_table_arn" {
  value = aws_dynamodb_table.events.arn
}

output "dedup_table_arn" {
  value = aws_dynamodb_table.dedup.arn
}

output "cycles_table_arn" {
  value = aws_dynamodb_table.cycles.arn
}

output "preferences_table_arn" {
  value = aws_dynamodb_table.preferences.arn
}
