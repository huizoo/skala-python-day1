# SKALA Python Day 1 종합실습

3개의 외부 API를 비동기로 수집하고, Pydantic으로 데이터를 검증한 뒤 CSV와 Parquet 형식으로 저장·비교하는 프로젝트입니다.

## 환경 설정

Python 3.11 이상과 `uv`가 필요합니다.

```bash
uv sync
```

프로젝트 루트의 `.env` 파일에 다음 환경 변수를 설정합니다.

```dotenv
OPEN_METEO_URL=...
COUNTRIES_URL=...
IP_API_URL=...
```

## 실행

```bash
uv run python pipeline.py
```

실행하면 API 응답을 수집·검증하고 다음 파일을 생성합니다.

- `output/collected_data.csv`
- `output/collected_data.parquet`

CSV와 Parquet의 읽기·쓰기 시간을 5회 반복 측정하여 평균, 표준편차, 최솟값을 출력합니다. 작업별 최대 메모리 증가량과 파일 크기도 함께 비교합니다.

## 검증

```bash
uv run pytest -q
uv run ruff check .
```

## 주요 파일

- `collector.py`: 비동기 API 요청
- `models.py`: Pydantic 검증 모델
- `transformer.py`: API 응답 변환
- `storage.py`: 저장, 재로딩, 성능 및 메모리 측정
- `pipeline.py`: 전체 처리 과정 실행
- `tests/`: 모델과 저장 기능 테스트
