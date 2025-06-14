from fastapi import FastAPI, WebSocket, Query, Request
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional, Dict, Set,Tuple, Optional, Any
import os, asyncio, json, requests
from reddit import fetch_posts
from blind import crawl_blind_board, list_available_topics, search_topics, load_blind_map, sort_posts as sort_blind_posts
from dcinside import crawl_dcinside_board, list_available_galleries, search_galleries, load_gallery_map, sort_posts as sort_dcinside_posts
from universal import crawl_universal_board, parse_generic
from lemmy import crawl_lemmy_board, search_lemmy_communities, get_popular_lemmy_instances, resolve_lemmy_community_id
from bbc import (
    detect_bbc_url_and_extract_info,
    is_bbc_domain,
    get_bbc_autocomplete_suggestions,
    get_bbc_topics_list,
    search_bbc_topics,
    validate_bbc_url_info,
    crawl_bbc_board
)

from datetime import datetime
import pandas as pd
from fastapi.middleware.cors import CORSMiddleware
import traceback
from dotenv import load_dotenv
from urllib.parse import urlparse
from enum import Enum
from dataclasses import dataclass
import weakref
import time
from fastapi import HTTPException
import logging

# ==================== 환경 설정 및 초기화 ====================
load_dotenv()

DEEPL_API_KEY = os.getenv("DEEPL_API_KEY")
APP_ENV = os.getenv("APP_ENV", "development")
DEBUG = os.getenv("DEBUG", "False").lower() == "true"
PORT = int(os.getenv("PORT", 8000))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000")

# ==================== 로깅 설정 ====================
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('app.log') if APP_ENV == "production" else logging.StreamHandler()
    ]
)

logger = logging.getLogger("pickpost")

if DEBUG:
    logger.debug(f"🔧 환경 설정:")
    logger.debug(f"  APP_ENV: {APP_ENV}")
    logger.debug(f"  DEBUG: {DEBUG}")
    logger.debug(f"  PORT: {PORT}")
    logger.debug(f"  ALLOWED_ORIGINS: {ALLOWED_ORIGINS}")
    logger.debug(f"  LOG_LEVEL: {LOG_LEVEL}")
    logger.debug(f"  DEEPL_API_KEY: {'설정됨' if DEEPL_API_KEY else '미설정'}")

# ==================== 다국어 지원 메시지 시스템 ====================
def create_localized_message(progress, status_key, lang='en', status_data=None, **kwargs):
    """다국어 지원 WebSocket 메시지 생성"""
    message = {
        "progress": progress,
        "status_key": status_key,
        "status_data": status_data or {},
        "language": lang
    }
    message.update(kwargs)
    return message

def create_error_message(error_key, lang='en', error_data=None):
    """다국어 지원 에러 메시지 생성"""
    return {
        "error_key": error_key,
        "error_data": error_data or {},
        "language": lang
    }

def create_message_response(message_key: str, lang: str = 'en', **data):
    """번역 가능한 메시지 응답 생성 (다국어 지원)"""
    return {
        "message_key": message_key,
        "message_data": data,
        "message_type": "crawl",
        "language": lang
    }

async def get_user_language(init_data):
    """사용자 언어 설정 추출"""
    return init_data.get("language", "en")

# ==================== FastAPI 앱 초기화 ====================
app = FastAPI(
    title="PickPost API",
    debug=DEBUG
)

# ==================== CORS 설정 ====================
def get_cors_origins():
    """환경별 CORS 도메인 설정"""
    if APP_ENV == "production":
        base_origins = os.getenv("ALLOWED_ORIGINS", "").split(",")
        production_origins = [
            "https://pickpost.netlify.app",
            "https://pickpost--*.netlify.app"
        ]
        
        for origin in base_origins:
            origin = origin.strip()
            if origin and origin.startswith("https://"):
                production_origins.append(origin)
                
        return production_origins
    else:
        return [
            "http://localhost:3000",
            "http://localhost:8000", 
            "http://127.0.0.1:8000",
            "https://127.0.0.1:8000",
            "https://pickpost.netlify.app"
        ]

if APP_ENV == "production":
    allowed_origins = get_cors_origins()
    allow_origin_regex = r"https://.*\.netlify\.app$"
else:
    allowed_origins = ["*"]
    allow_origin_regex = None

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=allow_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== 환경변수 검증 ====================
def validate_environment():
    """필수 환경변수 검증"""
    required_vars = ['DEEPL_API_KEY']
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        logger.error(f"❌ 필수 환경변수 누락: {', '.join(missing_vars)}")
        if APP_ENV == "production":
            raise ValueError(f"필수 환경변수 누락: {', '.join(missing_vars)}")
    
    logger.info(f"🔧 환경 설정 ({APP_ENV}):")
    logger.info(f"  PORT: {PORT}")
    logger.info(f"  DEEPL_API_KEY: {'설정됨' if DEEPL_API_KEY else '미설정'}")
    logger.info(f"  ALLOWED_ORIGINS: {os.getenv('ALLOWED_ORIGINS', 'default')}")

try:
    validate_environment()
    logger.info("✅ 환경변수 검증 완료")
except ValueError as e:
    logger.error(f"❌ 환경변수 오류: {e}")
    if APP_ENV == "production":
        exit(1)

# ==================== 동적 CORS 미들웨어 ====================
@app.middleware("http")
async def dynamic_cors_middleware(request: Request, call_next):
    """환경별 동적 CORS 처리"""
    origin = request.headers.get("origin")
    
    response = await call_next(request)
    
    if APP_ENV == "production":
        if origin and "netlify.app" in origin:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "*"
            response.headers["Access-Control-Allow-Credentials"] = "true"
    else:
        if origin and (
            "netlify.app" in origin or
            "localhost" in origin or
            "127.0.0.1" in origin
        ):
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "*"
            response.headers["Access-Control-Allow-Credentials"] = "true"
    
    return response

# ==================== 크롤링 관리 시스템 ====================
class CrawlManager:
    """크롤링 작업 관리 클래스"""
    def __init__(self):
        self.cancelled_crawls: Set[str] = set()
        self.creation_time = time.time()
    
    def cancel_crawl(self, crawl_id: str):
        """크롤링 작업 취소 마킹"""
        self.cancelled_crawls.add(crawl_id)
        print(f"🚫 크롤링 취소 요청: {crawl_id} (총 {len(self.cancelled_crawls)}개 취소됨)")
    
    def is_cancelled(self, crawl_id: str) -> bool:
        """크롤링이 취소되었는지 확인"""
        return crawl_id in self.cancelled_crawls
    
    def cleanup_crawl(self, crawl_id: str):
        """크롤링 정리"""
        removed = crawl_id in self.cancelled_crawls
        self.cancelled_crawls.discard(crawl_id)
        if removed:
            print(f"🧹 크롤링 정리: {crawl_id} (남은 취소된 크롤링: {len(self.cancelled_crawls)}개)")
    
    def get_stats(self) -> dict:
        """크롤링 매니저 통계"""
        return {
            "cancelled_crawls_count": len(self.cancelled_crawls),
            "uptime_seconds": time.time() - self.creation_time,
            "cancelled_ids": list(self.cancelled_crawls)
        }
    
    def cleanup_old_crawls(self, max_age_seconds: int = 3600):
        """오래된 크롤링 정리"""
        old_count = len(self.cancelled_crawls)
        self.cancelled_crawls.clear()
        print(f"🧹 오래된 크롤링 정리: {old_count}개")
        return old_count

crawl_manager = CrawlManager()

# ==================== 크롤링 진행 상태 관리 ====================
class CrawlStopReason(Enum):
    """크롤링 중단 이유"""
    COMPLETED = "completed"
    CONDITION_NOT_MET = "condition_not_met"
    DATE_OUT_OF_RANGE = "date_out_of_range"
    NO_MORE_PAGES = "no_more_pages"
    ERROR = "error"

@dataclass
class CrawlProgress:
    """크롤링 진행 상태"""
    current_page: int = 1
    total_found: int = 0
    condition_matched: int = 0
    consecutive_fails: int = 0
    stop_reason: Optional[CrawlStopReason] = None

# ==================== 스마트 조건 검사기 ====================
class SmartConditionChecker:
    """지능적 조건 검사기"""
    
    def __init__(self, min_views: int = 0, min_likes: int = 0, min_comments: int = 0,
                 start_date: str = None, end_date: str = None):
        self.min_views = min_views
        self.min_likes = min_likes
        self.min_comments = min_comments
        self.start_dt = self._parse_date(start_date)
        self.end_dt = self._parse_date(end_date)
        if self.end_dt:
            self.end_dt = self.end_dt.replace(hour=23, minute=59, second=59)
    
    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        if not date_str:
            return None
        try:
            return datetime.strptime(date_str, '%Y-%m-%d')
        except Exception:
            return None
    
    def check_post_conditions(self, post: dict) -> Tuple[bool, str]:
        """게시물이 조건을 만족하는지 검사"""
        views = post.get('조회수', 0)
        likes = post.get('추천수', 0)
        comments = post.get('댓글수', 0)
        
        if views < self.min_views:
            return False, f"조회수 부족: {views} < {self.min_views}"
        if likes < self.min_likes:
            return False, f"추천수 부족: {likes} < {self.min_likes}"
        if comments < self.min_comments:
            return False, f"댓글수 부족: {comments} < {self.min_comments}"
        
        if self.start_dt and self.end_dt:
            post_date = self._extract_post_date(post)
            if post_date:
                if post_date < self.start_dt:
                    return False, f"날짜 범위 이전"
                if post_date > self.end_dt:
                    return False, f"날짜 범위 이후"
        
        return True, "조건 만족"
    
    def _extract_post_date(self, post: dict) -> Optional[datetime]:
        date_str = post.get('작성일', '')
        if not date_str:
            return None
        
        formats = ['%Y.%m.%d %H:%M', '%Y-%m-%d %H:%M', '%Y.%m.%d', '%Y-%m-%d']
        for fmt in formats:
            try:
                return datetime.strptime(date_str.strip(), fmt)
            except ValueError:
                continue
        return None
    
    def should_stop_crawling(self, consecutive_fails: int, has_date_filter: bool) -> Tuple[bool, CrawlStopReason]:
        """크롤링 중단 여부 판단"""
        fail_threshold = 10 if has_date_filter else 20
        
        if consecutive_fails >= fail_threshold:
            return True, CrawlStopReason.CONDITION_NOT_MET
        
        return False, CrawlStopReason.COMPLETED

