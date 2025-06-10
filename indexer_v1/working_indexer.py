#!/usr/bin/env python3

import sqlite3
import pysrt
import re
from pathlib import Path

print("=== 미디어 자막 인덱서 v3 ===")
print("영어/한글 자막 지원 (_ko.srt)")

class WorkingIndexer:
    def __init__(self):
        self.db_path = "working_subtitles.db"
        self.init_db()
    
    def init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 테이블이 이미 존재하는지 확인
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
                    text TEXT,
                    language TEXT,
                    directory TEXT
                )
            """)
            conn.commit()
            print("✅ 데이터베이스 초기화 완료")
        else:
            print("✅ 기존 데이터베이스 연결")
        
        conn.close()
    
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
            cursor.execute("""
                INSERT INTO subtitles 
                (media_file, subtitle_file, start_time, end_time, text, language, directory)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                str(media_file), str(srt_file),
                sub['start_time'], sub['end_time'],
                sub['text'], sub['language'], str(directory)
            ))
        
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
    
    def search(self, query, language=None):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
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
        conn.close()
        
        if results:
            print(f"\n🔍 '{query}' 검색 결과 ({len(results)}개):")
            for i, (media, start, end, text, lang) in enumerate(results, 1):
                media_name = Path(media).name
                lang_name = "한국어" if lang == "ko" else "영어"
                print(f"\n{i:2d}. [{lang_name}] {media_name}")
                print(f"    시간: {start} ~ {end}")
                print(f"    자막: {text}")
        else:
            print(f"❌ '{query}' 검색 결과 없음")
    
    def stats(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM subtitles")
        total = cursor.fetchone()[0]
        
        cursor.execute("SELECT language, COUNT(*) FROM subtitles GROUP BY language")
        lang_stats = cursor.fetchall()
        
        cursor.execute("SELECT COUNT(DISTINCT media_file) FROM subtitles")
        media_count = cursor.fetchone()[0]
        
        conn.close()
        
        print(f"\n📊 데이터베이스 통계:")
        print(f"   총 자막: {total:,}개")
        print(f"   미디어 파일: {media_count}개")
        for lang, count in lang_stats:
            lang_name = "한국어" if lang == "ko" else "영어"
            print(f"   {lang_name}: {count:,}개")
    
    def index_all_directories(self):
        """전체 미디어 디렉토리 인덱싱"""
        media_root = Path("/mnt/qnap/media_eng")
        print(f"\n🚀 전체 인덱싱 시작: {media_root}")
        
        total_processed = 0
        total_dirs = 0
        
        for category_dir in media_root.iterdir():
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
        
        print(f"\n🎉 전체 인덱싱 완료!")
        print(f"   처리된 카테고리: {total_dirs}개")
        self.stats()

# 테스트 실행
if __name__ == "__main__":
    indexer = WorkingIndexer()
    
    print("\n🎯 인덱싱 옵션을 선택하세요:")
    print("1. 전체 인덱싱 (모든 미디어 디렉토리)")
    print("2. Batman 테스트 인덱싱")
    print("3. 사용자 지정 디렉토리")
    print("4. 현재 DB 통계만 보기")
    
    choice = input("\n선택 (1-4): ").strip()
    
    if choice == "1":
        print("\n⚠️  전체 인덱싱을 시작합니다. 시간이 오래 걸릴 수 있습니다.")
        confirm = input("계속하시겠습니까? (y/N): ").strip().lower()
        if confirm == 'y':
            indexer.index_all_directories()
        else:
            print("취소되었습니다.")
    
    elif choice == "2":
        batman_dir = "/mnt/qnap/media_eng/Ani/Batman The Animated Series (1992) Season 1-4 S01-S04 + Extras (1080p BluRay x265 HEVC 10bit AAC 2.0 RCVR)/Season 1"
        if Path(batman_dir).exists():
            indexer.index_directory(batman_dir)
            indexer.stats()
            indexer.search("Batman")
            indexer.search("perfect")
        else:
            print("❌ Batman 테스트 디렉토리를 찾을 수 없습니다")
    
    elif choice == "3":
        custom_path = input("인덱싱할 디렉토리 경로를 입력하세요: ").strip()
        if Path(custom_path).exists():
            indexer.index_directory(custom_path)
            indexer.stats()
        else:
            print("❌ 디렉토리를 찾을 수 없습니다")
    
    elif choice == "4":
        indexer.stats()
    
    else:
        print("❌ 잘못된 선택입니다.")

