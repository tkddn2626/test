# core/utils.py - 통합 메시지 처리 유틸리티 (단순화 버전)
import time
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import re

# ==================== 메시지 타입 정의 ====================
class MessageType:
    PROGRESS = "progress"
    STATUS = "status" 
    ERROR = "error"
    SUCCESS = "success"
    WARNING = "warning"
    INFO = "info"
    COMPLETE = "complete"

class CrawlStep:
    INITIALIZING = "initializing"
    DETECTING_SITE = "detecting_site"
    CONNECTING = "connecting"
    COLLECTING = "collecting"
    FILTERING = "filtering"
    PROCESSING = "processing"
    TRANSLATING = "translating"
    FINALIZING = "finalizing"
    COMPLETE = "complete"

class SiteType:
    REDDIT = "reddit"
    DCINSIDE = "dcinside"
    BLIND = "blind"
    BBC = "bbc"
    LEMMY = "lemmy"
    UNIVERSAL = "universal"
    AUTO = "auto"

# ==================== 핵심 메시지 생성 함수들 ====================

def create_message(message_type: str, **kwargs) -> Dict[str, Any]:
    """기본 메시지 구조 생성"""
    base_message = {
        "message_type": message_type,
        "timestamp": time.time(),
        "server_time": datetime.now().isoformat()
    }
    base_message.update(kwargs)
    return base_message

def create_progress_message(
    progress: int,
    step: str,
    site: Optional[str] = None,
    board: Optional[str] = None,
    details: Optional[Dict] = None,
    **kwargs
) -> Dict[str, Any]:
    """통일된 진행률 메시지 생성"""
    progress = validate_progress_range(progress)
    
    return create_message(
        MessageType.PROGRESS,
        progress=progress,
        step=step,
        site=site,
        board=sanitize_board_name(board) if board else None,
        details=details or {},
        **kwargs
    )

def create_status_message(
    step: str,
    site: Optional[str] = None,
    board: Optional[str] = None,
    details: Optional[Dict] = None,
    **kwargs
) -> Dict[str, Any]:
    """통일된 상태 메시지 생성"""
    return create_message(
        MessageType.STATUS,
        step=step,
        site=site,
        board=sanitize_board_name(board) if board else None,
        details=details or {},
        **kwargs
    )

def create_error_message(
    error_code: str,
    error_detail: Optional[str] = None,
    site: Optional[str] = None,
    suggestions: Optional[list] = None,
    **kwargs
) -> Dict[str, Any]:
    """통일된 에러 메시지 생성"""
    return create_message(
        MessageType.ERROR,
        error_code=error_code,
        error_detail=error_detail,
        site=site,
        suggestions=suggestions or [],
        **kwargs
    )

def create_success_message(
    success_type: str,
    count: int,
    site: Optional[str] = None,
    board: Optional[str] = None,
    start_rank: Optional[int] = None,
    end_rank: Optional[int] = None,
    additional_data: Optional[Dict] = None,
    **kwargs
) -> Dict[str, Any]:
    """통일된 성공 메시지 생성"""
    return create_message(
        MessageType.SUCCESS,
        success_type=success_type,
        count=count,
        site=site,
        board=sanitize_board_name(board) if board else None,
        start_rank=start_rank,
        end_rank=end_rank,
        additional_data=additional_data or {},
        **kwargs
    )

def create_complete_message(
    total_count: int,
    site: str,
    board: Optional[str] = None,
    start_rank: Optional[int] = None,
    end_rank: Optional[int] = None,
    crawl_mode: str = "basic",
    elapsed_time: Optional[float] = None,
    metadata: Optional[Dict] = None,
    **kwargs
) -> Dict[str, Any]:
    """통일된 완료 메시지 생성"""
    return create_message(
        MessageType.COMPLETE,
        total_count=total_count,
        site=site,
        board=sanitize_board_name(board) if board else None,
        start_rank=start_rank,
        end_rank=end_rank,
        crawl_mode=crawl_mode,
        elapsed_time=elapsed_time,
        metadata=metadata or {},
        **kwargs
    )

# ==================== 특수 메시지 생성 함수들 ====================

def create_date_filter_message(
    time_filter: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    progress: int = 5,
    site: Optional[str] = None
) -> Dict[str, Any]:
    """날짜 필터 적용 메시지"""
    details = {
        "time_filter": time_filter,
        "start_date": start_date,
        "end_date": end_date,
        "has_custom_date": bool(start_date and end_date)
    }
    
    return create_progress_message(
        progress=progress,
        step=CrawlStep.INITIALIZING,
        site=site,
        details=details
    )

