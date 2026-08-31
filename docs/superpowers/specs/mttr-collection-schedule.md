# MTTR Collection Schedule

## Recommendation

Run `collect_mttr_samples.py --mode apply` on a **4-hour cron interval** to continuously expand the MTTR dataset.

## Why 4-hour interval

- 8 scenarios (5 BLOCKER types) = 8 new traces per run
- At 4-hour cadence: 6 runs/day × ~9 samples = ~54 fresh BLOCKER traces/day
- After 1 week: ~378 new traces → MTTR table has statistical significance (n≥30 per type)
- No credential dependency — purely synthetic trace generation

## Cron configuration example (documentation only — not deployed)

```crontab
# MTTR data collection — every 4 hours
0 */4 * * * cd /path/to/qcloud-skills && python3 scripts/collect_mttr_samples.py --mode apply >> audit-results/mttr-collection.log 2>&1
```

## Alternative: systemd timer (documentation only)

```ini
# /etc/systemd/system/mttr-collector.timer
[Timer]
OnCalendar=*-*-* /4:00

[Install]
WantedBy=timers.target
```

```ini
# /etc/systemd/system/mttr-collector.service
[Service]
Type=oneshot
WorkingDirectory=/path/to/qcloud-skills
ExecStart=/usr/bin/python3 scripts/collect_mttr_samples.py --mode apply
```

## Retention

Traces older than 90 days should be pruned from `audit-results/` to prevent unbounded growth:
```bash
find audit-results/ -name "gcl-trace-mttr-*.json" -mtime +90 -delete
```

## Monitoring

Track MTTR sample growth:
```bash
python3 scripts/aggregate_gcl_traces.py 2>&1 | grep "MTTR.*BLOCKER" -A 5
```

Ideal state: each BLOCKER type has n ≥ 30 samples before drawing conclusions from MTTR averages.
