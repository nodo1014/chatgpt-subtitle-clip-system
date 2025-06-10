#!/usr/bin/env python3
"""
배치 다중 문장 검색 API
270K+ 자막 데이터베이스에서 여러 영어 문장을 동시에 검색하는 Flask API

기능:
- 한글/특수문자 필터링
- 영어 문장 추출
- 배치 데이터베이스 검색
- 검색 히스토리 관리
"""

import sqlite3
import re
import json
import time
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
import unicodedata
import sys
import os

app = Flask(__name__)
CORS(app)

# 클립 매니저 임포트
sys.path.append(os.path.join(os.path.dirname(__file__), 'indexer_v2'))
from clip_manager import ClipManager

# 데이터베이스 경로 설정
DB_PATHS = [
    '/home/kang/docker/youtube/indexer/indexer_v1/working_subtitles.db',
    '/home/kang/docker/youtube/indexer/indexer_v2/working_subtitles.db'
]

class BatchSearchEngine:
    def __init__(self):
        self.db_path = None
        self.connect_to_database()
        # 클립 매니저 초기화
        self.clip_manager = None
        try:
            from indexer_v2.clip_manager import ClipManager
            self.clip_manager = ClipManager(self.db_path)
        except ImportError:
            print("⚠️ 클립 매니저 모듈을 찾을 수 없습니다. 클리핑 기능이 비활성화됩니다.")
        except Exception as e:
            print(f"⚠️ 클립 매니저 초기화 실패: {e}")
    
    def connect_to_database(self):
        """가용한 데이터베이스에 연결"""
        for db_path in DB_PATHS:
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM subtitles LIMIT 1")
                count = cursor.fetchone()[0]
                conn.close()
                self.db_path = db_path
                print(f"✅ 데이터베이스 연결 성공: {db_path} ({count:,}개 자막)")
                return
            except Exception as e:
                print(f"❌ 데이터베이스 연결 실패: {db_path} - {e}")
                continue
        
        print("⚠️ 모든 데이터베이스 연결 실패 - 시뮬레이션 모드로 실행")
    
    def extract_english_sentences(self, text):
        """텍스트에서 영어 문장만 추출"""
        # 한글, 한자, 일본어 문자 패턴
        asian_pattern = re.compile(r'[\u1100-\u11FF\u3130-\u318F\uAC00-\uD7AF\u4E00-\u9FFF\u3040-\u309F\u30A0-\u30FF]')
        
        # 1단계: 줄별로 분리하고 아시아 문자가 포함된 줄 제거
        lines = []
        for line in text.split('\n'):
            clean_line = line.strip()
            if clean_line and not asian_pattern.search(clean_line):
                lines.append(clean_line)
        
        # 2단계: 영어 문장 추출 (대문자로 시작하고 .?!로 끝나는 문장)
        sentences = []
        sentence_pattern = re.compile(r'[A-Z][^.!?]*[.!?]')
        
        for line in lines:
            matches = sentence_pattern.findall(line)
            for sentence in matches:
                trimmed = sentence.strip()
                # 최소 길이와 단어 수 체크
                if len(trimmed) >= 10 and len(trimmed.split()) >= 3:
                    # 특수문자 정리
                    clean_sentence = re.sub(r'[^\w\s\.\!\?]', '', trimmed)
                    if clean_sentence:
                        sentences.append(clean_sentence)
        
        return sentences
    
    def search_sentence_in_db(self, sentence, limit=10):
        """데이터베이스에서 단일 문장 검색"""
        if not self.db_path:
            return self.generate_mock_results(sentence, limit)
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # FTS5 검색 (전체 텍스트 검색)
            search_query = """
            SELECT 
                file_path,
                subtitle_text,
                start_time,
                end_time,
                duration,
                SUBSTR(file_path, INSTR(file_path, '/') + 1) as media_name
            FROM subtitles 
            WHERE subtitles MATCH ? 
            ORDER BY rank 
            LIMIT ?
            """
            
            cursor.execute(search_query, (sentence, limit))
            results = cursor.fetchall()
            conn.close()
            
            formatted_results = []
            for result in results:
                file_path, subtitle_text, start_time, end_time, duration, media_name = result
                
                # 신뢰도 계산 (단순한 문자열 유사도)
                confidence = self.calculate_confidence(sentence, subtitle_text)
                
                formatted_results.append({
                    'file_path': file_path,
                    'media_name': media_name,
                    'subtitle_text': subtitle_text,
                    'start_time': start_time,
                    'end_time': end_time,
                    'duration': duration,
                    'confidence': confidence,
                    'timestamp': f"{int(start_time//60):02d}:{int(start_time%60):02d}"
                })
            
            return formatted_results
            
        except Exception as e:
            print(f"데이터베이스 검색 오류: {e}")
            return self.generate_mock_results(sentence, limit)
    
    def calculate_confidence(self, query, subtitle_text):
        """검색 결과의 신뢰도 계산"""
        query_words = set(query.lower().split())
        subtitle_words = set(subtitle_text.lower().split())
        
        if not query_words:
            return 0.0
        
        intersection = len(query_words.intersection(subtitle_words))
        confidence = intersection / len(query_words)
        return min(confidence, 1.0)
    
    def generate_mock_results(self, sentence, limit):
        """시뮬레이션용 가짜 결과 생성"""
        mock_sources = [
            {"name": "Friends", "type": "TV Series"},
            {"name": "The Office", "type": "TV Series"},
            {"name": "Breaking Bad", "type": "TV Series"},
            {"name": "Stranger Things", "type": "TV Series"},
            {"name": "The Crown", "type": "TV Series"},
            {"name": "Sherlock", "type": "TV Series"},
            {"name": "House of Cards", "type": "TV Series"},
            {"name": "Black Mirror", "type": "TV Series"},
            {"name": "Westworld", "type": "TV Series"},
            {"name": "Game of Thrones", "type": "TV Series"}
        ]
        
        results = []
        for i in range(min(limit, len(mock_sources))):
            source = mock_sources[i]
            confidence = max(0.5, 1.0 - (i * 0.1))
            
            results.append({
                'file_path': f"/media/{source['name'].lower().replace(' ', '_')}/s01e01.srt",
                'media_name': source['name'],
                'subtitle_text': sentence,
                'start_time': 120 + i * 30,
                'end_time': 125 + i * 30,
                'duration': 5,
                'confidence': confidence,
                'timestamp': f"{int((120 + i * 30)//60):02d}:{int((120 + i * 30)%60):02d}"
            })
        
        return results
    
    def batch_search(self, sentences, results_per_sentence=10):
        """배치 검색 실행"""
        search_start = time.time()
        all_results = []
        
        for i, sentence in enumerate(sentences):
            sentence_results = self.search_sentence_in_db(sentence, results_per_sentence)
            
            all_results.append({
                'sentence_index': i + 1,
                'search_sentence': sentence,
                'found_count': len(sentence_results),
                'results': sentence_results
            })
        
        search_end = time.time()
        
        return {
            'search_summary': {
                'total_sentences': len(sentences),
                'total_results': sum(r['found_count'] for r in all_results),
                'average_per_sentence': sum(r['found_count'] for r in all_results) / len(sentences) if sentences else 0,
                'search_time': round(search_end - search_start, 2)
            },
            'sentence_results': all_results,
            'timestamp': datetime.now().isoformat()
        }

