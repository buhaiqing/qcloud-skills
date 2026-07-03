# CLI Usage Guide

## Command Map

| Operation | CLI Command | SDK Method |
|-----------|------------|------------|
| Register Task | `tccli msp RegisterMigrationTask` | `RegisterMigrationTask` |
| List Tasks | `tccli msp ListMigrationTask` | `ListMigrationTask` |
| Describe Task | `tccli msp DescribeMigrationTask` | `DescribeMigrationTask` |
| Modify Task Status | `tccli msp ModifyMigrationTaskStatus` | `ModifyMigrationTaskStatus` |
| Deregister Task | `tccli msp DeregisterMigrationTask` | `DeregisterMigrationTask` |
| List Projects | `tccli msp ListMigrationProject` | `ListMigrationProject` |

## Common Patterns

```bash
# List all migration tasks
tccli msp ListMigrationTask --Region ap-guangzhou

# Get task details
tccli msp DescribeMigrationTask \
  --Region ap-guangzhou \
  --TaskId "task-xxx"

# List migration projects
tccli msp ListMigrationProject --Region ap-guangzhou
```

## Filtering Examples

```bash
# Filter by project
tccli msp ListMigrationTask \
  --Region ap-guangzhou \
  --ProjectId "project-xxx"
```
