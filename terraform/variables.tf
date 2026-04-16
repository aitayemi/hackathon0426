variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Project name for resource tagging"
  type        = string
  default     = "supply-chain-agent"
}

variable "eks_cluster_name" {
  description = "Name of the EKS cluster to deploy to"
  type        = string
}

variable "sns_email" {
  description = "Email for SNS escalation notifications"
  type        = string
  default     = ""
}
