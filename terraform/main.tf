provider "aws" {
  region = var.aws_region
}

resource "aws_dynamodb_table" "incidents" {
  name         = "${var.project}-incidents"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "incidentId"
  attribute { name = "incidentId"; type = "S" }
  tags = { Project = var.project }
}

resource "aws_sns_topic" "escalation" {
  name = "${var.project}-escalation"
  tags = { Project = var.project }
}

resource "aws_sns_topic_subscription" "email" {
  count     = var.sns_email != "" ? 1 : 0
  topic_arn = aws_sns_topic.escalation.arn
  protocol  = "email"
  endpoint  = var.sns_email
}

resource "aws_ecr_repository" "backend" {
  name                 = "${var.project}-backend"
  image_tag_mutability = "MUTABLE"
  force_delete         = true
  tags                 = { Project = var.project }
}

resource "aws_ecr_repository" "frontend" {
  name                 = "${var.project}-frontend"
  image_tag_mutability = "MUTABLE"
  force_delete         = true
  tags                 = { Project = var.project }
}

data "aws_eks_cluster" "cluster" {
  name = var.eks_cluster_name
}

resource "aws_iam_role" "agent" {
  name = "${var.project}-bedrock-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Federated = data.aws_eks_cluster.cluster.identity[0].oidc[0].issuer }
      Action    = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = {
          "${replace(data.aws_eks_cluster.cluster.identity[0].oidc[0].issuer, "https://", "")}:sub" = "system:serviceaccount:supply-chain-agent:sc-agent-sa"
        }
      }
    }]
  })
}

resource "aws_iam_role_policy" "agent" {
  name = "${var.project}-policy"
  role = aws_iam_role.agent.id
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
