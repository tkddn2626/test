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

# 크롤러 모듈 import
from reddit import fetch_posts
from blind import crawl_blind_board
from dcinside import crawl_dcinside_board
from universal import crawl_universal_board
from lemmy import crawl_lemmy_board
from bbc import crawl_bbc_board, detect_bbc_url_and_extract_info

# 코어 모듈 import
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

# ==================== 개별 크롤러 래퍼 함수들 ====================
async def fetch_posts_with_cancel_check(*args, crawl_id=None, **kwargs):
   if crawl_id and crawl_manager.is_cancelled(crawl_id):
       raise asyncio.CancelledError("크롤링 취소됨")
   kwargs.pop('crawl_id', None)
   return await fetch_posts(*args, **kwargs)

async def crawl_lemmy_board_with_cancel_check(*args, crawl_id=None, **kwargs):
   if crawl_id and crawl_manager.is_cancelled(crawl_id):
       raise asyncio.CancelledError("크롤링 취소됨")
   kwargs.pop('crawl_id', None)
   
   # 매개변수 매핑
   if 'start' in kwargs:
       kwargs['start_index'] = kwargs.pop('start')
   if 'end' in kwargs:
       kwargs['end_index'] = kwargs.pop('end')
   kwargs.setdefault('enforce_date_limit', False)
   
   return await crawl_lemmy_board(*args, **kwargs)

async def crawl_dcinside_board_with_cancel_check(*args, crawl_id=None, **kwargs):
   if crawl_id and crawl_manager.is_cancelled(crawl_id):
       raise asyncio.CancelledError("크롤링 취소됨")
   kwargs.pop('crawl_id', None)
   return await crawl_dcinside_board(*args, **kwargs)

async def crawl_blind_board_with_cancel_check(*args, crawl_id=None, **kwargs):
   if crawl_id and crawl_manager.is_cancelled(crawl_id):
       raise asyncio.CancelledError("크롤링 취소됨")
   kwargs.pop('crawl_id', None)
   return await crawl_blind_board(*args, **kwargs)

async def crawl_bbc_board_with_cancel_check(board_url: str, crawl_id=None, **kwargs):
   if crawl_id and crawl_manager.is_cancelled(crawl_id):
       raise asyncio.CancelledError("크롤링 취소됨")
   return await crawl_bbc_board(board_url=board_url, **kwargs)

async def crawl_universal_board_with_cancel_check(*args, crawl_id=None, **kwargs):
   if crawl_id and crawl_manager.is_cancelled(crawl_id):
       raise asyncio.CancelledError("크롤링 취소됨")
   kwargs.pop('crawl_id', None)
   return await crawl_universal_board(*args, **kwargs)

# ==================== 통합 크롤링 엔드포인트 ====================
@app.websocket("/ws/crawl")
async def unified_crawl_endpoint(websocket: WebSocket):
   """통합 크롤링 WebSocket 엔드포인트"""
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
       sort = config.get("sort", "recent")
       start_index = config.get("start", 1)
       end_index = config.get("end", 20)
       min_views = config.get("min_views", 0)
       min_likes = config.get("min_likes", 0)
       min_comments = config.get("min_comments", 0)
       time_filter = config.get("time_filter", "day")
       start_date_input = config.get("start_date")
       end_date_input = config.get("end_date")
       translate = config.get("translate", False)
       target_languages = config.get("target_languages", [])
       
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
           time_filter, start_date_input, end_date_input
       )
       
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

       # 크롤링 설정
       crawl_config = {
           'sort': sort,
           'start': start_index,
           'end': end_index,
           'min_views': min_views,
           'min_likes': min_likes,
           'min_comments': min_comments,
           'time_filter': time_filter,
           'start_date': actual_start_date,
           'end_date': actual_end_date,
           'crawl_id': crawl_id
       }

       # 사이트별 크롤링 실행
       raw_posts = []
       
       if detected_site == 'reddit':
           raw_posts = await fetch_posts_with_cancel_check(board_identifier, **crawl_config)
       elif detected_site == 'lemmy':
           raw_posts = await crawl_lemmy_board_with_cancel_check(board_identifier, **crawl_config)
       elif detected_site == 'dcinside':
           raw_posts = await crawl_dcinside_board_with_cancel_check(board_identifier, **crawl_config)
       elif detected_site == 'blind':
           raw_posts = await crawl_blind_board_with_cancel_check(board_identifier, **crawl_config)
       elif detected_site == 'bbc':
           raw_posts = await crawl_bbc_board_with_cancel_check(board_identifier, **crawl_config)
       elif detected_site == 'universal':
           raw_posts = await crawl_universal_board_with_cancel_check(input_data, **crawl_config)
       else:
           await ProgressManager.send_error(websocket, "unsupported_site", site=detected_site)
           return

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
           start=start_index,
           end=start_index + len(results) - 1 if results else start_index
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
           'end_date': actual_end_date
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
   if site == "bbc":
       bbc_detection = detect_bbc_url_and_extract_info(keyword)
       if bbc_detection["is_bbc"]:
           return {
               "matches": [bbc_detection["board_name"]],
               "detected_site": "bbc",
               "auto_detected": True
           }
   
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
           "metadata": raw_data
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
   return {"status": "healthy", "message": "PickPost API is running"}

@app.get("/")
def root():
   return {
       "message": "PickPost API Server", 
       "status": "running",
       "version": "2.0.0",
       "docs": "/docs",
       "unified_endpoint": "/ws/crawl",
       "progress_system": "localized"
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

# ==================== 서버 시작 ====================
if __name__ == "__main__":
   import uvicorn
   logger.info("🚀 PickPost v2.0 서버 시작 (언어팩 연동)")
   uvicorn.run(app, host="0.0.0.0", port=PORT)
    
