import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime, timedelta
from urllib.parse import urljoin, urlparse, quote
import logging
from typing import List, Dict, Optional, Tuple, Union
import asyncio
import json
from dataclasses import dataclass, field
import concurrent.futures
from collections import Counter
import time
from functools import lru_cache
import hashlib

# aiohttp 임포트를 try-except로 보호
try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False
    aiohttp = None
    logging.warning("aiohttp 라이브러리가 설치되지 않았습니다. pip install aiohttp로 설치하세요.")

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ================================
# 🔥 확장된 Lemmy 설정 및 상수
# ================================

# 안정적인 인스턴스 우선순위
STABILITY_TIER = {
    # Tier 1: 가장 안정적 (우선 시도)
    'tier1': ['lemmy.ml', 'lemmy.world', 'beehaw.org'],
    # Tier 2: 안정적 
    'tier2': ['sh.itjust.works', 'lemm.ee', 'programming.dev'],
    # Tier 3: 보통
    'tier3': ['lemmy.one', 'feddit.de', 'reddthat.com', 'sopuli.xyz']
}

# 📡 알려진 Lemmy 인스턴스 (확장됨)
KNOWN_LEMMY_INSTANCES = {
    # 메이저 인스턴스
    'lemmy.world': {'users': 50000, 'type': 'general', 'region': 'US'},
    'lemmy.ml': {'users': 30000, 'type': 'general', 'region': 'EU'},
    'beehaw.org': {'users': 12000, 'type': 'community', 'region': 'US'},
    'sh.itjust.works': {'users': 15000, 'type': 'tech', 'region': 'CA'},
    'lemmy.one': {'users': 8000, 'type': 'general', 'region': 'US'},
    
    # 지역별 인스턴스
    'feddit.de': {'users': 10000, 'type': 'regional', 'region': 'DE'},
    'feddit.uk': {'users': 5000, 'type': 'regional', 'region': 'UK'},
    'lemmy.ca': {'users': 4000, 'type': 'regional', 'region': 'CA'},
    'aussie.zone': {'users': 3000, 'type': 'regional', 'region': 'AU'},
    'feddit.it': {'users': 2000, 'type': 'regional', 'region': 'IT'},
    'feddit.nl': {'users': 2500, 'type': 'regional', 'region': 'NL'},
    
    # 특화 인스턴스
    'programming.dev': {'users': 8000, 'type': 'tech', 'region': 'US'},
    'discuss.tchncs.de': {'users': 6000, 'type': 'tech', 'region': 'DE'},
    'sopuli.xyz': {'users': 4000, 'type': 'general', 'region': 'FI'},
    'lemm.ee': {'users': 7000, 'type': 'general', 'region': 'EE'},
    'slrpnk.net': {'users': 3000, 'type': 'climate', 'region': 'US'},
    'lemmy.zip': {'users': 2000, 'type': 'general', 'region': 'US'},
    'midwest.social': {'users': 1500, 'type': 'regional', 'region': 'US'},
    'reddthat.com': {'users': 5000, 'type': 'general', 'region': 'CA'},
    'lemmy.dbzer0.com': {'users': 4000, 'type': 'piracy', 'region': 'US'},
    'startrek.website': {'users': 2000, 'type': 'fandom', 'region': 'US'},
    'lemmy.blahaj.zone': {'users': 3000, 'type': 'lgbtq', 'region': 'US'},
    'hexbear.net': {'users': 8000, 'type': 'leftist', 'region': 'US'},
    'lemmygrad.ml': {'users': 4000, 'type': 'leftist', 'region': 'ML'},
    'exploding-heads.com': {'users': 1000, 'type': 'rightist', 'region': 'US'},
    'lemmy.fmhy.ml': {'users': 3000, 'type': 'piracy', 'region': 'ML'},
    'burggit.moe': {'users': 1000, 'type': 'anime', 'region': 'US'},
    'ani.social': {'users': 2000, 'type': 'anime', 'region': 'US'},
    'ttrpg.network': {'users': 1500, 'type': 'gaming', 'region': 'US'},
    'pathfinder.social': {'users': 800, 'type': 'gaming', 'region': 'US'},
    'lemmy.studio': {'users': 1200, 'type': 'creative', 'region': 'US'},
    'mander.xyz': {'users': 2000, 'type': 'science', 'region': 'US'},
    'lemmy.eco.br': {'users': 1000, 'type': 'regional', 'region': 'BR'},
    'jlai.lu': {'users': 1500, 'type': 'regional', 'region': 'FR'},
    'lemmy.pt': {'users': 800, 'type': 'regional', 'region': 'PT'}
}

# ================================
# 🔥 기획서 기반 도메인 패턴 추가
# ================================

LEMMY_DOMAIN_PATTERNS = [
    # 1) lemmy.*
    r'^(?:[\w-]+\.)?lemmy\.[a-z]{2,}$',
    
    # 2) feddit.*
    r'^(?:[\w-]+\.)?feddit\.[a-z]{2,}$',
    
    # 3) beehaw.org
    r'^beehaw\.org$',
    
    # 4) social/zone/network TLD
    r'^[\w-]+\.(?:social|zone|network)$',
    
    # 5) dev/xyz/net/org TLD
    r'^[\w-]+\.(?:dev|xyz|net|org)$',
    
    # 6) 국가별 TLD
    r'^[\w-]+\.(?:ca|de|it|nl|uk|pt|br|lu|ee|cc|my)$',
    
    # 7) 기타 고정 도메인
    r'^(?:sh\.itjust\.works|lemm\.ee|sopuli\.xyz)$',
    
    # 8) .onion 페더레이션
    r'^(?:[\w-]+)\.onion$',

]

# 컴파일된 정규표현식 캐싱 (성능 최적화)
_compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in LEMMY_DOMAIN_PATTERNS]

# 🎯 Lemmy 특화 설정 (향상됨)
LEMMY_CONFIG = {
    'api_timeout': 12, 
    'rss_timeout': 8, 
    'html_timeout': 15,
    'max_pages': 8,    
    'max_concurrent': 3,
    'retry_count': 2, 
    'retry_delay': 1.5, 
    'rate_limit_delay': 1.0,
    'user_agent': 'LemmyCrawler/2.0 (Enhanced Community Crawler)',
    'cache_ttl': 240,
}

# 🔥 Lemmy API 엔드포인트 매핑
LEMMY_API_ENDPOINTS = {
    'posts': '/api/v3/post/list',
    'communities': '/api/v3/community/list',
    'search': '/api/v3/search',
    'site': '/api/v3/site',
    'nodeinfo': '/.well-known/nodeinfo',
    'feeds': {
        'all': '/feeds/all.xml',
        'local': '/feeds/local.xml',
        'community': '/feeds/c/{community}.xml'
    }
}

# 🚀 Lemmy 시간 필터 매핑 추가
LEMMY_TIME_FILTER_MAPPING = {
    'hour': 'TopHour',
    'day': 'TopDay',
    'week': 'TopWeek',
    'month': 'TopMonth',
    'year': 'TopYear',
    'all': 'TopAll'
}

# 🎨 Lemmy 정렬 방식 매핑 (확장됨)
LEMMY_SORT_MAPPING = {
    'hot': 'Hot',
    'popular': 'TopAll',
    'top': 'TopAll',
    'topall': 'TopAll',
    'topday': 'TopDay',
    'topweek': 'TopWeek',
    'topmonth': 'TopMonth',
    'topyear': 'TopYear',
    'new': 'New',
    'recent': 'New',
    'active': 'Active',
    'comments': 'MostComments',
    'mostcomments': 'MostComments',
    'newcomments': 'NewComments',
    'old': 'Old',
    'scaled': 'Scaled',
    'controversial': 'Controversial'
}

# 📊 인기 커뮤니티 템플릿
POPULAR_COMMUNITIES = {
    'technology': ['technology', 'tech', 'programming', 'linux', 'opensource'],
    'news': ['worldnews', 'news', 'globalnews', 'politics'],
    'gaming': ['gaming', 'games', 'pcgaming', 'nintendo', 'playstation'],
    'science': ['science', 'askscience', 'space', 'physics'],
    'entertainment': ['movies', 'television', 'music', 'books'],
    'lifestyle': ['cooking', 'food', 'fitness', 'travel'],
    'creative': ['art', 'photography', 'writing', 'diy'],
    'social': ['asklemmy', 'casualconversation', 'showerthoughts'],
    'memes': ['memes', 'dankmemes', 'funny'],
    'learning': ['todayilearned', 'explainlikeimfive', 'lifeprotips']
}

