# core/__init__.py
"""
🔥 PickPost 통합 크롤링 시스템 - 핵심 모듈 (안전한 버전)
"""

__version__ = "2.0.0"
__author__ = "PickPost Team"
__description__ = "통합 크롤링 시스템"

# 🔥 순환 import를 피하기 위해 지연 import 사용
def get_site_detector():
    """SiteDetector를 지연 로드"""
    try:
        from .site_detector import SiteDetector
        return SiteDetector
    except ImportError as e:
        print(f"❌ SiteDetector 로드 실패: {e}")
        return None

def get_auto_crawler():
    """AutoCrawler를 지연 로드"""
    try:
        from .auto_crawler import AutoCrawler
        return AutoCrawler
    except ImportError as e:
        print(f"❌ AutoCrawler 로드 실패: {e}")
        return None

def get_utils():
    """Utils 모듈을 지연 로드"""
    try:
        from . import utils
        return utils
    except ImportError as e:
        print(f"❌ Utils 모듈 로드 실패: {e}")
        return None

# 🔥 안전하게 로드 가능한 기본 함수들만 직접 import
try:
    from .utils import (
        get_user_language,
        calculate_actual_dates
    )
    _UTILS_AVAILABLE = True
    print("✅ 기본 Utils 함수 로드 성공")
except ImportError as e:
    print(f"❌ 기본 Utils 함수 로드 실패: {e}")
    _UTILS_AVAILABLE = False
    
    # 폴백 함수들
    def get_user_language(config):
        return config.get("language", "en")
    
    def calculate_actual_dates(time_filter, start_date_input=None, end_date_input=None):
        if time_filter == 'custom' and start_date_input and end_date_input:
            return start_date_input, end_date_input
        return None, None

# 버전 정보
VERSION_INFO = {
    "version": __version__,
    "description": __description__,
    "modules_available": {
        "site_detector": get_site_detector() is not None,
        "auto_crawler": get_auto_crawler() is not None,
        "utils": _UTILS_AVAILABLE
    },
    "supported_sites": [
        "reddit", "dcinside", "blind", "bbc", "lemmy", "universal"
    ]
}

def get_version_info():
    """버전 정보 반환"""
    return VERSION_INFO

# 안전한 팩토리 함수들
def create_site_detector():
    """SiteDetector 인스턴스 생성"""
    SiteDetector = get_site_detector()
    if SiteDetector:
        return SiteDetector()
    return None

def create_auto_crawler():
    """AutoCrawler 인스턴스 생성"""
    AutoCrawler = get_auto_crawler()
    if AutoCrawler:
        return AutoCrawler()
    return None

# 🔥 최소한의 안전한 export
__all__ = [
    # 팩토리 함수들 (안전함)
    "get_site_detector",
    "get_auto_crawler", 
    "get_utils",
    "create_site_detector",
    "create_auto_crawler",
    
    # 기본 함수들 (폴백 포함)
    "get_user_language",
    "calculate_actual_dates",
    
    # 메타 정보
    "get_version_info",
    "VERSION_INFO"
]

print(f"✅ Core 패키지 초기화 완료 (안전 모드): {VERSION_INFO['modules_available']}")
