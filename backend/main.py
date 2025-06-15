# main.py - 자동 감지 기반 엔드포인트 시스템 적용

from fastapi import FastAPI, WebSocket, Query, Request
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional, Dict, Set, Tuple, Optional, Any
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

# ==================== 🔥 NEW: 통합 크롤링 시스템 ====================
import core.messages 
import core.utils
import core.auto_crawler
import core.site_detector

from core.site_detector import SiteDetector
from core.auto_crawler import AutoCrawler
from core.utils import (
    create_localized_message, 
    create_error_message, 
    create_message_response,
    get_user_language,
    calculate_actual_dates,
    calculate_actual_dates_for_lemmy
)

# ==================== 크롤링 관리 시스템 ====================
class CrawlManager:
    """크롤링 작업 관리 클래스"""
    def __init__(self):
        self.cancelled_crawls: Set[str] = set()
        self.creation_time = time.time()
    
    def cancel_crawl(self, crawl_id: str):
        """크롤링 작업 취소 마킹"""
        self.cancelled_crawls.add(crawl_id)
        logger.info(f"🚫 크롤링 취소 요청: {crawl_id} (총 {len(self.cancelled_crawls)}개 취소됨)")
    
    def is_cancelled(self, crawl_id: str) -> bool:
        """크롤링이 취소되었는지 확인"""
        return crawl_id in self.cancelled_crawls
    
    def cleanup_crawl(self, crawl_id: str):
        """크롤링 정리"""
        removed = crawl_id in self.cancelled_crawls
        self.cancelled_crawls.discard(crawl_id)
        if removed:
            logger.info(f"🧹 크롤링 정리: {crawl_id} (남은 취소된 크롤링: {len(self.cancelled_crawls)}개)")
    
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
        logger.info(f"🧹 오래된 크롤링 정리: {old_count}개")
        return old_count

# 크롤링 매니저 인스턴스 생성
crawl_manager = CrawlManager()

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
        logger.error("DeepL 번역 오류:", e)
        return "(번역 실패)"

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

