output "vpc_id" {
  description = "VPC ID of EV Fleet Copilot deployment"
  value       = aws_vpc.main.id
}

output "public_subnet_id" {
  description = "Subnet ID of public deployment subnet"
  value       = aws_subnet.public.id
}

output "security_group_id" {
  description = "Security Group ID securing copilot endpoints"
  value       = aws_security_group.evc_sg.id
}

output "ec2_public_ip" {
  description = "Public IP address of the provisioned EC2 host"
  value       = aws_instance.host.public_ip
}

output "web_ui_url" {
  description = "URL for Web UI"
  value       = "http://${aws_instance.host.public_ip}"
}

output "api_endpoint" {
  description = "URL for FastAPI Service"
  value       = "http://${aws_instance.host.public_ip}:8000/api/v1"
}

output "copilot_agent_endpoint" {
  description = "URL for Copilot Agent Service"
  value       = "http://${aws_instance.host.public_ip}:8001/chat"
}

output "grafana_dashboard_url" {
  description = "URL for Grafana Dashboards"
  value       = "http://${aws_instance.host.public_ip}:3001"
}
