# Deployment Architecture — UOW-01 Capture Foundation

## Architecture Diagram

```
                        INTERNET
                           |
                    +------v-------+
                    | Telegram API |
                    +------+-------+
                           |
                     HTTPS POST /webhook/{secret}
                           |
                    +------v--------------+
                    | API Gateway HTTP API |  <-- TLS auto, access logs
                    | (Regional, us-east-1)|
                    +------+--------------+
                           |
                      VPC Link
                           |
     VPC 10.0.0.0/16      |
     +---------------------v-----------------------+
     |                                              |
     |   Private Subnets                            |
     |   +------------------+  +------------------+ |
     |   | 10.0.10.0/24     |  | 10.0.11.0/24     | |
     |   | (AZ-a)           |  | (AZ-b)           | |
     |   |                  |  |                   | |
     |   | +-------------+  |  |                   | |
     |   | | ECS Fargate  |  |  |   (spare AZ for  | |
     |   | | ppai-bot     |  |  |    failover)     | |
     |   | | 0.25vCPU     |  |  |                   | |
     |   | | 512MB        |  |  |                   | |
     |   | | port 8443    |  |  |                   | |
     |   | +------+------+  |  |                   | |
     |   +--------+--------+  +------------------+ |
     |            |                                 |
     |            | DynamoDB API calls              |
     |            v                                 |
     |   +------------------+                       |
     |   | VPC Endpoint     |                       |
     |   | (DynamoDB GW)    |                       |
     |   +--------+---------+                       |
     |            |                                 |
     |   Public Subnets                             |
     |   +------------------+                       |
     |   | 10.0.1.0/24      |                       |
     |   | NAT Gateway      |-- outbound HTTPS ---> Telegram API
     |   +------------------+                       |
     |                                              |
     +----------------------------------------------+

                    +-------------------+
                    |    DynamoDB       |
                    | - ppai-tasks      |
                    | - ppai-events     |
                    | - ppai-dedup      |
                    +-------------------+

     +-------------------+    +-------------------+
     | CloudWatch Logs   |    |    Amazon ECR     |
     | - /ppai/bot       |    | - ppai-bot:v0.1.0 |
     | - /ppai/apigw     |    +-------------------+
     +-------------------+

     +-------------------+
     | S3 (TF State)     |
     | DynamoDB (TF Lock)|
     +-------------------+
```

### Text Alternative
1. Telegram API sends HTTPS POST to API Gateway HTTP API (regional, us-east-1)
2. API Gateway forwards via VPC Link to ECS Fargate task in private subnet
3. ECS task processes message, accesses DynamoDB via VPC Gateway Endpoint (no internet)
4. ECS task sends confirmation to Telegram API via NAT Gateway (outbound HTTPS)
5. Application logs flow to CloudWatch via awslogs driver
6. API Gateway access logs flow to separate CloudWatch log group
7. Docker images stored in ECR, pulled by ECS at task launch

---

## Deployment Pipeline

### Build + Push (GitHub Actions — automated)

```
Developer pushes to main branch
         |
         v
GitHub Actions Workflow triggers
         |
         v
1. Checkout code
2. Run tests (unit + integration with moto)
3. Build Docker image
4. Tag image: ppai-bot:v{version} + ppai-bot:sha-{commit}
5. Login to ECR (via OIDC role, no access keys)
6. Push image to ECR
7. Output: image URI for deployment
```

### Infrastructure Deploy (Manual — terraform apply)

```
Developer runs from local machine:
         |
         v
1. cd terraform/
2. terraform plan -var="image_tag=v0.1.0"
   - Review changes
3. terraform apply -var="image_tag=v0.1.0"
   - Apply infrastructure + deploy new image
4. ECS service detects new task definition
5. ECS performs rolling update (stop old task, start new)
6. Verify: check CloudWatch logs + send test message to bot
```

### First-Time Bootstrap

