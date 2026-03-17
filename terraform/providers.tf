terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.40"
    }
  }

  backend "s3" {
    bucket         = "ppai-terraform-state"
    key            = "ppai/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "ppai-terraform-lock"
    encrypt        = true
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "ppai"
      ManagedBy   = "terraform"
      Environment = "production"
    }
  }
}
