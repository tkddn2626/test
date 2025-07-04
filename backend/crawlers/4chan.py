import requests
import re
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import asyncio
import logging
from urllib.parse import urlparse, quote
import time
from dataclasses import dataclass
import hashlib

# 🔥 언어팩 시스템 import 추가
from core.messages import create_localized_message

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ================================
# 🔥 4chan 설정 및 상수
# ================================

# 4chan API 설정
FOURCHAN_CONFIG = {
    'api_timeout': 15,
    'max_pages': 10,
    'rate_limit_delay': 1.0,
    'user_agent': '4chanCrawler/1.0 (Image Board Crawler)',
    'cache_ttl': 300,
    'max_threads_per_page': 15,
    'max_replies_per_thread': 5
}

# 4chan API 엔드포인트
FOURCHAN_API_ENDPOINTS = {
    'catalog': 'https://a.4cdn.org/{board}/catalog.json',
    'threads': 'https://a.4cdn.org/{board}/threads.json',
    'thread': 'https://a.4cdn.org/{board}/thread/{thread_id}.json',
    'boards': 'https://a.4cdn.org/boards.json'
}

# 4chan 이미지/썸네일 URL
FOURCHAN_IMAGE_URLS = {
    'thumbnail': 'https://i.4cdn.org/{board}/{tim}s.jpg',
    'image': 'https://i.4cdn.org/{board}/{tim}{ext}',
    'thread_url': 'https://boards.4chan.org/{board}/thread/{no}',
    'board_url': 'https://boards.4chan.org/{board}/'
}

# 주요 4chan 게시판 정보
FOURCHAN_BOARDS = {
    # 기술/프로그래밍
    'g': {'name': 'Technology', 'description': '기술 게시판', 'nsfw': False},
    'sci': {'name': 'Science & Math', 'description': '과학/수학', 'nsfw': False},
    'diy': {'name': 'Do It Yourself', 'description': 'DIY 프로젝트', 'nsfw': False},
    
    # 취미/관심사
    'v': {'name': 'Video Games', 'description': '비디오 게임', 'nsfw': False},
    'vg': {'name': 'Video Game Generals', 'description': '게임 일반', 'nsfw': False},
    'a': {'name': 'Anime & Manga', 'description': '애니메이션/만화', 'nsfw': False},
    'co': {'name': 'Comics & Cartoons', 'description': '만화/카툰', 'nsfw': False},
    'mu': {'name': 'Music', 'description': '음악', 'nsfw': False},
    'tv': {'name': 'Television & Film', 'description': 'TV/영화', 'nsfw': False},
    'lit': {'name': 'Literature', 'description': '문학', 'nsfw': False},
    'his': {'name': 'History & Humanities', 'description': '역사/인문학', 'nsfw': False},
    
    # 창작/예술
    'ic': {'name': 'Artwork/Critique', 'description': '예술 작품/비평', 'nsfw': False},
    'wg': {'name': 'Wallpapers/General', 'description': '배경화면/일반', 'nsfw': False},
    'w': {'name': 'Anime/Wallpapers', 'description': '애니메이션 배경화면', 'nsfw': False},
    
    # 라이프스타일
    'fit': {'name': 'Fitness', 'description': '피트니스', 'nsfw': False},
    'ck': {'name': 'Food & Cooking', 'description': '음식/요리', 'nsfw': False},
    'fa': {'name': 'Fashion', 'description': '패션', 'nsfw': False},
    'sp': {'name': 'Sports', 'description': '스포츠', 'nsfw': False},
    'out': {'name': 'Outdoors', 'description': '아웃도어', 'nsfw': False},
    
    # 기타
    'b': {'name': 'Random', 'description': '랜덤 (NSFW)', 'nsfw': True},
    'pol': {'name': 'Politically Incorrect', 'description': '정치 (논란의 여지)', 'nsfw': True},
    'r9k': {'name': 'ROBOT9001', 'description': '로봇', 'nsfw': True},
    'biz': {'name': 'Business & Finance', 'description': '비즈니스/금융', 'nsfw': False},
    'int': {'name': 'International', 'description': '국제', 'nsfw': False},
    'jp': {'name': 'Otaku Culture', 'description': '오타쿠 문화', 'nsfw': False},
    'k': {'name': 'Weapons', 'description': '무기', 'nsfw': False},
    'o': {'name': 'Auto', 'description': '자동차', 'nsfw': False},
    'p': {'name': 'Photography', 'description': '사진', 'nsfw': False},
    'toy': {'name': 'Toys', 'description': '장난감', 'nsfw': False},
    'trv': {'name': 'Travel', 'description': '여행', 'nsfw': False},
    'x': {'name': 'Paranormal', 'description': '초자연현상', 'nsfw': False}
}

