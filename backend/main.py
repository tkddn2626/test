from fastapi import FastAPI, WebSocket, Query, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Set, Any
import os, asyncio, json, requests, time, logging, traceback
from datetime import datetime
from dotenv import load_dotenv
from pathlib import Path
import sys

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

# 🔥 통합 크롤링 시스템 import
try:
    from core.unified_crawler import unified_crawler, crawl_any_site
    UNIFIED_SYSTEM_AVAILABLE = True
    logger.info("🔥 통합 크롤링 시스템 로드 성공")
except ImportError as e:
    logger.warning(f"통합 크롤링 시스템 로드 실패: {e}")
    UNIFIED_SYSTEM_AVAILABLE = False

# 기존 크롤러 모듈 import (폴백용)
try:
    from reddit import fetch_posts
    from blind import crawl_blind_board
    from dcinside import crawl_dcinside_board
    from universal import crawl_universal_board
    from lemmy import crawl_lemmy_board
    from bbc import crawl_bbc_board, detect_bbc_url_and_extract_info
    LEGACY_CRAWLERS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"레거시 크롤러 모듈 로드 실패: {e}")
    LEGACY_CRAWLERS_AVAILABLE = False

# 코어 모듈 import
import core.endpoints
from core.site_detector import SiteDetector
from core.auto_crawler import AutoCrawler
from core.utils import (
   get_user_language,
   calculate_actual_dates
)

# ==================== 진행률 및 메시지 관리 ====================
class ProgressManager:
   """진행률과 메시지 키 관리"""
   
   PROGRESS_STAGES = {
       "site_detecting": 5,
       "site_connecting": 15,
       "posts_collecting": 30,
       "posts_filtering": 60,
       "posts_processing": 75,
       "translation_preparing": 80,
       "translation_progress": 85,
       "finalizing": 95,
       "complete": 100
   }
   
   @staticmethod
   async def send_progress(websocket: WebSocket, stage_key: str, **template_data):
       """진행률과 상태 키를 전송 (텍스트 없음)"""
       await websocket.send_json({
           "progress": ProgressManager.PROGRESS_STAGES.get(stage_key, 0),
           "status_key": stage_key,
           "status_data": template_data
       })
   
   @staticmethod
   async def send_completion(websocket: WebSocket, completion_key: str, data: list, **template_data):
       """완료 메시지 전송"""
       await websocket.send_json({
           "done": True,
           "data": data,
           "progress": 100,
           "completion_key": completion_key,
           "completion_data": template_data
       })
   
   @staticmethod
   async def send_error(websocket: WebSocket, error_key: str, **template_data):
       """에러 메시지 전송"""
       await websocket.send_json({
           "error": True,
           "error_key": error_key,
           "error_data": template_data
       })

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

# ==================== 🔥 통합 크롤링 실행 함수 ====================
async def execute_unified_crawl(site_type: str, target_input: str, crawl_id: str = None, **config):
    """통합 크롤링 실행 함수"""
    
    # 취소 확인
    if crawl_id and crawl_manager.is_cancelled(crawl_id):
        raise asyncio.CancelledError("크롤링 취소됨")
    
    # 통합 시스템 사용 가능 여부 확인
    if UNIFIED_SYSTEM_AVAILABLE:
        try:
            logger.info(f"🔥 통합 크롤링 시스템 사용: {site_type} -> {target_input}")
            
            # 통합 크롤러 사용
            results = await unified_crawler.unified_crawl(site_type, target_input, **config)
            
            logger.info(f"✅ 통합 크롤링 완료: {len(results)}개 결과")
            return results
            
        except Exception as e:
            logger.error(f"❌ 통합 크롤링 오류: {e}")
            
            # 폴백: 레거시 크롤러 사용
            if LEGACY_CRAWLERS_AVAILABLE:
                logger.warning("⚠️ 레거시 크롤러로 폴백")
                return await execute_legacy_crawl(site_type, target_input, crawl_id, **config)
            else:
                raise
    else:
        # 레거시 크롤러만 사용 가능
        logger.info(f"📚 레거시 크롤링 시스템 사용: {site_type} -> {target_input}")
        return await execute_legacy_crawl(site_type, target_input, crawl_id, **config)

