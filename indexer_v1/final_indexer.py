#!/usr/bin/env python3
"""
최종 미디어 자막 인덱서
- 로컬 디렉토리에서 실행
- 영어/한글 자막 지원 (_ko.srt)
- SQLite 락 문제 해결
"""

import os
import sqlite3
import pysrt
import re
from pathlib import Path
from typing import List, Dict, Union
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FinalMediaIndexer:
    def __init__(self, media_root: str = "/mnt/qnap/media_eng"):
        self.media_root = Path(media_root)
        
        # 현재 디렉토리에 DB 생성 (권한 문제 회피)
        self.db_path = Path.cwd() / "final_media_subtitles.db"
        
        logger.info(f"Media root: {self.media_root}")
        logger.info(f"Database: {self.db_path}")
        
        self.setup_database()
    
    def setup_database(self):
        """데이터베이스 설정"""
        # 기존 DB 삭제
        if self.db_path.exists():
            self.db_path.unlink()
            logger.info("Removed existing database")
        
        # 새 DB 생성
        conn = sqlite3.connect(str(self.db_path), timeout=120)
        conn.execute("PRAGMA journal_mode=WAL")  # WAL 모드
        conn.execute("PRAGMA synchronous=NORMAL")  # 성능 향상
        
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE subtitles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                media_file TEXT NOT NULL,
                subtitle_file TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                text TEXT NOT NULL,
                language TEXT NOT NULL,
                directory TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 인덱스 생성
        cursor.execute("CREATE INDEX idx_text ON subtitles(text)")
        cursor.execute("CREATE INDEX idx_language ON subtitles(language)")
        cursor.execute("CREATE INDEX idx_media_file ON subtitles(media_file)")
        
        conn.commit()
        conn.close()
        logger.info("Database created successfully")
    
    def detect_language(self, text: str, filename_hint: str = "") -> str:
        """언어 감지"""
        try:
            # 파일명 힌트 우선
            if "_ko" in filename_hint.lower():
                return "ko"
            
            # 한글 문자 확인
            korean_chars = sum(1 for c in text if '\uac00' <= c <= '\ud7af')
            if korean_chars > 0:
                return "ko"
            
            # 기본값은 영어
            return "en"
            
        except Exception:
            return "en"
    
    def clean_subtitle_text(self, text: str, language: str = "en") -> str:
        """자막 텍스트 정제"""
        # HTML 태그 제거
        text = re.sub(r'<[^>]+>', '', text)
        
        # 자막 특수 문자 제거
        text = re.sub(r'{[^}]*}', '', text)
        
        if language == "en":
            # 영어 자막 - 설명 제거
            text = re.sub(r'\([^)]*\)', '', text)
            text = re.sub(r'\[[^\]]*\]', '', text)
            
            # 음향 효과 제거
            sound_patterns = [
                r'\b(music|laughs?|applause|cheering|crying|screaming)\b',
                r'\b(narrator|announcer|voice-over)\b'
            ]
            for pattern in sound_patterns:
                text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        # 공백 정리
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    
    def is_valid_dialogue(self, text: str) -> bool:
        """유효한 대사인지 판단"""
        if not text or len(text.strip()) < 2:
            return False
        
        # 제외할 패턴들
        exclude_patterns = [
            r'^\d+:\d+',          # 시간
            r'subtitle by',       # 자막 제작자
            r'www\.',            # 웹사이트
            r'http',             # URL
            r'[♪♫]',             # 음악 기호
            r'^\[.*\]$',         # 전체가 대괄호
            r'^\(.*\)$',         # 전체가 소괄호
        ]
        
        text_lower = text.lower()
        for pattern in exclude_patterns:
            if re.search(pattern, text_lower):
                return False
        
        return True
    
    def parse_srt_file(self, srt_path: Path) -> List[Dict]:
        """SRT 파일 파싱"""
        try:
            logger.info(f"Parsing: {srt_path.name}")
            
            subs = pysrt.open(str(srt_path), encoding='utf-8')
            subtitles = []
            
            for sub in subs:
                # 텍스트 정제
                original_text = sub.text
                language = self.detect_language(original_text, srt_path.name)
                cleaned_text = self.clean_subtitle_text(original_text, language)
                
                # 유효한 대사인지 확인
                if self.is_valid_dialogue(cleaned_text):
                    subtitles.append({
                        'start_time': str(sub.start),
                        'end_time': str(sub.end),
                        'text': cleaned_text,
                        'language': language
                    })
            
            logger.info(f"Extracted {len(subtitles)} valid subtitles")
            return subtitles
            
        except Exception as e:
            logger.error(f"Error parsing {srt_path}: {e}")
            return []
    
    def find_media_and_subtitles(self, directory: Path) -> List[Dict]:
        """디렉토리에서 미디어-자막 쌍 찾기"""
        media_extensions = {'.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v'}
        pairs = []
        
        try:
            # 모든 미디어 파일 찾기
            for media_file in directory.rglob('*'):
                if not media_file.is_file():
                    continue
                    
                if media_file.suffix.lower() in media_extensions:
                    media_stem = media_file.stem
                    media_dir = media_file.parent
                    
                    subtitle_files = []
                    
                    # 영어 자막 (.srt)
                    en_srt = media_dir / f"{media_stem}.srt"
                    if en_srt.exists():
                        subtitle_files.append(en_srt)
                    
                    # 한글 자막 (_ko.srt)
                    ko_srt = media_dir / f"{media_stem}_ko.srt"
                    if ko_srt.exists():
                        subtitle_files.append(ko_srt)
                    
                    # 자막 파일이 있으면 추가
                    if subtitle_files:
                        pairs.append({
                            'media_file': media_file,
                            'subtitle_files': subtitle_files,
                            'directory': directory
                        })
        
        except Exception as e:
            logger.error(f"Error scanning {directory}: {e}")
        
        return pairs
    
    def save_to_database(self, media_file: Path, subtitle_file: Path, 
                        subtitles: List[Dict], directory: Path):
        """데이터베이스에 저장"""
        if not subtitles:
            return
        
        try:
            conn = sqlite3.connect(str(self.db_path), timeout=120)
            cursor = conn.cursor()
            
            for subtitle in subtitles:
                cursor.execute("""
                    INSERT INTO subtitles 
                    (media_file, subtitle_file, start_time, end_time, text, language, directory)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    str(media_file),
                    str(subtitle_file),
                    subtitle['start_time'],
                    subtitle['end_time'],
                    subtitle['text'],
                    subtitle['language'],
                    str(directory)
                ))
            
            conn.commit()
            conn.close()
            
            # 통계 출력
            lang_count = {}
            for sub in subtitles:
                lang = sub['language']
                lang_count[lang] = lang_count.get(lang, 0) + 1
            
            lang_info = ', '.join([f"{lang}: {count}" for lang, count in lang_count.items()])
            logger.info(f"Saved {media_file.name} - {lang_info}")
            
        except Exception as e:
            logger.error(f"Database save failed for {media_file.name}: {e}")
    
    def index_directory(self, directory: Path):
        """단일 디렉토리 인덱싱"""
        logger.info(f"Indexing: {directory}")
        
        pairs = self.find_media_and_subtitles(directory)
        logger.info(f"Found {len(pairs)} media-subtitle pairs")
        
        for pair in pairs:
            media_file = pair['media_file']
            subtitle_files = pair['subtitle_files']
            
            logger.info(f"Processing: {media_file.name}")
            
            for subtitle_file in subtitle_files:
                subtitles = self.parse_srt_file(subtitle_file)
                if subtitles:
                    self.save_to_database(media_file, subtitle_file, subtitles, directory)
    
    def index_all(self):
        """전체 인덱싱"""
        logger.info("Starting full indexing")
        
        processed_dirs = 0
        for item in self.media_root.iterdir():
            if item.is_dir() and not item.name.startswith('.') and item.name != 'indexer':
                processed_dirs += 1
                logger.info(f"Directory {processed_dirs}: {item.name}")
                self.index_directory(item)
        
        self.print_stats()
        logger.info("Indexing completed")
    
    def search(self, query: str, language: Union[str, None] = None, limit: int = 50) -> List[Dict]:
        """자막 검색"""
        try:
            conn = sqlite3.connect(str(self.db_path), timeout=30)
            cursor = conn.cursor()
            
            if language:
                cursor.execute("""
                    SELECT media_file, subtitle_file, start_time, end_time, text, language, directory
                    FROM subtitles 
                    WHERE text LIKE ? AND language = ?
                    ORDER BY media_file, start_time
                    LIMIT ?
                """, (f"%{query}%", language, limit))
            else:
                cursor.execute("""
                    SELECT media_file, subtitle_file, start_time, end_time, text, language, directory
                    FROM subtitles 
                    WHERE text LIKE ?
                    ORDER BY language, media_file, start_time
                    LIMIT ?
                """, (f"%{query}%", limit))
            
            results = []
            for row in cursor.fetchall():
                results.append({
                    'media_file': row[0],
                    'subtitle_file': row[1],
                    'start_time': row[2],
                    'end_time': row[3],
                    'text': row[4],
                    'language': row[5],
                    'directory': row[6]
                })
            
            conn.close()
            return results
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
    
    def print_stats(self):
        """통계 출력"""
        try:
            conn = sqlite3.connect(str(self.db_path), timeout=30)
            cursor = conn.cursor()
            
            # 전체 통계
            cursor.execute("SELECT COUNT(*) FROM subtitles")
            total_subtitles = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(DISTINCT media_file) FROM subtitles")
            total_media = cursor.fetchone()[0]
            
            # 언어별 통계
            cursor.execute("""
                SELECT language, COUNT(*) 
                FROM subtitles 
                GROUP BY language 
                ORDER BY COUNT(*) DESC
            """)
            lang_stats = cursor.fetchall()
            
            conn.close()
            
            print(f"\n=== 데이터베이스 통계 ===")
            print(f"총 자막 수: {total_subtitles:,}")
            print(f"총 미디어 파일 수: {total_media}")
            print(f"언어별 분포:")
            for lang, count in lang_stats:
                lang_name = "한국어" if lang == "ko" else "영어"
                print(f"  {lang_name} ({lang}): {count:,}개")
            
        except Exception as e:
            logger.error(f"Stats failed: {e}")

# 테스트 및 실행 함수
def demo():
    """데모 실행"""
    indexer = FinalMediaIndexer()
    
    # Batman 디렉토리로 테스트
    test_dirs = []
    for item in Path("/mnt/qnap/media_eng/Ani").iterdir():
        if item.is_dir() and "batman" in item.name.lower():
            test_dirs.append(item)
            break
    
    if test_dirs:
        test_dir = test_dirs[0]
        logger.info(f"Demo with: {test_dir.name}")
        indexer.index_directory(test_dir)
        
        # 검색 테스트
        test_queries = ["Batman", "perfect", "good"]
        for query in test_queries:
            results = indexer.search(query, limit=3)
            if results:
                print(f"\n=== '{query}' 검색 결과 ===")
                for i, result in enumerate(results, 1):
                    print(f"{i}. [{result['language']}] {result['start_time']}")
                    print(f"   {result['text']}")
                    print()

if __name__ == "__main__":
    demo()
