# main.py - 미디어 다운로드 기능 포함 완전 버전

from fastapi import FastAPI, WebSocket, Query, Request, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Set, Any, List
import os, asyncio, json, requests, time, logging, traceback
from datetime import datetime, timedelta
from dotenv import load_dotenv
from pathlib import Path
import sys
import importlib.util
from core.site_detector import DynamicSiteDetector
from core.messages import create_localized_message
from core.first_visitor import first_visitor_router

# ==================== 🔥 로깅 설정을 가장 먼저 ==================== 
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

# 🔥 Supabase 환경 변수 확인
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

# 🔥 로깅 설정 - 다른 모든 것보다 먼저!
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("pickpost")

# 🔥 이제 database 모듈 import (로깅 설정 후)
try:
    from database import save_feedback_to_database, get_feedback_from_database, get_database_status
    DATABASE_AVAILABLE = True
    logger.info("✅ 데이터베이스 모듈 로드 성공")
except ImportError as e:
    DATABASE_AVAILABLE = False
    logger.warning(f"⚠️ 데이터베이스 모듈 로드 실패: {e}")

# AutoCrawler import 추가
try:
   from core.auto_crawler import AutoCrawler
   AUTO_CRAWLER_AVAILABLE = True
   logger.info("✅ AutoCrawler 로드 성공")
except ImportError as e:
   logger.error(f"❌ AutoCrawler 로드 실패: {e}")
   AUTO_CRAWLER_AVAILABLE = False

# 🔥 미디어 다운로드 모듈 import 추가
try:
    from core.media_download import get_media_download_manager
    MEDIA_DOWNLOAD_AVAILABLE = True
    logger.info("✅ 미디어 다운로드 모듈 로드 성공")
except ImportError as e:
    MEDIA_DOWNLOAD_AVAILABLE = False
    logger.warning(f"⚠️ 미디어 다운로드 모듈 로드 실패: {e}")

# ==================== 동적 크롤러 발견 시스템 ====================

def discover_available_crawlers():
    """backend/crawlers/ 디렉토리에서 사용 가능한 크롤러들을 동적으로 발견"""
    current_dir = Path(__file__).parent
    crawlers_dir = current_dir / "crawlers"
    available_crawlers = set()
    
    if not crawlers_dir.exists():
        logger.warning(f"⚠️ crawlers 디렉토리가 없습니다: {crawlers_dir}")
        if AUTO_CRAWLER_AVAILABLE:
            available_crawlers.add('universal')
            logger.debug("✅ AutoCrawler(universal)만 사용 가능")
        return available_crawlers
    
    for py_file in crawlers_dir.glob("*.py"):
        if py_file.name.startswith('_') or py_file.stem == '__init__':
            continue
            
        crawler_name = py_file.stem
        
        try:
            spec = importlib.util.spec_from_file_location(f"crawlers.{crawler_name}", py_file)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                crawl_functions = [
                    f'crawl_{crawler_name}_board',
                    f'fetch_posts',
                    f'crawl_{crawler_name}',
                    f'{crawler_name}_crawl',
                    f'crawl_{crawler_name.lower()}_board',
                ]
                
                has_crawl_function = any(hasattr(module, func) for func in crawl_functions)
                
                if has_crawl_function:
                    available_crawlers.add(crawler_name)
                    logger.debug(f"✅ 크롤러 발견: crawlers/{crawler_name}")
                else:
                    logger.debug(f"⚠️ 크롤링 함수 없음: crawlers/{crawler_name}")
                    
        except Exception as e:
            logger.debug(f"⚠️ 크롤러 확인 실패 crawlers/{crawler_name}: {e}")
    
    if AUTO_CRAWLER_AVAILABLE:
        available_crawlers.add('universal')
        logger.debug("✅ AutoCrawler(universal) 사용 가능")
    
    logger.info(f"🎯 사용 가능한 크롤러: {sorted(available_crawlers)}")
    return available_crawlers