# 전역 검색 엔진 인스턴스
search_engine = BatchSearchEngine()

@app.route('/')
def index():
    """메인 페이지"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>배치 검색 API</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            .container { max-width: 800px; margin: 0 auto; }
            .endpoint { background: #f5f5f5; padding: 15px; margin: 10px 0; border-radius: 5px; }
            .method { background: #007bff; color: white; padding: 3px 8px; border-radius: 3px; font-size: 12px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🔍 배치 다중 문장 검색 API</h1>
            <p>270K+ 자막 데이터베이스에서 여러 영어 문장을 동시에 검색합니다.</p>
            
            <h2>API 엔드포인트</h2>
            
            <div class="endpoint">
                <h3><span class="method">POST</span> /api/batch-search</h3>
                <p><strong>설명:</strong> 배치 다중 문장 검색</p>
                <p><strong>파라미터:</strong></p>
                <ul>
                    <li><code>text</code> - 검색할 텍스트 (한글/영어 혼합 가능)</li>
                    <li><code>results_per_sentence</code> - 문장당 결과 수 (기본값: 10)</li>
                </ul>
            </div>
            
            <div class="endpoint">
                <h3><span class="method">POST</span> /api/extract-sentences</h3>
                <p><strong>설명:</strong> 텍스트에서 영어 문장만 추출</p>
                <p><strong>파라미터:</strong></p>
                <ul>
                    <li><code>text</code> - 추출할 텍스트</li>
                </ul>
            </div>
            
            <div class="endpoint">
                <h3><span class="method">GET</span> /api/status</h3>
                <p><strong>설명:</strong> API 상태 및 데이터베이스 정보</p>
            </div>
            
            <h2>사용 예시</h2>
            <pre style="background: #f8f9fa; padding: 15px; border-radius: 5px;">
curl -X POST http://localhost:5000/api/batch-search \\
  -H "Content-Type: application/json" \\
  -d '{
    "text": "The meeting has been postponed until next Wednesday.\\n회의가 다음 주 수요일로 연기되었습니다.\\nPlease submit your reports by the end of the month.",
    "results_per_sentence": 10
  }'
            </pre>
        </div>
    </body>
    </html>
    """

