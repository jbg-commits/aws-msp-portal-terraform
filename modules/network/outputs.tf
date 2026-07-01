output "vpc_id" {
  description = "ID of the VPC"
  value       = aws_vpc.main.id
}

output "public_subnet_a_id" {
  description = "ID of public subnet A"
  value       = aws_subnet.public_a.id
}

output "public_subnet_b_id" {
  description = "ID of public subnet B"
  value       = aws_subnet.public_b.id
}

output "private_app_subnet_a_id" {
  description = "ID of private app subnet A"
  value       = aws_subnet.private_app_a.id
}

output "private_app_subnet_b_id" {
  description = "ID of private app subnet B"
  value       = aws_subnet.private_app_b.id
}

output "private_db_subnet_a_id" {
  description = "ID of private DB subnet A"
  value       = aws_subnet.private_db_a.id
}

output "private_db_subnet_b_id" {
  description = "ID of private DB subnet B"
  value       = aws_subnet.private_db_b.id
}

output "nat_gateway_id" {
  description = "ID of the NAT Gateway"
  value       = aws_nat_gateway.main.id
}

output "alb_security_group_id" {
  description = "ID of the load balancer security group"
  value       = aws_security_group.alb.id
}

output "app_security_group_id" {
  description = "ID of the application security group"
  value       = aws_security_group.app.id
}

output "db_security_group_id" {
  description = "ID of the database security group"
  value       = aws_security_group.db.id
}
