# 🎬 미디어 자막 인덱싱 시스템 - 프로젝트 개요

## 📁 프로젝트 구조

```
indexer/
├── indexer_v1/             # 🟢 안정 버전 (v1.0)
│   ├── working_indexer.py
│   ├── working_subtitles.db (97MB, 270k+ 레코드)
│   ├── VERSION.md
│   └── ... (완전한 기능 세트)
│
├── indexer_v2/             # 🟡 개발 버전 (v2.0)
│   ├── working_indexer.py (FTS5, 메타데이터 확장)
│   ├── working_subtitles_v2.db
│   ├── VERSION.md
│   └── ... (성능 향상 + 새 기능)
│
├── (기존 파일들)           # 🔴 레거시 (정리 필요)
├── README.md              # 전체 프로젝트 가이드
└── PROJECT_OVERVIEW.md    # 이 파일
```

## 🎯 버전별 사용 가이드

### 🟢 v1.0 - 안정 버전 (권장)
**사용 대상**: 안정적인 운영 환경
```bash
cd indexer/indexer_v1
python3 working_indexer.py
```

**특징**:
- ✅ 검증된 안정성
- ✅ 270k+ 자막 데이터
- ✅ 기본 LIKE 검색 (2-6ms)
- ✅ 완전한 기능 세트

### 🟡 v2.0 - 개발 버전 (실험)
**사용 대상**: 성능 테스트, 새 기능 체험
```bash
cd indexer/indexer_v2  
python3 working_indexer.py
```

**특징**:
- 🆕 FTS5 검색 (<1ms, 2-6배 빠름)
- 🆕 메타데이터 시스템
- 🆕 타임코드 밀리초 저장
- 🆕 향상된 통계
- ⚠️ 개발 중 (실험적)

## 📊 버전 비교

| 기능 | v1.0 | v2.0 |
|------|------|------|
| **안정성** | 🟢 검증됨 | 🟡 개발중 |
| **검색 성능** | 2-6ms | <1ms |
| **DB 구조** | 단일 테이블 | + 메타데이터 |
| **타임코드** | TEXT만 | TEXT + 밀리초 |
| **통계 정보** | 기본 | 상세 |
| **FTS 검색** | ❌ | ✅ |
| **호환성** | 기준 | v1과 별도 |

## 🚀 개발 로드맵

### ✅ 완료 (v1.0)
- 기본 SRT 파싱 및 인덱싱
- SQLite 데이터베이스 구축
- 영어/한글 자막 지원
- 기본 검색 기능
- 270k+ 레코드 안정적 처리

### 🔄 진행 중 (v2.0)
- FTS5 전문 검색 엔진
- 메타데이터 시스템
- 성능 최적화
- 타임코드 개선

### 📋 계획 (v3.0+)
- 정규화된 DB 구조
- 태그 시스템 (장르, 배우)
- 웹 인터페이스
- AI 기반 자동 태깅
- 실시간 검색 API

## 🎮 사용 시나리오

### 🔍 일반 검색 (v1 권장)
```bash
cd indexer/indexer_v1
python3 working_indexer.py
# 선택: 4 (통계 보기)
# 또는 search_interface.py 사용
```

### ⚡ 고성능 검색 테스트 (v2)
```bash
cd indexer/indexer_v2
python3 working_indexer.py
# 선택: 5 (검색 테스트 - FTS vs LIKE 비교)
```

### 🎬 비디오 재생 연동
```bash
cd indexer/indexer_v1  # 또는 v2
python3 video_player.py
# search <검색어>
```

### 📊 데이터 분석
```bash
# SQLite 직접 접근
sqlite3 indexer/indexer_v1/working_subtitles.db
sqlite3 indexer/indexer_v2/working_subtitles_v2.db
```

## 🔧 개발 가이드

### 새로운 기능 개발
1. **v2에서 실험**: `indexer/indexer_v2/`
2. **v1 백업 유지**: 안정성 보장
3. **검증 후 통합**: 충분한 테스트 후 v1 업데이트

### 버전 관리
- **v1**: 안정 버전, 수정 최소화
- **v2**: 활발한 개발, 실험적 기능
- **v3+**: 미래 계획, 설계 단계

## 📋 데이터베이스 현황

### v1 데이터베이스
- **파일**: `working_subtitles.db` (97MB)
- **레코드**: 270,143개 자막
- **언어**: 영어 68%, 한국어 32%
- **디렉토리**: 7개 (Ani, Avengers, Disney, Drama, Movie, Show)

### v2 데이터베이스  
- **파일**: `working_subtitles_v2.db` (신규)
- **구조**: v1 + 메타데이터 + FTS5
- **상태**: 개발 중

## 🎯 사용 권장사항

### 운영 환경
- **사용**: v1.0 (안정성 검증됨)
- **위치**: `indexer/indexer_v1/`
- **데이터**: 270k 레코드 완비

### 개발/테스트 환경
- **사용**: v2.0 (새 기능 체험)
- **위치**: `indexer/indexer_v2/`
- **목적**: 성능 비교, 새 기능 테스트

### 데이터 분석
- **v1**: 안정적인 대용량 데이터 분석
- **v2**: 새로운 검색 방식 실험

## 📞 문의 및 지원

- **설계 문서**: `db설계.md`
- **성능 분석**: `database_comparison.md`
- **버전별 상세**: 각 디렉토리의 `VERSION.md`

---

**현재 상태**: v1.0 안정 운영 중, v2.0 개발 진행 중  
**다음 마일스톤**: v2.0 성능 검증 완료 후 v3.0 설계 시작
