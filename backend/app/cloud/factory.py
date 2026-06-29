from __future__ import annotations

from app.cloud.base import CloudClient
from app.models.enums import CloudProvider


def build_client(*, provider: str, mock: bool, region: str) -> CloudClient:
    if provider == CloudProvider.AWS.value:
        from app.aws.client import MockAwsClient, RealAwsClient

        return MockAwsClient(region) if mock else RealAwsClient(region)
    if provider == CloudProvider.GCP.value:
        from app.gcp.client import MockGcpClient, RealGcpClient

        return MockGcpClient(region) if mock else RealGcpClient(region)
    raise ValueError(f"Unknown cloud provider: {provider!r}")


def get_client(settings) -> CloudClient:
    return build_client(
        provider=settings.cloud_provider,
        mock=settings.mock_cloud,
        region=settings.default_region_for(settings.cloud_provider),
    )
