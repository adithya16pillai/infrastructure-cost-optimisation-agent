from __future__ import annotations

from enum import Enum


class CloudProvider(str, Enum):
    AWS = "aws"
    GCP = "gcp"


class ResourceType(str, Enum):
    COMPUTE = "compute"
    DISK = "disk"
    SNAPSHOT = "snapshot"


class FindingType(str, Enum):
    IDLE_COMPUTE = "idle_compute"
    UNATTACHED_DISK = "unattached_disk"
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
