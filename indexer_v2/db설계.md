# 미디어 자막 인덱싱 시스템 - 데이터베이스 설계

## 📋 현재 데이터베이스 구조 (v3)

### 1. 메인 테이블: `subtitles`

```sql
CREATE TABLE subtitles (
    id INTEGER PRIMARY KEY,
    media_file TEXT,
    subtitle_file TEXT,
    start_time TEXT,
    end_time TEXT,
    text TEXT,
    language TEXT,
    directory TEXT
);
```

#### 컬럼 설명
- **id**: 자동 증가 기본키
- **media_file**: 미디어 파일 전체 경로
- **subtitle_file**: 자막 파일 전체 경로
- **start_time**: SRT 시작 타임코드 (예: "00:01:23,456")
- **end_time**: SRT 종료 타임코드 (예: "00:01:25,789")
- **text**: 정제된 자막 텍스트
- **language**: 언어 코드 ("en" 또는 "ko")
- **directory**: 미디어가 포함된 디렉토리 경로

#### 현재 데이터 규모
- **총 레코드**: ~270,000개
- **파일 크기**: ~97MB
- **언어 분포**: 영어 68%, 한국어 32%

## 🎯 현재 설계의 장단점

### ✅ 장점
1. **단순성**: 하나의 테이블로 모든 정보 관리
2. **빠른 검색**: JOIN 없이 직접 검색 가능
3. **이해하기 쉬움**: 직관적인 구조
4. **중복 최소화**: 실제 중복되는 데이터가 적음

### ⚠️ 현재 한계점
1. **타임코드 검색**: 문자열로 저장되어 시간 범위 검색 어려움
2. **메타데이터 부족**: 미디어 파일 정보 (해상도, 코덱 등) 없음
3. **인덱싱 이력**: 언제, 어떤 파일이 처리되었는지 추적 어려움
4. **태그 시스템**: 장르, 카테고리 등 분류 기능 없음
5. **검색 성능**: FTS(Full Text Search) 미구현

## 🚀 개선 계획 v4

### 1. 정규화된 테이블 구조

```sql
-- 미디어 파일 기본 정보
CREATE TABLE media_files (
    id INTEGER PRIMARY KEY,
    file_path TEXT UNIQUE NOT NULL,
    file_name TEXT NOT NULL,
    file_size INTEGER,
    duration_seconds INTEGER,
    resolution TEXT,
    codec TEXT,
    directory_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (directory_id) REFERENCES directories(id)
);

-- 디렉토리 정보
CREATE TABLE directories (
    id INTEGER PRIMARY KEY,
    path TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    category TEXT,
    parent_id INTEGER,
    total_files INTEGER DEFAULT 0,
    indexed_at TIMESTAMP,
    FOREIGN KEY (parent_id) REFERENCES directories(id)
);

-- 자막 파일 정보
CREATE TABLE subtitle_files (
    id INTEGER PRIMARY KEY,
    media_file_id INTEGER NOT NULL,
    file_path TEXT NOT NULL,
    language TEXT NOT NULL,
    encoding TEXT DEFAULT 'utf-8',
    total_entries INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (media_file_id) REFERENCES media_files(id)
);

-- 자막 엔트리 (현재 subtitles 테이블과 유사)
CREATE TABLE subtitle_entries (
    id INTEGER PRIMARY KEY,
    subtitle_file_id INTEGER NOT NULL,
    sequence_number INTEGER NOT NULL,
    start_time_ms INTEGER NOT NULL,  -- 밀리초로 저장
    end_time_ms INTEGER NOT NULL,    -- 밀리초로 저장
    start_time_text TEXT NOT NULL,   -- 원본 SRT 형식
    end_time_text TEXT NOT NULL,     -- 원본 SRT 형식
    text TEXT NOT NULL,
    text_cleaned TEXT,               -- 정제된 텍스트
    character_count INTEGER,
    word_count INTEGER,
    FOREIGN KEY (subtitle_file_id) REFERENCES subtitle_files(id)
);

-- 태그 시스템
CREATE TABLE tags (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    category TEXT,  -- genre, actor, director, etc.
    description TEXT
);

-- 미디어-태그 관계
CREATE TABLE media_tags (
    media_file_id INTEGER,
    tag_id INTEGER,
    PRIMARY KEY (media_file_id, tag_id),
    FOREIGN KEY (media_file_id) REFERENCES media_files(id),
    FOREIGN KEY (tag_id) REFERENCES tags(id)
);

-- 인덱싱 이력
CREATE TABLE indexing_logs (
    id INTEGER PRIMARY KEY,
    operation_type TEXT NOT NULL,  -- 'full', 'incremental', 'single_dir'
    target_path TEXT,
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    files_processed INTEGER DEFAULT 0,
    errors_count INTEGER DEFAULT 0,
    status TEXT DEFAULT 'running',  -- 'running', 'completed', 'failed'
    error_message TEXT
);

-- FTS 가상 테이블 (검색 성능 향상)
CREATE VIRTUAL TABLE subtitle_search USING fts5(
    text,
    text_cleaned,
    language,
    media_file_name,
    directory_name,
    content='subtitle_entries',
    content_rowid='id'
);
```

### 2. 인덱스 설계

```sql
-- 성능 최적화를 위한 인덱스
CREATE INDEX idx_subtitle_entries_time ON subtitle_entries(start_time_ms, end_time_ms);
CREATE INDEX idx_subtitle_entries_language ON subtitle_entries(subtitle_file_id, language);
CREATE INDEX idx_media_files_directory ON media_files(directory_id);
CREATE INDEX idx_media_files_name ON media_files(file_name);
CREATE INDEX idx_subtitle_files_media ON subtitle_files(media_file_id, language);
CREATE INDEX idx_directories_category ON directories(category);
CREATE INDEX idx_indexing_logs_status ON indexing_logs(status, started_at);
```