```
1. Create Terraform state backend (one-time):
   - S3 bucket + DynamoDB lock table
   - Can use a bootstrap script or separate Terraform config

2. terraform init (configure backend)

3. terraform apply (creates all infrastructure):
   - VPC + subnets + NAT + VPC endpoints
   - API Gateway + VPC Link
   - DynamoDB tables
   - ECR repository
   - ECS cluster + service + task definition
   - IAM roles + policies
   - CloudWatch log groups
   - Security groups

4. Register Telegram webhook:
   - POST to Telegram API: setWebhook(url=APIGW_URL/webhook/{secret})
   - Can be automated in app startup or as a one-time script

5. Deploy bot image:
   - Build + push to ECR
   - Update task definition with image URI
   - ECS starts the task
```

---

## Terraform Module Structure

```
terraform/
  main.tf                    # Root module, wires everything together
  variables.tf               # Input variables (region, image_tag, table_prefix, etc.)
  outputs.tf                 # Outputs (APIGW URL, ECR repo URI, etc.)
  providers.tf               # AWS provider config, backend config

  modules/
    networking/
      main.tf                # VPC, subnets, NAT, VPC endpoints, security groups
      variables.tf
      outputs.tf

    api-gateway/
      main.tf                # HTTP API, route, VPC Link, integration, access logs
      variables.tf
      outputs.tf

    ecs/
      main.tf                # Cluster, task definition, service, health check
      variables.tf
      outputs.tf

    dynamodb/
      main.tf                # 3 tables, GSIs, TTL config, deletion protection
      variables.tf
      outputs.tf

    iam/
      main.tf                # Task execution role, task role, policies
      variables.tf
      outputs.tf

    ecr/
      main.tf                # Repository, scanning, lifecycle policy
      variables.tf
      outputs.tf

    monitoring/
      main.tf                # CloudWatch log groups, retention policies
      variables.tf
      outputs.tf
```

### Module Dependencies

```
networking
    |
    +--> api-gateway (needs VPC, subnets, security groups)
    |
    +--> ecs (needs subnets, security groups, VPC endpoint)

iam --> ecs (task roles needed by task definition)

ecr --> ecs (repository URI needed by task definition)

monitoring --> ecs (log group needed by awslogs config)

dynamodb (independent, referenced by iam for resource ARNs)
```

---

## GitHub Actions Workflow (Build + Push)

```yaml
# .github/workflows/build-push.yml
name: Build and Push

on:
  push:
    branches: [main]
    paths:
      - 'src/**'
      - 'Dockerfile'
      - 'requirements.txt'

permissions:
  id-token: write   # OIDC for AWS
  contents: read

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Configure AWS credentials (OIDC)
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::<ACCOUNT_ID>:role/ppai-github-actions
          aws-region: us-east-1

      - name: Login to ECR
        uses: aws-actions/amazon-ecr-login@v2

      - name: Build, tag, push
        env:
          ECR_REGISTRY: <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com
          ECR_REPOSITORY: ppai-bot
          IMAGE_TAG: ${{ github.sha }}
        run: |
          docker build -t $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG .
          docker push $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG
```

**Note**: El workflow es ilustrativo. Los valores `<ACCOUNT_ID>` y el OIDC role se configuran al momento del deployment real.

---

## Webhook Registration

Al iniciar, la aplicación debe registrar el webhook con Telegram:

```
POST https://api.telegram.org/bot<TOKEN>/setWebhook
{
  "url": "https://<api-id>.execute-api.us-east-1.amazonaws.com/webhook/<secret-hash>",
  "allowed_updates": ["message"],
  "max_connections": 10
}
```

- Se ejecuta en el `main.py` al startup del bot
- Es idempotente (Telegram acepta re-registro sin error)
- `secret-hash` es un hash del bot token (no el token completo)
- `allowed_updates: ["message"]` limita a solo mensajes de texto (no edits, reactions, etc.)
