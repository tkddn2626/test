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

# 기존 크롤러 모듈 import
try:
    from reddit import fetch_posts
    from blind import crawl_blind_board
    from dcinside import crawl_dcinside_board
    from universal import crawl_universal_board
    from lemmy import crawl_lemmy_board
    from bbc import crawl_bbc_board, detect_bbc_url_and_extract_info
    LEGACY_CRAWLERS_AVAILABLE = True
    logger.info("✅ 레거시 크롤러 모듈 로드 성공")
except ImportError as e:
    logger.error(f"❌ 크롤러 모듈 로드 실패: {e}")
    LEGACY_CRAWLERS_AVAILABLE = False

# 간단한 사이트 감지기
class SiteDetector:
    async def detect_site_type(self, input_data: str) -> str:
        input_lower = input_data.lower()
        
        if 'reddit.com' in input_lower or '/r/' in input_lower:
            return 'reddit'
        elif any(lemmy_domain in input_lower for lemmy_domain in [
            'lemmy.world', 'lemmy.ml', 'beehaw.org', 'sh.itjust.works'
        ]) or '@lemmy' in input_lower:
            return 'lemmy'
        elif 'dcinside.com' in input_lower or 'gall.dcinside' in input_lower:
            return 'dcinside'
        elif 'teamblind.com' in input_lower or 'blind.com' in input_lower:
            return 'blind'
        elif 'bbc.com' in input_lower or 'bbc.co.uk' in input_lower:
            return 'bbc'
        elif input_data.startswith('http'):
            return 'universal'
        
        # 키워드 기반
        if any(word in input_lower for word in ['reddit', 'subreddit']):
            return 'reddit'
        elif any(word in input_lower for word in ['lemmy', '레미']):
            return 'lemmy'
        elif any(word in input_lower for word in ['dcinside', 'dc', '디시']):
            return 'dcinside'
        elif any(word in input_lower for word in ['blind', '블라인드']):
            return 'blind'
        elif any(word in input_lower for word in ['bbc', 'british']):
            return 'bbc'
        else:
            return 'universal'
    
    def extract_board_identifier(self, url: str, site_type: str) -> str:
        if site_type == 'reddit' and '/r/' in url:
            import re
            match = re.search(r'/r/([^/]+)', url)
            return match.group(1) if match else url
        elif site_type == 'lemmy' and '/c/' in url:
            parts = url.split('/c/')
            if len(parts) > 1:
                from urllib.parse import urlparse
                try:
                    domain = urlparse(url).netloc
                    community = parts[1].split('/')[0]
                    return f"{community}@{domain}"
                except:
                    pass
        elif site_type == 'dcinside' and '?id=' in url:
            import re
            match = re.search(r'[?&]id=([^&]+)', url)
            return match.group(1) if match else url
        
        return url

# 유틸리티 함수들
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

calculate_actual_dates_for_lemmy = calculate_actual_dates

# 크롤링 관리자
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

# 사이트별 크롤링 실행
async def execute_crawl_by_site(site_type: str, target_input: str, **config):
    crawl_id = config.pop('crawl_id', None)
    
    if crawl_id and crawl_manager.is_cancelled(crawl_id):
        raise asyncio.CancelledError("크롤링 취소됨")
    
    if not LEGACY_CRAWLERS_AVAILABLE:
        raise Exception("크롤러 모듈을 사용할 수 없습니다")
    
    logger.info(f"🚀 사이트별 크롤링 시작: {site_type} -> {target_input}")
    
    try:
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
            params = {k: v for k, v in params.items() if v is not None}
            return await fetch_posts(**params)
            
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
            params = {k: v for k, v in params.items() if v is not None}
            return await crawl_lemmy_board(**params)
            
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
            params = {k: v for k, v in params.items() if v is not None}
            return await crawl_dcinside_board(**params)
            
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
            params = {k: v for k, v in params.items() if v is not None}
            return await crawl_blind_board(**params)
            
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
            params = {k: v for k, v in params.items() if v is not None}
            return await crawl_bbc_board(**params)
            
        elif site_type == 'universal':
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
            params = {k: v for k, v in params.items() if v is not None}
            return await crawl_universal_board(**params)
        else:
            raise ValueError(f"지원하지 않는 사이트 타입: {site_type}")
            
    except Exception as e:
        logger.error(f"❌ 크롤링 오류 ({site_type}): {e}")
        raise

# 번역 서비스
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

# FastAPI 앱 초기화
app = FastAPI(title="PickPost API v2.0", debug=DEBUG)

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

