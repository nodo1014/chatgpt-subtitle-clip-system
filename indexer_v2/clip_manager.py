#!/usr/bin/env python3

import sqlite3
import subprocess
import os
import json
import uuid
from datetime import datetime
from pathlib import Path
import tempfile

class ClipManager:
    def __init__(self, db_path="working_subtitles.db"):
        self.db_path = db_path
        self.setup_clip_directories()
        self.init_clip_db()
    
    def setup_clip_directories(self):
        """클립 저장 디렉토리 구조 설정"""
        self.base_clips_dir = Path("clips")
        self.single_clips_dir = self.base_clips_dir / "single"
        self.batch_clips_dir = self.base_clips_dir / "batch" 
        self.temp_clips_dir = self.base_clips_dir / "temp"
        self.metadata_dir = self.base_clips_dir / "metadata"
        
        # 디렉토리 생성
        for directory in [self.single_clips_dir, self.batch_clips_dir, 
                         self.temp_clips_dir, self.metadata_dir]:
            directory.mkdir(parents=True, exist_ok=True)
        
        print(f"📁 클립 디렉토리 구조:")
        print(f"   📂 {self.single_clips_dir}")
        print(f"   📂 {self.batch_clips_dir}")
        print(f"   📂 {self.temp_clips_dir}")
        print(f"   📂 {self.metadata_dir}")
    
    def get_clip_output_path(self, clip_type, clip_id, sentence, project_name=None):
        """클립 타입에 따른 출력 경로 결정"""
        # 안전한 파일명 생성
        safe_sentence = "".join(c for c in sentence[:30] if c.isalnum() or c in (' ', '-', '_')).strip().replace(' ', '_')
        
        if clip_type == 'single':
            filename = f"{clip_id}_{safe_sentence}.mp4"
            return self.single_clips_dir / filename
        
        elif clip_type == 'batch':
            # 프로젝트별 서브디렉토리 생성
            if project_name:
                safe_project = "".join(c for c in project_name[:20] if c.isalnum() or c in (' ', '-', '_')).strip().replace(' ', '_')
                project_dir = self.batch_clips_dir / safe_project
                project_dir.mkdir(exist_ok=True)
                filename = f"{clip_id}_{safe_sentence}.mp4"
                return project_dir / filename
            else:
                filename = f"{clip_id}_{safe_sentence}.mp4"
                return self.batch_clips_dir / filename
        
        else:
            filename = f"{clip_id}_{safe_sentence}.mp4"
            return self.temp_clips_dir / filename
    
    def init_clip_db(self):
        """클립 요청 테이블 초기화"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 클립 프로젝트 테이블
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS clip_projects (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                type TEXT DEFAULT 'single',  -- 'single', 'batch', 'theme'
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'active'  -- 'active', 'completed', 'archived'
            )
        ''')
        
        # 개별 클립 요청 테이블
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS clip_requests (
                id TEXT PRIMARY KEY,
                project_id TEXT,
                sentence TEXT NOT NULL,
                media_file TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                clip_type TEXT DEFAULT 'single',  -- 'single', 'batch'
                priority INTEGER DEFAULT 5,      -- 1(높음) ~ 10(낮음)
                padding_seconds REAL DEFAULT 2.0,
                status TEXT DEFAULT 'pending',   -- 'pending', 'processing', 'completed', 'failed'
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                completed_at TEXT,
                output_file TEXT,
                file_size INTEGER,
                duration_seconds REAL,
                error_message TEXT,
                FOREIGN KEY (project_id) REFERENCES clip_projects(id)
            )
        ''')
        
        # 클립 태그 테이블
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS clip_tags (
                clip_id TEXT,
                tag TEXT,
                PRIMARY KEY (clip_id, tag),
                FOREIGN KEY (clip_id) REFERENCES clip_requests(id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def request_single_clip(self, sentence, media_file, start_time, end_time, tags=None, priority=5):
        """단일 문장 클립 요청"""
        clip_id = str(uuid.uuid4())
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO clip_requests 
            (id, sentence, media_file, start_time, end_time, clip_type, priority, status)
            VALUES (?, ?, ?, ?, ?, 'single', ?, 'pending')
        ''', (clip_id, sentence, media_file, start_time, end_time, priority))
        
        # 태그 추가
        if tags:
            for tag in tags:
                cursor.execute('''
                    INSERT INTO clip_tags (clip_id, tag) VALUES (?, ?)
                ''', (clip_id, tag.strip().lower()))
        
        conn.commit()
        conn.close()
        
        return {
            'success': True,
            'clip_id': clip_id,
            'type': 'single',
            'message': '단일 클립 요청이 등록되었습니다.'
        }
    
    def request_batch_clips(self, sentences_data, project_name, project_description=""):
        """배치(다중) 클립 요청 생성"""
        project_id = str(uuid.uuid4())
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 프로젝트 생성
        cursor.execute('''
            INSERT INTO clip_projects (id, name, description, type)
            VALUES (?, ?, ?, 'batch')
        ''', (project_id, project_name, project_description))
        
        clip_ids = []
        
        # 개별 클립 요청들 생성
        for i, data in enumerate(sentences_data):
            clip_id = str(uuid.uuid4())
            clip_ids.append(clip_id)
            
            cursor.execute('''
                INSERT INTO clip_requests 
                (id, project_id, sentence, media_file, start_time, end_time, clip_type, priority, status)
                VALUES (?, ?, ?, ?, ?, ?, 'batch', ?, 'pending')
            ''', (clip_id, project_id, data['sentence'], data['media_file'], 
                  data['start_time'], data['end_time'], data.get('priority', 5)))
            
            # 태그 추가
            if 'tags' in data:
                for tag in data['tags']:
                    cursor.execute('''
                        INSERT INTO clip_tags (clip_id, tag) VALUES (?, ?)
                    ''', (clip_id, tag.strip().lower()))
        
        conn.commit()
        conn.close()
        
        return {
            'success': True,
            'project_id': project_id,
            'clip_ids': clip_ids,
            'total_clips': len(sentences_data),
            'type': 'batch',
            'message': f'{len(sentences_data)}개의 배치 클립 요청이 등록되었습니다.'
        }
    
    def get_pending_clips(self):
        """대기 중인 클립 요청 목록"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT cr.id, cr.sentence, cr.media_file, cr.start_time, cr.end_time, 
                   cr.created_at, cr.clip_type, cr.priority, cp.name as project_name
            FROM clip_requests cr
            LEFT JOIN clip_projects cp ON cr.project_id = cp.id
            WHERE cr.status = 'pending'
            ORDER BY cr.priority ASC, cr.created_at ASC
        ''')
        
        results = cursor.fetchall()
        conn.close()
        
        return [
            {
                'id': row[0],
                'sentence': row[1], 
                'media_file': row[2],
                'start_time': row[3],
                'end_time': row[4],
                'created_at': row[5],
                'clip_type': row[6],
                'priority': row[7],
                'project_name': row[8]
            }
            for row in results
        ]
    
    def get_projects(self):
        """프로젝트 목록 조회"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, name, description, type, status, created_at
            FROM clip_projects
            ORDER BY created_at DESC
        ''')
        
        results = cursor.fetchall()
        conn.close()
        
        return [
            {
                'id': row[0],
                'name': row[1],
                'description': row[2],
                'type': row[3],
                'status': row[4],
                'created_at': row[5]
            }
            for row in results
        ]
    
    def get_completed_clips(self):
        """완료된 클립 목록"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, sentence, output_file, file_size, duration_seconds, completed_at
            FROM clip_requests 
            WHERE status = 'completed'
            ORDER BY completed_at DESC
        ''')
        
        results = cursor.fetchall()
        conn.close()
        
        return [
            {
                'id': row[0],
                'sentence': row[1],
                'output_file': row[2],
                'file_size': row[3] or 0,
                'duration_seconds': row[4] or 0,
                'completed_at': row[5]
            }
            for row in results
        ]
    
    def format_time_to_seconds(self, time_str):
        """SRT 시간 형식을 초로 변환"""
        try:
            time_str = time_str.replace(',', '.')
            parts = time_str.split(':')
            hours = int(parts[0])
            minutes = int(parts[1])
            seconds = float(parts[2])
            return hours * 3600 + minutes * 60 + seconds
        except:
            return 0
    
    def manual_clip_creation(self, clip_id, padding_seconds=2):
        """수동 클립 생성 (관리자가 호출)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 클립 요청 정보 가져오기
        cursor.execute('''
            SELECT sentence, media_file, start_time, end_time
            FROM clip_requests 
            WHERE id = ? AND status = 'pending'
        ''', (clip_id,))
        
        result = cursor.fetchone()
        if not result:
            return {'success': False, 'error': '클립 요청을 찾을 수 없습니다.'}
        
        sentence, media_file, start_time, end_time = result
        
        # 상태 업데이트
        cursor.execute('''
            UPDATE clip_requests 
            SET status = 'processing' 
            WHERE id = ?
        ''', (clip_id,))
        conn.commit()
        
        try:
            # 실제 비디오 파일 경로 찾기
            video_path = self.find_video_file(media_file)
            if not video_path:
                raise Exception(f"비디오 파일을 찾을 수 없습니다: {media_file}")
            
            # 시간 변환
            start_sec = self.format_time_to_seconds(start_time) - padding_seconds
            end_sec = self.format_time_to_seconds(end_time) + padding_seconds
            duration = end_sec - start_sec
            
            # 출력 파일명
            output_path = self.get_clip_output_path('single', clip_id, sentence)
            
            # FFmpeg 명령어 (간단한 버전)
            cmd = [
                'ffmpeg', '-y',
                '-i', str(video_path),
                '-ss', str(start_sec),
                '-t', str(duration),
                '-c:v', 'libx264',
                '-c:a', 'aac',
                '-avoid_negative_ts', 'make_zero',
                str(output_path)
            ]
            
            # 실행 (실제로는 백그라운드에서 실행하는 것이 좋음)
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                # 성공
                cursor.execute('''
                    UPDATE clip_requests 
                    SET status = 'completed', completed_at = CURRENT_TIMESTAMP, output_file = ?
                    WHERE id = ?
                ''', (str(output_path), clip_id))
                
                conn.commit()
                conn.close()
                
                return {
                    'success': True,
                    'output_file': str(output_path),
                    'message': '클립이 성공적으로 생성되었습니다.'
                }
            else:
                raise Exception(f"FFmpeg 오류: {result.stderr}")
                
        except Exception as e:
            # 실패
            cursor.execute('''
                UPDATE clip_requests 
                SET status = 'failed', error_message = ?
                WHERE id = ?
            ''', (str(e), clip_id))
            
            conn.commit()
            conn.close()
            
            return {
                'success': False,
                'error': str(e)
            }
    
    def find_video_file(self, media_file):
        """자막 파일명으로부터 비디오 파일 찾기"""
        # 자막 파일명에서 확장자 제거하고 비디오 확장자로 변경
        base_name = Path(media_file).stem
        video_extensions = ['.mp4', '.mkv', '.avi', '.mov', '.wmv', '.m4v']
        
        # 여러 경로에서 찾기
        search_paths = [
            Path("/mnt/qnap/media_eng"),  # 실제 미디어 경로
            Path("../media"),  # 상대 경로
            Path("."),  # 현재 디렉토리
            Path("indexer_v1"),  # v1 디렉토리
            Path("indexer_v2")   # v2 디렉토리
        ]
        
        print(f"🔍 비디오 파일 검색: {base_name}")
        
        for search_path in search_paths:
            if search_path.exists():
                print(f"   📁 경로 확인: {search_path}")
                
                # 직접 파일 찾기
                for ext in video_extensions:
                    video_file = search_path / f"{base_name}{ext}"
                    if video_file.exists():
                        print(f"   ✅ 파일 발견: {video_file}")
                        return video_file
                
                # 하위 디렉토리에서도 찾기
                for subdir in search_path.iterdir():
                    if subdir.is_dir():
                        for ext in video_extensions:
                            video_file = subdir / f"{base_name}{ext}"
                            if video_file.exists():
                                print(f"   ✅ 파일 발견: {video_file}")
                                return video_file
        
        print(f"   ❌ 비디오 파일을 찾을 수 없음: {base_name}")
        return None
    
    def get_clip_stats(self):
        """클립 통계 조회"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 상태별 클립 개수
        cursor.execute('''
            SELECT status, COUNT(*) as count
            FROM clip_requests
            GROUP BY status
        ''')
        status_counts = dict(cursor.fetchall())
        
        # 총 클립 개수
        cursor.execute('SELECT COUNT(*) FROM clip_requests')
        total_clips = cursor.fetchone()[0]
        
        # 오늘 생성된 클립 개수
        cursor.execute('''
            SELECT COUNT(*) FROM clip_requests
            WHERE date(created_at) = date('now')
        ''')
        today_clips = cursor.fetchone()[0]
        
        # 평균 클립 길이
        cursor.execute('''
            SELECT AVG(duration_seconds) FROM clip_requests
            WHERE status = 'completed' AND duration_seconds IS NOT NULL
        ''')
        avg_duration = cursor.fetchone()[0] or 0
        
        # 총 파일 크기
        cursor.execute('''
            SELECT SUM(file_size) FROM clip_requests
            WHERE status = 'completed' AND file_size IS NOT NULL
        ''')
        total_size = cursor.fetchone()[0] or 0
        
        conn.close()
        
        return {
            'total_clips': total_clips,
            'today_clips': today_clips,
            'status_counts': status_counts,
            'average_duration': round(avg_duration, 2),
            'total_size_mb': round(total_size / (1024 * 1024), 2) if total_size else 0
        }

    def update_clip_status(self, clip_id, status, error_message=None):
        """클립 상태 업데이트"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if status == 'completed':
            cursor.execute('''
                UPDATE clip_requests 
                SET status = ?, completed_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (status, clip_id))
        elif status == 'failed' and error_message:
            cursor.execute('''
                UPDATE clip_requests 
                SET status = ?, error_message = ?
                WHERE id = ?
            ''', (status, error_message, clip_id))
        else:
            cursor.execute('''
                UPDATE clip_requests 
                SET status = ?
                WHERE id = ?
            ''', (status, clip_id))
        
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        
        return success

# 사용 예시
if __name__ == "__main__":
    clip_manager = ClipManager()
    
    # 대기 중인 클립 목록 보기
    pending = clip_manager.get_pending_clips()
    print(f"대기 중인 클립: {len(pending)}개")
    
    for clip in pending:
        print(f"- {clip['sentence'][:50]}...")