def import_available_crawlers():
    """사용 가능한 크롤러들을 동적으로 import"""
    crawl_functions = {}
    
    current_dir = Path(__file__).parent
    crawlers_dir = current_dir / "crawlers"
    
    if not crawlers_dir.exists():
        logger.warning(f"⚠️ crawlers 디렉토리가 없습니다: {crawlers_dir}")
        return crawl_functions
    
    for py_file in crawlers_dir.glob("*.py"):
        if py_file.name.startswith('_') or py_file.stem == '__init__':
            continue
            
        crawler_name = py_file.stem
        
        try:
            spec = importlib.util.spec_from_file_location(f"crawlers.{crawler_name}", py_file)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                possible_functions = [
                    f'crawl_{crawler_name}_board',
                    f'fetch_posts',
                    f'crawl_{crawler_name}',
                    f'{crawler_name}_crawl',
                    f'crawl_board',
                    f'crawl'
                ]
                
                found_functions = []
                for func_name in possible_functions:
                    if hasattr(module, func_name):
                        func = getattr(module, func_name)
                        if callable(func):
                            found_functions.append((func_name, func))
                
                if found_functions:
                    main_func_name, main_func = found_functions[0]
                    crawl_functions[crawler_name] = main_func
                    logger.debug(f"✅ {crawler_name} 크롤러 import 성공 ({main_func_name})")
                    
                    for func_name, func in found_functions[1:]:
                        special_key = f"{crawler_name}_{func_name}"
                        crawl_functions[special_key] = func
                        logger.debug(f"   추가 함수: {special_key}")
                    
                    special_functions = [
                        f'detect_{crawler_name}_url_and_extract_info',
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

# core/ 폴더의 SiteDetector import (폴백용)
try:
    from core.site_detector import SiteDetector as CoreSiteDetector
    CORE_SITE_DETECTOR_AVAILABLE = True
    logger.info("✅ Core SiteDetector 로드 성공")
except ImportError as e:
    logger.warning(f"⚠️ Core SiteDetector 로드 실패: {e}")
    CORE_SITE_DETECTOR_AVAILABLE = False

# ==================== FastAPI 앱 초기화 ====================
app = FastAPI(title="PickPost API v2.1", debug=DEBUG)

# ==================== 🔥 정적 파일 라우팅 최우선 설정 ====================

# 🔥 정적 파일 개별 엔드포인트 (라우터보다 먼저 정의)
@app.get("/js/{file_path:path}")
async def serve_js_files(file_path: str):
    """JavaScript 파일 직접 서빙 - 최우선 처리"""
    # 현재 디렉토리에서 js 폴더 찾기
    possible_paths = [
        Path("js") / file_path,           # ./js/
        Path("static/js") / file_path,    # ./static/js/
        Path("frontend/js") / file_path,  # ./frontend/js/
        Path(".") / "js" / file_path      # 절대 경로
    ]
    
    for js_path in possible_paths:
        if js_path.exists() and js_path.is_file():
            logger.info(f"🎯 JavaScript 파일 서빙: {js_path}")
            return FileResponse(
                js_path,
                media_type="application/javascript; charset=utf-8",
                headers={
                    "Content-Type": "application/javascript; charset=utf-8",
                    "Cache-Control": "public, max-age=3600",
                    "Access-Control-Allow-Origin": "*"
                }
            )
    
    logger.error(f"❌ JavaScript 파일 없음: {file_path}")
    logger.error(f"   시도한 경로들: {[str(p) for p in possible_paths]}")
    raise HTTPException(status_code=404, detail=f"JavaScript file not found: {file_path}")

@app.get("/css/{file_path:path}")
async def serve_css_files(file_path: str):
    """CSS 파일 직접 서빙"""
    possible_paths = [
        Path("css") / file_path,
        Path("static/css") / file_path,
        Path("frontend/css") / file_path,
        Path(".") / "css" / file_path
    ]
    
    for css_path in possible_paths:
        if css_path.exists() and css_path.is_file():
            logger.info(f"🎨 CSS 파일 서빙: {css_path}")
            return FileResponse(
                css_path,
                media_type="text/css; charset=utf-8",
                headers={
                    "Content-Type": "text/css; charset=utf-8",
                    "Cache-Control": "public, max-age=3600",
                    "Access-Control-Allow-Origin": "*"
                }
            )
    
    raise HTTPException(status_code=404, detail=f"CSS file not found: {file_path}")

# 루트 경로에서 index.html 서빙 (정적 파일 엔드포인트 다음에 정의)
@app.get("/")
async def serve_index():
    """루트 경로에서 index.html 제공"""
    possible_paths = [
        Path("index.html"),
        Path("static/index.html"),
        Path("frontend/index.html"),
        Path(".") / "index.html"
    ]
    
    for index_path in possible_paths:
        if index_path.exists() and index_path.is_file():
            logger.info(f"🏠 index.html 서빙: {index_path}")
            return FileResponse(
                index_path,
                media_type="text/html; charset=utf-8",
                headers={
                    "Content-Type": "text/html; charset=utf-8",
                    "Cache-Control": "public, max-age=300",
                    "Access-Control-Allow-Origin": "*"
                }
            )
    
    # index.html이 없으면 API 정보 반환
    return {
        "message": "PickPost API Server", 
        "status": "running",
        "version": "2.1.1 (Media Download Support)",
        "docs": "/docs",
        "static_files_status": "Direct routing enabled",
        "media_download_status": "✅ Available" if MEDIA_DOWNLOAD_AVAILABLE else "❌ Unavailable"
    }

# 첫 번째 방문자 라우터 추가 (정적 파일 라우팅 이후)
app.include_router(first_visitor_router)

# ==================== 🔥 CORS 및 미들웨어 설정 ====================
@app.middleware("http")
async def cors_and_static_middleware(request, call_next):
    """CORS 및 정적 파일 처리 미들웨어"""
    
    # OPTIONS 요청 처리
    if request.method == "OPTIONS":
        response = JSONResponse({"message": "OK"})
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "*"
        response.headers["Access-Control-Max-Age"] = "86400"
        response.headers["Access-Control-Allow-Credentials"] = "true"
        return response
    
    # 일반 요청 처리
    response = await call_next(request)
    
    # 모든 응답에 CORS 헤더 추가
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "*"
    
    return response

# 기본 CORS 미들웨어
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=86400
)