# 통합 크롤링 엔드포인트
@app.websocket("/ws/crawl")
async def unified_crawl_endpoint(websocket: WebSocket):
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
    crawl_id = f"unified_{id(websocket)}_{int(time.time())}"
    logger.info(f"🔥 통합 크롤링 시작: {crawl_id}")
    
    try:
        config = await websocket.receive_json()
        user_lang = get_user_language(config)
        
        input_data = config.get("input", "").strip()
        
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
        
        # 사이트 감지
        await websocket.send_json({"progress": 5, "status": "사이트 감지 중..."})
        check_cancelled()

        site_detector = SiteDetector()
        detected_site = await site_detector.detect_site_type(input_data)
        board_identifier = site_detector.extract_board_identifier(input_data, detected_site)
        
        logger.info(f"감지된 사이트: {detected_site}, 게시판: {board_identifier}")

        # 사이트 연결
        await websocket.send_json({
            "progress": 15, 
            "status": f"{detected_site.upper()} 연결 중..."
        })
        check_cancelled()

        # 게시물 수집
        await websocket.send_json({
            "progress": 30, 
            "status": f"{detected_site.upper()}에서 게시물 수집 중..."
        })
        check_cancelled()

        raw_posts = await execute_crawl_by_site(
            detected_site, 
            board_identifier, 
            **crawl_options
        )

        check_cancelled()

        if raw_posts:
            await websocket.send_json({
                "progress": 60, 
                "status": f"게시물 필터링 중... ({len(raw_posts)}개 발견)"
            })

        await websocket.send_json({"progress": 75, "status": "데이터 처리 중..."})
        check_cancelled()

        if not raw_posts:
            await websocket.send_json({
                "error": f"{detected_site.upper()}에서 게시물을 찾을 수 없습니다"
            })
            return

        # 번역 처리
        results = []
        translate = crawl_options.get('translate', False)
        target_languages = crawl_options.get('target_languages', [])
        
        if translate and target_languages:
            await websocket.send_json({
                "progress": 80, 
                "status": f"번역 준비 중... ({len(raw_posts)}개 게시물)"
            })
            
            for idx, post in enumerate(raw_posts):
                check_cancelled()
                
                original_title = post.get('원제목', '')
                
                if any(ord(char) > 127 for char in original_title):
                    for lang_code in target_languages:
                        translated = await deepl_translate(original_title, lang_code)
                        post[f'번역제목_{lang_code}'] = translated
                else:
                    for lang_code in target_languages:
                        post[f'번역제목_{lang_code}'] = original_title
                
                results.append(post)
                
                if len(raw_posts) > 0:
                    translation_progress = 85 + int((idx + 1) / len(raw_posts) * 10)
                    await websocket.send_json({
                        "progress": translation_progress,
                        "status": f"번역 중... ({idx + 1}/{len(raw_posts)})"
                    })
        else:
            for post in raw_posts:
                original_title = post.get('원제목', '')
                if any(ord(char) > 127 for char in original_title):
                    post['번역제목'] = original_title
                else:
                    post['번역제목'] = await deepl_translate(original_title, "KO")
                results.append(post)

        check_cancelled()

        await websocket.send_json({"progress": 95, "status": "결과 정리 중..."})

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

# 레거시 자동 크롤링 엔드포인트
@app.websocket("/ws/auto-crawl")
async def crawl_auto_socket(websocket: WebSocket):
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
            await websocket.send_json({"error": "게시판 입력이 필요합니다"})
            return

        actual_start_date, actual_end_date = calculate_actual_dates(
            time_filter, start_date_input, end_date_input
        )

        crawl_config = {
            'sort': sort,
            'start_index': start,
            'end_index': end,
            'min_views': min_views,
            'min_likes': min_likes,
            'time_filter': time_filter,
            'start_date': actual_start_date,
            'end_date': actual_end_date,
            'websocket': websocket,
            'crawl_id': crawl_id
        }

        await websocket.send_json({"progress": 5, "status": "사이트 감지 중..."})
        check_cancelled()

        site_detector = SiteDetector()
        detected_site = await site_detector.detect_site_type(board_input)
        board_identifier = site_detector.extract_board_identifier(board_input, detected_site)

        raw_posts = await execute_crawl_by_site(
            detected_site, 
            board_identifier, 
            **crawl_config
        )
        
        if not raw_posts:
            await websocket.send_json({"error": "게시물을 찾을 수 없습니다"})
            return

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

        await websocket.send_json({
            "done": True,
            "data": results,
            "summary": f"크롤링 완료: {len(results)}개 게시물"
        })

    except asyncio.CancelledError:
        await websocket.send_json({"cancelled": True})
    except Exception as e:
        logger.error(f"❌ Auto crawl error: {e}")
        await websocket.send_json({"error": str(e)})
    finally:
        crawl_manager.cleanup_crawl(crawl_id)
        await websocket.close()

# 자동완성 API
@app.get("/autocomplete/{site}")
async def autocomplete(site: str, keyword: str = Query(...)):
    keyword = keyword.strip().lower()
    
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

# 크롤링 취소 시스템
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

# 피드백 시스템
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

# 기본 API
@app.get("/health")
def health_check():
    system_status = {
        "status": "healthy",
        "message": "PickPost API is running",
        "legacy_system": LEGACY_CRAWLERS_AVAILABLE
    }
    
    if not LEGACY_CRAWLERS_AVAILABLE:
        system_status["status"] = "degraded"
        system_status["message"] = "No crawler systems available"
    
    return system_status

@app.get("/")
def root():
    return {
        "message": "PickPost API Server", 
        "status": "running",
        "version": "2.0.0 (Fixed)",
        "docs": "/docs",
        "unified_endpoint": "/ws/crawl",
        "legacy_system": LEGACY_CRAWLERS_AVAILABLE
    }

@app.get("/api/system-info")
async def get_system_info():
    return {
        "version": "2.0.0",
        "environment": APP_ENV,
        "localized_messages": True,
        "supported_sites": ["reddit", "dcinside", "blind", "bbc", "lemmy", "universal"],
        "endpoints": {
            "unified": "/ws/crawl",
            "legacy": "/ws/auto-crawl"
        },
        "features": {
            "progress_localization": True,
            "error_localization": True,
            "multi_language_translation": True,
            "cancellation_support": True,
            "automatic_parameter_filtering": True
        },
        "system_status": {
            "legacy_crawlers": LEGACY_CRAWLERS_AVAILABLE
        }
    }

# 서버 시작
if __name__ == "__main__":
    import uvicorn
    
    logger.info("🚀 PickPost v2.0 서버 시작 (수정된 버전)")
    logger.info(f"   레거시 크롤러: {'✅' if LEGACY_CRAWLERS_AVAILABLE else '❌'}")
    
    if not LEGACY_CRAWLERS_AVAILABLE:
        logger.error("❌ 크롤링 시스템을 사용할 수 없습니다!")
    
    uvicorn.run(app, host="0.0.0.0", port=PORT)