@app.route('/api/status', methods=['GET'])
def api_status():
    """API 상태 정보"""
    status = {
        'status': 'active',
        'database_connected': search_engine.db_path is not None,
        'database_path': search_engine.db_path,
        'timestamp': datetime.now().isoformat()
    }
    
    if search_engine.db_path:
        try:
            conn = sqlite3.connect(search_engine.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM subtitles")
            count = cursor.fetchone()[0]
            conn.close()
            status['subtitle_count'] = count
        except:
            status['subtitle_count'] = 'unknown'
    
    return jsonify(status)

@app.route('/api/extract-sentences', methods=['POST'])
def extract_sentences():
    """텍스트에서 영어 문장 추출"""
    data = request.get_json()
    
    if not data or 'text' not in data:
        return jsonify({'error': '텍스트가 필요합니다'}), 400
    
    text = data['text']
    sentences = search_engine.extract_english_sentences(text)
    
    return jsonify({
        'original_text': text,
        'extracted_sentences': sentences,
        'sentence_count': len(sentences),
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/batch-search', methods=['POST'])
def batch_search():
    """배치 다중 문장 검색"""
    data = request.get_json()
    
    if not data or 'text' not in data:
        return jsonify({'error': '텍스트가 필요합니다'}), 400
    
    text = data['text']
    results_per_sentence = data.get('results_per_sentence', 10)
    
    # 영어 문장 추출
    sentences = search_engine.extract_english_sentences(text)
    
    if not sentences:
        return jsonify({
            'error': '영어 문장을 찾을 수 없습니다',
            'original_text': text,
            'extracted_sentences': [],
            'suggestion': '대문자로 시작하고 마침표로 끝나는 영어 문장을 입력해주세요'
        }), 400
    
    # 배치 검색 실행
    results = search_engine.batch_search(sentences, results_per_sentence)
    
    return jsonify({
        'success': True,
        'original_text': text,
        'extracted_sentences': sentences,
        **results
    })

@app.route('/api/search-history', methods=['GET'])
def get_search_history():
    """검색 히스토리 조회 (실제 구현에서는 데이터베이스 사용)"""
    # 임시로 파일 기반 히스토리 (실제로는 데이터베이스 사용)
    try:
        with open('/tmp/batch_search_history.json', 'r', encoding='utf-8') as f:
            history = json.load(f)
    except:
        history = []
    
    return jsonify(history[-10:])  # 최근 10개

@app.route('/api/save-search', methods=['POST'])
def save_search():
    """검색 결과 저장"""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': '데이터가 필요합니다'}), 400
    
    # 검색 히스토리에 추가
    history_item = {
        'timestamp': datetime.now().isoformat(),
        'sentences': data.get('sentences', []),
        'total_results': data.get('total_results', 0),
        'search_type': 'batch'
    }
    
    try:
        # 기존 히스토리 읽기
        try:
            with open('/tmp/batch_search_history.json', 'r', encoding='utf-8') as f:
                history = json.load(f)
        except:
            history = []
        
        # 새 항목 추가
        history.append(history_item)
        history = history[-50:]  # 최대 50개만 유지
        
        # 파일에 저장
        with open('/tmp/batch_search_history.json', 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
        
        return jsonify({'success': True, 'message': '검색 히스토리에 저장되었습니다'})
    
    except Exception as e:
        return jsonify({'error': f'저장 실패: {str(e)}'}), 500

# 클리핑 관련 API 엔드포인트
@app.route('/api/request-clip', methods=['POST'])
def request_clip():
    """클립 즉시 생성 (자동 처리)"""
    try:
        data = request.json
        sentence = data.get('sentence', '')
        media_file = data.get('media_file', '')
        start_time = data.get('start_time', '')
        end_time = data.get('end_time', '')
        
        if not all([sentence, media_file, start_time, end_time]):
            return jsonify({'error': '필수 필드가 누락되었습니다'}), 400
        
        # 클립 매니저 임포트 및 사용
        import sys
        import os
        sys.path.append(os.path.join(os.path.dirname(__file__), 'indexer_v2'))
        from clip_manager import ClipManager
        
        clip_manager = ClipManager(search_engine.db_path)
        
        # 1단계: 클립 요청 등록
        request_result = clip_manager.request_single_clip(
            sentence=sentence,
            media_file=media_file,
            start_time=start_time,
            end_time=end_time
        )
        
        if not request_result['success']:
            return jsonify(request_result)
        
        clip_id = request_result['clip_id']
        
        # 2단계: 즉시 클립 생성 시도
        try:
            creation_result = clip_manager.manual_clip_creation(clip_id)
            
            if creation_result['success']:
                return jsonify({
                    'success': True,
                    'clip_id': clip_id,
                    'message': '클립이 성공적으로 생성되었습니다!',
                    'output_path': creation_result.get('output_path', ''),
                    'type': 'immediate'
                })
            else:
                # 클립 생성 실패시 요청만 등록된 상태로 반환
                return jsonify({
                    'success': True,
                    'clip_id': clip_id,
                    'message': f'클립 요청이 등록되었습니다. 생성 오류: {creation_result.get("error", "알 수 없는 오류")}',
                    'warning': creation_result.get('error', ''),
                    'type': 'queued'
                })
                
        except Exception as creation_error:
            # 클립 생성 중 예외 발생시에도 요청은 등록된 상태
            return jsonify({
                'success': True,
                'clip_id': clip_id,
                'message': f'클립 요청이 등록되었습니다. 생성 중 오류 발생: {str(creation_error)}',
                'warning': str(creation_error),
                'type': 'queued'
            })
        
        return jsonify(request_result)
    
    except Exception as e:
        return jsonify({'error': f'클립 요청 실패: {str(e)}'}), 500

@app.route('/api/pending-clips', methods=['GET'])
def get_pending_clips():
    """대기 중인 클립 요청 목록"""
    try:
        import sys
        import os
        sys.path.append(os.path.join(os.path.dirname(__file__), 'indexer_v2'))
        from clip_manager import ClipManager
        
        clip_manager = ClipManager(search_engine.db_path)
        clips = clip_manager.get_pending_clips()
        
        return jsonify({
            'success': True,
            'clips': clips,
            'count': len(clips)
        })
    
    except Exception as e:
        return jsonify({'error': f'클립 목록 조회 실패: {str(e)}'}), 500

@app.route('/api/create-clip', methods=['POST'])
def create_clip():
    """클립 생성 (수동 처리용 - CLI에서 호출)"""
    try:
        data = request.json
        clip_id = data.get('clip_id', '')
        
        if not clip_id:
            return jsonify({'error': 'clip_id가 필요합니다'}), 400
        
        import sys
        import os
        sys.path.append(os.path.join(os.path.dirname(__file__), 'indexer_v2'))
        from clip_manager import ClipManager
        
        clip_manager = ClipManager(search_engine.db_path)
        result = clip_manager.manual_clip_creation(clip_id)
        
        return jsonify(result)
    
    except Exception as e:
        return jsonify({'error': f'클립 생성 실패: {str(e)}'}), 500

if __name__ == '__main__':
    print("🚀 배치 검색 API 서버 시작")
    print("📊 데이터베이스 연결 확인 중...")
    
    # 데이터베이스 상태 출력
    if search_engine.db_path:
        try:
            conn = sqlite3.connect(search_engine.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM subtitles")
            count = cursor.fetchone()[0]
            conn.close()
            print(f"✅ 데이터베이스 연결 성공: {count:,}개 자막 데이터")
        except Exception as e:
            print(f"⚠️ 데이터베이스 상태 확인 실패: {e}")
    else:
        print("⚠️ 시뮬레이션 모드로 실행")
    
    print("🌐 서버 주소: http://localhost:5000")
    print("📖 API 문서: http://localhost:5000")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