# ==================== 🔥 미디어 다운로드 모델 정의 ====================

class MediaDownloadRequest(BaseModel):
    posts: List[Dict[str, Any]]  # 크롤링된 게시물 데이터
    site_type: str               # reddit, 4chan, dcinside 등
    include_images: bool = True
    include_videos: bool = True
    include_audio: bool = False
    max_file_size_mb: int = 50   # 개별 파일 최대 크기

class MediaDownloadResponse(BaseModel):
    success: bool
    download_url: str = ""
    zip_filename: str = ""
    total_files: int = 0
    downloaded_files: int = 0
    failed_files: int = 0
    zip_size_mb: float = 0
    error: str = ""

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
    
    # 전용 크롤러 직접 호출
    if site_type in CRAWL_FUNCTIONS:
        try:
            crawl_func = CRAWL_FUNCTIONS[site_type]
            logger.info(f"🎯 전용 크롤러 직접 사용: {site_type} -> {target_input}")
            
            # 사이트별 매개변수 준비 (기존 코드와 동일)
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
            else:
                # 일반적인 매개변수
                params = {
                    'target_input': target_input,
                    **{k: v for k, v in config.items() if v is not None}
                }
            
            params = {k: v for k, v in params.items() if v is not None}
            return await crawl_func(**params)
            
        except Exception as e:
            logger.warning(f"⚠️ 전용 크롤러 실패, AutoCrawler로 폴백: {e}")
    
    # AutoCrawler 사용
    if AUTO_CRAWLER_AVAILABLE:
        try:
            auto_crawler = AutoCrawler()
            config['force_site_type'] = site_type
            logger.info(f"🤖 AutoCrawler 폴백 사용: {site_type} -> {target_input}")
            return await auto_crawler.crawl(target_input, **config)
        except Exception as e:
            logger.error(f"❌ AutoCrawler도 실패: {e}")
            raise
    
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

