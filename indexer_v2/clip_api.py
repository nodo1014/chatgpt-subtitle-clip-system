#!/usr/bin/env python3
"""
Flask API for subtitle search and clip management
"""

from flask import Flask, request, jsonify, g
from flask_cors import CORS
import sqlite3
import time
import re
from pathlib import Path
import os
import sys

# Add the current directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from search_interface import SubtitleSearch
from clip_manager import ClipManager

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Database path
DATABASE = 'working_subtitles.db'

def get_db():
    """Get database connection"""
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db

def close_db(e=None):
    """Close database connection"""
    db = g.pop('db', None)
    if db is not None:
        db.close()

@app.teardown_appcontext
def close_db(error):
    close_db()

# Initialize services
subtitle_search = SubtitleSearch(DATABASE)
clip_manager = ClipManager(DATABASE)

@app.route('/api/search', methods=['POST'])
def search_subtitles():
    """Search subtitles endpoint"""
    try:
        data = request.get_json()
        query = data.get('query', '')
        language = data.get('language')
        limit = data.get('limit', 20)
        
        if not query:
            return jsonify({'error': 'Query is required'}), 400
        
        results = subtitle_search.search(query, language, limit)
        
        # Format results for frontend
        formatted_results = []
        for row in results['results']:
            if language:
                # When language is specified, we have 6 fields
                media_file, start_time, end_time, text, directory, subtitle_file = row
                lang = language
            else:
                # When no language filter, we have 7 fields including language
                media_file, start_time, end_time, text, directory, subtitle_file, lang = row
            
            formatted_results.append({
                'media_file': media_file,
                'start_time': start_time,
                'end_time': end_time,
                'text': text,
                'directory': directory,
                'subtitle_file': subtitle_file,
                'language': lang
            })
        
        return jsonify({
            'results': formatted_results,
            'search_time': results['search_time'],
            'query': query,
            'total_results': len(formatted_results)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/clips', methods=['POST'])
def create_clip_request():
    """Create a new clip request"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['sentence', 'media_file', 'start_time', 'end_time']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Create clip request
        clip_id = clip_manager.create_clip_request(
            sentence=data['sentence'],
            media_file=data['media_file'],
            start_time=data['start_time'],
            end_time=data['end_time']
        )
        
        return jsonify({
            'success': True,
            'clip_id': clip_id,
            'message': 'Clip request created successfully'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/clips', methods=['GET'])
def get_clip_requests():
    """Get clip requests with optional status filter"""
    try:
        status = request.args.get('status')
        limit = request.args.get('limit', 50, type=int)
        
        clips = clip_manager.get_clip_requests(status=status, limit=limit)
        
        return jsonify({
            'clips': clips,
            'total': len(clips)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/clips/<int:clip_id>/status', methods=['PUT'])
def update_clip_status():
    """Update clip status"""
    try:
        data = request.get_json()
        new_status = data.get('status')
        
        if new_status not in ['pending', 'processing', 'completed', 'failed']:
            return jsonify({'error': 'Invalid status'}), 400
        
        success = clip_manager.update_clip_status(clip_id, new_status)
        
        if success:
            return jsonify({
                'success': True,
                'message': f'Clip status updated to {new_status}'
            })
        else:
            return jsonify({'error': 'Clip not found'}), 404
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/clips/stats', methods=['GET'])
def get_clip_stats():
    """Get clip statistics"""
    try:
        stats = clip_manager.get_clip_stats()
        return jsonify(stats)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': time.time(),
        'database': DATABASE
    })

@app.route('/api', methods=['GET'])
def api_info():
    """API information endpoint"""
    return jsonify({
        'name': 'Subtitle Search & Clip API',
        'version': '1.0.0',
        'endpoints': {
            'POST /api/search': 'Search subtitles',
            'POST /api/clips': 'Create clip request',
            'GET /api/clips': 'Get clip requests',
            'PUT /api/clips/<id>/status': 'Update clip status',
            'GET /api/clips/stats': 'Get clip statistics',
            'GET /api/health': 'Health check'
        }
    })

if __name__ == '__main__':
    # Create database tables if they don't exist
    clip_manager.init_database()
    
    # Run the Flask app
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True
    )
