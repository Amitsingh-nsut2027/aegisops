import json
import math
from typing import TypedDict


class CpuRecord(TypedDict):
    sample: int
    cpu_percent: float
    alert: bool


def validate_percentage(value: float, name: str) -> None:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not 0 <= value <= 100
        or not math.isfinite(value)
    ):
        raise ValueError(f"{name} must be a finite number between 0 and 100")


def detect_cpu_alerts(
    samples: list[float],
    threshold: float = 90,
    required_samples: int = 3,
) -> list[CpuRecord]:
    validate_percentage(threshold, "threshold")
    if type(required_samples) is not int or required_samples < 1:
        raise ValueError("required_samples must be a positive integer")

    consecutive_high = 0
    alert_active = False
    results: list[CpuRecord] = []

    for sample_number, cpu in enumerate(samples, start=1):
        validate_percentage(cpu, f"sample {sample_number}")
        alert = False
        if cpu > threshold:
            consecutive_high += 1
            if consecutive_high >= required_samples and not alert_active:
                alert = True
                alert_active = True
        else:
            consecutive_high = 0
            alert_active = False

        results.append({
            "sample": sample_number,
            "cpu_percent": cpu,
            "alert": alert,
        })
    return results


if __name__ == "__main__":
    samples = [91, 92, 93, 94, 95, 90, 91, 92, 93]
    for record in detect_cpu_alerts(samples):
        print(json.dumps(record))
