# SCF CLI Usage Reference

## Overview

The `tccli scf` command group provides CLI access to Tencent Serverless Cloud Function operations. This document maps CLI commands to SCF API methods and identifies coverage gaps.

## CLI Command Map

### Function Operations

| CLI Command | API Method | Description | Supports |
|-------------|------------|-------------|----------|
| `tccli scf CreateFunction` | CreateFunction | Deploy a new function | Code zip, runtime, memory, timeout |
| `tccli scf DeleteFunction` | DeleteFunction | Remove a function | Namespace support |
| `tccli scf GetFunction` | GetFunction | Get function details | Full configuration, code download |
| `tccli scf ListFunctions` | ListFunctions | List all functions | Pagination, namespace filter |
| `tccli scf UpdateFunctionConfiguration` | UpdateFunctionConfiguration | Update function config | Memory, timeout, env vars |
| `tccli scf UpdateFunctionCode` | UpdateFunctionCode | Update function code | Zip upload, COS bucket |
| `tccli scf Invoke` | Invoke | Invoke function synchronously | Event payload, log type |
| `tccli scf InvokeAsync` | InvokeAsync | Invoke function asynchronously | Event payload |

### Version and Alias Operations

| CLI Command | API Method | Description | Supports |
|-------------|------------|-------------|----------|
| `tccli scf PublishVersion` | PublishVersion | Create version from $LATEST | Version description |
| `tccli scf ListVersions` | ListVersionByFunction | List function versions | Pagination |
| `tccli scf DeleteVersion` | DeleteVersion | Delete specific version | Version number |
| `tccli scf CreateAlias` | CreateAlias | Create named alias | Alias name, version mapping |
| `tccli scf UpdateAlias` | UpdateAlias | Update alias configuration | Version change |
| `tccli scf DeleteAlias` | DeleteAlias | Delete alias | Namespace support |
| `tccli scf ListAliases` | ListAliases | List all aliases | Pagination |
| `tccli scf GetAlias` | GetAlias | Get alias details | Version routing config |

### Trigger Operations

| CLI Command | API Method | Description | Supports |
|-------------|------------|-------------|----------|
| `tccli scf CreateTrigger` | CreateTrigger | Create function trigger | Timer, COS, CMQ, Ckafka, API GW |
| `tccli scf DeleteTrigger` | DeleteTrigger | Remove trigger | Namespace support |
| `tccli scf ListTriggers` | ListTriggers | List function triggers | All trigger types |
| `tccli scf UpdateTriggerStatus` | UpdateTriggerStatus | Enable/disable trigger | OPEN/CLOSE |

### Layer Operations

| CLI Command | API Method | Description | Supports |
|-------------|------------|-------------|----------|
| `tccli scf CreateLayer` | CreateLayer | Create new layer | Layer name, description |
| `tccli scf DeleteLayer` | DeleteLayer | Delete layer | Layer name |
| `tccli scf ListLayers` | ListLayers | List all layers | Pagination |
| `tccli scf ListLayerVersions` | ListLayerVersions | List layer versions | Layer name |
| `tccli scf DeleteLayerVersion` | DeleteLayerVersion | Delete specific version | Layer name, version |
| `tccli scf GetLayerVersion` | GetLayerVersion | Get layer version details | Download URL |

### Concurrency and Provisioned Concurrency

| CLI Command | API Method | Description | Supports |
|-------------|------------|-------------|----------|
| `tccli scf PutReservedConcurrencyConfig` | PutReservedConcurrencyConfig | Set reserved concurrency | Namespace, qualifier |
| `tccli scf DeleteReservedConcurrencyConfig` | DeleteReservedConcurrencyConfig | Remove reserved concurrency | Namespace |
| `tccli scf GetReservedConcurrencyConfig` | GetReservedConcurrencyConfig | Get reserved concurrency | Current value |
| `tccli scf PutProvisionedConcurrencyConfig` | PutProvisionedConcurrencyConfig | Set provisioned concurrency | Version, count |
| `tccli scf DeleteProvisionedConcurrencyConfig` | DeleteProvisionedConcurrencyConfig | Remove provisioned concurrency | Version |
| `tccli scf GetProvisionedConcurrencyConfig` | GetProvisionedConcurrencyConfig | Get provisioned concurrency | Current allocation |

