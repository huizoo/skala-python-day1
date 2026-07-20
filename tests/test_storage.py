"""반복 성능 측정과 저장 용량 계산을 검증한다."""

from pathlib import Path

import pandas as pd
import pytest

from storage import benchmark_storage, measure_performance, storage_usage


def test_measure_performance_returns_statistics() -> None:
    """반복 측정 결과에 평균·표준편차·최솟값·메모리가 포함되는지 확인한다."""
    result, stats = measure_performance(lambda: sum(range(100)), repeats=3)

    assert result == 4950
    assert stats.average_seconds >= 0
    assert stats.standard_deviation_seconds >= 0
    assert stats.minimum_seconds >= 0
    assert stats.peak_memory_increase_mib >= 0


def test_measure_performance_rejects_small_repeat_count() -> None:
    """반복 횟수가 2보다 작으면 오류가 발생하는지 확인한다."""
    with pytest.raises(ValueError, match="반복 횟수"):
        measure_performance(lambda: None, repeats=1)


def test_storage_benchmark_and_sizes(tmp_path: Path) -> None:
    """두 파일 형식의 성능 통계와 저장 크기가 생성되는지 확인한다."""
    data_frame = pd.DataFrame(
        {
            "지역": ["서울", "부산", "광주"],
            "매출": [1000, 2000, 3000],
        }
    )
    csv_path = tmp_path / "sample.csv"
    parquet_path = tmp_path / "sample.parquet"
    data_frame.to_csv(csv_path, index=False, encoding="utf-8-sig")
    data_frame.to_parquet(parquet_path, index=False)

    benchmarks = benchmark_storage(
        data_frame,
        csv_path,
        parquet_path,
        repeats=2,
    )
    usage = storage_usage(data_frame, csv_path, parquet_path)

    assert set(benchmarks) == {
        "CSV 쓰기",
        "Parquet 쓰기",
        "CSV 읽기",
        "Parquet 읽기",
    }
    assert all(stats.average_seconds >= 0 for stats in benchmarks.values())
    assert usage["DataFrame 메모리"] > 0
    assert usage["CSV 파일 크기"] > 0
    assert usage["Parquet 파일 크기"] > 0
