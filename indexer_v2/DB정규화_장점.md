# 🗄️ DB 정규화의 장점 - 자막 학습 DB 맥락에서

## 📊 현재 상황 vs 정규화 후 비교

### 🔴 현재 단일 테이블 구조 (비정규화)
```sql
-- 현재 subtitles 테이블
CREATE TABLE subtitles (
    id INTEGER PRIMARY KEY,
    media_file TEXT,              -- "/path/Friends.S01E01.mkv"
    subtitle_file TEXT,           -- "/path/Friends.S01E01.srt"  
    start_time TEXT,              -- "00:01:23,456"
    end_time TEXT,                -- "00:01:25,789"
    text TEXT,                    -- "How are you doing?"
    language TEXT,                -- "en"
    directory TEXT                -- "/path/Friends/Season1/"
);
```

### ✅ 정규화된 구조
```sql
-- 1. 쇼/시리즈 정보
CREATE TABLE shows (
    id INTEGER PRIMARY KEY,
    name TEXT,                    -- "Friends"
    genre TEXT,                   -- "Comedy, Drama"
    year_start INTEGER,           -- 1994
    year_end INTEGER,             -- 2004
    difficulty_level TEXT         -- "Intermediate"
);

-- 2. 시즌 정보  
CREATE TABLE seasons (
    id INTEGER PRIMARY KEY,
    show_id INTEGER,              -- shows.id 참조
    season_number INTEGER,        -- 1, 2, 3...
    episode_count INTEGER,        -- 24
    FOREIGN KEY (show_id) REFERENCES shows(id)
);

-- 3. 에피소드 정보
CREATE TABLE episodes (
    id INTEGER PRIMARY KEY,
    season_id INTEGER,            -- seasons.id 참조
    episode_number INTEGER,       -- 1, 2, 3...
    title TEXT,                   -- "The One Where Monica Gets a Roommate"
    duration_seconds INTEGER,     -- 1320 (22분)
    air_date DATE,               -- "1994-09-22"
    FOREIGN KEY (season_id) REFERENCES seasons(id)
);

-- 4. 자막 엔트리 (정규화됨)
CREATE TABLE subtitle_entries (
    id INTEGER PRIMARY KEY,
    episode_id INTEGER,           -- episodes.id 참조
    start_time_ms INTEGER,        -- 83456 (밀리초)
    end_time_ms INTEGER,          -- 85789
    text TEXT,                    -- "How are you doing?"
    language TEXT,                -- "en"
    speaker TEXT,                 -- "Joey" (화자 정보)
    emotion TEXT,                 -- "friendly" (감정)
    FOREIGN KEY (episode_id) REFERENCES episodes(id)
);

-- 5. 표현/구문 정보 (NEW!)
CREATE TABLE expressions (
    id INTEGER PRIMARY KEY,
    text TEXT,                    -- "How are you doing"
    normalized_text TEXT,         -- "how are you doing" (소문자)
    word_count INTEGER,           -- 4
    difficulty_level INTEGER,     -- 1-5
    category TEXT,                -- "greeting", "business", "emotion"
    frequency_rank INTEGER        -- 전체 빈도 순위
);

-- 6. 표현-자막 연결 (NEW!)
CREATE TABLE expression_occurrences (
    id INTEGER PRIMARY KEY,
    expression_id INTEGER,        -- expressions.id 참조
    subtitle_entry_id INTEGER,   -- subtitle_entries.id 참조
    context_before TEXT,          -- "Hi Joey! "
    context_after TEXT,           -- "? I'm fine, thanks."
    FOREIGN KEY (expression_id) REFERENCES expressions(id),
    FOREIGN KEY (subtitle_entry_id) REFERENCES subtitle_entries(id)
);
```

---

## 🚀 정규화의 주요 장점

### 1. **🔍 훨씬 다양하고 복잡한 쿼리 가능**

#### 🔴 현재 (단일 테이블)로는 어려운 쿼리들:
```sql
-- ❌ 이런 쿼리들이 복잡하거나 불가능:

-- "Friends 시즌별 가장 많이 사용된 표현 TOP 10"
-- → media_file에서 시즌 정보를 파싱해야 함

-- "Joey가 가장 많이 사용하는 인사말"  
-- → 화자 정보가 없음

-- "코미디 장르에서 자주 나오는 감정 표현"
-- → 장르 정보가 없음

-- "2000년대 vs 1990년대 영어 표현 변화"
-- → 년도 정보 추출이 복잡
```

#### ✅ 정규화 후 가능한 강력한 쿼리들:

