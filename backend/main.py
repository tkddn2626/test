# main.py - 폴더 구조 변경사항 반영한 완전 수정 버전

from fastapi import FastAPI, WebSocket, Query, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Set, Any
import os, asyncio, json, requests, time, logging, traceback
from datetime import datetime, timedelta
from dotenv import load_dotenv
from pathlib import Path
import sys
import importlib.util
from core.site_detector import DynamicSiteDetector
from core.messages import create_localized_message


# 환경 설정
load_dotenv()
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# 환경 변수
DEEPL_API_KEY = os.getenv("DEEPL_API_KEY")
APP_ENV = os.getenv("APP_ENV", "development")
DEBUG = os.getenv("DEBUG", "False").lower() == "true"
PORT = int(os.getenv("PORT", 8000))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# 로깅 설정
logging.basicConfig(
  level=getattr(logging, LOG_LEVEL.upper()),
  format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("pickpost")

# AutoCrawler import 추가
try:
   from core.auto_crawler import AutoCrawler
   AUTO_CRAWLER_AVAILABLE = True
   logger.info("✅ AutoCrawler 로드 성공")
except ImportError as e:
   logger.error(f"❌ AutoCrawler 로드 실패: {e}")
   AUTO_CRAWLER_AVAILABLE = False

# ==================== 동적 크롤러 발견 시스템 ====================

def discover_available_crawlers():
    """
    backend/crawlers/ 디렉토리에서 사용 가능한 크롤러들을 동적으로 발견
    """
    current_dir = Path(__file__).parent  # backend/ 디렉토리
    crawlers_dir = current_dir / "crawlers"  # backend/crawlers/ 디렉토리
    available_crawlers = set()
    
    # crawlers/ 디렉토리가 존재하는지 확인
    if not crawlers_dir.exists():
        logger.warning(f"⚠️ crawlers 디렉토리가 없습니다: {crawlers_dir}")
        # AutoCrawler만 사용 가능
        if AUTO_CRAWLER_AVAILABLE:
            available_crawlers.add('universal')
            logger.debug("✅ AutoCrawler(universal)만 사용 가능")
        return available_crawlers
    
    # backend/crawlers/ 디렉토리의 모든 .py 파일 스캔
    for py_file in crawlers_dir.glob("*.py"):
        # 제외할 파일들
        if py_file.name.startswith('_') or py_file.stem == '__init__':
            continue
            
        crawler_name = py_file.stem
        
        try:
            # 실제 import 가능한지 확인
            spec = importlib.util.spec_from_file_location(f"crawlers.{crawler_name}", py_file)
            if spec and spec.loader:
                # 모듈을 실제로 로드해서 크롤링 함수가 있는지 확인
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                # 일반적인 크롤링 함수명들 확인
                crawl_functions = [
                    f'crawl_{crawler_name}_board',  # crawl_reddit_board
                    f'fetch_posts',                 # reddit용
                    f'crawl_{crawler_name}',        # crawl_reddit
                    f'{crawler_name}_crawl',         # reddit_crawl
                    f'crawl_{crawler_name.lower()}_board',
                ]
                
                # 하나라도 크롤링 함수가 있으면 유효한 크롤러로 간주
                has_crawl_function = any(hasattr(module, func) for func in crawl_functions)
                
                if has_crawl_function:
                    available_crawlers.add(crawler_name)
                    logger.debug(f"✅ 크롤러 발견: crawlers/{crawler_name}")
                else:
                    logger.debug(f"⚠️ 크롤링 함수 없음: crawlers/{crawler_name}")
                    
        except Exception as e:
            logger.debug(f"⚠️ 크롤러 확인 실패 crawlers/{crawler_name}: {e}")
    
    # AutoCrawler는 universal 기능을 포함하므로 항상 사용 가능
    if AUTO_CRAWLER_AVAILABLE:
        available_crawlers.add('universal')
        logger.debug("✅ AutoCrawler(universal) 사용 가능")
    
    logger.info(f"🎯 사용 가능한 크롤러: {sorted(available_crawlers)}")
    return available_crawlers

# 동적 크롤러 import
def import_available_crawlers():
    """사용 가능한 크롤러들을 동적으로 import"""
    crawl_functions = {}
    
    current_dir = Path(__file__).parent  # backend/ 디렉토리
    crawlers_dir = current_dir / "crawlers"  # backend/crawlers/ 디렉토리
    
    # crawlers/ 디렉토리가 존재하지 않으면 빈 딕셔너리 반환
    if not crawlers_dir.exists():
        logger.warning(f"⚠️ crawlers 디렉토리가 없습니다: {crawlers_dir}")
        return crawl_functions
    
    # backend/crawlers/ 디렉토리의 모든 .py 파일 스캔
    for py_file in crawlers_dir.glob("*.py"):
        # 제외할 파일들
        if py_file.name.startswith('_') or py_file.stem == '__init__':
            continue
            
        crawler_name = py_file.stem
        
        try:
            # 모듈 동적 로드
            spec = importlib.util.spec_from_file_location(f"crawlers.{crawler_name}", py_file)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                # 일반적인 크롤링 함수명들 시도
                possible_functions = [
                    f'crawl_{crawler_name}_board',  # crawl_reddit_board
                    f'fetch_posts',                 # reddit용
                    f'crawl_{crawler_name}',        # crawl_reddit
                    f'{crawler_name}_crawl',        # reddit_crawl
                    f'crawl_board',                 # 일반적인 함수명
                    f'crawl'                        # 간단한 함수명
                ]
                
                # 찾은 함수들을 저장
                found_functions = []
                for func_name in possible_functions:
                    if hasattr(module, func_name):
                        func = getattr(module, func_name)
                        if callable(func):
                            found_functions.append((func_name, func))
                
                # 메인 크롤링 함수 등록 (첫 번째로 발견된 함수)
                if found_functions:
                    main_func_name, main_func = found_functions[0]
                    crawl_functions[crawler_name] = main_func
                    logger.debug(f"✅ {crawler_name} 크롤러 import 성공 ({main_func_name})")
                    
                    # 추가 함수들도 특별한 키로 저장 (예: BBC의 detect 함수)
                    for func_name, func in found_functions[1:]:
                        special_key = f"{crawler_name}_{func_name}"
                        crawl_functions[special_key] = func
                        logger.debug(f"   추가 함수: {special_key}")
                    
                    # 특별한 함수들 개별 확인 (detect, parse 등)
                    special_functions = [
                        f'detect_{crawler_name}_url_and_extract_info',  # BBC 스타일
                        f'parse_{crawler_name}',
                        f'extract_{crawler_name}_info'
                    ]
                    
                    for special_func_name in special_functions:
                        if hasattr(module, special_func_name):
                            special_func = getattr(module, special_func_name)
                            if callable(special_func):
                                crawl_functions[special_func_name] = special_func
                                logger.debug(f"   특별 함수: {special_func_name}")
                else:
                    logger.debug(f"⚠️ 크롤링 함수 없음: crawlers/{crawler_name}")
                    
        except Exception as e:
            logger.debug(f"⚠️ 크롤러 import 실패 crawlers/{crawler_name}: {e}")
    
    logger.info(f"🚀 동적 로드된 크롤링 함수: {list(crawl_functions.keys())}")
    return crawl_functions

# 앱 시작시 크롤러 목록 및 함수들 가져오기
AVAILABLE_CRAWLERS = discover_available_crawlers()
CRAWL_FUNCTIONS = import_available_crawlers()

logger.info(f"🚀 로드된 크롤링 함수: {list(CRAWL_FUNCTIONS.keys())}")

# core/ 폴더의 SiteDetector import (폴백용)
try:
    from core.site_detector import SiteDetector as CoreSiteDetector
    CORE_SITE_DETECTOR_AVAILABLE = True
    logger.info("✅ Core SiteDetector 로드 성공")
except ImportError as e:
    logger.warning(f"⚠️ Core SiteDetector 로드 실패: {e}")
    CORE_SITE_DETECTOR_AVAILABLE = False

# ==================== 나머지 유틸리티 함수들 ====================
def get_user_language(config):
    if not config:
        return "en"
    return config.get("language", "en")

def calculate_actual_dates(time_filter, start_date_input=None, end_date_input=None):
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

# ==================== 크롤링 관리자 ====================
class CrawlManager:
    def __init__(self):
        self.cancelled_crawls: Set[str] = set()
        self.creation_time = time.time()
    
    def cancel_crawl(self, crawl_id: str):
        self.cancelled_crawls.add(crawl_id)
        logger.info(f"🚫 크롤링 취소: {crawl_id}")
    
    def is_cancelled(self, crawl_id: str) -> bool:
        return crawl_id in self.cancelled_crawls
    
    def cleanup_crawl(self, crawl_id: str):
        self.cancelled_crawls.discard(crawl_id)

crawl_manager = CrawlManager()

# ==================== 사이트별 크롤링 실행 ====================
async def execute_crawl_by_site(site_type: str, target_input: str, **config):
    crawl_id = config.pop('crawl_id', None)
    
    if crawl_id and crawl_manager.is_cancelled(crawl_id):
        raise asyncio.CancelledError("크롤링 취소됨")
    
    # 🔥 1순위: 전용 크롤러 직접 호출 (가장 우선)
    if site_type in CRAWL_FUNCTIONS:
        try:
            crawl_func = CRAWL_FUNCTIONS[site_type]
            logger.info(f"🎯 전용 크롤러 직접 사용: {site_type} -> {target_input}")
            
            # 사이트별 매개변수 준비
            if site_type == 'reddit':
                params = {
                    'subreddit_name': target_input,
                    'limit': config.get('limit', config.get('end_index', 20) + 5),
                    'sort': config.get('sort', 'top'),
                    'time_filter': config.get('time_filter', 'day'),
                    'websocket': config.get('websocket'),
                    'min_views': config.get('min_views', 0),
                    'min_likes': config.get('min_likes', 0),
                    'start_date': config.get('start_date'),
                    'end_date': config.get('end_date'),
                    'start_index': config.get('start_index', 1),
                    'end_index': config.get('end_index', 20)
                }
            elif site_type == 'lemmy':
                params = {
                    'community_input': target_input,
                    'limit': config.get('limit', config.get('end_index', 20) + 5),
                    'sort': config.get('sort', 'Hot'),
                    'min_views': config.get('min_views', 0),
                    'min_likes': config.get('min_likes', 0),
                    'time_filter': config.get('time_filter', 'day'),
                    'start_date': config.get('start_date'),
                    'end_date': config.get('end_date'),
                    'websocket': config.get('websocket'),
                    'start_index': config.get('start_index', 1),
                    'end_index': config.get('end_index', 20)
                }
            elif site_type == 'dcinside':
                params = {
                    'board_name': target_input,
                    'limit': config.get('limit', config.get('end_index', 20) + 5),
                    'sort': config.get('sort', 'recent'),
                    'min_views': config.get('min_views', 0),
                    'min_likes': config.get('min_likes', 0),
                    'time_filter': config.get('time_filter', 'day'),
                    'start_date': config.get('start_date'),
                    'end_date': config.get('end_date'),
                    'websocket': config.get('websocket'),
                    'start_index': config.get('start_index', 1),
                    'end_index': config.get('end_index', 20)
                }
            elif site_type == 'blind':
                params = {
                    'board_input': target_input,
                    'limit': config.get('limit', config.get('end_index', 20) + 5),
                    'sort': config.get('sort', 'recent'),
                    'min_views': config.get('min_views', 0),
                    'min_likes': config.get('min_likes', 0),
                    'time_filter': config.get('time_filter', 'day'),
                    'start_date': config.get('start_date'),
                    'end_date': config.get('end_date'),
                    'websocket': config.get('websocket'),
                    'start_index': config.get('start_index', 1),
                    'end_index': config.get('end_index', 20)
                }
            elif site_type == 'bbc':
                params = {
                    'board_url': target_input,
                    'limit': config.get('limit', config.get('end_index', 20) + 5),
                    'sort': config.get('sort', 'recent'),
                    'min_views': config.get('min_views', 0),
                    'min_likes': config.get('min_likes', 0),
                    'min_comments': config.get('min_comments', 0),
                    'time_filter': config.get('time_filter', 'day'),
                    'start_date': config.get('start_date'),
                    'end_date': config.get('end_date'),
                    'websocket': config.get('websocket'),
                    'board_name': config.get('board_name', ""),
                    'start_index': config.get('start_index', 1),
                    'end_index': config.get('end_index', 20)
                }
            else:
                # 일반적인 매개변수
                params = {
                    'target_input': target_input,
                    **{k: v for k, v in config.items() if v is not None}
                }
            
            # None 값 제거
            params = {k: v for k, v in params.items() if v is not None}
            
            return await crawl_func(**params)
            
        except Exception as e:
            logger.warning(f"⚠️ 전용 크롤러 실패, AutoCrawler로 폴백: {e}")
            # 전용 크롤러 실패시에만 AutoCrawler로 폴백
    
    # 🔥 2순위: AutoCrawler 사용 (전용 크롤러 실패시에만)
    if AUTO_CRAWLER_AVAILABLE:
        try:
            auto_crawler = AutoCrawler()
            # 이미 결정된 사이트 타입을 강제로 전달
            config['force_site_type'] = site_type
            logger.info(f"🤖 AutoCrawler 폴백 사용: {site_type} -> {target_input}")
            return await auto_crawler.crawl(target_input, **config)
        except Exception as e:
            logger.error(f"❌ AutoCrawler도 실패: {e}")
            raise
    
    # 🔥 3순위: 오류 발생
    raise Exception(f"사용 가능한 크롤러를 찾을 수 없습니다: {site_type}")
# ==================== 번역 서비스 ====================
async def deepl_translate(text: str, target_lang: str) -> str:
    try:
        if not text.strip() or not DEEPL_API_KEY:
            return text
            
        response = requests.post(
            "https://api-free.deepl.com/v2/translate",
            data={
                "auth_key": DEEPL_API_KEY,
                "text": text,
                "target_lang": target_lang.upper()
            },
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            return result["translations"][0]["text"]
        else:
            logger.warning(f"번역 API 오류: {response.status_code}")
            return text
            
    except Exception as e:
        logger.error(f"번역 오류: {e}")
        return text

# ==================== FastAPI 앱 초기화 ====================
app = FastAPI(title="PickPost API v2.1", debug=DEBUG)

# CORS 설정
def get_cors_origins():
    if APP_ENV == "production":
        return [
            "https://pickpost.netlify.app"
        ]
    else:
        return ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== 통합 크롤링 엔드포인트 ====================
@app.websocket("/ws/crawl")
async def websocket_crawl(websocket: WebSocket):
    await websocket.accept()
    crawl_id = f"unified_{id(websocket)}_{int(time.time())}"
    logger.info(f"🔥 통합 크롤링 시작: {crawl_id}")
    
    try:
        config = await websocket.receive_json()
        user_lang = config.get("language", "ko")  # ← 언어 추출
        
        logger.info(f"🔧 번역 설정 수신: translate={config.get('translate')}, user_lang={user_lang}")
        
        input_data = config.get("input", "").strip()
        frontend_site = config.get("site", "")
        
        crawl_options = {
            'sort': config.get("sort", "recent"),
            'start_index': config.get("start", 1),
            'end_index': config.get("end", 20),
            'min_views': config.get("min_views", 0),
            'min_likes': config.get("min_likes", 0),
            'min_comments': config.get("min_comments", 0),
            'time_filter': config.get("time_filter", "day"),
            'start_date': config.get("start_date"),
            'end_date': config.get("end_date"),
            'translate': config.get("translate", False),
            'target_languages': config.get("target_languages", []),
            'skip_translation': config.get("skip_translation", False),
            'websocket': websocket,
            'crawl_id': crawl_id
        }
        
        def check_cancelled():
            if crawl_manager.is_cancelled(crawl_id):
                raise asyncio.CancelledError(f"크롤링 {crawl_id} 취소됨")

        check_cancelled()

        if not input_data:
            await websocket.send_json({"error": "입력이 비어있습니다"})
            return

        actual_start_date, actual_end_date = calculate_actual_dates(
            crawl_options['time_filter'], 
            crawl_options['start_date'], 
            crawl_options['end_date']
        )
        crawl_options.update({
            'start_date': actual_start_date,
            'end_date': actual_end_date
        })
        
        # 🎯 수정된 사이트 감지 로직
        if frontend_site and frontend_site != 'auto':
            detected_site = frontend_site
            
            if detected_site in CRAWL_FUNCTIONS:
                board_identifier = input_data
                logger.info(f"🎯 전용 크롤러 사용: {detected_site} → 입력: {board_identifier}")
            else:
                detected_site = 'universal'
                board_identifier = input_data
                logger.info(f"🌐 AutoCrawler(universal) 처리: {frontend_site} → {input_data}")
            
        else:
            # ✅ 사이트 감지 메시지 - 언어팩 기반
            message = create_localized_message(
                progress=5,
                status_key="crawlingProgress.site_detecting",
                lang=user_lang
            )
            await websocket.send_json(message)
            check_cancelled()
            
            # core SiteDetector 우선 사용, 없으면 폴백
            if CORE_SITE_DETECTOR_AVAILABLE:
                site_detector = CoreSiteDetector()
                detected_site = await site_detector.detect_site_type(input_data)
            else:
                site_detector = DynamicSiteDetector()
                detected_site = await site_detector.detect_site_type(input_data)
                
            board_identifier = site_detector.extract_board_identifier(input_data, detected_site)
            logger.info(f"🔍 자동 감지된 사이트: {detected_site}, 게시판: {board_identifier}")

        # ✅ 사이트 연결 메시지 - 언어팩 기반
        site_display = detected_site.upper() if detected_site != 'lemmy' else 'Lemmy'
        message = create_localized_message(
            progress=15,
            status_key="crawlingProgress.site_connecting",
            lang=user_lang,
            status_data={"site": site_display}
        )
        await websocket.send_json(message)
        check_cancelled()

        # ✅ 게시물 수집 메시지 - 언어팩 기반
        message = create_localized_message(
            progress=30,
            status_key="crawlingProgress.posts_collecting",
            lang=user_lang,
            status_data={"site": site_display}
        )
        await websocket.send_json(message)
        check_cancelled()

        # 크롤링 실행
        raw_posts = await execute_crawl_by_site(
            detected_site, 
            board_identifier, 
            **crawl_options
        )

        check_cancelled()

        if raw_posts:
            # ✅ 게시물 필터링 메시지 - 언어팩 기반
            message = create_localized_message(
                progress=60,
                status_key="crawlingProgress.posts_filtering",
                lang=user_lang,
                status_data={"matched": len(raw_posts), "total": len(raw_posts)}
            )
            await websocket.send_json(message)

        # ✅ 데이터 처리 메시지 - 언어팩 기반
        message = create_localized_message(
            progress=75,
            status_key="crawlingProgress.posts_processing",
            lang=user_lang
        )
        await websocket.send_json(message)
        check_cancelled()

        if not raw_posts:
            await websocket.send_json({
                "error": f"{site_display}에서 게시물을 찾을 수 없습니다"
            })
            return

        # 번역 처리 로직
        results = []
        translate = crawl_options.get('translate', False)
        target_languages = crawl_options.get('target_languages', [])
        skip_translation = crawl_options.get('skip_translation', False)

        # 번역 스킵 조건 확인
        if skip_translation or not translate or not target_languages:
            logger.info(f"🚫 번역 건너뛰기: skip_translation={skip_translation}")
            
            await websocket.send_json({
                "progress": 85, 
                "status": "번역 건너뛰기 - 동일 언어"
            })
            
            for post in raw_posts:
                results.append(post)
            
        elif translate and target_languages:
            logger.info(f"✅ 번역 수행: target_languages={target_languages}")
            
            # ✅ 번역 준비 메시지 - 언어팩 기반
            message = create_localized_message(
                progress=80,
                status_key="crawlingProgress.translation_preparing",
                lang=user_lang,
                status_data={"count": len(raw_posts)}
            )
            await websocket.send_json(message)
            
            for idx, post in enumerate(raw_posts):
                check_cancelled()
                
                original_title = post.get('원제목', '')
                
                # 번역 수행
                for lang_code in target_languages:
                    translated = await deepl_translate(original_title, lang_code)
                    if lang_code.lower() == 'ko':
                        post['번역제목'] = translated
                    else:
                        post[f'번역제목_{lang_code}'] = translated
                
                results.append(post)
                
                if len(raw_posts) > 0:
                    translation_progress = 85 + int((idx + 1) / len(raw_posts) * 10)
                    
                    # ✅ 번역 진행 메시지 - 언어팩 기반
                    message = create_localized_message(
                        progress=translation_progress,
                        status_key="crawlingProgress.translation_progress",
                        lang=user_lang,
                        status_data={"current": idx + 1, "total": len(raw_posts)}
                    )
                    await websocket.send_json(message)

        check_cancelled()

        # ✅ 결과 정리 메시지 - 언어팩 기반
        message = create_localized_message(
            progress=95,
            status_key="crawlingProgress.finalizing",
            lang=user_lang
        )
        await websocket.send_json(message)

        await websocket.send_json({
            "done": True,
            "data": results,
            "progress": 100,
            "detected_site": detected_site,
            "summary": f"크롤링 완료: {len(results)}개 게시물"
        })
        
        logger.info(f"✅ 통합 크롤링 완료: {len(results)}개 ({detected_site})")

    except asyncio.CancelledError:
        logger.info(f"❌ 크롤링 취소: {crawl_id}")
        await websocket.send_json({"cancelled": True})
    except Exception as e:
        logger.error(f"❌ 크롤링 오류: {e}")
        await websocket.send_json({"error": str(e)})
    finally:
        crawl_manager.cleanup_crawl(crawl_id)
        await websocket.close()

# ==================== 자동완성 API ====================
@app.get("/autocomplete/{site}")
async def autocomplete(site: str, keyword: str = Query(...)):
    keyword = keyword.strip().lower()
    
    # BBC 자동완성 (detect_bbc_url_and_extract_info 함수가 있는 경우에만)
    if site == "bbc" and 'detect_bbc_url_and_extract_info' in CRAWL_FUNCTIONS:
        try:
            detect_func = CRAWL_FUNCTIONS['detect_bbc_url_and_extract_info']
            bbc_detection = detect_func(keyword)
            if bbc_detection["is_bbc"]:
                return {
                    "matches": [bbc_detection["board_name"]],
                    "detected_site": "bbc",
                    "auto_detected": True
                }
        except Exception as e:
            logger.warning(f"BBC 자동완성 오류: {e}")
    
    matches = []
    
    if site == "reddit":
        reddit_subreddits = ["askreddit", "todayilearned", "funny", "pics", "worldnews", "gaming", "technology", "programming", "korea"]
        matches = [sub for sub in reddit_subreddits if keyword in sub.lower()]
    elif site == "lemmy":
        lemmy_communities = ["technology@lemmy.world", "asklemmy@lemmy.ml", "worldnews@lemmy.ml", "programming@programming.dev"]
        matches = [comm for comm in lemmy_communities if keyword in comm.lower()]
    elif site == "blind":
        blind_topics = ["블라블라", "회사생활", "자유토크", "개발자", "경력개발", "취업/이직"]
        matches = [topic for topic in blind_topics if keyword in topic.lower()]
    elif site == "dcinside":
        dc_galleries = ["싱글벙글", "유머", "정치", "축구", "야구", "게임", "프로그래밍"]
        matches = [gallery for gallery in dc_galleries if keyword in gallery.lower()]
    
    return {"matches": matches[:15], "auto_detected": False}

# ==================== 크롤링 취소 시스템 ====================
class CancelRequest(BaseModel):
    crawl_id: str
    action: str = "cancel"

@app.post("/api/cancel-crawl")
async def cancel_crawl_endpoint(request: CancelRequest):
    try:
        crawl_id = request.crawl_id
        if not crawl_id:
            raise HTTPException(status_code=400, detail="crawl_id가 필요합니다")
        
        crawl_manager.cancel_crawl(crawl_id)
        return {
            "success": True,
            "message": f"크롤링 {crawl_id} 취소 완료",
            "crawl_id": crawl_id,
            "timestamp": time.time()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== 피드백 시스템 ====================
@app.post("/api/feedback")
async def submit_feedback(request: Request):
    try:
        raw_data = await request.json()
        feedback_content = raw_data.get("description", raw_data.get("message", "")).strip()
        
        if not feedback_content:
            return JSONResponse(status_code=400, content={"error": "피드백 내용이 필요합니다."})
        
        feedback_dir = "outputs/feedback"
        os.makedirs(feedback_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        
        feedback_data = {
            "timestamp": timestamp,
            "ip": request.client.host,
            "content": feedback_content,
            "metadata": raw_data,
            "system_info": {
                "auto_crawler_available": AUTO_CRAWLER_AVAILABLE,
                "core_site_detector_available": CORE_SITE_DETECTOR_AVAILABLE,
                "available_crawlers": list(AVAILABLE_CRAWLERS),
                "loaded_crawl_functions": list(CRAWL_FUNCTIONS.keys())
            }
        }
        
        filename = f"feedback_{timestamp}.json"
        filepath = os.path.join(feedback_dir, filename)
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(feedback_data, f, ensure_ascii=False, indent=2)

        logger.info(f"📝 피드백 수신: {len(feedback_content)}자")
        
        return {"status": "success", "message": "피드백이 저장되었습니다."}
        
    except Exception as e:
        logger.error(f"❌ 피드백 오류: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

# ==================== 기본 API ====================
@app.get("/health")
def health_check():
    system_status = {
        "status": "healthy",
        "message": "PickPost API is running",
        "auto_crawler_available": AUTO_CRAWLER_AVAILABLE,
        "core_site_detector_available": CORE_SITE_DETECTOR_AVAILABLE,
        "available_crawlers": list(AVAILABLE_CRAWLERS),
        "loaded_functions": list(CRAWL_FUNCTIONS.keys()),
        "dynamic_discovery": True
    }
    
    if not AUTO_CRAWLER_AVAILABLE and not CRAWL_FUNCTIONS:
        system_status["status"] = "degraded"
        system_status["message"] = "No crawler systems available"
    
    return system_status

@app.get("/")
def root():
    return {
        "message": "PickPost API Server", 
        "status": "running",
        "version": "2.1.1 (Dynamic Crawler Discovery)",
        "docs": "/docs",
        "unified_endpoint": "/ws/crawl",
        "auto_crawler_available": AUTO_CRAWLER_AVAILABLE,
        "core_site_detector_available": CORE_SITE_DETECTOR_AVAILABLE,
        "dynamic_crawlers": list(AVAILABLE_CRAWLERS),
        "loaded_functions": list(CRAWL_FUNCTIONS.keys())
    }

@app.get("/api/system-info")
async def get_system_info():
    return {
        "version": "2.1.1",
        "environment": APP_ENV,
        "localized_messages": True,
        "supported_sites": list(AVAILABLE_CRAWLERS),
        "loaded_crawlers": list(CRAWL_FUNCTIONS.keys()),
        "endpoints": {
            "unified": "/ws/crawl",
            "autocomplete": "/autocomplete/{site}"
        },
        "features": {
            "dynamic_crawler_discovery": True,
            "progress_localization": True,
            "error_localization": True,
            "multi_language_translation": True,
            "translation_skip_support": True,
            "cancellation_support": True,
            "automatic_parameter_filtering": True,
            "auto_crawler_integration": AUTO_CRAWLER_AVAILABLE,
            "core_site_detector": CORE_SITE_DETECTOR_AVAILABLE
        },
        "system_status": {
            "auto_crawler": AUTO_CRAWLER_AVAILABLE,
            "core_site_detector": CORE_SITE_DETECTOR_AVAILABLE,
            "available_crawlers": list(AVAILABLE_CRAWLERS),
            "functional_crawlers": list(CRAWL_FUNCTIONS.keys())
        }
    }

@app.get("/api/crawlers")
async def get_available_crawlers():
    """사용 가능한 크롤러 목록 및 상태 반환"""
    crawler_info = {}
    
    for crawler_name in AVAILABLE_CRAWLERS:
        crawler_info[crawler_name] = {
            "available": True,
            "functional": crawler_name in CRAWL_FUNCTIONS,
            "type": "AutoCrawler" if crawler_name == "universal" else "Direct",
            "status": "✅ 사용 가능" if crawler_name in CRAWL_FUNCTIONS or crawler_name == "universal" else "⚠️ 함수 없음"
        }
    
    return {
        "total_discovered": len(AVAILABLE_CRAWLERS),
        "functional_count": len(CRAWL_FUNCTIONS) + (1 if AUTO_CRAWLER_AVAILABLE else 0),
        "crawlers": crawler_info,
        "discovery_method": "Dynamic file scanning",
        "auto_crawler_enabled": AUTO_CRAWLER_AVAILABLE
    }

# ==================== 서버 시작 ====================
if __name__ == "__main__":
    import uvicorn
    
    logger.info("🚀 PickPost v2.1.1 서버 시작 (동적 크롤러 탐지)")
    logger.info(f"   AutoCrawler: {'✅' if AUTO_CRAWLER_AVAILABLE else '❌'}")
    logger.info(f"   Core SiteDetector: {'✅' if CORE_SITE_DETECTOR_AVAILABLE else '❌'}")
    logger.info(f"   발견된 크롤러: {list(AVAILABLE_CRAWLERS)}")
    logger.info(f"   로드된 함수: {list(CRAWL_FUNCTIONS.keys())}")
    logger.info("   크롤러 위치: backend/crawlers/")
    logger.info("   동적 크롤러 탐지: ✅ 활성화")
    logger.info("   번역 스킵 기능: ✅ 활성화")
    
    if not AUTO_CRAWLER_AVAILABLE and not CRAWL_FUNCTIONS:
        logger.error("❌ 모든 크롤링 시스템을 사용할 수 없습니다!")
    
    uvicorn.run(app, host="0.0.0.0", port=PORT)