# ================================
# 🔥 향상된 데이터 클래스
# ================================

@dataclass
class LemmyInstance:
    """Lemmy 인스턴스 정보 (확장됨)"""
    domain: str
    name: str
    description: str = ""
    users: int = 0
    communities: int = 0
    posts: int = 0
    comments: int = 0
    version: str = ""
    is_nsfw: bool = False
    registration_open: bool = True
    federation_enabled: bool = True
    region: str = ""
    type: str = "general"  # general, tech, regional, etc.
    status: str = "online"  # online, offline, slow
    response_time: float = 0.0
    last_checked: datetime = field(default_factory=datetime.now)
    

@dataclass
class LemmyCommunity:
    """Lemmy 커뮤니티 정보 (확장됨)"""
    name: str
    display_name: str
    description: str
    subscribers: int = 0
    posts: int = 0
    comments: int = 0
    url: str = ""
    instance: str = ""
    nsfw: bool = False
    removed: bool = False
    posting_restricted: bool = False
    icon: str = ""
    banner: str = ""
    created: datetime = field(default_factory=datetime.now)
    last_active: datetime = field(default_factory=datetime.now)

@dataclass
class LemmyPost:
    """Lemmy 게시물 정보"""
    id: int
    title: str
    url: str = ""
    body: str = ""
    score: int = 0
    upvotes: int = 0
    downvotes: int = 0
    comments: int = 0
    author: str = ""
    community: str = ""
    instance: str = ""
    published: datetime = field(default_factory=datetime.now)
    updated: datetime = field(default_factory=datetime.now)
    nsfw: bool = False
    locked: bool = False
    stickied: bool = False
    featured: bool = False
    thumbnail_url: str = ""
    embed_title: str = ""
    embed_description: str = ""

# ================================
# 🔥 고급 캐싱 시스템
# ================================

class LemmyCache:
    """Lemmy 전용 캐싱 시스템"""
    
    def __init__(self, ttl: int = 300):
        self.cache = {}
        self.ttl = ttl
        self.failed_instances = set()  # 실패한 인스턴스 추적
        self.instance_success_time = {}  # 마지막 성공 시간
    
    def _generate_key(self, *args, **kwargs) -> str:
        """캐시 키 생성"""
        key_data = str(args) + str(sorted(kwargs.items()))
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def is_instance_reliable(self, domain: str) -> bool:
        """인스턴스 신뢰성 확인 (캐시 기반)"""
        if domain in self.failed_instances:
            last_success = self.instance_success_time.get(domain)
            if last_success and time.time() - last_success < self.ttl:
                return False
        return True

    def mark_instance_failed(self, domain: str):
        """인스턴스를 실패로 마킹 (캐시 기반)"""
        self.failed_instances.add(domain)
        logger.warning(f"[Cache] 인스턴스 실패로 마킹: {domain}")

    def mark_instance_success(self, domain: str):
        """인스턴스를 성공으로 복구 (캐시 기반)"""
        self.failed_instances.discard(domain)
        self.instance_success_time[domain] = time.time()
        logger.info(f"[Cache] 인스턴스 성공으로 복구: {domain}")

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
# 🔥 향상된 인스턴스 관리자
# ================================

class EnhancedLemmyInstanceManager:
    """향상된 Lemmy 인스턴스 관리자"""
    
    def __init__(self):
        self.instances = {}
        self.cache = LemmyCache(ttl=600)  # 10분 캐시
        self.session = None
        if AIOHTTP_AVAILABLE:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(
                    total=LEMMY_CONFIG['api_timeout'],
                    connect=3,  # 🔥 추가: 연결 타임아웃
                    sock_read=5  # 🔥 추가: 읽기 타임아웃
                ),
                headers={'User-Agent': LEMMY_CONFIG['user_agent']},
                connector=aiohttp.TCPConnector(
                    limit=10,           # 🔥 추가: 전체 연결 수 제한
                    limit_per_host=5    # 🔥 추가: 호스트당 연결 수 제한
                )
            )
    
    async def get_best_instance_for_community(self, community_name: str) -> str:
        """커뮤니티에 가장 적합한 안정적인 인스턴스 선택"""
        # 1. 커뮤니티별 권장 인스턴스 확인
        community_preferences = {
            'asklemmy': ['lemmy.ml', 'lemmy.world'],
            'technology': ['lemmy.world', 'programming.dev', 'lemmy.ml'],
            'programming': ['programming.dev', 'lemmy.ml', 'lemmy.world'],
            'worldnews': ['lemmy.ml', 'lemmy.world'],
            'linux': ['lemmy.ml', 'programming.dev'],
            'privacy': ['lemmy.ml', 'beehaw.org'],
        }
        
        if community_name.lower() in community_preferences:
            for instance in community_preferences[community_name.lower()]:
                if self.cache.is_instance_reliable(instance):
                    if await self._quick_health_check(instance):
                        return instance
        
        # 2. Tier별로 안정적인 인스턴스 시도
        for tier in ['tier1', 'tier2', 'tier3']:
            for instance in STABILITY_TIER[tier]:
                if self.cache.is_instance_reliable(instance):
                    if await self._quick_health_check(instance):
                        return instance
        
        # 3. 기본값
        return 'lemmy.ml'
    
    async def _quick_health_check(self, domain: str) -> bool:
        """빠른 헬스체크 (5초 이내)"""
        if not AIOHTTP_AVAILABLE:
            return True  # aiohttp 없으면 기본적으로 통과
            
        try:
            # 🔥 타임아웃 단축 및 재시도 로직
            timeout = aiohttp.ClientTimeout(total=5, connect=2)
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                url = f"https://{domain}/api/v3/site"
                
                try:
                    async with session.get(url) as response:
                        is_healthy = response.status in [200, 301, 302]  # 리다이렉트도 OK
                        
                        if is_healthy:
                            self.cache.mark_instance_success(domain)
                            return True
                except asyncio.TimeoutError:
                    logger.debug(f"헬스체크 타임아웃: {domain}")
                except Exception as e:
                    logger.debug(f"헬스체크 오류 {domain}: {e}")
            
            # 🔥 실패해도 완전히 차단하지 않고 경고만
            logger.warning(f"인스턴스 헬스체크 실패하지만 크롤링 시도: {domain}")
            return True  # ← 여기를 True로 변경 (기존: False)
            
        except Exception as e:
            logger.debug(f"헬스체크 예외 {domain}: {e}")
            return True  # 🔥 예외 발생해도 시도
    
    async def get_instance_info(self, domain: str) -> Optional[LemmyInstance]:
        """향상된 인스턴스 정보 수집"""
        if not AIOHTTP_AVAILABLE:
            # aiohttp 없으면 기본 정보 반환
            known_info = KNOWN_LEMMY_INSTANCES.get(domain, {})
            return LemmyInstance(
                domain=domain,
                name=known_info.get('name', domain),
                users=known_info.get('users', 0),
                region=known_info.get('region', ''),
                type=known_info.get('type', 'general')
            )
            
        # 신뢰할 수 없는 인스턴스는 건너뛰기
        if not self.cache.is_instance_reliable(domain):
            logger.debug(f"신뢰할 수 없는 인스턴스 건너뛰기: {domain}")
            return None
        
        # 캐시 확인
        cached = self.cache.get('instance', domain)
        if cached:
            return cached
        
        try:
            start_time = time.time()
            
            # 🔥 더 짧은 타임아웃으로 시도
            instance = await self._get_site_info(domain)
            
            if instance:
                instance.response_time = time.time() - start_time
                instance.last_checked = datetime.now()
                
                # 캐시에 저장
                self.cache.set(instance, 'instance', domain)
                self.cache.mark_instance_success(domain)
                self.instances[domain] = instance
                
                return instance
            else:
                self.cache.mark_instance_failed(domain)
            
        except Exception as e:
            logger.debug(f"인스턴스 정보 수집 실패 ({domain}): {e}")
            self.cache.mark_instance_failed(domain)
        
        return None
    
    async def _get_site_info(self, domain: str) -> Optional[LemmyInstance]:
        """Lemmy Site API로 정보 수집"""
        if not self.session:
            return None
            
        try:
            url = f"https://{domain}/api/v3/site"
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._parse_site_info(domain, data)
        except Exception as e:
            logger.debug(f"Site API 조회 실패 ({domain}): {e}")
        
        return None
    
    def _parse_site_info(self, domain: str, data: Dict) -> LemmyInstance:
        """Site API 데이터 파싱"""
        site_view = data.get('site_view', {})
        site = site_view.get('site', {})
        counts = site_view.get('counts', {})
        
        known_info = KNOWN_LEMMY_INSTANCES.get(domain, {})
        
        return LemmyInstance(
            domain=domain,
            name=site.get('name', domain),
            description=site.get('description', ''),
            users=counts.get('users', 0),
            communities=counts.get('communities', 0),
            posts=counts.get('posts', 0),
            comments=counts.get('comments', 0),
            version=data.get('version', ''),
            is_nsfw=site.get('content_warning', False),
            region=known_info.get('region', ''),
            type=known_info.get('type', 'general')
        )
    
    def is_lemmy_instance(self, domain: str) -> bool:
        """도메인이 Lemmy 인스턴스인지 확인 (기획서 패턴 적용)"""
        domain = domain.lower().strip()
        
        # 1. 알려진 인스턴스 확인 (기존 로직 유지)
        if domain in KNOWN_LEMMY_INSTANCES:
            return True
        
        # 2. 기획서 정규표현식 패턴 확인 (새로 추가)
        for pattern in _compiled_patterns:
            if pattern.match(domain):
                logger.debug(f"Lemmy 패턴 매칭: {domain}")
                return True
        
        return False
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