## 🔄 마이그레이션 계획

### Phase 1: 백워드 호환성 유지
1. 현재 `subtitles` 테이블 유지
2. 새로운 테이블들 병렬 생성
3. 데이터 점진적 마이그레이션

### Phase 2: 데이터 이전
```sql
-- 기존 데이터를 새 구조로 이전하는 스크립트
INSERT INTO directories (path, name, category)
SELECT DISTINCT 
    directory,
    SUBSTR(directory, INSTR(directory, '/media_eng/') + 11),
    CASE 
        WHEN directory LIKE '%/Ani/%' THEN 'Animation'
        WHEN directory LIKE '%/Movie/%' THEN 'Movie'
        WHEN directory LIKE '%/Show/%' THEN 'TV Show'
        ELSE 'Other'
    END
FROM subtitles;
```

### Phase 3: 새 API 구현
- 기존 검색 API 유지하면서 새 API 점진적 도입
- 성능 비교 테스트
- 기존 기능 100% 호환성 확보

## 🎯 향후 기능 확장

### 1. 고급 검색 기능
```python
def advanced_search(
    query: str,
    language: str = None,
    time_range: tuple = None,  # (start_ms, end_ms)
    media_type: str = None,    # 'movie', 'tv', 'anime'
    tags: list = None,
    fuzzy_search: bool = False
):
    # 복합 조건 검색 구현
    pass
```

### 2. 시간 기반 검색
```python
def search_by_timerange(
    start_time: str,  # "00:05:00"
    end_time: str,    # "00:10:00"
    media_file: str = None
):
    # 특정 시간 구간의 자막 검색
    pass
```

### 3. 통계 및 분석
```python
def get_analytics():
    return {
        'most_common_words': [],
        'language_distribution': {},
        'average_subtitle_length': 0,
        'peak_dialogue_times': [],
        'character_frequency': {}
    }
```

### 4. 자동 태깅 시스템
```python
def auto_tag_media(file_path: str):
    # 파일명, 경로, 자막 내용 분석하여 자동 태그 생성
    # - 장르 추출 (액션, 로맨스, 코미디 등)
    # - 등장인물 이름 추출
    # - 주요 키워드 추출
    pass
```

## 📊 성능 최적화 전략

### 1. 캐싱 시스템
- Redis 또는 메모리 캐시 도입
- 자주 검색되는 쿼리 결과 캐싱
- 통계 정보 캐싱

### 2. 파티셔닝
```sql
-- 언어별 파티셔닝 (PostgreSQL 이전 시)
CREATE TABLE subtitle_entries_en PARTITION OF subtitle_entries
FOR VALUES IN ('en');

CREATE TABLE subtitle_entries_ko PARTITION OF subtitle_entries
FOR VALUES IN ('ko');
```

### 3. 백그라운드 처리
- 대용량 인덱싱 작업의 백그라운드 처리
- 진행상황 추적 및 중단/재시작 기능
- 오류 발생 시 자동 재시도

## 🔮 장기 로드맵

### v5: 분산 시스템
- 여러 스토리지 시스템 지원
- 클러스터 환경 지원
- API 서버 분리

### v6: AI 통합
- 자막 내용 기반 장면 분석
- 감정 분석 및 태깅
- 자동 요약 생성
- 대화 패턴 분석

### v7: 웹 인터페이스
- React/Vue.js 기반 웹 UI
- 실시간 검색 및 미리보기
- 북마크 및 플레이리스트 기능
- 사용자별 설정 관리

## 📝 구현 우선순위

### 높음 (v4)
1. ✅ FTS 검색 구현
2. ✅ 타임코드 밀리초 변환
3. ✅ 메타데이터 테이블 추가
4. ⭕ 인덱싱 이력 추적

### 중간 (v5)
1. ⭕ 정규화된 테이블 구조
2. ⭕ 태그 시스템
3. ⭕ 고급 검색 API
4. ⭕ 성능 최적화

### 낮음 (v6+)
1. ⭕ 웹 인터페이스
2. ⭕ AI 기능 통합
3. ⭕ 분산 시스템
4. ⭕ 실시간 동기화

## 🛡️ 데이터 무결성 보장

### 1. 제약 조건
```sql
-- 필수 데이터 검증
ALTER TABLE subtitle_entries 
ADD CONSTRAINT chk_time_valid 
CHECK (start_time_ms >= 0 AND end_time_ms > start_time_ms);

-- 언어 코드 검증
ALTER TABLE subtitle_entries 
ADD CONSTRAINT chk_language_valid 
CHECK (language IN ('en', 'ko', 'ja', 'zh', 'es', 'fr'));
```

### 2. 트리거
```sql
-- 자동 통계 업데이트
CREATE TRIGGER update_subtitle_file_stats
AFTER INSERT ON subtitle_entries
BEGIN
    UPDATE subtitle_files 
    SET total_entries = (
        SELECT COUNT(*) 
        FROM subtitle_entries 
        WHERE subtitle_file_id = NEW.subtitle_file_id
    )
    WHERE id = NEW.subtitle_file_id;
END;
```

### 3. 백업 전략
- 매일 자동 백업
- 증분 백업 지원
- 데이터 복구 절차 문서화

---

## 📋 변경 이력

| 버전 | 날짜 | 주요 변경사항 |
|------|------|---------------|
| v3 | 2025-06-10 | 현재 단일 테이블 구조 |
| v4 | TBD | FTS 검색, 메타데이터 추가 |
| v5 | TBD | 정규화된 구조, 태그 시스템 |

---

이 설계는 현재 시스템의 안정성을 유지하면서 점진적으로 발전시킬 수 있는 로드맵을 제공합니다.