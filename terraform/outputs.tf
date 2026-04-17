output "dynamodb_table" { value = aws_dynamodb_table.incidents.name }
output "sns_topic_arn" { value = aws_sns_topic.escalation.arn }
output "ecr_backend" { value = aws_ecr_repository.backend.repository_url }
output "ecr_frontend" { value = aws_ecr_repository.frontend.repository_url }
output "agent_role_arn" { value = aws_iam_role.agent.arn }
