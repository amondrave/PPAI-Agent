output "webhook_url" {
  value = aws_apigatewayv2_api.webhook.api_endpoint
}

output "api_id" {
  value = aws_apigatewayv2_api.webhook.id
}
