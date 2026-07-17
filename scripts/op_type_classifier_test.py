#!/usr/bin/env python3
"""Unit tests for op_type_classifier.py."""

import unittest

from op_type_classifier import classify_operation, classify_batch


CASES = [
    # read
    ("tccli cvm DescribeInstances", "read"),
    ("tccli cdb DescribeAccounts", "read"),
    ("tccli cos ListObjects", "read"),
    ("tccli vpc DescribeVpcs", "read"),
    ("tccli clb DescribeLoadBalancers", "read"),
    ("tccli redis DescribeInstances", "read"),
    ("tccli es DescribeInstances", "read"),
    ("tccli cvm DescribeInstanceInternetBandwidth", "read"),
    ("tccli cdb DescribeSlowQueries", "read"),
    ("tccli cdn DescribeDomains", "read"),
    ("tccli cvm DescribeInstances --Region ap-guangzhou", "read"),
    ("tccli cam GetPolicy", "read"),
    ("tccli tke DescribeClusters", "read"),
    ("tccli scf GetFunction", "read"),
    # delete
    ("tccli cdb DeleteAccounts", "delete"),
    ("tccli cos DeleteObject", "delete"),
    ("tccli vpc DeleteVpc", "delete"),
    ("tccli cvm TerminateInstances", "delete"),
    ("tccli clb DeleteLoadBalancer", "delete"),
    ("tccli redis DeleteInstance", "delete"),
    ("tccli es DeleteInstance", "delete"),
    ("tccli scf DeleteFunction", "delete"),
    ("tccli cbs DeleteDisks", "delete"),
    ("tccli cam DeletePolicy", "delete"),
    ("tccli cls DeleteLogset", "delete"),
    ("tccli ckafka DeleteTopic", "delete"),
    ("tccli cdn PurgePathCache", "delete"),
    ("tccli vpn DeleteVpnGw", "delete"),
    # write
    ("tccli cos PutObject", "write"),
    ("tccli cdb CreateAccounts", "write"),
    ("tccli cvm StopInstances", "write"),
    ("tccli cvm StartInstances", "write"),
    ("tccli cvm RebootInstances", "write"),
    ("tccli redis ModifyInstance", "write"),
    ("tccli clb RegisterTargets", "write"),
    ("tccli vpc CreateSubnet", "write"),
    ("tccli cbs ResizeDisk", "write"),
    ("tccli cam CreatePolicy", "write"),
    ("tccli cls CreateLogset", "write"),
    ("tccli tke AddClusterInstances", "write"),
    ("tccli scf UpdateFunction", "write"),
    ("tccli cdb ModifyAccountPrivileges", "write"),
    ("tccli vpc ModifyVpcAttribute", "write"),
    ("tccli cdn UpdateDomainConfig", "write"),
    # edge cases
    ("", "read"),  # empty → safe default
    ("tccli", "read"),  # just tccli → read
    ("tccli cvm", "read"),  # no action → read
    ("tccli cvm DescribeInstancesEx", "read"),  # DescribeEx ends with Ex
    ("tccli cvm Stop", "write"),  # Stop is a write keyword
    ("tccli cvm DescribeAndStop", "read"),  # Describe first → read
]


class TestClassifyOperation(unittest.TestCase):
    def test_read_cases(self):
        for cmd, expected in CASES:
            if expected == "read":
                self.assertEqual(classify_operation(cmd), expected, msg=f"{cmd!r}")

    def test_delete_cases(self):
        for cmd, expected in CASES:
            if expected == "delete":
                self.assertEqual(classify_operation(cmd), expected, msg=f"{cmd!r}")

    def test_write_cases(self):
        for cmd, expected in CASES:
            if expected == "write":
                self.assertEqual(classify_operation(cmd), expected, msg=f"{cmd!r}")

    def test_batch(self):
        cmds = [c for c, _ in CASES]
        results = classify_batch(cmds)
        expecteds = [e for _, e in CASES]
        self.assertEqual(results, expecteds)


if __name__ == "__main__":
    unittest.main(verbosity=2)