# ==================== 스마트 크롤링 엔진 ====================
async def smart_crawl_with_conditions(crawl_func, condition_checker: SmartConditionChecker,
                                    start_index: int, end_index: int, websocket=None):
    """조건 기반 지능적 크롤링"""
    progress = CrawlProgress()
    all_posts = []
    matched_posts = []
    
    try:
        has_filters = (condition_checker.min_views > 0 or 
                      condition_checker.min_likes > 0 or 
                      condition_checker.min_comments > 0 or
                      (condition_checker.start_dt and condition_checker.end_dt))
        
        if has_filters:
            crawl_limit = min(end_index * 3, 200)
        else:
            crawl_limit = end_index + 5
        
        if websocket:
            await websocket.send_json({
                "progress": 20,
                "status": f"🎯 지능적 크롤링 시작",
                "details": f"필터 {'있음' if has_filters else '없음'}, 수집량: {crawl_limit}개"
            })
        
        raw_posts = await crawl_func(limit=crawl_limit, websocket=websocket)
        
        if not raw_posts:
            return []
        
        for idx, post in enumerate(raw_posts):
            all_posts.append(post)
            
            is_valid, reason = condition_checker.check_post_conditions(post)
            
            if is_valid:
                matched_posts.append(post)
                progress.consecutive_fails = 0
                
                if websocket and len(matched_posts) % 5 == 0:
                    await websocket.send_json({
                        "progress": 40 + int(len(matched_posts) / (end_index - start_index + 1) * 40),
                        "status": f"✅ 조건 만족 게시물 발견: {len(matched_posts)}개",
                        "details": f"전체 {len(all_posts)}개 중 검사"
                    })
                
                if len(matched_posts) >= (end_index - start_index + 1):
                    break
            else:
                progress.consecutive_fails += 1
                
                should_stop, stop_reason = condition_checker.should_stop_crawling(
                    progress.consecutive_fails, 
                    condition_checker.start_dt is not None
                )
                
                if should_stop:
                    if websocket:
                        await websocket.send_json({
                            "progress": 80,
                            "status": f"⚠️ 조건 불만족으로 크롤링 중단",
                            "details": f"연속 {progress.consecutive_fails}개 불만족"
                        })
                    break
        
        final_posts = matched_posts[start_index-1:end_index] if start_index <= len(matched_posts) else matched_posts
        
        for idx, post in enumerate(final_posts):
            post['번호'] = start_index + idx
        
        if websocket:
            await websocket.send_json({
                "progress": 95,
                "status": f"🎯 최종 결과: {len(final_posts)}개",
                "details": f"전체 {len(all_posts)}개 → 조건만족 {len(matched_posts)}개 → 범위적용 {len(final_posts)}개"
            })
        
        return final_posts
        
    except Exception as e:
        print(f"지능적 크롤링 오류: {e}")
        return []

# ==================== 번역 서비스 ====================
async def deepl_translate(text: str, target_lang: str) -> str:
    try:
        if not text.strip():
            return ""
        response = requests.post(
            "https://api-free.deepl.com/v2/translate",
            data={
                "auth_key": DEEPL_API_KEY,
                "text": text,
                "target_lang": target_lang.upper()
            }
        )
        result = response.json()
        return result["translations"][0]["text"]
    except Exception as e:
        print("DeepL 번역 오류:", e)
        return "(번역 실패)"

# ==================== 날짜 계산 유틸리티 ====================
def calculate_actual_dates(time_filter: str, start_date_input: str = None, end_date_input: str = None):
    """시간 필터를 실제 날짜로 변환하는 함수"""
    from datetime import datetime, timedelta
    
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
    
    print(f"📅 시간 필터 '{time_filter}' → 날짜 범위: {start_date} ~ {end_date}")
    
    return start_date, end_date

def calculate_actual_dates_for_lemmy(time_filter: str, start_date_input: str = None, end_date_input: str = None):
    """Lemmy용 시간 필터를 실제 날짜로 변환하는 함수"""
    from datetime import datetime, timedelta
    
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
async def detect_site_from_url(url: str) -> str:
    """URL에서 사이트 종류 자동 감지"""
    if not url:
        return "universal"
    
    url = url.lower().strip()
    
    if not url.startswith('http'):
        return "keyword"
    
    try:
        domain = urlparse(url).netloc.lower()
        
        if 'reddit.com' in domain:
            return 'reddit'
        elif 'dcinside.com' in domain or 'gall.dcinside.com' in domain:
            return 'dcinside'
        elif 'teamblind.com' in domain or 'blind.com' in domain:
            return 'blind'
        elif is_bbc_domain(url):
            return 'bbc'
        elif any(lemmy_domain in domain for lemmy_domain in 
                ['lemmy.', 'beehaw.', 'sh.itjust.works', 'feddit.', 'lemm.ee']):
            return 'lemmy'
        else:
            return 'universal'
            
    except Exception as e:
        print(f"URL 파싱 오류: {e}")
        return 'universal'

def should_apply_strict_date_filter(time_filter: str) -> bool:
    """엄격한 날짜 필터링이 필요한지 확인"""
    return time_filter in ['hour', 'day', 'week', 'month', 'year']

def extract_board_from_url(url: str, site: str) -> str:
    """URL에서 게시판 정보 추출"""
    try:
        if site == 'reddit':
            import re
            match = re.search(r'/r/([^/]+)', url)
            return match.group(1) if match else url
        elif site == 'dcinside':
            import re
            match = re.search(r'[?&]id=([^&]+)', url)
            return match.group(1) if match else url
        elif site == 'blind':
            return url
        elif site == 'lemmy':
            if '/c/' in url:
                parts = url.split('/c/')
                if len(parts) > 1:
                    community_part = parts[1].split('/')[0]
                    domain = urlparse(url).netloc
                    return f"{community_part}@{domain}"
            return url
        else:
            return url
    except Exception as e:
        print(f"게시판 추출 오류: {e}")
        return url

# ==================== 크롤링 취소 확인 함수들 ====================
async def fetch_posts_with_cancel_check(*args, crawl_id=None, **kwargs):
    """Reddit 크롤링에 취소 확인 추가"""
    if crawl_id and crawl_manager.is_cancelled(crawl_id):
        raise asyncio.CancelledError("크롤링이 취소되었습니다")
    
    kwargs.pop('crawl_id', None)
    return await fetch_posts(*args, **kwargs)

async def crawl_dcinside_board_with_cancel_check(*args, crawl_id=None, **kwargs):
    """DCInside 크롤링에 취소 확인 추가"""
    if crawl_id and crawl_manager.is_cancelled(crawl_id):
        raise asyncio.CancelledError("크롤링이 취소되었습니다")
    
    kwargs.pop('crawl_id', None)
    return await crawl_dcinside_board(*args, **kwargs)

async def crawl_blind_board_with_cancel_check(*args, crawl_id=None, **kwargs):
    """Blind 크롤링에 취소 확인 추가"""
    if crawl_id and crawl_manager.is_cancelled(crawl_id):
        raise asyncio.CancelledError("크롤링이 취소되었습니다")
    
    kwargs.pop('crawl_id', None)
    return await crawl_blind_board(*args, **kwargs)

async def crawl_bbc_board_with_cancel_check(board_url: str, crawl_id=None, **kwargs):
    """BBC 크롤링에 취소 확인 추가"""
    if crawl_id and crawl_manager.is_cancelled(crawl_id):
        raise asyncio.CancelledError("크롤링이 취소되었습니다")
    
    from bbc import crawl_bbc_board
    return await crawl_bbc_board(board_url=board_url, **kwargs)

async def crawl_lemmy_board_with_cancel_check(*args, crawl_id=None, **kwargs):
    """Lemmy 크롤링에 취소 확인 추가"""
    if crawl_id and crawl_manager.is_cancelled(crawl_id):
        raise asyncio.CancelledError("크롤링이 취소되었습니다")
    
    kwargs.pop('crawl_id', None)
    return await crawl_lemmy_board(*args, **kwargs)

