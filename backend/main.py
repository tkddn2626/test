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


load_dotenv()

DEEPL_API_KEY = os.getenv("DEEPL_API_KEY")
APP_ENV = os.getenv("APP_ENV", "development")
DEBUG = os.getenv("DEBUG", "False").lower() == "true"
PORT = int(os.getenv("PORT", 8000))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000")

# 로깅 설정
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('app.log') if APP_ENV == "production" else logging.StreamHandler()
    ]
)

# 전역 로거 생성
logger = logging.getLogger("pickpost")

# 🔧 환경별 설정 출력
if DEBUG:
    logger.debug(f"🔧 환경 설정:")
    logger.debug(f"  APP_ENV: {APP_ENV}")
    logger.debug(f"  DEBUG: {DEBUG}")
    logger.debug(f"  PORT: {PORT}")
    logger.debug(f"  ALLOWED_ORIGINS: {ALLOWED_ORIGINS}")
    logger.debug(f"  LOG_LEVEL: {LOG_LEVEL}")
    logger.debug(f"  DEEPL_API_KEY: {'설정됨' if DEEPL_API_KEY else '미설정'}")

# 전역 로거 설정
'''logger = logging.getLogger("lemmy_logger")
logger.setLevel(logging.INFO)

# 콘솔 출력 핸들러 설정
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

# 중복 방지
if not logger.hasHandlers():
    logger.addHandler(handler)'''

def create_message_response(message_key: str, **data):
    """번역 가능한 메시지 응답 생성"""
    return {
        "message_key": message_key,
        "message_data": data,
        "message_type": "crawl"
    }

app = FastAPI(
    title="PickPost API",
    debug=DEBUG  # 🔥 DEBUG 변수 사용
)
# 1. 동적 CORS 설정 함수 추가
def get_cors_origins():
    """환경별 CORS 도메인 설정"""
    base_origins = os.getenv("ALLOWED_ORIGINS", "").split(",")
    
    # 기본 도메인들
    default_origins = [
        "http://localhost:3000",
        "http://localhost:8000", 
        "http://127.0.0.1:8000",
        "https://127.0.0.1:8000"
    ]
    
    # Netlify 도메인 패턴 추가
    netlify_patterns = [
        "https://pickpost.netlify.app",
        "https://pickpost--*.netlify.app",  # 브랜치 배포
        "https://*.netlify.app"  # 다른 앱들
    ]
    
    all_origins = default_origins + netlify_patterns
    
    
    # .env에서 가져온 도메인들 추가
    for origin in base_origins:
        if origin.strip():
            all_origins.append(origin.strip())
    
    return list(set(all_origins))  # 중복 제거

# APP_ENV에 따른 CORS 정책 구분
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


@app.middleware("http")
async def dynamic_cors_middleware(request: Request, call_next):
    """동적 CORS 처리"""
    origin = request.headers.get("origin")
    
    response = await call_next(request)
    
    # Netlify 도메인 체크
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


class CrawlManager:
    """크롤링 작업 관리 클래스 (확장됨)"""
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
        """오래된 크롤링 정리 (1시간 이상된 것들)"""
        # 실제 구현시 크롤링 시작 시간을 추적해야 함
        # 지금은 단순히 모든 취소된 크롤링을 정리
        old_count = len(self.cancelled_crawls)
        self.cancelled_crawls.clear()
        print(f"🧹 오래된 크롤링 정리: {old_count}개")
        return old_count

# 전역 크롤링 매니저
crawl_manager = CrawlManager()

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
        
        # 날짜 검사
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
        # 🔥 핵심: 날짜 필터 유무에 따른 중단 임계값 조정
        fail_threshold = 10 if has_date_filter else 20
        
        if consecutive_fails >= fail_threshold:
            return True, CrawlStopReason.CONDITION_NOT_MET
        
        return False, CrawlStopReason.COMPLETED

async def smart_crawl_with_conditions(crawl_func, condition_checker: SmartConditionChecker,
                                    start_index: int, end_index: int, websocket=None):
    """조건 기반 지능적 크롤링"""
    progress = CrawlProgress()
    all_posts = []
    matched_posts = []
    
    try:
        # 🚀 1단계: 여유있게 크롤링 (조건 필터링 고려)
        has_filters = (condition_checker.min_views > 0 or 
                      condition_checker.min_likes > 0 or 
                      condition_checker.min_comments > 0 or
                      (condition_checker.start_dt and condition_checker.end_dt))
        
        if has_filters:
            # 필터가 있으면 더 많이 수집
            crawl_limit = min(end_index * 3, 200)
        else:
            # 필터가 없으면 정확히
            crawl_limit = end_index + 5
        
        if websocket:
            await websocket.send_json({
                "progress": 20,
                "status": f"🎯 지능적 크롤링 시작",
                "details": f"필터 {'있음' if has_filters else '없음'}, 수집량: {crawl_limit}개"
            })
        
        # 🚀 2단계: 실제 크롤링 실행
        raw_posts = await crawl_func(limit=crawl_limit, websocket=websocket)
        
        if not raw_posts:
            return []
        
        # 🚀 3단계: 조건 기반 필터링
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
                
                # 목표 달성 시 조기 종료
                if len(matched_posts) >= (end_index - start_index + 1):
                    break
            else:
                progress.consecutive_fails += 1
                
                # 🔥 지능적 중단 판단
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
        
        # 🚀 4단계: 정확한 범위 적용
        final_posts = matched_posts[start_index-1:end_index] if start_index <= len(matched_posts) else matched_posts
        
        # 번호 재부여
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

