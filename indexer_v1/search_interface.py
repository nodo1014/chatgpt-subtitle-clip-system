#!/usr/bin/env python3

import sqlite3
import time
import re
from pathlib import Path

class SubtitleSearch:
    def __init__(self, db_path="working_subtitles.db"):
        self.db_path = db_path
        
    def search(self, query, language=None, limit=20):
        """
        자막에서 텍스트 검색
        
        Args:
            query: 검색할 텍스트
            language: 언어 필터 ('en', 'ko', None for all)
            limit: 결과 개수 제한
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        start_time = time.time()
        
        if language:
            cursor.execute('''
                SELECT s.media_file, s.start_time, s.end_time, s.text, s.directory, s.subtitle_file
                FROM subtitles_fts fts
                JOIN subtitles s ON s.id = fts.rowid
                WHERE fts.text MATCH ? AND s.language = ?
                ORDER BY rank
                LIMIT ?
            ''', (query, language, limit))
        else:
            cursor.execute('''
                SELECT s.media_file, s.start_time, s.end_time, s.text, s.directory, s.subtitle_file, s.language
                FROM subtitles_fts fts
                JOIN subtitles s ON s.id = fts.rowid
                WHERE fts.text MATCH ?
                ORDER BY rank
                LIMIT ?
            ''', (query, limit))
        
        results = cursor.fetchall()
        search_time = (time.time() - start_time) * 1000
        
        conn.close()
        
        return {
            'results': results,
            'count': len(results),
            'search_time_ms': search_time,
            'query': query,
            'language_filter': language
        }
    
    def format_time(self, time_str):
        """SRT 시간을 초로 변환"""
        try:
            time_parts = time_str.replace(',', '.').split(':')
            hours = int(time_parts[0])
            minutes = int(time_parts[1])
            seconds = float(time_parts[2])
            return hours * 3600 + minutes * 60 + seconds
        except:
            return 0
    
    def print_results(self, search_result):
        """검색 결과를 보기 좋게 출력"""
        print(f"\n🔍 검색어: '{search_result['query']}'")
        print(f"📊 결과: {search_result['count']}개 (검색시간: {search_result['search_time_ms']:.2f}ms)")
        
        if search_result['language_filter']:
            lang_name = "영어" if search_result['language_filter'] == 'en' else "한글"
            print(f"🌐 언어 필터: {lang_name}")
        
        print("-" * 80)
        
        for i, result in enumerate(search_result['results'], 1):
            media_file = Path(result[0]).name
            start_time = result[1]
            end_time = result[2]
            text = result[3]
            directory = Path(result[4]).name
            
            # 언어 정보 (전체 검색일 때만)
            if not search_result['language_filter']:
                language = result[6]
                lang_emoji = "🇺🇸" if language == 'en' else "🇰🇷"
            else:
                lang_emoji = "🇺🇸" if search_result['language_filter'] == 'en' else "🇰🇷"
            
            print(f"{i:2d}. {lang_emoji} 📁 {directory}")
            print(f"    📺 {media_file}")
            print(f"    ⏰ {start_time} → {end_time}")
            print(f"    💬 {text}")
            
            # 비디오 플레이를 위한 정보
            start_seconds = self.format_time(start_time)
            print(f"    🎬 플레이 시작: {start_seconds:.1f}초")
            print()
    
    def interactive_search(self):
        """대화형 검색 인터페이스"""
        print("=" * 60)
        print("🎬 미디어 자막 검색 시스템")
        print("=" * 60)
        print("💡 사용법:")
        print("  - 검색어 입력 후 Enter")
        print("  - 'en:검색어' (영어만), 'ko:검색어' (한글만)")
        print("  - 'quit' 또는 'exit'로 종료")
        print("-" * 60)
        
        while True:
            try:
                user_input = input("\n🔍 검색어를 입력하세요: ").strip()
                
                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("👋 검색을 종료합니다.")
                    break
                
                if not user_input:
                    continue
                
                # 언어 필터 파싱
                language = None
                if user_input.startswith('en:'):
                    language = 'en'
                    query = user_input[3:].strip()
                elif user_input.startswith('ko:'):
                    language = 'ko'
                    query = user_input[3:].strip()
                else:
                    query = user_input
                
                if not query:
                    print("❌ 검색어를 입력해주세요.")
                    continue
                
                # 검색 실행
                result = self.search(query, language, limit=10)
                self.print_results(result)
                
                if result['count'] == 0:
                    print("💡 다른 검색어를 시도해보세요.")
                
            except KeyboardInterrupt:
                print("\n👋 검색을 종료합니다.")
                break
            except Exception as e:
                print(f"❌ 오류 발생: {e}")

def main():
    searcher = SubtitleSearch()
    
    # 데이터베이스 상태 확인
    conn = sqlite3.connect(searcher.db_path)
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM subtitles')
    total_count = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(DISTINCT directory) FROM subtitles')
    dir_count = cursor.fetchone()[0]
    
    print(f"📊 데이터베이스 상태: {total_count:,}개 자막, {dir_count}개 디렉토리")
    
    conn.close()
    
    # 대화형 검색 시작
    searcher.interactive_search()

if __name__ == "__main__":
    main()
