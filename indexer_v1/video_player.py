#!/usr/bin/env python3

import sqlite3
import subprocess
import sys
from pathlib import Path
import re

class VideoPlayer:
    def __init__(self, db_path="working_subtitles.db"):
        self.db_path = db_path
        
    def format_time_to_seconds(self, time_str):
        """SRT 시간 형식을 초로 변환 (00:02:30,500 -> 150.5)"""
        try:
            # 쉼표를 점으로 변경
            time_str = time_str.replace(',', '.')
            parts = time_str.split(':')
            hours = int(parts[0])
            minutes = int(parts[1])
            seconds = float(parts[2])
            return hours * 3600 + minutes * 60 + seconds
        except:
            return 0
    
    def search_and_play(self, search_query, language=None):
        """검색어로 자막을 찾고 해당 시점에서 비디오 재생"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # FTS 검색
        if language:
            cursor.execute('''
                SELECT s.media_file, s.start_time, s.end_time, s.text, s.directory
                FROM subtitles_fts fts
                JOIN subtitles s ON s.id = fts.rowid
                WHERE fts.text MATCH ? AND s.language = ?
                ORDER BY rank
                LIMIT 10
            ''', (search_query, language))
        else:
            cursor.execute('''
                SELECT s.media_file, s.start_time, s.end_time, s.text, s.directory
                FROM subtitles_fts fts
                JOIN subtitles s ON s.id = fts.rowid
                WHERE fts.text MATCH ?
                ORDER BY rank
                LIMIT 10
            ''', (search_query,))
        
        results = cursor.fetchall()
        conn.close()
        
        if not results:
            print(f"❌ '{search_query}' 검색 결과가 없습니다.")
            return
        
        print(f"🔍 '{search_query}' 검색 결과:")
        print("-" * 60)
        
        for i, result in enumerate(results, 1):
            media_file = Path(result[0]).name
            start_time = result[1]
            text = result[3][:100] + "..." if len(result[3]) > 100 else result[3]
            
            print(f"{i:2d}. {media_file}")
            print(f"    ⏰ {start_time}")
            print(f"    💬 {text}")
            print()
        
        try:
            choice = input("재생할 번호를 선택하세요 (1-10, Enter=첫번째): ").strip()
            if not choice:
                choice = "1"
            
            idx = int(choice) - 1
            if 0 <= idx < len(results):
                selected = results[idx]
                self.play_video_at_time(selected[0], selected[1])
            else:
                print("❌ 잘못된 번호입니다.")
                
        except ValueError:
            print("❌ 숫자를 입력해주세요.")
        except KeyboardInterrupt:
            print("\n취소되었습니다.")
    
    def play_video_at_time(self, video_path, start_time):
        """특정 시점에서 비디오 재생"""
        if not Path(video_path).exists():
            print(f"❌ 비디오 파일을 찾을 수 없습니다: {video_path}")
            return
        
        start_seconds = self.format_time_to_seconds(start_time)
        
        print(f"🎬 재생 시작: {Path(video_path).name}")
        print(f"⏰ 시작 시점: {start_time} ({start_seconds:.1f}초)")
        
        # VLC 플레이어로 재생 (설치되어 있는 경우)
        players = [
            ['vlc', '--start-time', str(int(start_seconds)), video_path],
            ['mpv', f'--start={start_seconds}', video_path],
            ['mplayer', '-ss', str(int(start_seconds)), video_path],
        ]
        
        for player_cmd in players:
            try:
                print(f"🎥 {player_cmd[0]}로 재생 중...")
                subprocess.run(player_cmd, check=True)
                return
            except (subprocess.CalledProcessError, FileNotFoundError):
                continue
        
        print("❌ 비디오 플레이어를 찾을 수 없습니다.")
        print("💡 VLC, MPV, 또는 MPlayer를 설치해주세요:")
        print("   sudo apt install vlc")
        print("   sudo apt install mpv")
        print("   sudo apt install mplayer")
    
    def browse_by_directory(self):
        """디렉토리별로 미디어 탐색"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 디렉토리 목록
        cursor.execute('''
            SELECT directory, COUNT(*) as subtitle_count, COUNT(DISTINCT media_file) as file_count
            FROM subtitles 
            GROUP BY directory 
            ORDER BY directory
        ''')
        
        directories = cursor.fetchall()
        
        print("📁 미디어 디렉토리:")
        print("-" * 60)
        
        for i, (directory, sub_count, file_count) in enumerate(directories, 1):
            dir_name = Path(directory).name
            print(f"{i:2d}. {dir_name} ({file_count}개 파일, {sub_count:,}개 자막)")
        
        try:
            choice = input(f"\n디렉토리를 선택하세요 (1-{len(directories)}): ").strip()
            if not choice:
                return
            
            idx = int(choice) - 1
            if 0 <= idx < len(directories):
                selected_dir = directories[idx][0]
                self.browse_files_in_directory(selected_dir)
            else:
                print("❌ 잘못된 번호입니다.")
                
        except ValueError:
            print("❌ 숫자를 입력해주세요.")
        except KeyboardInterrupt:
            print("\n취소되었습니다.")
        
        conn.close()
    
    def browse_files_in_directory(self, directory):
        """특정 디렉토리의 파일들 탐색"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT media_file, COUNT(*) as subtitle_count
            FROM subtitles 
            WHERE directory = ?
            GROUP BY media_file 
            ORDER BY media_file
        ''', (directory,))
        
        files = cursor.fetchall()
        
        print(f"\n📺 {Path(directory).name} 디렉토리의 파일들:")
        print("-" * 60)
        
        for i, (media_file, sub_count) in enumerate(files, 1):
            file_name = Path(media_file).name
            print(f"{i:2d}. {file_name} ({sub_count:,}개 자막)")
        
        try:
            choice = input(f"\n파일을 선택하세요 (1-{len(files)}): ").strip()
            if not choice:
                return
            
            idx = int(choice) - 1
            if 0 <= idx < len(files):
                selected_file = files[idx][0]
                self.play_video_at_time(selected_file, "00:00:00,000")
            else:
                print("❌ 잘못된 번호입니다.")
                
        except ValueError:
            print("❌ 숫자를 입력해주세요.")
        except KeyboardInterrupt:
            print("\n취소되었습니다.")
        
        conn.close()

def main():
    player = VideoPlayer()
    
    print("=" * 60)
    print("🎬 미디어 플레이어 & 검색")
    print("=" * 60)
    print("1. search <검색어> - 자막에서 검색 후 재생")
    print("2. search en:<검색어> - 영어 자막만 검색")
    print("3. search ko:<검색어> - 한글 자막만 검색")
    print("4. browse - 디렉토리별 탐색")
    print("5. quit - 종료")
    print("-" * 60)
    
    while True:
        try:
            command = input("\n🎮 명령어를 입력하세요: ").strip()
            
            if command.lower() in ['quit', 'exit', 'q']:
                print("👋 플레이어를 종료합니다.")
                break
            
            elif command.startswith('search '):
                query = command[7:].strip()
                language = None
                
                if query.startswith('en:'):
                    language = 'en'
                    query = query[3:].strip()
                elif query.startswith('ko:'):
                    language = 'ko'
                    query = query[3:].strip()
                
                if query:
                    player.search_and_play(query, language)
                else:
                    print("❌ 검색어를 입력해주세요.")
            
            elif command.lower() == 'browse':
                player.browse_by_directory()
            
            elif command == '':
                continue
                
            else:
                print("❌ 알 수 없는 명령어입니다.")
                print("💡 'search <검색어>' 또는 'browse'를 사용하세요.")
        
        except KeyboardInterrupt:
            print("\n👋 플레이어를 종료합니다.")
            break
        except Exception as e:
            print(f"❌ 오류 발생: {e}")

if __name__ == "__main__":
    main()
