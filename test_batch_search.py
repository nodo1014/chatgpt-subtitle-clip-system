#!/usr/bin/env python3
"""
배치 검색 API 테스트 스크립트
"""

import requests
import json
import time

API_BASE_URL = "http://localhost:5000"

def test_api_status():
    """API 상태 테스트"""
    print("🔍 API 상태 확인...")
    try:
        response = requests.get(f"{API_BASE_URL}/api/status")
        if response.status_code == 200:
            status = response.json()
            print(f"✅ API 활성: {status}")
            return True
        else:
            print(f"❌ API 상태 오류: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ API 연결 실패: {e}")
        return False

def test_extract_sentences():
    """영어 문장 추출 테스트"""
    print("\n📝 영어 문장 추출 테스트...")
    
    test_text = """
    The meeting has been postponed until next Wednesday.
    회의가 다음 주 수요일로 연기되었습니다.
    
    Please submit your expense reports by the end of the month.
    이달 말까지 경비 보고서를 제출해 주십시오.
    
    I hope you have a great day!
    좋은 하루 되세요!
    """
    
    try:
        response = requests.post(f"{API_BASE_URL}/api/extract-sentences", 
                               json={"text": test_text})
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 추출된 문장 {result['sentence_count']}개:")
            for i, sentence in enumerate(result['extracted_sentences'], 1):
                print(f"   {i}. {sentence}")
            return result['extracted_sentences']
        else:
            print(f"❌ 문장 추출 실패: {response.status_code}")
            return []
    except Exception as e:
        print(f"❌ 문장 추출 오류: {e}")
        return []

def test_batch_search():
    """배치 검색 테스트"""
    print("\n🔍 배치 검색 테스트...")
    
    test_text = """
    The meeting has been postponed until next Wednesday.
    회의가 다음 주 수요일로 연기되었습니다.
    
    Please submit your expense reports by the end of the month.
    이달 말까지 경비 보고서를 제출해 주십시오.
    
    I hope you have a great day!
    좋은 하루 되세요!
    """
    
    try:
        start_time = time.time()
        response = requests.post(f"{API_BASE_URL}/api/batch-search", 
                               json={
                                   "text": test_text,
                                   "results_per_sentence": 5
                               })
        end_time = time.time()
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 배치 검색 성공 (소요시간: {end_time - start_time:.2f}초)")
            print(f"   추출된 문장: {result['search_summary']['total_sentences']}개")
            print(f"   총 검색 결과: {result['search_summary']['total_results']}개")
            print(f"   문장당 평균: {result['search_summary']['average_per_sentence']:.1f}개")
            
            # 상세 결과 출력
            for sentence_result in result['sentence_results']:
                print(f"\n📝 문장 {sentence_result['sentence_index']}: \"{sentence_result['search_sentence']}\"")
                print(f"   검색 결과: {sentence_result['found_count']}개")
                
                for i, res in enumerate(sentence_result['results'][:3], 1):  # 처음 3개만 출력
                    print(f"   {i}. {res['media_name']} ({res['timestamp']}) - 신뢰도: {res['confidence']:.2f}")
                    print(f"      \"{res['subtitle_text']}\"")
            
            return True
        else:
            print(f"❌ 배치 검색 실패: {response.status_code}")
            if response.text:
                print(f"   오류 메시지: {response.text}")
            return False
    except Exception as e:
        print(f"❌ 배치 검색 오류: {e}")
        return False

def test_search_history():
    """검색 히스토리 테스트"""
    print("\n📚 검색 히스토리 테스트...")
    
    try:
        # 검색 저장
        save_response = requests.post(f"{API_BASE_URL}/api/save-search", 
                                    json={
                                        "sentences": ["Test sentence 1", "Test sentence 2"],
                                        "total_results": 15
                                    })
        
        if save_response.status_code == 200:
            print("✅ 검색 히스토리 저장 성공")
        
        # 히스토리 조회
        history_response = requests.get(f"{API_BASE_URL}/api/search-history")
        
        if history_response.status_code == 200:
            history = history_response.json()
            print(f"✅ 검색 히스토리 조회 성공: {len(history)}개 항목")
            
            for i, item in enumerate(history[-3:], 1):  # 최근 3개만 출력
                print(f"   {i}. {item['timestamp']} - {len(item['sentences'])}개 문장, {item['total_results']}개 결과")
            
            return True
        else:
            print(f"❌ 히스토리 조회 실패: {history_response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 히스토리 테스트 오류: {e}")
        return False

def main():
    """메인 테스트 함수"""
    print("🚀 배치 검색 API 테스트 시작\n")
    
    # API 상태 확인
    if not test_api_status():
        print("\n❌ API 서버가 실행 중이지 않습니다.")
        print("다음 명령으로 서버를 시작하세요:")
        print("python batch_search_api.py")
        return
    
    # 각 기능 테스트
    tests = [
        ("영어 문장 추출", test_extract_sentences),
        ("배치 검색", test_batch_search),
        ("검색 히스토리", test_search_history)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} 테스트 중 오류: {e}")
            results.append((test_name, False))
    
    # 결과 요약
    print("\n" + "="*50)
    print("📊 테스트 결과 요약")
    print("="*50)
    
    passed = 0
    for test_name, result in results:
        status = "✅ 통과" if result else "❌ 실패"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n총 {len(results)}개 테스트 중 {passed}개 통과")
    
    if passed == len(results):
        print("🎉 모든 테스트가 성공적으로 완료되었습니다!")
    else:
        print("⚠️ 일부 테스트가 실패했습니다. 로그를 확인해 주세요.")

if __name__ == "__main__":
    main()
