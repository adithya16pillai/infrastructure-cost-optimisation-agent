from __future__ import annotations

from enum import Enum


class ResourceType(str, Enum):
    EC2 = "ec2"
    EBS = "ebs"
    SNAPSHOT = "snapshot"


class FindingType(str, Enum):
    IDLE_EC2 = "idle_ec2"
    UNATTACHED_EBS = "unattached_ebs"
    OLD_SNAPSHOT = "old_snapshot"


class ValidationStatus(str, Enum):
    PENDING = "pending"
    APPROVE = "approve"
    NEEDS_REVIEW = "needs_review"
    REJECT = "reject"


class RunStatus(str, Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