class LemmyConditionChecker:
    """Lemmy 전용 조건 검사기"""
    
    def __init__(self, min_views: int = 0, min_likes: int = 0, 
                start_date: str = None, end_date: str = None):
        self.min_views = min_views
        self.min_likes = min_likes
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
    
    def check_conditions(self, post: Dict) -> bool:
        """게시물 조건 검사"""
        # 메트릭 검사
        if post.get('조회수', 0) < self.min_views:
            return False
        if post.get('추천수', 0) < self.min_likes:
            return False
        
        # 날짜 검사
        if self.start_dt and self.end_dt:
            post_date = self._extract_post_date(post)
            if post_date:
                if not (self.start_dt <= post_date <= self.end_dt):
                    return False
        
        return True
    
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
# 🔥 고급 커뮤니티 검색기
# ================================

class AdvancedLemmyCommunitySearcher:
    """고급 Lemmy 커뮤니티 검색기"""
    
    def __init__(self, instance_manager: EnhancedLemmyInstanceManager):
        self.instance_manager = instance_manager
        self.cache = LemmyCache(ttl=900)  # 15분 캐시
        self.popular_cache = {}
    
    def resolve_community_url(self, community_input: str) -> Tuple[str, str, str]:
        """커뮤니티 입력을 URL, 커뮤니티명, 인스턴스로 분해 (완전 개선됨)"""
        community_input = community_input.strip()
        
        # 1. 이미 URL인 경우 (완전히 개선된 로직)
        if community_input.startswith('http'):
            parsed = urlparse(community_input)
            instance = parsed.netloc
            
            # Lemmy 인스턴스 검증
            if not self.instance_manager.is_lemmy_instance(instance):
                logger.warning(f"Lemmy 인스턴스가 아닐 수 있음: {instance}")
            
            # 🔥 모든 URL 패턴 감지 로직
            path = parsed.path.strip('/')
            
            # 패턴 1: /c/커뮤니티 형태
            if '/c/' in parsed.path:
                community_name = parsed.path.split('/c/')[1].split('/')[0]
                return community_input, community_name, instance
            
            # 패턴 2: /post/번호 형태 - 게시물 URL에서 커뮤니티 추출 시도
            elif '/post/' in parsed.path:
                # 게시물 URL이지만 인스턴스는 확정적이므로 크롤링 가능
                # 일반적으로 인스턴스의 전체 피드를 가져옴
                return community_input, "all", instance
            
            # 패턴 3: /comment/번호 형태 - 댓글 URL
            elif '/comment/' in parsed.path:
                # 댓글 URL이지만 인스턴스는 확정적
                return community_input, "all", instance
            
            # 패턴 4: /u/사용자 형태 - 사용자 프로필
            elif '/u/' in parsed.path:
                username = parsed.path.split('/u/')[1].split('/')[0]
                # 사용자별 게시물을 가져올 수 있음 (구현 가능)
                return community_input, f"user:{username}", instance
            
            # 패턴 5: /communities 형태 - 커뮤니티 목록
            elif path in ['communities', 'communities/']:
                return community_input, "communities", instance
            
            # 패턴 6: 루트 도메인 (https://instance.com/ 또는 https://instance.com)
            elif not path or path == '/':
                # 인스턴스 메인 페이지 - 전체 피드 크롤링
                return community_input, "local", instance
            
            # 패턴 7: 기타 알 수 없는 경로
            else:
                # 경로가 있지만 알 수 없는 형태 - 시도해볼 가치가 있음
                logger.info(f"알 수 없는 Lemmy URL 패턴이지만 시도: {community_input}")
                return community_input, "unknown", instance
        
        # 2. !community@instance 형태 (기존 로직 유지)
        if community_input.startswith('!') and '@' in community_input:
            parts = community_input[1:].split('@')
            if len(parts) == 2:
                community_name, instance = parts
                if self.instance_manager.is_lemmy_instance(instance):
                    url = f"https://{instance}/c/{community_name}"
                    return url, community_name, instance
                else:
                    logger.warning(f"Lemmy 인스턴스가 아닐 수 있음: {instance}")
        
        # 3. community@instance 형태 (기존 로직 유지)
        if '@' in community_input and not community_input.startswith('http'):
            parts = community_input.split('@')
            if len(parts) == 2:
                community_name, instance = parts
                if self.instance_manager.is_lemmy_instance(instance):
                    url = f"https://{instance}/c/{community_name}"
                    return url, community_name, instance
                else:
                    logger.info(f"알려지지 않은 도메인이지만 시도: {instance}")
                    url = f"https://{instance}/c/{community_name}"
                    return url, community_name, instance
        
        # 4. 커뮤니티 이름만 있는 경우 (기존 로직 유지)
        if '/' not in community_input and '.' not in community_input:
            community_name = community_input
            instance = "lemmy.world"
            url = f"https://{instance}/c/{community_name}"
            return url, community_name, instance
        
        # 5. 도메인만 입력된 경우 (개선됨)
        if '.' in community_input and '/' not in community_input and '@' not in community_input:
            if self.instance_manager.is_lemmy_instance(community_input):
                instance = community_input
                url = f"https://{instance}"
                return url, "local", instance  # 🔥 "local"로 명확히 지정
        
        # 기본값
        return community_input, "", ""
# ================================
# 🔥 향상된 Lemmy 크롤러
# ================================

