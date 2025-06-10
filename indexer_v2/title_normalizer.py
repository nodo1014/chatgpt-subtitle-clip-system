#!/usr/bin/env python3

import re
import os
from pathlib import Path

class TitleNormalizer:
    """파일명에서 간단한 제목을 추출하는 클래스"""
    
    def __init__(self):
        pass
    
    def extract_title(self, file_path):
        """파일 경로에서 제목 추출"""
        filename = os.path.basename(file_path)
        name = os.path.splitext(filename)[0]
        
        # 년도 제거
        name = re.sub(r'\(\d{4}\)', '', name)
        
        # 시즌/에피소드 앞까지만
        season_match = re.search(r'[- ](S\d{1,2}E\d{1,2}|\d{1,2}x\d{1,2})', name, re.IGNORECASE)
        if season_match:
            name = name[:season_match.start()]
        
        # 년도 앞까지만 (영화)
        year_match = re.search(r'\b(19|20)\d{2}\b', name)
        if year_match:
            name = name[:year_match.start()]
        
        # 화질정보 제거
        name = re.sub(r'\b(1080p|720p|480p|BluRay|DVDRip|WEBRip).*$', '', name, flags=re.IGNORECASE)
        
        # 특수문자를 공백으로
        name = re.sub(r'[._-]+', ' ', name)
        name = name.strip()
        
        return name
    
    def normalize_for_folder(self, text):
        """폴더명에 사용할 수 있도록 정규화"""
        # 특수문자를 언더스코어로
        normalized = re.sub(r'[^\w\s-]', '', text)
        normalized = re.sub(r'[-\s]+', '_', normalized)
        return normalized.strip('_')
    
    def normalize_for_filename(self, text):
        """파일명에 사용할 수 있도록 정규화"""
        # 특수문자 제거하고 언더스코어로
        normalized = re.sub(r'[^\w\s-]', '', text)
        normalized = re.sub(r'[-\s]+', '_', normalized)
        return normalized.strip('_')

# 테스트
if __name__ == "__main__":
    normalizer = TitleNormalizer()
    
    test_files = [
        "Batman The Animated Series (1992) - S01E01 - The Cat & the Claw (Part 1) (1080p BluRay x265 RCVR).mkv",
        "Missing.Link.2019.1080p.BluRay.x264-[YTS.LT].mp4",
        "Charlie Brown and Snoopy Show - 1x01 - Snoopy's Cat Fight.mp4",
        "The.Matrix.1999.1080p.BluRay.x264.YIFY.mp4",
        "Friends - S10E02 - The One Where Ross Is Fine.mkv"
    ]
    
    print("=== 제목 정규화 테스트 ===")
    for file in test_files:
        normalized = normalizer.extract_title(file)
        print(f"원본: {file}")
        print(f"정규화: {normalized}")
        print("-" * 50)
