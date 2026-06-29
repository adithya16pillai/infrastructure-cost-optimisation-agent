from __future__ import annotations

import logging

from app.models.enums import CloudProvider

logger = logging.getLogger(__name__)

# GCP Compute Engine on-demand pricing (USD/hour), us-central1 list prices.
GCE_HOURLY_PRICE: dict[str, dict[str, float]] = {
    "us-central1": {
        "e2-small": 0.01675,
        "e2-medium": 0.03351,
        "e2-standard-2": 0.06701,
        "e2-standard-4": 0.13402,
        "n2-standard-2": 0.09712,
        "n2-standard-4": 0.19424,
        "n2-standard-8": 0.38848,
    }
}
# Persistent Disk pricing (USD/GB/month).
PD_GB_MONTH_PRICE: dict[str, float] = {
    "pd-standard": 0.04,
    "pd-balanced": 0.10,
    "pd-ssd": 0.17,
}
# Persistent Disk snapshot storage (USD/GB/month).
SNAPSHOT_GB_MONTH_PRICE = 0.026


class _PriceTableMixin:
    def get_instance_hourly_cost(self, instance_type: str, region: str) -> float:
        region_table = GCE_HOURLY_PRICE.get(region)
        if region_table is None or instance_type not in region_table:
            logger.warning(
                "No GCE price for instance_type=%s region=%s", instance_type, region
            )
            return 0.0
        return region_table[instance_type]

    def get_disk_gb_month_cost(self, disk_type: str) -> float:
        return PD_GB_MONTH_PRICE.get(disk_type, 0.04)

    def get_snapshot_gb_month_cost(self) -> float:
        return SNAPSHOT_GB_MONTH_PRICE


class RealGcpClient(_PriceTableMixin):
    """Placeholder for a future google-cloud-compute / -monitoring integration.

    Each data method raises so a misconfigured deployment fails loudly instead
    of silently returning nothing. Run with mock mode until this is wired up.
    """

    provider = CloudProvider.GCP.value

    def __init__(self, region: str) -> None:
        self.region = region

    @staticmethod
    def _not_implemented():
        raise NotImplementedError(
            "Real GCP client not yet implemented; run with mock mode (MOCK_CLOUD=true)."
        )

    def list_compute_instances(self) -> list[dict]:
        self._not_implemented()

    def get_cpu_utilization(self, instance_id: str, days: int = 14) -> list[float]:
        self._not_implemented()

    def list_disks(self) -> list[dict]:
        self._not_implemented()

    def list_snapshots(self) -> list[dict]:
        self._not_implemented()


class MockGcpClient(_PriceTableMixin):
    provider = CloudProvider.GCP.value

    def __init__(self, region: str = "us-central1") -> None:
        self.region = region

    def list_compute_instances(self) -> list[dict]:
        from app.gcp import mock_data

        return mock_data.compute_instances(self.region)

    def get_cpu_utilization(self, instance_id: str, days: int = 14) -> list[float]:
        from app.gcp import mock_data

        return mock_data.cpu_utilization(instance_id, days)

    def list_disks(self) -> list[dict]:
        from app.gcp import mock_data

        return mock_data.disks(self.region)

    def list_snapshots(self) -> list[dict]:
        from app.gcp import mock_data

        return mock_data.snapshots()
