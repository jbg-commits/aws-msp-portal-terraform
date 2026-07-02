output "alb_dns_name" {
  description = "Public DNS name of the ALB"
  value       = aws_lb.app.dns_name
}

output "alb_arn" {
  description = "ARN of the ALB"
  value       = aws_lb.app.arn
}

output "target_group_arn" {
  description = "ARN of the app target group"
  value       = aws_lb_target_group.app.arn
}

output "target_group_name" {
  description = "Name of the app target group (used by CodeDeploy deployment group)"
  value       = aws_lb_target_group.app.name
}

output "instance_id" {
  description = "ID of the app EC2 instance"
  value       = aws_instance.app.id
}
