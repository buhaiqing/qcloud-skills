# API Gateway Core Concepts

## Resource model

```
Service (service-xxx)
├── API (api-xxx)          # one path+method, frontend + backend config
├── Environment
│   ├── test
│   ├── prepub
│   └── release            # published versions of the service
├── UsagePlan (usagePlan-) # rate limit / quota
│   ├── SecretKey (ak-)    # API keys bound to the plan
│   └── Environment bind   # plan → service environment
├── IPStrategy             # access control by IP/CIDR
├── Plugin                 # auth, throttling, caching, CORS, etc.
└── SubDomain (custom)     # custom domain → service
```

## Key terms

- **Service**: the unit of API management; groups APIs and release environments.
- **API**: a single path+method with frontend (RequestConfig) and backend (ServiceConfig).
- **Environment**: `test` / `prepub` / `release`. Only `release` serves production traffic.
- **Usage Plan**: throttling + quota (`MaxRequestNum`, `MaxRequestNumPreSec`).
- **AuthType**: `NONE` / `APP` (secretId+key) / `OAUTH`.
- **SkipVerification**: `DeleteService` safety flag — keep `0` (ON) unless user explicitly accepts skipping.

## Lifecycle

CreateService → CreateApi → ReleaseService(test) → verify → ReleaseService(release) →
BindUsagePlan → BindSubDomain. Decommission: UnReleaseService → DeleteApi → DeleteService.