# ==================== API 엔드포인트 ====================
@app.get("/api/topics/{site}")
def get_available_topics(site: str):
    """사용 가능한 토픽/갤러리 목록을 반환합니다."""
    try:
        if site == "blind":
            board_map = load_blind_map()
            return {"topics": list(board_map.keys()), "count": len(board_map)}
        elif site == "dcinside":
            gallery_map = load_gallery_map()
            return {"topics": list(gallery_map.keys()), "count": len(gallery_map)}
        elif site == "bbc": 
            return get_bbc_topics_list()
        elif site == "lemmy":
            instances = get_popular_lemmy_instances()
            return {
                "topics": ["Lemmy 커뮤니티 URL을 입력하세요"], 
                "count": len(instances),
                "instances": instances,
                "note": "예: technology@lemmy.world 또는 https://lemmy.world/c/technology"
            }
        elif site == "universal":
            return {"topics": ["URL을 직접 입력하세요"], "count": 1, "note": "범용 크롤러는 게시판 URL을 직접 입력하세요"}
        else:
            return JSONResponse(status_code=400, content={"error": "지원하지 않는 사이트입니다."})
    except Exception as e:
        print(f"Topics API error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/search/{site}")
def search_topics_api(site: str, keyword: str = Query(...)):
    """키워드로 토픽/갤러리를 검색합니다."""
    try:
        keyword = keyword.strip().lower()
        if site == "blind":
            board_map = load_blind_map()
            matches = [(name, board_id) for name, board_id in board_map.items() if keyword in name.lower()]
            return {"matches": [{"name": name, "id": board_id} for name, board_id in matches[:20]]}
        elif site == "dcinside":
            gallery_map = load_gallery_map()
            matches = [(name, board_id) for name, board_id in gallery_map.items() if keyword in name.lower()]
            return {"matches": [{"name": name, "id": board_id} for name, board_id in matches[:20]]}
        elif site == "bbc": 
                return search_bbc_topics(keyword)
        elif site == "lemmy":
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                communities = loop.run_until_complete(search_lemmy_communities(keyword))
                matches = [{"name": f"{comm['이름']}@{comm['인스턴스']}", "id": comm['URL']} for comm in communities[:20]]
                return {"matches": matches}
            finally:
                loop.close()
        elif site == "universal":
            return {"matches": [{"name": "범용 크롤러", "id": "URL 직접 입력"}], "note": "게시판 URL을 직접 입력하세요"}
        else:
            return JSONResponse(status_code=400, content={"error": "지원하지 않는 사이트입니다."})
    except Exception as e:
        print(f"Search API error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

# ==================== 자동완성 API ====================
@app.get("/autocomplete/{site}")
async def autocomplete(site: str, keyword: str = Query(...)):
    keyword = keyword.strip()
    matches = []
    
    bbc_detection = detect_bbc_url_and_extract_info(keyword)
    
    if bbc_detection["is_bbc"]:
        return {
            "matches": [bbc_detection["board_name"]],
            "detected_site": "bbc",
            "original_url": bbc_detection["normalized_url"],
            "board_url": bbc_detection["normalized_url"],
            "section_info": {
                "section": bbc_detection["section"],
                "subsection": bbc_detection["subsection"], 
                "description": bbc_detection["description"]
            },
            "auto_detected": True,
            "auto_switch_site": True,
            "switch_message": bbc_detection["switch_message"],
            "suggestion": f"자동으로 BBC 크롤러로 전환됩니다: {bbc_detection['board_name']}"
        }
    
    if keyword.startswith('http'):
        detected_site = await detect_site_from_url(keyword)
        board_name = extract_board_from_url(keyword, detected_site)
        
        return {
            "matches": [board_name],
            "detected_site": detected_site,
            "original_url": keyword,
            "auto_detected": True
        }
    
    keyword_lower = keyword.lower()
    
    try:
        if site == "blind":
            try:
                board_map = load_blind_map()
                if board_map:
                    matches = [name for name in board_map.keys() if keyword_lower in name.lower()]
                else:
                    with open("id_data/boards.json", encoding="utf-8") as f:
                        data = json.load(f)
                        matches = [name for name in data.keys() if keyword_lower in name.lower()]
            except FileNotFoundError:
                print("id_data/boards.json not found")
                matches = [
                    "블라블라", "회사생활", "자유토크", "개발자", "경력개발", 
                    "취업/이직", "스타트업", "회사와사람들", "디자인", "금융/재테크",
                    "부동산", "결혼/육아", "여행", "음식", "건강", "연애", "게임",
                    "주식", "암호화폐", "IT/기술", "AI/머신러닝"
                ]
                matches = [name for name in matches if keyword_lower in name.lower()]
                
        elif site == "dcinside":
            try:
                gallery_map = load_gallery_map()
                if gallery_map:
                    matches = [name for name in gallery_map.keys() if keyword_lower in name.lower()]
                else:
                    gallery_map = {}
                    gallery_dir = "id_data"
                    if os.path.isdir(gallery_dir):
                        for filename in os.listdir(gallery_dir):
                            if filename.endswith(".json"):
                                with open(os.path.join(gallery_dir, filename), "r", encoding="utf-8") as f:
                                    data = json.load(f)
                                    gallery_map.update(data)
                    
                    matches = [name for name in gallery_map.keys() if keyword_lower in name.lower()]
            except Exception as e:
                print(f"id loading error: {e}")
                matches = [
                    "싱글벙글", "유머", "정치", "축구", "야구", "농구", "배구",
                    "게임", "리그오브레전드", "오버워치", "스타크래프트", "카운터스트라이크",
                    "PC게임", "모바일게임", "애니메이션", "만화", "영화", "드라마",
                    "음악", "아이돌", "케이팝", "힙합", "록음악", "재즈", 
                    "요리", "여행", "사진", "자동차", "오토바이", "컴퓨터",
                    "스마트폰", "카메라", "연예인", "주식", "부동산", "경제",
                    "IT", "프로그래밍", "개발", "디자인", "건강", "헬스",
                    "패션", "뷰티", "반려동물", "고양이", "강아지"
                ]
                matches = [name for name in matches if keyword_lower in name.lower()]
                
        elif site == "bbc": 
            bbc_suggestions = {
                "news": ["news", "뉴스", "세계", "국제"],
                "business": ["business", "비즈니스", "경제", "금융"],
                "technology": ["technology", "기술", "tech", "테크"],
                "sport": ["sport", "스포츠", "축구", "올림픽"],
                "health": ["health", "건강", "의료", "코로나"],
                "science": ["science", "과학", "연구", "발견"],
                "entertainment": ["entertainment", "연예", "문화", "음악", "영화"]
            }
            
            for section, keywords in bbc_suggestions.items():
                if any(keyword_lower in keyword.lower() for keyword in keywords):
                    matches.append(f"https://www.bbc.com/{section}")
            
            matches = list(set(matches))

        elif site == "lemmy":
            lemmy_communities = {
                "technology": ["technology", "기술", "tech"],
                "worldnews": ["worldnews", "뉴스", "news", "세계뉴스"],
                "asklemmy": ["asklemmy", "질문", "ask"],
                "programming": ["programming", "프로그래밍", "코딩", "개발"],
                "linux": ["linux", "리눅스"],
                "privacy": ["privacy", "프라이버시", "보안"],
                "opensource": ["opensource", "오픈소스"],
                "science": ["science", "과학"],
                "memes": ["memes", "밈", "meme"],
                "gaming": ["gaming", "게임", "game"],
                "movies": ["movies", "영화", "movie"],
                "music": ["music", "음악"],
                "books": ["books", "책", "독서"],
                "photography": ["photography", "사진"],
                "art": ["art", "예술"],
                "food": ["food", "음식", "요리"],
                "travel": ["travel", "여행"],
                "fitness": ["fitness", "헬스", "운동"],
                "diy": ["diy", "diy프로젝트"],
                "gardening": ["gardening", "원예", "정원"],
                "pets": ["pets", "반려동물", "애완동물"]
            }
            
            for community, keywords in lemmy_communities.items():
                if any(keyword_lower in keyword.lower() for keyword in keywords):
                    matches.append(f"{community}@lemmy.world")
            
            matches = list(set(matches))
            
        elif site == "universal":
            universal_suggestions = [
                "네이버 카페", "다음 카페", "디시인사이드", "클리앙", "루리웹", 
                "뽐뿌", "인벤", "와이고수", "92dp", "티스토리", "네이트판"
            ]
            matches = [name for name in universal_suggestions if keyword_lower in name.lower()]
            
        elif site == "reddit":
            reddit_subreddits = {
                "askreddit": ["askreddit", "질문", "ask"],
                "todayilearned": ["todayilearned", "til", "오늘배운것", "배움"],
                "funny": ["funny", "유머", "웃긴", "재미"],
                "pics": ["pics", "사진", "picture"],
                "worldnews": ["worldnews", "뉴스", "news", "세계뉴스"],
                "gaming": ["gaming", "게임", "game"],
                "movies": ["movies", "영화", "movie"],
                "music": ["music", "음악"],
                "science": ["science", "과학"],
                "technology": ["technology", "기술", "tech"],
                "programming": ["programming", "프로그래밍", "코딩", "개발"],
                "python": ["python", "파이썬"],
                "javascript": ["javascript", "자바스크립트", "js"],
                "webdev": ["webdev", "웹개발", "web"],
                "learnpython": ["learnpython", "파이썬배우기"],
                "MachineLearning": ["machinelearning", "머신러닝", "ml", "ai"],
                "artificial": ["artificial", "인공지능", "ai"],
                "lifeprotips": ["lifeprotips", "생활팁", "팁"],
                "showerthoughts": ["showerthoughts", "샤워생각", "생각"],
                "mildlyinteresting": ["mildlyinteresting", "흥미로운"],
                "food": ["food", "음식", "요리"],
                "cooking": ["cooking", "요리"],
                "fitness": ["fitness", "헬스", "운동"],
                "getmotivated": ["getmotivated", "동기부여", "motivation"],
                "aww": ["aww", "귀여운", "cute"],
                "videos": ["videos", "비디오", "영상"],
                "gifs": ["gifs", "gif", "움짤"],
                "memes": ["memes", "밈", "meme"],
                "dankmemes": ["dankmemes", "댄크밈"],
                "oddlysatisfying": ["oddlysatisfying", "만족스러운"],
                "explainlikeimfive": ["explainlikeimfive", "eli5", "쉬운설명"],
                "nostupidquestions": ["nostupidquestions", "바보같은질문없다"],
                "lifehacks": ["lifehacks", "생활꿀팁", "꿀팁"],
                "iama": ["iama", "ama", "무엇이든물어보세요"],
                "casualconversation": ["casualconversation", "일상대화"],
                "relationship_advice": ["relationship_advice", "연애조언", "관계조언"],
                "korea": ["korea", "한국"],
                "hanguk": ["hanguk", "한국"],
                "korean": ["korean", "한국어", "코리안"],
                "earthporn": ["earthporn", "지구사진", "자연사진"],
                "space": ["space", "우주"],
                "history": ["history", "역사"],
                "philosophy": ["philosophy", "철학"],
                "books": ["books", "책", "독서"]
            }
            
            for subreddit, keywords in reddit_subreddits.items():
                if any(keyword_lower in keyword.lower() for keyword in keywords):
                    matches.append(subreddit)
            
            matches = list(set(matches))
            
        return {"matches": matches[:15], "auto_detected": False}
        
    except Exception as e:
        print(f"Autocomplete error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

# ==================== WebSocket 크롤링 핸들러 - 자동 크롤링 ====================
@app.websocket("/ws/auto-crawl")
async def crawl_auto_socket(websocket: WebSocket):
    """통합 자동 크롤링 WebSocket 핸들러"""
    origin = websocket.headers.get("origin", "")

    if APP_ENV == "production":
        allowed_patterns = ["netlify.app", "onrender.com"]
        origin_allowed = any(pattern in origin for pattern in allowed_patterns)
    else:
        allowed_patterns = ["netlify.app", "localhost", "127.0.0.1", "onrender.com", "file://"]
        origin_allowed = (
            any(pattern in origin for pattern in allowed_patterns) or 
            origin == "" or 
            origin == "null" or
            origin.startswith("http://localhost") or
            origin.startswith("http://127.0.0.1")
        )

    if not origin_allowed:
        logger.warning(f"❌ WebSocket Origin 거부 ({APP_ENV}): {origin}")
        await websocket.close(code=1008, reason="Invalid origin")
        return

    if APP_ENV != "production":
        logger.info(f"✅ WebSocket Origin 허용: {origin}")

    await websocket.accept()
    
    crawl_id = f"auto_{id(websocket)}_{int(time.time())}"
    print(f"🚀 새 크롤링 시작: {crawl_id}")
    
    try:
        init_data = await websocket.receive_json()
        user_lang = await get_user_language(init_data)
        
        board_input = init_data.get("board", "")
        sort = init_data.get("sort", "recent")
        start = init_data.get("start", 1)
        end = init_data.get("end", 20)
        min_views = init_data.get("min_views", 0)
        min_likes = init_data.get("min_likes", 0)
        time_filter = init_data.get("time_filter", "day")
        start_date_input = init_data.get("start_date")
        end_date_input = init_data.get("end_date")

        print(f"Auto crawl started: {board_input}")

        def check_cancelled():
            if crawl_manager.is_cancelled(crawl_id):
                raise asyncio.CancelledError(f"크롤링 {crawl_id} 취소됨")

        check_cancelled()

        detected_site = await detect_site_from_url(board_input)
        print(f"Detected site: {detected_site}")

        check_cancelled()

        actual_start_date, actual_end_date = calculate_actual_dates(
            time_filter, start_date_input, end_date_input
        )
        
        print(f"🗓️ 계산된 날짜: {actual_start_date} ~ {actual_end_date}")
        has_date_filter = bool(actual_start_date and actual_end_date)

        if detected_site != 'universal' and detected_site != 'bbc':
            board_name = extract_board_from_url(board_input, detected_site)
        else:
            if ' ' in board_input:
                parts = board_input.split(' ', 1)
                board_url = parts[0]
                board_name = parts[1] if len(parts) > 1 else ""
            else:
                board_url = board_input
                board_name = ""

        await websocket.send_json(create_localized_message(
            progress=5,
            status_key="period_filter",
            lang=user_lang,
            status_data={
                "timeFilter": time_filter,
                "dateRange": f" ({actual_start_date}~{actual_end_date})" if has_date_filter else " (전체)"
            },
            detected_site=detected_site,
            board_name=board_name
        ))

        check_cancelled()

        if has_date_filter or min_views > 0 or min_likes > 0:
            required_limit = min(end * 5, 500)
            enforce_date_limit = True
        else:
            required_limit = end + 5
            enforce_date_limit = False

        raw = None
        
        if detected_site == 'reddit':
            reddit_sort_map = {
                "popular": "hot", "recommend": "top", "recent": "new",
                "comments": "top", "top": "top", "hot": "hot", 
                "new": "new", "rising": "rising", "best": "best"
            }
            reddit_sort = reddit_sort_map.get(sort, "top")
            
            await websocket.send_json(create_localized_message(
                progress=15,
                status_key="reddit_collecting",
                lang=user_lang,
                status_data={"boardName": board_name, "sort": reddit_sort}
            ))
            
            raw = await fetch_posts_with_cancel_check(
                subreddit_name=board_name,
                limit=required_limit,
                sort=reddit_sort,
                time_filter=time_filter,
                websocket=websocket,
                min_views=min_views,
                min_likes=min_likes,
                start_date=actual_start_date,
                end_date=actual_end_date,
                enforce_date_limit=enforce_date_limit,
                start_index=start,
                end_index=end,
                crawl_id=crawl_id
            )
            
        elif detected_site == 'dcinside':
            await websocket.send_json(create_localized_message(
                progress=15,
                status_key="dcinside_collecting",
                lang=user_lang,
                status_data={"boardName": board_name, "sort": sort}
            ))

            raw = await crawl_dcinside_board_with_cancel_check(
                board_name=board_name,
                limit=required_limit,
                sort=sort,
                min_views=min_views,
                min_likes=min_likes,
                time_filter=time_filter,
                start_date=actual_start_date,
                end_date=actual_end_date,
                websocket=websocket,
                enforce_date_limit=enforce_date_limit,
                start_index=start,
                end_index=end,
                crawl_id=crawl_id
            )
            
        elif detected_site == 'blind':
            await websocket.send_json(create_localized_message(
                progress=15,
                status_key="blind_collecting",
                lang=user_lang,
                status_data={"boardName": board_name, "sort": sort}
            ))
            
            raw = await crawl_blind_board_with_cancel_check(
                board_input=board_name,
                limit=required_limit,
                sort=sort,
                min_views=min_views,
                min_likes=min_likes,
                time_filter=time_filter,
                start_date=actual_start_date,
                end_date=actual_end_date,
                websocket=websocket,
                enforce_date_limit=enforce_date_limit,
                start_index=start,
                end_index=end,
                crawl_id=crawl_id
            )
            
        elif detected_site == 'bbc': 
            await websocket.send_json(create_localized_message(
                progress=15,
                status_key="bbc_starting",
                lang=user_lang
            ))
            
            raw = await crawl_bbc_board_with_cancel_check(
                board_url=board_input,
                limit=required_limit,
                sort=sort,
                min_views=min_views,
                min_likes=min_likes,
                min_comments=0,
                time_filter=time_filter,
                start_date=actual_start_date,
                end_date=actual_end_date,
                websocket=websocket,
                board_name="",
                enforce_date_limit=enforce_date_limit,
                start_index=start,
                end_index=end,
                crawl_id=crawl_id
            )

        elif detected_site == 'lemmy': 
            await websocket.send_json(create_localized_message(
                progress=15,
                status_key="lemmy_starting",
                lang=user_lang,
                status_data={"community": board_name}
            ))

            raw = await crawl_lemmy_board_with_cancel_check(
                board_url=board_input,
                limit=required_limit,
                sort=sort,
                min_views=min_views,
                min_likes=min_likes,
                min_comments=0,
                time_filter=time_filter,
                start_date=actual_start_date,
                end_date=actual_end_date,
                websocket=websocket,
                board_name="",
                enforce_date_limit=enforce_date_limit,
                start_index=start,
                end_index=end,
                crawl_id=crawl_id
            )

        check_cancelled()
        
        await websocket.send_json(create_localized_message(
            progress=85,
            status_key="translating_posts",
            lang=user_lang,
            details_key="translating_details", 
            details_data={"count": len(raw)}
        ))

        results = []
        for idx, post in enumerate(raw, start=1):
            check_cancelled()
            
            if detected_site == 'bbc' and user_lang == 'ko':
                post['번역제목'] = await deepl_translate(post['원제목'], user_lang)
            else:
                post['번역제목'] = await deepl_translate(post['원제목'], user_lang)
            results.append(post)
            
            if len(raw) > 0:
                translation_progress = 60 + int((idx / len(raw)) * 30)
                await websocket.send_json({"progress": translation_progress})

        await websocket.send_json({
            "done": True, 
            "data": results,
            "detected_site": detected_site,
            "board_name": board_name if detected_site not in ['universal', 'bbc'] else board_url,
            "total_found": len(results),
            "date_filtered": has_date_filter,
            "summary": create_message_response(
                "complete",
                lang=user_lang,
                site=detected_site,
                count=len(results),
                start=start,
                end=start+len(results)-1,
                has_date_filter=has_date_filter,
                start_date=actual_start_date,
                end_date=actual_end_date
            )
        })
        
        print(f"Auto crawl completed: {len(results)} posts returned from {detected_site}")

    except asyncio.CancelledError:
        print(f"❌ 크롤링 취소됨: {crawl_id}")
        await websocket.send_json({
            "cancelled": True,
            "message": "크롤링이 사용자에 의해 취소되었습니다."
        })
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"❌ Auto crawl error: {e}")
        print(f"❌ Full traceback: {error_detail}")
        
        await websocket.send_json(create_error_message(
            error_key="crawling_error",
            lang=user_lang,
            error_data={"error": str(e)}
        ))
    finally:
        crawl_manager.cleanup_crawl(crawl_id)
        await websocket.close()

# ==================== WebSocket 크롤링 핸들러 - Blind ====================
@app.websocket("/ws/blind-crawl")
async def crawl_blind_socket(websocket: WebSocket):
    """Blind 전용 크롤링 WebSocket 핸들러"""
    origin = websocket.headers.get("origin", "")
    
    if APP_ENV == "production":
        allowed_patterns = ["netlify.app", "onrender.com"]
        origin_allowed = any(pattern in origin for pattern in allowed_patterns)
    else:
        allowed_patterns = ["netlify.app", "localhost", "127.0.0.1", "onrender.com", "file://"]
        origin_allowed = (
            any(pattern in origin for pattern in allowed_patterns) or 
            origin == "" or 
            origin == "null" or
            origin.startswith("http://localhost") or
            origin.startswith("http://127.0.0.1")
        )
    
    if not origin_allowed:
        logger.warning(f"❌ Blind WebSocket Origin 거부: {origin}")
        await websocket.close(code=1008, reason="Invalid origin")
        return
    
    await websocket.accept()
    
    try:
        init_data = await websocket.receive_json()
        user_lang = await get_user_language(init_data)
        
        board = init_data.get("board")
        limit = init_data.get("limit", 50)
        sort = init_data.get("sort", "recent")
        start = init_data.get("start", 1)
        end = init_data.get("end", 20)
        min_views = init_data.get("min_views", 0)
        min_likes = init_data.get("min_likes", 0)
        time_filter = init_data.get("time_filter", "day")
        start_date_input = init_data.get("start_date")
        end_date_input = init_data.get("end_date")

        actual_start_date, actual_end_date = calculate_actual_dates(
            time_filter, start_date_input, end_date_input
        )
        
        has_date_filter = bool(actual_start_date and actual_end_date)
        enforce_date_limit = has_date_filter or min_views > 0 or min_likes > 0

        print(f"Blind crawl started: {board}, sort: {sort}, range: {start}-{end}")

        if start < 1 or end < start:
            await websocket.send_json(create_error_message(
                error_key="invalid_rank_range",
                lang=user_lang
            ))
            return

        if enforce_date_limit:
            required_limit = min(end * 5, 500)
        else:
            required_limit = end + 5

        await websocket.send_json(create_localized_message(
            progress=10,
            status_key="blind_collecting",
            lang=user_lang,
            status_data={"boardName": board, "sort": sort}
        ))

        all_posts = await crawl_blind_board(
            board_input=board,
            limit=required_limit,
            sort=sort,
            min_views=min_views,
            min_likes=min_likes,
            time_filter=time_filter,
            start_date=actual_start_date,
            end_date=actual_end_date,
            websocket=websocket,
            enforce_date_limit=enforce_date_limit,
            start_index=start, 
            end_index=end       
        )

        await websocket.send_json(create_localized_message(
            progress=50,
            status_key="translating_posts",
            lang=user_lang
        ))

        results = []
        for idx, post in enumerate(all_posts, start=1):
            post['번역제목'] = await deepl_translate(post['원제목'], user_lang)
            results.append(post)

            if idx <= len(all_posts):
                progress = 50 + int((idx / len(all_posts)) * 40)
                await websocket.send_json({"progress": progress})

        await websocket.send_json({"progress": 100})
        await websocket.send_json({
            "done": True, 
            "data": results,
            "total_found": len(results),
            "summary": create_message_response(
                "complete",
                lang=user_lang,
                site="blind", 
                count=len(results),
                start=start,
                end=start+len(results)-1
            )
        })

        if not all_posts:
            await websocket.send_json(create_error_message(
                error_key="no_posts_found",
                lang=user_lang
            ))
            return

        print(f"Blind crawl completed: {len(results)} posts returned")

    except Exception as e:
        await websocket.send_json(create_error_message(
            error_key="crawling_error",
            lang=user_lang,
            error_data={"error": str(e)}
        ))

# ==================== WebSocket 크롤링 핸들러 - Reddit ====================
@app.websocket("/ws/reddit-crawl")
async def enhanced_reddit_crawl(websocket: WebSocket):
    """Reddit 전용 크롤링 WebSocket 핸들러"""
    origin = websocket.headers.get("origin", "")
    
    if APP_ENV == "production":
        allowed_patterns = ["netlify.app", "onrender.com"]
        origin_allowed = any(pattern in origin for pattern in allowed_patterns)
    else:
        allowed_patterns = ["netlify.app", "localhost", "127.0.0.1", "onrender.com", "file://"]
        origin_allowed = (
            any(pattern in origin for pattern in allowed_patterns) or 
            origin == "" or 
            origin == "null" or
            origin.startswith("http://localhost") or
            origin.startswith("http://127.0.0.1")
        )
    
    if not origin_allowed:
        logger.warning(f"❌ Reddit WebSocket Origin 거부: {origin}")
        await websocket.close(code=1008, reason="Invalid origin")
        return
        
    await websocket.accept()

    try:
        init_data = await websocket.receive_json()
        user_lang = await get_user_language(init_data)
        
        subreddit = init_data.get("board")
        sort = init_data.get("sort", "top")
        time_filter = init_data.get("time_filter", "day")
        start = init_data.get("start", 1)
        end = init_data.get("end", 20)
        
        min_views = init_data.get("min_views", 0)
        min_likes = init_data.get("min_likes", 0)
        min_comments = init_data.get("min_comments", 0)
        start_date_input = init_data.get("start_date")
        end_date_input = init_data.get("end_date")
        
        actual_start_date, actual_end_date = calculate_actual_dates(
            time_filter, start_date_input, end_date_input
        )
        
        condition_checker = SmartConditionChecker(
            min_views=min_views,
            min_likes=min_likes, 
            min_comments=min_comments,
            start_date=actual_start_date,
            end_date=actual_end_date
        )
        
        await websocket.send_json(create_localized_message(
            progress=10,
            status_key="reddit_collecting",
            lang=user_lang,
            status_data={"boardName": subreddit, "sort": sort}
        ))
        
        async def reddit_crawl_func(limit, websocket):
            return await fetch_posts(
                subreddit_name=subreddit,
                limit=limit,
                sort=sort,
                time_filter=time_filter,
                websocket=websocket,
                min_views=0,
                min_likes=0,
                start_date=actual_start_date,
                end_date=actual_end_date,
                enforce_date_limit=False,
                start_index=start,
                end_index=end
            )
        
        results = await smart_crawl_with_conditions(
            crawl_func=reddit_crawl_func,
            condition_checker=condition_checker,
            start_index=start,
            end_index=end,
            websocket=websocket
        )
        
        if not results:
            await websocket.send_json(create_error_message(
                error_key="no_posts_found",
                lang=user_lang
            ))
            return
        
        await websocket.send_json(create_localized_message(
            progress=90,
            status_key="translating_posts",
            lang=user_lang,
            details_key="translating_details",
            details_data={"count": len(results)}
        ))
        
        for idx, post in enumerate(results):
            post['번역제목'] = await deepl_translate(post['원제목'], user_lang)
            
            if len(results) > 0:
                translation_progress = 90 + int((idx + 1) / len(results) * 10)
                await websocket.send_json({"progress": translation_progress})
        
        filter_info = []
        if min_views > 0: filter_info.append(f"조회수≥{min_views}")
        if min_likes > 0: filter_info.append(f"추천≥{min_likes}")
        if min_comments > 0: filter_info.append(f"댓글≥{min_comments}")
        if actual_start_date and actual_end_date: 
            filter_info.append(f"기간:{actual_start_date}~{actual_end_date}")
        
        filter_text = f" ({', '.join(filter_info)})" if filter_info else ""
        
        await websocket.send_json({
            "done": True,
            "data": results,
            "total_found": len(results),
            "summary": create_message_response(
                "complete_filtered" if filter_info else "complete",
                lang=user_lang,
                site="reddit",
                count=len(results), 
                start=start,
                end=start+len(results)-1,
                filter_text=filter_text if filter_info else ""
            ),
            "filter_applied": len(filter_info) > 0,
            "intelligent_mode": True
        })
        
        print(f"🧠 지능적 Reddit 크롤링 완료: {len(results)} posts")
        
    except Exception as e:
        await websocket.send_json(create_error_message(
            error_key="crawling_error",
            lang=user_lang,
            error_data={"error": str(e)}
        ))

# ==================== WebSocket 크롤링 핸들러 - BBC ====================
@app.websocket("/ws/bbc-crawl")
async def crawl_bbc_socket(websocket: WebSocket):
    """BBC 전용 크롤링 WebSocket 핸들러"""
    origin = websocket.headers.get("origin", "")
    
    if APP_ENV == "production":
        allowed_patterns = ["netlify.app", "onrender.com"]
        origin_allowed = any(pattern in origin for pattern in allowed_patterns)
    else:
        allowed_patterns = ["netlify.app", "localhost", "127.0.0.1", "onrender.com", "file://"]
        origin_allowed = (
            any(pattern in origin for pattern in allowed_patterns) or 
            origin == "" or 
            origin == "null" or
            origin.startswith("http://localhost") or
            origin.startswith("http://127.0.0.1")
        )
    
    if not origin_allowed:
        logger.warning(f"❌ BBC WebSocket Origin 거부: {origin}")
        await websocket.close(code=1008, reason="Invalid origin")
        return
        
    await websocket.accept()

    try:
        init_data = await websocket.receive_json()
        user_lang = await get_user_language(init_data)
        
        board_url = init_data.get("board")
        limit = init_data.get("limit", 50)
        sort = init_data.get("sort", "recent")
        start = init_data.get("start", 1)
        end = init_data.get("end", 20)
        min_views = init_data.get("min_views", 0)
        min_likes = init_data.get("min_likes", 0)
        time_filter = init_data.get("time_filter", "day")
        start_date_input = init_data.get("start_date")
        end_date_input = init_data.get("end_date")

        actual_start_date, actual_end_date = calculate_actual_dates(
            time_filter, start_date_input, end_date_input
        )
        
        has_date_filter = bool(actual_start_date and actual_end_date)
        enforce_date_limit = has_date_filter or min_views > 0 or min_likes > 0

        print(f"BBC crawl started: {board_url}, sort: {sort}, range: {start}-{end}")

        if not board_url or 'bbc.com' not in board_url.lower():
            await websocket.send_json(create_error_message(
                error_key="invalid_bbc_url",
                lang=user_lang
            ))
            return

        if start < 1 or end < start:
            await websocket.send_json(create_error_message(
                error_key="invalid_rank_range",
                lang=user_lang
            ))
            return

        if enforce_date_limit:
            required_limit = min(end * 5, 500)
        else:
            required_limit = end + 5

        await websocket.send_json(create_localized_message(
            progress=10,
            status_key="bbc_starting",
            lang=user_lang
        ))

        all_posts = await crawl_bbc_board(
            board_url=board_url,
            limit=required_limit,
            sort=sort,
            min_views=min_views,
            min_likes=min_likes,
            min_comments=0,
            time_filter=time_filter,
            start_date=actual_start_date,
            end_date=actual_end_date,
            websocket=websocket,
            board_name="",
            enforce_date_limit=enforce_date_limit,
            start_index=start,
            end_index=end
        )
        
        if not all_posts:
            await websocket.send_json(create_error_message(
                error_key="no_posts_found",
                lang=user_lang
            ))
            return

        await websocket.send_json(create_localized_message(
            progress=70,
            status_key="translating_posts",
            lang=user_lang
        ))

        results = []
        for idx, post in enumerate(all_posts, start=1):
            post['번역제목'] = await deepl_translate(post['원제목'], user_lang)
            results.append(post)
            
            if idx <= len(all_posts):
                translation_progress = 70 + int((idx / len(all_posts)) * 25)
                await websocket.send_json({"progress": translation_progress})

        await websocket.send_json({"progress": 100})
        await websocket.send_json({
            "done": True, 
            "data": results,
            "total_found": len(results),
            "summary": create_message_response(
                "complete",
                lang=user_lang,
                site="bbc",
                count=len(results),
                start=start, 
                end=start+len(results)-1
            )
        })
        
        print(f"BBC crawl completed: {len(results)} posts returned")

    except Exception as e:
        await websocket.send_json(create_error_message(
            error_key="crawling_error",
            lang=user_lang,
            error_data={"error": str(e)}
        ))

# ==================== WebSocket 크롤링 핸들러 - DCInside ====================
@app.websocket("/ws/dcinside-crawl")
async def crawl_dcinside_socket(websocket: WebSocket):
    """DCInside 전용 크롤링 WebSocket 핸들러"""
    origin = websocket.headers.get("origin", "")
    
    if APP_ENV == "production":
        allowed_patterns = ["netlify.app", "onrender.com"]
        origin_allowed = any(pattern in origin for pattern in allowed_patterns)
    else:
        allowed_patterns = ["netlify.app", "localhost", "127.0.0.1", "onrender.com", "file://"]
        origin_allowed = (
            any(pattern in origin for pattern in allowed_patterns) or 
            origin == "" or 
            origin == "null" or
            origin.startswith("http://localhost") or
            origin.startswith("http://127.0.0.1")
        )
    
    if not origin_allowed:
        logger.warning(f"❌ DCInside WebSocket Origin 거부: {origin}")
        await websocket.close(code=1008, reason="Invalid origin")
        return
        
    await websocket.accept()

    try:
        init_data = await websocket.receive_json()
        user_lang = await get_user_language(init_data)
        
        board = init_data.get("board")
        limit = init_data.get("limit", 50)
        sort = init_data.get("sort", "recent")
        start = init_data.get("start", 1)
        end = init_data.get("end", 20)
        min_views = init_data.get("min_views", 0)
        min_likes = init_data.get("min_likes", 0)
        time_filter = init_data.get("time_filter", "day")
        start_date_input = init_data.get("start_date")
        end_date_input = init_data.get("end_date")

        actual_start_date, actual_end_date = calculate_actual_dates(
            time_filter, start_date_input, end_date_input
        )
        
        has_date_filter = bool(actual_start_date and actual_end_date)
        enforce_date_limit = has_date_filter or min_views > 0 or min_likes > 0

        print(f"DCInside crawl started: {board}, sort: {sort}, range: {start}-{end}")

        if start < 1 or end < start:
            await websocket.send_json(create_error_message(
                error_key="invalid_rank_range",
                lang=user_lang
            ))
            return

        if enforce_date_limit:
            required_limit = min(end * 5, 500)
        else:
            required_limit = end + 5

        await websocket.send_json(create_localized_message(
            progress=10,
            status_key="dcinside_collecting",
            lang=user_lang,
            status_data={"boardName": board, "sort": sort}
        ))

        all_posts = await crawl_dcinside_board(
            board_name=board, 
            limit=required_limit, 
            sort=sort,
            min_views=min_views,
            min_likes=min_likes,
            time_filter=time_filter,
            start_date=actual_start_date,
            end_date=actual_end_date,
            websocket=websocket,
            enforce_date_limit=enforce_date_limit,
            start_index=start,
            end_index=end
        )
        
        if not all_posts:
            await websocket.send_json(create_error_message(
                error_key="no_posts_found",
                lang=user_lang
            ))
            return

        await websocket.send_json(create_localized_message(
            progress=50,
            status_key="translating_posts",
            lang=user_lang
        ))

        results = []
        for idx, post in enumerate(all_posts, start=1):
            post['번역제목'] = await deepl_translate(post['원제목'], user_lang)
            results.append(post)
            
            if idx <= len(all_posts):
                translation_progress = 50 + int((idx / len(all_posts)) * 40)
                await websocket.send_json({"progress": translation_progress})

        await websocket.send_json({"progress": 100})
        await websocket.send_json({
            "done": True, 
            "data": results,
            "total_found": len(results),
            "summary": create_message_response(
                "complete",
                lang=user_lang, 
                site="dcinside",
                count=len(results),
                start=start,
                end=start+len(results)-1
            )
        })
        
        print(f"DCInside crawl completed: {len(results)} posts returned")

    except Exception as e:
        await websocket.send_json(create_error_message(
            error_key="crawling_error",
            lang=user_lang,
            error_data={"error": str(e)}
        ))

# ==================== WebSocket 크롤링 핸들러 - Lemmy ====================
@app.websocket("/ws/lemmy-crawl")
async def crawl_lemmy_socket(websocket: WebSocket):
    """Lemmy 전용 크롤링 WebSocket 핸들러"""
    origin = websocket.headers.get("origin", "")
    
    if APP_ENV == "production":
        allowed_patterns = ["netlify.app", "onrender.com"]
        origin_allowed = any(pattern in origin for pattern in allowed_patterns)
    else:
        allowed_patterns = ["netlify.app", "localhost", "127.0.0.1", "onrender.com", "file://"]
        origin_allowed = (
            any(pattern in origin for pattern in allowed_patterns) or 
            origin == "" or 
            origin == "null" or
            origin.startswith("http://localhost") or
            origin.startswith("http://127.0.0.1")
        )
    
    if not origin_allowed:
        logger.warning(f"❌ Lemmy WebSocket Origin 거부: {origin}")
        await websocket.close(code=1008, reason="Invalid origin")
        return
        
    await websocket.accept()

    try:
        init_data = await websocket.receive_json()
        user_lang = await get_user_language(init_data)
        
        community = init_data.get("board")
        limit = init_data.get("limit", 50)
        sort = init_data.get("sort", "Hot")
        start = init_data.get("start", 1)
        end = init_data.get("end", 20)
        min_views = init_data.get("min_views", 0)
        min_likes = init_data.get("min_likes", 0)
        
        time_filter = init_data.get("time_filter", "day")
        start_date_input = init_data.get("start_date")
        end_date_input = init_data.get("end_date")
        
        actual_start_date, actual_end_date = calculate_actual_dates_for_lemmy(
            time_filter, start_date_input, end_date_input
        )
        
        logger.info(f"Lemmy 크롤링 설정: time_filter={time_filter}, dates={actual_start_date}~{actual_end_date}")
        
        has_date_filter = bool(actual_start_date and actual_end_date)

        if time_filter == 'all':
            actual_start_date = None
            actual_end_date = None
            has_date_filter = False
            logger.info("전체 기간 모드: 날짜 필터링 비활성화")
        
        has_date_filter = bool(actual_start_date and actual_end_date)

        print(f"Lemmy crawl started: {community}, sort: {sort}, range: {start}-{end}")

        if not community or len(community.strip()) < 2:
            await websocket.send_json(create_error_message(
                error_key="lemmyEmpty",
                lang=user_lang
            ))
            return

        original_community = community
        if '@' not in community and '.' not in community:
            community = f"{community}@lemmy.world"
            await websocket.send_json(create_localized_message(
                progress=5,
                status_key="lemmy_connecting",
                lang=user_lang,
                status_data={"community": community}
            ))

        if start < 1 or end < start:
            await websocket.send_json(create_error_message(
                error_key="invalid_rank_range",
                lang=user_lang
            ))
            return

        if has_date_filter or min_views > 0 or min_likes > 0:
            required_limit = min(end * 5, 200)
            enforce_date_limit = True
        else:
            required_limit = end + 5
            enforce_date_limit = False

        await websocket.send_json(create_localized_message(
            progress=10,
            status_key="lemmy_starting",
            lang=user_lang,
            status_data={"community": community, "start": start, "end": end, "sort": sort}
        ))

        try:
            all_posts = await crawl_lemmy_board(
                community_input=community,
                limit=required_limit,
                sort=sort,
                min_views=min_views,
                min_likes=min_likes,
                time_filter=time_filter,
                start_date=actual_start_date,
                end_date=actual_end_date,
                websocket=websocket,
                enforce_date_limit=enforce_date_limit,
                start_index=start,
                end_index=end
            )
            
        except Exception as lemmy_error:
            await websocket.send_json(create_error_message(
                error_key="crawling_error",
                lang=user_lang,
                error_data={"error": str(lemmy_error)}
            ))
            return
        
        if not all_posts:
            await websocket.send_json(create_error_message(
                error_key="no_posts_found",
                lang=user_lang
            ))
            return

        await websocket.send_json(create_localized_message(
            progress=70,
            status_key="translating_posts",
            lang=user_lang
        ))

        if has_date_filter:
            results_to_process = all_posts
        else:
            results_to_process = all_posts[start-1:end] if start <= len(all_posts) else all_posts

        results = []
        for idx, post in enumerate(results_to_process, start=1):
            original_title = post['원제목']
            if any(ord(char) > 127 for char in original_title):
                post['번역제목'] = original_title
            else:
                post['번역제목'] = await deepl_translate(original_title, user_lang)
            
            results.append(post)
            
            if len(results_to_process) > 0:
                translation_progress = 70 + int((idx / len(results_to_process)) * 25)
                await websocket.send_json({"progress": translation_progress})

        for idx, post in enumerate(results):
            post['번호'] = start + idx

        await websocket.send_json({"progress": 100})
        
        await websocket.send_json({
            "done": True, 
            "data": results,
            "total_found": len(results),
            "date_filtered": has_date_filter,
            "community_used": community,
            "summary": create_message_response(
                "complete",
                lang=user_lang, 
                site="lemmy",
                count=len(results),
                start=start,
                end=start+len(results)-1
            )
        })
        
        print(f"✅ Lemmy crawl completed successfully: {len(results)} posts from {community}")

    except Exception as e:
        print(f"❌ Lemmy crawl critical error: {e}")
        await websocket.send_json(create_error_message(
            error_key="crawling_error",
            lang=user_lang,
            error_data={"error": str(e)}
        ))
    finally:
        await websocket.close()

# ==================== WebSocket 크롤링 핸들러 - Universal ====================
@app.websocket("/ws/universal-crawl")
async def crawl_universal_socket(websocket: WebSocket):
    """범용 크롤링 WebSocket 핸들러"""
    origin = websocket.headers.get("origin", "")
    
    if APP_ENV == "production":
        allowed_patterns = ["netlify.app", "onrender.com"]
        origin_allowed = any(pattern in origin for pattern in allowed_patterns)
    else:
        allowed_patterns = ["netlify.app", "localhost", "127.0.0.1", "onrender.com", "file://"]
        origin_allowed = (
            any(pattern in origin for pattern in allowed_patterns) or 
            origin == "" or 
            origin == "null" or
            origin.startswith("http://localhost") or
            origin.startswith("http://127.0.0.1")
        )
    
    if not origin_allowed:
        logger.warning(f"❌ Universal WebSocket Origin 거부: {origin}")
        await websocket.close(code=1008, reason="Invalid origin")
        return
        
    await websocket.accept()

    try:
        init_data = await websocket.receive_json()
        user_lang = await get_user_language(init_data)
        
        board_url = init_data.get("board")
        limit = init_data.get("limit", 50)
        sort = init_data.get("sort", "recent")
        start = init_data.get("start", 1)
        end = init_data.get("end", 20)
        min_views = init_data.get("min_views", 0)
        min_likes = init_data.get("min_likes", 0)
        time_filter = init_data.get("time_filter", "all")
        start_date_input = init_data.get("start_date")
        end_date_input = init_data.get("end_date")

        actual_start_date, actual_end_date = calculate_actual_dates(
            time_filter, start_date_input, end_date_input
        )
        
        has_date_filter = bool(actual_start_date and actual_end_date)
        enforce_date_limit = has_date_filter or min_views > 0 or min_likes > 0

        print(f"Universal crawl started: {board_url}, sort: {sort}, range: {start}-{end}")

        if not board_url or not board_url.startswith('http'):
            await websocket.send_json(create_error_message(
                error_key="universalUrlError",
                lang=user_lang
            ))
            return

        if start < 1 or end < start:
            await websocket.send_json(create_error_message(
                error_key="invalid_rank_range",
                lang=user_lang
            ))
            return

        if enforce_date_limit:
            required_limit = min(end * 5, 500)
        else:
            required_limit = end + 5

        if ' ' in board_url:
            parts = board_url.split(' ', 1)
            target_url = parts[0]
            target_board_name = parts[1]
        else:
            target_url = board_url
            target_board_name = ""

        await websocket.send_json(create_localized_message(
            progress=5,
            status_key="universal_starting",
            lang=user_lang
        ))

        all_posts = await crawl_universal_board(
            board_url=target_url,
            limit=required_limit,
            sort=sort,
            min_views=min_views,
            min_likes=min_likes,
            time_filter=time_filter,
            start_date=actual_start_date,
            end_date=actual_end_date,
            websocket=websocket,
            board_name=target_board_name,
            enforce_date_limit=enforce_date_limit,
            start_index=start,
            end_index=end
        )
        
        if not all_posts:
            await websocket.send_json(create_error_message(
                error_key="no_posts_found",
                lang=user_lang
            ))
            return

        if websocket:
            await websocket.send_json(create_localized_message(
                progress=85,
                status_key="translating_posts",
                lang=user_lang,
                details_key="translating_details",
                details_data={"count": len(all_posts)}
            ))

        results = []
        for idx, post in enumerate(all_posts, start=1):
            original_title = post['원제목']
            if any(ord(char) > 127 for char in original_title):
                post['번역제목'] = original_title
            else:
                post['번역제목'] = await deepl_translate(original_title, user_lang)
            
            results.append(post)
            
            if idx <= len(all_posts):
                translation_progress = 85 + int((idx / len(all_posts)) * 10)
                await websocket.send_json({"progress": translation_progress})

        await websocket.send_json({"progress": 100})
        await websocket.send_json({
            "done": True, 
            "data": results,
            "total_found": len(results),
            "summary": create_message_response(
                "complete",
                lang=user_lang,
                site="universal", 
                count=len(results),
                start=start,
                end=start+len(results)-1,
                has_date_filter=has_date_filter,
                start_date=actual_start_date,
                end_date=actual_end_date
            )
        })
        
        print(f"Universal crawl completed: {len(results)} posts returned")

    except Exception as e:
        print(f"Universal crawl error: {e}")
        await websocket.send_json(create_error_message(
            error_key="crawling_error",
            lang=user_lang,
            error_data={"error": str(e)}
        ))
    finally:
        await websocket.close()

# ==================== 기본 API 엔드포인트 ====================
@app.get("/health")
def health_check():
    return {"status": "healthy", "message": "Community Crawler API is running"}

@app.get("/")
def root():
    return {
        "message": "PickPost API Server", 
        "status": "running",
        "version": "1.0.0",
        "docs": "/docs"
    }

# ==================== 크롤링 취소 시스템 ====================
@app.websocket("/ws/cancel")
async def cancel_crawl_socket(websocket: WebSocket):
    await websocket.accept()
    try:
        data = await websocket.receive_json()
        crawl_id = data.get("crawl_id")
        
        if crawl_id:
            crawl_manager.cancel_crawl(crawl_id)
            await websocket.send_json({"success": True, "message": f"크롤링 {crawl_id}가 취소되었습니다."})
        else:
            await websocket.send_json({"error": "crawl_id가 필요합니다."})
    except Exception as e:
        await websocket.send_json({"error": str(e)})
    finally:
        await websocket.close()

class CancelRequest(BaseModel):
    crawl_id: str
    action: str = "cancel"

@app.post("/api/cancel-crawl")
async def cancel_crawl_endpoint(request: CancelRequest):
    """크롤링 취소 요청 처리"""
    try:
        crawl_id = request.crawl_id
        
        if not crawl_id:
            raise HTTPException(status_code=400, detail="crawl_id가 필요합니다")
        
        crawl_manager.cancel_crawl(crawl_id)
        
        print(f"📡 HTTP 취소 요청 수신: {crawl_id}")
        
        return {
            "success": True,
            "message": f"크롤링 {crawl_id} 취소 요청이 처리되었습니다",
            "crawl_id": crawl_id,
            "timestamp": time.time()
        }
        
    except Exception as e:
        print(f"❌ 취소 요청 처리 오류: {e}")
        raise HTTPException(status_code=500, detail=f"취소 요청 처리 중 오류: {str(e)}")
   
@app.get("/api/crawl-status/{crawl_id}")
async def get_crawl_status(crawl_id: str):
    """크롤링 상태 확인"""
    try:
        is_cancelled = crawl_manager.is_cancelled(crawl_id)
        
        return {
            "crawl_id": crawl_id,
            "is_cancelled": is_cancelled,
            "timestamp": time.time()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"상태 확인 중 오류: {str(e)}")

@app.get("/api/active-crawls")
async def get_active_crawls():
    """활성 크롤링 목록 반환"""
    try:
        return {
            "cancelled_crawls": list(crawl_manager.cancelled_crawls),
            "cancelled_count": len(crawl_manager.cancelled_crawls),
            "timestamp": time.time()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"활성 크롤링 조회 중 오류: {str(e)}")

@app.post("/api/cleanup-crawls")
async def cleanup_all_crawls():
    """모든 크롤링 정리"""
    try:
        cancelled_count = len(crawl_manager.cancelled_crawls)
        crawl_manager.cancelled_crawls.clear()
        
        print(f"🧹 모든 크롤링 정리 완료: {cancelled_count}개")
        
        return {
            "success": True,
            "cleaned_count": cancelled_count,
            "message": f"{cancelled_count}개의 크롤링이 정리되었습니다",
            "timestamp": time.time()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"정리 중 오류: {str(e)}")

# ==================== BBC URL 검증 API ====================
@app.post("/api/validate-bbc-url")
async def validate_bbc_url(request: dict):
    """BBC URL 유효성 검사 및 정보 추출"""
    try:
        url = request.get("url", "")
        return validate_bbc_url_info(url)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

# ==================== 피드백 시스템 ====================
class Feedback(BaseModel):
    description: str
    hasFile: Optional[bool] = False
    fileName: Optional[str] = None
    fileSize: Optional[int] = None
    systemInfo: Optional[Dict[str, Any]] = {}
    currentLanguage: Optional[str] = "ko"
    currentSite: Optional[str] = None
    url: Optional[str] = None
    timestamp: Optional[str] = None

class SimpleFeedback(BaseModel):
    message: str

@app.post("/api/feedback")
async def submit_feedback(request: Request):
    """개선된 피드백 처리 - 다양한 형태의 데이터 수용"""
    try:
        raw_data = await request.json()
        
        feedback_dir = "outputs/feedback"
        os.makedirs(feedback_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        client_ip = request.client.host

        if "description" in raw_data:
            feedback_content = raw_data.get("description", "").strip()
            
            if not feedback_content:
                return JSONResponse(
                    status_code=400, 
                    content={"error": "피드백 내용이 비어있습니다."}
                )
            
            feedback_data = {
                "type": "enhanced",
                "timestamp": timestamp,
                "ip": client_ip,
                "content": feedback_content,
                "metadata": {
                    "hasFile": raw_data.get("hasFile", False),
                    "fileName": raw_data.get("fileName"),
                    "fileSize": raw_data.get("fileSize"),
                    "currentLanguage": raw_data.get("currentLanguage", "ko"),
                    "currentSite": raw_data.get("currentSite"),
                    "url": raw_data.get("url"),
                    "clientTimestamp": raw_data.get("timestamp"),
                    "systemInfo": raw_data.get("systemInfo", {})
                }
            }
            
        elif "message" in raw_data:
            feedback_content = raw_data.get("message", "").strip()
            
            if not feedback_content:
                return JSONResponse(
                    status_code=400, 
                    content={"error": "메시지가 비어있습니다."}
                )
            
            feedback_data = {
                "type": "simple",
                "timestamp": timestamp,
                "ip": client_ip,
                "content": feedback_content,
                "metadata": {}
            }
            
        else:
            return JSONResponse(
                status_code=400, 
                content={
                    "error": "올바른 피드백 형식이 아닙니다. 'description' 또는 'message' 필드가 필요합니다.",
                    "received_fields": list(raw_data.keys())
                }
            )

        filename = f"feedback_{timestamp}_{feedback_data['type']}.json"
        filepath = os.path.join(feedback_dir, filename)
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(feedback_data, f, ensure_ascii=False, indent=2)

        print(f"📝 새로운 피드백 수신:")
        print(f"   📁 파일: {filename}")
        print(f"   📍 IP: {client_ip}")
        print(f"   🌐 언어: {feedback_data.get('metadata', {}).get('currentLanguage', 'N/A')}")
        print(f"   📏 길이: {len(feedback_content)}자")
        print(f"   📄 내용 미리보기: {feedback_content[:100]}{'...' if len(feedback_content) > 100 else ''}")

        return {
            "status": "success", 
            "message": "피드백이 성공적으로 저장되었습니다.",
            "feedback_id": timestamp,
            "type": feedback_data["type"]
        }

    except json.JSONDecodeError:
        return JSONResponse(
            status_code=400, 
            content={"error": "잘못된 JSON 형식입니다."}
        )
    except Exception as e:
        print(f"❌ 피드백 처리 오류: {e}")
        return JSONResponse(
            status_code=500, 
            content={"error": f"서버 오류가 발생했습니다: {str(e)}"}
        )

@app.get("/api/feedback/{feedback_id}")
async def get_feedback_detail(feedback_id: str):
    """특정 피드백 상세 정보 조회"""
    try:
        feedback_dir = "outputs/feedback"
        
        for filename in os.listdir(feedback_dir):
            if filename.startswith(f"feedback_{feedback_id}") and filename.endswith(".json"):
                filepath = os.path.join(feedback_dir, filename)
                
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data
        
        return JSONResponse(
            status_code=404,
            content={"error": f"피드백 {feedback_id}를 찾을 수 없습니다."}
        )
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"피드백 조회 오류: {str(e)}"}
        )