def calculate_actual_dates(time_filter: str, start_date_input: str = None, end_date_input: str = None):
    """시간 필터를 실제 날짜로 변환하는 함수 - 더 정확한 로직"""
    from datetime import datetime, timedelta
    
    now = datetime.now()
    
    if time_filter == 'custom' and start_date_input and end_date_input:
        return start_date_input, end_date_input
        
    elif time_filter == 'hour':
        # 🔥 수정: '1시간' → 최근 1시간 (오늘만)
        start_date = now.strftime('%Y-%m-%d')
        end_date = now.strftime('%Y-%m-%d')
        
    elif time_filter == 'day':
        # 🔥 수정: '1일' → 오늘 하루만 엄격하게
        start_date = now.strftime('%Y-%m-%d')
        end_date = now.strftime('%Y-%m-%d')
        
    elif time_filter == 'week':
        # 정확히 7일 전부터
        start_dt = now - timedelta(days=7)
        start_date = start_dt.strftime('%Y-%m-%d')
        end_date = now.strftime('%Y-%m-%d')
        
    elif time_filter == 'month':
        # 정확히 30일 전부터
        start_dt = now - timedelta(days=30)
        start_date = start_dt.strftime('%Y-%m-%d')
        end_date = now.strftime('%Y-%m-%d')
        
    elif time_filter == 'year':
        # 정확히 365일 전부터
        start_dt = now - timedelta(days=365)
        start_date = start_dt.strftime('%Y-%m-%d')
        end_date = now.strftime('%Y-%m-%d')
        
    else:  # 'all'
        # 전체 기간 - None 반환하여 필터링 없음 명시
        return None, None
    
    # 🔥 디버깅 로그 업데이트
    print(f"📅 시간 필터 '{time_filter}' → 날짜 범위: {start_date} ~ {end_date}")
    
    return start_date, end_date

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
        elif is_bbc_domain(url):  # 🔥 BBC 모듈 함수 사용
            return 'bbc'
        elif any(lemmy_domain in domain for lemmy_domain in 
                ['lemmy.', 'beehaw.', 'sh.itjust.works', 'feddit.', 'lemm.ee']):
            return 'lemmy'
        else:
            return 'universal'
            
    except Exception as e:
        print(f"URL 파싱 오류: {e}")
        return 'universal'

def calculate_actual_dates_for_lemmy(time_filter: str, start_date_input: str = None, end_date_input: str = None):
    """Lemmy용 시간 필터를 실제 날짜로 변환하는 함수"""
    from datetime import datetime, timedelta
    
    today = datetime.now()
    
    if time_filter == 'custom' and start_date_input and end_date_input:
        # 사용자 지정 날짜
        return start_date_input, end_date_input
        
    elif time_filter == 'hour':
        # 최근 1시간 → 오늘만
        return today.strftime('%Y-%m-%d'), today.strftime('%Y-%m-%d')
        
    elif time_filter == 'day':
        # 🔥 핵심 수정: 오늘 하루만
        return today.strftime('%Y-%m-%d'), today.strftime('%Y-%m-%d')
        
    elif time_filter == 'week':
        # 최근 일주일
        start_dt = today - timedelta(days=7)
        return start_dt.strftime('%Y-%m-%d'), today.strftime('%Y-%m-%d')
        
    elif time_filter == 'month':
        # 최근 한 달
        start_dt = today - timedelta(days=30)
        return start_dt.strftime('%Y-%m-%d'), today.strftime('%Y-%m-%d')
        
    elif time_filter == 'year':
        # 최근 일년
        start_dt = today - timedelta(days=365)
        return start_dt.strftime('%Y-%m-%d'), today.strftime('%Y-%m-%d')
        
    else:  # 'all'
        # 전체 기간 - 날짜 없음
        return None, None

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
            # Lemmy 커뮤니티 URL 처리
            if '/c/' in url:
                parts = url.split('/c/')
                if len(parts) > 1:
                    community_part = parts[1].split('/')[0]
                    domain = urlparse(url).netloc
                    return f"{community_part}@{domain}"
            return url
        else:
            # 범용 크롤러의 경우 전체 URL 반환
            return url
    except Exception as e:
        print(f"게시판 추출 오류: {e}")
        return url



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
            # 비동기 함수를 동기적으로 실행
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


@app.get("/autocomplete/{site}")
async def autocomplete(site: str, keyword: str = Query(...)):
    keyword = keyword.strip()
    matches = []
    
    # 🎯 BBC URL 자동 감지 우선 처리 (BBC 모듈 사용)
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
            "auto_switch_site": True,  # 🔥 사이트 자동 전환 플래그
            "switch_message": bbc_detection["switch_message"],
            "suggestion": f"자동으로 BBC 크롤러로 전환됩니다: {bbc_detection['board_name']}"
        }
    
    # 일반 URL 감지 (기존 로직 유지)
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



async def fetch_posts_with_cancel_check(*args, crawl_id=None, **kwargs):
    """Reddit 크롤링에 취소 확인 추가"""
    if crawl_id and crawl_manager.is_cancelled(crawl_id):
        raise asyncio.CancelledError("크롤링이 취소되었습니다")
    
    # 기존 함수 호출 (crawl_id 제거)
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

# 기존 BBC 취소 확인 함수를 찾아서 간단히 수정:
async def crawl_bbc_board_with_cancel_check(board_url: str, crawl_id=None, **kwargs):
    """BBC 크롤링에 취소 확인 추가 (간단 버전)"""
    if crawl_id and crawl_manager.is_cancelled(crawl_id):
        raise asyncio.CancelledError("크롤링이 취소되었습니다")
    
    # 🔥 bbc.py의 안정성 크롤러 사용
    from bbc import crawl_bbc_board
    return await crawl_bbc_board(board_url=board_url, **kwargs)


