from __future__ import annotations

from typing import Protocol, runtime_checkable


class CloudClientError(Exception):
    """Raised when a cloud provider API call fails."""


@runtime_checkable
class CloudClient(Protocol):
    """Provider-neutral interface implemented by the AWS and GCP clients.

    Every client returns the same normalized dict shapes so the detectors stay
    provider-agnostic:

    - compute instance:
        {instance_id, instance_type, region, state, launch_time, tags}
        ``state`` is normalized to "running" / "stopped".
    - disk:
        {disk_id, size_gb, disk_type, region, state, attached_instance_id,
         create_time}
        ``state`` is normalized to "available" (unattached) / "in-use".
    - snapshot:
        {snapshot_id, size_gb, start_time, description}
    """

    provider: str
    region: str

    def list_compute_instances(self) -> list[dict]: ...
    def get_cpu_utilization(self, instance_id: str, days: int = 14) -> list[float]: ...
    def list_disks(self) -> list[dict]: ...
    def list_snapshots(self) -> list[dict]: ...

    # Pricing lives behind the client so each provider keeps its own tables.
    def get_instance_hourly_cost(self, instance_type: str, region: str) -> float: ...
    def get_disk_gb_month_cost(self, disk_type: str) -> float: ...
    def get_snapshot_gb_month_cost(self) -> float: ...
