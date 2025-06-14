# core/utils.py
"""
🛠️ 공통 유틸리티 모듈
메시지 생성, 날짜 계산 등 공통 기능을 제공합니다.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# ==================== 다국어 지원 메시지 시스템 ====================

def create_localized_message(progress: int, status_key: str, lang: str = 'en', 
                           status_data: Optional[Dict] = None, **kwargs) -> Dict[str, Any]:
    """다국어 지원 WebSocket 메시지 생성"""
    message = {
        "progress": progress,
        "status_key": status_key,
        "status_data": status_data or {},
        "language": lang
    }
    message.update(kwargs)
    return message

def create_error_message(error_key: str, lang: str = 'en', 
                        error_data: Optional[Dict] = None) -> Dict[str, Any]:
    """다국어 지원 에러 메시지 생성"""
    return {
        "error_key": error_key,
        "error_data": error_data or {},
        "language": lang
    }

def create_message_response(message_key: str, lang: str = 'en', **data) -> Dict[str, Any]:
    """번역 가능한 메시지 응답 생성 (다국어 지원)"""
    return {
        "message_key": message_key,
        "message_data": data,
        "message_type": "crawl",
        "language": lang
    }

async def get_user_language(init_data: Dict) -> str:
    """사용자 언어 설정 추출"""
    return init_data.get("language", "en")

# ==================== 날짜 계산 유틸리티 ====================

def calculate_actual_dates(time_filter: str, start_date_input: Optional[str] = None, 
                          end_date_input: Optional[str] = None) -> tuple[Optional[str], Optional[str]]:
    """시간 필터를 실제 날짜로 변환하는 함수"""
    now = datetime.now()
    
    if time_filter == 'custom' and start_date_input and end_date_input:
        return start_date_input, end_date_input
        
    elif time_filter == 'hour':
        start_date = now.strftime('%Y-%m-%d')
        end_date = now.strftime('%Y-%m-%d')
        
    elif time_filter == 'day':
        start_date = now.strftime('%Y-%m-%d')
        end_date = now.strftime('%Y-%m-%d')
        
    elif time_filter == 'week':
        start_dt = now - timedelta(days=7)
        start_date = start_dt.strftime('%Y-%m-%d')
        end_date = now.strftime('%Y-%m-%d')
        
    elif time_filter == 'month':
        start_dt = now - timedelta(days=30)
        start_date = start_dt.strftime('%Y-%m-%d')
        end_date = now.strftime('%Y-%m-%d')
        
    elif time_filter == 'year':
        start_dt = now - timedelta(days=365)
        start_date = start_dt.strftime('%Y-%m-%d')
        end_date = now.strftime('%Y-%m-%d')
        
    else:
        return None, None
    
    logger.debug(f"📅 시간 필터 '{time_filter}' → 날짜 범위: {start_date} ~ {end_date}")
    
    return start_date, end_date

def calculate_actual_dates_for_lemmy(time_filter: str, start_date_input: Optional[str] = None, 
                                    end_date_input: Optional[str] = None) -> tuple[Optional[str], Optional[str]]:
    """Lemmy용 시간 필터를 실제 날짜로 변환하는 함수"""
    today = datetime.now()
    
    if time_filter == 'custom' and start_date_input and end_date_input:
        return start_date_input, end_date_input
        
    elif time_filter == 'hour':
        return today.strftime('%Y-%m-%d'), today.strftime('%Y-%m-%d')
        
    elif time_filter == 'day':
        return today.strftime('%Y-%m-%d'), today.strftime('%Y-%m-%d')
        
    elif time_filter == 'week':
        start_dt = today - timedelta(days=7)
        return start_dt.strftime('%Y-%m-%d'), today.strftime('%Y-%m-%d')
        
    elif time_filter == 'month':
        start_dt = today - timedelta(days=30)
        return start_dt.strftime('%Y-%m-%d'), today.strftime('%Y-%m-%d')
        
    elif time_filter == 'year':
        start_dt = today - timedelta(days=365)
        return start_dt.strftime('%Y-%m-%d'), today.strftime('%Y-%m-%d')
        
    else:
        return None, None

# ==================== URL 분석 유틸리티 ====================

def extract_domain_from_url(url: str) -> str:
    """URL에서 도메인 추출"""
    try:
        from urllib.parse import urlparse
        return urlparse(url).netloc.lower()
    except Exception as e:
        logger.warning(f"URL 도메인 추출 실패: {e}")
        return ""

def is_valid_url(url: str) -> bool:
    """URL 유효성 검사"""
    try:
        from urllib.parse import urlparse
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False

def normalize_url(url: str) -> str:
    """URL 정규화"""
    try:
        url = url.strip()
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        return url
    except Exception:
        return url

# ==================== 데이터 처리 유틸리티 ====================

def safe_int(value, default: int = 0) -> int:
    """안전한 정수 변환"""
    try:
        if value is None:
            return default
        return int(value)
    except (ValueError, TypeError):
        return default

def safe_float(value, default: float = 0.0) -> float:
    """안전한 실수 변환"""
    try:
        if value is None:
            return default
        return float(value)
    except (ValueError, TypeError):
        return default

def truncate_string(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """문자열 길이 제한"""
    if not text:
        return ""
    
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix

def clean_text(text: str) -> str:
    """텍스트 정리 (공백, 특수문자 등)"""
    if not text:
        return ""
    
    import re
    # 연속된 공백을 하나로 통합
    text = re.sub(r'\s+', ' ', text)
    # 앞뒤 공백 제거
    text = text.strip()
    
    return text

# ==================== 성능 측정 유틸리티 ====================

class Timer:
    """실행 시간 측정"""
    
    def __init__(self, name: str = "Operation"):
        self.name = name
        self.start_time = None
        self.end_time = None
    
    def __enter__(self):
        self.start_time = datetime.now()
        logger.debug(f"⏱️ {self.name} 시작")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = datetime.now()
        duration = (self.end_time - self.start_time).total_seconds()
        logger.debug(f"⏱️ {self.name} 완료: {duration:.2f}초")
    
    def elapsed(self) -> float:
        """경과 시간 반환 (초)"""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0

# ==================== 캐시 유틸리티 ====================

class SimpleCache:
    """간단한 메모리 캐시"""
    
    def __init__(self, max_size: int = 1000, ttl_seconds: int = 3600):
        self.cache = {}
        self.timestamps = {}
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
    
    def get(self, key: str):
        """캐시에서 값 조회"""
        if key not in self.cache:
            return None
        
        # TTL 확인
        if self._is_expired(key):
            self.delete(key)
            return None
        
        return self.cache[key]
    
    def set(self, key: str, value):
        """캐시에 값 저장"""
        # 크기 제한 확인
        if len(self.cache) >= self.max_size:
            self._evict_oldest()
        
        self.cache[key] = value
        self.timestamps[key] = datetime.now()
    
    def delete(self, key: str):
        """캐시에서 값 삭제"""
        self.cache.pop(key, None)
        self.timestamps.pop(key, None)
    
    def clear(self):
        """캐시 전체 삭제"""
        self.cache.clear()
        self.timestamps.clear()
    
    def _is_expired(self, key: str) -> bool:
        """TTL 만료 확인"""
        if key not in self.timestamps:
            return True
        
        age = (datetime.now() - self.timestamps[key]).total_seconds()
        return age > self.ttl_seconds
    
    def _evict_oldest(self):
        """가장 오래된 항목 제거"""
        if not self.timestamps:
            return
        
        oldest_key = min(self.timestamps.keys(), key=lambda k: self.timestamps[k])
        self.delete(oldest_key)
    
    def stats(self) -> Dict[str, Any]:
        """캐시 통계"""
        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "ttl_seconds": self.ttl_seconds,
            "oldest_entry": min(self.timestamps.values()) if self.timestamps else None,
            "newest_entry": max(self.timestamps.values()) if self.timestamps else None
        }

# ==================== 데이터 검증 유틸리티 ====================

def validate_crawl_params(start_index: int, end_index: int, min_views: int = 0, 
                         min_likes: int = 0) -> tuple[bool, str]:
    """크롤링 매개변수 검증"""
    errors = []
    
    if start_index < 1:
        errors.append("시작 인덱스는 1 이상이어야 합니다")
    
    if end_index < start_index:
        errors.append("종료 인덱스는 시작 인덱스보다 크거나 같아야 합니다")
    
    if end_index - start_index > 100:
        errors.append("한 번에 요청할 수 있는 게시물은 최대 100개입니다")
    
    if min_views < 0:
        errors.append("최소 조회수는 0 이상이어야 합니다")
    
    if min_likes < 0:
        errors.append("최소 추천수는 0 이상이어야 합니다")
    
    if errors:
        return False, "; ".join(errors)
    
    return True, ""

def validate_date_range(start_date: Optional[str], end_date: Optional[str]) -> tuple[bool, str]:
    """날짜 범위 검증"""
    if not start_date or not end_date:
        return True, ""  # 날짜가 없으면 검증 생략
    
    try:
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        
        if start_dt > end_dt:
            return False, "시작 날짜는 종료 날짜보다 빨라야 합니다"
        
        # 너무 긴 기간 제한 (1년)
        if (end_dt - start_dt).days > 365:
            return False, "날짜 범위는 최대 1년까지 가능합니다"
        
        return True, ""
        
    except ValueError:
        return False, "날짜 형식이 올바르지 않습니다 (YYYY-MM-DD)"

# ==================== 로깅 유틸리티 ====================

def log_crawl_start(site_type: str, board_identifier: str, **params):
    """크롤링 시작 로깅"""
    logger.info(f"🚀 크롤링 시작 - {site_type.upper()}: {board_identifier}")
    logger.debug(f"   매개변수: {params}")

def log_crawl_complete(site_type: str, result_count: int, duration: float):
    """크롤링 완료 로깅"""
    logger.info(f"✅ 크롤링 완료 - {site_type.upper()}: {result_count}개 게시물, {duration:.2f}초")

def log_crawl_error(site_type: str, error: Exception):
    """크롤링 오류 로깅"""
    logger.error(f"❌ 크롤링 오류 - {site_type.upper()}: {str(error)}")

# ==================== 시스템 정보 유틸리티 ====================

def get_system_stats() -> Dict[str, Any]:
    """시스템 통계 정보"""
    import psutil
    import platform
    
    try:
        return {
            "platform": platform.system(),
            "python_version": platform.python_version(),
            "cpu_count": psutil.cpu_count(),
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_total": psutil.virtual_memory().total,
            "memory_used": psutil.virtual_memory().used,
            "memory_percent": psutil.virtual_memory().percent,
            "disk_usage": psutil.disk_usage('/').percent,
            "timestamp": datetime.now().isoformat()
        }
    except ImportError:
        # psutil이 없는 경우 기본 정보만
        return {
            "platform": platform.system(),
            "python_version": platform.python_version(),
            "timestamp": datetime.now().isoformat()
        }

# ==================== 파일 처리 유틸리티 ====================

def ensure_directory(path: str):
    """디렉토리 존재 확인 및 생성"""
    import os
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)
        logger.debug(f"📁 디렉토리 생성: {path}")

def get_file_size_mb(filepath: str) -> float:
    """파일 크기를 MB 단위로 반환"""
    try:
        import os
        size_bytes = os.path.getsize(filepath)
        return size_bytes / (1024 * 1024)
    except (OSError, FileNotFoundError):
        return 0.0

def cleanup_old_files(directory: str, max_age_days: int = 7):
    """오래된 파일 정리"""
    import os
    import time
    
    try:
        current_time = time.time()
        cutoff_time = current_time - (max_age_days * 24 * 3600)
        
        removed_count = 0
        for filename in os.listdir(directory):
            filepath = os.path.join(directory, filename)
            if os.path.isfile(filepath):
                file_time = os.path.getmtime(filepath)
                if file_time < cutoff_time:
                    os.remove(filepath)
                    removed_count += 1
        
        if removed_count > 0:
            logger.info(f"🧹 오래된 파일 정리: {removed_count}개 삭제")
        
        return removed_count
        
    except Exception as e:
        logger.error(f"파일 정리 중 오류: {e}")
        return 0

# ==================== 상수 및 설정 ====================

# 지원되는 정렬 방법
SUPPORTED_SORT_METHODS = [
    "recent", "popular", "recommend", "comments", 
    "confidence", "content_type", "hot", "top", "new"
]

# 지원되는 시간 필터
SUPPORTED_TIME_FILTERS = [
    "hour", "day", "week", "month", "year", "all", "custom"
]

# 기본 설정값
DEFAULT_CONFIG = {
    "start_index": 1,
    "end_index": 20,
    "min_views": 0,
    "min_likes": 0,
    "min_comments": 0,
    "sort": "recent",
    "time_filter": "day",
    "language": "en"
}

# 글로벌 캐시 인스턴스
_global_cache = SimpleCache()

def get_cache() -> SimpleCache:
    """글로벌 캐시 인스턴스 반환"""
    return _global_cache