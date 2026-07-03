# Well-Architected Assessment — CI/CD

## Reliability

- **Pipeline retry strategy**: Configure auto-retry for transient failures
- **Multi-stage approval**: Require manual approval before production deploy
- **Artifact versioning**: Tag every build with unique version
- **Rollback capability**: Maintain ability to rollback to previous versions

## Security

- **Credential management**: Use environment variables (masked) for secrets
- **Code scanning**: Integrate SAST/DAST in pipeline
- **Access control**: Restrict pipeline modification permissions
- **Audit logging**: Enable comprehensive operation logging

## Cost

- **Build cache**: Enable dependency caching to reduce build time
- **Runner optimization**: Use appropriate compute resources
- **Artifact lifecycle**: Auto-delete old artifacts
- **Resource scheduling**: Schedule non-critical builds during off-peak

## Efficiency

- **Parallel stages**: Run independent tests concurrently
- **Pipeline templates**: Reuse standardized pipeline definitions
- **Caching**: Cache dependencies across builds
- **Incremental builds**: Build only changed components when possible

## Assessment Checklist

| Pillar | Check | Weight |
|--------|-------|--------|
| Reliability | Pipeline has automated rollback | High |
| Reliability | Critical deployments require approval | High |
| Security | Secrets are not in source code | Critical |
| Security | Pipeline has security scanning | High |
| Cost | Build cache is enabled | Medium |
| Cost | Unused artifacts are cleaned up | Medium |
| Efficiency | Parallel stage execution | Medium |
| Efficiency | Pipeline templates are used | Low |
