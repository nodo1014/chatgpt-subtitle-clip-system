#!/usr/bin/env python3

import sqlite3
import json
import os
from pathlib import Path

def convert_db_to_json():
    """SQLite DB에서 데이터를 추출하여 JSON으로 변환"""
    
    db_path = 'working_subtitles.db'
    output_path = 'theme-search/public/subtitles_sample.json'
    
    if not os.path.exists(db_path):
        print('❌ DB 파일을 찾을 수 없습니다.')
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 샘플 데이터 추출 (전체 데이터는 너무 클 수 있음)
        print('📊 데이터베이스에서 샘플 데이터 추출 중...')
        cursor.execute('''
            SELECT media_file, text, start_time, end_time, language, directory
            FROM subtitles 
            WHERE language = 'en' AND length(text) > 10
            LIMIT 10000
        ''')
        
        results = cursor.fetchall()
        
        # JSON 형태로 변환
        data = []
        for row in results:
            # 파일명만 추출
            media_file = Path(row[0]).name if row[0] else ''
            directory = Path(row[5]).name if row[5] else ''
            
            data.append({
                'media_file': media_file,
                'text': row[1],
                'start_time': row[2],
                'end_time': row[3],
                'language': row[4],
                'directory': directory
            })
        
        # JSON 파일로 저장
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f'✅ {len(data)}개 자막 데이터를 JSON으로 변환 완료')
        print(f'📁 저장 위치: {output_path}')
        
        conn.close()
        
    except Exception as e:
        print(f'❌ 변환 중 오류 발생: {e}')

if __name__ == "__main__":
    convert_db_to_json() 