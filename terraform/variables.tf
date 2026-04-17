variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "project" {
  type    = string
  default = "supply-chain-agent"
}

variable "eks_cluster_name" {
  type = string
}

variable "sns_email" {
  type    = string
  default = ""
}