```sql
-- 1. Friends 시즌 1에서 가장 많이 사용된 표현 TOP 20
SELECT 
    e.text,
    COUNT(*) as frequency,
    AVG(e.difficulty_level) as avg_difficulty
FROM expressions e
JOIN expression_occurrences eo ON e.id = eo.expression_id
JOIN subtitle_entries se ON eo.subtitle_entry_id = se.id
JOIN episodes ep ON se.episode_id = ep.id
JOIN seasons s ON ep.season_id = s.id
JOIN shows sh ON s.show_id = sh.id
WHERE sh.name = 'Friends' AND s.season_number = 1
GROUP BY e.id, e.text
ORDER BY frequency DESC
LIMIT 20;

-- 2. 코미디 vs 드라마 장르별 감정 표현 비교
SELECT 
    sh.genre,
    se.emotion,
    COUNT(*) as usage_count,
    AVG(e.difficulty_level) as avg_difficulty
FROM shows sh
JOIN seasons s ON sh.id = s.show_id
JOIN episodes ep ON s.id = ep.season_id
JOIN subtitle_entries se ON ep.id = se.episode_id
JOIN expression_occurrences eo ON se.id = eo.subtitle_entry_id
JOIN expressions e ON eo.expression_id = e.id
WHERE se.emotion IS NOT NULL
GROUP BY sh.genre, se.emotion
ORDER BY sh.genre, usage_count DESC;

-- 3. 시간대별 언어 변화 분석 (1990년대 vs 2000년대)
SELECT 
    CASE 
        WHEN sh.year_start < 2000 THEN '1990s'
        ELSE '2000s'
    END as decade,
    e.category,
    e.text,
    COUNT(*) as frequency
FROM shows sh
JOIN seasons s ON sh.id = s.show_id
JOIN episodes ep ON s.id = ep.season_id
JOIN subtitle_entries se ON ep.id = se.episode_id
JOIN expression_occurrences eo ON se.id = eo.subtitle_entry_id
JOIN expressions e ON eo.expression_id = e.id
GROUP BY decade, e.category, e.text
HAVING frequency > 10
ORDER BY decade, e.category, frequency DESC;

-- 4. 특정 표현의 문맥 분석 ("How are you" 사용 패턴)
SELECT 
    sh.name as show_name,
    s.season_number,
    ep.episode_number,
    ep.title,
    se.speaker,
    eo.context_before + e.text + eo.context_after as full_context,
    se.emotion
FROM expressions e
JOIN expression_occurrences eo ON e.id = eo.expression_id
JOIN subtitle_entries se ON eo.subtitle_entry_id = se.id
JOIN episodes ep ON se.episode_id = ep.id
JOIN seasons s ON ep.season_id = s.id
JOIN shows sh ON s.show_id = sh.id
WHERE e.normalized_text = 'how are you'
ORDER BY sh.name, s.season_number, ep.episode_number;

-- 5. 학습 난이도별 표현 추천 (초급자용)
SELECT 
    e.text,
    e.category,
    COUNT(*) as frequency,
    AVG(e.difficulty_level) as avg_difficulty,
    STRING_AGG(DISTINCT sh.name, ', ') as appears_in_shows
FROM expressions e
JOIN expression_occurrences eo ON e.id = eo.expression_id
JOIN subtitle_entries se ON eo.subtitle_entry_id = se.id
JOIN episodes ep ON se.episode_id = ep.id
JOIN seasons s ON ep.season_id = s.id
JOIN shows sh ON s.show_id = sh.id
WHERE e.difficulty_level <= 2  -- 초급자용
GROUP BY e.id, e.text, e.category
HAVING frequency >= 5  -- 최소 5번 이상 등장
ORDER BY frequency DESC, avg_difficulty ASC;
```

### 2. **📈 데이터 분석 능력 향상**

