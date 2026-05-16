#!/bin/bash

# ======================================================
# [Program Information]
# - File: run_system.sh
# - Version: v1.0.0 (2026-01-14)
# - Description: 웹 서버 및 AI 진단 엔진 통합 실행 스크립트
# - Usage: ./run_system.sh
# ======================================================

# [Configuration]
# 가상환경 및 실행 파일 경로 설정
VENV_PYTHON="/home/kiie/projects/.venv-yolo/bin/python3"
WEB_SERVER="web_server.py"
MAIN_ENGINE="main.py"

echo "🚀 AI 진단 통합 시스템을 시작합니다..."

# [Process Management] 
# 스크립트 종료(Ctrl+C) 시 실행 중인 백그라운드 프로세스를 모두 종료하는 함수
cleanup() {
    echo ""
    echo "🛑 시스템을 종료합니다. 프로세스를 정리 중..."
    kill $WEB_PID $MAIN_PID 2>/dev/null
    exit
}

# SIGINT(Ctrl+C) 신호를 받으면 cleanup 함수 실행
trap cleanup SIGINT

# 1. 웹 서버 실행 (백그라운드)
echo "🌐 [1/2] 웹 서버 실행 중... (Port: 38000)"
$VENV_PYTHON $WEB_SERVER > web_server.log 2>&1 &
WEB_PID=$!

# 2. 메인 진단 엔진 실행 (포그라운드)
echo "🧠 [2/2] AI 진단 엔진(Polling) 실행 중..."
echo "------------------------------------------------------"
echo "💡 팁: 시스템을 종료하려면 Ctrl+C를 누르세요."
echo "------------------------------------------------------"
$VENV_PYTHON $MAIN_ENGINE

# 메인 엔진이 종료되면 (백그라운드인 웹 서버도 종료되도록 유도)
cleanup
