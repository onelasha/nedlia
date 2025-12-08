# Security Architecture

This document defines the security architecture, authentication flows, and security best practices for Nedlia.

## Security Principles

1. **Defense in Depth**: Multiple layers of security controls
2. **Least Privilege**: Minimal permissions required for each component
3. **Zero Trust**: Verify every request, trust nothing by default
4. **Secure by Default**: Security enabled out of the box
5. **Fail Secure**: On error, deny access

---

## Authentication

### Authentication Methods

| Client             | Method                  | Token Type        |
| ------------------ | ----------------------- | ----------------- |
| Portal (Web)       | Cognito Hosted UI       | JWT (ID + Access) |
| SDK                | API Key                 | Static key        |
| Plugin             | OAuth 2.0 + Device Flow | JWT               |
| Service-to-Service | IAM Roles               | STS credentials   |

### Cognito Configuration

```hcl
# nedlia-IaC/modules/cognito/main.tf
resource "aws_cognito_user_pool" "main" {
  name = "nedlia-${var.environment}"

  # Password policy
  password_policy {
    minimum_length    = 12
    require_lowercase = true
    require_uppercase = true
    require_numbers   = true
    require_symbols   = true
  }

  # MFA
  mfa_configuration = "OPTIONAL"
  software_token_mfa_configuration {
    enabled = true
  }

  # Account recovery
  account_recovery_setting {
    recovery_mechanism {
      name     = "verified_email"
      priority = 1
    }
  }

  # Email verification
  auto_verified_attributes = ["email"]

  # User attributes
  schema {
    name                = "organization_id"
    attribute_data_type = "String"
    mutable             = true
  }
}
```

### JWT Token Structure

```json
{
  "sub": "user-uuid",
  "email": "user@example.com",
  "cognito:groups": ["advertisers", "admin"],
  "custom:organization_id": "org-123",
  "iat": 1705312800,
  "exp": 1705316400,
  "iss": "https://cognito-idp.us-east-1.amazonaws.com/us-east-1_xxx"
}
```

### Token Validation

```python
# src/infrastructure/auth.py
from jose import jwt, JWTError
import httpx

class TokenValidator:
    def __init__(self, user_pool_id: str, region: str):
        self.issuer = f"https://cognito-idp.{region}.amazonaws.com/{user_pool_id}"
        self.jwks_url = f"{self.issuer}/.well-known/jwks.json"
        self._jwks = None

    async def validate(self, token: str) -> dict:
        if not self._jwks:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.jwks_url)
                self._jwks = response.json()

        try:
            payload = jwt.decode(
                token,
                self._jwks,
                algorithms=["RS256"],
                issuer=self.issuer,
                options={"verify_aud": False}  # Cognito doesn't set aud
            )
            return payload
        except JWTError as e:
            raise AuthenticationError(f"Invalid token: {e}")
```

---

## Authorization

### Role-Based Access Control (RBAC)

| Role               | Permissions                        |
| ------------------ | ---------------------------------- |
| `viewer`           | Read placements, videos, campaigns |
| `editor`           | Create/edit placements, videos     |
| `campaign_manager` | Manage campaigns, budgets          |
| `admin`            | Full access, user management       |
| `super_admin`      | Cross-organization access          |

### Permission Matrix

| Resource           | viewer | editor | campaign_manager | admin |
| ------------------ | ------ | ------ | ---------------- | ----- |
| Placements (read)  | ✅     | ✅     | ✅               | ✅    |
| Placements (write) | ❌     | ✅     | ✅               | ✅    |
| Campaigns (read)   | ✅     | ✅     | ✅               | ✅    |
| Campaigns (write)  | ❌     | ❌     | ✅               | ✅    |
| Users (manage)     | ❌     | ❌     | ❌               | ✅    |
| Billing            | ❌     | ❌     | ✅               | ✅    |

### Organization-Based Access

All resources are scoped to an organization:

```python
# src/application/authorization.py
class AuthorizationService:
    def can_access_placement(self, user: User, placement: Placement) -> bool:
        # Super admin can access all
        if user.is_super_admin:
            return True

        # Must be in same organization
        if user.organization_id != placement.organization_id:
            return False

        # Check role permissions
        return self.has_permission(user, "placements:read")

    def can_modify_placement(self, user: User, placement: Placement) -> bool:
        if not self.can_access_placement(user, placement):
            return False

        return self.has_permission(user, "placements:write")
```

### API Gateway Authorization

