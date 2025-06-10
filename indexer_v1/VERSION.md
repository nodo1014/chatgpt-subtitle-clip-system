# 미디어 자막 인덱싱 시스템 v1.0

## 📋 버전 정보
- **버전**: v1.0 (Stable)
- **릴리즈 날짜**: 2025-06-10
- **상태**: 안정 버전 (백업용)

## 🎯 주요 기능
- ✅ 단일 테이블 구조 (`subtitles`)
- ✅ 영어/한글 자막 지원 (_ko.srt 패턴)
- ✅ SRT 파싱 및 텍스트 정제
- ✅ SQLite 데이터베이스 (97MB, 270k+ 레코드)
- ✅ 기본 LIKE 검색
- ✅ 전체 미디어 디렉토리 인덱싱

## 📊 성과
- **인덱싱된 자막**: 270,143개
- **언어 분포**: 영어 68%, 한국어 32%
- **처리된 디렉토리**: 7개 (Ani, Avengers, Disney, Drama, Movie, Show)
- **검색 성능**: LIKE 쿼리 기준 2-6ms

## 🔧 기술 스택
- Python 3.10+
- SQLite3
- pysrt (자막 파싱)
- pathlib (파일 처리)

## 📁 파일 구조
```
indexer_v1/
├── working_indexer.py      # 메인 인덱서
├── search_interface.py     # 검색 인터페이스
├── video_player.py         # 비디오 플레이어
├── media_system.py         # 통합 시스템
├── working_subtitles.db    # SQLite 데이터베이스
├── requirements.txt        # 의존성
├── README.md              # 사용법
├── database_comparison.md  # DB 비교 분석
└── db설계.md              # 설계 문서
```

## ⚠️ 알려진 제한사항
1. 타임코드가 문자열로 저장되어 시간 범위 검색 어려움
2. FTS(Full Text Search) 미구현으로 상대적으로 느린 검색
3. 메타데이터 및 태그 시스템 없음
4. 인덱싱 이력 추적 불가

## 🚀 v2로의 업그레이드 경로
v2에서는 다음 기능들이 추가될 예정:
- FTS5 검색 엔진
- 타임코드 밀리초 저장
- 메타데이터 테이블
- 인덱싱 이력 추적
- 향상된 통계 정보

---
**참고**: 이 버전은 안정성이 검증된 백업 버전입니다. 새로운 기능 개발은 v2에서 진행됩니다.
