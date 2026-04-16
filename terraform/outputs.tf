output "dynamodb_table_name" {
  value = aws_dynamodb_table.incidents.name
}

output "sns_topic_arn" {
  value = aws_sns_topic.escalation.arn
}

output "ecr_backend_url" {
  value = aws_ecr_repository.backend.repository_url
}

output "ecr_frontend_url" {
  value = aws_ecr_repository.frontend.repository_url
}

output "agent_role_arn" {
  value = aws_iam_role.agent_role.arn
}
