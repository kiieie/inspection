import requests
import sys

# ======================================================
# [Program Information]
# - File: push_task.py
# - Version: v1.0.0 (2026-01-14)
# - Description: 터미널 기반 수동 태스크 주입(Manual Task Push) 도구
# - Usage: python3 push_task.py
# ======================================================

# 웹 서버 주소 설정 (web_server.py의 포트 준수)
URL = "http://localhost:38000/api/push-task"

def manual_push():
    """웹 서버의 API를 호출하여 새로운 진단 태스크를 DB에 주입합니다."""
    print("📤 [Manual Push] 새로운 진단 태스크 주입 중...")
    
    try:
        # POST 요청을 보내어 태스크 주입 트리거
        response = requests.post(URL, timeout=5)
        
        if response.status_code == 200:
            result = response.json()
            if result.get("status") == "success":
                print(f"✅ 성공: 새 태스크가 주입되었습니다 (ID: {result.get('task_id')})")
                print(f"🔍 미션: {result.get('mission')}, 지점: {result.get('inspection')}")
                print("\n💡 main.py 터미널에서 분석 로그를 확인하세요.")
            else:
                print(f"❌ 실패: 서버 응답 오류 - {result.get('message')}")
        else:
            print(f"❌ 에러: 서버 상태 코드 {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("❌ 연결 실패: 웹 서버가 실행 중인지 확인하세요 (Port: 38000)")
    except Exception as e:
        print(f"❌ 알 수 없는 오류 발생: {e}")

if __name__ == "__main__":
    # 실행 시 안내 문구 출력
    print("------------------------------------------------------")
    print("AI 진단 시스템 - 수동 태스크 주입 도구")
    print("------------------------------------------------------")
    
    manual_push()