async def crawl_lemmy_board_with_cancel_check(*args, crawl_id=None, **kwargs):
    """Lemmy 크롤링에 취소 확인 추가 (🔥 버그 수정)"""
    if crawl_id and crawl_manager.is_cancelled(crawl_id):
        raise asyncio.CancelledError("크롤링이 취소되었습니다")
    
    kwargs.pop('crawl_id', None)
    # 🔥 중요 수정: crawl_bbc_board → crawl_lemmy_board
    return await crawl_lemmy_board(*args, **kwargs)


# 🔧 기존 auto-crawl WebSocket 핸들러 수정 (기존 코드 기반)
@app.websocket("/ws/auto-crawl")
async def crawl_auto_socket(websocket: WebSocket):

    origin = websocket.headers.get("origin", "")
    
    if not (
        "netlify.app" in origin or 
        "localhost" in origin or
        "127.0.0.1" in origin or
        "onrender.com" in origin or  # 추가
        origin == ""  # 추가 - Origin 없는 경우도 허용
    ):
        print(f"❌ Origin 거부: {origin}")  # 추가 - 디버깅용
        await websocket.close(code=1008, reason="Invalid origin")
        return
    
    print(f"✅ Origin 허용: {origin}")  # 추가 - 디버깅용
    await websocket.accept()
    
    # 고유 크롤링 ID 생성
    crawl_id = f"auto_{id(websocket)}_{int(time.time())}"
    print(f"🚀 새 크롤링 시작: {crawl_id}")
    
    try:
        # 🔥 기존 init_data 수신 로직 유지
        init_data = await websocket.receive_json()
        board_input = init_data.get("board", "")
        sort = init_data.get("sort", "recent")
        lang = init_data.get("language", "ko")
        start = init_data.get("start", 1)
        end = init_data.get("end", 20)
        min_views = init_data.get("min_views", 0)
        min_likes = init_data.get("min_likes", 0)
        time_filter = init_data.get("time_filter", "day")
        start_date_input = init_data.get("start_date")
        end_date_input = init_data.get("end_date")

        print(f"Auto crawl started: {board_input}")

        # 🔥 취소 확인 함수 정의
        def check_cancelled():
            if crawl_manager.is_cancelled(crawl_id):
                raise asyncio.CancelledError(f"크롤링 {crawl_id} 취소됨")

        # 초기 취소 확인
        check_cancelled()

        detected_site = await detect_site_from_url(board_input)
        print(f"Detected site: {detected_site}")

        # 취소 확인
        check_cancelled()

        # 🔥 기존 날짜 계산 로직 유지
        actual_start_date, actual_end_date = calculate_actual_dates(
            time_filter, start_date_input, end_date_input
        )
        
        

        print(f"🗓️ 계산된 날짜: {actual_start_date} ~ {actual_end_date}")
        has_date_filter = bool(actual_start_date and actual_end_date)

        # 게시판명 추출 로직 유지
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

        await websocket.send_json({
            "detected_site": detected_site,
            "board_name": board_name if detected_site not in ['universal', 'bbc'] else board_url,
            "progress": 5,
            "status": f"🔧 기간: {time_filter}" + (f" ({actual_start_date}~{actual_end_date})" if has_date_filter else " (전체)")
        })

        # 취소 확인
        check_cancelled()

        # 🔥 기존 크롤링 로직 유지하되 취소 확인 추가
        if has_date_filter or min_views > 0 or min_likes > 0:
            required_limit = min(end * 5, 500)
            enforce_date_limit = True
        else:
            required_limit = end + 5
            enforce_date_limit = False

        # 각 사이트별 크롤링 실행 (기존 함수 호출에 crawl_id만 추가)
        raw = None
        
        if detected_site == 'reddit':
            reddit_sort_map = {
                "popular": "hot", "recommend": "top", "recent": "new",
                "comments": "top", "top": "top", "hot": "hot", 
                "new": "new", "rising": "rising", "best": "best"
            }
            reddit_sort = reddit_sort_map.get(sort, "top")
            
            await websocket.send_json({
                "status": f"🔍 Reddit r/{board_name} - {reddit_sort} 정렬로 수집 중...",
                "progress": 15
            })
            
            # 🔥 기존 함수 호출에 취소 확인만 추가
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
                crawl_id=crawl_id  # 🔥 추가
            )
            
        elif detected_site == 'dcinside':
            await websocket.send_json({
                "status": f"🔍 DCInside {board_name} 갤러리 수집 중... ({sort})",
                "progress": 15
            })

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
                crawl_id=crawl_id  # 🔥 추가
            )
            
        elif detected_site == 'blind':
            await websocket.send_json({
                "status": f"🔍 Blind {board_name} 토픽 수집 중... ({sort})",
                "progress": 15
            })

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
                crawl_id=crawl_id  # 🔥 추가
            )
            
        elif detected_site == 'bbc': 
            await websocket.send_json({
                "status": f"🛡️ BBC 안정성 크롤러 시작...",
                "progress": 15
            })
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
            await websocket.send_json({
                "status": f"lemmy 크롤링 시작...",
                "progress": 15
            })

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

        # 최종 취소 확인
        check_cancelled()

        if not raw:
            await websocket.send_json({
                "error": create_message_response("no_matching_posts", site=detected_site),
                "details": f"사이트: {detected_site}, 기간: {actual_start_date or 'N/A'}~{actual_end_date or 'N/A'}"
            })
            return

        # 🔥 기존 번역 로직 유지
        results = []
        for idx, post in enumerate(raw, start=1):
            check_cancelled()  # 번역 중에도 취소 확인
            
            if detected_site == 'bbc' and lang == 'ko':
                post['번역제목'] = await deepl_translate(post['원제목'], lang)
            else:
                post['번역제목'] = await deepl_translate(post['원제목'], lang)
            results.append(post)
            
            if len(raw) > 0:
                translation_progress = 60 + int((idx / len(raw)) * 30)
                await websocket.send_json({"progress": translation_progress})

        # 최종 성공 응답 (기존과 동일)
        await websocket.send_json({
            "done": True, 
            "data": results,
            "detected_site": detected_site,
            "board_name": board_name if detected_site not in ['universal', 'bbc'] else board_url,
            "total_found": len(results),
            "date_filtered": has_date_filter,
            "summary": create_message_response(
                "crawl_complete",
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
        print(f"Auto crawl error: {e}")
        await websocket.send_json({
            "error": f"크롤링 중 오류가 발생했습니다: {str(e)}"
        })
    finally:
        crawl_manager.cleanup_crawl(crawl_id)
        await websocket.close()

@app.websocket("/ws/blind-crawl")
async def crawl_blind_socket(websocket: WebSocket):
    await websocket.accept()
    try:
        init_data = await websocket.receive_json()
        board = init_data.get("board")
        limit = init_data.get("limit", 50)
        sort = init_data.get("sort", "recent")
        lang = init_data.get("language", "ko")
        start = init_data.get("start", 1)
        end = init_data.get("end", 20)
        min_views = init_data.get("min_views", 0)
        min_likes = init_data.get("min_likes", 0)
        time_filter = init_data.get("time_filter", "day")
        start_date_input = init_data.get("start_date")
        end_date_input = init_data.get("end_date")

        # 🔥 통일된 날짜 계산
        actual_start_date, actual_end_date = calculate_actual_dates(
            time_filter, start_date_input, end_date_input
        )
        
        has_date_filter = bool(actual_start_date and actual_end_date)
        enforce_date_limit = has_date_filter or min_views > 0 or min_likes > 0

        print(f"Blind crawl started: {board}, sort: {sort}, range: {start}-{end}")

        if start < 1 or end < start:
            await websocket.send_json({"error": "잘못된 순위 범위입니다."})
            return

        # 🔥 정확한 개수만 크롤링
        if enforce_date_limit:
            required_limit = min(end * 5, 500)
        else:
            required_limit = end + 5

        await websocket.send_json({"progress": 10})

        # 🔥 수정: start_index, end_index 파라미터 추가
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

        if not all_posts:
            await websocket.send_json({"error": create_message_response("no_posts_found", site=detected_site)})
            return

        await websocket.send_json({"progress": 50})

        results = []
        for idx, post in enumerate(all_posts, start=1):
            post['번역제목'] = await deepl_translate(post['원제목'], lang)
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
                "crawl_complete",
                site="blind", 
                count=len(results),
                start=start,
                end=start+len(results)-1
            )
        })

        print(f"Blind crawl completed: {len(results)} posts returned")

    except Exception as e:
        print(f"Blind crawl error: {e}")
        await websocket.send_json({"error": f"크롤링 중 오류가 발생했습니다: {str(e)}"})
    finally:
        await websocket.close()


