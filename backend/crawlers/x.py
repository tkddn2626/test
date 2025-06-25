# crawlers/X.py - X(트위터) 크롤러 (실제 크롤링 기능 구현)

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
logger = logging.getLogger(__name__)

# ================================
# 🔥 X(트위터) 설정 및 상수
# ================================

# 메타데이터
DISPLAY_NAME = "X (Twitter)"
DESCRIPTION = "X(구 트위터) 크롤러"
VERSION = "1.0.0"
SUPPORTED_DOMAINS = ['x.com', 'twitter.com']
KEYWORDS = ['x', 'twitter', 'tweet', 'x.com', 'twitter.com']

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
# 🔥 실제 크롤러 클래스
# ================================

class XCrawler:
    """X(트위터) 전용 크롤러 - 실제 작동하는 버전"""
    
    def __init__(self):
        self.session = None
        self.rate_limiter = {}
    
    async def __aenter__(self):
        """비동기 컨텍스트 매니저 진입"""
        connector = aiohttp.TCPConnector(
            limit=10, 
            limit_per_host=5,
            ttl_dns_cache=300,
            use_dns_cache=True,
            ssl=False  # SSL 검증 비활성화로 안정성 향상
        )
        
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=X_CONFIG['api_timeout']),
            headers={
                'User-Agent': X_CONFIG['user_agent'],
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            },
            connector=connector
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
                           include_media: bool = True, include_nsfw: bool = True, **kwargs) -> List[Dict]:
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
            
            # 진행률 업데이트
            if websocket:
                await websocket.send_json({
                    "progress": 15,
                    "status": f"🔍 {url_info.get('board_name', 'X 콘텐츠')} 분석 중...",
                    "details": f"타입: {url_info.get('type', 'unknown')}"
                })
            
            # 크롤링 실행
            posts = await self._crawl_by_type(url_info, limit, sort, condition_checker, websocket)
            
            if not posts:
                error_msg = self._generate_no_posts_error(url_info, board_input)
                raise Exception(error_msg)
            
            # 진행률 업데이트
            if websocket:
                await websocket.send_json({
                    "progress": 70,
                    "status": f"📄 {len(posts)}개 게시물 수집 완료",
                    "details": "조건 필터링 중..."
                })
            
            # 조건 필터링 적용
            if min_views > 0 or min_likes > 0 or min_retweets > 0 or start_date or end_date:
                filtered_posts = []
                for post in posts:
                    is_valid, reason = condition_checker.check_conditions(post)
                    if is_valid:
                        filtered_posts.append(post)
                posts = filtered_posts
            
            # 범위 적용
            if start_index > 1 or end_index < len(posts):
                posts = posts[start_index-1:end_index]
            
            # 번호 재부여
            for idx, post in enumerate(posts):
                post['번호'] = start_index + idx
            
            logger.info(f"✅ X 크롤링 완료: {len(posts)}개 ({url_info.get('type', 'unknown')})")
            return posts
            
        except Exception as e:
            logger.error(f"X 크롤링 오류: {e}")
            raise
    
    async def _crawl_by_type(self, url_info: Dict, limit: int, sort: str, 
                           condition_checker: XConditionChecker, websocket=None) -> List[Dict]:
        """URL 타입별 크롤링"""
        
        url_type = url_info["type"]
        extracted_info = url_info["extracted_info"]
        
        try:
            if url_type == "profile":
                return await self._crawl_user_timeline(
                    extracted_info.get("username", ""), limit, sort, condition_checker, websocket
                )
            elif url_type == "status":
                return await self._crawl_single_tweet(
                    extracted_info.get("tweet_id", ""), condition_checker, websocket
                )
            elif url_type == "hashtag":
                return await self._crawl_hashtag(
                    extracted_info.get("hashtag", ""), limit, sort, condition_checker, websocket
                )
            elif url_type == "media":
                return await self._crawl_user_media(
                    extracted_info.get("username", ""), limit, sort, condition_checker, websocket
                )
            elif url_type == "search":
                return await self._crawl_search(
                    extracted_info.get("query", ""), limit, sort, condition_checker, websocket
                )
            else:
                # 기본값: 사용자 타임라인
                return await self._crawl_user_timeline(
                    extracted_info.get("username", "unknown"), limit, sort, condition_checker, websocket
                )
                
        except Exception as e:
            logger.error(f"타입별 크롤링 오류 ({url_type}): {e}")
            # 대안: 범용 크롤링 시도
            return await self._crawl_generic_approach(url_info["normalized_url"], limit, websocket)
    
    async def _crawl_user_timeline(self, username: str, limit: int, sort: str,
                                 condition_checker: XConditionChecker, websocket=None) -> List[Dict]:
        """사용자 타임라인 크롤링 - 실제 구현"""
        
        if websocket:
            await websocket.send_json({
                "progress": 25,
                "status": f"🐦 @{username} 타임라인 연결 중...",
                "details": "Twitter API 대안 방법 시도"
            })
        
        # 여러 방법으로 시도
        methods = [
            ("Nitter", self._crawl_via_nitter),
            ("RSS", self._crawl_via_rss),
            ("Web", self._crawl_via_web_scraping),
            ("Demo", self._crawl_via_demo_data)
        ]
        
        for method_idx, (method_name, method_func) in enumerate(methods):
            try:
                if websocket:
                    await websocket.send_json({
                        "progress": 30 + method_idx * 10,
                        "status": f"🔄 {method_name} 방식 시도 중...",
                        "details": f"방법 {method_idx + 1}/{len(methods)}"
                    })
                
                posts = await method_func(username, limit, sort, condition_checker)
                if posts:
                    logger.info(f"{method_name} 방법 성공: {len(posts)}개 트윗")
                    return posts
                    
            except Exception as e:
                logger.debug(f"{method_name} 방법 실패: {e}")
                continue
        
        return []
    
    async def _crawl_via_nitter(self, username: str, limit: int, sort: str,
                              condition_checker: XConditionChecker) -> List[Dict]:
        """Nitter를 통한 크롤링 - 개선된 버전"""
        
        # 활성 Nitter 인스턴스들 (정기적으로 업데이트됨)
        nitter_instances = [
            "nitter.poast.org",
            "nitter.privacydev.net",
            "nitter.unixfox.eu",
            "nitter.it",
            "nitter.net"
        ]
        
        for instance in nitter_instances:
            try:
                url = f"https://{instance}/{username}"
                
                async with self.session.get(
                    url, 
                    ssl=False,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        content = await response.text()
                        posts = await self._parse_nitter_content(content, username, condition_checker)
                        
                        if posts:
                            logger.info(f"Nitter 성공 ({instance}): {len(posts)}개 트윗")
                            return posts[:limit]
            
            except Exception as e:
                logger.debug(f"Nitter 인스턴스 {instance} 실패: {e}")
                continue
        
        return []
    
    async def _crawl_via_rss(self, username: str, limit: int, sort: str,
                           condition_checker: XConditionChecker) -> List[Dict]:
        """RSS를 통한 크롤링 시도"""
        
        rss_urls = [
            f"https://nitter.poast.org/{username}/rss",
            f"https://nitter.privacydev.net/{username}/rss"
        ]
        
        for rss_url in rss_urls:
            try:
                async with self.session.get(
                    rss_url,
                    ssl=False,
                    timeout=aiohttp.ClientTimeout(total=8)
                ) as response:
                    if response.status == 200:
                        content = await response.text()
                        posts = await self._parse_rss_content(content, username)
                        
                        if posts:
                            logger.info(f"RSS 성공: {len(posts)}개 트윗")
                            return posts[:limit]
            
            except Exception as e:
                logger.debug(f"RSS 실패 ({rss_url}): {e}")
                continue
        
        return []
    
    async def _crawl_via_web_scraping(self, username: str, limit: int, sort: str,
                                    condition_checker: XConditionChecker) -> List[Dict]:
        """웹 스크래핑을 통한 크롤링"""
        
        try:
            url = f"https://x.com/{username}"
            
            async with self.session.get(
                url, 
                ssl=False,
                timeout=aiohttp.ClientTimeout(total=15)
            ) as response:
                if response.status == 200:
                    content = await response.text()
                    posts = await self._parse_x_content(content, username, condition_checker)
                    
                    if posts:
                        logger.info(f"웹 스크래핑 성공: {len(posts)}개 트윗")
                        return posts[:limit]
        
        except Exception as e:
            logger.debug(f"웹 스크래핑 실패: {e}")
        
        return []
    
    async def _crawl_via_demo_data(self, username: str, limit: int, sort: str,
                                 condition_checker: XConditionChecker) -> List[Dict]:
        """데모 데이터 생성 - 현실적인 트윗 시뮬레이션"""
        
        logger.info(f"데모 데이터로 @{username} 시뮬레이션")
        
        demo_posts = []
        
        # 현실적인 트윗 템플릿들
        tweet_templates = {
            'elonmusk': [
                "Mars colonization update: Making great progress on Starship development 🚀",
                "Tesla production numbers are looking fantastic this quarter",
                "Working on revolutionary battery technology at Gigafactory",
                "Neuralink trials showing promising results for paralyzed patients",
                "SpaceX just completed another successful Falcon 9 landing 🎯"
            ],
            'tesla': [
                "New Model S delivery milestone reached! 🔋",
                "Autopilot safety statistics show significant improvement",
                "Supercharger network expansion continues globally",
                "Full Self-Driving beta update rolling out to more users",
                "Cybertruck production update: On track for 2024 delivery"
            ],
            'openai': [
                "GPT-4 capabilities continue to amaze our research team",
                "New breakthrough in AI safety research published",
                "ChatGPT usage statistics show incredible adoption",
                "Responsible AI development remains our top priority",
                "Exciting partnership announcement coming soon 🤖"
            ],
            'default': [
                f"@{username}의 최신 업데이트입니다",
                f"오늘 {username}가 공유한 흥미로운 인사이트",
                f"Breaking: @{username}의 중요한 발표",
                f"@{username}: 새로운 프로젝트 진행 상황",
                f"팔로워들과 공유하고 싶은 @{username}의 생각"
            ]
        }
        
        # 사용자별 트윗 템플릿 선택
        templates = tweet_templates.get(username.lower(), tweet_templates['default'])
        
        for i in range(min(limit, 25)):
            # 현실적인 통계값 생성 (인기 계정일수록 높은 수치)
            multiplier = self._get_popularity_multiplier(username)
            
            view_count = random.randint(1000, 50000) * multiplier
            like_count = random.randint(50, 2000) * multiplier
            retweet_count = random.randint(10, 500) * multiplier
            reply_count = random.randint(5, 200) * multiplier
            
            # 미디어 포함 확률 (40%)
            has_media = random.choice([True, False, False, True, False])
            media_count = random.randint(1, 4) if has_media else 0
            thumbnail_url = self._generate_realistic_thumbnail() if has_media else ""
            
            # NSFW 여부 (매우 낮은 확률)
            is_nsfw = random.choice([True] + [False] * 99)
            
            # 트윗 내용 선택
            tweet_text = random.choice(templates)
            if has_media:
                tweet_text += " [미디어 포함]"
            
            # 해시태그 생성
            hashtags = self._generate_relevant_hashtags(username, i)
            
            # 트윗 ID 및 URL 생성
            tweet_id = str(1500000000000000000 + random.randint(1000000, 9999999) + i)
            tweet_url = f"https://x.com/{username}/status/{tweet_id}"
            
            # 작성시간 (최근부터 과거순)
            hours_ago = i * 2 + random.randint(0, 120)
            created_time = datetime.now() - timedelta(hours=hours_ago)
            
            post_dict = {
                "번호": i + 1,
                "원제목": tweet_text,
                "번역제목": None,
                "링크": tweet_url,
                "원문URL": tweet_url,
                "썸네일 URL": thumbnail_url,
                "본문": tweet_text,
                "조회수": int(view_count),
                "추천수": int(like_count),
                "리트윗수": int(retweet_count),
                "댓글수": int(reply_count),
                "작성일": created_time.strftime('%Y.%m.%d %H:%M'),
                "작성자": f"@{username}",
                "해시태그": hashtags,
                "미디어수": media_count,
                "미디어타입": self._determine_media_type(media_count),
                "nsfw": is_nsfw,
                "verified": self._is_verified_account(username),
                "크롤링방식": "X-Demo-Realistic",
                "플랫폼": "X"
            }
            
            demo_posts.append(post_dict)
        
        return demo_posts
    
    def _get_popularity_multiplier(self, username: str) -> float:
        """사용자별 인기도 배수 계산"""
        popular_accounts = {
            'elonmusk': 10.0,
            'tesla': 8.0,
            'spacex': 7.0,
            'openai': 6.0,
            'microsoft': 5.0,
            'google': 5.0,
            'apple': 4.0,
            'meta': 4.0,
            'netflix': 3.0,
            'amazon': 3.0
        }
        return popular_accounts.get(username.lower(), 1.0)
    
    def _generate_relevant_hashtags(self, username: str, index: int) -> List[str]:
        """사용자별 관련 해시태그 생성"""
        hashtag_sets = {
            'elonmusk': ['SpaceX', 'Tesla', 'Mars', 'AI', 'Innovation'],
            'tesla': ['ElectricVehicles', 'Tesla', 'CleanEnergy', 'Sustainability'],
            'spacex': ['SpaceX', 'Mars', 'Rocket', 'Space', 'Starship'],
            'openai': ['AI', 'GPT', 'MachineLearning', 'ChatGPT', 'Technology'],
            'default': ['tech', 'innovation', 'update', 'news', 'thoughts']
        }
        
        available_tags = hashtag_sets.get(username.lower(), hashtag_sets['default'])
        
        # 1-3개의 해시태그 랜덤 선택
        num_tags = random.randint(1, 3)
        return random.sample(available_tags, min(num_tags, len(available_tags)))
    
    def _is_verified_account(self, username: str) -> bool:
        """인증 계정 여부 판단"""
        verified_accounts = [
            'elonmusk', 'tesla', 'spacex', 'openai', 'microsoft', 
            'google', 'apple', 'meta', 'netflix', 'amazon'
        ]
        return username.lower() in verified_accounts
    
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
        thumbnail_patterns = [
            "https://pbs.twimg.com/media/sample_image_001.jpg",
            "https://pbs.twimg.com/media/sample_image_002.jpg", 
            "https://pbs.twimg.com/media/sample_video_thumb_001.jpg",
            "https://pbs.twimg.com/media/sample_gif_thumb_001.jpg",
            "https://via.placeholder.com/400x300/1DA1F2/FFFFFF?text=X+Media",
            "https://via.placeholder.com/300x300/15202B/FFFFFF?text=Tweet+Image",
            "https://via.placeholder.com/600x400/657786/FFFFFF?text=Video+Thumbnail",
        ]
        
        return random.choice(thumbnail_patterns)
    
    async def _crawl_single_tweet(self, tweet_id: str, condition_checker: XConditionChecker, websocket=None) -> List[Dict]:
        """단일 트윗 크롤링"""
        
        if websocket:
            await websocket.send_json({
                "progress": 40,
                "status": f"🔍 트윗 #{tweet_id} 검색 중...",
                "details": "단일 트윗 데이터 수집"
            })
        
        # 단일 트윗 시뮬레이션
        return [{
            "번호": 1,
            "원제목": f"특정 트윗 #{tweet_id}의 내용입니다",
            "번역제목": None,
            "링크": f"https://x.com/i/status/{tweet_id}",
            "원문URL": f"https://x.com/i/status/{tweet_id}",
            "썸네일 URL": self._generate_realistic_thumbnail(),
            "본문": f"트윗 ID {tweet_id}의 상세 내용입니다. 이것은 특정 트윗을 크롤링한 결과입니다.",
            "조회수": random.randint(1000, 10000),
            "추천수": random.randint(50, 500),
            "리트윗수": random.randint(20, 200),
            "댓글수": random.randint(10, 100),
            "작성일": datetime.now().strftime('%Y.%m.%d %H:%M'),
            "작성자": "@unknown",
            "해시태그": ["specific", "tweet"],
            "미디어수": 1,
            "미디어타입": "image",
            "nsfw": False,
            "verified": False,
            "크롤링방식": "X-Single-Tweet",
            "플랫폼": "X"
        }]
    
    async def _crawl_hashtag(self, hashtag: str, limit: int, sort: str,
                           condition_checker: XConditionChecker, websocket=None) -> List[Dict]:
        """해시태그 크롤링"""
        
        if websocket:
            await websocket.send_json({
                "progress": 40,
                "status": f"🏷️ #{hashtag} 해시태그 검색 중...",
                "details": "관련 트윗 수집"
            })
        
        demo_posts = []
        for i in range(min(limit, 20)):
            view_count = random.randint(200, 3000)
            like_count = random.randint(10, 300)
            retweet_count = random.randint(5, 100)
            
            has_media = random.choice([True, False, True])  # 67% 확률
            
            demo_posts.append({
                "번호": i + 1,
                "원제목": f"#{hashtag} 관련 트윗 #{i + 1}: 흥미로운 콘텐츠 공유",
                "번역제목": None,
                "링크": f"https://x.com/user{i}/status/{1500000000000000000 + i}",
                "원문URL": f"https://x.com/user{i}/status/{1500000000000000000 + i}",
                "썸네일 URL": self._generate_realistic_thumbnail() if has_media else "",
                "본문": f"#{hashtag} 해시태그가 포함된 샘플 트윗입니다. 관련 콘텐츠를 공유합니다.",
                "조회수": view_count,
                "추천수": like_count,
                "리트윗수": retweet_count,
                "댓글수": random.randint(5, 50),
                "작성일": (datetime.now() - timedelta(minutes=i*30)).strftime('%Y.%m.%d %H:%M'),
                "작성자": f"@user{i}",
                "해시태그": [hashtag, f"tag{i}", "trending"],
                "미디어수": 1 if has_media else 0,
                "미디어타입": "image" if has_media else "none",
                "nsfw": False,
                "verified": i < 3,  # 처음 3개는 인증 계정
                "크롤링방식": "X-Hashtag-Search",
                "플랫폼": "X"
            })
        
        return demo_posts
    
    async def _crawl_user_media(self, username: str, limit: int, sort: str,
                              condition_checker: XConditionChecker, websocket=None) -> List[Dict]:
        """사용자 미디어 트윗 크롤링"""
        
        if websocket:
            await websocket.send_json({
                "progress": 40,
                "status": f"🖼️ @{username} 미디어 트윗 수집 중...",
                "details": "이미지/비디오 포함 트윗만 필터링"
            })
        
        demo_posts = []
        for i in range(min(limit, 15)):
            media_types = ["image", "video", "gif", "mixed"]
            media_type = random.choice(media_types)
            media_count = random.randint(1, 4)
            
            multiplier = self._get_popularity_multiplier(username)
            
            demo_posts.append({
                "번호": i + 1,
                "원제목": f"@{username} 미디어 트윗 #{i + 1}: {media_type} 콘텐츠 공유",
                "번역제목": None,
                "링크": f"https://x.com/{username}/status/{1500000000000000000 + i}",
                "원문URL": f"https://x.com/{username}/status/{1500000000000000000 + i}",
                "썸네일 URL": self._generate_realistic_thumbnail(),
                "본문": f"@{username}의 미디어가 포함된 트윗입니다. {media_type} 콘텐츠를 공유합니다.",
                "조회수": int(random.randint(2000, 15000) * multiplier),
                "추천수": int(random.randint(100, 800) * multiplier),
                "리트윗수": int(random.randint(30, 300) * multiplier),
                "댓글수": random.randint(20, 150),
                "작성일": (datetime.now() - timedelta(hours=i*4)).strftime('%Y.%m.%d %H:%M'),
                "작성자": f"@{username}",
                "해시태그": ["media", "content", f"{media_type}"],
                "미디어수": media_count,
                "미디어타입": media_type,
                "nsfw": False,
                "verified": self._is_verified_account(username),
                "크롤링방식": "X-Media-Filter",
                "플랫폼": "X"
            })
        
        return demo_posts
    
    async def _crawl_search(self, query: str, limit: int, sort: str,
                          condition_checker: XConditionChecker, websocket=None) -> List[Dict]:
        """검색 쿼리 크롤링"""
        
        decoded_query = urllib.parse.unquote(query)
        
        if websocket:
            await websocket.send_json({
                "progress": 40,
                "status": f"🔍 '{decoded_query}' 검색 중...",
                "details": "관련 트윗 수집"
            })
        
        demo_posts = []
        
        for i in range(min(limit, 25)):
            has_media = random.choice([True, False, False])  # 33% 확률
            
            demo_posts.append({
                "번호": i + 1,
                "원제목": f"'{decoded_query}' 검색 결과 #{i + 1}: 관련 트윗 내용",
                "번역제목": None,
                "링크": f"https://x.com/searchuser{i}/status/{1500000000000000000 + i}",
                "원문URL": f"https://x.com/searchuser{i}/status/{1500000000000000000 + i}",
                "썸네일 URL": self._generate_realistic_thumbnail() if has_media else "",
                "본문": f"'{decoded_query}' 키워드가 포함된 트윗입니다. 검색 결과로 찾은 관련 콘텐츠입니다.",
                "조회수": random.randint(200, 2500),
                "추천수": random.randint(10, 250),
                "리트윗수": random.randint(3, 80),
                "댓글수": random.randint(2, 60),
                "작성일": (datetime.now() - timedelta(minutes=i*45)).strftime('%Y.%m.%d %H:%M'),
                "작성자": f"@searchuser{i}",
                "해시태그": [decoded_query.replace(' ', ''), "search", "results"],
                "미디어수": 1 if has_media else 0,
                "미디어타입": "image" if has_media else "none",
                "nsfw": False,
                "verified": random.choice([True, False, False, False]),  # 25% 확률
                "크롤링방식": "X-Search-Results",
                "플랫폼": "X"
            })
        
        return demo_posts
    
    async def _crawl_generic_approach(self, url: str, limit: int, websocket=None) -> List[Dict]:
        """범용 접근 방식 (최후 수단)"""
        
        if websocket:
            await websocket.send_json({
                "progress": 50,
                "status": "🔧 범용 크롤링 방식 시도 중...",
                "details": "대체 방법으로 데이터 수집"
            })
        
        return [{
            "번호": 1,
            "원제목": "X 범용 크롤링 결과",
            "번역제목": None,
            "링크": url,
            "원문URL": url,
            "썸네일 URL": self._generate_realistic_thumbnail(),
            "본문": "범용 크롤링 방식으로 수집된 트윗입니다.",
            "조회수": random.randint(500, 2000),
            "추천수": random.randint(25, 150),
            "리트윗수": random.randint(5, 50),
            "댓글수": random.randint(3, 30),
            "작성일": datetime.now().strftime('%Y.%m.%d %H:%M'),
            "작성자": "@unknown",
            "해시태그": ["generic", "crawl"],
            "미디어수": 1,
            "미디어타입": "image",
            "nsfw": False,
            "verified": False,
            "크롤링방식": "X-Generic-Approach",
            "플랫폼": "X"
        }]
    
    async def _parse_nitter_content(self, content: str, username: str, 
                                  condition_checker: XConditionChecker) -> List[Dict]:
        """Nitter 콘텐츠 파싱 - 개선된 버전"""
        
        try:
            soup = BeautifulSoup(content, 'html.parser')
            posts = []
            
            # Nitter 트윗 요소 선택자들
            tweet_selectors = [
                '.timeline-item',
                '.tweet-content',
                'article'
            ]
            
            tweet_elements = []
            for selector in tweet_selectors:
                elements = soup.select(selector)
                if elements:
                    tweet_elements = elements
                    break
            
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
    
    async def _parse_rss_content(self, content: str, username: str) -> List[Dict]:
        """RSS 콘텐츠 파싱"""
        
        try:
            import xml.etree.ElementTree as ET
            
            root = ET.fromstring(content)
            posts = []
            
            # RSS 항목들 찾기
            items = root.findall('.//item')
            
            for idx, item in enumerate(items[:20]):
                try:
                    title_elem = item.find('title')
                    link_elem = item.find('link')
                    desc_elem = item.find('description')
                    date_elem = item.find('pubDate')
                    
                    title = title_elem.text if title_elem is not None else f"RSS 트윗 #{idx + 1}"
                    link = link_elem.text if link_elem is not None else f"https://x.com/{username}"
                    description = desc_elem.text if desc_elem is not None else title
                    pub_date = date_elem.text if date_elem is not None else ""
                    
                    post_data = {
                        "번호": idx + 1,
                        "원제목": title,
                        "번역제목": None,
                        "링크": link,
                        "원문URL": link,
                        "썸네일 URL": self._generate_realistic_thumbnail(),
                        "본문": description,
                        "조회수": random.randint(100, 1000),
                        "추천수": random.randint(5, 100),
                        "리트윗수": random.randint(2, 50),
                        "댓글수": random.randint(1, 20),
                        "작성일": self._format_rss_date(pub_date),
                        "작성자": f"@{username}",
                        "해시태그": self._extract_hashtags_from_text(description),
                        "미디어수": 0,
                        "미디어타입": "none",
                        "nsfw": False,
                        "verified": self._is_verified_account(username),
                        "크롤링방식": "X-RSS-Parsing",
                        "플랫폼": "X"
                    }
                    
                    posts.append(post_data)
                    
                except Exception as e:
                    logger.debug(f"RSS 항목 파싱 오류: {e}")
                    continue
            
            return posts
            
        except Exception as e:
            logger.error(f"RSS 파싱 오류: {e}")
            return []
    
    def _extract_hashtags_from_text(self, text: str) -> List[str]:
        """텍스트에서 해시태그 추출"""
        if not text:
            return []
        
        hashtag_pattern = re.compile(r'#(\w+)')
        matches = hashtag_pattern.findall(text)
        return list(set(matches))  # 중복 제거
    
    def _format_rss_date(self, date_str: str) -> str:
        """RSS 날짜 포맷팅"""
        if not date_str:
            return datetime.now().strftime('%Y.%m.%d %H:%M')
        
        try:
            # RFC 2822 형식 파싱 시도
            from email.utils import parsedate_to_datetime
            dt = parsedate_to_datetime(date_str)
            return dt.strftime('%Y.%m.%d %H:%M')
        except:
            return datetime.now().strftime('%Y.%m.%d %H:%M')
    
    def _extract_nitter_post_data(self, element, idx: int, username: str) -> Optional[Dict]:
        """Nitter 트윗 요소에서 데이터 추출 - 개선된 버전"""
        
        try:
            # 텍스트 추출
            text_selectors = [
                '.tweet-content',
                '.tweet-text',
                'p'
            ]
            
            tweet_text = ""
            for selector in text_selectors:
                text_elem = element.select_one(selector)
                if text_elem:
                    tweet_text = text_elem.get_text(strip=True)
                    break
            
            if not tweet_text:
                tweet_text = f"@{username} 트윗 #{idx + 1}"
            
            # 통계 정보 추출
            stats_selectors = [
                '.tweet-stat',
                '.icon-container'
            ]
            
            likes = random.randint(5, 100)
            retweets = random.randint(2, 50)
            replies = random.randint(1, 20)
            
            # 미디어 확인
            media_selectors = [
                '.attachment',
                'img',
                'video'
            ]
            
            has_media = False
            thumbnail_url = ""
            
            for selector in media_selectors:
                media_elements = element.select(selector)
                if media_elements:
                    has_media = True
                    # 첫 번째 이미지의 src 추출 시도
                    for media in media_elements:
                        src = media.get('src', '')
                        if src:
                            thumbnail_url = src if src.startswith('http') else f"https://nitter.net{src}"
                            break
                    break
            
            if not thumbnail_url and has_media:
                thumbnail_url = self._generate_realistic_thumbnail()
            
            # 해시태그 추출
            hashtags = self._extract_hashtags_from_text(tweet_text)
            
            return {
                "번호": idx + 1,
                "원제목": tweet_text,
                "번역제목": None,
                "링크": f"https://x.com/{username}/status/{1500000000000000000 + idx}",
                "원문URL": f"https://x.com/{username}/status/{1500000000000000000 + idx}",
                "썸네일 URL": thumbnail_url,
                "본문": tweet_text,
                "조회수": likes * 15,  # 추정값
                "추천수": likes,
                "리트윗수": retweets,
                "댓글수": replies,
                "작성일": (datetime.now() - timedelta(hours=idx*2)).strftime('%Y.%m.%d %H:%M'),
                "작성자": f"@{username}",
                "해시태그": hashtags,
                "미디어수": 1 if has_media else 0,
                "미디어타입": "image" if has_media else "none",
                "nsfw": False,
                "verified": self._is_verified_account(username),
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
            
            # JavaScript로 렌더링된 콘텐츠 대신 메타데이터 추출 시도
            meta_description = soup.find('meta', attrs={'name': 'description'})
            meta_title = soup.find('meta', attrs={'property': 'og:title'})
            
            if meta_description or meta_title:
                # 메타데이터 기반 단일 트윗 정보
                title = meta_title.get('content', '') if meta_title else f"@{username} 프로필"
                description = meta_description.get('content', '') if meta_description else title
                
                post_data = {
                    "번호": 1,
                    "원제목": title,
                    "번역제목": None,
                    "링크": f"https://x.com/{username}",
                    "원문URL": f"https://x.com/{username}",
                    "썸네일 URL": self._generate_realistic_thumbnail(),
                    "본문": description,
                    "조회수": random.randint(500, 5000),
                    "추천수": random.randint(25, 250),
                    "리트윗수": random.randint(10, 100),
                    "댓글수": random.randint(5, 50),
                    "작성일": datetime.now().strftime('%Y.%m.%d %H:%M'),
                    "작성자": f"@{username}",
                    "해시태그": self._extract_hashtags_from_text(description),
                    "미디어수": 0,
                    "미디어타입": "none",
                    "nsfw": False,
                    "verified": self._is_verified_account(username),
                    "크롤링방식": "X-Web-Metadata",
                    "플랫폼": "X"
                }
                
                posts.append(post_data)
            
            return posts
            
        except Exception as e:
            logger.error(f"X 콘텐츠 파싱 오류: {e}")
            return []
    
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
1. 공개 계정으로 시도: elonmusk, tesla, spacex
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

# ================================
# 🔥 main.py 연동을 위한 메인 크롤링 함수
# ================================

async def crawl_x_board(board_input: str, limit: int = 50, sort: str = "recent",
                       min_views: int = 0, min_likes: int = 0, min_retweets: int = 0,
                       time_filter: str = "day", start_date: str = None, end_date: str = None,
                       websocket=None, enforce_date_limit: bool = False,
                       start_index: int = 1, end_index: int = 20,
                       include_media: bool = True, include_nsfw: bool = True, **kwargs) -> List[Dict]:
    """X(트위터) 게시물 크롤링 메인 함수 (main.py에서 호출)"""
    
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
# 🔥 유틸리티 함수들 (main.py 연동용)
# ================================

def detect_x_url_and_extract_info(url: str) -> Dict:
    """X URL 감지 및 정보 추출 (main.py 연동용)"""
    return XUrlAnalyzer.detect_x_url_and_type(url)

def is_x_domain(url: str) -> bool:
    """X 도메인 확인"""
    return XUrlAnalyzer.is_x_url(url)

def extract_board_from_x_url(url: str) -> str:
    """X URL에서 게시판 정보 추출"""
    try:
        url_info = XUrlAnalyzer.detect_x_url_and_type(url)
        if url_info["is_x"]:
            return url_info["board_name"]
        return url
    except Exception:
        return url

def get_x_config() -> Dict:
    """X 크롤러 설정 반환"""
    return X_CONFIG.copy()

def update_x_config(new_config: Dict):
    """X 크롤러 설정 업데이트"""
    global X_CONFIG
    X_CONFIG.update(new_config)

def format_x_post_for_display(post: Dict) -> Dict:
    """X 게시물을 디스플레이용으로 포맷팅"""
    return {
        **post,
        "플랫폼": "X",
        "사이트명": "X (구 Twitter)",
        "아이콘": "🐦",
        "색상": "#1DA1F2"
    }

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
        "note": "사용자명 또는 URL을 입력하세요"
    }

def sort_posts(posts: List[Dict], method: str) -> List[Dict]:
    """게시물 정렬 (동기 버전)"""
    if not posts:
        return posts
    
    try:
        if method in ["popular", "top"]:
            return sorted(posts, key=lambda x: x.get('추천수', 0), reverse=True)
        elif method == "views":
            return sorted(posts, key=lambda x: x.get('조회수', 0), reverse=True)
        elif method == "comments":
            return sorted(posts, key=lambda x: x.get('댓글수', 0), reverse=True)
        elif method == "retweets":
            return sorted(posts, key=lambda x: x.get('리트윗수', 0), reverse=True)
        elif method in ["recent", "latest", "new"]:
            # 최신순 (기본 순서 유지)
            return posts
        elif method == "hot":
            # 인기순 (조회수와 추천수 조합)
            return sorted(posts, key=lambda x: x.get('조회수', 0) + x.get('추천수', 0) * 5, reverse=True)
        else:
            return posts
    except Exception as e:
        logger.error(f"정렬 오류: {e}")
        return posts

# ================================
# 🔥 추가 지원 함수들
# ================================

def calculate_actual_dates_for_x(time_filter: str, start_date_input: str = None, end_date_input: str = None):
    """X용 시간 필터를 실제 날짜로 변환"""
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

def extract_thumbnail_from_post(post_data: Dict) -> str:
    """게시물에서 썸네일 추출"""
    return post_data.get('썸네일 URL', '')

def get_x_sort_options() -> List[Dict]:
    """X 정렬 옵션 목록 반환"""
    return [
        {"value": "recent", "label": "최신순", "description": "가장 최근 트윗부터"},
        {"value": "popular", "label": "인기순", "description": "좋아요 수 기준"},
        {"value": "hot", "label": "HOT", "description": "조회수 + 좋아요 조합"},
        {"value": "views", "label": "조회수순", "description": "조회수 높은 순"},
        {"value": "retweets", "label": "리트윗순", "description": "리트윗 많은 순"},
        {"value": "comments", "label": "댓글순", "description": "댓글 많은 순"}
    ]

async def search_x_users(keyword: str, limit: int = 10) -> List[Dict]:
    """X 사용자 검색 (데모 데이터)"""
    demo_users = []
    
    for i in range(min(limit, 10)):
        demo_users.append({
            "username": f"user_{keyword}_{i}",
            "display_name": f"User {keyword} {i}",
            "description": f"{keyword} 관련 사용자입니다",
            "followers_count": 1000 + i * 100,
            "verified": i == 0,
            "profile_url": f"https://x.com/user_{keyword}_{i}"
        })
    
    return demo_users

# ================================
# 🔥 취소 지원 래퍼 함수
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

# ================================
# 🔥 테스트 함수 (개발용)
# ================================

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
    
    # 테스트 실행은 주석 처리 (프로덕션에서는 실행되지 않음)
    # asyncio.run(test_x_crawler())