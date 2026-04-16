provider "aws" {
  region = var.aws_region
}

# DynamoDB table for incident storage
resource "aws_dynamodb_table" "incidents" {
  name         = "${var.project_name}-incidents"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "incidentId"

  attribute {
    name = "incidentId"
    type = "S"
  }

  tags = {
    Project = var.project_name
  }
}

# SNS topic for escalation notifications
resource "aws_sns_topic" "escalation" {
  name = "${var.project_name}-escalation"
  tags = { Project = var.project_name }
}

resource "aws_sns_topic_subscription" "email" {
  count     = var.sns_email != "" ? 1 : 0
  topic_arn = aws_sns_topic.escalation.arn
  protocol  = "email"
  endpoint  = var.sns_email
}

# ECR repositories
resource "aws_ecr_repository" "backend" {
  name                 = "${var.project_name}-backend"
  image_tag_mutability = "MUTABLE"
  force_delete         = true
  tags                 = { Project = var.project_name }
}

resource "aws_ecr_repository" "frontend" {
  name                 = "${var.project_name}-frontend"
  image_tag_mutability = "MUTABLE"
  force_delete         = true
  tags                 = { Project = var.project_name }
}

# IAM role for EKS pods to access Bedrock + DynamoDB + SNS
data "aws_eks_cluster" "cluster" {
  name = var.eks_cluster_name
}

resource "aws_iam_role" "agent_role" {
  name = "${var.project_name}-bedrock-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Federated = data.aws_eks_cluster.cluster.identity[0].oidc[0].issuer
      }
      Action = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = {
          "${replace(data.aws_eks_cluster.cluster.identity[0].oidc[0].issuer, "https://", "")}:sub" = "system:serviceaccount:supply-chain-agent:supply-chain-agent-sa"
        }
      }
    }]
  })
}

resource "aws_iam_role_policy" "agent_policy" {
  name = "${var.project_name}-policy"
  role = aws_iam_role.agent_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["bedrock:InvokeModel"]
        Resource = ["arn:aws:bedrock:${var.aws_region}::foundation-model/anthropic.claude-*"]
      },
      {
        Effect   = "Allow"
        Action   = ["dynamodb:PutItem", "dynamodb:GetItem", "dynamodb:Scan"]
        Resource = [aws_dynamodb_table.incidents.arn]
      },
      {
        Effect   = "Allow"
        Action   = ["sns:Publish"]
        Resource = [aws_sns_topic.escalation.arn]
      }
    ]
  })
}