@app.websocket("/ws/reddit-crawl")
async def enhanced_reddit_crawl(websocket: WebSocket):
    await websocket.accept()
    try:
        init_data = await websocket.receive_json()
        
        # 기본 파라미터
        subreddit = init_data.get("board")
        sort = init_data.get("sort", "top")
        time_filter = init_data.get("time_filter", "day")
        lang = init_data.get("language", "ko")
        start = init_data.get("start", 1)
        end = init_data.get("end", 20)
        
        # 🔥 개선: 조건 파라미터
        min_views = init_data.get("min_views", 0)
        min_likes = init_data.get("min_likes", 0)
        min_comments = init_data.get("min_comments", 0)
        start_date_input = init_data.get("start_date")
        end_date_input = init_data.get("end_date")
        
        # 🔥 통일된 날짜 계산
        actual_start_date, actual_end_date = calculate_actual_dates(
            time_filter, start_date_input, end_date_input
        )
        
        # 🔥 조건 검사기 생성
        condition_checker = SmartConditionChecker(
            min_views=min_views,
            min_likes=min_likes, 
            min_comments=min_comments,
            start_date=actual_start_date,
            end_date=actual_end_date
        )
        
        await websocket.send_json({
            "progress": 10,
            "status": f"🧠 지능적 크롤링 모드 활성화",
            "details": f"조건: 조회수≥{min_views}, 추천≥{min_likes}, 댓글≥{min_comments}"
        })
        
        # 🔥 지능적 크롤링 실행
        async def reddit_crawl_func(limit, websocket):
            return await fetch_posts(
                subreddit_name=subreddit,
                limit=limit,
                sort=sort,
                time_filter=time_filter,
                websocket=websocket,
                min_views=0,  # 여기서는 0으로, 나중에 조건 검사기에서 필터링
                min_likes=0,
                start_date=actual_start_date,
                end_date=actual_end_date,
                enforce_date_limit=False,  # 조건 검사기에서 처리
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
            await websocket.send_json({
                "error": "설정한 조건에 맞는 게시물을 찾을 수 없습니다.",
                "suggestion": "조건을 완화하거나 기간을 늘려보세요."
            })
            return
        
        # 번역 처리
        await websocket.send_json({
            "progress": 90,
            "status": "🌐 번역 처리 중...",
            "details": f"{len(results)}개 게시물"
        })
        
        for idx, post in enumerate(results):
            post['번역제목'] = await deepl_translate(post['원제목'], lang)
            
            if len(results) > 0:
                translation_progress = 90 + int((idx + 1) / len(results) * 10)
                await websocket.send_json({"progress": translation_progress})
        
        # 🔥 개선된 완료 메시지
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
                "crawl_complete_filtered" if filter_info else "crawl_complete",
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
        print(f"Reddit crawl error: {e}")
        await websocket.send_json({
            "error": f"크롤링 중 오류가 발생했습니다: {str(e)}"
        })
    finally:
        await websocket.close()

@app.websocket("/ws/bbc-crawl")
async def crawl_bbc_socket(websocket: WebSocket):
    await websocket.accept()
    try:
        init_data = await websocket.receive_json()
        board_url = init_data.get("board")
        limit = init_data.get("limit", 50)
        sort = init_data.get("sort", "recent")
        lang = init_data.get("language", "ko")
        start = init_data.get("start", 1)
        end = init_data.get("end", 20)
        min_views = init_data.get("min_views", 0)
        min_likes = init_data.get("min_likes", 0)
        time_filter = init_data.get("time_filter", "day")
        start_date_input = init_data.get("start_date")
        end_date_input = init_data.get("end_date")

        # 🔥 통일된 날짜 계산
        actual_start_date, actual_end_date = calculate_actual_dates(
            time_filter, start_date_input, end_date_input
        )
        
        has_date_filter = bool(actual_start_date and actual_end_date)
        enforce_date_limit = has_date_filter or min_views > 0 or min_likes > 0

        print(f"BBC crawl started: {board_url}, sort: {sort}, range: {start}-{end}")

        # BBC URL 검증
        if not board_url or 'bbc.com' not in board_url.lower():
            await websocket.send_json({
                "error": "올바른 BBC 뉴스 URL을 입력해주세요. (예: https://www.bbc.com/business)"
            })
            return

        if start < 1 or end < start:
            await websocket.send_json({"error": "잘못된 순위 범위입니다."})
            return

        # 🔥 정확한 개수만 크롤링
        if enforce_date_limit:
            required_limit = min(end * 5, 500)
        else:
            required_limit = end + 5

        await websocket.send_json({"progress": 10})

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
            await websocket.send_json({"error": "BBC 뉴스 기사를 찾을 수 없습니다."})
            return

        await websocket.send_json({"progress": 70})

        results = []
        for idx, post in enumerate(all_posts, start=1):
            # BBC는 영어이므로 한국어로 번역
            post['번역제목'] = await deepl_translate(post['원제목'], lang)
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
                "crawl_complete",
                site="bbc",
                count=len(results),
                start=start, 
                end=start+len(results)-1
            )
        })
        
        print(f"BBC crawl completed: {len(results)} posts returned")

    except Exception as e:
        print(f"BBC crawl error: {e}")
        await websocket.send_json({"error": f"BBC 크롤링 중 오류가 발생했습니다: {str(e)}"})
    finally:
        await websocket.close()


