data "aws_ami" "amazon_linux" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-*-x86_64"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# ── IAM role for SSM access (no inbound SSH needed) ───────────────────────────

resource "aws_iam_role" "ec2_ssm" {
  name = "${var.project_name}-ec2-ssm-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "ec2.amazonaws.com"
      }
    }]
  })

  tags = {
    Name = "${var.project_name}-ec2-ssm-role"
  }
}

resource "aws_iam_role_policy_attachment" "ec2_ssm" {
  role       = aws_iam_role.ec2_ssm.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_role_policy_attachment" "ec2_codedeploy" {
  role       = aws_iam_role.ec2_ssm.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonEC2RoleforAWSCodeDeploy"
}

resource "aws_iam_instance_profile" "ec2_ssm" {
  name = "${var.project_name}-ec2-ssm-profile"
  role = aws_iam_role.ec2_ssm.name
}

# ── Target group ──────────────────────────────────────────────────────────────

resource "aws_lb_target_group" "app" {
  name     = "${var.project_name}-app-tg"
  port     = var.app_port
  protocol = "HTTP"
  vpc_id   = var.vpc_id

  deregistration_delay = 30

  health_check {
    path                = "/"
    protocol            = "HTTP"
    matcher             = "200"
    healthy_threshold   = 2
    unhealthy_threshold = 2
    interval            = 30
    timeout             = 5
  }

  tags = {
    Name = "${var.project_name}-app-tg"
  }
}

# ── Application Load Balancer ──────────────────────────────────────────────────

resource "aws_lb" "app" {
  name               = "${var.project_name}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [var.alb_security_group_id]
  subnets            = var.public_subnet_ids

  tags = {
    Name = "${var.project_name}-alb"
  }
}

resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.app.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.app.arn
  }
}

# ── EC2 app instance ────────────────────────────────────────────────────────────

resource "aws_instance" "app" {
  ami                    = data.aws_ami.amazon_linux.id
  instance_type          = var.instance_type
  subnet_id              = var.private_app_subnet_id
  vpc_security_group_ids = [var.app_security_group_id]
  iam_instance_profile   = aws_iam_instance_profile.ec2_ssm.name

  user_data = <<-EOF
    #!/bin/bash
    # Install CodeDeploy agent (retry: NAT route may not be ready in the first
    # seconds after boot, and chkconfig is required for systemctl enable on AL2023)
    for i in 1 2 3 4 5; do
      yum install -y ruby wget chkconfig python3-pip postgresql16 && break
      sleep 5
    done
    python3 -m venv /opt/msp-portal-venv
    cd /tmp
    for i in 1 2 3 4 5; do
      wget https://aws-codedeploy-${var.aws_region}.s3.${var.aws_region}.amazonaws.com/latest/install && break
      sleep 5
    done
    chmod +x ./install
    ./install auto
    systemctl enable codedeploy-agent
    systemctl start codedeploy-agent

    # Install and start the CloudWatch Agent (config fetched from SSM Parameter Store)
    mkdir -p /var/log/${var.project_name}
    for i in 1 2 3 4 5; do
      yum install -y amazon-cloudwatch-agent && break
      sleep 5
    done
    /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
      -a fetch-config -m ec2 -s -c ssm:/${var.project_name}/cwagent-config

    mkdir -p /opt/msp-portal
    cat <<'UNIT' > /etc/systemd/system/app.service
    [Unit]
    Description=MSP Portal app server
    After=network.target

    [Service]
    WorkingDirectory=/opt/msp-portal
    ExecStart=/opt/msp-portal-venv/bin/uvicorn app.main:app --host 0.0.0.0 --port ${var.app_port}
    Restart=always
    StandardOutput=append:/var/log/${var.project_name}/app.log
    StandardError=append:/var/log/${var.project_name}/app.log

    [Install]
    WantedBy=multi-user.target
    UNIT
    systemctl daemon-reload
    systemctl enable app.service
    # Not started here -- the venv has no app code/uvicorn yet on first boot.
    # CodeDeploy's ApplicationStart hook starts it after the first deployment.
  EOF

  tags = {
    Name      = "${var.project_name}-app-instance"
    DeployApp = var.project_name
  }
}

resource "aws_lb_target_group_attachment" "app" {
  target_group_arn = aws_lb_target_group.app.arn
  target_id        = aws_instance.app.id
  port             = var.app_port
}
