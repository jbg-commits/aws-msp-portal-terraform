data "aws_caller_identity" "current" {}

data "aws_kms_alias" "ssm" {
  name = "alias/aws/ssm"
}

# ── App runtime DB credential (msp_app) ───────────────────────────────────────
# Fully Terraform-owned, decoupled from var.db_password/dbadmin -- this is a
# brand-new role/credential the app runtime connects as (NOBYPASSRLS), never
# the migrator/admin credential.

resource "random_password" "msp_app_db_password" {
  length  = 32
  special = false # avoid characters that need URL-encoding inside a DSN
}

resource "aws_ssm_parameter" "app_db_url" {
  name   = "/${var.project_name}/db-url"
  type   = "SecureString"
  key_id = data.aws_kms_alias.ssm.target_key_arn

  value = "postgresql+psycopg2://msp_app:${random_password.msp_app_db_password.result}@${var.db_endpoint}/${var.db_name}"

  tags = {
    Name = "${var.project_name}-app-db-url"
  }
}

# ── Migrator/admin DB credential (dbadmin) ────────────────────────────────────
# Terraform owns the parameter's existence and IAM grants only. The real
# dbadmin DSN is set once, out-of-band, via:
#   aws ssm put-parameter --name /${var.project_name}/db-admin-url --type SecureString --overwrite --value "postgresql+psycopg2://dbadmin:<password>@<endpoint>/<db_name>"
# so Terraform state and the live database password are never a single
# source of truth for the same secret.

resource "aws_ssm_parameter" "db_admin_url" {
  name   = "/${var.project_name}/db-admin-url"
  type   = "SecureString"
  key_id = data.aws_kms_alias.ssm.target_key_arn
  value  = "placeholder-set-via-aws-ssm-put-parameter"

  lifecycle {
    ignore_changes = [value]
  }

  tags = {
    Name = "${var.project_name}-db-admin-url"
  }
}

# ── Cookie Secure flag (config-driven, flip once HTTPS exists) ───────────────

resource "aws_ssm_parameter" "cookie_secure" {
  name  = "/${var.project_name}/cookie-secure"
  type  = "String"
  value = var.cookie_secure ? "true" : "false"

  tags = {
    Name = "${var.project_name}-cookie-secure"
  }
}

# ── IAM: let the instance role read these parameters ─────────────────────────

resource "aws_iam_role_policy" "app_ssm_read" {
  name = "${var.project_name}-app-ssm-read"
  role = var.ec2_role_name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "ReadAppConfigParameters"
        Effect = "Allow"
        Action = ["ssm:GetParameter"]
        Resource = [
          aws_ssm_parameter.app_db_url.arn,
          aws_ssm_parameter.db_admin_url.arn,
          aws_ssm_parameter.cookie_secure.arn,
        ]
      },
      {
        Sid      = "DecryptSecureStringParameters"
        Effect   = "Allow"
        Action   = ["kms:Decrypt"]
        Resource = [data.aws_kms_alias.ssm.target_key_arn]
      }
    ]
  })
}