@app.websocket("/ws/dcinside-crawl")
async def crawl_dcinside_socket(websocket: WebSocket):
    await websocket.accept()
    try:
        init_data = await websocket.receive_json()
        board = init_data.get("board")
        limit = init_data.get("limit", 50)
        sort = init_data.get("sort", "recent")
        lang = init_data.get("language", "ko")
        start = init_data.get("start", 1)
        end = init_data.get("end", 20)
        min_views = init_data.get("min_views", 0)
        min_likes = init_data.get("min_likes", 0)
        time_filter = init_data.get("time_filter", "day")
        start_date_input = init_data.get("start_date")
        end_date_input = init_data.get("end_date")

        # 🔥 통일된 날짜 계산
        actual_start_date, actual_end_date = calculate_actual_dates(
            time_filter, start_date_input, end_date_input
        )
        
        has_date_filter = bool(actual_start_date and actual_end_date)
        enforce_date_limit = has_date_filter or min_views > 0 or min_likes > 0

        print(f"DCInside crawl started: {board}, sort: {sort}, range: {start}-{end}")

        if start < 1 or end < start:
            await websocket.send_json({"error": "잘못된 순위 범위입니다."})
            return

        # 🔥 정확한 개수만 크롤링
        if enforce_date_limit:
            required_limit = min(end * 5, 500)
        else:
            required_limit = end + 5

        await websocket.send_json({"progress": 10})

        # 🔥 수정: start_index, end_index 파라미터 추가
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
            start_index=start,  # 🔥 추가
            end_index=end       # 🔥 추가
        )
        
        if not all_posts:
            await websocket.send_json({"error": create_message_response("no_posts_found", site=detected_site)})
            return

        await websocket.send_json({"progress": 50})

        results = []
        for idx, post in enumerate(all_posts, start=1):
            post['번역제목'] = await deepl_translate(post['원제목'], lang)
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
                "crawl_complete", 
                site="dcinside",
                count=len(results),
                start=start,
                end=start+len(results)-1
            )
        })
        
        print(f"DCInside crawl completed: {len(results)} posts returned")

    except Exception as e:
        print(f"DCInside crawl error: {e}")
        await websocket.send_json({"error": f"크롤링 중 오류가 발생했습니다: {str(e)}"})
    finally:
        await websocket.close()