def create_translation_message(
    progress: int,
    current_post: int,
    total_posts: int,
    site: Optional[str] = None,
    **kwargs
) -> Dict[str, Any]:
    """번역 진행 메시지"""
    details = {
        "current_post": current_post,
        "total_posts": total_posts,
        "translation_progress": round((current_post / total_posts) * 100, 1) if total_posts > 0 else 0
    }
    
    return create_progress_message(
        progress=progress,
        step=CrawlStep.TRANSLATING,
        site=site,
        details=details,
        **kwargs
    )

def create_filtering_message(
    progress: int,
    matched_posts: int,
    total_checked: int,
    site: Optional[str] = None,
    min_views: int = 0,
    min_likes: int = 0,
    min_comments: int = 0,
    **kwargs
) -> Dict[str, Any]:
    """필터링 진행 메시지"""
    details = {
        "matched_posts": matched_posts,
        "total_checked": total_checked,
        "filters": {
            "min_views": min_views,
            "min_likes": min_likes,
            "min_comments": min_comments
        }
    }
    
    return create_progress_message(
        progress=progress,
        step=CrawlStep.FILTERING,
        site=site,
        details=details,
        **kwargs
    )

def create_collecting_message(
    progress: int,
    site: str,
    board: str,
    sort_method: Optional[str] = None,
    page: Optional[int] = None,
    found_posts: Optional[int] = None,
    **kwargs
) -> Dict[str, Any]:
    """수집 진행 메시지 (모든 사이트 공통)"""
    details = {
        "sort_method": sort_method,
        "page": page,
        "found_posts": found_posts
    }
    # None 값 제거
    details = {k: v for k, v in details.items() if v is not None}
    
    return create_progress_message(
        progress=progress,
        step=CrawlStep.COLLECTING,
        site=site,
        board=board,
        details=details,
        **kwargs
    )

def create_page_message(
    progress: int,
    site: str,
    board: str,
    current_page: int,
    total_pages: Optional[int] = None,
    found_posts: int = 0,
    **kwargs
) -> Dict[str, Any]:
    """페이지 수집 진행 메시지"""
    details = {
        "current_page": current_page,
        "total_pages": total_pages,
        "found_posts": found_posts
    }
    
    return create_progress_message(
        progress=progress,
        step=CrawlStep.COLLECTING,
        site=site,
        board=board,
        details=details,
        **kwargs
    )

# ==================== 다국어 지원 메시지 ====================

def create_localized_message(
    progress: Optional[int] = None,
    status_key: Optional[str] = None,
    lang: str = "ko",
    status_data: Optional[Dict] = None,
    details_key: Optional[str] = None,
    details_data: Optional[Dict] = None,
    **kwargs
) -> Dict[str, Any]:
    """다국어 지원 메시지 생성 (프론트엔드에서 렌더링용)"""
    message = create_message(MessageType.INFO, **kwargs)
    
    if progress is not None:
        message["progress"] = validate_progress_range(progress)
    
    if status_key:
        message["status_key"] = status_key
        message["status_data"] = status_data or {}
    
    if details_key:
        message["details_key"] = details_key
        message["details_data"] = details_data or {}
    
    message["lang"] = lang
    
    return message

def create_localized_error_message(
    error_key: str,
    lang: str = "ko",
    error_data: Optional[Dict] = None,
    **kwargs
) -> Dict[str, Any]:
    """다국어 지원 에러 메시지"""
    return create_message(
        MessageType.ERROR,
        error_key=error_key,
        error_data=error_data or {},
        lang=lang,
        **kwargs
    )

def create_message_response(
    message_key: str,
    lang: str = "ko",
    **template_data
) -> Dict[str, Any]:
    """템플릿 기반 메시지 응답"""
    return {
        "message_key": message_key,
        "lang": lang,
        "template_data": template_data,
        "timestamp": time.time()
    }

# ==================== 유틸리티 함수들 ====================

def get_user_language(config: Dict) -> str:
    """사용자 언어 감지"""
    return config.get("language", "ko")

async def get_user_language_async(config: Dict) -> str:
    """비동기 버전 (기존 호환성)"""
    return config.get("language", "ko")

def calculate_actual_dates(
    time_filter: str,
    start_date_input: Optional[str] = None,
    end_date_input: Optional[str] = None
) -> tuple[Optional[str], Optional[str]]:
    """실제 날짜 범위 계산"""
    if time_filter == "custom" and start_date_input and end_date_input:
        return start_date_input, end_date_input
    
    if time_filter == "all":
        return None, None
    
    # 상대적 시간 계산
    now = datetime.now()
    end_date = now.strftime('%Y-%m-%d')
    
    if time_filter == "hour":
        start_date = (now - timedelta(hours=1)).strftime('%Y-%m-%d')
    elif time_filter == "day":
        start_date = (now - timedelta(days=1)).strftime('%Y-%m-%d')
    elif time_filter == "week":
        start_date = (now - timedelta(weeks=1)).strftime('%Y-%m-%d')
    elif time_filter == "month":
        start_date = (now - timedelta(days=30)).strftime('%Y-%m-%d')
    elif time_filter == "year":
        start_date = (now - timedelta(days=365)).strftime('%Y-%m-%d')
    else:
        return None, None
    
    return start_date, end_date