# 4chan URL 패턴 (lemmy.py 스타일)
FOURCHAN_URL_PATTERNS = [
    r'^(?:https?://)?(?:www\.)?boards\.4chan\.org/([a-z0-9]+)/?$',  # 게시판
    r'^(?:https?://)?(?:www\.)?boards\.4chan\.org/([a-z0-9]+)/thread/(\d+)/?',  # 스레드
    r'^(?:https?://)?(?:www\.)?boards\.4chan\.org/([a-z0-9]+)/catalog$',  # 카탈로그
    r'^(?:https?://)?(?:www\.)?4chan\.org/([a-z0-9]+)/?$',  # 4chan.org
    r'^([a-z0-9]+)$'  # 게시판 이름만
]

# 컴파일된 정규표현식
_compiled_4chan_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in FOURCHAN_URL_PATTERNS]

# ================================
# 🔥 4chan 데이터 클래스
# ================================

@dataclass
class FourchanPost:
    """4chan 게시물 정보"""
    no: int
    name: str = "Anonymous"
    sub: str = ""  # 제목
    com: str = ""  # 댓글 내용
    filename: str = ""
    ext: str = ""
    tim: str = ""  # 타임스탬프 (이미지 파일명)
    time: int = 0
    replies: int = 0
    images: int = 0
    bumplimit: int = 0
    imagelimit: int = 0
    semantic_url: str = ""
    w: int = 0  # 이미지 너비
    h: int = 0  # 이미지 높이
    tn_w: int = 0  # 썸네일 너비
    tn_h: int = 0  # 썸네일 높이
    fsize: int = 0  # 파일 크기
    md5: str = ""
    resto: int = 0  # 답글 대상 (0이면 OP)
    sticky: int = 0
    closed: int = 0
    archived: int = 0
    
@dataclass 
class FourchanBoard:
    """4chan 게시판 정보"""
    board: str
    title: str
    ws_board: int = 0
    per_page: int = 15
    pages: int = 10
    max_filesize: int = 0
    max_webm_filesize: int = 0
    max_comment_chars: int = 2000
    max_webm_duration: int = 0
    bump_limit: int = 300
    image_limit: int = 150
    cooldowns: dict = None
    meta_description: str = ""
    spoilers: int = 0
    custom_spoilers: int = 0
    is_archived: int = 0
    troll_flags: int = 0
    country_flags: int = 0
    user_ids: int = 0
    oekaki: int = 0
    sjis_tags: int = 0
    code_tags: int = 0
    math_tags: int = 0
    text_only: int = 0
    forced_anon: int = 0
    webm_audio: int = 0
    require_subject: int = 0
    min_image_width: int = 0
    min_image_height: int = 0

# ================================
# 🔥 4chan URL 파서
# ================================

class FourchanURLParser:
    """4chan URL 파싱 및 정규화 (lemmy.py 스타일)"""
    
    @staticmethod
    def parse_board_input(board_input: str) -> Tuple[str, str, str]:
        """
        4chan 입력을 분석하여 URL, 게시판명, 스레드ID 반환
        반환: (url, board_name, thread_id)
        """
        board_input = board_input.strip()
        
        # 1. 전체 URL인 경우
        if board_input.startswith('http'):
            return FourchanURLParser._parse_full_url(board_input)
        
        # 2. 게시판명만 있는 경우 (예: "g", "v", "pol")
        if re.match(r'^[a-z0-9]+$', board_input, re.IGNORECASE):
            board_name = board_input.lower()
            if board_name in FOURCHAN_BOARDS:
                url = f"https://boards.4chan.org/{board_name}/"
                return url, board_name, ""
            else:
                # 알려지지 않은 게시판이지만 시도
                url = f"https://boards.4chan.org/{board_name}/"
                return url, board_name, ""
        
        # 3. 기타 형태들 시도
        for pattern in _compiled_4chan_patterns:
            match = pattern.match(board_input)
            if match:
                groups = match.groups()
                if len(groups) >= 1:
                    board_name = groups[0].lower()
                    thread_id = groups[1] if len(groups) > 1 else ""
                    
                    if thread_id:
                        url = f"https://boards.4chan.org/{board_name}/thread/{thread_id}"
                    else:
                        url = f"https://boards.4chan.org/{board_name}/"
                    
                    return url, board_name, thread_id
        
        # 기본값
        return board_input, "", ""
    
    @staticmethod
    def _parse_full_url(url: str) -> Tuple[str, str, str]:
        """전체 URL 파싱"""
        parsed = urlparse(url)
        path = parsed.path.strip('/')
        
        # /board/thread/id 형태
        thread_match = re.match(r'([a-z0-9]+)/thread/(\d+)', path)
        if thread_match:
            board_name, thread_id = thread_match.groups()
            return url, board_name.lower(), thread_id
        
        # /board 형태
        board_match = re.match(r'([a-z0-9]+)/?', path)
        if board_match:
            board_name = board_match.group(1)
            return url, board_name.lower(), ""
        
        return url, "", ""
    
    @staticmethod
    def is_4chan_url(url: str) -> bool:
        """4chan URL인지 확인"""
        if not url:
            return False
            
        # 도메인 확인
        if any(domain in url.lower() for domain in ['4chan.org', 'boards.4chan.org', '4channel.org']):
            return True
        
        # 패턴 확인
        for pattern in _compiled_4chan_patterns:
            if pattern.match(url):
                return True
        
        return False

