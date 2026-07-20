"""CSV와 Parquet 파일의 저장, 재로딩 및 검증 기능을 제공한다."""

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from statistics import mean, pstdev
from time import perf_counter
from typing import Any, TypeVar

import pandas as pd
from memory_profiler import memory_usage

T = TypeVar("T")


@dataclass(frozen=True)
class PerformanceStats:
    """반복 실행 시간과 최대 메모리 증가량을 담는다."""

    average_seconds: float
    standard_deviation_seconds: float
    minimum_seconds: float
    peak_memory_increase_mib: float


def measure_performance(
    operation: Callable[[], T],
    repeats: int = 5,
) -> tuple[T, PerformanceStats]:
    """함수를 반복 측정하고 실행 시간 통계와 최대 메모리 증가량을 반환한다."""
    if repeats < 2:
        raise ValueError("반복 횟수는 2 이상이어야 합니다.")

    # 최초 실행 준비 비용이 평균에 섞이지 않도록 준비 실행
    operation()

    elapsed_times: list[float] = []
    result: T
    for _ in range(repeats):
        started = perf_counter()
        result = operation()
        elapsed_times.append(perf_counter() - started)

    samples, result = memory_usage(
        (operation, (), {}),
        interval=0.01,
        retval=True,
        max_usage=False,
    )
    peak_memory_increase = max(samples) - min(samples) if samples else 0.0

    return result, PerformanceStats(
        average_seconds=mean(elapsed_times),
        standard_deviation_seconds=pstdev(elapsed_times),
        minimum_seconds=min(elapsed_times),
        peak_memory_increase_mib=peak_memory_increase,
    )


def benchmark_storage(
    data_frame: pd.DataFrame,
    csv_path: Path,
    parquet_path: Path,
    repeats: int = 5,
) -> dict[str, PerformanceStats]:
    """CSV와 Parquet 읽기·쓰기를 같은 횟수로 반복 측정한다."""
    operations: dict[str, Callable[[], object]] = {
        "CSV 쓰기": lambda: data_frame.to_csv(
            csv_path,
            index=False,
            encoding="utf-8-sig",
        ),
        "Parquet 쓰기": lambda: data_frame.to_parquet(
            parquet_path,
            index=False,
        ),
        "CSV 읽기": lambda: pd.read_csv(csv_path),
        "Parquet 읽기": lambda: pd.read_parquet(parquet_path),
    }
    return {
        name: measure_performance(operation, repeats=repeats)[1]
        for name, operation in operations.items()
    }


def storage_usage(
    data_frame: pd.DataFrame,
    csv_path: Path,
    parquet_path: Path,
) -> dict[str, int]:
    """DataFrame 메모리와 CSV·Parquet 파일 크기를 바이트 단위로 반환한다."""
    return {
        "DataFrame 메모리": int(data_frame.memory_usage(deep=True).sum()),
        "CSV 파일 크기": csv_path.stat().st_size,
        "Parquet 파일 크기": parquet_path.stat().st_size,
    }


def save_records(
    records: list[dict[str, Any]],
    csv_path: Path,
    parquet_path: Path,
) -> tuple[pd.DataFrame, float, float]:
    """동일한 데이터를 CSV와 Parquet으로 저장하고 시간을 반환한다."""
    csv_path.parent.mkdir(parents=True, exist_ok=True)

    data_frame = pd.DataFrame(records)

    csv_start = perf_counter()
    data_frame.to_csv(
        csv_path,
        index=False,
        encoding="utf-8-sig",
    )
    csv_write_time = perf_counter() - csv_start

    parquet_start = perf_counter()
    data_frame.to_parquet(
        parquet_path,
        index=False,
    )
    parquet_write_time = perf_counter() - parquet_start

    return data_frame, csv_write_time, parquet_write_time


def reload_records(
    csv_path: Path,
    parquet_path: Path,
) -> tuple[pd.DataFrame, pd.DataFrame, float, float]:
    """CSV와 Parquet을 다시 읽고 각각의 읽기 시간을 반환한다."""
    csv_start = perf_counter()
    reloaded_csv = pd.read_csv(csv_path)
    csv_read_time = perf_counter() - csv_start

    parquet_start = perf_counter()
    reloaded_parquet = pd.read_parquet(parquet_path)
    parquet_read_time = perf_counter() - parquet_start

    return (
        reloaded_csv,
        reloaded_parquet,
        csv_read_time,
        parquet_read_time,
    )


def validate_reloaded(
    original: pd.DataFrame,
    reloaded_csv: pd.DataFrame,
    reloaded_parquet: pd.DataFrame,
    required_columns: set[str],
) -> None:
    """재로딩한 파일의 데이터 개수와 컬럼을 검증한다."""
    assert len(reloaded_csv) == len(original), "CSV의 데이터 개수가 다릅니다."
    assert len(reloaded_parquet) == len(original), "Parquet의 데이터 개수가 다릅니다."

    assert set(reloaded_csv.columns) == set(original.columns), (
        "CSV의 컬럼이 원본과 다릅니다."
    )
    assert set(reloaded_parquet.columns) == set(original.columns), (
        "Parquet의 컬럼이 원본과 다릅니다."
    )

    assert required_columns.issubset(reloaded_csv.columns), (
        "CSV에 필수 컬럼이 없습니다."
    )
    assert required_columns.issubset(reloaded_parquet.columns), (
        "Parquet에 필수 컬럼이 없습니다."
    )
