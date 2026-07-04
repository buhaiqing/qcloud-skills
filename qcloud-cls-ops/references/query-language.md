# CLS Query Language

> CLS log search query language syntax.

## Basic Syntax

| Operator | Description | Example |
|----------|-------------|---------|
| AND | Logical AND | `level:ERROR AND msg:timeout` |
| OR | Logical OR | `level:ERROR OR level:WARN` |
| NOT | Logical NOT | `NOT level:DEBUG` |
| = | Exact match | `ip:192.168.1.1` |
| : | Field search | `status:200` |

## Full-Text Search

Search all fields:
```sql
timeout error
```

## Field-Specific Search

```sql
level:ERROR
status:[500 TO 599]
msg:"connection refused"
```

## Range Queries

```sql
status:[200 TO 299]
latency:[100 TO 500]
```

## Wildcards

```sql
msg:/conn.*refused/
ip:/192\.168\.\d+\.\d+/
```

## SQL Syntax

CLS supports SQL-like queries for advanced analysis:

```sql
SELECT status, count(*) as cnt GROUP BY status ORDER BY cnt DESC LIMIT 10
```

## See also
- [Core Concepts](core-concepts.md)
- [Integration](integration.md)