class AdvancedLemmyCrawler:
    """향상된 Lemmy 전용 크롤러"""
    
    def __init__(self):
        self.instance_manager = EnhancedLemmyInstanceManager()
        self.community_searcher = AdvancedLemmyCommunitySearcher(self.instance_manager)
        self.cache = LemmyCache(ttl=LEMMY_CONFIG['cache_ttl'])
        self.rate_limiter = {}  # 인스턴스별 레이트 리미터
    
    async def crawl_lemmy_community(self, community_url: str, limit: int = 50, 
                                sort: str = "Hot", min_views: int = 0, 
                                min_likes: int = 0, start_date: str = None, 
                                end_date: str = None, websocket=None, 
                                enforce_date_limit: bool = False,
                                time_filter: str = "day") -> List[Dict]:
        """향상된 에러 처리가 포함된 Lemmy 크롤링"""
        start_time = time.time()
        
        try:
            logger.info(f"향상된 Lemmy 크롤링 시작: {community_url}")
            
            # 🔥 입력 검증 강화
            if not community_url or len(community_url.strip()) < 2:
                raise Exception("올바른 Lemmy 커뮤니티를 입력해주세요. 예: technology@lemmy.world")
            
            # URL 파싱 및 정규화
            url, community_name, instance = self.community_searcher.resolve_community_url(community_url)
            
            if not community_name or not instance:
                # 자동 보정 시도
                if '@' not in community_url and '.' not in community_url:
                    corrected_url = f"{community_url}@lemmy.world"
                    url, community_name, instance = self.community_searcher.resolve_community_url(corrected_url)
                else:
                    raise Exception(f"올바르지 않은 Lemmy 커뮤니티 형식입니다: {community_url}\n예시: technology@lemmy.world")
            
            # 🔥 더 유연한 인스턴스 상태 확인
            instance_info = await self.instance_manager.get_instance_info(instance)
            if not instance_info:
                logger.warning(f"인스턴스 정보를 가져올 수 없지만 크롤링을 계속 시도합니다: {instance}")
                instance_info = type('obj', (object,), {
                    'name': instance,
                    'domain': instance,
                    'users': 0,
                    'status': 'unknown',
                    'region': '',
                    'type': 'general'
                })()
            
            await self._apply_rate_limit(instance)
            
            # 🔥 여러 방법으로 시도하는 fallback 체인
            posts = []
            attempted_methods = []
            
            try:
                # 방법 1: 향상된 API 크롤링
                posts = await self._try_api_crawling_with_fallback(
                    url, community_name, instance, limit, sort, time_filter, websocket
                )
                attempted_methods.append("API")
                
            except Exception as api_error:
                logger.debug(f"API 크롤링 실패: {api_error}")
                attempted_methods.append("API(실패)")
            
            if not posts:
                try:
                    # 방법 2: RSS 크롤링
                    posts = await self._crawl_via_enhanced_rss(url, community_name, instance, limit)
                    attempted_methods.append("RSS")
                    
                except Exception as rss_error:
                    logger.debug(f"RSS 크롤링 실패: {rss_error}")
                    attempted_methods.append("RSS(실패)")
            
            if not posts:
                try:
                    # 방법 3: HTML 크롤링
                    posts = await self._crawl_via_enhanced_html(url, instance, limit)
                    attempted_methods.append("HTML")
                    
                except Exception as html_error:
                    logger.debug(f"HTML 크롤링 실패: {html_error}")
                    attempted_methods.append("HTML(실패)")
            
            # 🔥 더 자세한 에러 메시지 제공
            if not posts:
                error_details = f"""
Lemmy 커뮤니티 '{community_name}@{instance}'에서 데이터를 가져올 수 없습니다.

시도한 방법들: {', '.join(attempted_methods)}

가능한 해결책:
1. 커뮤니티 이름 확인:
• technology@lemmy.world ✓
• asklemmy@lemmy.ml ✓
• programming@programming.dev ✓

2. 다른 인스턴스 시도:
• {community_name}@lemmy.ml
• {community_name}@beehaw.org
• {community_name}@sh.itjust.works

3. 잠시 후 다시 시도 (인스턴스가 일시적으로 불안정할 수 있음)

4. 전체 URL 형태로 시도:
• https://{instance}/c/{community_name}
                """
                
                raise Exception(error_details.strip())
            
            # 필터링 적용
            if min_views > 0 or min_likes > 0:
                posts = await self._apply_metric_filters(posts, min_views, min_likes)
            
            if start_date and end_date:
                posts = await self._apply_exact_date_filter(posts, start_date, end_date)
            
            # 메타데이터 보강
            enhanced_posts = await self._enhance_post_metadata(posts, instance_info)
            
            logger.info(f"Lemmy 크롤링 완료: {len(enhanced_posts)}개 게시물")
            return enhanced_posts
            
        except Exception as e:
            logger.error(f"Lemmy 크롤링 오류: {e}")
            raise

    async def _try_api_crawling_with_fallback(self, url: str, community_name: str, 
                                            instance: str, limit: int, sort: str,
                                            time_filter: str, websocket=None) -> List[Dict]:
        """여러 API 엔드포인트를 시도하는 fallback 크롤링"""
        
        if not AIOHTTP_AVAILABLE or not self.instance_manager.session:
            return []
        
        # 🔥 여러 API 엔드포인트 시도
        api_attempts = [
            # 1. 커뮤니티별 게시물 조회
            {
                'url': f"https://{instance}/api/v3/post/list",
                'params': {
                    'limit': min(limit, 50),
                    'sort': LEMMY_SORT_MAPPING.get(sort.lower(), sort),
                    'type_': 'All',
                    'community_name': community_name
                }
            },
            # 2. 전체 게시물에서 커뮤니티 필터링
            {
                'url': f"https://{instance}/api/v3/post/list",
                'params': {
                    'limit': min(limit * 2, 100),
                    'sort': LEMMY_SORT_MAPPING.get(sort.lower(), sort),
                    'type_': 'Local'
                }
            },
            # 3. 검색 API 사용
            {
                'url': f"https://{instance}/api/v3/search",
                'params': {
                    'q': community_name,
                    'type_': 'Posts',
                    'sort': LEMMY_SORT_MAPPING.get(sort.lower(), sort),
                    'limit': min(limit, 20)
                }
            }
        ]
        
        for attempt_idx, attempt in enumerate(api_attempts):
            try:
                async with self.instance_manager.session.get(
                    attempt['url'], 
                    params=attempt['params'],
                    timeout=aiohttp.ClientTimeout(total=20)  # 더 긴 타임아웃
                ) as response:
                    
                    if response.status == 200:
                        data = await response.json()
                        
                        if attempt['url'].endswith('/search'):
                            # 검색 API 응답 처리
                            posts = self._parse_search_api_response(data, instance, community_name)
                        else:
                            # 일반 API 응답 처리
                            posts = self._parse_enhanced_api_response(data, instance)
                            
                            # 전체 게시물에서 커뮤니티 필터링
                            if attempt_idx == 1:  # 두 번째 시도인 경우
                                posts = [p for p in posts if community_name.lower() in p.get('커뮤니티', '').lower()]
                        
                        if posts:
                            logger.info(f"API 시도 {attempt_idx + 1} 성공: {len(posts)}개 게시물")
                            return posts[:limit]
                        
                    else:
                        logger.debug(f"API 시도 {attempt_idx + 1} 실패: HTTP {response.status}")
                        
            except asyncio.TimeoutError:
                logger.debug(f"API 시도 {attempt_idx + 1} 타임아웃")
            except Exception as e:
                logger.debug(f"API 시도 {attempt_idx + 1} 오류: {e}")
        
        return []
    
    def _parse_enhanced_api_response(self, data: Dict, instance: str) -> List[Dict]:
        """향상된 API 응답 파싱"""
        posts = []
        
        try:
            post_list = data.get('posts', [])
            
            for idx, item in enumerate(post_list):
                try:
                    post_data = item.get('post', {})
                    counts = item.get('counts', {})
                    creator = item.get('creator', {})
                    community = item.get('community', {})
                    
                    # 기본 정보
                    title = post_data.get('name', f'Post {idx + 1}')
                    body = post_data.get('body', '')
                    url = post_data.get('ap_id', post_data.get('url', ''))
                    
                    # 통계 정보
                    score = counts.get('score', 0)
                    upvotes = counts.get('upvotes', 0)
                    downvotes = counts.get('downvotes', 0)
                    comments = counts.get('comments', 0)
                    
                    # 메타 정보
                    author = creator.get('name', '익명')
                    community_name = community.get('name', '')
                    published = post_data.get('published', '')
                    
                    # 썸네일 및 임베드 정보
                    thumbnail_url = post_data.get('thumbnail_url', '')
                    embed_title = post_data.get('embed_title', '')
                    embed_description = post_data.get('embed_description', '')
                    
                    # 플래그
                    nsfw = post_data.get('nsfw', False)
                    locked = post_data.get('locked', False)
                    featured = post_data.get('featured_community', False) or post_data.get('featured_local', False)
                    
                    posts.append({
                        "번호": idx + 1,
                        "원제목": title,
                        "번역제목": None,
                        "링크": url,
                        "원문URL": url,
                        "썸네일 URL": thumbnail_url,
                        "본문": body[:200] + "..." if len(body) > 200 else body,
                        "조회수": comments,  # Lemmy는 조회수 대신 댓글수 사용
                        "추천수": score,
                        "upvotes": upvotes,
                        "downvotes": downvotes,
                        "댓글수": comments,
                        "작성일": self._format_lemmy_date(published),
                        "작성자": author,
                        "커뮤니티": community_name,
                        "인스턴스": instance,
                        "nsfw": nsfw,
                        "잠김": locked,
                        "추천됨": featured,
                        "임베드제목": embed_title,
                        "임베드설명": embed_description,
                        "크롤링방식": "Lemmy-Enhanced-API"
                    })
                    
                except Exception as e:
                    logger.debug(f"API 게시물 파싱 오류: {e}")
                    continue
            
            return posts
            
        except Exception as e:
            logger.error(f"API 응답 파싱 오류: {e}")
            return []
    
    def _parse_search_api_response(self, data: Dict, instance: str, community_name: str) -> List[Dict]:
        """검색 API 응답 파싱"""
        posts = []
        
        try:
            post_list = data.get('posts', [])
            
            for idx, item in enumerate(post_list):
                try:
                    post_data = item.get('post', {})
                    counts = item.get('counts', {})
                    creator = item.get('creator', {})
                    community = item.get('community', {})
                    
                    # 커뮤니티 이름 확인
                    if community_name.lower() not in community.get('name', '').lower():
                        continue
                    
                    # 기본 정보
                    title = post_data.get('name', f'Search Result {idx + 1}')
                    body = post_data.get('body', '')
                    url = post_data.get('ap_id', post_data.get('url', ''))
                    
                    posts.append({
                        "번호": idx + 1,
                        "원제목": title,
                        "번역제목": None,
                        "링크": url,
                        "원문URL": url,
                        "본문": body[:200] + "..." if len(body) > 200 else body,
                        "조회수": counts.get('comments', 0),
                        "추천수": counts.get('score', 0),
                        "댓글수": counts.get('comments', 0),
                        "작성일": self._format_lemmy_date(post_data.get('published', '')),
                        "작성자": creator.get('name', '익명'),
                        "커뮤니티": community.get('name', ''),
                        "인스턴스": instance,
                        "크롤링방식": "Lemmy-Search-API"
                    })
                    
                except Exception as e:
                    logger.debug(f"검색 결과 파싱 오류: {e}")
                    continue
            
            return posts
            
        except Exception as e:
            logger.error(f"검색 API 응답 파싱 오류: {e}")
            return []
    
    async def _apply_exact_date_filter(self, posts: List[Dict], start_date: str, end_date: str) -> List[Dict]:
        """정확한 날짜 필터링"""
        if not start_date or not end_date:
            return posts
            
        try:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            end_dt = end_dt.replace(hour=23, minute=59, second=59)
            
            filtered_posts = []
            for post in posts:
                post_date_str = post.get('작성일', '')
                post_date = self._parse_post_date_flexible(post_date_str)  # 🔥 유연한 파싱
                
                if post_date:
                    if start_dt <= post_date <= end_dt:
                        filtered_posts.append(post)
                    else:
                        # 🔥 디버깅을 위한 로그
                        logger.debug(f"날짜 필터 제외: {post_date_str} ({post_date}) not in {start_date}~{end_date}")
                else:
                    # 🔥 날짜 파싱 실패한 게시물도 포함 (너무 엄격하지 않게)
                    logger.debug(f"날짜 파싱 실패로 포함: {post_date_str}")
                    filtered_posts.append(post)
            
            logger.info(f"날짜 필터링: {len(posts)} -> {len(filtered_posts)}개 (제외된 이유 확인 필요)")
            return filtered_posts
            
        except Exception as e:
            logger.error(f"날짜 필터링 오류: {e}")
            return posts  # 🔥 오류시 원본 반환
    
    def _parse_post_date_flexible(self, date_str: str) -> Optional[datetime]:
        """유연한 게시물 날짜 파싱"""
        if not date_str:
            return None
        
        # 🔥 Lemmy 특화 날짜 형식들 시도
        formats = [
            '%Y.%m.%d %H:%M',          # 한국 형식
            '%Y-%m-%d %H:%M',          # 일반 형식
            '%Y.%m.%d',                # 날짜만
            '%Y-%m-%d',                # 날짜만
            '%Y-%m-%dT%H:%M:%SZ',      # ISO with Z
            '%Y-%m-%dT%H:%M:%S.%fZ',   # ISO with microseconds
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str.strip(), fmt)
            except ValueError:
                continue
        
        # 🔥 ISO 형식 특별 처리
        if 'T' in date_str:
            try:
                cleaned = date_str.replace('Z', '+00:00')
                return datetime.fromisoformat(cleaned)
            except Exception:
                pass
        
        logger.debug(f"날짜 파싱 실패: {date_str}")
        return None

    async def _apply_metric_filters(self, posts: List[Dict], min_views: int, min_likes: int) -> List[Dict]:
        """메트릭 필터링 (최소 조회수, 추천수)"""
        if min_views <= 0 and min_likes <= 0:
            return posts
        
        filtered_posts = [
            post for post in posts
            if post.get('조회수', 0) >= min_views and post.get('추천수', 0) >= min_likes
        ]
        
        logger.info(f"메트릭 필터링: {len(posts)} -> {len(filtered_posts)}개")
        return filtered_posts

    async def _crawl_via_enhanced_rss(self, url: str, community_name: str, 
                                    instance: str, limit: int) -> List[Dict]:
        """향상된 RSS 크롤링"""
        if not AIOHTTP_AVAILABLE or not self.instance_manager.session:
            return []
            
        try:
            rss_urls = []
            
            # 커뮤니티별 RSS
            if community_name:
                rss_urls.append(f"https://{instance}/feeds/c/{community_name}.xml")
            
            # 전체 RSS
            rss_urls.extend([
                f"https://{instance}/feeds/all.xml",
                f"https://{instance}/feeds/local.xml"
            ])
            
            for rss_url in rss_urls:
                try:
                    async with self.instance_manager.session.get(rss_url) as response:
                        if response.status == 200:
                            content = await response.text()
                            posts = self._parse_enhanced_rss(content, instance)
                            
                            if posts:
                                logger.info(f"RSS 크롤링 성공: {len(posts)}개 게시물")
                                return posts[:limit]
                                
                except Exception as e:
                    logger.debug(f"RSS URL 실패 ({rss_url}): {e}")
                    continue
                    
        except Exception as e:
            logger.debug(f"RSS 크롤링 실패: {e}")
        
        return []
    
    async def _crawl_via_enhanced_html(self, url: str, instance: str, limit: int) -> List[Dict]:
        """향상된 HTML 크롤링"""
        if not AIOHTTP_AVAILABLE or not self.instance_manager.session:
            return []
            
        try:
            async with self.instance_manager.session.get(url) as response:
                if response.status == 200:
                    content = await response.text()
                    soup = BeautifulSoup(content, 'html.parser')
                    posts = self._parse_enhanced_html(soup, url, instance)
                    
                    if posts:
                        logger.info(f"HTML 크롤링 성공: {len(posts)}개 게시물")
                        return posts[:limit]
                        
        except Exception as e:
            logger.debug(f"HTML 크롤링 실패: {e}")
        
        return []
    
    def _parse_enhanced_rss(self, content: str, instance: str) -> List[Dict]:
        """향상된 RSS 파싱"""
        posts = []
        
        try:
            soup = BeautifulSoup(content, 'xml') or BeautifulSoup(content, 'html.parser')
            items = soup.find_all(['item', 'entry'])
            
            for idx, item in enumerate(items):
                try:
                    # 기본 정보
                    title_elem = item.find('title')
                    link_elem = item.find('link')
                    description_elem = item.find('description') or item.find('summary') or item.find('content')
                    pub_date_elem = item.find('pubDate') or item.find('published') or item.find('updated')
                    author_elem = item.find('author') or item.find('dc:creator')
                    
                    title = title_elem.get_text(strip=True) if title_elem else f'RSS Item {idx + 1}'
                    link = link_elem.get_text(strip=True) if link_elem else ''
                    description = description_elem.get_text(strip=True) if description_elem else ''
                    pub_date = pub_date_elem.get_text(strip=True) if pub_date_elem else ''
                    author = author_elem.get_text(strip=True) if author_elem else 'RSS'
                    
                    # RSS 특화 메타데이터 추출
                    guid = item.find('guid')
                    category = item.find('category')
                    
                    post_id = guid.get_text(strip=True) if guid else f"rss_{idx}"
                    community = category.get_text(strip=True) if category else ""
                    
                    posts.append({
                        "번호": idx + 1,
                        "원제목": title,
                        "번역제목": None,
                        "링크": link,
                        "원문URL": link,
                        "썸네일 URL": None,
                        "본문": description[:200] + "..." if len(description) > 200 else description,
                        "조회수": 0,
                        "추천수": 0,
                        "댓글수": 0,
                        "작성일": self._format_rss_date(pub_date),
                        "작성자": author,
                        "커뮤니티": community,
                        "인스턴스": instance,
                        "게시물ID": post_id,
                        "크롤링방식": "Lemmy-Enhanced-RSS"
                    })
                    
                except Exception as e:
                    logger.debug(f"RSS 항목 파싱 오류: {e}")
                    continue
            
            return posts
            
        except Exception as e:
            logger.error(f"RSS 파싱 오류: {e}")
            return []
    
    def _parse_enhanced_html(self, soup: BeautifulSoup, base_url: str, instance: str) -> List[Dict]:
        """향상된 HTML 파싱"""
        posts = []
        
        try:
            # Lemmy UI 구조에 특화된 선택자들 (확장됨)
            post_selectors = [
                'article.post-listing',
                '.post-listing',
                'div[class*="post-listing"]',
                'article[class*="post"]',
                '.post',
                '.community-link',
                '.post-link',
                'div[data-testid*="post"]',
                'div[role="article"]',
                '.thread-listing',
                '.item[data-post-id]',
                '.lemmy-post',
                '.feed-item'
            ]
            
            found_elements = []
            for selector in post_selectors:
                elements = soup.select(selector)
                if elements:
                    logger.info(f"HTML 선택자 '{selector}'로 {len(elements)}개 요소 발견")
                    found_elements.extend(elements)
                    break  # 첫 번째로 결과가 나온 선택자 사용
            
            for idx, element in enumerate(found_elements[:50]):
                try:
                    post_data = self._extract_enhanced_post_from_element(element, idx, base_url, instance)
                    if post_data:
                        posts.append(post_data)
                except Exception as e:
                    logger.debug(f"HTML 요소 파싱 오류: {e}")
                    continue
            
            return posts
            
        except Exception as e:
            logger.error(f"HTML 파싱 오류: {e}")
            return []
    
    def _extract_enhanced_post_from_element(self, element, idx: int, base_url: str, instance: str) -> Optional[Dict]:
        """향상된 HTML 요소에서 게시물 데이터 추출"""
        try:
            # 제목 추출 (확장된 선택자)
            title_selectors = [
                '.post-title', '.post-name', 'h1', 'h2', 'h3',
                '.title', 'a[href*="/post/"]', '.lemmy-post-title',
                '.post-listing-title', '[data-testid="post-title"]'
            ]
            
            title = ""
            link = ""
            
            for selector in title_selectors:
                title_elem = element.select_one(selector)
                if title_elem:
                    title = title_elem.get_text(strip=True)
                    if title_elem.name == 'a' and title_elem.get('href'):
                        link = urljoin(base_url, title_elem.get('href'))
                    if len(title) > 5:
                        break
            
            if not title:
                return None
            
            # 링크 추출 (제목에서 못 찾은 경우)
            if not link:
                link_selectors = [
                    'a[href*="/post/"]', 'a[href*="/posts/"]',
                    '.post-link', '.lemmy-link', '.permalink'
                ]
                for selector in link_selectors:
                    link_elem = element.select_one(selector)
                    if link_elem and link_elem.get('href'):
                        link = urljoin(base_url, link_elem.get('href'))
                        break
            
            # 메타데이터 추출 (확장됨)
            score = self._extract_score(element)
            comments = self._extract_comments(element)
            author = self._extract_author(element)
            community = self._extract_community(element)
            date_str = self._extract_date(element)
            
            # 추가 메타데이터
            nsfw = self._check_nsfw(element)
            locked = self._check_locked(element)
            featured = self._check_featured(element)
            
            return {
                "번호": idx + 1,
                "원제목": title,
                "번역제목": None,
                "링크": link or base_url,
                "원문URL": link or base_url,
                "썸네일 URL": self._extract_thumbnail(element, base_url),
                "본문": f"Lemmy 게시물: {title}",
                "조회수": comments,  # 댓글수를 조회수로 사용
                "추천수": score,
                "댓글수": comments,
                "작성일": self._format_lemmy_date(date_str),
                "작성자": author,
                "커뮤니티": community,
                "인스턴스": instance,
                "nsfw": nsfw,
                "잠김": locked,
                "추천됨": featured,
                "크롤링방식": "Lemmy-Enhanced-HTML"
            }
            
        except Exception as e:
            logger.debug(f"HTML 요소 데이터 추출 오류: {e}")
            return None
    
    def _extract_score(self, element) -> int:
        """점수 추출 (확장됨)"""
        score_selectors = [
            '.score', '.points', '.upvotes', '.vote-score',
            '.post-score', '.karma', '[data-testid="score"]',
            '.lemmy-score', '.post-rating'
        ]
        
        for selector in score_selectors:
            score_elem = element.select_one(selector)
            if score_elem:
                score_text = score_elem.get_text(strip=True)
                numbers = re.findall(r'-?\d+', score_text)
                if numbers:
                    return int(numbers[0])
        
        return 0
    
    def _extract_comments(self, element) -> int:
        """댓글수 추출 (확장됨)"""
        comment_selectors = [
            '.comments', '.replies', '.comment-count',
            '.reply-count', '[data-testid="comments"]',
            '.lemmy-comments', '.post-comments', '.num-comments'
        ]
        
        for selector in comment_selectors:
            comment_elem = element.select_one(selector)
            if comment_elem:
                comment_text = comment_elem.get_text(strip=True)
                numbers = re.findall(r'\d+', comment_text)
                if numbers:
                    return int(numbers[0])
        
        return 0
    
    def _extract_author(self, element) -> str:
        """작성자 추출 (확장됨)"""
        author_selectors = [
            '.author', '.creator', '.username', '.user',
            '.post-author', '.by-author', '[data-testid="author"]',
            '.lemmy-author', '.posted-by'
        ]
        
        for selector in author_selectors:
            author_elem = element.select_one(selector)
            if author_elem:
                author = author_elem.get_text(strip=True)
                if author and len(author) > 0:
                    return author
        
        return "익명"
    
    def _extract_community(self, element) -> str:
        """커뮤니티 추출"""
        community_selectors = [
            '.community', '.community-name', '.subreddit',
            '.community-link', '[data-testid="community"]',
            '.lemmy-community', '.in-community'
        ]
        
        for selector in community_selectors:
            community_elem = element.select_one(selector)
            if community_elem:
                community = community_elem.get_text(strip=True)
                if community:
                    return community
        
        return ""
    
    def _extract_date(self, element) -> str:
        """날짜 추출 (확장됨)"""
        date_selectors = [
            '.date', '.time', '.timestamp', '.created',
            '.post-date', '.published', '[data-testid="date"]',
            '.lemmy-date', '.posted-time', 'time'
        ]
        
        for selector in date_selectors:
            date_elem = element.select_one(selector)
            if date_elem:
                # datetime 속성 우선 확인
                if date_elem.get('datetime'):
                    return date_elem.get('datetime')
                
                date_text = date_elem.get_text(strip=True)
                if date_text:
                    return date_text
        
        return ""
    
    def _extract_thumbnail(self, element, base_url: str) -> Optional[str]:
        """썸네일 추출 (확장됨)"""
        img_selectors = [
            'img', '.thumbnail', '.post-thumbnail',
            '.lemmy-thumbnail', '[data-testid="thumbnail"]'
        ]
        
        for selector in img_selectors:
            img_elem = element.select_one(selector)
            if img_elem:
                src = (img_elem.get('src') or
                      img_elem.get('data-src') or
                      img_elem.get('data-original'))
                if src:
                    if src.startswith('http'):
                        return src
                    else:
                        return urljoin(base_url, src)
        
        return None
    
    def _check_nsfw(self, element) -> bool:
        """NSFW 여부 확인"""
        nsfw_indicators = [
            '.nsfw', '.adult', '[data-nsfw="true"]',
            '.lemmy-nsfw', '.content-warning'
        ]
        
        for indicator in nsfw_indicators:
            if element.select_one(indicator):
                return True
        
        # 텍스트에서 NSFW 확인
        element_text = element.get_text().lower()
        if 'nsfw' in element_text or 'adult' in element_text:
            return True
        
        return False
    
    def _check_locked(self, element) -> bool:
        """잠김 여부 확인"""
        locked_indicators = [
            '.locked', '.closed', '[data-locked="true"]',
            '.lemmy-locked', '.post-locked'
        ]
        
        for indicator in locked_indicators:
            if element.select_one(indicator):
                return True
        
        return False
    
    def _check_featured(self, element) -> bool:
        """추천 여부 확인"""
        featured_indicators = [
            '.featured', '.pinned', '.sticky', '.stickied',
            '.lemmy-featured', '.post-featured', '[data-featured="true"]'
        ]
        
        for indicator in featured_indicators:
            if element.select_one(indicator):
                return True
        
        return False
    
    async def _apply_rate_limit(self, instance: str):
        """인스턴스별 레이트 리미터 적용"""
        now = time.time()
        if instance in self.rate_limiter:
            last_request = self.rate_limiter[instance]
            elapsed = now - last_request
            if elapsed < LEMMY_CONFIG['rate_limit_delay']:
                await asyncio.sleep(LEMMY_CONFIG['rate_limit_delay'] - elapsed)
        
        self.rate_limiter[instance] = now
    
    def _apply_lemmy_sorting(self, posts: List[Dict], sort: str) -> List[Dict]:
        """Lemmy 특화 정렬 적용"""
        if not posts:
            return posts
        
        try:
            sort_lower = sort.lower()
            
            if sort_lower in ["hot", "active"]:
                # 복합 점수 기반 정렬 (점수 + 댓글 + 시간)
                def hot_score(post):
                    score = post.get('추천수', 0)
                    comments = post.get('댓글수', 0)
                    # 시간 가중치 (최근일수록 높은 점수)
                    try:
                        post_date = self._parse_post_date(post.get('작성일', ''))
                        if post_date:
                            hours_ago = (datetime.now() - post_date).total_seconds() / 3600
                            time_weight = max(0, 1 - (hours_ago / 168))  # 일주일 기준
                        else:
                            time_weight = 0.5
                    except:
                        time_weight = 0.5
                    
                    return (score * 1.0 + comments * 0.5) * (1 + time_weight)
                
                return sorted(posts, key=hot_score, reverse=True)
                
            elif sort_lower in ["top", "topall", "popular"]:
                return sorted(posts, key=lambda x: x.get('추천수', 0), reverse=True)
                
            elif sort_lower in ["new", "recent"]:
                return sorted(posts, key=lambda x: x.get('작성일', ''), reverse=True)
                
            elif sort_lower in ["comments", "mostcomments"]:
                return sorted(posts, key=lambda x: x.get('댓글수', 0), reverse=True)
                
            elif sort_lower == "controversial":
                # 논란의 여지가 있는 게시물 (upvotes와 downvotes 비율)
                def controversial_score(post):
                    upvotes = post.get('upvotes', post.get('추천수', 0))
                    downvotes = post.get('downvotes', 0)
                    total = upvotes + downvotes
                    if total == 0:
                        return 0
                    return min(upvotes, downvotes) * total
                
                return sorted(posts, key=controversial_score, reverse=True)
                
            else:
                return posts
                
        except Exception as e:
            logger.error(f"정렬 오류: {e}")
            return posts
    
    async def _enhance_post_metadata(self, posts: List[Dict], instance_info: LemmyInstance) -> List[Dict]:
        """게시물 메타데이터 보강"""
        for post in posts:
            # 인스턴스 정보 추가
            post['인스턴스정보'] = {
                '이름': instance_info.name,
                '사용자수': instance_info.users,
                '지역': instance_info.region,
                '타입': instance_info.type
            }
            
            # 품질 점수 계산
            post['품질점수'] = self._calculate_post_quality(post)
            
            # 추가 메타데이터
            post['크롤링시간'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            post['플랫폼'] = 'Lemmy'
            
            # URL 정규화
            if post.get('링크') and not post['링크'].startswith('http'):
                post['링크'] = f"https://{instance_info.domain}{post['링크']}"
            
        return posts
    
    def _calculate_post_quality(self, post: Dict) -> float:
        """게시물 품질 점수 계산"""
        score = 0.0
        
        # 제목 품질
        title = post.get('원제목', '')
        if 10 <= len(title) <= 100:
            score += 2.0
        elif 5 <= len(title) <= 200:
            score += 1.0
        
        # 참여도
        upvotes = post.get('추천수', 0)
        comments = post.get('댓글수', 0)
        
        if upvotes > 0:
            score += min(2.0, upvotes / 10)
        if comments > 0:
            score += min(2.0, comments / 5)
        
        # 콘텐츠 유형
        if post.get('썸네일 URL'):
            score += 0.5
        if post.get('본문') and len(post['본문']) > 50:
            score += 1.0
        
        # 메타데이터 완성도
        if post.get('작성자') != '익명':
            score += 0.5
        if post.get('커뮤니티'):
            score += 0.5
        
        return min(10.0, score)
    
    def _format_lemmy_date(self, date_str: str) -> str:
        """Lemmy 날짜 형식 변환 (향상됨)"""
        if not date_str:
            return datetime.now().strftime('%Y.%m.%d')
        
        try:
            # 🔥 ISO 형식 처리 개선
            if 'T' in date_str:
                # Z 또는 +00:00 형태 모두 처리
                cleaned = date_str.replace('Z', '+00:00')
                if not cleaned.endswith(('+', '-')):
                    cleaned += '+00:00'
                dt = datetime.fromisoformat(cleaned.replace('Z', '+00:00'))
                return dt.strftime('%Y.%m.%d %H:%M')
            
            # 🔥 추가: Lemmy 특화 날짜 형식들
            formats = [
                '%Y-%m-%dT%H:%M:%S.%fZ',     # 마이크로초 포함
                '%Y-%m-%dT%H:%M:%SZ',        # 기본 ISO
                '%Y-%m-%d %H:%M:%S',         # 일반 형식
                '%Y.%m.%d %H:%M',            # 한국 형식
            ]
            
            for fmt in formats:
                try:
                    dt = datetime.strptime(date_str, fmt)
                    return dt.strftime('%Y.%m.%d %H:%M')
                except ValueError:
                    continue
                    
            return date_str  # 파싱 실패시 원본 반환
            
        except Exception as e:
            logger.debug(f"날짜 파싱 실패: {date_str} -> {e}")
            return datetime.now().strftime('%Y.%m.%d')
    
    def _format_rss_date(self, date_str: str) -> str:
        """RSS 날짜 형식 변환 (향상됨)"""
        if not date_str:
            return datetime.now().strftime('%Y.%m.%d')
        
        try:
            # 다양한 RSS 날짜 형식 지원
            formats = [
                '%a, %d %b %Y %H:%M:%S %z',
                '%a, %d %b %Y %H:%M:%S %Z',
                '%Y-%m-%dT%H:%M:%S%z',
                '%Y-%m-%dT%H:%M:%SZ',
                '%Y-%m-%d %H:%M:%S',
                '%Y-%m-%d'
            ]
            
            for fmt in formats:
                try:
                    dt = datetime.strptime(date_str.strip(), fmt)
                    return dt.strftime('%Y.%m.%d %H:%M')
                except ValueError:
                    continue
            
            return datetime.now().strftime('%Y.%m.%d')
            
        except Exception:
            return datetime.now().strftime('%Y.%m.%d')
    
    def _parse_post_date(self, date_str: str) -> Optional[datetime]:
        """게시물 날짜 파싱 (향상됨)"""
        if not date_str:
            return None
        
        try:
            # 다양한 형식 시도
            formats = [
                '%Y.%m.%d %H:%M',
                '%Y-%m-%d %H:%M',
                '%Y.%m.%d',
                '%Y-%m-%d',
                '%m.%d %H:%M',
                '%m-%d %H:%M'
            ]
            
            for fmt in formats:
                try:
                    return datetime.strptime(date_str.strip(), fmt)
                except ValueError:
                    continue
            
            # ISO 형식 시도
            if 'T' in date_str:
                return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            
            return None
            
        except Exception:
            return None
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.instance_manager.__aexit__(exc_type, exc_val, exc_tb)

# ================================
# 🔥 메인 크롤링 함수 (향상됨)
# ================================

async def crawl_lemmy_board(community_input: str, limit: int = 50, sort: str = "Hot",
                           min_views: int = 0, min_likes: int = 0, 
                           time_filter: str = "day", start_date: str = None, 
                           end_date: str = None, websocket=None, 
                           enforce_date_limit: bool = False,
                           start_index: int = 1, end_index: int = 20) -> List[Dict]:
    """향상된 Lemmy 커뮤니티 크롤링 - 정확한 범위 지원"""
    
    # aiohttp 가용성 확인
    if not AIOHTTP_AVAILABLE:
        error_msg = "Lemmy 크롤러를 사용할 수 없습니다. aiohttp 라이브러리를 설치하세요: pip install aiohttp"
        logger.error(error_msg)
        raise Exception(error_msg)
    
    async with AdvancedLemmyCrawler() as crawler:
        try:
            logger.info(f"Lemmy 크롤링 시작: {community_input} (범위: {start_index}-{end_index})")
            
            # URL 파싱 및 정규화
            url, community_name, instance = crawler.community_searcher.resolve_community_url(community_input)
            
            if not community_name or not instance:
                if '@' not in community_input and '.' not in community_input:
                    corrected_url = f"{community_input}@lemmy.world"
                    url, community_name, instance = crawler.community_searcher.resolve_community_url(corrected_url)
                else:
                    raise Exception(f"올바르지 않은 Lemmy 커뮤니티 형식: {community_input}")
            
            # 인스턴스 상태 확인
            instance_info = await crawler.instance_manager.get_instance_info(instance)
            if not instance_info:
                logger.warning(f"인스턴스 정보를 가져올 수 없지만 크롤링을 계속 시도합니다: {instance}")
                instance_info = type('obj', (object,), {
                    'name': instance,
                    'domain': instance,
                    'users': 0,
                    'status': 'unknown',
                    'region': '',
                    'type': 'general'
                })()
            
            await crawler._apply_rate_limit(instance)
            
            # 🔥 핵심 개선: 정확한 개수만 크롤링
            if start_date and end_date:
                # 날짜 필터링 모드: 충분한 양 수집 후 필터링
                posts = await crawler.crawl_lemmy_community(
                    community_input, limit * 2, sort, min_views, min_likes,
                    start_date, end_date, websocket, enforce_date_limit, time_filter
                )
                
                # 날짜 필터링 후 범위 적용
                if posts and len(posts) >= end_index:
                    posts = posts[start_index-1:end_index]
                
            else:
                # 🔥 일반 모드: 정확한 범위만 크롤링
                # 약간의 여유를 두고 크롤링 (API 페이지네이션 고려)
                actual_limit = min(end_index + 10, 100)
                
                posts = await crawler.crawl_lemmy_community(
                    community_input, actual_limit, sort, min_views, min_likes,
                    start_date, end_date, websocket, enforce_date_limit, time_filter
                )
                
                # 🔥 정확한 범위로 자르기
                if posts:
                    posts = posts[start_index-1:end_index]
            
            if not posts:
                error_details = f"""
Lemmy 커뮤니티 '{community_name}@{instance}'에서 {start_index}-{end_index}위 게시물을 가져올 수 없습니다.

가능한 원인:
1. 커뮤니티에 게시물이 {end_index}개 미만
2. 설정한 정렬 기준에 맞는 게시물이 부족
3. 인스턴스가 일시적으로 불안정
                """
                raise Exception(error_details.strip())
            
            # 🔥 메타데이터 보강
            enhanced_posts = await crawler._enhance_post_metadata(posts, instance_info)
            
            # 🔥 번호를 start_index부터 정확히 부여
            for idx, post in enumerate(enhanced_posts):
                post['번호'] = start_index + idx
            
            logger.info(f"Lemmy 크롤링 완료: {len(enhanced_posts)}개 게시물 ({start_index}-{start_index+len(enhanced_posts)-1}위)")
            return enhanced_posts
            
        except Exception as e:
            logger.error(f"Lemmy 크롤링 오류: {e}")
            raise

# ================================
# 🔥 레거시 호환성 함수들
# ================================

def resolve_lemmy_community_id(community_input: str) -> str:
    """커뮤니티 입력을 표준 URL로 변환 (동기 버전)"""
    manager = EnhancedLemmyInstanceManager()
    searcher = AdvancedLemmyCommunitySearcher(manager)
    url, _, _ = searcher.resolve_community_url(community_input)
    return url

def filter_posts_by_date(posts: List[dict], start_date: Optional[str], end_date: Optional[str]) -> List[dict]:
    """날짜별 게시물 필터링 (레거시 호환성)"""
    if not start_date or not end_date:
        return posts

    from datetime import datetime
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    end_dt = end_dt.replace(hour=23, minute=59, second=59)

    filtered = []
    for post in posts:
        post_time = post.get('작성일') or post.get('published')  # datetime 객체 or 문자열
        if isinstance(post_time, str):
            try:
                post_time = datetime.strptime(post_time, "%Y-%m-%d %H:%M:%S")
            except:
                continue
        if start_dt <= post_time <= end_dt:
            filtered.append(post)
    
    return filtered

# ================================
# 🔥 추가 헬퍼 함수 (기존 코드 영향 없음)
# ================================

def is_lemmy_instance(domain: str) -> bool:
    """전역 함수로 Lemmy 인스턴스 확인 (모듈 호환성)"""
    domain = domain.lower().strip()
    
    # 1. 알려진 인스턴스 확인
    if domain in KNOWN_LEMMY_INSTANCES:
        return True
    
    # 2. 기획서 정규표현식 패턴 확인
    for pattern in _compiled_patterns:
        if pattern.match(domain):
            return True
    
    return False

# 모듈 정보 (동적 탐지를 위한 메타데이터)
DISPLAY_NAME = "Lemmy Crawler"
DESCRIPTION = "Lemmy 커뮤니티 크롤러"
VERSION = "2.0.0"
SUPPORTED_DOMAINS = ["lemmy.world", "lemmy.ml", "beehaw.org", "sh.itjust.works", "programming.dev"]
KEYWORDS = ["lemmy", "fediverse", "@lemmy"]

# 모듈 로드 시 초기화
logger.info("🔥 향상된 Lemmy 크롤러 v2.0 로드 완료")
logger.info(f"📊 지원 인스턴스: {len(KNOWN_LEMMY_INSTANCES)}개")
logger.info(f"🎯 안정성 티어: {sum(len(v) for v in STABILITY_TIER.values())}개")
logger.info(f"⚙️ 설정: {LEMMY_CONFIG['api_timeout']}s timeout, {LEMMY_CONFIG['cache_ttl']}s cache")
logger.info(f"🔍 도메인 패턴: {len(LEMMY_DOMAIN_PATTERNS)}개 정규표현식 적용")
if not AIOHTTP_AVAILABLE:
    logger.warning("⚠️ aiohttp가 설치되지 않았습니다. Lemmy 크롤러가 제한적으로 작동합니다.")