# ==================== 미디어 다운로드 API 엔드포인트 ====================
@app.post("/api/download-media", response_model=MediaDownloadResponse)
async def download_media_files(request: MediaDownloadRequest):
    """미디어 파일 크롤링 및 ZIP 다운로드 생성"""
    
    if not MEDIA_DOWNLOAD_AVAILABLE:
        raise HTTPException(
            status_code=503, 
            detail="Media download service is currently unavailable"
        )
    
    try:
        logger.info(f"🖼️ Media download request: {len(request.posts)} posts ({request.site_type})")
        
        # 사용자 언어 감지 (기본값: 영어)
        user_lang = getattr(request, 'user_lang', 'en')
        
        # 미디어 다운로드 매니저 사용
        async with get_media_download_manager(user_lang) as manager:
            
            # 진행률 콜백 함수 (선택사항)
            async def progress_callback(current, total):
                percentage = (current / total) * 100
                logger.debug(f"Media download progress: {percentage:.1f}% ({current}/{total})")
            
            # 미디어 일괄 다운로드 실행 - 올바른 메서드 이름 사용
            result = await manager.download_media_from_posts(
                posts=request.posts,
                site_type=request.site_type,
                progress_callback=progress_callback
            )
            
            if result['success']:
                # 응답 형식이 다르므로 수정
                return MediaDownloadResponse(
                    success=True,
                    download_url=result['download_url'],
                    zip_filename=result['zip_filename'],
                    total_files=result['total_media_found'],
                    downloaded_files=result['downloaded_files'],
                    failed_files=result['failed_files'],
                    zip_size_mb=result['zip_size_mb']
                )
            else:
                return MediaDownloadResponse(
                    success=False,
                    error=result.get('error', 'Media download failed'),
                    total_files=result.get('total_media_found', 0),
                    downloaded_files=result.get('downloaded_files', 0),
                    failed_files=result.get('failed_files', 0)
                )
                
    except Exception as e:
        logger.error(f"❌ Media download processing error: {e}")
        return MediaDownloadResponse(
            success=False,
            error=f"Error during media download: {str(e)}"
        )