async def execute_legacy_crawl(site_type: str, target_input: str, crawl_id: str = None, **config):
    """레거시 크롤링 실행 함수 (폴백용)"""
    
    # 취소 확인
    if crawl_id and crawl_manager.is_cancelled(crawl_id):
        raise asyncio.CancelledError("크롤링 취소됨")
    
    # 레거시 크롤러 직접 호출
    try:
        if site_type == 'reddit':
            # Reddit 매개변수 정리
            reddit_params = {
                'subreddit_name': target_input,
                'limit': config.get('limit', config.get('end_index', 20) + 5),
                'sort': config.get('sort', 'top'),
                'time_filter': config.get('time_filter', 'day'),
                'websocket': config.get('websocket'),
                'min_views': config.get('min_views', 0),
                'min_likes': config.get('min_likes', 0),
                'start_date': config.get('start_date'),
                'end_date': config.get('end_date'),
                'enforce_date_limit': config.get('enforce_date_limit', False),
                'start_index': config.get('start_index', 1),
                'end_index': config.get('end_index', 20)
            }
            # None 값 제거
            reddit_params = {k: v for k, v in reddit_params.items() if v is not None}
            return await fetch_posts(**reddit_params)
            
        elif site_type == 'lemmy':
            # Lemmy 매개변수 정리 (min_comments 제외)
            lemmy_params = {
                'community_input': target_input,
                'limit': config.get('limit', config.get('end_index', 20) + 5),
                'sort': config.get('sort', 'Hot'),
                'min_views': config.get('min_views', 0),
                'min_likes': config.get('min_likes', 0),
                'time_filter': config.get('time_filter', 'day'),
                'start_date': config.get('start_date'),
                'end_date': config.get('end_date'),
                'websocket': config.get('websocket'),
                'enforce_date_limit': config.get('enforce_date_limit', False),
                'start_index': config.get('start_index', 1),
                'end_index': config.get('end_index', 20)
            }
            # None 값 제거
            lemmy_params = {k: v for k, v in lemmy_params.items() if v is not None}
            return await crawl_lemmy_board(**lemmy_params)
            
        elif site_type == 'dcinside':
            # DCInside 매개변수 정리 (min_comments 제외)
            dc_params = {
                'board_name': target_input,
                'limit': config.get('limit', config.get('end_index', 20) + 5),
                'sort': config.get('sort', 'recent'),
                'min_views': config.get('min_views', 0),
                'min_likes': config.get('min_likes', 0),
                'time_filter': config.get('time_filter', 'day'),
                'start_date': config.get('start_date'),
                'end_date': config.get('end_date'),
                'websocket': config.get('websocket'),
                'enforce_date_limit': config.get('enforce_date_limit', False),
                'start_index': config.get('start_index', 1),
                'end_index': config.get('end_index', 20)
            }
            # None 값 제거
            dc_params = {k: v for k, v in dc_params.items() if v is not None}
            return await crawl_dcinside_board(**dc_params)
            
        elif site_type == 'blind':
            # Blind 매개변수 정리 (min_comments 제외)
            blind_params = {
                'board_input': target_input,
                'limit': config.get('limit', config.get('end_index', 20) + 5),
                'sort': config.get('sort', 'recent'),
                'min_views': config.get('min_views', 0),
                'min_likes': config.get('min_likes', 0),
                'time_filter': config.get('time_filter', 'day'),
                'start_date': config.get('start_date'),
                'end_date': config.get('end_date'),
                'websocket': config.get('websocket'),
                'enforce_date_limit': config.get('enforce_date_limit', False),
                'start_index': config.get('start_index', 1),
                'end_index': config.get('end_index', 20)
            }
            # None 값 제거
            blind_params = {k: v for k, v in blind_params.items() if v is not None}
            return await crawl_blind_board(**blind_params)
            
        elif site_type == 'bbc':
            # BBC 매개변수 정리
            bbc_params = {
                'board_url': target_input,
                'limit': config.get('limit', config.get('end_index', 20) + 5),
                'sort': config.get('sort', 'recent'),
                'min_views': config.get('min_views', 0),
                'min_likes': config.get('min_likes', 0),
                'min_comments': config.get('min_comments', 0),  # BBC는 지원
                'time_filter': config.get('time_filter', 'day'),
                'start_date': config.get('start_date'),
                'end_date': config.get('end_date'),
                'websocket': config.get('websocket'),
                'board_name': config.get('board_name', ""),
                'enforce_date_limit': config.get('enforce_date_limit', False),
                'start_index': config.get('start_index', 1),
                'end_index': config.get('end_index', 20)
            }
            # None 값 제거 (board_name은 빈 문자열로 유지)
            bbc_params = {k: v for k, v in bbc_params.items() if v is not None}
            return await crawl_bbc_board(**bbc_params)
            
        elif site_type == 'universal':
            # Universal 매개변수 정리
            universal_params = {
                'board_url': target_input,
                'limit': config.get('limit', config.get('end_index', 20) + 5),
                'sort': config.get('sort', 'recent'),
                'min_views': config.get('min_views', 0),
                'min_likes': config.get('min_likes', 0),
                'min_comments': config.get('min_comments', 0),  # Universal은 지원
                'time_filter': config.get('time_filter', 'day'),
                'start_date': config.get('start_date'),
                'end_date': config.get('end_date'),
                'websocket': config.get('websocket'),
                'board_name': config.get('board_name', ""),
                'enforce_date_limit': config.get('enforce_date_limit', False),
                'start_index': config.get('start_index', 1),
                'end_index': config.get('end_index', 20)
            }
            # None 값 제거
            universal_params = {k: v for k, v in universal_params.items() if v is not None}
            return await crawl_universal_board(**universal_params)
        else:
            raise ValueError(f"지원하지 않는 사이트 타입: {site_type}")
            
    except Exception as e:
        logger.error(f"❌ 레거시 크롤링 오류 ({site_type}): {e}")
        raise

