output "vpc_id" {
  description = "ID of the VPC"
  value       = module.network.vpc_id
}

output "public_subnet_ids" {
  description = "IDs of the public subnets"
  value = [
    module.network.public_subnet_a_id,
    module.network.public_subnet_b_id,
  ]
}

output "private_app_subnet_ids" {
  description = "IDs of the private app subnets"
  value = [
    module.network.private_app_subnet_a_id,
    module.network.private_app_subnet_b_id,
  ]
}

output "private_db_subnet_ids" {
  description = "IDs of the private DB subnets"
  value = [
    module.network.private_db_subnet_a_id,
    module.network.private_db_subnet_b_id,
  ]
}

output "nat_gateway_id" {
  description = "ID of the NAT Gateway"
  value       = module.network.nat_gateway_id
}

output "alb_security_group_id" {
  description = "ID of the load balancer security group"
  value       = module.network.alb_security_group_id
}

output "app_security_group_id" {
  description = "ID of the application security group"
  value       = module.network.app_security_group_id
}

output "db_security_group_id" {
  description = "ID of the database security group"
  value       = module.network.db_security_group_id
}

output "alb_dns_name" {
  description = "Public DNS name of the ALB"
  value       = module.compute.alb_dns_name
}

output "target_group_arn" {
  description = "ARN of the app target group"
  value       = module.compute.target_group_arn
}

output "app_instance_id" {
  description = "ID of the app EC2 instance"
  value       = module.compute.instance_id
}

output "db_endpoint" {
  description = "Connection endpoint for the RDS instance"
  value       = module.database.db_endpoint
}

output "db_identifier" {
  description = "Identifier of the RDS instance"
  value       = module.database.db_identifier
}

output "db_subnet_group_name" {
  description = "Name of the DB subnet group"
  value       = module.database.db_subnet_group_name
}

output "codedeploy_app_name" {
  description = "Name of the CodeDeploy application"
  value       = module.deploy.codedeploy_app_name
}

output "deployment_group_name" {
  description = "Name of the CodeDeploy deployment group"
  value       = module.deploy.deployment_group_name
}

output "artifacts_bucket_name" {
  description = "S3 bucket to upload deployment bundles"
  value       = module.deploy.artifacts_bucket_name
}

output "scheduler_role_arn" {
  description = "IAM role ARN EventBridge Scheduler assumes to start/stop EC2 and RDS (null if scheduler disabled)"
  value       = try(module.scheduler[0].scheduler_role_arn, null)
}

output "codebuild_project_name" {
  description = "Name of the CodeBuild project"
  value       = module.build.codebuild_project_name
}