### Log and Monitoring Operations

| CLI Command | API Method | Description | Supports |
|-------------|------------|-------------|----------|
| `tccli scf GetFunctionLogs` | GetFunctionLogs | Query function logs | Time range, request ID |
| `tccli scf GetRequestStatus` | GetRequestStatus | Get request status | Async invoke status |

## Coverage Gap Analysis

CLI covers the majority of SCF API operations. Minor gaps:

| API Method | CLI Coverage | Gap Description |
|------------|--------------|-----------------|
| CreateFunction | ✓ Full | All params exposed |
| UpdateFunctionCode | ✓ Full | Zip and COS sources supported |
| CopyFunction | Partial | May need SDK for advanced options |
| TerminateAsyncEvent | Partial | Async event management |

## CLI Invocation Patterns

### Basic Usage

```bash
# List all functions in namespace
tccli scf ListFunctions --Namespace default --Limit 100

# Get function details
tccli scf GetFunction --FunctionName my-function --Namespace default

# Extract just the function status
tccli scf GetFunction --FunctionName my-function | jq -r '.Response.Status'
```

### JSON Output (Default)

CLI outputs JSON by default. Parse with jq:

```bash
# List functions with name and runtime
tccli scf ListFunctions --Namespace default | jq -r '.Response.Functions[] | "\(.FunctionName) \(.Runtime)"'

# Count total functions
tccli scf ListFunctions --Namespace default | jq '.Response.TotalCount'
```

### Help System

```bash
# List all SCF CLI actions
tccli scf help

# Get help for specific action
tccli scf help CreateFunction

# Get parameter help
tccli scf help CreateFunction --param Runtime
```

### Function Code Deployment

```bash
# Deploy from local zip
tccli scf UpdateFunctionCode \
  --FunctionName my-function \
  --Code.ZipFile /path/to/code.zip \
  --Handler index.handler

# Deploy from COS bucket
tccli scf UpdateFunctionCode \
  --FunctionName my-function \
  --Code.CosBucketName mybucket \
  --Code.CosObjectName /functions/code.zip \
  --Code.CosBucketRegion ap-guangzhou
```

### Batch Operations

```bash
# Delete multiple functions
for FUNC in "func1" "func2"; do
  echo "Deleting $FUNC..."
  tccli scf DeleteFunction --FunctionName "$FUNC" --Namespace default
done

# Update all functions to Python3.8
for FUNC in $(tccli scf ListFunctions | jq -r '.Response.Functions[].FunctionName'); do
  tccli scf UpdateFunctionConfiguration \
    --FunctionName "$FUNC" \
    --Runtime Python3.8
done
```

### Pagination Pattern

```bash
# Manual pagination loop for ListFunctions
OFFSET=0
LIMIT=20
while true; do
  DATA=$(tccli scf ListFunctions --Offset $OFFSET --Limit $LIMIT --Namespace default)
  ITEMS=$(echo "$DATA" | jq '.Response.Functions | length')
  echo "$DATA" | jq '.Response.Functions[]'
  [ "$ITEMS" -lt "$LIMIT" ] && break
  OFFSET=$((OFFSET + LIMIT))
done
```

### Error Handling Pattern

```bash
# Check for errors in response
RESPONSE=$(tccli scf GetFunction --FunctionName my-function 2>&1)
if echo "$RESPONSE" | jq -e '.Response.Error' > /dev/null 2>&1; then
  CODE=$(echo "$RESPONSE" | jq -r '.Response.Error.Code')
  MESSAGE=$(echo "$RESPONSE" | jq -r '.Response.Error.Message')
  echo "[ERROR] $CODE: $MESSAGE"
  exit 1
fi
```