# ================================
# 🔥 4chan 조건 검사기
# ================================

class FourchanConditionChecker:
    """4chan 전용 조건 검사기"""
    
    def __init__(self, min_views: int = 0, min_likes: int = 0, min_comments: int = 0,
                 start_date: str = None, end_date: str = None, include_media: bool = True,
                 include_nsfw: bool = True):
        self.min_views = min_views  # 4chan에서는 replies로 사용
        self.min_likes = min_likes  # 4chan에서는 사용하지 않음
        self.min_comments = min_comments  # replies
        self.start_dt = self._parse_date(start_date)
        self.end_dt = self._parse_date(end_date)
        self.include_media = include_media
        self.include_nsfw = include_nsfw
        
        if self.end_dt:
            self.end_dt = self.end_dt.replace(hour=23, minute=59, second=59)
    
    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        if not date_str:
            return None
        try:
            return datetime.strptime(date_str, '%Y-%m-%d')
        except Exception:
            return None
    
    def check_conditions(self, post: Dict) -> Tuple[bool, str]:
        """게시물 조건 검사"""
        
        # 미디어 필터
        if not self.include_media and post.get('파일명'):
            return False, "미디어 필터링"
        
        # NSFW 필터
        board = post.get('게시판', '')
        if not self.include_nsfw and FOURCHAN_BOARDS.get(board, {}).get('nsfw', False):
            return False, "NSFW 필터링"
        
        # 최소 댓글수 (replies)
        if post.get('댓글수', 0) < self.min_comments:
            return False, f"최소 댓글수 {self.min_comments}개 미만"
        
        # 날짜 검사
        if self.start_dt and self.end_dt:
            post_date = self._extract_post_date(post)
            if post_date:
                if not (self.start_dt <= post_date <= self.end_dt):
                    return False, "날짜 범위 벗어남"
        
        return True, "통과"
    
    def _extract_post_date(self, post: Dict) -> Optional[datetime]:
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

# ================================
# 🔥 4chan API 클라이언트
# ================================

