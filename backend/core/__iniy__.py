# core/__init__.py
"""
🔥 PickPost 통합 크롤링 시스템 - 핵심 모듈
"""

from .site_detector import SiteDetector
from .auto_crawler import AutoCrawler
from .utils import (
    create_localized_message,
    create_error_message, 
    create_message_response,
    get_user_language,
    calculate_actual_dates,
    calculate_actual_dates_for_lemmy,
    extract_domain_from_url,
    is_valid_url,
    normalize_url,
    safe_int,
    safe_float,
    truncate_string,
    clean_text,
    Timer,
    SimpleCache,
    validate_crawl_params,
    validate_date_range,
    log_crawl_start,
    log_crawl_complete,
    log_crawl_error,
    get_system_stats,
    ensure_directory,
    get_file_size_mb,
    cleanup_old_files,
    get_cache,
    SUPPORTED_SORT_METHODS,
    SUPPORTED_TIME_FILTERS,
    DEFAULT_CONFIG
)

__version__ = "2.0.0"
__author__ = "PickPost Team"
__description__ = "통합 크롤링 시스템"

# 버전 정보
VERSION_INFO = {
    "version": __version__,
    "description": __description__,
    "modules": [
        "SiteDetector",
        "AutoCrawler", 
        "Utils"
    ],
    "supported_sites": [
        "reddit", "dcinside", "blind", "bbc", "lemmy", "universal"
    ]
}

def get_version_info():
    """버전 정보 반환"""
    return VERSION_INFO

# 기본 익스포트
__all__ = [
    # 클래스
    "SiteDetector",
    "AutoCrawler",
    "Timer",
    "SimpleCache",
    
    # 메시지 함수
    "create_localized_message",
    "create_error_message",
    "create_message_response",
    "get_user_language",
    
    # 유틸리티 함수
    "calculate_actual_dates",
    "calculate_actual_dates_for_lemmy",
    "extract_domain_from_url",
    "is_valid_url", 
    "normalize_url",
    "safe_int",
    "safe_float",
    "truncate_string",
    "clean_text",
    
    # 검증 함수
    "validate_crawl_params",
    "validate_date_range",
    
    # 로깅 함수
    "log_crawl_start",
    "log_crawl_complete", 
    "log_crawl_error",
    
    # 시스템 함수
    "get_system_stats",
    "ensure_directory",
    "get_file_size_mb",
    "cleanup_old_files",
    "get_cache",
    
    # 상수
    "SUPPORTED_SORT_METHODS",
    "SUPPORTED_TIME_FILTERS",
    "DEFAULT_CONFIG",
    
    # 메타 정보
    "get_version_info",
    "VERSION_INFO"
]