@app.get("/api/download-file/{filename}")
async def download_file(filename: str):
    """ZIP 파일 다운로드 엔드포인트"""
    try:
        # 임시 다운로드 디렉토리에서 파일 찾기
        from core.media_download import TEMP_DOWNLOAD_DIR
        
        file_path = TEMP_DOWNLOAD_DIR / filename
        
        if not file_path.exists() or not file_path.is_file():
            raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다")
        
        # 파일 크기 확인 (너무 큰 파일 방지)
        file_size_mb = file_path.stat().st_size / (1024 * 1024)
        if file_size_mb > 1000:  # 1GB 제한
            raise HTTPException(status_code=413, detail="파일이 너무 큽니다")
        
        logger.info(f"📥 미디어 ZIP 다운로드: {filename} ({file_size_mb:.1f}MB)")
        
        return FileResponse(
            path=file_path,
            filename=filename,
            media_type="application/zip",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 파일 다운로드 오류: {e}")
        raise HTTPException(status_code=500, detail="파일 다운로드 중 오류 발생")

@app.get("/api/media-info")
async def get_media_manager_info():
    """미디어 다운로드 매니저 정보 조회"""
    
    if not MEDIA_DOWNLOAD_AVAILABLE:
        return {
            "available": False,
            "error": "미디어 다운로드 모듈을 로드할 수 없습니다"
        }
    
    try:
        manager = get_media_download_manager()
        info = manager.get_manager_info()
        
        return {
            "available": True,
            "manager_info": info,
            "supported_sites": manager.extractor_manager.get_supported_sites()
        }
        
    except Exception as e:
        logger.error(f"❌ 미디어 매니저 정보 조회 오류: {e}")
        return {
            "available": False,
            "error": str(e)
        }

# ==================== 디버깅 엔드포인트 ====================
@app.get("/api/debug/static-files")
async def debug_static_files():
    """정적 파일 디버깅 정보"""
    current_path = Path(".")
    
    # 가능한 모든 경로 체크
    paths_to_check = [
        "js/first_one.js",
        "js/present.js",
        "static/js/first_one.js",
        "static/js/present.js",
        "frontend/js/first_one.js",
        "frontend/js/present.js",
        "index.html",
        "static/index.html",
        "frontend/index.html"
    ]
    
    file_status = {}
    for path_str in paths_to_check:
        path = Path(path_str)
        file_status[path_str] = {
            "exists": path.exists(),
            "is_file": path.is_file() if path.exists() else False,
            "absolute_path": str(path.absolute())
        }
    
    # 디렉토리 구조
    js_dirs = []
    for js_dir in ["js", "static/js", "frontend/js"]:
        js_path = Path(js_dir)
        if js_path.exists() and js_path.is_dir():
            js_files = [f.name for f in js_path.glob("*.js")]
            js_dirs.append({
                "path": str(js_path),
                "exists": True,
                "files": js_files
            })
        else:
            js_dirs.append({
                "path": str(js_path),
                "exists": False,
                "files": []
            })
    
    return {
        "current_directory": str(current_path.absolute()),
        "file_status": file_status,
        "js_directories": js_dirs,
        "routing_order": [
            "1. /js/{file_path:path} -> serve_js_files()",
            "2. /css/{file_path:path} -> serve_css_files()",
            "3. / -> serve_index()",
            "4. first_visitor_router",
            "5. other API routes"
        ]
    }

# ==================== 피드백 시스템 ====================
class FeedbackRequest(BaseModel):
    description: Optional[str] = None
    message: Optional[str] = None
    hasFile: Optional[bool] = False
    fileName: Optional[str] = None
    fileSize: Optional[int] = None
    systemInfo: Optional[Dict] = None
    currentLanguage: Optional[str] = "en"
    currentSite: Optional[str] = None
    url: Optional[str] = None

def save_feedback_locally(feedback_data: Dict) -> Dict:
    """로컬 파일에 피드백 저장"""
    try:
        feedback_dir = "outputs/feedback"
        os.makedirs(feedback_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        
        local_feedback = {
            "timestamp": timestamp,
            "content": feedback_data.get("description", ""),
            "metadata": feedback_data,
            "system_info": {
                "auto_crawler_available": AUTO_CRAWLER_AVAILABLE,
                "core_site_detector_available": CORE_SITE_DETECTOR_AVAILABLE,
                "available_crawlers": list(AVAILABLE_CRAWLERS),
                "loaded_crawl_functions": list(CRAWL_FUNCTIONS.keys()),
                "database_available": DATABASE_AVAILABLE,
                "media_download_available": MEDIA_DOWNLOAD_AVAILABLE
            }
        }
        
        filename = f"feedback_{timestamp}.json"
        filepath = os.path.join(feedback_dir, filename)
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(local_feedback, f, ensure_ascii=False, indent=2)

        return {
            "feedback_id": f"local_{timestamp}",
            "status": "success",
            "message": "피드백이 로컬에 저장되었습니다"
        }
        
    except Exception as e:
        logger.error(f"❌ 로컬 저장 실패: {e}")
        raise HTTPException(status_code=500, detail=f"로컬 저장 실패: {str(e)}")

@app.post("/api/feedback")
async def submit_feedback(request: Request, feedback: Optional[FeedbackRequest] = None):
    """피드백 제출 API"""
    try:
        if feedback:
            feedback_content = feedback.description or feedback.message or ""
            raw_data = feedback.dict()
        else:
            raw_data = await request.json()
            feedback_content = raw_data.get("description", raw_data.get("message", "")).strip()
        
        if not feedback_content:
            return JSONResponse(
                status_code=400, 
                content={"error": "피드백 내용이 필요합니다"}
            )
        
        raw_data["client_ip"] = request.client.host
        raw_data["timestamp"] = datetime.now().isoformat()
        
        if DATABASE_AVAILABLE:
            try:
                result = await save_feedback_to_database(raw_data)
                logger.info(f"✅ Supabase 피드백 저장 성공: ID {result.get('feedback_id')}")
                return {
                    "success": True,
                    "feedback_id": result.get("feedback_id"),
                    "message": "피드백이 데이터베이스에 저장되었습니다",
                    "storage": "supabase"
                }
            except Exception as e:
                logger.warning(f"⚠️ Supabase 저장 실패, 로컬 저장으로 폴백: {e}")
        
        result = save_feedback_locally(raw_data)
        logger.info(f"📁 피드백 로컬 저장: {feedback_content[:50]}...")
        
        return {
            "success": True,
            "feedback_id": result.get("feedback_id"),
            "message": "피드백이 저장되었습니다",
            "storage": "local"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 피드백 처리 오류: {e}")
        return JSONResponse(
            status_code=500, 
            content={"error": f"피드백 처리 오류: {str(e)}"}
        )

# ==================== 웹소켓 크롤링 엔드포인트 ====================
@app.websocket("/ws/crawl")
async def websocket_crawl(websocket: WebSocket):
    await websocket.accept()
    crawl_id = f"unified_{id(websocket)}_{int(time.time())}"
    logger.info(f"🔥 통합 크롤링 시작: {crawl_id}")
    
    try:
        config = await websocket.receive_json()
        user_lang = config.get("language", "en")
        
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
        
        # 사이트 감지 로직
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
            # 사이트 감지 메시지
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

        # 사이트 연결 메시지
        site_display = detected_site.upper() if detected_site != 'lemmy' else 'Lemmy'
        message = create_localized_message(
            progress=15,
            status_key="crawlingProgress.site_connecting",
            lang=user_lang,
            status_data={"site": site_display}
        )
        await websocket.send_json(message)
        check_cancelled()

        # 게시물 수집 메시지
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
            # 게시물 필터링 메시지
            message = create_localized_message(
                progress=60,
                status_key="crawlingProgress.posts_filtering",
                lang=user_lang,
                status_data={"matched": len(raw_posts), "total": len(raw_posts)}
            )
            await websocket.send_json(message)

        # 데이터 처리 메시지
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
            
            # 번역 준비 메시지
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
                    
                    # 번역 진행 메시지
                    message = create_localized_message(
                        progress=translation_progress,
                        status_key="crawlingProgress.translation_progress",
                        lang=user_lang,
                        status_data={"current": idx + 1, "total": len(raw_posts)}
                    )
                    await websocket.send_json(message)

        check_cancelled()

        # 결과 정리 메시지
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
    
    # BBC 자동완성
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

# ==================== 크롤링 취소 API ====================
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

# ==================== 피드백 관리 API ====================
@app.get("/api/feedback")
async def get_feedback_list(limit: int = 50, offset: int = 0):
    """피드백 목록 조회 (관리자용)"""
    
    if not DATABASE_AVAILABLE:
        return JSONResponse(
            status_code=503,
            content={"error": "데이터베이스 연결을 사용할 수 없습니다"}
        )
    
    try:
        result = await get_feedback_from_database(limit, offset)
        return result
        
    except Exception as e:
        logger.error(f"❌ 피드백 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/database-status")
async def get_database_status_endpoint():
    """데이터베이스 연결 상태 확인"""
    
    status = {
        "database_module_available": DATABASE_AVAILABLE,
        "supabase_configured": bool(SUPABASE_URL and SUPABASE_ANON_KEY),
        "environment_variables": {
            "SUPABASE_URL": "✅ 설정됨" if SUPABASE_URL else "❌ 미설정",
            "SUPABASE_ANON_KEY": "✅ 설정됨" if SUPABASE_ANON_KEY else "❌ 미설정"
        }
    }
    
    if DATABASE_AVAILABLE:
        try:
            db_status = get_database_status()
            status.update(db_status)
        except Exception as e:
            status["database_error"] = str(e)
    
    return status

# ==================== 기본 API 엔드포인트들 ====================
@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "message": "PickPost API is running",
        "static_files_routing": "Direct routing enabled",
        "version": "2.1.1-media",
        "media_download": "✅ Available" if MEDIA_DOWNLOAD_AVAILABLE else "❌ Unavailable"
    }

@app.get("/api/health")
async def api_health_check():
    return {
        "status": "healthy",
        "api_version": "2.1",
        "static_files_enabled": True,
        "media_download_enabled": MEDIA_DOWNLOAD_AVAILABLE,
        "endpoints": [
            "/api/check-first-visitor",
            "/api/claim-first-visitor", 
            "/api/admin/login",
            "/api/admin/first-visitor-info",
            "/api/admin/reset-first-visitor",
            "/api/download-media",
            "/api/media-info"
        ]
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
            "autocomplete": "/autocomplete/{site}",
            "feedback": "/api/feedback",
            "media_download": "/api/download-media",
            "media_info": "/api/media-info"
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
            "core_site_detector": CORE_SITE_DETECTOR_AVAILABLE,
            "supabase_database": DATABASE_AVAILABLE,
            "enhanced_cors": True,
            "static_files_serving": True,
            "media_download": MEDIA_DOWNLOAD_AVAILABLE
        },
        "system_status": {
            "auto_crawler": AUTO_CRAWLER_AVAILABLE,
            "core_site_detector": CORE_SITE_DETECTOR_AVAILABLE,
            "available_crawlers": list(AVAILABLE_CRAWLERS),
            "functional_crawlers": list(CRAWL_FUNCTIONS.keys()),
            "database_available": DATABASE_AVAILABLE,
            "supabase_configured": bool(SUPABASE_URL and SUPABASE_ANON_KEY),
            "cors_configured": True,
            "static_files_enabled": True,
            "media_download_available": MEDIA_DOWNLOAD_AVAILABLE
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
        "auto_crawler_enabled": AUTO_CRAWLER_AVAILABLE,
        "database_available": DATABASE_AVAILABLE,
        "cors_enabled": True,
        "static_files_enabled": True,
        "media_download_enabled": MEDIA_DOWNLOAD_AVAILABLE
    }

# ==================== 서버 시작 ====================
if __name__ == "__main__":
    import uvicorn
    
    logger.info("🚀 PickPost v2.1.1 서버 시작 (미디어 다운로드 지원)")
    logger.info(f"   정적 파일 라우팅: ✅ 직접 엔드포인트 방식")
    logger.info(f"   JavaScript 파일: /js/{{filename}} -> serve_js_files()")
    logger.info(f"   CSS 파일: /css/{{filename}} -> serve_css_files()")
    logger.info(f"   AutoCrawler: {'✅' if AUTO_CRAWLER_AVAILABLE else '❌'}")
    logger.info(f"   Core SiteDetector: {'✅' if CORE_SITE_DETECTOR_AVAILABLE else '❌'}")
    logger.info(f"   Database: {'✅' if DATABASE_AVAILABLE else '❌'}")
    logger.info(f"   Media Download: {'✅' if MEDIA_DOWNLOAD_AVAILABLE else '❌'}")
    logger.info(f"   발견된 크롤러: {list(AVAILABLE_CRAWLERS)}")
    logger.info(f"   로드된 함수: {list(CRAWL_FUNCTIONS.keys())}")
    
    if MEDIA_DOWNLOAD_AVAILABLE:
        try:
            manager = get_media_download_manager()
            supported_sites = manager.extractor_manager.get_supported_sites()
            logger.info(f"   미디어 지원 사이트: {supported_sites}")
        except Exception as e:
            logger.warning(f"   미디어 매니저 정보 로드 실패: {e}")
    
    if not AUTO_CRAWLER_AVAILABLE and not CRAWL_FUNCTIONS:
        logger.error("❌ 모든 크롤링 시스템을 사용할 수 없습니다!")
    
    uvicorn.run(app, host="0.0.0.0", port=PORT)