@app.websocket("/ws/lemmy-crawl")
async def crawl_lemmy_socket(websocket: WebSocket):
    await websocket.accept()
    try:
        init_data = await websocket.receive_json()
        community = init_data.get("board")
        limit = init_data.get("limit", 50)
        sort = init_data.get("sort", "Hot")
        lang = init_data.get("language", "ko")
        start = init_data.get("start", 1)
        end = init_data.get("end", 20)
        min_views = init_data.get("min_views", 0)
        min_likes = init_data.get("min_likes", 0)
        
        time_filter = init_data.get("time_filter", "day")
        start_date_input = init_data.get("start_date")
        end_date_input = init_data.get("end_date")
        
        # 날짜 계산
        actual_start_date, actual_end_date = calculate_actual_dates_for_lemmy(
            time_filter, start_date_input, end_date_input
        )
        
        # 🔥 디버깅 로그 추가
        logger.info(f"Lemmy 크롤링 설정: time_filter={time_filter}, dates={actual_start_date}~{actual_end_date}")
        
        has_date_filter = bool(actual_start_date and actual_end_date)

        # 🔥 중복 날짜 필터링 방지
        if time_filter == 'all':
            # 전체 기간일 때는 날짜 필터링 완전 비활성화
            actual_start_date = None
            actual_end_date = None
            has_date_filter = False
            logger.info("전체 기간 모드: 날짜 필터링 비활성화")
        
        has_date_filter = bool(actual_start_date and actual_end_date)

        print(f"Lemmy crawl started: {community}, sort: {sort}, range: {start}-{end}")

        # 🔥 개선된 입력 검증
        if not community or len(community.strip()) < 2:
            await websocket.send_json({
                "error": """❌ 올바른 Lemmy 커뮤니티를 입력해주세요.

✅ 올바른 형식:
• technology@lemmy.world
• asklemmy@lemmy.ml  
• programming@programming.dev

🌟 추천 안정적인 커뮤니티:
• asklemmy@lemmy.ml (질문/답변)
• worldnews@lemmy.ml (뉴스)
• programming@programming.dev (프로그래밍)"""
            })
            return

        # 🔥 자동 보정 기능
        original_community = community
        if '@' not in community and '.' not in community:
            community = f"{community}@lemmy.world"
            await websocket.send_json({
                "progress": 5,
                "status": f"🔄 자동 보정: {original_community} → {community}",
                "details": "기본 인스턴스를 추가했습니다"
            })

        if start < 1 or end < start:
            await websocket.send_json({"error": "❌ 잘못된 순위 범위입니다. (시작 ≥ 1, 끝 ≥ 시작)"})
            return

        if has_date_filter or min_views > 0 or min_likes > 0:
            required_limit = min(end * 5, 200)
            enforce_date_limit = True
        else:
            required_limit = end + 5
            enforce_date_limit = False

        await websocket.send_json({
            "progress": 10,
            "status": f"🌐 Lemmy 크롤링 시작: {community}",
            "details": f"범위: {start}-{end}위, 정렬: {sort}"
        })

        # 🔥 향상된 에러 처리와 대안 제안
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
            error_msg = str(lemmy_error)
            
            # 🔥 에러 유형별 맞춤 메시지
            if "올바르지 않은 Lemmy 커뮤니티 형식" in error_msg:
                suggested_alternatives = []
                community_name = community.split('@')[0] if '@' in community else community
                
                # 대안 커뮤니티 제안
                alternatives = [
                    f"{community_name}@lemmy.ml",
                    f"{community_name}@beehaw.org", 
                    f"{community_name}@sh.itjust.works",
                    "asklemmy@lemmy.ml",
                    "technology@lemmy.world",
                    "programming@programming.dev"
                ]
                
                await websocket.send_json({
                    "error": f"""❌ Lemmy 커뮤니티 '{community}'에 접근할 수 없습니다.

🔄 다음 대안들을 시도해보세요:

🎯 같은 커뮤니티, 다른 인스턴스:
• {community_name}@lemmy.ml
• {community_name}@beehaw.org
• {community_name}@programming.dev

🌟 안정적인 대안 커뮤니티:
• asklemmy@lemmy.ml (질문/답변, 매우 안정적)
• worldnews@lemmy.ml (뉴스, 활발함)
• technology@lemmy.world (기술, 인기)

🔧 범용 크롤러 사용:
• 사이트: "범용 크롤러" 선택
• URL: https://lemmy.world/c/{community_name}""",
                    "alternatives": alternatives,
                    "original_input": original_community
                })
                
            elif "인스턴스" in error_msg.lower():
                # 인스턴스 문제
                community_name = community.split('@')[0] if '@' in community else community
                await websocket.send_json({
                    "error": f"""❌ 인스턴스 연결 문제가 발생했습니다.

🔄 다른 인스턴스로 시도해보세요:
• {community_name}@lemmy.ml (원조, 안정적)
• {community_name}@lemmy.world (대형, 다양함) 
• {community_name}@beehaw.org (커뮤니티 중심)

⏰ 잠시 후 다시 시도해보세요:
인스턴스가 일시적으로 과부하 상태일 수 있습니다.""",
                    "retry_suggestions": [
                        f"{community_name}@lemmy.ml",
                        f"{community_name}@lemmy.world", 
                        f"{community_name}@beehaw.org"
                    ]
                })
                
            elif "게시물" in error_msg and ("없습니다" in error_msg or "가져올 수 없습니다" in error_msg):
                # 게시물 부족 문제
                await websocket.send_json({
                    "error": f"""❌ '{community}' 커뮤니티에서 충분한 게시물을 찾을 수 없습니다.

💡 해결 방법:
1️⃣ 순위 범위 줄이기: 1-5위로 시도
2️⃣ 기간 늘리기: "일주일" 또는 "전체"로 변경  
3️⃣ 필터 조건 완화: 최소 추천수/조회수 낮추기

🌟 활발한 대안 커뮤니티:
• asklemmy@lemmy.ml (항상 활발함)
• worldnews@lemmy.ml (매일 업데이트)
• memes@lemmy.ml (인기 콘텐츠)""",
                    "quick_fixes": {
                        "range": "1-5",
                        "period": "week", 
                        "min_filters": 0
                    }
                })
            else:
                # 일반적인 에러
                await websocket.send_json({
                    "error": f"""❌ Lemmy 크롤링 중 오류가 발생했습니다.

오류 내용: {error_msg}

🔄 권장 해결책:
1. asklemmy@lemmy.ml 로 테스트 (가장 안정적)
2. 범위를 1-5로 줄여서 재시도
3. 범용 크롤러로 대체 시도

🆘 지속적인 문제 시:
• 네트워크 연결 확인
• 잠시 후 다시 시도
• 다른 Lemmy 인스턴스 사용""",
                    "test_community": "asklemmy@lemmy.ml"
                })
            return
        
        if not all_posts:
            await websocket.send_json({
                "error": f"""❌ '{community}' 커뮤니티에서 게시물을 찾을 수 없습니다.

🔍 가능한 원인:
• 커뮤니티가 비어있거나 비활성 상태
• 설정한 순위 범위({start}-{end})에 게시물 부족
• 필터 조건이 너무 까다로움

💡 즉시 해결책:
1️⃣ asklemmy@lemmy.ml 시도 (검증된 활성 커뮤니티)
2️⃣ 순위를 1-5로 줄이기
3️⃣ 최소 조건들 제거하기""",
                "quick_test": "asklemmy@lemmy.ml"
            })
            return

        await websocket.send_json({"progress": 70})

        # 번역 및 결과 처리
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
                post['번역제목'] = await deepl_translate(original_title, lang)
            
            results.append(post)
            
            if len(results_to_process) > 0:
                translation_progress = 70 + int((idx / len(results_to_process)) * 25)
                await websocket.send_json({"progress": translation_progress})

        # 번호 정확히 부여
        for idx, post in enumerate(results):
            post['번호'] = start + idx

        await websocket.send_json({"progress": 100})
        
        await websocket.send_json({
            "done": True, 
            "data": results,
            "total_found": len(results),
            "date_filtered": has_date_filter,
            "community_used": community,
            "success_tips": "다음에는 asklemmy@lemmy.ml 같은 안정적인 커뮤니티도 시도해보세요!",
            "summary": create_message_response(
                "crawl_complete", 
                site="lemmy",
                count=len(results),
                start=start,
                end=start+len(results)-1
            )
        })
        
        print(f"✅ Lemmy crawl completed successfully: {len(results)} posts from {community}")

    except Exception as e:
        print(f"❌ Lemmy crawl critical error: {e}")
        await websocket.send_json({
            "error": f"""❌ 예상치 못한 오류가 발생했습니다.

🔧 즉시 시도해볼 방법:
1. asklemmy@lemmy.ml 커뮤니티로 테스트
2. 브라우저 새로고침 후 재시도  
3. 범용 크롤러로 대체

🆘 기술적 오류: {str(e)}"""
        })
    finally:
        await websocket.close()