```python
# src/interface/middleware/auth.py
from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security),
    token_validator: TokenValidator = Depends(),
) -> User:
    token = credentials.credentials
    payload = await token_validator.validate(token)

    user = await user_repository.find_by_id(payload["sub"])
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user

def require_permission(permission: str):
    async def check_permission(user: User = Depends(get_current_user)):
        if not authorization_service.has_permission(user, permission):
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user
    return check_permission

# Usage
@router.post("/placements")
async def create_placement(
    request: CreatePlacementRequest,
    user: User = Depends(require_permission("placements:write")),
):
    # ...
```

---

## API Key Management

### Key Format

```
nedlia_<environment>_<random_32_chars>

Examples:
nedlia_live_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6
nedlia_test_x9y8z7w6v5u4t3s2r1q0p9o8n7m6l5k4
```

### Key Storage

API keys are stored hashed:

```python
import hashlib
import secrets

def generate_api_key() -> tuple[str, str]:
    """Returns (raw_key, hashed_key)"""
    raw_key = f"nedlia_live_{secrets.token_hex(16)}"
    hashed_key = hashlib.sha256(raw_key.encode()).hexdigest()
    return raw_key, hashed_key

def verify_api_key(raw_key: str, hashed_key: str) -> bool:
    return hashlib.sha256(raw_key.encode()).hexdigest() == hashed_key
```

### Key Rotation

```python
# API keys can be rotated without downtime
class ApiKeyService:
    def rotate_key(self, key_id: str) -> str:
        old_key = self.repository.find(key_id)

        # Generate new key
        new_raw, new_hash = generate_api_key()

        # Keep old key valid for 24 hours
        old_key.expires_at = datetime.utcnow() + timedelta(hours=24)
        self.repository.save(old_key)

        # Create new key
        new_key = ApiKey(
            id=str(uuid4()),
            organization_id=old_key.organization_id,
            hash=new_hash,
            created_at=datetime.utcnow(),
        )
        self.repository.save(new_key)

        return new_raw  # Return to user once, never stored
```

---

## Secrets Management

### AWS Secrets Manager

```python
# src/infrastructure/secrets.py
import boto3
import json

secrets_client = boto3.client('secretsmanager')

def get_secret(secret_name: str) -> dict:
    response = secrets_client.get_secret_value(SecretId=secret_name)
    return json.loads(response['SecretString'])

# Usage
db_credentials = get_secret("nedlia/production/database")
connection_string = f"postgresql://{db_credentials['username']}:{db_credentials['password']}@..."
```

### Secret Hierarchy

```
nedlia/
  production/
    database          # DB credentials
    api-keys/
      stripe          # Payment provider
      sendgrid        # Email service
    jwt-signing-key   # JWT private key
  staging/
    ...
  dev/
    ...
```

### Environment Variables (Non-Sensitive)

```bash
# .env.example
NODE_ENV=development
LOG_LEVEL=debug
AWS_REGION=us-east-1

# Never in .env - use Secrets Manager
# DATABASE_URL=...
# API_KEY=...
```

---

## Network Security

### VPC Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                           VPC                                    │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                    Public Subnets                            ││
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          ││
│  │  │   NAT GW    │  │   NAT GW    │  │   ALB       │          ││
│  │  │   (AZ-a)    │  │   (AZ-b)    │  │             │          ││
│  │  └─────────────┘  └─────────────┘  └─────────────┘          ││
│  └─────────────────────────────────────────────────────────────┘│
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                   Private Subnets                            ││
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          ││
│  │  │   Lambda    │  │   Lambda    │  │   Lambda    │          ││
│  │  │   (API)     │  │  (Workers)  │  │             │          ││
│  │  └─────────────┘  └─────────────┘  └─────────────┘          ││
│  └─────────────────────────────────────────────────────────────┘│
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                   Database Subnets                           ││
│  │  ┌─────────────┐  ┌─────────────┐                           ││
│  │  │   Aurora    │  │   Aurora    │                           ││
│  │  │  (Primary)  │  │  (Replica)  │                           ││
│  │  └─────────────┘  └─────────────┘                           ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

### Security Groups

```hcl
# Lambda security group
resource "aws_security_group" "lambda" {
  name        = "nedlia-lambda"
  description = "Security group for Lambda functions"
  vpc_id      = var.vpc_id

  # Outbound to Aurora
  egress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.aurora.id]
  }

  # Outbound to internet (via NAT)
  egress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# Aurora security group
resource "aws_security_group" "aurora" {
  name        = "nedlia-aurora"
  description = "Security group for Aurora"
  vpc_id      = var.vpc_id

  # Inbound from Lambda only
  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.lambda.id]
  }

  # No outbound
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = []
  }
}
```

---

## Data Protection

### Encryption at Rest

| Service         | Encryption        |
| --------------- | ----------------- |
| Aurora          | AWS KMS (AES-256) |
| S3              | SSE-S3 or SSE-KMS |
| SQS             | SSE-SQS           |
| Secrets Manager | AWS KMS           |