def calculate_actual_dates_for_lemmy(
    time_filter: str,
    start_date_input: Optional[str] = None,
    end_date_input: Optional[str] = None
) -> tuple[Optional[str], Optional[str]]:
    """Lemmy용 날짜 범위 계산"""
    return calculate_actual_dates(time_filter, start_date_input, end_date_input)

def validate_progress_range(progress: int) -> int:
    """진행률 범위 검증"""
    return max(0, min(100, progress))

def sanitize_board_name(board_name: str) -> str:
    """게시판 이름 정제"""
    if not board_name:
        return ""
    
    # 기본 정제
    cleaned = re.sub(r'[<>"\']', '', str(board_name).strip())
    return cleaned[:100]  # 길이 제한

def extract_domain_from_url(url: str) -> str:
    """URL에서 도메인 추출"""
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        return parsed.netloc.lower()
    except:
        return ""

def format_elapsed_time(start_time: float) -> float:
    """경과 시간 계산"""
    return round(time.time() - start_time, 2)

def safe_int(value: Any, default: int = 0) -> int:
    """안전한 정수 변환"""
    try:
        return int(value) if value is not None else default
    except (ValueError, TypeError):
        return default

def safe_str(value: Any, default: str = "") -> str:
    """안전한 문자열 변환"""
    try:
        return str(value) if value is not None else default
    except:
        return default

# ==================== 상수 정의 ====================

# 에러 코드 정의
class ErrorCode:
    INVALID_URL = "invalid_url"
    SITE_NOT_FOUND = "site_not_found"
    NO_POSTS_FOUND = "no_posts_found"
    CONNECTION_FAILED = "connection_failed"
    TIMEOUT = "timeout"
    RATE_LIMITED = "rate_limited"
    CRAWLING_ERROR = "crawling_error"
    TRANSLATION_FAILED = "translation_failed"
    INVALID_PARAMETERS = "invalid_parameters"
    UNIFIED_CRAWLING_ERROR = "unified_crawling_error"

# 성공 타입 정의
class SuccessType:
    CRAWL_COMPLETE = "crawl_complete"
    POSTS_COLLECTED = "posts_collected"
    FILTERING_COMPLETE = "filtering_complete"
    TRANSLATION_COMPLETE = "translation_complete"
    UNIFIED_COMPLETE = "unified_complete"

# 기본 진행률 단계
PROGRESS_STEPS = {
    CrawlStep.INITIALIZING: 5,
    CrawlStep.DETECTING_SITE: 10,
    CrawlStep.CONNECTING: 20,
    CrawlStep.COLLECTING: 40,
    CrawlStep.FILTERING: 60,
    CrawlStep.PROCESSING: 70,
    CrawlStep.TRANSLATING: 85,
    CrawlStep.FINALIZING: 95,
    CrawlStep.COMPLETE: 100
}

# 사이트별 기본 진행률 (필요시 사용)
SITE_PROGRESS_OFFSETS = {
    SiteType.REDDIT: {"collecting": 30, "processing": 60},
    SiteType.DCINSIDE: {"collecting": 25, "processing": 65},
    SiteType.BLIND: {"collecting": 35, "processing": 70},
    SiteType.BBC: {"collecting": 40, "processing": 70},
    SiteType.LEMMY: {"collecting": 35, "processing": 65},
    SiteType.UNIVERSAL: {"collecting": 50, "processing": 75}
}

# ==================== 편의 함수들 ====================

def quick_progress(progress: int, step: str, site: str, board: str = "", **details) -> Dict[str, Any]:
    """빠른 진행률 메시지 생성"""
    return create_progress_message(
        progress=progress,
        step=step,
        site=site,
        board=board,
        details=details
    )

def quick_error(error_code: str, site: str = "", detail: str = "") -> Dict[str, Any]:
    """빠른 에러 메시지 생성"""
    return create_error_message(
        error_code=error_code,
        site=site,
        error_detail=detail
    )

def quick_complete(count: int, site: str, board: str = "", start: int = 1, end: int = None) -> Dict[str, Any]:
    """빠른 완료 메시지 생성"""
    return create_complete_message(
        total_count=count,
        site=site,
        board=board,
        start_rank=start,
        end_rank=end or (start + count - 1)
    )