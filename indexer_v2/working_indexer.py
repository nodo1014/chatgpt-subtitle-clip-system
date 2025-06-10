#!/usr/bin/env python3

import sqlite3
import pysrt
import re
import os
from pathlib import Path
from datetime import datetime

print("=== 미디어 자막 인덱서 v2.0 ===")
print("영어/한글 자막 지원, FTS 검색, 메타데이터 추가")

class WorkingIndexer:
    def __init__(self):
        self.db_path = "working_subtitles_v2.db"
        self.media_root = Path("/mnt/qnap/media_eng")
        self.init_db()
    
    def init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # subtitles 테이블 (v2에서 indexed_at 컬럼 추가)
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='subtitles'")
        table_exists = cursor.fetchone() is not None
        
        if not table_exists:
            cursor.execute("""
                CREATE TABLE subtitles (
                    id INTEGER PRIMARY KEY,
                    media_file TEXT,
                    subtitle_file TEXT,
                    start_time TEXT,
                    end_time TEXT,
                    start_time_ms INTEGER,
                    end_time_ms INTEGER,
                    text TEXT,
                    language TEXT,
                    directory TEXT,
                    indexed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # metadata 테이블 생성 (인덱싱 정보 저장)
            cursor.execute("""
                CREATE TABLE metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
            print("✅ 데이터베이스 v2 초기화 완료")
        else:
            print("✅ 기존 데이터베이스 연결")
        
        # FTS 테이블 생성 또는 확인
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='subtitles_fts'")
        fts_exists = cursor.fetchone() is not None
        
        if not fts_exists:
            cursor.execute("""
                CREATE VIRTUAL TABLE subtitles_fts USING fts5(
                    text, 
                    media_file, 
                    language, 
                    directory,
                    content='subtitles', 
                    content_rowid='id'
                )
            """)
            
            # 기존 데이터가 있으면 FTS에 복사
            cursor.execute("SELECT COUNT(*) FROM subtitles")
            if cursor.fetchone()[0] > 0:
                cursor.execute("""
                    INSERT INTO subtitles_fts(rowid, text, media_file, language, directory)
                    SELECT id, text, media_file, language, directory FROM subtitles
                """)
                print("✅ FTS 인덱스 구성 완료")
            
            conn.commit()
        
        conn.close()
    
    def update_metadata(self, key, value):
        """메타데이터 업데이트"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO metadata (key, value, updated_at) 
            VALUES (?, ?, CURRENT_TIMESTAMP)
        """, (key, value))
        
        conn.commit()
        conn.close()
    
    def get_metadata(self, key):
        """메타데이터 조회"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT value, updated_at FROM metadata WHERE key = ?", (key,))
            result = cursor.fetchone()
            conn.close()
            
            return result if result else (None, None)
        except:
            return (None, None)
    
    def convert_time_to_ms(self, time_str):
        """SRT 시간을 밀리초로 변환"""
        try:
            # "00:01:23,456" -> 83456
            time_str = time_str.replace(',', '.')
            parts = time_str.split(':')
            hours = int(parts[0])
            minutes = int(parts[1])
            seconds = float(parts[2])
            return int((hours * 3600 + minutes * 60 + seconds) * 1000)
        except:
            return 0

    def detect_language(self, text, filename):
        if "_ko" in filename.lower():
            return "ko"
        
        korean_chars = sum(1 for c in text if '\uac00' <= c <= '\ud7af')
        if korean_chars > 0:
            return "ko"
        return "en"
    
    def clean_text(self, text, language):
        text = re.sub(r'<[^>]+>', '', text)
        text = re.sub(r'{[^}]*}', '', text)
        
        if language == "en":
            text = re.sub(r'\([^)]*\)', '', text)
            text = re.sub(r'\[[^\]]*\]', '', text)
        
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    
    def is_dialogue(self, text):
        if len(text) < 3:
            return False
        
        exclude = ['subtitle by', 'www.', 'http', 'chapter']
        text_lower = text.lower()
        
        for pattern in exclude:
            if pattern in text_lower:
                return False
        
        return True
    
    def process_srt(self, srt_path):
        print(f"📁 처리 중: {srt_path.name}")
        
        try:
            subs = pysrt.open(str(srt_path), encoding='utf-8')
            subtitles = []
            
            for sub in subs:
                language = self.detect_language(sub.text, srt_path.name)
                cleaned = self.clean_text(sub.text, language)
                
                if self.is_dialogue(cleaned):
                    subtitles.append({
                        'start_time': str(sub.start),
                        'end_time': str(sub.end),
                        'text': cleaned,
                        'language': language
                    })
            
            print(f"   추출된 자막: {len(subtitles)}개")
            return subtitles
            
        except Exception as e:
            print(f"   ❌ 오류: {e}")
            return []
    
    def save_subtitles(self, media_file, srt_file, subtitles, directory):
        if not subtitles:
            return
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for sub in subtitles:
            start_ms = self.convert_time_to_ms(sub['start_time'])
            end_ms = self.convert_time_to_ms(sub['end_time'])
            
            cursor.execute("""
                INSERT INTO subtitles 
                (media_file, subtitle_file, start_time, end_time, start_time_ms, end_time_ms, text, language, directory)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                str(media_file), str(srt_file),
                sub['start_time'], sub['end_time'],
                start_ms, end_ms,
                sub['text'], sub['language'], str(directory)
            ))
            
            # FTS에도 추가
            subtitle_id = cursor.lastrowid
            cursor.execute("""
                INSERT INTO subtitles_fts (rowid, text, media_file, language, directory)
                VALUES (?, ?, ?, ?, ?)
            """, (subtitle_id, sub['text'], str(media_file), sub['language'], str(directory)))
        
        conn.commit()
        conn.close()
        
        ko_count = sum(1 for s in subtitles if s['language'] == 'ko')
        en_count = sum(1 for s in subtitles if s['language'] == 'en')
        
        print(f"   💾 저장 완료: 한국어 {ko_count}개, 영어 {en_count}개")
    
    def find_subtitles(self, media_file):
        media_stem = media_file.stem
        media_dir = media_file.parent
        subtitles = []
        
        # 영어 자막
        en_srt = media_dir / f"{media_stem}.srt"
        if en_srt.exists():
            subtitles.append(en_srt)
        
        # 한글 자막
        ko_srt = media_dir / f"{media_stem}_ko.srt"
        if ko_srt.exists():
            subtitles.append(ko_srt)
        
        return subtitles
    
    def find_test_directory(self):
        """테스트용 디렉토리 자동 검색"""
        test_patterns = [
            "**/Batman*/**/Season*",
            "**/Batman*",
            "**/Ani/**/Season*"
        ]
        
        for pattern in test_patterns:
            matches = list(self.media_root.glob(pattern))
            if matches:
                # 가장 적당한 크기의 디렉토리 선택
                for match in matches:
                    if match.is_dir():
                        media_files = list(match.glob("*.mp4")) + list(match.glob("*.mkv"))
                        if 1 <= len(media_files) <= 30:  # 1-30개 파일이 있는 디렉토리
                            return match
        
        # 패턴이 없으면 첫 번째 발견되는 적당한 디렉토리
        for category in self.media_root.iterdir():
            if category.is_dir() and not category.name.startswith('.'):
                for subdir in category.rglob("*"):
                    if subdir.is_dir():
                        media_files = list(subdir.glob("*.mp4")) + list(subdir.glob("*.mkv"))
                        if 1 <= len(media_files) <= 10:
                            return subdir
        
        return None
    
    def index_directory(self, directory_path):
        directory = Path(directory_path)
        print(f"\n🎬 디렉토리 스캔: {directory.name}")
        
        media_extensions = {'.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v'}
        media_files = []
        
        for file_path in directory.rglob('*'):
            if file_path.is_file() and file_path.suffix.lower() in media_extensions:
                media_files.append(file_path)
        
        print(f"   미디어 파일: {len(media_files)}개 발견")
        
        processed = 0
        for media_file in media_files:  # 전체 파일 처리
            subtitle_files = self.find_subtitles(media_file)
            
            if subtitle_files:
                print(f"\n🎥 {media_file.name}")
                
                for srt_file in subtitle_files:
                    subtitles = self.process_srt(srt_file)
                    if subtitles:
                        self.save_subtitles(media_file, srt_file, subtitles, directory)
                        processed += 1
        
        print(f"\n✅ 처리 완료: {processed}개 파일")
        
        # 인덱싱 완료 시간 기록
        self.update_metadata("last_indexing", datetime.now().isoformat())
    
    def search(self, query, language=None, use_fts=True):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        start_time = datetime.now()
        
        if use_fts:
            # FTS 검색 사용
            if language:
                cursor.execute("""
                    SELECT s.media_file, s.start_time, s.end_time, s.text, s.language
                    FROM subtitles_fts f
                    JOIN subtitles s ON f.rowid = s.id
                    WHERE f.text MATCH ? AND s.language = ?
                    ORDER BY s.media_file, s.start_time
                    LIMIT 10
                """, (query, language))
            else:
                cursor.execute("""
                    SELECT s.media_file, s.start_time, s.end_time, s.text, s.language
                    FROM subtitles_fts f
                    JOIN subtitles s ON f.rowid = s.id
                    WHERE f.text MATCH ?
                    ORDER BY s.language, s.media_file, s.start_time
                    LIMIT 10
                """, (query,))
        else:
            # LIKE 검색 사용
            if language:
                cursor.execute("""
                    SELECT media_file, start_time, end_time, text, language
                    FROM subtitles 
                    WHERE text LIKE ? AND language = ?
                    ORDER BY media_file, start_time
                    LIMIT 10
                """, (f"%{query}%", language))
            else:
                cursor.execute("""
                    SELECT media_file, start_time, end_time, text, language
                    FROM subtitles 
                    WHERE text LIKE ?
                    ORDER BY language, media_file, start_time
                    LIMIT 10
                """, (f"%{query}%",))
        
        results = cursor.fetchall()
        search_time = (datetime.now() - start_time).total_seconds() * 1000
        conn.close()
        
        search_method = "FTS" if use_fts else "LIKE"
        
        if results:
            print(f"\n🔍 '{query}' 검색 결과 ({len(results)}개) - {search_method} 검색: {search_time:.2f}ms")
            for i, (media, start, end, text, lang) in enumerate(results, 1):
                media_name = Path(media).name
                lang_name = "한국어" if lang == "ko" else "영어"
                print(f"\n{i:2d}. [{lang_name}] {media_name}")
                print(f"    시간: {start} ~ {end}")
                print(f"    자막: {text}")
        else:
            print(f"❌ '{query}' 검색 결과 없음 - {search_method} 검색: {search_time:.2f}ms")
    
    def get_db_size(self):
        """데이터베이스 파일 크기 반환 (MB)"""
        try:
            size_bytes = os.path.getsize(self.db_path)
            size_mb = size_bytes / (1024 * 1024)
            return size_mb
        except:
            return 0
    
    def get_table_info(self):
        """테이블 정보 조회"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 테이블 목록
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [row[0] for row in cursor.fetchall()]
        
        table_info = {}
        for table in tables:
            if not table.startswith('subtitles_fts'):  # FTS 테이블은 제외
                cursor.execute(f"PRAGMA table_info({table})")
                columns = cursor.fetchall()
                table_info[table] = [(col[1], col[2]) for col in columns]  # (name, type)
        
        conn.close()
        return table_info
    
    def stats(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 기본 통계
        cursor.execute("SELECT COUNT(*) FROM subtitles")
        total = cursor.fetchone()[0]
        
        cursor.execute("SELECT language, COUNT(*) FROM subtitles GROUP BY language")
        lang_stats = cursor.fetchall()
        
        cursor.execute("SELECT COUNT(DISTINCT media_file) FROM subtitles")
        media_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT directory) FROM subtitles")
        dir_count = cursor.fetchone()[0]
        
        conn.close()
        
        # 메타데이터 정보
        last_indexing, last_time = self.get_metadata("last_indexing")
        db_size = self.get_db_size()
        table_info = self.get_table_info()
        
        print(f"\n📊 데이터베이스 통계 (v2.0):")
        print(f"{'='*50}")
        print(f"   💾 DB 파일: {self.db_path}")
        print(f"   📦 DB 크기: {db_size:.2f} MB")
        
        if last_indexing:
            try:
                last_dt = datetime.fromisoformat(last_indexing)
                time_str = last_dt.strftime("%Y-%m-%d %H:%M:%S")
                print(f"   🕒 최근 인덱싱: {time_str}")
            except:
                print(f"   🕒 최근 인덱싱: {last_indexing}")
        else:
            print(f"   🕒 최근 인덱싱: 정보 없음")
        
        print(f"\n📈 데이터 통계:")
        print(f"   총 자막: {total:,}개")
        print(f"   미디어 파일: {media_count:,}개")
        print(f"   처리된 디렉토리: {dir_count:,}개")
        
        for lang, count in lang_stats:
            lang_name = "한국어" if lang == "ko" else "영어"
            percentage = (count / total * 100) if total > 0 else 0
            print(f"   {lang_name}: {count:,}개 ({percentage:.1f}%)")
        
        print(f"\n🗄️  테이블 구조:")
        for table_name, columns in table_info.items():
            print(f"   📋 {table_name}:")
            for col_name, col_type in columns:
                print(f"      - {col_name} ({col_type})")
        
        # FTS 테이블 존재 여부
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='subtitles_fts'")
        fts_exists = cursor.fetchone() is not None
        conn.close()
        
        print(f"\n🔍 검색 엔진:")
        if fts_exists:
            print(f"   ✅ FTS5 가상 테이블 활성화")
        else:
            print(f"   ❌ FTS5 테이블 없음 (LIKE 검색만 가능)")
    
    def index_all_directories(self):
        """전체 미디어 디렉토리 인덱싱"""
        print(f"\n🚀 전체 인덱싱 시작: {self.media_root}")
        start_time = datetime.now()
        
        total_processed = 0
        total_dirs = 0
        
        for category_dir in self.media_root.iterdir():
            if (category_dir.is_dir() and 
                not category_dir.name.startswith('.') and 
                category_dir.name != 'indexer'):
                
                total_dirs += 1
                print(f"\n{'='*60}")
                print(f"📁 카테고리 {total_dirs}: {category_dir.name}")
                print(f"{'='*60}")
                
                try:
                    self.index_directory(category_dir)
                    
                    # 현재까지의 통계 출력
                    conn = sqlite3.connect(self.db_path)
                    cursor = conn.cursor()
                    cursor.execute("SELECT COUNT(*) FROM subtitles")
                    current_total = cursor.fetchone()[0]
                    conn.close()
                    
                    print(f"\n📊 현재까지 총 자막: {current_total:,}개")
                    
                except Exception as e:
                    print(f"❌ {category_dir.name} 처리 실패: {e}")
        
        end_time = datetime.now()
        duration = end_time - start_time
        
        print(f"\n🎉 전체 인덱싱 완료!")
        print(f"   처리된 카테고리: {total_dirs}개")
        print(f"   소요 시간: {duration}")
        
        # 인덱싱 완료 정보 저장
        self.update_metadata("last_full_indexing", end_time.isoformat())
        self.update_metadata("last_indexing_duration", str(duration.total_seconds()))
        
        self.stats()

# 테스트 실행
if __name__ == "__main__":
    indexer = WorkingIndexer()
    
    print("\n🎯 인덱싱 옵션을 선택하세요:")
    print("1. 전체 인덱싱 (모든 미디어 디렉토리)")
    print("2. 테스트 인덱싱 (자동 검색된 디렉토리)")
    print("3. 사용자 지정 디렉토리")
    print("4. 현재 DB 통계만 보기")
    print("5. 검색 테스트 (FTS vs LIKE 비교)")
    
    choice = input("\n선택 (1-5): ").strip()
    
    if choice == "1":
        print("\n⚠️  전체 인덱싱을 시작합니다. 시간이 오래 걸릴 수 있습니다.")
        confirm = input("계속하시겠습니까? (y/N): ").strip().lower()
        if confirm == 'y':
            indexer.index_all_directories()
        else:
            print("취소되었습니다.")
    
    elif choice == "2":
        test_dir = indexer.find_test_directory()
        if test_dir:
            print(f"🎯 자동 검색된 테스트 디렉토리: {test_dir}")
            confirm = input("이 디렉토리로 테스트하시겠습니까? (y/N): ").strip().lower()
            if confirm == 'y':
                indexer.index_directory(test_dir)
                indexer.stats()
                
                # 샘플 검색 테스트
                print("\n🔍 샘플 검색 테스트:")
                indexer.search("the", use_fts=True)
                print("\n--- 성능 비교 ---")
                indexer.search("Batman", use_fts=True)
                indexer.search("Batman", use_fts=False)
            else:
                print("취소되었습니다.")
        else:
            print("❌ 적당한 테스트 디렉토리를 찾을 수 없습니다")
    
    elif choice == "3":
        custom_path = input("인덱싱할 디렉토리 경로를 입력하세요: ").strip()
        if Path(custom_path).exists():
            indexer.index_directory(custom_path)
            indexer.stats()
        else:
            print("❌ 디렉토리를 찾을 수 없습니다")
    
    elif choice == "4":
        indexer.stats()
    
    elif choice == "5":
        print("\n🔍 검색 테스트 (FTS vs LIKE 성능 비교)")
        while True:
            query = input("\n검색어 입력 (q=종료): ").strip()
            if query.lower() == 'q':
                break
            if query:
                print("\n--- FTS 검색 ---")
                indexer.search(query, use_fts=True)
                print("\n--- LIKE 검색 ---")
                indexer.search(query, use_fts=False)
    
    else:
        print("❌ 잘못된 선택입니다.")

