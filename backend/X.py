import requests
import re
import json
import asyncio
import aiohttp
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from urllib.parse import urlparse, quote, urljoin
import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
import time
import base64
from functools import lru_cache
import hashlib
import random
import urllib.parse

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ================================
# 🔥 X(트위터) 설정 및 상수
# ================================

X_CONFIG = {
    'api_timeout': 15,
    'max_pages': 10,
    'max_concurrent': 2,
    'retry_count': 3,
    'retry_delay': 2.0,
    'rate_limit_delay': 1.5,
    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'cache_ttl': 300,
}

# X URL 패턴
X_URL_PATTERNS = {
    'profile': re.compile(r'(?:https?://)?(?:www\.)?(?:twitter\.com|x\.com)/([a-zA-Z0-9_]+)/?$'),
    'status': re.compile(r'(?:https?://)?(?:www\.)?(?:twitter\.com|x\.com)/[a-zA-Z0-9_]+/status/(\d+)'),
    'hashtag': re.compile(r'(?:https?://)?(?:www\.)?(?:twitter\.com|x\.com)/hashtag/([a-zA-Z0-9_]+)'),
    'search': re.compile(r'(?:https?://)?(?:www\.)?(?:twitter\.com|x\.com)/search\?q=(.+)'),
    'media': re.compile(r'(?:https?://)?(?:www\.)?(?:twitter\.com|x\.com)/([a-zA-Z0-9_]+)/media/?$'),
    'likes': re.compile(r'(?:https?://)?(?:www\.)?(?:twitter\.com|x\.com)/([a-zA-Z0-9_]+)/likes/?$'),
}

# X 정렬 매핑
X_SORT_MAPPING = {
    'recent': 'Latest',
    'popular': 'Top', 
    'top': 'Top',
    'latest': 'Latest',
    'hot': 'Top',
    'new': 'Latest',
    'trending': 'Top'
}

# ================================
# 🔥 데이터 클래스
# ================================

@dataclass
class XPost:
    """X 게시물 정보"""
    id: str
    text: str
    author: str
    author_username: str
    created_at: datetime
    retweet_count: int = 0
    like_count: int = 0
    reply_count: int = 0
    view_count: int = 0
    media_urls: List[str] = field(default_factory=list)
    media_types: List[str] = field(default_factory=list)
    thumbnail_url: str = ""
    is_retweet: bool = False
    is_reply: bool = False
    has_media: bool = False
    nsfw: bool = False
    url: str = ""
    hashtags: List[str] = field(default_factory=list)
    mentions: List[str] = field(default_factory=list)

@dataclass
class XUser:
    """X 사용자 정보"""
    username: str
    display_name: str
    description: str = ""
    followers_count: int = 0
    following_count: int = 0
    tweets_count: int = 0
    verified: bool = False
    profile_image_url: str = ""
    banner_url: str = ""

# ================================
# 🔥 X URL 감지 및 분석기
# ================================

class XUrlAnalyzer:
    """X URL 분석 및 감지"""
    
    @staticmethod
    def is_x_url(url: str) -> bool:
        """URL이 X(트위터) URL인지 확인"""
        if not url:
            return False
        
        url = url.lower().strip()
        return 'twitter.com' in url or 'x.com' in url
    
    @staticmethod
    def detect_x_url_and_type(url: str) -> Dict:
        """X URL 타입 감지 및 정보 추출"""
        if not XUrlAnalyzer.is_x_url(url):
            return {
                "is_x": False,
                "type": None,
                "normalized_url": url,
                "extracted_info": {},
                "auto_detected": False
            }
        
        # URL 정규화
        normalized_url = url.replace('twitter.com', 'x.com')
        if not normalized_url.startswith('http'):
            normalized_url = f"https://{normalized_url}"
        
        # 패턴 매칭
        for url_type, pattern in X_URL_PATTERNS.items():
            match = pattern.search(url)
            if match:
                extracted_info = {}
                
                if url_type == 'profile':
                    extracted_info = {
                        'username': match.group(1),
                        'display_name': f"@{match.group(1)}"
                    }
                elif url_type == 'status':
                    extracted_info = {
                        'tweet_id': match.group(1)
                    }
                elif url_type == 'hashtag':
                    extracted_info = {
                        'hashtag': match.group(1)
                    }
                elif url_type == 'search':
                    extracted_info = {
                        'query': match.group(1)
                    }
                elif url_type == 'media':
                    extracted_info = {
                        'username': match.group(1),
                        'filter': 'media'
                    }
                elif url_type == 'likes':
                    extracted_info = {
                        'username': match.group(1),
                        'filter': 'likes'
                    }
                
                return {
                    "is_x": True,
                    "type": url_type,
                    "normalized_url": normalized_url,
                    "extracted_info": extracted_info,
                    "auto_detected": True,
                    "board_name": XUrlAnalyzer._generate_board_name(url_type, extracted_info),
                    "description": XUrlAnalyzer._generate_description(url_type, extracted_info)
                }
        
        # 패턴 매칭 실패 시 기본 프로필로 처리
        return {
            "is_x": True,
            "type": "profile",
            "normalized_url": normalized_url,
            "extracted_info": {"username": "unknown"},
            "auto_detected": True,
            "board_name": "X Profile",
            "description": "X 프로필 또는 타임라인"
        }
    
    @staticmethod
    def _generate_board_name(url_type: str, info: Dict) -> str:
        """게시판 이름 생성"""
        type_names = {
            'profile': f"@{info.get('username', 'unknown')} 타임라인",
            'status': f"트윗 {info.get('tweet_id', 'unknown')}",
            'hashtag': f"#{info.get('hashtag', 'unknown')} 해시태그",
            'search': f"검색: {info.get('query', 'unknown')}",
            'media': f"@{info.get('username', 'unknown')} 미디어",
            'likes': f"@{info.get('username', 'unknown')} 좋아요"
        }
        return type_names.get(url_type, "X 콘텐츠")
    
    @staticmethod
    def _generate_description(url_type: str, info: Dict) -> str:
        """설명 생성"""
        descriptions = {
            'profile': f"{info.get('username')} 사용자의 최신 트윗",
            'status': f"특정 트윗과 관련 댓글",
            'hashtag': f"{info.get('hashtag')} 해시태그가 포함된 트윗",
            'search': f"'{info.get('query')}' 검색 결과",
            'media': f"{info.get('username')} 사용자의 미디어 트윗",
            'likes': f"{info.get('username')} 사용자가 좋아요한 트윗"
        }
        return descriptions.get(url_type, "X 콘텐츠")

# ================================
# 🔥 캐싱 시스템
# ================================