class FourchanAPIClient:
    """4chan API 클라이언트"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': FOURCHAN_CONFIG['user_agent']
        })
        self.rate_limiter = {}
        self.cache = {}
    
    def _apply_rate_limit(self, board: str):
        """게시판별 레이트 리미터"""
        now = time.time()
        if board in self.rate_limiter:
            last_request = self.rate_limiter[board]
            elapsed = now - last_request
            if elapsed < FOURCHAN_CONFIG['rate_limit_delay']:
                time.sleep(FOURCHAN_CONFIG['rate_limit_delay'] - elapsed)
        
        self.rate_limiter[board] = time.time()
    
    def get_boards_list(self) -> List[Dict]:
        """모든 게시판 목록 가져오기"""
        try:
            url = FOURCHAN_API_ENDPOINTS['boards']
            response = self.session.get(url, timeout=FOURCHAN_CONFIG['api_timeout'])
            response.raise_for_status()
            
            data = response.json()
            return data.get('boards', [])
            
        except Exception as e:
            logger.error(f"게시판 목록 조회 실패: {e}")
            return []
    
    def get_catalog(self, board: str) -> List[Dict]:
        """게시판 카탈로그 가져오기 (모든 스레드 요약)"""
        try:
            self._apply_rate_limit(board)
            
            # 캐시 확인
            cache_key = f"catalog_{board}"
            if cache_key in self.cache:
                cached_data, timestamp = self.cache[cache_key]
                if time.time() - timestamp < FOURCHAN_CONFIG['cache_ttl']:
                    return cached_data
            
            url = FOURCHAN_API_ENDPOINTS['catalog'].format(board=board)
            response = self.session.get(url, timeout=FOURCHAN_CONFIG['api_timeout'])
            response.raise_for_status()
            
            data = response.json()
            
            # 캐시 저장
            self.cache[cache_key] = (data, time.time())
            
            return data
            
        except Exception as e:
            logger.error(f"카탈로그 조회 실패 ({board}): {e}")
            return []
    
    def get_thread(self, board: str, thread_id: str) -> Dict:
        """특정 스레드 상세 정보 가져오기"""
        try:
            self._apply_rate_limit(board)
            
            url = FOURCHAN_API_ENDPOINTS['thread'].format(board=board, thread_id=thread_id)
            response = self.session.get(url, timeout=FOURCHAN_CONFIG['api_timeout'])
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            logger.error(f"스레드 조회 실패 ({board}/{thread_id}): {e}")
            return {}
    
    def get_threads_list(self, board: str) -> List[Dict]:
        """게시판의 모든 스레드 목록 가져오기"""
        try:
            self._apply_rate_limit(board)
            
            url = FOURCHAN_API_ENDPOINTS['threads'].format(board=board)
            response = self.session.get(url, timeout=FOURCHAN_CONFIG['api_timeout'])
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            logger.error(f"스레드 목록 조회 실패 ({board}): {e}")
            return []

# ================================
# 🔥 4chan 크롤러
# ================================

class FourchanCrawler:
    """4chan 전용 크롤러"""
    
    def __init__(self):
        self.api_client = FourchanAPIClient()
        self.url_parser = FourchanURLParser()
    
    async def crawl_4chan_board(self, board_input: str, limit: int = 50, sort: str = "recent",
                               min_views: int = 0, min_likes: int = 0, min_comments: int = 0,
                               start_date: str = None, end_date: str = None, 
                               include_media: bool = True, include_nsfw: bool = True,
                               time_filter: str = None,
                               websocket=None, start_index: int = 1, end_index: int = 20, 
                               user_lang: str = "en") -> List[Dict]:
        """4chan 게시판 크롤링"""
        
        try:
            logger.info(f"4chan 크롤링 시작: {board_input}")
            
            # URL 파싱
            url, board_name, thread_id = self.url_parser.parse_board_input(board_input)
            
            if not board_name:
                raise Exception(f"올바르지 않은 4chan 게시판: {board_input}\n예시: g, v, pol, https://boards.4chan.org/g/")
            
            # 게시판 정보 확인
            board_info = FOURCHAN_BOARDS.get(board_name, {
                'name': board_name.upper(),
                'description': f'/{board_name}/ 게시판',
                'nsfw': False
            })
            
            if websocket:
                # 🔥 언어팩 사용하여 메시지 생성
                message = create_localized_message(
                    progress=20,
                    status_key="crawlingProgress.site_connecting",
                    lang=user_lang,
                    status_data={"site": "4chan"}
                )
                await websocket.send_json(message)
            
            # 조건 검사기 설정
            condition_checker = FourchanConditionChecker(
                min_views, min_likes, min_comments, start_date, end_date, 
                include_media, include_nsfw
            )
            
            posts = []
            
            # 특정 스레드 크롤링
            if thread_id:
                posts = await self._crawl_single_thread(board_name, thread_id, condition_checker, websocket, user_lang)
            else:
                # 게시판 전체 크롤링
                posts = await self._crawl_board_catalog(board_name, limit, sort, condition_checker, websocket, user_lang)
            
            if not posts:
                # 🔥 언어팩을 사용한 에러 메시지는 예외로 던져서 상위에서 처리하도록 함
                error_msg = f"""
4chan /{board_name}/ 게시판에서 게시물을 찾을 수 없습니다.

가능한 원인:
1. 게시판에 게시물이 없음
2. 설정한 조건이 너무 까다로움
3. 게시판이 존재하지 않음

