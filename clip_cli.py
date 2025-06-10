#!/usr/bin/env python3
"""
CLI 클립 매니저
수동으로 클립 요청을 처리하는 명령행 도구

사용법:
  python clip_cli.py list               # 대기 중인 클립 목록
  python clip_cli.py create <clip_id>   # 특정 클립 생성
  python clip_cli.py create-all         # 모든 대기 중인 클립 생성
  python clip_cli.py status             # 클립 상태 확인
"""

import sys
import os
import argparse
from pathlib import Path

# 현재 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'indexer_v2'))

from indexer_v2.clip_manager import ClipManager

def main():
    parser = argparse.ArgumentParser(description='클립 매니저 CLI')
    parser.add_argument('command', choices=['list', 'create', 'create-all', 'status', 'clear'],
                       help='실행할 명령')
    parser.add_argument('clip_id', nargs='?', help='클립 ID (create 명령시 필요)')
    parser.add_argument('--db', default='indexer_v1/working_subtitles.db', 
                       help='데이터베이스 경로 (기본값: indexer_v1/working_subtitles.db)')
    
    args = parser.parse_args()
    
    # 클립 매니저 초기화
    try:
        clip_manager = ClipManager(args.db)
        print(f"✅ 클립 매니저 초기화 완료: {args.db}")
    except Exception as e:
        print(f"❌ 클립 매니저 초기화 실패: {e}")
        return
    
    if args.command == 'list':
        list_pending_clips(clip_manager)
    
    elif args.command == 'create':
        if not args.clip_id:
            print("❌ 클립 ID가 필요합니다: python clip_cli.py create <clip_id>")
            return
        create_single_clip(clip_manager, args.clip_id)
    
    elif args.command == 'create-all':
        create_all_clips(clip_manager)
    
    elif args.command == 'status':
        show_status(clip_manager)
    
    elif args.command == 'clear':
        clear_failed_clips(clip_manager)

def list_pending_clips(clip_manager):
    """대기 중인 클립 목록 표시"""
    print("\n📋 대기 중인 클립 요청:")
    print("=" * 80)
    
    clips = clip_manager.get_pending_clips()
    
    if not clips:
        print("🎉 대기 중인 클립 요청이 없습니다!")
        return
    
    for i, clip in enumerate(clips, 1):
        print(f"\n{i}. 클립 ID: {clip['id'][:8]}...")
        print(f"   문장: \"{clip['sentence'][:60]}{'...' if len(clip['sentence']) > 60 else ''}\"")
        print(f"   파일: {clip['media_file']}")
        print(f"   시간: {clip['start_time']} → {clip['end_time']}")
        print(f"   요청: {clip['created_at']}")
    
    print(f"\n📊 총 {len(clips)}개의 클립 요청이 대기 중입니다.")
    print("\n💡 클립 생성 명령:")
    print("   python clip_cli.py create <clip_id>     # 개별 생성")
    print("   python clip_cli.py create-all           # 전체 생성")

def create_single_clip(clip_manager, clip_id):
    """단일 클립 생성"""
    print(f"\n🎬 클립 생성 시작: {clip_id[:8]}...")
    
    try:
        result = clip_manager.manual_clip_creation(clip_id)
        
        if result['success']:
            print(f"✅ 클립 생성 완료!")
            print(f"📁 파일: {result['output_file']}")
            print(f"💬 {result['message']}")
        else:
            print(f"❌ 클립 생성 실패: {result['error']}")
    
    except Exception as e:
        print(f"❌ 오류 발생: {e}")

def create_all_clips(clip_manager):
    """모든 대기 중인 클립 생성"""
    clips = clip_manager.get_pending_clips()
    
    if not clips:
        print("🎉 대기 중인 클립이 없습니다!")
        return
    
    print(f"\n🎬 {len(clips)}개 클립 일괄 생성 시작...")
    print("=" * 50)
    
    success_count = 0
    fail_count = 0
    
    for i, clip in enumerate(clips, 1):
        print(f"\n[{i}/{len(clips)}] 처리 중: {clip['sentence'][:40]}...")
        
        try:
            result = clip_manager.manual_clip_creation(clip['id'])
            
            if result['success']:
                print(f"✅ 성공: {clip['id'][:8]}")
                success_count += 1
            else:
                print(f"❌ 실패: {result['error']}")
                fail_count += 1
        
        except Exception as e:
            print(f"❌ 오류: {e}")
            fail_count += 1
    
    print(f"\n📊 완료 요약:")
    print(f"   ✅ 성공: {success_count}개")
    print(f"   ❌ 실패: {fail_count}개")

def show_status(clip_manager):
    """클립 상태 요약"""
    import sqlite3
    
    conn = sqlite3.connect(clip_manager.db_path)
    cursor = conn.cursor()
    
    cursor.execute('SELECT status, COUNT(*) FROM clip_requests GROUP BY status')
    status_counts = dict(cursor.fetchall())
    
    cursor.execute('SELECT COUNT(*) FROM clip_requests')
    total = cursor.fetchone()[0]
    
    conn.close()
    
    print("\n📊 클립 상태 요약:")
    print("=" * 30)
    print(f"⏳ 대기 중: {status_counts.get('pending', 0)}개")
    print(f"🔄 처리 중: {status_counts.get('processing', 0)}개")
    print(f"✅ 완료: {status_counts.get('completed', 0)}개")
    print(f"❌ 실패: {status_counts.get('failed', 0)}개")
    print(f"📈 전체: {total}개")
    
    # 클립 폴더 정보
    clips_dir = Path("indexer_v2/clips")
    if clips_dir.exists():
        clip_files = list(clips_dir.glob("*.mp4"))
        print(f"📁 생성된 파일: {len(clip_files)}개")
        
        total_size = sum(f.stat().st_size for f in clip_files)
        print(f"💾 총 용량: {total_size / (1024*1024):.1f}MB")

def clear_failed_clips(clip_manager):
    """실패한 클립 요청 정리"""
    import sqlite3
    
    conn = sqlite3.connect(clip_manager.db_path)
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM clip_requests WHERE status = "failed"')
    failed_count = cursor.fetchone()[0]
    
    if failed_count == 0:
        print("🎉 정리할 실패한 클립이 없습니다!")
        conn.close()
        return
    
    confirm = input(f"❓ {failed_count}개의 실패한 클립 요청을 삭제하시겠습니까? (y/N): ")
    
    if confirm.lower() == 'y':
        cursor.execute('DELETE FROM clip_requests WHERE status = "failed"')
        conn.commit()
        print(f"✅ {failed_count}개의 실패한 클립 요청을 삭제했습니다.")
    else:
        print("❌ 취소되었습니다.")
    
    conn.close()

if __name__ == '__main__':
    print("🎬 클립 매니저 CLI v1.0")
    print("=" * 40)
    
    main()