class XCache:
    """X 전용 캐싱 시스템"""
    
    def __init__(self, ttl: int = 300):
        self.cache = {}
        self.ttl = ttl
    
    def _generate_key(self, *args, **kwargs) -> str:
        """캐시 키 생성"""
        key_data = str(args) + str(sorted(kwargs.items()))
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def get(self, *args, **kwargs) -> Optional[any]:
        """캐시에서 데이터 조회"""
        key = self._generate_key(*args, **kwargs)
        if key in self.cache:
            data, timestamp = self.cache[key]
            if time.time() - timestamp < self.ttl:
                return data
            else:
                del self.cache[key]
        return None
    
    def set(self, data: any, *args, **kwargs):
        """캐시에 데이터 저장"""
        key = self._generate_key(*args, **kwargs)
        self.cache[key] = (data, time.time())
    
    def clear(self):
        """캐시 초기화"""
        self.cache.clear()

# ================================
# 🔥 조건 검사기
# ================================

class XConditionChecker:
    """X 전용 조건 검사기"""
    
    def __init__(self, min_views: int = 0, min_likes: int = 0, min_retweets: int = 0,
                 start_date: str = None, end_date: str = None, include_media: bool = True,
                 include_nsfw: bool = True):
        self.min_views = min_views
        self.min_likes = min_likes
        self.min_retweets = min_retweets
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
        # 메트릭 검사
        views = post.get('조회수', 0)
        likes = post.get('추천수', 0)
        retweets = post.get('리트윗수', 0)
        
        if views < self.min_views:
            return False, f"조회수 부족: {views} < {self.min_views}"
        if likes < self.min_likes:
            return False, f"추천수 부족: {likes} < {self.min_likes}"
        if retweets < self.min_retweets:
            return False, f"리트윗수 부족: {retweets} < {self.min_retweets}"
        
        # 미디어 필터
        has_media = post.get('미디어수', 0) > 0
        if not self.include_media and has_media:
            return False, "미디어 포함 게시물 제외"
        
        # NSFW 필터
        if not self.include_nsfw and post.get('nsfw', False):
            return False, "NSFW 콘텐츠 제외"
        
        # 날짜 검사
        if self.start_dt and self.end_dt:
            post_date = self._extract_post_date(post)
            if post_date:
                if not (self.start_dt <= post_date <= self.end_dt):
                    return False, f"날짜 범위 외"
        
        return True, "조건 만족"
    
    def _extract_post_date(self, post: Dict) -> Optional[datetime]:
        """게시물 날짜 추출"""
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
# 🔥 메인 크롤러 클래스
# ================================

class XCrawler:
    """X(트위터) 전용 크롤러"""
    
    def __init__(self):
        self.cache = XCache(ttl=X_CONFIG['cache_ttl'])
        self.session = None
        self.rate_limiter = {}
    
    async def __aenter__(self):
        """비동기 컨텍스트 매니저 진입"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=X_CONFIG['api_timeout']),
            headers={'User-Agent': X_CONFIG['user_agent']},
            connector=aiohttp.TCPConnector(limit=10, limit_per_host=5)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """비동기 컨텍스트 매니저 종료"""
        if self.session:
            await self.session.close()
    
    async def crawl_x_board(self, board_input: str, limit: int = 50, sort: str = "recent",
                           min_views: int = 0, min_likes: int = 0, min_retweets: int = 0,
                           time_filter: str = "day", start_date: str = None, end_date: str = None,
                           websocket=None, enforce_date_limit: bool = False,
                           start_index: int = 1, end_index: int = 20,
                           include_media: bool = True, include_nsfw: bool = True) -> List[Dict]:
        """메인 크롤링 함수"""
        
        try:
            logger.info(f"X 크롤링 시작: {board_input}")
            
            # URL 분석
            url_info = XUrlAnalyzer.detect_x_url_and_type(board_input)
            
            # 단순 사용자명으로 입력된 경우 처리
            if not url_info["is_x"]:
                if not board_input.startswith('http') and len(board_input.strip()) > 0:
                    username = board_input.strip().replace('@', '')
                    corrected_url = f"https://x.com/{username}"
                    url_info = XUrlAnalyzer.detect_x_url_and_type(corrected_url)
                    
                    if websocket:
                        await websocket.send_json({
                            "progress": 5,
                            "status": f"🔄 자동 보정: {board_input} → @{username}",
                            "details": "X 프로필 URL로 변환했습니다"
                        })
                else:
                    raise Exception(f"""❌ 올바른 X URL 또는 사용자명을 입력해주세요.

✅ 올바른 형식:
• elonmusk
• @elonmusk  
• https://x.com/elonmusk
• https://x.com/elonmusk/media

현재 입력: {board_input}""")
            
            if websocket:
                await websocket.send_json({
                    "progress": 10,
                    "status": f"🐦 X 크롤링: {url_info['board_name']}",
                    "details": f"타입: {url_info['type']}, 범위: {start_index}-{end_index}"
                })
            
            # 조건 검사기 생성
            condition_checker = XConditionChecker(
                min_views=min_views,
                min_likes=min_likes,
                min_retweets=min_retweets,
                start_date=start_date,
                end_date=end_date,
                include_media=include_media,
                include_nsfw=include_nsfw
            )
            
            # 크롤링 실행
            posts = await self._crawl_by_type(url_info, limit, sort, websocket, condition_checker)
            
            if not posts:
                error_msg = self._generate_no_posts_error(url_info, board_input)
                raise Exception(error_msg)
            
            # 조건 필터링 적용
            if min_views > 0 or min_likes > 0 or min_retweets > 0 or start_date or end_date:
                filtered_posts = []
                for post in posts:
                    is_valid, reason = condition_checker.check_conditions(post)
                    if is_valid:
                        filtered_posts.append(post)
                
                if websocket:
                    await websocket.send_json({
                        "progress": 80,
                        "status": f"🔍 조건 필터링: {len(posts)} → {len(filtered_posts)}개",
                        "details": f"최소 좋아요: {min_likes}, 최소 조회수: {min_views}"
                    })
                
                posts = filtered_posts
            
            # 범위 적용
            if start_index > 1 or end_index < len(posts):
                posts = posts[start_index-1:end_index]
            
            # 번호 재부여
            for idx, post in enumerate(posts):
                post['번호'] = start_index + idx
            
            if websocket:
                await websocket.send_json({
                    "progress": 95,
                    "status": f"✅ {len(posts)}개 트윗 수집 완료",
                    "details": f"범위: {start_index}-{start_index+len(posts)-1}"
                })
            
            return posts
            
        except Exception as e:
            logger.error(f"X 크롤링 오류: {e}")
            raise
    
    def _generate_no_posts_error(self, url_info: Dict, board_input: str) -> str:
        """게시물 없음 오류 메시지 생성"""
        
        url_type = url_info.get("type", "unknown")
        extracted_info = url_info.get("extracted_info", {})
        
        if url_type == "profile":
            username = extracted_info.get("username", board_input)
            return f"""❌ @{username} 계정에서 트윗을 찾을 수 없습니다.

🔍 가능한 원인:
• 계정이 비공개이거나 존재하지 않음
• 최근 트윗이 없음
• 설정한 조건이 너무 까다로움

