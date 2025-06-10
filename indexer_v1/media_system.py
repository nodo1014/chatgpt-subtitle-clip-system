#!/usr/bin/env python3

import sqlite3
import sys
import os
from pathlib import Path

# 현재 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from search_interface import SubtitleSearch
from video_player import VideoPlayer

class MediaIndexSystem:
    def __init__(self):
        self.db_path = "working_subtitles.db"
        self.searcher = SubtitleSearch(self.db_path)
        self.player = VideoPlayer(self.db_path)
        
    def show_database_stats(self):
        """데이터베이스 통계 표시"""
        if not Path(self.db_path).exists():
            print("❌ 데이터베이스 파일을 찾을 수 없습니다.")
            return False
            
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 전체 통계
        cursor.execute('SELECT COUNT(*) FROM subtitles')
        total_subtitles = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(DISTINCT media_file) FROM subtitles')
        total_files = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(DISTINCT directory) FROM subtitles')
        total_dirs = cursor.fetchone()[0]
        
        # 언어별 통계
        cursor.execute('SELECT language, COUNT(*) FROM subtitles GROUP BY language')
        lang_stats = cursor.fetchall()
        
        # 디렉토리별 통계
        cursor.execute('''
            SELECT directory, COUNT(*) as subtitle_count, COUNT(DISTINCT media_file) as file_count
            FROM subtitles 
            GROUP BY directory 
            ORDER BY subtitle_count DESC
        ''')
        dir_stats = cursor.fetchall()
        
        # 결과 출력
        print("=" * 80)
        print("🎬 미디어 자막 인덱스 시스템 - 데이터베이스 현황")
        print("=" * 80)
        print(f"📊 총 자막 엔트리: {total_subtitles:,}개")
        print(f"📁 총 미디어 파일: {total_files:,}개")
        print(f"🗂️  총 디렉토리: {total_dirs}개")
        
        print(f"\n🌐 언어별 분포:")
        for lang, count in lang_stats:
            lang_name = "영어" if lang == 'en' else "한글" if lang == 'ko' else lang
            percentage = (count / total_subtitles) * 100
            print(f"   {lang_name}: {count:,}개 ({percentage:.1f}%)")
        
        print(f"\n📁 디렉토리별 현황 (상위 10개):")
        for directory, sub_count, file_count in dir_stats[:10]:
            dir_name = Path(directory).name
            avg_subs = sub_count // file_count if file_count > 0 else 0
            print(f"   {dir_name}: {file_count}개 파일, {sub_count:,}개 자막 (평균 {avg_subs}개/파일)")
        
        if len(dir_stats) > 10:
            print(f"   ... 기타 {len(dir_stats) - 10}개 디렉토리")
        
        # 데이터베이스 크기
        db_size = Path(self.db_path).stat().st_size / (1024 * 1024)  # MB
        print(f"\n💾 데이터베이스 크기: {db_size:.1f} MB")
        
        conn.close()
        return True
    
    def main_menu(self):
        """메인 메뉴"""
        if not self.show_database_stats():
            return
        
        print("\n" + "=" * 80)
        print("🎮 사용 가능한 기능:")
        print("=" * 80)
        print("1️⃣  search  - 대화형 자막 검색 (텍스트만)")
        print("2️⃣  play    - 검색 후 비디오 재생")
        print("3️⃣  browse  - 디렉토리별 미디어 탐색")
        print("4️⃣  stats   - 데이터베이스 통계 다시 보기")
        print("5️⃣  reindex - 미디어 파일 재인덱싱")
        print("0️⃣  quit    - 종료")
        print("-" * 80)
        
        while True:
            try:
                choice = input("\n🎯 기능을 선택하세요 (1-5, 0=종료): ").strip()
                
                if choice == '0' or choice.lower() in ['quit', 'exit', 'q']:
                    print("👋 시스템을 종료합니다.")
                    break
                
                elif choice == '1' or choice.lower() == 'search':
                    print("\n🔍 대화형 검색 모드 시작...")
                    self.searcher.interactive_search()
                
                elif choice == '2' or choice.lower() == 'play':
                    print("\n🎬 비디오 플레이어 모드 시작...")
                    self.player.main()
                
                elif choice == '3' or choice.lower() == 'browse':
                    print("\n📁 디렉토리 탐색 모드...")
                    self.player.browse_by_directory()
                
                elif choice == '4' or choice.lower() == 'stats':
                    self.show_database_stats()
                
                elif choice == '5' or choice.lower() == 'reindex':
                    self.reindex_media()
                
                else:
                    print("❌ 잘못된 선택입니다. 0-5 사이의 숫자를 입력하세요.")
            
            except KeyboardInterrupt:
                print("\n👋 시스템을 종료합니다.")
                break
            except Exception as e:
                print(f"❌ 오류 발생: {e}")
    
    def reindex_media(self):
        """미디어 재인덱싱"""
        print("🔄 미디어 파일 재인덱싱...")
        print("⚠️  주의: 기존 데이터베이스가 백업되고 새로 생성됩니다.")
        
        confirm = input("계속하시겠습니까? (y/N): ").strip().lower()
        if confirm != 'y':
            print("❌ 재인덱싱이 취소되었습니다.")
            return
        
        try:
            # 기존 DB 백업
            if Path(self.db_path).exists():
                backup_path = f"{self.db_path}.backup"
                Path(self.db_path).rename(backup_path)
                print(f"✅ 기존 데이터베이스가 {backup_path}로 백업되었습니다.")
            
            # 인덱서 실행
            from working_indexer import WorkingIndexer
            indexer = WorkingIndexer()
            indexer.index_all_directories()
            
            print("✅ 재인덱싱이 완료되었습니다!")
            
        except Exception as e:
            print(f"❌ 재인덱싱 중 오류 발생: {e}")

def main():
    """메인 함수"""
    try:
        system = MediaIndexSystem()
        system.main_menu()
    except KeyboardInterrupt:
        print("\n👋 프로그램을 종료합니다.")
    except Exception as e:
        print(f"❌ 시스템 오류: {e}")

if __name__ == "__main__":
    main()