```sql
-- 언어 학습자를 위한 고급 분석 쿼리들

-- A. 표현 난이도별 학습 순서 제안
WITH expression_stats AS (
    SELECT 
        e.id, e.text, e.category, e.difficulty_level,
        COUNT(*) as frequency,
        COUNT(DISTINCT ep.id) as episode_count,
        COUNT(DISTINCT sh.id) as show_count
    FROM expressions e
    JOIN expression_occurrences eo ON e.id = eo.expression_id
    JOIN subtitle_entries se ON eo.subtitle_entry_id = se.id
    JOIN episodes ep ON se.episode_id = ep.id
    JOIN seasons s ON ep.season_id = s.id
    JOIN shows sh ON s.show_id = sh.id
    GROUP BY e.id, e.text, e.category, e.difficulty_level
)
SELECT 
    difficulty_level,
    category,
    text,
    frequency,
    episode_count,
    show_count,
    -- 학습 우선순위 점수 (빈도 + 출현 범위)
    (frequency * 0.7 + episode_count * 0.2 + show_count * 0.1) as learning_priority
FROM expression_stats
WHERE difficulty_level = 1  -- 초급
ORDER BY learning_priority DESC;

-- B. 상황별 대화 패턴 분석 
SELECT 
    e.category,
    se.emotion,
    e.text,
    COUNT(*) as usage_count,
    -- 해당 상황에서의 사용 비율
    ROUND(
        COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (PARTITION BY e.category), 
        2
    ) as usage_percentage_in_category
FROM expressions e
JOIN expression_occurrences eo ON e.id = eo.expression_id
JOIN subtitle_entries se ON eo.subtitle_entry_id = se.id
WHERE e.category IN ('greeting', 'goodbye', 'apology', 'gratitude')
GROUP BY e.category, se.emotion, e.text
ORDER BY e.category, usage_count DESC;
```

### 3. **🎯 학습자 맞춤 기능**

```sql
-- 개인화된 학습 추천 시스템 쿼리들

-- A. 사용자가 아직 학습하지 않은 고빈도 표현
SELECT e.text, e.category, COUNT(*) as frequency
FROM expressions e
JOIN expression_occurrences eo ON e.id = eo.expression_id
WHERE e.id NOT IN (
    -- 사용자가 이미 학습한 표현들
    SELECT DISTINCT expression_id 
    FROM user_learning_history 
    WHERE user_id = ? AND mastery_level >= 3
)
AND e.difficulty_level <= ?  -- 사용자 레벨
GROUP BY e.id, e.text, e.category
ORDER BY frequency DESC
LIMIT 20;

-- B. 약점 영역 식별 (카테고리별 학습 진도)
SELECT 
    e.category,
    COUNT(DISTINCT e.id) as total_expressions,
    COUNT(DISTINCT uh.expression_id) as learned_expressions,
    ROUND(
        COUNT(DISTINCT uh.expression_id) * 100.0 / COUNT(DISTINCT e.id),
        2
    ) as completion_percentage
FROM expressions e
LEFT JOIN user_learning_history uh ON e.id = uh.expression_id 
    AND uh.user_id = ? AND uh.mastery_level >= 3
GROUP BY e.category
ORDER BY completion_percentage ASC;
```

---

## 📊 구체적인 장점 요약

### 1. **쿼리 다양성 📈**
- **현재**: 기본적인 텍스트 검색만 가능
- **정규화 후**: 시즌별, 장르별, 화자별, 감정별, 시대별 분석 가능

### 2. **성능 최적화 🚀**
```sql
-- 인덱스 최적화 가능
CREATE INDEX idx_expressions_difficulty ON expressions(difficulty_level);
CREATE INDEX idx_episodes_show_season ON episodes(season_id, episode_number);
CREATE INDEX idx_subtitle_speaker ON subtitle_entries(speaker);
```

### 3. **데이터 무결성 🛡️**
```sql
-- 외래키 제약으로 데이터 일관성 보장
ALTER TABLE subtitle_entries 
ADD CONSTRAINT fk_episode 
FOREIGN KEY (episode_id) REFERENCES episodes(id);
```

### 4. **확장성 🌟**
- 새로운 쇼 추가가 체계적
- 화자, 감정, 상황 정보 추가 용이
- AI 해설, 사용자 데이터 연동 간편

### 5. **비즈니스 로직 구현 💰**
```sql
-- 프리미엄 기능: 고급 표현만 접근
SELECT * FROM expressions 
WHERE difficulty_level >= 4 
AND id IN (SELECT expression_id FROM premium_content);

-- 학습 진도 추적
INSERT INTO user_learning_history 
(user_id, expression_id, learned_at, mastery_level)
VALUES (?, ?, NOW(), ?);
```

---

## 🎯 결론

정규화하면 **단순한 자막 검색 DB**에서 **지능형 언어 학습 플랫폼**으로 진화할 수 있습니다!

**현재**: "Batman이 나오는 자막 찾기"  
**정규화 후**: "Friends 시즌 1에서 Joey가 사용한 인사말 중 초급자에게 적합한 표현을 빈도순으로 추천하되, 사용자가 아직 학습하지 않은 것만"

이런 복잡한 비즈니스 로직이 SQL 한 방에 가능해집니다! 🚀
