#!/usr/bin/env python3
"""
자동 클립 처리기
주기적으로 대기 중인 클립 요청을 자동으로 처리합니다.
"""

import time
import sys
import os
from pathlib import Path

# 현재 디렉토리를 Python 경로에 추가
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'indexer_v2'))

from indexer_v2.clip_manager import ClipManager

class AutoClipProcessor:
    def __init__(self, db_path="indexer_v1/working_subtitles.db", check_interval=30):
        self.db_path = db_path
        self.check_interval = check_interval  # 초 단위
        self.clip_manager = ClipManager(self.db_path)
        
    def process_pending_clips(self):
        """대기 중인 모든 클립 처리"""
        clips = self.clip_manager.get_pending_clips()
        
        if not clips:
            print("📭 대기 중인 클립이 없습니다.")
            return
        
        print(f"🎬 {len(clips)}개 클립 자동 처리 시작...")
        
        success_count = 0
        fail_count = 0
        
        for clip in clips:
            try:
                print(f"   📝 처리 중: {clip['sentence'][:40]}...")
                result = self.clip_manager.manual_clip_creation(clip['id'])
                
                if result['success']:
                    print(f"   ✅ 성공: {clip['id'][:8]}")
                    success_count += 1
                else:
                    print(f"   ❌ 실패: {result['error']}")
                    fail_count += 1
                    
            except Exception as e:
                print(f"   🚨 오류: {e}")
                fail_count += 1
        
        if success_count > 0 or fail_count > 0:
            print(f"📊 처리 완료: ✅{success_count}개 성공, ❌{fail_count}개 실패")
    
    def run_continuous(self):
        """지속적인 모니터링 모드"""
        print(f"🔄 자동 클립 처리기 시작 (검사 간격: {self.check_interval}초)")
        print("   Ctrl+C로 중지할 수 있습니다.")
        
        try:
            while True:
                self.process_pending_clips()
                time.sleep(self.check_interval)
                
        except KeyboardInterrupt:
            print("\n🛑 자동 처리기가 중지되었습니다.")
    
    def run_once(self):
        """한 번만 실행"""
        print("🎬 자동 클립 처리기 (일회성 실행)")
        self.process_pending_clips()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='자동 클립 처리기')
    parser.add_argument('--mode', choices=['once', 'continuous'], default='once',
                       help='실행 모드 (once: 한 번만, continuous: 지속 모니터링)')
    parser.add_argument('--interval', type=int, default=30,
                       help='검사 간격 (초, continuous 모드용)')
    parser.add_argument('--db', default='indexer_v1/working_subtitles.db',
                       help='데이터베이스 경로')
    
    args = parser.parse_args()
    
    processor = AutoClipProcessor(args.db, args.interval)
    
    if args.mode == 'continuous':
        processor.run_continuous()
    else:
        processor.run_once()
