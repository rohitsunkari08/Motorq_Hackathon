variable "aws_region" {
  type        = string
  description = "AWS region for deployment"
  default     = "us-east-1"
}

variable "environment" {
  type        = string
  description = "Environment identifier"
  default     = "prod"
}

variable "vpc_cidr" {
  type        = string
  description = "CIDR block for EV Copilot VPC"
  default     = "10.0.0.0/16"
}

variable "public_subnet_cidr" {
  type        = string
  description = "CIDR block for public subnet"
  default     = "10.0.1.0/24"
}

variable "instance_type" {
  type        = string
  description = "EC2 instance type for host node"
  default     = "t3.xlarge"
}

variable "root_volume_size_gb" {
  type        = number
  description = "Size of encrypted EBS gp3 root volume in GB"
  default     = 100
}

variable "allowed_ssh_cidr" {
  type        = list(string)
  description = "Allowed CIDR blocks for SSH management access"
  default     = ["0.0.0.0/0"]
}