@app.websocket("/ws/universal-crawl")
async def crawl_universal_socket(websocket: WebSocket):
    await websocket.accept()
    try:
        init_data = await websocket.receive_json()
        board_url = init_data.get("board")
        limit = init_data.get("limit", 50)
        sort = init_data.get("sort", "recent")
        lang = init_data.get("language", "ko")
        start = init_data.get("start", 1)
        end = init_data.get("end", 20)
        min_views = init_data.get("min_views", 0)
        min_likes = init_data.get("min_likes", 0)
        time_filter = init_data.get("time_filter", "all")
        start_date_input = init_data.get("start_date")
        end_date_input = init_data.get("end_date")

        # 🔥 통일된 날짜 계산
        actual_start_date, actual_end_date = calculate_actual_dates(
            time_filter, start_date_input, end_date_input
        )
        
        has_date_filter = bool(actual_start_date and actual_end_date)
        enforce_date_limit = has_date_filter or min_views > 0 or min_likes > 0

        print(f"Universal crawl started: {board_url}, sort: {sort}, range: {start}-{end}")

        if not board_url or not board_url.startswith('http'):
            await websocket.send_json({
                "error": "올바른 URL을 입력해주세요. (http:// 또는 https://로 시작)"
            })
            return

        if start < 1 or end < start:
            await websocket.send_json({"error": "잘못된 순위 범위입니다."})
            return

        # 🔥 정확한 개수만 크롤링
        if enforce_date_limit:
            required_limit = min(end * 5, 500)
        else:
            required_limit = end + 5

        # board_url을 URL과 게시판명으로 분리
        if ' ' in board_url:
            parts = board_url.split(' ', 1)
            target_url = parts[0]
            target_board_name = parts[1]
        else:
            target_url = board_url
            target_board_name = ""

        await websocket.send_json({"progress": 5})

        # 🔥 수정: start_index, end_index 파라미터 추가
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
            start_index=start,  # 🔥 추가
            end_index=end       # 🔥 추가
        )
        
        if not all_posts:
            await websocket.send_json({
                "error": "게시물을 찾을 수 없습니다. URL이 올바른 게시판 페이지인지 확인해주세요."
            })
            return

        # 번역 처리
        if websocket:
            await websocket.send_json({
                "progress": 85,
                "status": "🌐 번역 처리 중...",
                "details": f"{len(all_posts)}개 게시물 번역"
            })

        results = []
        for idx, post in enumerate(all_posts, start=1):
            # 번역 처리
            original_title = post['원제목']
            if any(ord(char) > 127 for char in original_title):
                post['번역제목'] = original_title  # 이미 한국어인 경우
            else:
                post['번역제목'] = await deepl_translate(original_title, lang)
            
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
                "crawl_complete",
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
        await websocket.send_json({"error": f"크롤링 중 오류가 발생했습니다: {str(e)}"})
    finally:
        await websocket.close()


@app.get("/health")
def health_check():
    return {"status": "healthy", "message": "Community Crawler API is running"}

'''@app.get("/")
def serve_frontend():
    try:
        if os.path.exists("frontend/index.html"):
            return FileResponse("frontend/index.html")
        elif os.path.exists("index.html"):
            return FileResponse("index.html")
        else:
            return {"message": "Community Crawler API", "version": "1.0", "note": "index.html not found"}
    except Exception as e:
        print(f"Frontend serving error: {e}")
        return {"message": "Community Crawler API", "version": "1.0", "error": str(e)}

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Community Crawler API...")
    print("📡 Frontend: http://localhost:8000")
    print("📚 API Docs: http://localhost:8000/docs")
    print("🔧 Features:")
    print("   - 📅 Custom date range support for all sites")
    print("   - 📊 Min views/likes filtering")
    print("   - 🌐 Multi-language support")
    print("   - 🔍 Smart autocomplete")
    print("   - 📱 Responsive UI design")
    print("   - 🔀 Advanced sorting for all sites")
    print("   - 📋 metadata display (date, views, likes)")
    print("   - 💬 Comments sorting support")
    print("   - 🌐 Universal crawler for any website")
    print("   - 🔗 Lemmy federated network support")
    print("   - 🤖 Auto-detection of site types from URLs")
    uvicorn.run(app, host="0.0.0.0", port=8000)'''