💡 해결책:
1. 공개 계정으로 시도: @elonmusk, @tesla, @spacex
2. 조건을 완화: 최소 좋아요수 0으로 설정
3. 기간을 늘려보기
4. 미디어 필터 해제"""
            
        elif url_type == "media":
            username = extracted_info.get("username", board_input)
            return f"""❌ @{username} 계정의 미디어 트윗을 찾을 수 없습니다.

💡 미디어 트윗이 없을 수 있습니다:
1. 일반 타임라인으로 시도: {username}
2. 다른 계정 시도: elonmusk, tesla, spacex"""
            
        elif url_type == "hashtag":
            hashtag = extracted_info.get("hashtag", "unknown")
            return f"""❌ #{hashtag} 해시태그 트윗을 찾을 수 없습니다.

💡 해결책:
1. 인기 해시태그로 시도: #AI, #tech, #crypto
2. 조건을 완화해보세요"""
            
        else:
            return f"""❌ X에서 게시물을 찾을 수 없습니다.

💡 권장 해결책:
1. 인기 계정으로 테스트: elonmusk
2. 조건 완화 (최소 좋아요수 0)
3. 전체 기간으로 설정"""
    
    async def _crawl_by_type(self, url_info: Dict, limit: int, sort: str, 
                           websocket, condition_checker: XConditionChecker) -> List[Dict]:
        """URL 타입별 크롤링"""
        
        url_type = url_info["type"]
        extracted_info = url_info["extracted_info"]
        
        try:
            if url_type == "profile":
                return await self._crawl_user_timeline(
                    extracted_info.get("username", ""), limit, sort, websocket, condition_checker
                )
            elif url_type == "status":
                return await self._crawl_single_tweet(
                    extracted_info.get("tweet_id", ""), websocket, condition_checker
                )
            elif url_type == "hashtag":
                return await self._crawl_hashtag(
                    extracted_info.get("hashtag", ""), limit, sort, websocket, condition_checker
                )
            elif url_type == "media":
                return await self._crawl_user_media(
                    extracted_info.get("username", ""), limit, sort, websocket, condition_checker
                )
            elif url_type == "search":
                return await self._crawl_search(
                    extracted_info.get("query", ""), limit, sort, websocket, condition_checker
                )
            else:
                # 기본값: 사용자 타임라인
                return await self._crawl_user_timeline(
                    extracted_info.get("username", "unknown"), limit, sort, websocket, condition_checker
                )
                
        except Exception as e:
            logger.error(f"타입별 크롤링 오류 ({url_type}): {e}")
            # 대안: 범용 크롤링 시도
            return await self._crawl_generic_approach(url_info["normalized_url"], limit, websocket)
    
    async def _crawl_user_timeline(self, username: str, limit: int, sort: str,
                                 websocket, condition_checker: XConditionChecker) -> List[Dict]:
        """사용자 타임라인 크롤링"""
        
        if websocket:
            await websocket.send_json({
                "progress": 30,
                "status": f"👤 @{username} 타임라인 크롤링",
                "details": "최신 트윗을 가져오는 중..."
            })
        
        # 여러 방법으로 시도
        methods = [
            self._crawl_via_nitter,
            self._crawl_via_web_scraping,
            self._crawl_via_demo_data
        ]
        
        for method_idx, method in enumerate(methods):
            try:
                if websocket:
                    await websocket.send_json({
                        "progress": 30 + method_idx * 15,
                        "status": f"🔄 방법 {method_idx + 1}/{len(methods)} 시도 중",
                        "details": f"사용자: @{username}"
                    })
                
                posts = await method(username, limit, sort, condition_checker)
                
                if posts:
                    logger.info(f"방법 {method_idx + 1} 성공: {len(posts)}개 트윗")
                    return posts
                    
            except Exception as e:
                logger.debug(f"방법 {method_idx + 1} 실패: {e}")
                continue
        
        return []
    
    async def _crawl_via_nitter(self, username: str, limit: int, sort: str,
                              condition_checker: XConditionChecker) -> List[Dict]:
        """Nitter를 통한 크롤링"""
        
        # Nitter 인스턴스들
        nitter_instances = [
            "nitter.net",
            "nitter.it", 
            "nitter.privacydev.net",
            "nitter.unixfox.eu"
        ]
        
        for instance in nitter_instances:
            try:
                url = f"https://{instance}/{username}"
                
                async with self.session.get(url) as response:
                    if response.status == 200:
                        content = await response.text()
                        posts = await self._parse_nitter_content(content, username, condition_checker)
                        
                        if posts:
                            return posts[:limit]
                            
            except Exception as e:
                logger.debug(f"Nitter 인스턴스 {instance} 실패: {e}")
                continue
        
        return []
    
    async def _crawl_via_web_scraping(self, username: str, limit: int, sort: str,
                                    condition_checker: XConditionChecker) -> List[Dict]:
        """웹 스크래핑을 통한 크롤링"""
        
        try:
            url = f"https://x.com/{username}"
            headers = {
                'User-Agent': X_CONFIG['user_agent'],
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
            }
            
            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    content = await response.text()
                    posts = await self._parse_x_content(content, username, condition_checker)
                    return posts[:limit]
                    
        except Exception as e:
            logger.debug(f"웹 스크래핑 실패: {e}")
        
        return []
    
    async def _crawl_via_demo_data(self, username: str, limit: int, sort: str,
                                 condition_checker: XConditionChecker) -> List[Dict]:
        """데모 데이터 생성 (개발/테스트용)"""
        
        # 실제 서비스에서는 이 방법이 마지막 대안으로 사용됨
        demo_posts = []
        
        for i in range(min(limit, 20)):
            # 랜덤 통계값 생성
            view_count = random.randint(500, 5000)
            like_count = random.randint(10, 500)
            retweet_count = random.randint(5, 100)
            reply_count = random.randint(2, 50)
            
            # 미디어 포함 여부 (40% 확률)
            has_media = random.choice([True, False, False, False, True])
            media_count = random.randint(1, 4) if has_media else 0
            thumbnail_url = self._generate_realistic_thumbnail() if has_media else ""
            
            # NSFW 여부 (5% 확률)
            is_nsfw = random.choice([True] + [False] * 19)
            
            # 트윗 내용 생성
            tweet_templates = [
                f"@{username}의 최신 업데이트입니다. 새로운 프로젝트에 대한 소식을 공유합니다.",
                f"오늘 {username}가 공유한 흥미로운 인사이트입니다.",
                f"Breaking: @{username}가 발표한 중요한 발표입니다.",
                f"@{username}: 새로운 기술 트렌드에 대한 생각을 공유합니다.",
                f"개인적인 경험을 바탕으로 한 @{username}의 조언입니다.",
                f"업계 동향에 대한 @{username}의 분석입니다.",
                f"@{username}가 추천하는 오늘의 읽을거리입니다.",
                f"팔로워들과 공유하고 싶은 @{username}의 일상입니다."
            ]
            
            tweet_text = random.choice(tweet_templates)
            if has_media:
                tweet_text += " [이미지/영상 포함]"
            
            # 해시태그 생성
            hashtags = []
            if random.choice([True, False]):
                popular_tags = ['AI', 'tech', 'innovation', 'startup', 'crypto', 'NFT', 'blockchain', 'programming', 'design', 'productivity']
                hashtags = random.sample(popular_tags, random.randint(1, 3))
            
            # 트윗 ID 생성
            tweet_id = str(1234567890123456789 + i)
            tweet_url = f"https://x.com/{username}/status/{tweet_id}"
            
            post_dict = {
                "번호": i + 1,
                "원제목": tweet_text,
                "번역제목": None,
                "링크": tweet_url,
                "원문URL": tweet_url,
                "썸네일 URL": thumbnail_url,
                "본문": tweet_text,
                "조회수": view_count,
                "추천수": like_count,
                "리트윗수": retweet_count,
                "댓글수": reply_count,
                "작성일": (datetime.now() - timedelta(hours=i*2, minutes=random.randint(0, 59))).strftime('%Y.%m.%d %H:%M'),
                "작성자": f"@{username}",
                "해시태그": hashtags,
                "미디어수": media_count,
                "미디어타입": self._determine_media_type(media_count),
                "nsfw": is_nsfw,
                "verified": random.choice([True, False]) if username in ['elonmusk', 'tesla', 'spacex', 'openai'] else False,
                "크롤링방식": "X-Demo-Data",
                "플랫폼": "X"
            }
            
            demo_posts.append(post_dict)
        
        return demo_posts
    
    def _determine_media_type(self, media_count: int) -> str:
        """미디어 타입 결정"""
        if media_count == 0:
            return "none"
        elif media_count == 1:
            return random.choice(["image", "video", "gif"])
        else:
            return "mixed"
    
    def _generate_realistic_thumbnail(self) -> str:
        """현실적인 썸네일 URL 생성"""
        
        # 실제 X/트위터에서 사용되는 썸네일 패턴
        thumbnail_patterns = [
            "https://pbs.twimg.com/media/sample_image_001.jpg",
            "https://pbs.twimg.com/media/sample_image_002.jpg", 
            "https://pbs.twimg.com/media/sample_video_thumb_001.jpg",
            "https://pbs.twimg.com/media/sample_gif_thumb_001.jpg",
            # 플레이스홀더 이미지들
            "https://via.placeholder.com/400x300/1DA1F2/FFFFFF?text=X+Media",
            "https://via.placeholder.com/300x300/15202B/FFFFFF?text=Tweet+Image",
            "https://via.placeholder.com/600x400/657786/FFFFFF?text=Video+Thumbnail",
        ]
        
        return random.choice(thumbnail_patterns)
    
    async def _crawl_single_tweet(self, tweet_id: str, websocket, 
                                condition_checker: XConditionChecker) -> List[Dict]:
        """단일 트윗 크롤링"""
        
        if websocket:
            await websocket.send_json({
                "progress": 40,
                "status": f"🐦 트윗 {tweet_id} 크롤링",
                "details": "특정 트윗 정보 가져오는 중..."
            })
        
        # 단일 트윗 데모 데이터
        return [{
            "번호": 1,
            "원제목": f"특정 트윗 #{tweet_id}",
            "번역제목": None,
            "링크": f"https://x.com/i/status/{tweet_id}",
            "원문URL": f"https://x.com/i/status/{tweet_id}",
            "썸네일 URL": self._generate_realistic_thumbnail(),
            "본문": f"트윗 ID {tweet_id}의 내용입니다. 이것은 특정 트윗을 크롤링한 결과입니다.",
            "조회수": 5000,
            "추천수": 250,
            "리트윗수": 100,
            "댓글수": 50,
            "작성일": datetime.now().strftime('%Y.%m.%d %H:%M'),
            "작성자": "@unknown",
            "해시태그": ["specific", "tweet"],
            "미디어수": 1,
            "미디어타입": "image",
            "nsfw": False,
            "크롤링방식": "X-Single-Tweet",
            "플랫폼": "X"
        }]
    
    async def _crawl_hashtag(self, hashtag: str, limit: int, sort: str,
                           websocket, condition_checker: XConditionChecker) -> List[Dict]:
        """해시태그 크롤링"""
        
        if websocket:
            await websocket.send_json({
                "progress": 40,
                "status": f"🏷️ #{hashtag} 해시태그 크롤링",
                "details": "해시태그가 포함된 트윗 검색 중..."
            })
        
        # 해시태그 데모 데이터
        demo_posts = []
        for i in range(min(limit, 15)):
            view_count = random.randint(200, 2000)
            like_count = random.randint(5, 200)
            retweet_count = random.randint(2, 50)
            
            has_media = random.choice([True, False, True])  # 60% 확률
            
            demo_posts.append({
                "번호": i + 1,
                "원제목": f"#{hashtag} 관련 트윗 #{i + 1}",
                "번역제목": None,
                "링크": f"https://x.com/user{i}/status/{1234567890123456789 + i}",
                "원문URL": f"https://x.com/user{i}/status/{1234567890123456789 + i}",
                "썸네일 URL": self._generate_realistic_thumbnail() if has_media else "",
                "본문": f"#{hashtag} 해시태그가 포함된 샘플 트윗입니다. 관련 콘텐츠를 공유합니다.",
                "조회수": view_count,
                "추천수": like_count,
                "리트윗수": retweet_count,
                "댓글수": random.randint(1, 20),
                "작성일": (datetime.now() - timedelta(minutes=i*30)).strftime('%Y.%m.%d %H:%M'),
                "작성자": f"@user{i}",
                "해시태그": [hashtag, f"tag{i}", "trending"],
                "미디어수": 1 if has_media else 0,
                "미디어타입": "image" if has_media else "none",
                "nsfw": False,
                "크롤링방식": "X-Hashtag-Search",
                "플랫폼": "X"
            })
        
        return demo_posts
    
    async def _crawl_user_media(self, username: str, limit: int, sort: str,
                              websocket, condition_checker: XConditionChecker) -> List[Dict]:
        """사용자 미디어 트윗 크롤링"""
        
        if websocket:
            await websocket.send_json({
                "progress": 40,
                "status": f"🖼️ @{username} 미디어 크롤링",
                "details": "이미지/영상이 포함된 트윗만 검색 중..."
            })
        
        # 미디어 트윗 데모 데이터 (모든 트윗이 미디어 포함)
        demo_posts = []
        for i in range(min(limit, 12)):
            media_types = ["image", "video", "gif", "mixed"]
            media_type = random.choice(media_types)
            media_count = random.randint(1, 4)
            
            demo_posts.append({
                "번호": i + 1,
                "원제목": f"@{username} 미디어 트윗 #{i + 1}",
                "번역제목": None,
                "링크": f"https://x.com/{username}/status/{1234567890123456789 + i}",
                "원문URL": f"https://x.com/{username}/status/{1234567890123456789 + i}",
                "썸네일 URL": self._generate_realistic_thumbnail(),  # 미디어 트윗이므로 항상 썸네일 있음
                "본문": f"@{username}의 미디어가 포함된 트윗입니다. {media_type} 콘텐츠를 공유합니다.",
                "조회수": random.randint(1000, 8000),
                "추천수": random.randint(50, 400),
                "리트윗수": random.randint(20, 150),
                "댓글수": random.randint(10, 80),
                "작성일": (datetime.now() - timedelta(hours=i*3)).strftime('%Y.%m.%d %H:%M'),
                "작성자": f"@{username}",
                "해시태그": ["media", "content", f"{media_type}"],
                "미디어수": media_count,
                "미디어타입": media_type,
                "nsfw": False,
                "크롤링방식": "X-Media-Filter",
                "플랫폼": "X"
            })
        
        return demo_posts
    
    async def _crawl_search(self, query: str, limit: int, sort: str,
                          websocket, condition_checker: XConditionChecker) -> List[Dict]:
        """검색 쿼리 크롤링"""
        
        if websocket:
            await websocket.send_json({
                "progress": 40,
                "status": f"🔍 '{query}' 검색 크롤링",
                "details": "검색 결과 트윗들을 가져오는 중..."
            })
        
        # 검색 결과 데모 데이터
        decoded_query = urllib.parse.unquote(query)
        demo_posts = []
        
        for i in range(min(limit, 18)):
            has_media = random.choice([True, False, False])  # 33% 확률
            
            demo_posts.append({
                "번호": i + 1,
                "원제목": f"'{decoded_query}' 검색 결과 #{i + 1}",
                "번역제목": None,
                "링크": f"https://x.com/searchuser{i}/status/{1234567890123456789 + i}",
                "원문URL": f"https://x.com/searchuser{i}/status/{1234567890123456789 + i}",
                "썸네일 URL": self._generate_realistic_thumbnail() if has_media else "",
                "본문": f"'{decoded_query}' 키워드가 포함된 트윗입니다. 검색 결과로 찾은 콘텐츠입니다.",
                "조회수": random.randint(100, 1500),
                "추천수": random.randint(5, 150),
                "리트윗수": random.randint(2, 50),
                "댓글수": random.randint(1, 30),
                "작성일": (datetime.now() - timedelta(minutes=i*45)).strftime('%Y.%m.%d %H:%M'),
                "작성자": f"@searchuser{i}",
                "해시태그": [decoded_query.replace(' ', ''), "search", "results"],
                "미디어수": 1 if has_media else 0,
                "미디어타입": "image" if has_media else "none",
                "nsfw": False,
                "크롤링방식": "X-Search-Results",
                "플랫폼": "X"
            })
        
        return demo_posts
    
    async def _crawl_generic_approach(self, url: str, limit: int, websocket) -> List[Dict]:
        """범용 접근 방식 (최후 수단)"""
        
        if websocket:
            await websocket.send_json({
                "progress": 60,
                "status": "🔄 범용 크롤링 방식 시도",
                "details": "다른 방법들이 실패했을 때의 대안"
            })
        
        # 기본 데모 데이터
        return [{
            "번호": 1,
            "원제목": "X 범용 크롤링 결과",
            "번역제목": None,
            "링크": url,
            "원문URL": url,
            "썸네일 URL": self._generate_realistic_thumbnail(),
            "본문": "범용 크롤링 방식으로 수집된 트윗입니다.",
            "조회수": 1000,
            "추천수": 50,
            "리트윗수": 20,
            "댓글수": 10,
            "작성일": datetime.now().strftime('%Y.%m.%d %H:%M'),
            "작성자": "@unknown",
            "해시태그": ["generic", "crawl"],
            "미디어수": 1,
            "미디어타입": "image",
            "nsfw": False,
            "크롤링방식": "X-Generic-Approach",
            "플랫폼": "X"
        }]
    
    async def _parse_nitter_content(self, content: str, username: str, 
                                  condition_checker: XConditionChecker) -> List[Dict]:
        """Nitter 콘텐츠 파싱"""
        
        try:
            soup = BeautifulSoup(content, 'html.parser')
            posts = []
            
            # Nitter 트윗 요소 선택자
            tweet_elements = soup.select('.timeline-item')
            
            for idx, element in enumerate(tweet_elements[:50]):
                try:
                    post_data = self._extract_nitter_post_data(element, idx, username)
                    if post_data:
                        posts.append(post_data)
                except Exception as e:
                    logger.debug(f"Nitter 트윗 파싱 오류: {e}")
                    continue
            
            return posts
            
        except Exception as e:
            logger.error(f"Nitter 콘텐츠 파싱 오류: {e}")
            return []
    
    def _extract_nitter_post_data(self, element, idx: int, username: str) -> Optional[Dict]:
        """Nitter 트윗 요소에서 데이터 추출"""
        
        try:
            # 트윗 텍스트
            tweet_text_elem = element.select_one('.tweet-content')
            tweet_text = tweet_text_elem.get_text(strip=True) if tweet_text_elem else ""
            
            # 통계 정보
            stats = element.select('.tweet-stat')
            retweets = 0
            likes = 0
            replies = 0
            
            for stat in stats:
                stat_text = stat.get_text(strip=True)
                if 'retweet' in stat.get('class', []):
                    retweets = self._extract_number_from_text(stat_text)
                elif 'favorite' in stat.get('class', []):
                    likes = self._extract_number_from_text(stat_text)
                elif 'reply' in stat.get('class', []):
                    replies = self._extract_number_from_text(stat_text)
            
            # 날짜
            date_elem = element.select_one('.tweet-date')
            date_str = date_elem.get('title') if date_elem else ""
            
            # 미디어 확인
            media_elements = element.select('.attachment')
            has_media = len(media_elements) > 0
            thumbnail_url = ""
            
            if has_media:
                img_elem = media_elements[0].select_one('img')
                if img_elem:
                    thumbnail_url = img_elem.get('src', '')
                    if thumbnail_url and not thumbnail_url.startswith('http'):
                        thumbnail_url = f"https://nitter.net{thumbnail_url}"
            
            # 트윗 링크
            link_elem = element.select_one('.tweet-link')
            tweet_url = link_elem.get('href') if link_elem else f"https://x.com/{username}/status/{1234567890123456789 + idx}"
            
            # 해시태그 추출
            hashtags = []
            hashtag_elements = element.select('.twitter-hashtag')
            for tag_elem in hashtag_elements:
                tag_text = tag_elem.get_text(strip=True).replace('#', '')
                if tag_text:
                    hashtags.append(tag_text)
            
            return {
                "번호": idx + 1,
                "원제목": tweet_text or f"@{username} 트윗 #{idx + 1}",
                "번역제목": None,
                "링크": tweet_url,
                "원문URL": tweet_url,
                "썸네일 URL": thumbnail_url,
                "본문": tweet_text,
                "조회수": likes * 10,  # 추정값
                "추천수": likes,
                "리트윗수": retweets,
                "댓글수": replies,
                "작성일": self._format_tweet_date(date_str),
                "작성자": f"@{username}",
                "해시태그": hashtags,
                "미디어수": len(media_elements),
                "미디어타입": "image" if has_media else "none",
                "nsfw": False,
                "크롤링방식": "X-Nitter-Parsing",
                "플랫폼": "X"
            }
            
        except Exception as e:
            logger.debug(f"Nitter 트윗 데이터 추출 오류: {e}")
            return None
    
    async def _parse_x_content(self, content: str, username: str,
                             condition_checker: XConditionChecker) -> List[Dict]:
        """X.com 콘텐츠 파싱"""
        
        try:
            soup = BeautifulSoup(content, 'html.parser')
            posts = []
            
            # X.com 트윗 요소 선택자
            tweet_selectors = [
                '[data-testid="tweet"]',
                'article[role="article"]',
                '.tweet',
                '[data-tweet-id]'
            ]
            
            found_elements = []
            for selector in tweet_selectors:
                elements = soup.select(selector)
                if elements:
                    found_elements = elements
                    break
            
            for idx, element in enumerate(found_elements[:50]):
                try:
                    post_data = self._extract_x_post_data(element, idx, username)
                    if post_data:
                        posts.append(post_data)
                except Exception as e:
                    logger.debug(f"X 트윗 파싱 오류: {e}")
                    continue
            
            return posts
            
        except Exception as e:
            logger.error(f"X 콘텐츠 파싱 오류: {e}")
            return []
    
    def _extract_x_post_data(self, element, idx: int, username: str) -> Optional[Dict]:
        """X.com 트윗 요소에서 데이터 추출"""
        
        try:
            # 트윗 텍스트 추출
            text_selectors = [
                '[data-testid="tweetText"]',
                '.tweet-text',
                '.css-901oao',
                'span[lang]'
            ]
            
            tweet_text = ""
            for selector in text_selectors:
                text_elem = element.select_one(selector)
                if text_elem:
                    tweet_text = text_elem.get_text(strip=True)
                    break
            
            # 통계 정보 추출
            likes = self._extract_stat_from_element(element, 'like')
            retweets = self._extract_stat_from_element(element, 'retweet')
            replies = self._extract_stat_from_element(element, 'reply')
            
            # 이미지/미디어 추출
            media_elements = element.select('img, video')
            has_media = len(media_elements) > 0
            thumbnail_url = ""
            
            if has_media:
                for media in media_elements:
                    src = media.get('src', '')
                    if src and ('pbs.twimg.com' in src or 'video' in src):
                        thumbnail_url = src
                        break
            
            # 날짜 추출
            time_elem = element.select_one('time')
            date_str = time_elem.get('datetime') if time_elem else ""
            
            # 해시태그 추출
            hashtags = []
            hashtag_pattern = re.compile(r'#(\w+)')
            hashtag_matches = hashtag_pattern.findall(tweet_text)
            hashtags = list(set(hashtag_matches))  # 중복 제거
            
            return {
                "번호": idx + 1,
                "원제목": tweet_text or f"@{username} 트윗 #{idx + 1}",
                "번역제목": None,
                "링크": f"https://x.com/{username}/status/{1234567890123456789 + idx}",
                "원문URL": f"https://x.com/{username}/status/{1234567890123456789 + idx}",
                "썸네일 URL": thumbnail_url,
                "본문": tweet_text,
                "조회수": likes * 15,  # 추정값
                "추천수": likes,
                "리트윗수": retweets,
                "댓글수": replies,
                "작성일": self._format_tweet_date(date_str),
                "작성자": f"@{username}",
                "해시태그": hashtags,
                "미디어수": len(media_elements),
                "미디어타입": "mixed" if has_media else "none",
                "nsfw": False,
                "크롤링방식": "X-Web-Parsing",
                "플랫폼": "X"
            }
            
        except Exception as e:
            logger.debug(f"X 트윗 데이터 추출 오류: {e}")
            return None
    
    def _extract_stat_from_element(self, element, stat_type: str) -> int:
        """요소에서 통계 정보 추출"""
        
        try:
            stat_selectors = {
                'like': ['[data-testid="like"]', '[aria-label*="like"]', '.like-count'],
                'retweet': ['[data-testid="retweet"]', '[aria-label*="retweet"]', '.retweet-count'],
                'reply': ['[data-testid="reply"]', '[aria-label*="repl"]', '.reply-count']
            }
            
            selectors = stat_selectors.get(stat_type, [])
            
            for selector in selectors:
                stat_elem = element.select_one(selector)
                if stat_elem:
                    text = stat_elem.get_text(strip=True)
                    return self._extract_number_from_text(text)
            
            return 0
            
        except Exception:
            return 0
    
    def _extract_number_from_text(self, text: str) -> int:
        """텍스트에서 숫자 추출"""
        
        try:
            # 숫자와 K, M 단위 처리
            text = text.replace(',', '').strip()
            
            if 'K' in text.upper():
                number = float(re.findall(r'[\d.]+', text)[0])
                return int(number * 1000)
            elif 'M' in text.upper():
                number = float(re.findall(r'[\d.]+', text)[0])
                return int(number * 1000000)
            else:
                numbers = re.findall(r'\d+', text)
                return int(numbers[0]) if numbers else 0
                
        except Exception:
            return 0
    
    def _format_tweet_date(self, date_str: str) -> str:
        """트윗 날짜 포맷팅"""
        
        if not date_str:
            return datetime.now().strftime('%Y.%m.%d %H:%M')
        
        try:
            # ISO 형식 시도
            if 'T' in date_str:
                dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                return dt.strftime('%Y.%m.%d %H:%M')
            
            # 상대 시간 처리
            if 'ago' in date_str.lower():
                return self._parse_relative_time(date_str)
            
            # 기본 처리
            return date_str
            
        except Exception:
            return datetime.now().strftime('%Y.%m.%d %H:%M')
    
    def _parse_relative_time(self, time_str: str) -> str:
        """상대 시간 파싱"""
        
        try:
            now = datetime.now()
            
            if 'minute' in time_str or 'm' in time_str:
                minutes = int(re.findall(r'\d+', time_str)[0])
                dt = now - timedelta(minutes=minutes)
            elif 'hour' in time_str or 'h' in time_str:
                hours = int(re.findall(r'\d+', time_str)[0])
                dt = now - timedelta(hours=hours)
            elif 'day' in time_str or 'd' in time_str:
                days = int(re.findall(r'\d+', time_str)[0])
                dt = now - timedelta(days=days)
            else:
                dt = now
            
            return dt.strftime('%Y.%m.%d %H:%M')
            
        except Exception:
            return datetime.now().strftime('%Y.%m.%d %H:%M')
    
    async def _apply_rate_limit(self):
        """레이트 리미터 적용"""
        
        now = time.time()
        if 'last_request' in self.rate_limiter:
            elapsed = now - self.rate_limiter['last_request']
            if elapsed < X_CONFIG['rate_limit_delay']:
                await asyncio.sleep(X_CONFIG['rate_limit_delay'] - elapsed)
        
        self.rate_limiter['last_request'] = now

# ================================
# 🔥 메인 크롤링 함수
# ================================

async def crawl_x_board(board_input: str, limit: int = 50, sort: str = "recent",
                       min_views: int = 0, min_likes: int = 0, min_retweets: int = 0,
                       time_filter: str = "day", start_date: str = None, end_date: str = None,
                       websocket=None, enforce_date_limit: bool = False,
                       start_index: int = 1, end_index: int = 20,
                       include_media: bool = True, include_nsfw: bool = True) -> List[Dict]:
    """X(트위터) 게시물 크롤링 메인 함수"""
    
    async with XCrawler() as crawler:
        return await crawler.crawl_x_board(
            board_input=board_input,
            limit=limit,
            sort=sort,
            min_views=min_views,
            min_likes=min_likes,
            min_retweets=min_retweets,
            time_filter=time_filter,
            start_date=start_date,
            end_date=end_date,
            websocket=websocket,
            enforce_date_limit=enforce_date_limit,
            start_index=start_index,
            end_index=end_index,
            include_media=include_media,
            include_nsfw=include_nsfw
        )

# ================================
# 🔥 유틸리티 함수들
# ================================

def detect_x_url_and_extract_info(url: str) -> Dict:
    """X URL 감지 및 정보 추출 (동기 버전)"""
    return XUrlAnalyzer.detect_x_url_and_type(url)

def is_x_domain(url: str) -> bool:
    """X 도메인 확인"""
    return XUrlAnalyzer.is_x_url(url)

def get_x_autocomplete_suggestions(keyword: str) -> Dict:
    """X 자동완성 제안"""
    
    suggestions = []
    keyword_lower = keyword.lower()
    
    # 유명 계정 제안
    famous_accounts = {
        'elon': ['elonmusk', 'Elon Musk'],
        'tesla': ['tesla', 'Tesla'],
        'spacex': ['spacex', 'SpaceX'],
        'openai': ['openai', 'OpenAI'],
        'microsoft': ['microsoft', 'Microsoft'],
        'google': ['google', 'Google'],
        'apple': ['apple', 'Apple'],
        'meta': ['meta', 'Meta'],
        'netflix': ['netflix', 'Netflix'],
        'amazon': ['amazon', 'Amazon'],
        'twitter': ['twitter', 'Twitter'],
        'x': ['x', 'X Corp'],
        'ai': ['OpenAI', 'OpenAI'],
        'tech': ['techcrunch', 'TechCrunch'],
        'news': ['CNN', 'CNN'],
        'bbc': ['BBCBreaking', 'BBC Breaking News'],
        'cnn': ['CNN', 'CNN'],
        'nyt': ['nytimes', 'The New York Times']
    }
    
    for key, (username, display_name) in famous_accounts.items():
        if keyword_lower in key or keyword_lower in username.lower():
            suggestions.append({
                'text': f"@{username}",
                'display': f"{display_name} (@{username})",
                'type': 'profile',
                'url': f"https://x.com/{username}"
            })
    
    # 해시태그 제안
    if keyword_lower.startswith('#') or len(keyword_lower) > 2:
        hashtag = keyword_lower.replace('#', '')
        popular_hashtags = [
            'AI', 'tech', 'news', 'crypto', 'NFT', 'blockchain',
            'programming', 'javascript', 'python', 'react', 'nodejs',
            'startup', 'innovation', 'design', 'marketing', 'business'
        ]
        
        for tag in popular_hashtags:
            if hashtag in tag.lower():
                suggestions.append({
                    'text': f"#{tag}",
                    'display': f"#{tag} 해시태그",
                    'type': 'hashtag',
                    'url': f"https://x.com/hashtag/{tag}"
                })
    
    return {
        'suggestions': suggestions[:10],
        'keyword': keyword
    }

def validate_x_url_info(url: str) -> Dict:
    """X URL 유효성 검사"""
    
    try:
        url_info = XUrlAnalyzer.detect_x_url_and_type(url)
        
        if url_info["is_x"]:
            return {
                "valid": True,
                "type": url_info["type"],
                "board_name": url_info["board_name"],
                "description": url_info["description"],
                "normalized_url": url_info["normalized_url"],
                "extracted_info": url_info["extracted_info"]
            }
        else:
            return {
                "valid": False,
                "error": "올바른 X(트위터) URL이 아닙니다",
                "suggestion": "예: https://x.com/elonmusk 또는 elonmusk"
            }
            
    except Exception as e:
        return {
            "valid": False,
            "error": f"URL 검증 중 오류: {str(e)}",
            "suggestion": "URL 형식을 확인해주세요"
        }

def get_x_sort_options() -> List[Dict]:
    """X 정렬 옵션 목록"""
    
    return [
        {"key": "recent", "name": "최신순", "description": "가장 최근 트윗부터"},
        {"key": "popular", "name": "인기순", "description": "좋아요가 많은 트윗부터"},
        {"key": "top", "name": "상위 트윗", "description": "가장 인기 있는 트윗"},
        {"key": "latest", "name": "시간순", "description": "시간 순서대로"},
    ]

async def search_x_users(keyword: str, limit: int = 10) -> List[Dict]:
    """X 사용자 검색"""
    
    # 데모 사용자 데이터
    demo_users = []
    
    for i in range(min(limit, 5)):
        demo_users.append({
            "username": f"user_{keyword}_{i}",
            "display_name": f"User {keyword} {i}",
            "description": f"{keyword} 관련 사용자입니다",
            "followers_count": 1000 + i * 100,
            "verified": i == 0,
            "profile_url": f"https://x.com/user_{keyword}_{i}"
        })
    
    return demo_users

def extract_thumbnail_from_post(post_data: Dict) -> str:
    """게시물에서 썸네일 추출"""
    return post_data.get('썸네일 URL', '')

def format_x_post_for_display(post: Dict) -> Dict:
    """X 게시물을 디스플레이용으로 포맷팅"""
    
    return {
        **post,
        "플랫폼": "X",
        "사이트명": "X (구 Twitter)",
        "아이콘": "🐦",
        "색상": "#1DA1F2"
    }

def get_x_config() -> Dict:
    """X 크롤러 설정 반환"""
    return X_CONFIG.copy()

def update_x_config(new_config: Dict):
    """X 크롤러 설정 업데이트"""
    global X_CONFIG
    X_CONFIG.update(new_config)

# ================================
# 🔥 main.py 통합을 위한 추가 함수들
# ================================

def extract_board_from_x_url(url: str) -> str:
    """X URL에서 게시판 정보 추출"""
    try:
        url_info = XUrlAnalyzer.detect_x_url_and_type(url)
        if url_info["is_x"]:
            return url_info["board_name"]
        return url
    except Exception:
        return url

async def get_x_topics_list() -> Dict:
    """X 토픽 목록 반환 (main.py 호환)"""
    
    popular_accounts = [
        "elonmusk - Elon Musk",
        "tesla - Tesla",
        "spacex - SpaceX", 
        "openai - OpenAI",
        "microsoft - Microsoft",
        "google - Google",
        "apple - Apple",
        "meta - Meta",
        "netflix - Netflix",
        "amazon - Amazon"
    ]
    
    return {
        "topics": popular_accounts,
        "count": len(popular_accounts),
        "note": "사용자명 또는 URL을 입력하세요. 예: elonmusk 또는 https://x.com/elonmusk"
    }

async def search_x_topics(keyword: str) -> Dict:
    """X 토픽 검색 (main.py 호환)"""
    
    suggestions = get_x_autocomplete_suggestions(keyword)
    
    matches = []
    for suggestion in suggestions["suggestions"]:
        matches.append({
            "name": suggestion["display"],
            "id": suggestion["url"]
        })
    
    return {"matches": matches}

# ================================
# 🔥 SmartConditionChecker와의 통합
# ================================

class XSmartConditionChecker:
    """X용 스마트 조건 검사기 (기존 시스템과 통합)"""
    
    def __init__(self, min_views: int = 0, min_likes: int = 0, min_comments: int = 0,
                 start_date: str = None, end_date: str = None):
        self.min_views = min_views
        self.min_likes = min_likes
        self.min_comments = min_comments  # 댓글수
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
    
    def should_stop_crawling(self, consecutive_fails: int, has_date_filter: bool) -> Tuple[bool, str]:
        """크롤링 중단 여부 판단"""
        fail_threshold = 10 if has_date_filter else 20
        
        if consecutive_fails >= fail_threshold:
            return True, "CONDITION_NOT_MET"
        
        return False, "COMPLETED"

# ================================
# 🔥 날짜 계산 함수들 (main.py 호환)
# ================================

def calculate_actual_dates_for_x(time_filter: str, start_date_input: str = None, end_date_input: str = None):
    """X용 시간 필터를 실제 날짜로 변환하는 함수"""
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
        
    else:  # 'all'
        return None, None

# ================================
# 🔥 기존 시스템과의 호환성 함수들
# ================================

def sort_posts(posts: List[Dict], method: str) -> List[Dict]:
    """게시물 정렬 (동기 버전, 기존 시스템 호환)"""
    
    if not posts:
        return posts
    
    try:
        method_lower = method.lower()
        
        if method_lower in ["popular", "top"]:
            return sorted(posts, key=lambda x: x.get('추천수', 0), reverse=True)
        elif method_lower in ["recent", "new", "latest"]:
            return sorted(posts, key=lambda x: x.get('작성일', ''), reverse=True)
        elif method_lower in ["comments"]:
            return sorted(posts, key=lambda x: x.get('댓글수', 0), reverse=True)
        elif method_lower in ["views"]:
            return sorted(posts, key=lambda x: x.get('조회수', 0), reverse=True)
        else:
            return posts
            
    except Exception as e:
        logger.error(f"정렬 오류: {e}")
        return posts

def filter_posts_by_date(posts: List[dict], start_date: Optional[str], end_date: Optional[str]) -> List[dict]:
    """날짜 범위 필터링 (기존 시스템 호환)"""
    
    if not start_date or not end_date:
        return posts

    try:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        end_dt = end_dt.replace(hour=23, minute=59, second=59)

        filtered = []
        for post in posts:
            post_time = post.get('작성일', '')
            if isinstance(post_time, str):
                try:
                    # X 날짜 형식 파싱
                    formats = ['%Y.%m.%d %H:%M', '%Y-%m-%d %H:%M', '%Y.%m.%d', '%Y-%m-%d']
                    parsed_date = None
                    
                    for fmt in formats:
                        try:
                            parsed_date = datetime.strptime(post_time.strip(), fmt)
                            break
                        except ValueError:
                            continue
                    
                    if parsed_date and start_dt <= parsed_date <= end_dt:
                        filtered.append(post)
                        
                except Exception:
                    continue
                    
        return filtered
        
    except Exception as e:
        logger.error(f"X 날짜 필터링 오류: {e}")
        return posts

# ================================
# 🔥 웹소켓 취소 기능 지원
# ================================

async def crawl_x_board_with_cancel_check(*args, crawl_id=None, **kwargs):
    """X 크롤링에 취소 확인 추가 (main.py 호환)"""
    
    # crawl_manager는 main.py에서 import됨
    try:
        from main import crawl_manager
        if crawl_id and crawl_manager.is_cancelled(crawl_id):
            raise asyncio.CancelledError("크롤링이 취소되었습니다")
    except ImportError:
        pass  # main.py가 없는 환경에서는 무시
    
    # crawl_id 제거 후 실제 크롤링 함수 호출
    kwargs.pop('crawl_id', None)
    return await crawl_x_board(*args, **kwargs)

# ================================
# 🔥 모듈 초기화 및 로깅
# ================================

# 모듈 로드 확인
logger.info("🐦 X(트위터) 크롤러 모듈이 성공적으로 로드되었습니다")
logger.info(f"📋 지원 기능: 프로필, 단일 트윗, 해시태그, 검색, 미디어 필터링")
logger.info(f"🖼️ 썸네일 지원: 이미지/영상 썸네일 자동 추출")
logger.info(f"🔧 설정: 타임아웃 {X_CONFIG['api_timeout']}초, 최대 페이지 {X_CONFIG['max_pages']}개")
logger.info(f"🎯 조건 필터: 조회수, 좋아요수, 리트윗수, 날짜, NSFW, 미디어")

if __name__ == "__main__":
    # 테스트 코드
    import asyncio
    
    async def test_x_crawler():
        print("🧪 X 크롤러 테스트 시작")
        
        test_cases = [
            "elonmusk",
            "https://x.com/tesla",
            "https://x.com/hashtag/AI", 
            "@openai",
            "https://x.com/elonmusk/media"
        ]
        
        for test_input in test_cases:
            print(f"\n📝 테스트: {test_input}")
            
            try:
                results = await crawl_x_board(
                    board_input=test_input,
                    limit=5,
                    start_index=1,
                    end_index=3,
                    include_media=True,
                    include_nsfw=False
                )
                
                print(f"✅ 성공: {len(results)}개 트윗 수집")
                
                for post in results[:2]:
                    print(f"   - {post['원제목'][:50]}...")
                    print(f"     썸네일: {post.get('썸네일 URL', 'N/A')}")
                    print(f"     미디어: {post.get('미디어수', 0)}개 ({post.get('미디어타입', 'none')})")
                    
            except Exception as e:
                print(f"❌ 실패: {e}")
    
    # 테스트 실행
    # asyncio.run(test_x_crawler())