### Encryption in Transit

- All API traffic over HTTPS (TLS 1.2+)
- Database connections use SSL
- Internal service communication uses TLS

### PII Handling

```python
# Identify and protect PII fields
PII_FIELDS = {"email", "phone", "address", "ip_address"}

def mask_pii(data: dict) -> dict:
    """Mask PII for logging"""
    return {
        k: "***MASKED***" if k in PII_FIELDS else v
        for k, v in data.items()
    }

# Encrypt PII at rest
from cryptography.fernet import Fernet

class PIIEncryptor:
    def __init__(self, key: bytes):
        self.fernet = Fernet(key)

    def encrypt(self, value: str) -> str:
        return self.fernet.encrypt(value.encode()).decode()

    def decrypt(self, encrypted: str) -> str:
        return self.fernet.decrypt(encrypted.encode()).decode()
```

---

## Threat Model

### STRIDE Analysis

| Threat               | Category               | Mitigation                                   |
| -------------------- | ---------------------- | -------------------------------------------- |
| Stolen API key       | Spoofing               | Key rotation, rate limiting, IP allowlisting |
| JWT tampering        | Tampering              | RS256 signatures, short expiry               |
| Data exfiltration    | Information Disclosure | Encryption, access logging, DLP              |
| SQL injection        | Tampering              | Parameterized queries, ORM                   |
| DDoS                 | Denial of Service      | WAF, rate limiting, CloudFront               |
| Privilege escalation | Elevation of Privilege | RBAC, least privilege                        |

### Attack Surface

```
┌─────────────────────────────────────────────────────────────────┐
│                        Attack Surface                            │
├─────────────────────────────────────────────────────────────────┤
│  External                                                        │
│  ├── API Gateway (public endpoints)                             │
│  ├── CloudFront (static assets)                                 │
│  └── Cognito (authentication)                                   │
├─────────────────────────────────────────────────────────────────┤
│  Internal                                                        │
│  ├── Lambda functions                                           │
│  ├── Aurora database                                            │
│  ├── S3 buckets                                                 │
│  └── SQS queues                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Security Monitoring

### CloudTrail

All API calls logged to CloudTrail:

```hcl
resource "aws_cloudtrail" "main" {
  name                          = "nedlia-trail"
  s3_bucket_name                = aws_s3_bucket.cloudtrail.id
  include_global_service_events = true
  is_multi_region_trail         = true
  enable_log_file_validation    = true

  event_selector {
    read_write_type           = "All"
    include_management_events = true
  }
}
```

### Security Alerts

```yaml
# Security-related alerts
alerts:
  - name: Unauthorized Access Attempt
    condition: api.errors.401 > 100 in 5 minutes
    severity: high

  - name: Privilege Escalation Attempt
    condition: api.errors.403 > 50 in 5 minutes
    severity: high

  - name: Unusual API Key Usage
    condition: api_key.requests > 10x normal
    severity: medium

  - name: Failed Login Attempts
    condition: cognito.failed_logins > 10 for same IP
    severity: medium
```

### GuardDuty

Enable AWS GuardDuty for threat detection:

```hcl
resource "aws_guardduty_detector" "main" {
  enable = true

  datasources {
    s3_logs {
      enable = true
    }
  }
}
```

---

## Compliance

### SOC 2 Controls

| Control           | Implementation          |
| ----------------- | ----------------------- |
| Access Control    | Cognito + RBAC          |
| Encryption        | KMS + TLS               |
| Logging           | CloudTrail + CloudWatch |
| Incident Response | Runbooks + Alerts       |
| Change Management | Git + CI/CD             |

### GDPR Considerations

- **Data minimization**: Only collect necessary data
- **Right to erasure**: Implement data deletion API
- **Data portability**: Export user data in standard format
- **Consent**: Track consent for data processing

---

## Security Checklist

### Development

- [ ] No secrets in code or git history
- [ ] Dependencies scanned for vulnerabilities
- [ ] Input validation on all endpoints
- [ ] Output encoding to prevent XSS
- [ ] Parameterized queries (no SQL injection)

### Deployment

- [ ] HTTPS only (no HTTP)
- [ ] Security headers configured
- [ ] CORS properly configured
- [ ] Rate limiting enabled
- [ ] WAF rules active

### Operations

- [ ] CloudTrail enabled
- [ ] GuardDuty enabled
- [ ] Security alerts configured
- [ ] Incident response plan documented
- [ ] Regular security reviews

---

## Related Documentation

- [SECURITY.md](../SECURITY.md) – Vulnerability reporting
- [Observability](observability.md) – Security monitoring
- [API Standards](api-standards.md) – Authentication details