# ==================== 애플리케이션 시작 이벤트 ====================
@app.on_event("startup")
async def startup_event():
    """앱 시작시 실행"""
    print("🚀 크롤링 매니저 초기화 완료")
    
    import asyncio
    
    async def periodic_cleanup():
        while True:
            await asyncio.sleep(3600)
            crawl_manager.cleanup_old_crawls()
    
    asyncio.create_task(periodic_cleanup())

print("✅ 크롤링 취소 시스템 설정 완료")
print("📡 사용 가능한 엔드포인트:")
print("  - POST /api/cancel-crawl - 크롤링 취소")
print("  - GET /api/crawl-status/{crawl_id} - 상태 확인")
print("  - GET /api/active-crawls - 활성 크롤링 목록")
print("  - POST /api/cleanup-crawls - 전체 정리")

# ==================== 서버 시작 로직 ====================
if __name__ == "__main__":
    import uvicorn
    
    validate_environment()
    
    port = int(os.environ.get("PORT", 8000))
    
    logger.info(f"🚀 서버 시작:")
    logger.info(f"  환경: {APP_ENV}")
    logger.info(f"  포트: {port}")
    logger.info(f"  호스트: 0.0.0.0")
    logger.info(f"  로그 레벨: {LOG_LEVEL}")
    
    if APP_ENV == "production":
        logger.info("🌐 프로덕션 모드 - CORS 제한 활성화")
        allowed_origins = get_cors_origins()
        logger.info(f"  허용된 Origins: {allowed_origins}")
        
        uvicorn.run(
            app,
            host="0.0.0.0", 
            port=port,   
            log_level=LOG_LEVEL.lower(),
            access_log=True,
            timeout_keep_alive=30,
            timeout_graceful_shutdown=30
        )
    else:
        logger.info("🔧 개발 모드 - CORS 개방")
        uvicorn.run(
            app,
            host="0.0.0.0", 
            port=port,
            reload=True,
            log_level=LOG_LEVEL.lower()
        )