## Common CLI Recipes

### Deploy and Test Function

```bash
#!/bin/bash
FUNCTION_NAME="my-function"
ZIP_FILE="function.zip"

# Update code
tccli scf UpdateFunctionCode \
  --FunctionName "$FUNCTION_NAME" \
  --Code.ZipFile "$ZIP_FILE" \
  --Handler index.handler

# Wait for Active status
for i in {1..30}; do
  STATUS=$(tccli scf GetFunction --FunctionName "$FUNCTION_NAME" | jq -r '.Response.Status')
  [ "$STATUS" = "Active" ] && break
  sleep 2
done

# Test invoke
RESULT=$(tccli scf Invoke --FunctionName "$FUNCTION_NAME" \
  --ClientContext '{"key":"value"}' \
  --LogType Tail)

# Check result
RETCODE=$(echo "$RESULT" | jq -r '.Response.Result.RetCode')
if [ "$RETCODE" = "0" ]; then
  echo "✅ Invoke successful"
  echo "$RESULT" | jq -r '.Response.Result.Log'
else
  echo "❌ Invoke failed: $RETCODE"
fi
```

### Create Version and Alias

```bash
FUNCTION_NAME="my-function"
VERSION_DESC="Production release v1.2.0"
ALIAS_NAME="prod"

# Publish version
echo "Publishing version..."
VERSION_RESULT=$(tccli scf PublishVersion \
  --FunctionName "$FUNCTION_NAME" \
  --Description "$VERSION_DESC")

VERSION=$(echo "$VERSION_RESULT" | jq -r '.Response.FunctionVersion')
echo "✅ Published version: $VERSION"

# Create or update alias
echo "Updating alias '$ALIAS_NAME' to version $VERSION..."
tccli scf UpdateAlias \
  --FunctionName "$FUNCTION_NAME" \
  --Name "$ALIAS_NAME" \
  --FunctionVersion "$VERSION" \
  --Namespace default

echo "✅ Alias updated"
```

### Setup Timer Trigger

```bash
FUNCTION_NAME="scheduled-task"
TRIGGER_NAME="daily-trigger"
CRON="0 0 2 * * *"  # 2:00 AM daily

tccli scf CreateTrigger \
  --FunctionName "$FUNCTION_NAME" \
  --TriggerName "$TRIGGER_NAME" \
  --Type timer \
  --TriggerDesc "{\"cron\": \"$CRON\"}" \
  --Enable OPEN

echo "✅ Timer trigger created: $CRON"
```

### Query Function Logs

```bash
FUNCTION_NAME="my-function"
START_TIME=$(date -v-1H -u +"%Y-%m-%dT%H:%M:%SZ")  # 1 hour ago
END_TIME=$(date -u +"%Y-%m-%dT%H:%M:%SZ")  # now

# Get recent logs
tccli scf GetFunctionLogs \
  --FunctionName "$FUNCTION_NAME" \
  --StartTime "$START_TIME" \
  --EndTime "$END_TIME" \
  --Limit 100 \
  --Order DESC | jq -r '.Response.Data[].Log'
```

### Check Function Health

```bash
FUNCTION_NAME="my-function"

# Get function status
STATUS=$(tccli scf GetFunction --FunctionName "$FUNCTION_NAME" | jq -r '.Response.Status')
if [ "$STATUS" != "Active" ]; then
  echo "⚠️ Function status: $STATUS"
  exit 1
fi

# Test invoke
RESULT=$(tccli scf Invoke --FunctionName "$FUNCTION_NAME" --LogType None)
RETCODE=$(echo "$RESULT" | jq -r '.Response.Result.RetCode')

if [ "$RETCODE" = "0" ]; then
  echo "✅ Function healthy"
else
  echo "❌ Function unhealthy: retCode=$RETCODE"
  exit 1
fi
```