# ==================== 🔥 간소화된 크롤링 래퍼 함수들 ====================
async def crawl_reddit_with_cancel_check(*args, crawl_id=None, **kwargs):
    target = args[0] if args else kwargs.get('subreddit_name', kwargs.get('board_identifier', ''))
    return await execute_unified_crawl('reddit', target, crawl_id, **kwargs)

async def crawl_lemmy_board_with_cancel_check(*args, crawl_id=None, **kwargs):
    target = args[0] if args else kwargs.get('community_input', kwargs.get('board_identifier', ''))
    return await execute_unified_crawl('lemmy', target, crawl_id, **kwargs)

async def crawl_dcinside_board_with_cancel_check(*args, crawl_id=None, **kwargs):
    target = args[0] if args else kwargs.get('board_name', kwargs.get('board_identifier', ''))
    return await execute_unified_crawl('dcinside', target, crawl_id, **kwargs)

async def crawl_blind_board_with_cancel_check(*args, crawl_id=None, **kwargs):
    target = args[0] if args else kwargs.get('board_input', kwargs.get('board_identifier', ''))
    return await execute_unified_crawl('blind', target, crawl_id, **kwargs)

async def crawl_bbc_board_with_cancel_check(board_url: str = None, crawl_id=None, **kwargs):
    target = board_url or kwargs.get('board_url', kwargs.get('board_identifier', ''))
    return await execute_unified_crawl('bbc', target, crawl_id, **kwargs)

