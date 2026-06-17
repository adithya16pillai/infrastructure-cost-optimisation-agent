from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Protocol, runtime_checkable

logger = logging.getLogger(__name__)

EC2_HOURLY_PRICE: dict[str, dict[str, float]] = {
    "us-east-1": {
        "t3.micro": 0.0104,
        "t3.small": 0.0208,
        "t3.medium": 0.0416,
        "m5.large": 0.096,
        "m5.xlarge": 0.192,
        "m5.2xlarge": 0.384,
        "c5.large": 0.085,
        "c5.xlarge": 0.17,
    }
}
EBS_GB_MONTH_PRICE: dict[str, float] = {
    "gp3": 0.08,
    "gp2": 0.10,
    "io2": 0.125,
    "standard": 0.05,
}
SNAPSHOT_GB_MONTH_PRICE = 0.05


class AwsClientError(Exception):
    pass


@runtime_checkable
class AwsClient(Protocol):
    region: str

    def list_ec2_instances(self) -> list[dict]: ...
    def get_ec2_cpu_utilization(self, instance_id: str, days: int = 14) -> list[float]: ...
    def list_ebs_volumes(self) -> list[dict]: ...
    def list_ebs_snapshots(self) -> list[dict]: ...
    def get_instance_hourly_cost(self, instance_type: str, region: str) -> float: ...


class _PriceTableMixin:
    def get_instance_hourly_cost(self, instance_type: str, region: str) -> float:
        region_table = EC2_HOURLY_PRICE.get(region)
        if region_table is None or instance_type not in region_table:
            logger.warning(
                "No EC2 price for instance_type=%s region=%s", instance_type, region
            )
            return 0.0
        return region_table[instance_type]


def _iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


class RealAwsClient(_PriceTableMixin):
    def __init__(self, region: str) -> None:
        self.region = region
        self._ec2 = None
        self._cw = None

    @property
    def ec2(self):
        if self._ec2 is None:
            import boto3

            self._ec2 = boto3.client("ec2", region_name=self.region)
        return self._ec2

    @property
    def cloudwatch(self):
        if self._cw is None:
            import boto3

            self._cw = boto3.client("cloudwatch", region_name=self.region)
        return self._cw

    def list_ec2_instances(self) -> list[dict]:
        from botocore.exceptions import ClientError

        instances: list[dict] = []
        try:
            for page in self.ec2.get_paginator("describe_instances").paginate():
                for reservation in page["Reservations"]:
                    for inst in reservation["Instances"]:
                        tags = {t["Key"]: t["Value"] for t in inst.get("Tags", [])}
                        instances.append(
                            {
                                "instance_id": inst["InstanceId"],
                                "instance_type": inst["InstanceType"],
                                "region": self.region,
                                "state": inst["State"]["Name"],
                                "launch_time": _iso(inst["LaunchTime"]),
                                "tags": tags,
                            }
                        )
        except ClientError as exc:
            logger.error("describe_instances failed: %s", exc)
            raise AwsClientError("describe_instances failed") from exc
        return instances

    def get_ec2_cpu_utilization(self, instance_id: str, days: int = 14) -> list[float]:
        from botocore.exceptions import ClientError

        end = datetime.now(timezone.utc)
        start = end - timedelta(days=days)
        try:
            resp = self.cloudwatch.get_metric_statistics(
                Namespace="AWS/EC2",
                MetricName="CPUUtilization",
                Dimensions=[{"Name": "InstanceId", "Value": instance_id}],
                StartTime=start,
                EndTime=end,
                Period=86400,
                Statistics=["Average"],
            )
        except ClientError as exc:
            logger.error("get_metric_statistics failed for %s: %s", instance_id, exc)
            raise AwsClientError("get_metric_statistics failed") from exc

        points = sorted(resp.get("Datapoints", []), key=lambda p: p["Timestamp"])
        return [round(p["Average"], 2) for p in points]

    def list_ebs_volumes(self) -> list[dict]:
        from botocore.exceptions import ClientError

        volumes: list[dict] = []
        try:
            for page in self.ec2.get_paginator("describe_volumes").paginate():
                for vol in page["Volumes"]:
                    attachments = vol.get("Attachments", [])
                    attached_id = attachments[0]["InstanceId"] if attachments else None
                    volumes.append(
                        {
                            "volume_id": vol["VolumeId"],
                            "size_gb": vol["Size"],
                            "volume_type": vol["VolumeType"],
                            "region": self.region,
                            "state": vol["State"],
                            "attached_instance_id": attached_id,
                            "create_time": _iso(vol["CreateTime"]),
                        }
                    )
        except ClientError as exc:
            logger.error("describe_volumes failed: %s", exc)
            raise AwsClientError("describe_volumes failed") from exc
        return volumes

    def list_ebs_snapshots(self) -> list[dict]:
        from botocore.exceptions import ClientError

        snapshots: list[dict] = []
        try:
            paginator = self.ec2.get_paginator("describe_snapshots")
            for page in paginator.paginate(OwnerIds=["self"]):
                for snap in page["Snapshots"]:
                    snapshots.append(
                        {
                            "snapshot_id": snap["SnapshotId"],
                            "volume_id": snap.get("VolumeId"),
                            "size_gb": snap["VolumeSize"],
                            "start_time": _iso(snap["StartTime"]),
                            "description": snap.get("Description", ""),
                        }
                    )
        except ClientError as exc:
            logger.error("describe_snapshots failed: %s", exc)
            raise AwsClientError("describe_snapshots failed") from exc
        return snapshots


class MockAwsClient(_PriceTableMixin):
    def __init__(self, region: str = "us-east-1") -> None:
        self.region = region

    def list_ec2_instances(self) -> list[dict]:
        from app.aws import mock_data

        return mock_data.ec2_instances(self.region)

    def get_ec2_cpu_utilization(self, instance_id: str, days: int = 14) -> list[float]:
        from app.aws import mock_data

        return mock_data.cpu_utilization(instance_id, days)

    def list_ebs_volumes(self) -> list[dict]:
        from app.aws import mock_data

        return mock_data.ebs_volumes(self.region)

    def list_ebs_snapshots(self) -> list[dict]:
        from app.aws import mock_data

        return mock_data.ebs_snapshots()


def build_client(*, mock: bool, region: str) -> AwsClient:
    return MockAwsClient(region) if mock else RealAwsClient(region)


def get_aws_client(settings) -> AwsClient:
    return build_client(mock=settings.mock_aws, region=settings.aws_region)
