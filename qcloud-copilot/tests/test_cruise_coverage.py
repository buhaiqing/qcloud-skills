from copilot.integration.cruise import _build_resource_coverage, _inspected_from_report


def test_inspected_from_service_reports():
    report = {
        "service_reports": [
            {
                "service": "vm",
                "resources_count": 2,
                "findings": [
                    {"resource_id": "i-aaa", "message": "disk"},
                    {"resource_id": "i-bbb", "message": "expire"},
                ],
            }
        ],
        "all_findings": [],
    }
    assert _inspected_from_report(report) == ["i-aaa", "i-bbb"]


def test_build_resource_coverage_marks_analyzed_types():
    report = {
        "service_reports": [
            {"service": "vm", "resources_count": 4, "findings": [{}] * 3},
            {"service": "clb", "resources_count": 1, "findings": [{}]},
            {"service": "eip", "resources_count": 2, "findings": [{}] * 2},
            {"service": "rds_mysql", "resources_count": 2, "findings": [{}] * 2},
        ]
    }
    sniff = {
        "raw": {
            "vms": [{}] * 4,
            "lbs": [{}],
            "eips": [{}] * 2,
            "rds": [{}] * 2,
            "redis": [],
        }
    }
    coverage = _build_resource_coverage(report, sniff)
    by_svc = {r["service"]: r for r in coverage["analyzer_runs"]}
    assert by_svc["vm"]["analyzed_count"] == 4
    assert by_svc["clb"]["analyzed_count"] == 1
    assert by_svc["redis"]["status"] == "no_resources"
    assert coverage["total_analyzed_resources"] == 9