@app.get("/")
def root():
    return {
        "message": "PickPost API Server", 
        "status": "running",
        "version": "1.0.0",
        "docs": "/docs"
    }

# WebSocket 메시지 처리 핸들러 추가
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

# 기존 크롤링 함수들에 취소 확인 추가하는 데코레이터
def check_cancellation(func):
    """크롤링 함수에 취소 확인 기능을 추가하는 데코레이터"""
    async def wrapper(*args, crawl_id=None, websocket=None, **kwargs):
        if crawl_id and crawl_manager.is_cancelled(crawl_id):
            if websocket:
                await websocket.send_json({"cancelled": True, "message": "크롤링이 취소되었습니다."})
            return []
        
        # 함수 실행 중간에도 취소 확인
        result = await func(*args, **kwargs)
        
        if crawl_id and crawl_manager.is_cancelled(crawl_id):
            if websocket:
                await websocket.send_json({"cancelled": True, "message": "크롤링이 취소되었습니다."})
            return []
        
        return result
    return wrapper

# 취소 요청을 위한 데이터 모델
class CancelRequest(BaseModel):
    crawl_id: str
    action: str = "cancel"

# 🔥 크롤링 취소 HTTP 엔드포인트 추가
@app.post("/api/cancel-crawl")
async def cancel_crawl_endpoint(request: CancelRequest):
    """크롤링 취소 요청 처리"""
    try:
        crawl_id = request.crawl_id
        
        if not crawl_id:
            raise HTTPException(status_code=400, detail="crawl_id가 필요합니다")
        
        # 크롤링 취소 마킹
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
    
# 🔥 크롤링 상태 확인 엔드포인트 (디버깅용)
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

# 🔥 활성 크롤링 목록 확인 엔드포인트 (관리용)
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

# 🔥 크롤링 매니저 정리 엔드포인트 (관리용)
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
    
# 🔥 주기적 정리 작업 (선택사항)
@app.on_event("startup")
async def startup_event():
    """앱 시작시 실행"""
    print("🚀 크롤링 매니저 초기화 완료")
    
    # 선택적: 주기적으로 오래된 크롤링 정리
    import asyncio
    
    async def periodic_cleanup():
        while True:
            await asyncio.sleep(3600)  # 1시간마다
            crawl_manager.cleanup_old_crawls()
    
    # 백그라운드 작업으로 실행
    asyncio.create_task(periodic_cleanup())

print("✅ 크롤링 취소 시스템 설정 완료")
print("📡 사용 가능한 엔드포인트:")
print("  - POST /api/cancel-crawl - 크롤링 취소")
print("  - GET /api/crawl-status/{crawl_id} - 상태 확인")
print("  - GET /api/active-crawls - 활성 크롤링 목록")
print("  - POST /api/cleanup-crawls - 전체 정리")


@app.post("/api/validate-bbc-url")
async def validate_bbc_url(request: dict):
    """BBC URL 유효성 검사 및 정보 추출"""
    try:
        url = request.get("url", "")
        # 🔥 BBC 모듈 함수 사용 (한 줄!)
        return validate_bbc_url_info(url)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

from fastapi import Request
from pydantic import BaseModel

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
        # 원시 JSON 데이터 받기
        raw_data = await request.json()
        
        feedback_dir = "outputs/feedback"
        os.makedirs(feedback_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        client_ip = request.client.host

        # 🔥 데이터 정규화 및 검증
        if "description" in raw_data:
            # 향상된 피드백 (프론트엔드에서 오는 상세 데이터)
            feedback_content = raw_data.get("description", "").strip()
            
            if not feedback_content:
                return JSONResponse(
                    status_code=400, 
                    content={"error": "피드백 내용이 비어있습니다."}
                )
            
            # 전체 데이터 구조 보존
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
            # 단순 피드백 (기존 호환성)
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

        # 🔥 피드백 저장
        filename = f"feedback_{timestamp}_{feedback_data['type']}.json"
        filepath = os.path.join(feedback_dir, filename)
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(feedback_data, f, ensure_ascii=False, indent=2)

        # 🔥 콘솔에 요약 출력
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

# 🔥 선택사항: 특정 피드백 상세 조회
@app.get("/api/feedback/{feedback_id}")
async def get_feedback_detail(feedback_id: str):
    """특정 피드백 상세 정보 조회"""
    try:
        feedback_dir = "outputs/feedback"
        
        # 파일명 패턴 매칭
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

if __name__ == "__main__":
    import uvicorn
    
    port = int(os.environ.get("PORT", 8000))
    
    print(f"🚀 서버 시작: 포트 {port}")
    print(f"🔧 환경: {APP_ENV}")
    print(f"📡 바인딩: 0.0.0.0:{port}")
    
    # 🔧 환경별 서버 설정
    if APP_ENV == "production":
        logger.info("🚀 프로덕션 모드로 서버 시작")
        uvicorn.run(
            app,
            host="0.0.0.0", 
            port=port,   
            log_level=LOG_LEVEL.lower(),
            access_log=False,
            timeout_keep_alive=30,
            timeout_graceful_shutdown=30
        )
    else:
        logger.info("🔧 개발 모드로 서버 시작")
        uvicorn.run(
            app,
            host="0.0.0.0", 
            port=port,
            reload=True,
            log_level=LOG_LEVEL.lower()
        )
