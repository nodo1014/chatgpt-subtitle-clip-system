# 🎬 미디어 자막 인덱스 시스템

`/mnt/qnap/media_eng/` 디렉토리의 미디어 파일과 자막을 인덱싱하여 빠른 검색과 비디오 재생을 제공하는 시스템입니다.

## 📊 현재 데이터베이스 현황

- **총 자막 엔트리**: 270,143개
- **언어 분포**: 영어 184,188개 (68.2%), 한글 85,955개 (31.8%)
- **인덱싱된 디렉토리**: Ani, Avengers, Disney, Drama, Movie, Show
- **데이터베이스 크기**: ~97MB
- **검색 성능**: FTS5 기반 < 1ms

## 🚀 주요 기능

### 1. 빠른 텍스트 검색
- **FTS5 Full Text Search** 엔진 사용
- 영어/한글 자막 동시 검색
- 언어별 필터링 지원
- 밀리초 단위 검색 속도

### 2. 비디오 플레이어 연동
- 검색 결과에서 바로 해당 시점 재생
- VLC, MPV, MPlayer 지원
- 정확한 타임코드 변환

### 3. 디렉토리 탐색
- 카테고리별 미디어 브라우징
- 파일별 자막 통계
- 직관적인 네비게이션

## 📁 파일 구조

```
/home/kang/docker/youtube/indexer/
├── working_subtitles.db      # SQLite 데이터베이스 (97MB)
├── working_indexer.py        # 메인 인덱서
├── search_interface.py       # 검색 인터페이스
├── video_player.py          # 비디오 플레이어
├── media_system.py          # 통합 시스템
├── requirements.txt         # 의존성 패키지
└── README.md               # 이 파일
```

## 🔧 설치 & 설정

### 1. 의존성 설치
```bash
cd /home/kang/docker/youtube/indexer
pip install -r requirements.txt
```

### 2. 비디오 플레이어 설치 (선택사항)
```bash
# VLC (권장)
sudo apt install vlc

# 또는 MPV
sudo apt install mpv

# 또는 MPlayer
sudo apt install mplayer
```

## 🎮 사용법

### 메인 시스템 실행
```bash
python3 media_system.py
```

### 개별 도구 실행

#### 1. 검색만 사용
```bash
python3 search_interface.py
```

#### 2. 비디오 플레이어
```bash
python3 video_player.py
```

#### 3. 재인덱싱
```bash
python3 working_indexer.py
```

## 🔍 검색 사용법

### 기본 검색
```
🔍 검색어를 입력하세요: Batman
🔍 검색어를 입력하세요: Hello world
```

### 언어별 검색
```
🔍 검색어를 입력하세요: en:Batman    # 영어만
🔍 검색어를 입력하세요: ko:안녕하세요   # 한글만
```

### 특수 명령어
- `quit` 또는 `exit`: 종료
- `en:검색어`: 영어 자막만 검색
- `ko:검색어`: 한글 자막만 검색

## 🎬 비디오 플레이어 사용법

### 검색 후 재생
```
🎮 명령어를 입력하세요: search Batman
🎮 명령어를 입력하세요: search en:Hello
🎮 명령어를 입력하세요: search ko:안녕
```

### 디렉토리 탐색
```
🎮 명령어를 입력하세요: browse
```

## 🗄️ 데이터베이스 구조

### `subtitles` 테이블
```sql
CREATE TABLE subtitles (
    id INTEGER PRIMARY KEY,
    media_file TEXT,        -- 비디오 파일 경로
    subtitle_file TEXT,     -- 자막 파일 경로  
    start_time TEXT,        -- 시작 시간 (SRT 형식)
    end_time TEXT,          -- 종료 시간 (SRT 형식)
    text TEXT,              -- 자막 텍스트
    language TEXT,          -- 언어 (en/ko)
    directory TEXT          -- 디렉토리 경로
);
```

### `subtitles_fts` FTS5 테이블
- 빠른 전문 검색을 위한 가상 테이블
- `text`, `media_file`, `language`, `directory` 인덱스

## 📈 성능 지표

### 검색 성능
- **FTS5 검색**: < 1ms
- **일반 LIKE 검색**: 2-6ms (2-6배 느림)
- **데이터베이스 크기**: 97MB (270k 레코드)

### 인덱싱 현황
| 디렉토리 | 파일 수 | 자막 수 | 평균 자막/파일 |
|---------|--------|--------|--------------|
| Drama | 902개 | 220,496개 | 244개 |
| Movie | 미집계 | 19,876개 | - |
| Disney | 11개 | 15,600개 | 1,418개 |
| Ani | 30개 | 12,151개 | 405개 |
| Show | 미집계 | 991개 | - |
| Avengers | 1개 | 820개 | 820개 |

## 🔄 재인덱싱

새로운 미디어 파일이 추가되었거나 데이터베이스를 다시 생성하려면:

```bash
python3 working_indexer.py
```

또는 메인 시스템에서:
```
🎯 기능을 선택하세요: 5    # 재인덱싱
```

## 🐛 문제 해결

### 1. 검색 결과가 없는 경우
- 검색어 철자 확인
- 언어 필터 확인 (`en:` 또는 `ko:` 접두사)
- 다른 키워드 시도

### 2. 비디오 재생이 안되는 경우
- 비디오 플레이어 설치 확인 (`vlc`, `mpv`, `mplayer`)
- 파일 경로 및 권한 확인
- 비디오 파일 존재 여부 확인

### 3. 데이터베이스 오류
- 디스크 공간 확인
- 데이터베이스 파일 권한 확인
- 재인덱싱 시도

## 📋 TODO / 개선 사항

- [ ] 웹 인터페이스 추가
- [ ] 자막 편집 기능
- [ ] 북마크/즐겨찾기 기능
- [ ] 자막 동기화 도구
- [ ] 다국어 자막 지원 확장
- [ ] 클러스터링 검색 결과

## 📞 지원

문제가 발생하거나 개선 사항이 있으면 이슈를 등록해주세요.

---

**마지막 업데이트**: 2025년 6월 10일  
**데이터베이스 버전**: v3 (FTS5 지원)  
**총 인덱싱된 자막**: 270,143개
