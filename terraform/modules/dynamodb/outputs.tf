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

output "user_profiles_table_arn" {
  value = aws_dynamodb_table.user_profiles.arn
}

output "calendar_auth_table_arn" {
  value = aws_dynamodb_table.calendar_auth.arn
}

output "time_blocks_table_arn" {
  value = aws_dynamodb_table.time_blocks.arn
}
