# CI/CD Core Concepts

## Architecture

Tencent Cloud CI/CD ecosystem includes:

- **CODING DevOps**: Full DevOps platform providing code repository, CI/CD pipelines, artifact repository, and test management
- **Cloud Studio**: Cloud-based IDE for development workspaces (separate from CI/CD pipelines)
- **Custom CI/CD**: Build custom pipelines using Tencent Cloud APIs and SDKs

## Pipeline Stages

A typical CI/CD pipeline consists of:

1. **Source** — Code checkout from repository
2. **Build** — Compile, test, package application
3. **Deploy** — Push to target environment

## Resource Limits

| Resource | Typical Limit |
|----------|--------------|
| Max pipelines per account | 200 |
| Max concurrent builds | 10 |
| Build timeout | 120 minutes |
| Artifact retention | 90 days |

## Delegation

- K8s deploy → `qcloud-tke-ops`
- SCF deploy → `qcloud-scf-ops`
- Monitor pipeline metrics → `qcloud-monitor-ops`
- Cost tracking → `qcloud-finops-ops`

## Security Best Practices

1. **Credential Management**: Use environment variables for secrets, never hardcode
2. **Access Control**: Restrict pipeline modification permissions via CAM
3. **Code Scanning**: Integrate SAST/DAST tools in pipeline stages
4. **Audit Logging**: Enable operation logs for compliance
