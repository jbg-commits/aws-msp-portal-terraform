data "aws_caller_identity" "current" {}

# ── IAM role CodeBuild assumes to build and trigger the deployment ───────────

resource "aws_iam_role" "codebuild" {
  name = "${var.project_name}-codebuild-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "codebuild.amazonaws.com"
      }
    }]
  })

  tags = {
    Name = "${var.project_name}-codebuild-role"
  }
}

resource "aws_iam_role_policy" "codebuild" {
  name = "${var.project_name}-codebuild-policy"
  role = aws_iam_role.codebuild.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "Logs"
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
        ]
        Resource = "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/codebuild/${var.project_name}-build*"
      },
      {
        Sid      = "ArtifactBucket"
        Effect   = "Allow"
        Action   = ["s3:PutObject", "s3:GetObject", "s3:GetBucketLocation"]
        Resource = ["${var.artifacts_bucket_arn}", "${var.artifacts_bucket_arn}/*"]
      },
      {
        Sid    = "TriggerCodeDeploy"
        Effect = "Allow"
        Action = [
          "codedeploy:CreateDeployment",
          "codedeploy:GetApplication",
          "codedeploy:GetDeploymentGroup",
          "codedeploy:RegisterApplicationRevision",
        ]
        Resource = [
          "arn:aws:codedeploy:${var.aws_region}:${data.aws_caller_identity.current.account_id}:application:${var.codedeploy_app_name}",
          "arn:aws:codedeploy:${var.aws_region}:${data.aws_caller_identity.current.account_id}:deploymentgroup:${var.codedeploy_app_name}/${var.codedeploy_deployment_group_name}",
        ]
      },
      {
        Sid      = "CodeDeployDefaultConfig"
        Effect   = "Allow"
        Action   = ["codedeploy:GetDeploymentConfig"]
        Resource = "arn:aws:codedeploy:${var.aws_region}:${data.aws_caller_identity.current.account_id}:deploymentconfig:*"
      }
    ]
  })
}

# ── CodeBuild project ──────────────────────────────────────────────────────────

resource "aws_codebuild_project" "app" {
  name         = "${var.project_name}-build"
  service_role = aws_iam_role.codebuild.arn

  artifacts {
    type = "NO_ARTIFACTS"
  }

  environment {
    type            = "LINUX_CONTAINER"
    compute_type    = var.compute_type
    image           = var.build_image
    privileged_mode = false

    environment_variable {
      name  = "ARTIFACTS_BUCKET"
      value = var.artifacts_bucket_name
    }

    environment_variable {
      name  = "CODEDEPLOY_APP"
      value = var.codedeploy_app_name
    }

    environment_variable {
      name  = "CODEDEPLOY_GROUP"
      value = var.codedeploy_deployment_group_name
    }
  }

  source {
    type      = "GITHUB"
    location  = var.github_repo_url
    buildspec = "buildspec.yml"
  }

  tags = {
    Name = "${var.project_name}-build"
  }
}

# ── Webhook: trigger a build on every push to the target branch ──────────────

resource "aws_codebuild_webhook" "app" {
  project_name = aws_codebuild_project.app.name
  build_type   = "BUILD"

  filter_group {
    filter {
      type    = "EVENT"
      pattern = "PUSH"
    }

    filter {
      type    = "HEAD_REF"
      pattern = "^refs/heads/${var.github_branch}$"
    }
  }
}