시도해볼 수 있는 게시판:
• /g/ - Technology
• /v/ - Video Games  
• /a/ - Anime & Manga
• /mu/ - Music
• /fit/ - Fitness
                """
                raise Exception(error_msg.strip())
            
            # 범위 적용
            if posts and len(posts) >= end_index:
                posts = posts[start_index-1:end_index]
                
                # 번호 재부여
                for idx, post in enumerate(posts):
                    post['번호'] = start_index + idx
            
            logger.info(f"4chan 크롤링 완료: {len(posts)}개 게시물")
            return posts
            
        except Exception as e:
            logger.error(f"4chan 크롤링 오류: {e}")
            raise
    
    async def _crawl_board_catalog(self, board_name: str, limit: int, sort: str, 
                                  condition_checker: FourchanConditionChecker, websocket=None, user_lang: str = "en") -> List[Dict]:
        """게시판 카탈로그 크롤링"""
        
        if websocket:
            # 🔥 언어팩 사용하여 카탈로그 분석 메시지
            message = create_localized_message(
                progress=40,
                status_key="crawlingProgress.posts_collecting",
                lang=user_lang,
                status_data={"site": "4chan"}
            )
            await websocket.send_json(message)
        
        try:
            catalog_data = self.api_client.get_catalog(board_name)
            
            if not catalog_data:
                return []
            
            posts = []
            processed_count = 0
            
            # 카탈로그의 각 페이지 처리
            for page_idx, page in enumerate(catalog_data):
                if processed_count >= limit:
                    break
                
                threads = page.get('threads', [])
                
                for thread_idx, thread in enumerate(threads):
                    if processed_count >= limit:
                        break
                    
                    # 스레드를 게시물로 변환
                    post_data = self._convert_thread_to_post(thread, board_name, processed_count + 1)
                    
                    if post_data:
                        # 조건 검사
                        passes, reason = condition_checker.check_conditions(post_data)
                        if passes:
                            posts.append(post_data)
                            processed_count += 1
                            
                            if websocket and processed_count % 5 == 0:
                                # 🔥 언어팩 사용하여 진행 상황 메시지
                                message = create_localized_message(
                                    progress=40 + int((processed_count / limit) * 40),
                                    status_key="crawlingProgress.page_collecting",
                                    lang=user_lang,
                                    status_data={"page": page_idx + 1}
                                )
                                await websocket.send_json(message)
            
            # 정렬 적용
            sorted_posts = self._apply_4chan_sorting(posts, sort)
            
            return sorted_posts[:limit]
            
        except Exception as e:
            logger.error(f"카탈로그 크롤링 오류: {e}")
            return []
    
    async def _crawl_single_thread(self, board_name: str, thread_id: str, 
                                  condition_checker: FourchanConditionChecker, websocket=None, user_lang: str = "en") -> List[Dict]:
        """단일 스레드 크롤링"""
        
        if websocket:
            message = create_localized_message(
                progress=40,
                status_key="crawlingProgress.content_parsing",
                lang=user_lang
            )
            await websocket.send_json(message)
        
        try:
            thread_data = self.api_client.get_thread(board_name, thread_id)
            
            if not thread_data or 'posts' not in thread_data:
                return []
            
            posts = []
            thread_posts = thread_data['posts']
            
            for idx, post in enumerate(thread_posts[:FOURCHAN_CONFIG['max_replies_per_thread'] + 1]):
                post_data = self._convert_post_to_dict(post, board_name, idx + 1, thread_id)
                
                if post_data:
                    # 조건 검사
                    passes, reason = condition_checker.check_conditions(post_data)
                    if passes:
                        posts.append(post_data)
            
            return posts
            
        except Exception as e:
            logger.error(f"스레드 크롤링 오류: {e}")
            return []
    
    def _convert_thread_to_post(self, thread: Dict, board_name: str, post_number: int) -> Optional[Dict]:
        """스레드 데이터를 게시물 형식으로 변환"""
        try:
            # 기본 정보
            thread_no = thread.get('no', 0)
            subject = thread.get('sub', '')
            comment = thread.get('com', '')
            
            # 파일 정보
            filename = thread.get('filename', '')
            ext = thread.get('ext', '')
            tim = thread.get('tim', '')
            
            # 통계 정보
            replies = thread.get('replies', 0)
            images = thread.get('images', 0)
            
            # 날짜 정보
            timestamp = thread.get('time', 0)
            
            # 이미지 정보
            width = thread.get('w', 0)
            height = thread.get('h', 0)
            filesize = thread.get('fsize', 0)
            
            # 제목 생성 (subject가 없으면 날짜 또는 파일명 사용)
            if subject:
                title = subject
            elif filename:
                title = f"{filename}{ext}"
            else:
                # 업로드 날짜를 제목으로 사용
                if timestamp:
                    date_obj = datetime.fromtimestamp(timestamp)
                    title = date_obj.strftime('%Y.%m.%d %H:%M')
                else:
                    title = f"#{thread_no}"
            
            # 🔥 이미지 URL 생성 (원본)
            image_url = ""
            if tim and ext and board_name:
                image_url = FOURCHAN_IMAGE_URLS['image'].format(
                    board=board_name, tim=tim, ext=ext
                )
            
            # 🔥 썸네일 URL은 원본 이미지와 동일하게 설정
            thumbnail_url = image_url
            
            # 스레드 URL
            thread_url = FOURCHAN_IMAGE_URLS['thread_url'].format(
                board=board_name, no=thread_no
            )
            
            # HTML 태그 제거 (4chan 댓글에서)
            clean_comment = self._clean_html_content(comment)
            
            return {
                "번호": post_number,
                "원제목": title,
                "번역제목": None,
                "링크": thread_url,
                "원문URL": thread_url,
                "썸네일 URL": thumbnail_url,
                "이미지 URL": image_url,
                "본문": clean_comment[:300] + "..." if len(clean_comment) > 300 else clean_comment,
                "조회수": replies,  # 4chan에서는 replies를 조회수로 사용
                "추천수": 0,  # 4chan에는 추천 시스템 없음
                "댓글수": replies,
                "이미지수": images,
                "작성일": self._format_4chan_date(timestamp),
                "작성자": "Anonymous",
                "게시판": board_name,
                "스레드번호": thread_no,
                "파일명": filename,
                "파일확장자": ext,
                "파일크기": filesize,
                "이미지크기": f"{width}x{height}" if width and height else "",
                "타임스탬프": tim,
                "nsfw": FOURCHAN_BOARDS.get(board_name, {}).get('nsfw', False),
                "크롤링방식": "4chan-Catalog-API",
                "플랫폼": "4chan"
            }
            
        except Exception as e:
            logger.debug(f"스레드 변환 오류: {e}")
            return None
    
    def _convert_post_to_dict(self, post: Dict, board_name: str, post_number: int, thread_id: str) -> Optional[Dict]:
        """개별 게시물 데이터를 딕셔너리로 변환"""
        try:
            # 기본 정보
            post_no = post.get('no', 0)
            name = post.get('name', 'Anonymous')
            subject = post.get('sub', '')
            comment = post.get('com', '')
            
            # 파일 정보
            filename = post.get('filename', '')
            ext = post.get('ext', '')
            tim = post.get('tim', '')
            
            # 날짜 정보
            timestamp = post.get('time', 0)
            
            # 이미지 정보
            width = post.get('w', 0)
            height = post.get('h', 0)
            filesize = post.get('fsize', 0)
            
            # 제목 생성
            if subject:
                title = subject
            elif filename:
                title = f"{filename}{ext}"
            elif post_number == 1:
                title = f"스레드 #{thread_id}"
            else:
                title = f"답글 #{post_no}"
            
            # 🔥 이미지 URL 생성 (원본)
            image_url = ""
            if tim and ext and board_name:
                image_url = FOURCHAN_IMAGE_URLS['image'].format(
                    board=board_name, tim=tim, ext=ext
                )
            
            # 🔥 썸네일 URL은 원본 이미지와 동일하게 설정
            thumbnail_url = image_url
            
            # 게시물 URL
            post_url = f"https://boards.4chan.org/{board_name}/thread/{thread_id}#{post_no}"
            
            # HTML 태그 제거
            clean_comment = self._clean_html_content(comment)
            
            return {
                "번호": post_number,
                "원제목": title,
                "번역제목": None,
                "링크": post_url,
                "원문URL": post_url,
                "썸네일 URL": thumbnail_url,
                "이미지 URL": image_url,
                "본문": clean_comment[:300] + "..." if len(clean_comment) > 300 else clean_comment,
                "조회수": 0,  # 개별 게시물에는 조회수 없음
                "추천수": 0,
                "댓글수": 0,
                "작성일": self._format_4chan_date(timestamp),
                "작성자": name,
                "게시판": board_name,
                "스레드번호": thread_id,
                "게시물번호": post_no,
                "파일명": filename,
                "파일확장자": ext,
                "파일크기": filesize,
                "이미지크기": f"{width}x{height}" if width and height else "",
                "타임스탬프": tim,
                "OP여부": post_number == 1,
                "nsfw": FOURCHAN_BOARDS.get(board_name, {}).get('nsfw', False),
                "크롤링방식": "4chan-Thread-API",
                "플랫폼": "4chan"
            }
            
        except Exception as e:
            logger.debug(f"게시물 변환 오류: {e}")
            return None
    
    def _clean_html_content(self, html_content: str) -> str:
        """4chan HTML 태그 제거 및 정리"""
        if not html_content:
            return ""
        
        # 기본 HTML 태그 제거
        import re
        
        # 4chan 특화 정리
        content = html_content
        
        # <br> 태그를 줄바꿈으로
        content = re.sub(r'<br\s*/?>', '\n', content)
        
        # 인용 처리 (>>번호)
        content = re.sub(r'<a[^>]*class="quotelink"[^>]*>&gt;&gt;(\d+)</a>', r'>>\1', content)
        
        # 일반 링크 처리
        content = re.sub(r'<a[^>]*href="([^"]*)"[^>]*>([^<]*)</a>', r'\2 (\1)', content)
        
        # 굵은 글씨 처리
        content = re.sub(r'<b>(.*?)</b>', r'**\1**', content)
        content = re.sub(r'<strong>(.*?)</strong>', r'**\1**', content)
        
        # 기울임 처리
        content = re.sub(r'<i>(.*?)</i>', r'*\1*', content)
        content = re.sub(r'<em>(.*?)</em>', r'*\1*', content)
        
        # 나머지 HTML 태그 제거
        content = re.sub(r'<[^>]+>', '', content)
        
        # HTML 엔티티 디코딩
        import html
        content = html.unescape(content)
        
        # 여러 줄바꿈을 하나로
        content = re.sub(r'\n\s*\n', '\n', content)
        
        return content.strip()
    
    def _format_4chan_date(self, timestamp: int) -> str:
        """4chan 타임스탬프를 날짜 문자열로 변환"""
        if not timestamp:
            return datetime.now().strftime('%Y.%m.%d %H:%M')
        
        try:
            date_obj = datetime.fromtimestamp(timestamp)
            return date_obj.strftime('%Y.%m.%d %H:%M')
        except Exception:
            return datetime.now().strftime('%Y.%m.%d %H:%M')
    
    def _apply_4chan_sorting(self, posts: List[Dict], sort: str) -> List[Dict]:
        """4chan 특화 정렬"""
        if not posts:
            return posts
        
        try:
            sort_lower = sort.lower()
            
            if sort_lower in ["recent", "new", "latest"]:
                # 최신순 (타임스탬프 기준)
                return sorted(posts, key=lambda x: x.get('타임스탬프', ''), reverse=True)
            
            elif sort_lower in ["popular", "hot", "active"]:
                # 인기순 (답글수 기준)
                return sorted(posts, key=lambda x: x.get('댓글수', 0), reverse=True)
            
            elif sort_lower in ["images", "media"]:
                # 이미지가 있는 것 우선
                return sorted(posts, key=lambda x: (x.get('이미지수', 0), x.get('댓글수', 0)), reverse=True)
            
            elif sort_lower == "oldest":
                # 오래된 순
                return sorted(posts, key=lambda x: x.get('타임스탬프', ''), reverse=False)
            
            elif sort_lower == "replies":
                # 답글 많은 순
                return sorted(posts, key=lambda x: x.get('댓글수', 0), reverse=True)
            
            else:
                # 기본값: 최신순
                return sorted(posts, key=lambda x: x.get('타임스탬프', ''), reverse=True)
            
        except Exception as e:
            logger.error(f"정렬 오류: {e}")
            return posts

# ================================
# 🔥 검색 및 자동완성 기능
# ================================

class FourchanBoardSearcher:
    """4chan 게시판 검색 및 자동완성"""
    
    @staticmethod
    def search_boards(keyword: str) -> List[Dict]:
        """키워드로 게시판 검색"""
        keyword = keyword.lower().strip()
        matches = []
        
        for board_code, board_info in FOURCHAN_BOARDS.items():
            # 게시판 코드 매칭
            if keyword in board_code:
                matches.append({
                    'code': board_code,
                    'name': board_info['name'],
                    'description': board_info['description'],
                    'url': f"https://boards.4chan.org/{board_code}/",
                    'nsfw': board_info['nsfw'],
                    'match_type': 'code'
                })
            
            # 게시판 이름 매칭
            elif keyword in board_info['name'].lower():
                matches.append({
                    'code': board_code,
                    'name': board_info['name'],
                    'description': board_info['description'],
                    'url': f"https://boards.4chan.org/{board_code}/",
                    'nsfw': board_info['nsfw'],
                    'match_type': 'name'
                })
            
            # 설명 매칭
            elif keyword in board_info['description'].lower():
                matches.append({
                    'code': board_code,
                    'name': board_info['name'],
                    'description': board_info['description'],
                    'url': f"https://boards.4chan.org/{board_code}/",
                    'nsfw': board_info['nsfw'],
                    'match_type': 'description'
                })
        
        # 정렬: code 매칭 > name 매칭 > description 매칭
        priority = {'code': 0, 'name': 1, 'description': 2}
        matches.sort(key=lambda x: (priority[x['match_type']], x['code']))
        
        return matches[:15]  # 최대 15개
    
    @staticmethod
    def get_popular_boards() -> List[Dict]:
        """인기 게시판 목록"""
        popular_codes = ['g', 'v', 'a', 'mu', 'fit', 'ck', 'tv', 'pol', 'b', 'sci']
        
        popular_boards = []
        for code in popular_codes:
            if code in FOURCHAN_BOARDS:
                board_info = FOURCHAN_BOARDS[code]
                popular_boards.append({
                    'code': code,
                    'name': board_info['name'],
                    'description': board_info['description'],
                    'url': f"https://boards.4chan.org/{code}/",
                    'nsfw': board_info['nsfw']
                })
        
        return popular_boards
    
    @staticmethod
    def get_safe_boards() -> List[Dict]:
        """SFW(Safe for Work) 게시판만"""
        safe_boards = []
        
        for code, info in FOURCHAN_BOARDS.items():
            if not info.get('nsfw', False):
                safe_boards.append({
                    'code': code,
                    'name': info['name'],
                    'description': info['description'],
                    'url': f"https://boards.4chan.org/{code}/",
                    'nsfw': False
                })
        
        # 인기도순 정렬 (임의의 순서)
        priority_order = ['g', 'v', 'a', 'mu', 'sci', 'diy', 'fit', 'ck', 'tv', 'co', 'lit', 'his']
        
        def get_priority(board):
            try:
                return priority_order.index(board['code'])
            except ValueError:
                return 999
        
        safe_boards.sort(key=get_priority)
        return safe_boards

# ================================
# 🔥 메인 크롤링 함수
# ================================

async def crawl_4chan_board(board_input: str, limit: int = 50, sort: str = "recent",
                              min_views: int = 0, min_likes: int = 0, min_comments: int = 0,
                              start_date: str = None, end_date: str = None,
                              include_media: bool = True, include_nsfw: bool = True,
                              time_filter: str = None,
                              websocket=None, start_index: int = 1, end_index: int = 20, 
                              user_lang: str = "en") -> List[Dict]:
    """4chan 게시판 크롤링 메인 함수"""
    
    crawler = FourchanCrawler()
    
    try:
        logger.info(f"4chan 크롤링 시작: {board_input} (범위: {start_index}-{end_index})")
        
        # 크롤링 실행
        posts = await crawler.crawl_4chan_board(
            board_input=board_input,
            limit=max(end_index + 10, 50),  # 여유분 포함
            sort=sort,
            min_views=min_views,
            min_likes=min_likes,
            min_comments=min_comments,
            start_date=start_date,
            end_date=end_date,
            include_media=include_media,
            include_nsfw=include_nsfw,
            time_filter=time_filter,
            websocket=websocket,
            start_index=start_index,
            end_index=end_index,
            user_lang=user_lang
        )
        
        logger.info(f"4chan 크롤링 완료: {len(posts)}개 게시물")
        return posts
        
    except Exception as e:
        logger.error(f"4chan 크롤링 메인 함수 오류: {e}")
        raise

# ================================
# 🔥 유틸리티 함수들
# ================================

def detect_4chan_url_and_extract_info(url: str) -> Dict:
    """4chan URL 감지 및 정보 추출 (BBC 스타일)"""
    parser = FourchanURLParser()
    
    if parser.is_4chan_url(url):
        parsed_url, board_name, thread_id = parser.parse_board_input(url)
        
        board_info = FOURCHAN_BOARDS.get(board_name, {})
        
        return {
            "is_4chan": True,
            "board_name": board_name,
            "thread_id": thread_id,
            "board_title": board_info.get('name', board_name.upper()),
            "board_description": board_info.get('description', f'/{board_name}/ 게시판'),
            "nsfw": board_info.get('nsfw', False),
            "parsed_url": parsed_url,
            "input_type": "thread" if thread_id else "board"
        }
    
    return {"is_4chan": False}

def get_4chan_autocomplete_suggestions(keyword: str) -> List[str]:
    """4chan 자동완성 제안"""
    searcher = FourchanBoardSearcher()
    matches = searcher.search_boards(keyword)
    
    suggestions = []
    for match in matches:
        suggestions.append(f"/{match['code']}/ - {match['name']}")
    
    return suggestions[:10]

def is_4chan_board_safe(board_name: str) -> bool:
    """게시판이 SFW인지 확인"""
    board_info = FOURCHAN_BOARDS.get(board_name.lower(), {})
    return not board_info.get('nsfw', False)

# ================================
# 🔥 모듈 메타데이터
# ================================

# 모듈 정보 (동적 탐지를 위한 메타데이터)
DISPLAY_NAME = "4chan Crawler"
DESCRIPTION = "4chan 이미지보드 크롤러"
VERSION = "1.0.0"
SUPPORTED_DOMAINS = ["4chan.org", "boards.4chan.org", "4channel.org"]
KEYWORDS = ["4chan", "imageboard", "anonymous"]

# 모듈 로드 확인
logger.info("🔥 4chan 크롤러 v1.0 로드 완료")
logger.info(f"📊 지원 게시판: {len(FOURCHAN_BOARDS)}개")
logger.info(f"🎯 API 엔드포인트: {len(FOURCHAN_API_ENDPOINTS)}개")
logger.info(f"⚙️ 설정: {FOURCHAN_CONFIG['api_timeout']}s timeout, {FOURCHAN_CONFIG['cache_ttl']}s cache")
logger.info(f"🔍 URL 패턴: {len(FOURCHAN_URL_PATTERNS)}개 정규표현식")
logger.info(f"🖼️ 썸네일 지원: 자동 추출 및 표시")