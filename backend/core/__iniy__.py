# core/__init__.py - 단순화된 버전

"""
PickPost 코어 모듈 - 단순화된 버전
"""

import logging

logger = logging.getLogger(__name__)

__version__ = "2.0.0"

# 기본 유틸리티 함수들만 제공
def get_user_language(config):
    """사용자 언어 감지"""
    if not config:
        return "en"
    return config.get("language", "en")

def calculate_actual_dates(time_filter, start_date_input=None, end_date_input=None):
    """날짜 범위 계산"""
    from datetime import datetime, timedelta
    
    if time_filter == 'custom' and start_date_input and end_date_input:
        return start_date_input, end_date_input
    
    now = datetime.now()
    
    if time_filter == 'day':
        start = now - timedelta(days=1)
        return start.strftime('%Y-%m-%d'), now.strftime('%Y-%m-%d')
    elif time_filter == 'week':
        start = now - timedelta(weeks=1)
        return start.strftime('%Y-%m-%d'), now.strftime('%Y-%m-%d')
    elif time_filter == 'month':
        start = now - timedelta(days=30)
        return start.strftime('%Y-%m-%d'), now.strftime('%Y-%m-%d')
    elif time_filter == 'year':
        start = now - timedelta(days=365)
        return start.strftime('%Y-%m-%d'), now.strftime('%Y-%m-%d')
    
    return None, None

# Lemmy용 별칭
calculate_actual_dates_for_lemmy = calculate_actual_dates

# 버전 정보
VERSION_INFO = {
    "version": __version__,
    "description": "PickPost Core Module (Simplified)",
    "available_functions": [
        "get_user_language",
        "calculate_actual_dates",
        "calculate_actual_dates_for_lemmy"
    ]
}

def get_version_info():
    """버전 정보 반환"""
    return VERSION_INFO

# 최소한의 export만
__all__ = [
    "get_user_language",
    "calculate_actual_dates", 
    "calculate_actual_dates_for_lemmy",
    "get_version_info",
    "VERSION_INFO"
]

logger.info(f"✅ Core 모듈 초기화 완료 (단순화 버전): {__version__}")