async def crawl_universal_board_with_cancel_check(*args, crawl_id=None, **kwargs):
    target = args[0] if args else kwargs.get('board_url', kwargs.get('board_identifier', ''))
    return await execute_unified_crawl('universal', target, crawl_id, **kwargs)

# fetch_posts도 통합으로 처리
async def fetch_posts_with_cancel_check(*args, crawl_id=None, **kwargs):
    target = args[0] if args else kwargs.get('subreddit_name', kwargs.get('board_identifier', ''))
    return await execute_unified_crawl('reddit', target, crawl_id, **kwargs)

# ==================== 번역 서비스 ====================
async def deepl_translate(text: str, target_lang: str) -> str:
   """DeepL API를 사용한 번역"""
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
app = FastAPI(title="PickPost API v2.0 (Unified)", debug=DEBUG)

# CORS 설정
def get_cors_origins():
   if APP_ENV == "production":
       return [
           "https://pickpost.netlify.app",
           "https://testfdd.netlify.app",
           "https://test-1-zm0k.onrender.com"
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

# ==================== 🔥 통합 크롤링 엔드포인트 ====================
@app.websocket("/ws/crawl")
async def unified_crawl_endpoint(websocket: WebSocket):
    """통합 크롤링 WebSocket 엔드포인트 (통합 시스템 사용)"""
    origin = websocket.headers.get("origin", "")
    
    # Origin 검증
    if APP_ENV == "production":
        allowed_patterns = ["netlify.app", "onrender.com"]
        origin_allowed = any(pattern in origin for pattern in allowed_patterns)
    else:
        origin_allowed = True
        
    if not origin_allowed:
        await websocket.close(code=1008, reason="Invalid origin")
        return
        
    await websocket.accept()
    crawl_id = f"unified_{id(websocket)}_{int(time.time())}"
    logger.info(f"🔥 통합 크롤링 시작: {crawl_id}")
    
    try:
        # 설정 수신
        config = await websocket.receive_json()
        user_lang = get_user_language(config)
        
        input_data = config.get("input", "").strip()
        
        # 기본 크롤링 옵션들
        crawl_options = {
            'sort': config.get("sort", "recent"),
            'start_index': config.get("start", 1),
            'end_index': config.get("end", 20),
            'min_views': config.get("min_views", 0),
            'min_likes': config.get("min_likes", 0),
            'min_comments': config.get("min_comments", 0),  # 통합 시스템에서 자동 필터링됨
            'time_filter': config.get("time_filter", "day"),
            'start_date': config.get("start_date"),
            'end_date': config.get("end_date"),
            'translate': config.get("translate", False),
            'target_languages': config.get("target_languages", []),
            'websocket': websocket,
            'crawl_id': crawl_id
        }
        
        # 취소 확인 함수
        def check_cancelled():
            if crawl_manager.is_cancelled(crawl_id):
                raise asyncio.CancelledError(f"크롤링 {crawl_id} 취소됨")

        check_cancelled()

        # 입력 검증
        if not input_data:
            await ProgressManager.send_error(websocket, "empty_input")
            return

        # 날짜 계산
        actual_start_date, actual_end_date = calculate_actual_dates(
            crawl_options['time_filter'], 
            crawl_options['start_date'], 
            crawl_options['end_date']
        )
        crawl_options.update({
            'start_date': actual_start_date,
            'end_date': actual_end_date
        })
        
        # 1단계: 사이트 감지
        await ProgressManager.send_progress(websocket, "site_detecting", input=input_data)
        check_cancelled()

        site_detector = SiteDetector()
        detected_site = await site_detector.detect_site_type(input_data)
        board_identifier = site_detector.extract_board_identifier(input_data, detected_site)
        
        logger.info(f"감지된 사이트: {detected_site}, 게시판: {board_identifier}")

        # 2단계: 사이트 연결
        await ProgressManager.send_progress(websocket, "site_connecting", site=detected_site.upper())
        check_cancelled()

        # 3단계: 게시물 수집
        await ProgressManager.send_progress(
            websocket, "posts_collecting", 
            site=detected_site.upper(), 
            board=board_identifier
        )
        check_cancelled()

        # 🔥 통합 크롤링 시스템 사용
        raw_posts = await execute_unified_crawl(
            detected_site, 
            board_identifier, 
            crawl_id,
            **crawl_options
        )

        check_cancelled()

        # 4단계: 필터링
        if raw_posts:
            await ProgressManager.send_progress(
                websocket, "posts_filtering", 
                total=len(raw_posts), 
                matched=len(raw_posts)
            )

        # 5단계: 데이터 처리
        await ProgressManager.send_progress(websocket, "posts_processing")
        check_cancelled()

        if not raw_posts:
            await ProgressManager.send_error(
                websocket, "no_posts_found", 
                site=detected_site.upper(),
                board=board_identifier
            )
            return

        # 6단계: 번역 처리
        results = []
        translate = crawl_options.get('translate', False)
        target_languages = crawl_options.get('target_languages', [])
        
        if translate and target_languages:
            await ProgressManager.send_progress(
                websocket, "translation_preparing", 
                count=len(raw_posts)
            )
            
            for idx, post in enumerate(raw_posts):
                check_cancelled()
                
                original_title = post.get('원제목', '')
                
                # 번역 필요 여부 확인 (한글이 포함된 경우 번역)
                if any(ord(char) > 127 for char in original_title):
                    # 각 타겟 언어로 번역
                    for lang_code in target_languages:
                        translated = await deepl_translate(original_title, lang_code)
                        post[f'번역제목_{lang_code}'] = translated
                else:
                    # 영어 제목인 경우 원제목 사용
                    for lang_code in target_languages:
                        post[f'번역제목_{lang_code}'] = original_title
                
                results.append(post)
                
                # 번역 진행률 업데이트
                if len(raw_posts) > 0:
                    translation_progress = 85 + int((idx + 1) / len(raw_posts) * 10)
                    await websocket.send_json({
                        "progress": translation_progress,
                        "status_key": "translation_progress",
                        "status_data": {
                            "current": idx + 1,
                            "total": len(raw_posts)
                        }
                    })
        else:
            # 번역 없이 기본 번역제목 설정
            for post in raw_posts:
                original_title = post.get('원제목', '')
                if any(ord(char) > 127 for char in original_title):
                    post['번역제목'] = original_title
                else:
                    post['번역제목'] = await deepl_translate(original_title, "KO")
                results.append(post)

        check_cancelled()

        # 7단계: 결과 정리
        await ProgressManager.send_progress(websocket, "finalizing")

        # 최종 결과 전송
        await ProgressManager.send_completion(
            websocket, 
            "unified_complete",
            results,
            site=detected_site.upper(),
            input=input_data,
            count=len(results),
            start=crawl_options['start_index'],
            end=crawl_options['start_index'] + len(results) - 1 if results else crawl_options['start_index']
        )
        
        logger.info(f"✅ 통합 크롤링 완료: {len(results)}개 ({detected_site})")

    except asyncio.CancelledError:
        logger.info(f"❌ 크롤링 취소: {crawl_id}")
        await websocket.send_json({
            "cancelled": True,
            "cancellation_key": "crawl_cancelled"
        })
    except Exception as e:
        logger.error(f"❌ 크롤링 오류: {e}")
        await ProgressManager.send_error(
            websocket, 
            "crawling_error",
            error=str(e)
        )
    finally:
        crawl_manager.cleanup_crawl(crawl_id)
        await websocket.close()

# ==================== 레거시 자동 크롤링 엔드포인트 ====================
@app.websocket("/ws/auto-crawl")
async def crawl_auto_socket(websocket: WebSocket):
   """레거시 자동 크롤링 엔드포인트 (하위 호환성)"""
   origin = websocket.headers.get("origin", "")
   
   if APP_ENV == "production":
       allowed_patterns = ["netlify.app", "onrender.com"]
       origin_allowed = any(pattern in origin for pattern in allowed_patterns)
   else:
       origin_allowed = True

   if not origin_allowed:
       await websocket.close(code=1008, reason="Invalid origin")
       return

   await websocket.accept()
   crawl_id = f"auto_{id(websocket)}_{int(time.time())}"
   
   try:
       init_data = await websocket.receive_json()
       user_lang = get_user_language(init_data)
       
       board_input = init_data.get("board", "").strip()
       sort = init_data.get("sort", "recent")
       start = init_data.get("start", 1)
       end = init_data.get("end", 20)
       min_views = init_data.get("min_views", 0)
       min_likes = init_data.get("min_likes", 0)
       time_filter = init_data.get("time_filter", "day")
       start_date_input = init_data.get("start_date")
       end_date_input = init_data.get("end_date")

       def check_cancelled():
           if crawl_manager.is_cancelled(crawl_id):
               raise asyncio.CancelledError(f"크롤링 {crawl_id} 취소됨")

       check_cancelled()

       if not board_input:
           await ProgressManager.send_error(websocket, "empty_input")
           return

       # AutoCrawler 실행 (레거시 방식)
       auto_crawler = AutoCrawler()
       actual_start_date, actual_end_date = calculate_actual_dates(
           time_filter, start_date_input, end_date_input
       )

       crawl_config = {
           'sort': sort,
           'start': start,
           'end': end,
           'min_views': min_views,
           'min_likes': min_likes,
           'time_filter': time_filter,
           'start_date': actual_start_date,
           'end_date': actual_end_date,
           'websocket': websocket,
           'crawl_id': crawl_id
       }

       await ProgressManager.send_progress(websocket, "site_detecting", input=board_input)
       check_cancelled()

       raw_posts = await auto_crawler.crawl(board_input, **crawl_config)
       
       if not raw_posts:
           await ProgressManager.send_error(websocket, "no_posts_found")
           return

       # 번역 처리 (레거시 방식)
       results = []
       for idx, post in enumerate(raw_posts):
           check_cancelled()
           
           original_title = post.get('원제목', '')
           if any(ord(char) > 127 for char in original_title):
               post['번역제목'] = original_title
           else:
               post['번역제목'] = await deepl_translate(original_title, "KO")

           results.append(post)

           if len(raw_posts) > 0:
               progress = 85 + int((idx + 1) / len(raw_posts) * 10)
               await websocket.send_json({"progress": progress})

       await ProgressManager.send_completion(
           websocket,
           "legacy_complete",
           results,
           count=len(results)
       )

   except asyncio.CancelledError:
       await websocket.send_json({
           "cancelled": True,
           "cancellation_key": "crawl_cancelled"
       })
   except Exception as e:
       logger.error(f"❌ Auto crawl error: {e}")
       await ProgressManager.send_error(
           websocket,
           "crawling_error",
           error=str(e)
       )
   finally:
       crawl_manager.cleanup_crawl(crawl_id)
       await websocket.close()

# ==================== 사이트 분석 엔드포인트 ====================
@app.websocket("/ws/analyze")
async def analyze_site_endpoint(websocket: WebSocket):
   """사이트 분석 전용 엔드포인트"""
   await websocket.accept()
   
   try:
       data = await websocket.receive_json()
       input_data = data.get("input", "")
       
       site_detector = SiteDetector()
       detected_site = await site_detector.detect_site_type(input_data)
       board_identifier = site_detector.extract_board_identifier(input_data, detected_site)
       
       analysis_result = {
           "input": input_data,
           "detected_site": detected_site,
           "board_identifier": board_identifier,
           "is_url": input_data.startswith('http'),
           "analysis_complete": True
       }
       
       if detected_site == 'bbc' and LEGACY_CRAWLERS_AVAILABLE:
           try:
               bbc_info = detect_bbc_url_and_extract_info(input_data)
               analysis_result.update({
                   "bbc_info": bbc_info,
                   "section": bbc_info.get("section"),
                   "description": bbc_info.get("description")
               })
           except Exception as e:
               logger.warning(f"BBC 정보 추출 실패: {e}")
       
       await websocket.send_json(analysis_result)
       
   except Exception as e:
       await websocket.send_json({
           "error": True,
           "error_key": "analysis_failed",
           "error_data": {"error": str(e)}
       })
   finally:
       await websocket.close()

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

# ==================== 자동완성 API ====================
@app.get("/autocomplete/{site}")
async def autocomplete(site: str, keyword: str = Query(...)):
   keyword = keyword.strip().lower()
   
   # BBC URL 감지
   if site == "bbc" and LEGACY_CRAWLERS_AVAILABLE:
       try:
           bbc_detection = detect_bbc_url_and_extract_info(keyword)
           if bbc_detection["is_bbc"]:
               return {
                   "matches": [bbc_detection["board_name"]],
                   "detected_site": "bbc",
                   "auto_detected": True
               }
       except Exception as e:
           logger.warning(f"BBC 자동완성 오류: {e}")
   
   # URL 감지
   if keyword.startswith('http'):
       site_detector = SiteDetector()
       detected_site = await site_detector.detect_site_type(keyword)
       board_name = site_detector.extract_board_identifier(keyword, detected_site)
       
       return {
           "matches": [board_name],
           "detected_site": detected_site,
           "auto_detected": True
       }
   
   # 사이트별 자동완성
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

# ==================== 🔥 통합 시스템 관련 API ====================
@app.get("/api/site-parameters/{site_type}")
async def get_site_parameters(site_type: str):
    """사이트별 지원 매개변수 조회 API"""
    try:
        if UNIFIED_SYSTEM_AVAILABLE:
            params = unified_crawler.get_supported_parameters(site_type)
            if not params:
                raise HTTPException(status_code=404, detail=f"지원하지 않는 사이트: {site_type}")
            
            return {
                "site": site_type,
                "parameters": params,
                "unified_system": True,
                "example_request": {
                    "input": f"example_{site_type}_board",
                    "sort": "recent",
                    "start": 1,
                    "end": 20,
                    **{param: "example_value" for param in params['optional'][:3]}
                }
            }
        else:
            # 레거시 시스템용 하드코딩된 매개변수
            legacy_params = {
                'reddit': {
                    'required': ['subreddit_name'],
                    'optional': ['limit', 'sort', 'time_filter', 'min_views', 'min_likes', 'start_date', 'end_date']
                },
                'lemmy': {
                    'required': ['community_input'],
                    'optional': ['limit', 'sort', 'min_views', 'min_likes', 'time_filter', 'start_date', 'end_date']
                },
                'dcinside': {
                    'required': ['board_name'],
                    'optional': ['limit', 'sort', 'min_views', 'min_likes', 'time_filter', 'start_date', 'end_date']
                },
                'blind': {
                    'required': ['board_input'],
                    'optional': ['limit', 'sort', 'min_views', 'min_likes', 'time_filter', 'start_date', 'end_date']
                },
                'bbc': {
                    'required': ['board_url'],
                    'optional': ['limit', 'sort', 'min_views', 'min_likes', 'min_comments', 'time_filter', 'start_date', 'end_date']
                },
                'universal': {
                    'required': ['board_url'],
                    'optional': ['limit', 'sort', 'min_views', 'min_likes', 'min_comments', 'time_filter', 'start_date', 'end_date']
                }
            }
            
            if site_type not in legacy_params:
                raise HTTPException(status_code=404, detail=f"지원하지 않는 사이트: {site_type}")
            
            return {
                "site": site_type,
                "parameters": legacy_params[site_type],
                "unified_system": False,
                "legacy_mode": True
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/unified-system-status")
async def get_unified_system_status():
    """통합 시스템 상태 확인 API"""
    status = {
        "unified_system_available": UNIFIED_SYSTEM_AVAILABLE,
        "legacy_crawlers_available": LEGACY_CRAWLERS_AVAILABLE,
        "timestamp": datetime.now().isoformat()
    }
    
    if UNIFIED_SYSTEM_AVAILABLE:
        try:
            registry_info = unified_crawler.get_registry_info()
            status.update({
                "unified_system_info": registry_info,
                "total_sites": registry_info['total_sites'],
                "supported_sites": registry_info['supported_sites']
            })
        except Exception as e:
            status["unified_system_error"] = str(e)
    
    return status

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
               "unified_system": UNIFIED_SYSTEM_AVAILABLE,
               "legacy_system": LEGACY_CRAWLERS_AVAILABLE
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
       "unified_system": UNIFIED_SYSTEM_AVAILABLE,
       "legacy_system": LEGACY_CRAWLERS_AVAILABLE
   }
   
   if not UNIFIED_SYSTEM_AVAILABLE and not LEGACY_CRAWLERS_AVAILABLE:
       system_status["status"] = "degraded"
       system_status["message"] = "No crawler systems available"
   
   return system_status

@app.get("/")
def root():
   return {
       "message": "PickPost API Server", 
       "status": "running",
       "version": "2.0.0 (Unified)",
       "docs": "/docs",
       "unified_endpoint": "/ws/crawl",
       "progress_system": "localized",
       "unified_system": UNIFIED_SYSTEM_AVAILABLE,
       "legacy_system": LEGACY_CRAWLERS_AVAILABLE
   }

@app.get("/api/system-info")
async def get_system_info():
    base_info = {
        "version": "2.0.0",
        "environment": APP_ENV,
        "localized_messages": True,
        "endpoints": {
            "unified": "/ws/crawl",
            "analyze": "/ws/analyze",
            "legacy": "/ws/auto-crawl"
        },
        "features": {
            "progress_localization": True,
            "error_localization": True,
            "multi_language_translation": True,
            "cancellation_support": True
        }
    }
    
    # 통합 시스템 정보 추가
    if UNIFIED_SYSTEM_AVAILABLE:
        try:
            registry_info = unified_crawler.get_registry_info()
            base_info.update({
                "unified_crawler": True,
                "crawler_registry": registry_info,
                "supported_sites": registry_info['supported_sites'],
                "features": {
                    **base_info["features"],
                    "unified_parameter_handling": True,
                    "automatic_parameter_filtering": True,
                    "dynamic_crawler_loading": True
                }
            })
        except Exception as e:
            logger.error(f"통합 시스템 정보 조회 오류: {e}")
            base_info["unified_system_error"] = str(e)
    else:
        # 레거시 시스템 정보
        base_info.update({
            "unified_crawler": False,
            "legacy_mode": True,
            "supported_sites": ["reddit", "dcinside", "blind", "bbc", "lemmy", "universal"]
        })
    
    return base_info

# ==================== 서버 시작 ====================
if __name__ == "__main__":
   import uvicorn
   
   # 시스템 상태 로깅
   if UNIFIED_SYSTEM_AVAILABLE:
       logger.info("🔥 PickPost v2.0 서버 시작 (통합 크롤링 시스템)")
   elif LEGACY_CRAWLERS_AVAILABLE:
       logger.info("📚 PickPost v2.0 서버 시작 (레거시 크롤링 시스템)")
   else:
       logger.warning("⚠️ PickPost v2.0 서버 시작 (크롤링 시스템 없음)")
   
   uvicorn.run(app, host="0.0.0.0", port=PORT)