# ==================== 애플리케이션 생명주기 관리 ====================
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 생명주기 관리"""
    # 시작시 실행
    logger.info("🔥 PickPost v2.0 크롤링 시스템 시작")
    logger.info("🚀 크롤링 매니저 초기화 완료")
    logger.info("🔄 통합 크롤링 엔드포인트 활성화")
    
    # 주기적 정리 작업 시작
    async def periodic_cleanup():
        while True:
            await asyncio.sleep(3600)  # 1시간마다
            crawl_manager.cleanup_old_crawls()
    
    cleanup_task = asyncio.create_task(periodic_cleanup())
    
    try:
        yield  # 애플리케이션 실행
    finally:
        # 종료시 실행
        logger.info("🛑 PickPost v2.0 크롤링 시스템 종료")
        cleanup_task.cancel()
        try:
            await cleanup_task
        except asyncio.CancelledError:
            logger.info("✅ 정리 작업 취소 완료")

# ==================== FastAPI 앱 초기화 ====================
app = FastAPI(
    title="PickPost API",
    debug=DEBUG,
    lifespan=lifespan
)

# ==================== 🔥 자동 엔드포인트 시스템 초기화 ====================
# 🚨 중요: app과 crawl_manager가 정의된 후에 호출
try:
    from core.endpoints import create_simple_endpoint_manager
    
    # 자동 엔드포인트 매니저 생성 - 모든 크롤러 자동 감지 및 엔드포인트 생성
    endpoint_manager = create_simple_endpoint_manager(app, crawl_manager)
    
    logger.info("✅ 자동 엔드포인트 시스템 초기화 완료")
    logger.info(f"📡 자동 생성된 엔드포인트: {len(endpoint_manager.crawlers)}개 크롤러")
    
    # 감지된 크롤러 정보 로깅
    for site_type, crawler_info in endpoint_manager.crawlers.items():
        logger.info(f"  🎯 {site_type}: /ws/{site_type}-crawl")
    
    # 통합 엔드포인트 확인
    logger.info("🔥 통합 엔드포인트:")
    logger.info("  📡 /ws/crawl - 자동 감지 + 통합 크롤링")
    logger.info("  🔍 /ws/analyze - 사이트 분석 전용")
    
except ImportError as e:
    logger.error(f"❌ core.simple_endpoints 모듈을 찾을 수 없습니다: {e}")
    logger.warning("⚠️ 레거시 엔드포인트만 사용됩니다")
    endpoint_manager = None
except Exception as e:
    logger.error(f"❌ 자동 엔드포인트 시스템 초기화 실패: {e}")
    logger.warning("⚠️ 레거시 엔드포인트만 사용됩니다")
    endpoint_manager = None

# ==================== CORS 설정 ====================
def get_cors_origins():
    """환경별 CORS 도메인 설정"""
    if APP_ENV == "production":
        base_origins = os.getenv("ALLOWED_ORIGINS", "").split(",")
        production_origins = [
            "https://pickpost.netlify.app",
            "https://pickpost--*.netlify.app"
            "https:testfdd.netlify.app"
            "https:testfdd--*.netlify.app"
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
            "https://testfdd.netlify.app"
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
        logger.error(f"Topics API error: {e}")
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
        logger.error(f"Search API error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

# ==================== 자동완성 API ====================
@app.get("/autocomplete/{site}")
async def autocomplete(site: str, keyword: str = Query(...)):
    keyword = keyword.strip()
    matches = []
    
    # BBC URL 감지 로직
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
    
    # URL 감지 로직
    if keyword.startswith('http'):
        site_detector = SiteDetector()
        detected_site = await site_detector.detect_site_type(keyword)
        board_name = site_detector.extract_board_identifier(keyword, detected_site)
        
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
                    # 기본 매치 목록 사용
                    matches = [
                        "블라블라", "회사생활", "자유토크", "개발자", "경력개발", 
                        "취업/이직", "스타트업", "회사와사람들", "디자인", "금융/재테크",
                        "부동산", "결혼/육아", "여행", "음식", "건강", "연애", "게임",
                        "주식", "암호화폐", "IT/기술", "AI/머신러닝"
                    ]
                    matches = [name for name in matches if keyword_lower in name.lower()]
            except Exception as e:
                logger.warning(f"Blind 자동완성 오류: {e}")
                matches = []
                
        elif site == "dcinside":
            try:
                gallery_map = load_gallery_map()
                if gallery_map:
                    matches = [name for name in gallery_map.keys() if keyword_lower in name.lower()]
                else:
                    # 기본 매치 목록 사용
                    matches = [
                        "싱글벙글", "유머", "정치", "축구", "야구", "농구", "배구",
                        "게임", "리그오브레전드", "오버워치", "스타크래프트",
                        "PC게임", "모바일게임", "애니메이션", "만화", "영화", "드라마",
                        "음악", "아이돌", "케이팝", "힙합", "요리", "여행", "사진"
                    ]
                    matches = [name for name in matches if keyword_lower in name.lower()]
            except Exception as e:
                logger.warning(f"DCInside 자동완성 오류: {e}")
                matches = []
                
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
                "gaming": ["gaming", "게임", "game"],
                "movies": ["movies", "영화", "movie"],
                "music": ["music", "음악"]
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
                "technology": ["technology", "기술", "tech"],
                "programming": ["programming", "프로그래밍", "코딩", "개발"],
                "korea": ["korea", "한국"],
                "korean": ["korean", "한국어", "코리안"]
            }
            
            for subreddit, keywords in reddit_subreddits.items():
                if any(keyword_lower in keyword.lower() for keyword in keywords):
                    matches.append(subreddit)
            
            matches = list(set(matches))
            
        return {"matches": matches[:15], "auto_detected": False}
        
    except Exception as e:
        logger.error(f"Autocomplete error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

# ==================== 🔥 NEW: 통합 크롤링 엔드포인트 ====================
# 📝 주의: 자동 엔드포인트 시스템이 성공적으로 초기화된 경우 
# 이 엔드포인트들은 자동 생성된 것으로 대체됩니다.

if endpoint_manager is None:
    # 자동 시스템이 실패한 경우에만 수동 엔드포인트 생성
    logger.warning("⚠️ 자동 엔드포인트 시스템이 비활성화됨 - 수동 엔드포인트 생성")
    
    @app.websocket("/ws/crawl")
    async def unified_crawl_endpoint(websocket: WebSocket):
        """🔥 통합 크롤링 WebSocket 엔드포인트 (수동 버전)"""
        origin = websocket.headers.get("origin", "")

        # Origin 검증 (기존 로직과 동일)
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
            logger.warning(f"❌ 통합 WebSocket Origin 거부 ({APP_ENV}): {origin}")
            await websocket.close(code=1008, reason="Invalid origin")
            return

        await websocket.accept()
        
        crawl_id = f"unified_{id(websocket)}_{int(time.time())}"
        logger.info(f"🔥 새 통합 크롤링 시작: {crawl_id}")
        
        try:
            # 설정 데이터 수신
            config = await websocket.receive_json()
            user_lang = await get_user_language(config)
            
            input_data = config.get("input", "")
            sort = config.get("sort", "recent")
            start_index = config.get("start", 1)
            end_index = config.get("end", 20)
            min_views = config.get("min_views", 0)
            min_likes = config.get("min_likes", 0)
            min_comments = config.get("min_comments", 0)
            time_filter = config.get("time_filter", "day")
            start_date_input = config.get("start_date")
            end_date_input = config.get("end_date")
            
            logger.info(f"통합 크롤링 요청: {input_data}, sort: {sort}, range: {start_index}-{end_index}")

            # 취소 확인
            def check_cancelled():
                if crawl_manager.is_cancelled(crawl_id):
                    raise asyncio.CancelledError(f"크롤링 {crawl_id} 취소됨")

            check_cancelled()

            # 날짜 범위 계산
            actual_start_date, actual_end_date = calculate_actual_dates(
                time_filter, start_date_input, end_date_input
            )
            
            # AutoCrawler 인스턴스 생성 및 설정
            auto_crawler = AutoCrawler()
            
            # 크롤링 설정 구성
            crawl_config = {
                'websocket': websocket,
                'sort': sort,
                'start_index': start_index,
                'end_index': end_index,
                'min_views': min_views,
                'min_likes': min_likes,
                'min_comments': min_comments,
                'time_filter': time_filter,
                'start_date': actual_start_date,
                'end_date': actual_end_date,
                'crawl_id': crawl_id
            }

            # 사이트 감지 진행률 업데이트
            await websocket.send_json(create_localized_message(
                progress=5,
                status_key="detecting_site",
                lang=user_lang,
                status_data={"input": input_data}
            ))

            check_cancelled()

            # 통합 크롤링 실행
            raw_posts = await auto_crawler.crawl(input_data, **crawl_config)
            
            if not raw_posts:
                await websocket.send_json(create_error_message(
                    error_key="no_posts_found",
                    lang=user_lang
                ))
                return

            # 번역 진행률 업데이트
            await websocket.send_json(create_localized_message(
                progress=85,
                status_key="translating_posts",
                lang=user_lang,
                details_key="translating_details", 
                details_data={"count": len(raw_posts)}
            ))

            # 번역 처리
            results = []
            for idx, post in enumerate(raw_posts):
                check_cancelled()
                
                original_title = post['원제목']
                # 한국어가 포함된 경우 번역하지 않음
                if any(ord(char) > 127 for char in original_title):
                    post['번역제목'] = original_title
                else:
                    post['번역제목'] = await deepl_translate(original_title, user_lang)
                    
                results.append(post)
                
                if len(raw_posts) > 0:
                    translation_progress = 85 + int((idx + 1) / len(raw_posts) * 15)
                    await websocket.send_json({"progress": translation_progress})

            # 최종 결과 전송
            detected_site = await auto_crawler.site_detector.detect_site_type(input_data)
            
            await websocket.send_json({
                "done": True, 
                "data": results,
                "detected_site": detected_site,
                "total_found": len(results),
                "unified_mode": True,  # 통합 모드임을 표시
                "summary": create_message_response(
                    "unified_complete",
                    lang=user_lang,
                    site=detected_site,
                    count=len(results),
                    start=start_index,
                    end=start_index+len(results)-1,
                    input=input_data
                )
            })
            
            logger.info(f"🔥 통합 크롤링 완료: {len(results)}개 게시물 ({detected_site})")

        except asyncio.CancelledError:
            logger.info(f"❌ 통합 크롤링 취소됨: {crawl_id}")
            await websocket.send_json({
                "cancelled": True,
                "message": "통합 크롤링이 사용자에 의해 취소되었습니다."
            })
        except Exception as e:
            error_detail = traceback.format_exc()
            logger.error(f"❌ 통합 크롤링 오류: {e}")
            logger.error(f"❌ Full traceback: {error_detail}")
            
            await websocket.send_json(create_error_message(
                error_key="unified_crawling_error",
                lang=user_lang,
                error_data={"error": str(e)}
            ))
        finally:
            crawl_manager.cleanup_crawl(crawl_id)
            await websocket.close()

    # ==================== 🔍 NEW: 사이트 분석 전용 엔드포인트 ====================
    @app.websocket("/ws/analyze")
    async def analyze_site_endpoint(websocket: WebSocket):
        """🔍 사이트 분석 전용 WebSocket 엔드포인트"""
        await websocket.accept()
        
        try:
            data = await websocket.receive_json()
            input_data = data.get("input", "")
            user_lang = data.get("language", "en")
            
            # 사이트 감지 및 분석
            site_detector = SiteDetector()
            detected_site = await site_detector.detect_site_type(input_data)
            board_identifier = site_detector.extract_board_identifier(input_data, detected_site)
            
            # 분석 결과 전송
            analysis_result = {
                "input": input_data,
                "detected_site": detected_site,
                "board_identifier": board_identifier,
                "is_url": input_data.startswith('http'),
                "analysis_complete": True
            }
            
            # BBC의 경우 추가 정보 제공
            if detected_site == 'bbc':
                bbc_info = detect_bbc_url_and_extract_info(input_data)
                analysis_result.update({
                    "bbc_info": bbc_info,
                    "section": bbc_info.get("section"),
                    "description": bbc_info.get("description")
                })
            
            await websocket.send_json(analysis_result)
            
        except Exception as e:
            await websocket.send_json({
                "error": "사이트 분석 중 오류가 발생했습니다.",
                "error_detail": str(e)
            })
        finally:
            await websocket.close()

else:
    logger.info("✅ 자동 엔드포인트 시스템 활성화됨 - 수동 엔드포인트 생략")

# ==================== LEGACY WebSocket 엔드포인트들 (하위 호환성 유지) ====================

@app.websocket("/ws/auto-crawl")
async def crawl_auto_socket(websocket: WebSocket):
    """통합 자동 크롤링 WebSocket 핸들러 (기존 호환성 유지)"""
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
    logger.info(f"🚀 새 크롤링 시작: {crawl_id}")
    
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

        logger.info(f"Auto crawl started: {board_input}")

        def check_cancelled():
            if crawl_manager.is_cancelled(crawl_id):
                raise asyncio.CancelledError(f"크롤링 {crawl_id} 취소됨")

        check_cancelled()

        # 사이트 감지 (하위 호환성을 위해 기존 로직 유지)
        site_detector = SiteDetector()
        detected_site = await site_detector.detect_site_type(board_input)
        logger.info(f"Detected site: {detected_site}")

        check_cancelled()

        actual_start_date, actual_end_date = calculate_actual_dates(
            time_filter, start_date_input, end_date_input
        )
        
        logger.info(f"🗓️ 계산된 날짜: {actual_start_date} ~ {actual_end_date}")
        has_date_filter = bool(actual_start_date and actual_end_date)

        if detected_site != 'universal' and detected_site != 'bbc':
            board_name = site_detector.extract_board_identifier(board_input, detected_site)
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
                community_input=board_input,
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

        elif detected_site == 'universal':
            await websocket.send_json(create_localized_message(
                progress=15,
                status_key="universal_starting",
                lang=user_lang
            ))
            
            raw = await crawl_universal_board(
                board_url=board_input,
                limit=required_limit,
                sort=sort,
                min_views=min_views,
                min_likes=min_likes,
                time_filter=time_filter,
                start_date=actual_start_date,
                end_date=actual_end_date,
                websocket=websocket,
                board_name=board_name,
                enforce_date_limit=enforce_date_limit,
                start_index=start,
                end_index=end
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
        
        logger.info(f"Auto crawl completed: {len(results)} posts returned from {detected_site}")

    except asyncio.CancelledError:
        logger.info(f"❌ 크롤링 취소됨: {crawl_id}")
        await websocket.send_json({
            "cancelled": True,
            "message": "크롤링이 사용자에 의해 취소되었습니다."
        })
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        logger.error(f"❌ Auto crawl error: {e}")
        logger.error(f"❌ Full traceback: {error_detail}")
        
        await websocket.send_json(create_error_message(
            error_key="crawling_error",
            lang=user_lang,
            error_data={"error": str(e)}
        ))
    finally:
        crawl_manager.cleanup_crawl(crawl_id)
        await websocket.close()

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
        
        logger.info(f"📡 HTTP 취소 요청 수신: {crawl_id}")
        
        return {
            "success": True,
            "message": f"크롤링 {crawl_id} 취소 요청이 처리되었습니다",
            "crawl_id": crawl_id,
            "timestamp": time.time()
        }
        
    except Exception as e:
        logger.error(f"❌ 취소 요청 처리 오류: {e}")
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
        
        logger.info(f"🧹 모든 크롤링 정리 완료: {cancelled_count}개")
        
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

# ==================== 🔥 NEW: 시스템 정보 API ====================
@app.get("/api/system-info")
async def get_system_info():
    """시스템 정보 및 통계 반환"""
    try:
        crawl_stats = crawl_manager.get_stats()
        
        system_info = {
            "system": {
                "version": "2.0.0",
                "environment": APP_ENV,
                "debug_mode": DEBUG,
                "unified_mode": True,  # 통합 크롤링 지원
                "uptime_seconds": crawl_stats["uptime_seconds"],
                "auto_endpoint_system": endpoint_manager is not None
            },
            "endpoints": {
                "unified": "/ws/crawl",  # 새로운 통합 엔드포인트
                "analyze": "/ws/analyze",  # 사이트 분석 전용
                "legacy": [
                    "/ws/auto-crawl",
                    "/ws/reddit-crawl",
                    "/ws/dcinside-crawl", 
                    "/ws/blind-crawl",
                    "/ws/bbc-crawl",
                    "/ws/lemmy-crawl",
                    "/ws/universal-crawl"
                ]
            },
            "supported_sites": [
                "reddit", "dcinside", "blind", "bbc", "lemmy", "universal"
            ],
            "crawl_manager": crawl_stats,
            "features": {
                "auto_site_detection": True,
                "smart_conditions": True,
                "multi_language": True,
                "cancellation_support": True,
                "progress_tracking": True
            }
        }
        
        # 자동 엔드포인트 시스템 정보 추가
        if endpoint_manager:
            system_info["auto_endpoints"] = {
                "status": "active",
                "crawlers_detected": len(endpoint_manager.crawlers),
                "crawlers": list(endpoint_manager.crawlers.keys())
            }
        else:
            system_info["auto_endpoints"] = {
                "status": "inactive",
                "reason": "자동 엔드포인트 시스템 초기화 실패"
            }
        
        return system_info
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"시스템 정보 조회 중 오류: {str(e)}")

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
                    "systemInfo": raw_data.get("systemInfo", {}),
                    "version": "2.0.0",  # 리팩토링 버전 기록
                    "auto_endpoint_active": endpoint_manager is not None
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
                "metadata": {
                    "version": "2.0.0",
                    "auto_endpoint_active": endpoint_manager is not None
                }
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

        logger.info(f"📝 새로운 피드백 수신 (v2.0):")
        logger.info(f"   📁 파일: {filename}")
        logger.info(f"   📍 IP: {client_ip}")
        logger.info(f"   🌐 언어: {feedback_data.get('metadata', {}).get('currentLanguage', 'N/A')}")
        logger.info(f"   📏 길이: {len(feedback_content)}자")
        logger.info(f"   📄 내용 미리보기: {feedback_content[:100]}{'...' if len(feedback_content) > 100 else ''}")

        return {
            "status": "success", 
            "message": "피드백이 성공적으로 저장되었습니다.",
            "feedback_id": timestamp,
            "type": feedback_data["type"],
            "version": "2.0.0"
        }

    except json.JSONDecodeError:
        return JSONResponse(
            status_code=400, 
            content={"error": "잘못된 JSON 형식입니다."}
        )
    except Exception as e:
        logger.error(f"❌ 피드백 처리 오류: {e}")
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

# ==================== 기본 API 엔드포인트 ====================
@app.get("/health")
def health_check():
    return {"status": "healthy", "message": "Community Crawler API is running"}

@app.get("/")
def root():
    return {
        "message": "PickPost API Server", 
        "status": "running",
        "version": "2.0.0",  # 리팩토링된 버전
        "docs": "/docs",
        "unified_endpoint": "/ws/crawl",  # 새로운 통합 엔드포인트 안내
        "auto_endpoint_system": endpoint_manager is not None,
        "legacy_endpoints": [
            "/ws/auto-crawl",
            "/ws/reddit-crawl", 
            "/ws/dcinside-crawl",
            "/ws/blind-crawl",
            "/ws/bbc-crawl",
            "/ws/lemmy-crawl",
            "/ws/universal-crawl"
        ]
    }

# ==================== 시작 시 최종 로깅 ====================
logger.info("✅ PickPost v2.0 크롤링 시스템 설정 완료")
logger.info("📡 사용 가능한 엔드포인트:")
logger.info("  🔥 NEW:")
logger.info("    - /ws/crawl - 통합 크롤링 엔드포인트")  
logger.info("    - /ws/analyze - 사이트 분석 전용")
logger.info("    - GET /api/system-info - 시스템 정보")

if endpoint_manager:
    logger.info("  🤖 AUTO-GENERATED:")
    for site_type in endpoint_manager.crawlers.keys():
        logger.info(f"    - /ws/{site_type}-crawl - {site_type} 전용 (자동생성)")
else:
    logger.info("  ⚠️ AUTO-GENERATED: 비활성화됨")

logger.info("  📜 LEGACY (하위 호환성):")
logger.info("    - /ws/auto-crawl - 자동 크롤링")
logger.info("  🛠️ MANAGEMENT:")
logger.info("    - POST /api/cancel-crawl - 크롤링 취소")
logger.info("    - GET /api/crawl-status/{crawl_id} - 상태 확인")
logger.info("    - POST /api/cleanup-crawls - 모든 크롤링 정리")
logger.info("  📝 FEEDBACK:")
logger.info("    - POST /api/feedback - 피드백 제출")
logger.info("    - GET /api/feedback/{feedback_id} - 피드백 조회")

if endpoint_manager:
    logger.info("🎉 자동 엔드포인트 시스템 활성화: 새 크롤러 파일을 추가하면 자동으로 엔드포인트가 생성됩니다!")
else:
    logger.info("⚠️ 자동 엔드포인트 시스템 비활성화: core.simple_endpoints 모듈을 확인하세요")
