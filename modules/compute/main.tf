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
    # Install CodeDeploy agent
    yum install -y ruby wget
    cd /tmp
    wget https://aws-codedeploy-${var.aws_region}.s3.${var.aws_region}.amazonaws.com/latest/install
    chmod +x ./install
    ./install auto
    systemctl enable codedeploy-agent
    systemctl start codedeploy-agent

    # Bootstrap landing page (CodeDeploy deployments will overwrite this)
    mkdir -p /opt/msp-portal
    cat > /opt/msp-portal/index.html <<'HTML'
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1.0" />
      <title>MSP Portal</title>
      <style>
        body { font-family: sans-serif; background: #0f172a; color: #e2e8f0; display: flex; align-items: center; justify-content: center; min-height: 100vh; margin: 0; }
        .card { background: #1e293b; border-radius: 12px; padding: 48px 56px; text-align: center; max-width: 480px; box-shadow: 0 4px 24px rgba(0,0,0,0.4); }
        h1 { font-size: 2rem; margin: 0 0 8px; color: #38bdf8; }
        p { color: #94a3b8; margin: 0 0 24px; }
        .badge { display: inline-block; padding: 4px 12px; border-radius: 20px; font-size: 0.75rem; font-weight: 600; letter-spacing: 0.05em; text-transform: uppercase; }
        .green { background: #14532d; color: #86efac; }
      </style>
    </head>
    <body>
      <div class="card">
        <h1>MSP Portal</h1>
        <p>AWS three-tier architecture — VPC &bull; ALB &bull; EC2 &bull; RDS PostgreSQL</p>
        <span class="badge green">&#x2714; Healthy</span>
      </div>
    </body>
    </html>
    HTML
    cat <<'UNIT' > /etc/systemd/system/app.service
    [Unit]
    Description=MSP Portal app server
    After=network.target

    [Service]
    WorkingDirectory=/opt/msp-portal
    ExecStart=/usr/bin/python3 -m http.server ${var.app_port}
    Restart=always

    [Install]
    WantedBy=multi-user.target
    UNIT
    systemctl daemon-reload
    systemctl enable --now app.service
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
