# bbc.py - 순수 크롤링 로직만 (메시지 처리는 main.py에서)

import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime, timedelta
from urllib.parse import urljoin, urlparse
import logging
from typing import List, Dict, Optional, Tuple
import asyncio
import time
import hashlib
from dataclasses import dataclass, field

# aiohttp 임포트를 try-except로 보호
try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False
    aiohttp = None
    logging.warning("aiohttp 라이브러리가 설치되지 않았습니다. pip install aiohttp로 설치하세요.")

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ================================
# 🎯 BBC URL 자동 감지 시스템
# ================================

def detect_bbc_url_and_extract_info(input_text: str) -> dict:
    """BBC URL을 감지하고 관련 정보를 추출"""
    
    if not input_text or not input_text.strip():
        return {"is_bbc": False}
    
    input_text = input_text.strip()
    
    # BBC URL 패턴들
    bbc_patterns = [
        r'https?://(?:www\.)?bbc\.com/.*',
        r'https?://(?:www\.)?bbc\.co\.uk/.*',
        r'bbc\.com/.*',
        r'bbc\.co\.uk/.*'
    ]
    
    is_bbc_url = False
    for pattern in bbc_patterns:
        if re.match(pattern, input_text, re.IGNORECASE):
            is_bbc_url = True
            break
    
    if not is_bbc_url:
        return {"is_bbc": False}
    
    # URL 정규화
    if not input_text.startswith('http'):
        if input_text.startswith('bbc.'):
            normalized_url = f"https://www.{input_text}"
        else:
            normalized_url = f"https://www.bbc.com/{input_text.lstrip('/')}"
    else:
        normalized_url = input_text
    
    # URL에서 정보 추출
    try:
        parsed = urlparse(normalized_url)
        path_parts = [p for p in parsed.path.split('/') if p]
        
        # 섹션 정보 추출
        section_info = analyze_bbc_url_section(normalized_url, path_parts)
        
        return {
            "is_bbc": True,
            "original_input": input_text,
            "normalized_url": normalized_url,
            "detected_site": "bbc",
            "board_name": section_info["display_name"],
            "section": section_info["section"],
            "subsection": section_info["subsection"],
            "description": section_info["description"],
            "auto_detected": True,
            "switch_message": f"🎯 BBC {section_info['display_name']} 섹션이 감지되었습니다!"
        }
        
    except Exception as e:
        logger.error(f"BBC URL 분석 오류: {e}")
        return {
            "is_bbc": True,
            "original_input": input_text,
            "normalized_url": normalized_url,
            "detected_site": "bbc",
            "board_name": "BBC News",
            "section": "general",
            "subsection": "",
            "description": "BBC 뉴스 및 콘텐츠",
            "auto_detected": True,
            "switch_message": "🎯 BBC 사이트가 감지되었습니다!"
        }

def analyze_bbc_url_section(url: str, path_parts: list) -> dict:
    """BBC URL의 섹션 정보를 분석"""
    
    # BBC 섹션별 정보 (확장됨)
    bbc_section_map = {
        # 주요 섹션
        "news": {"display_name": "BBC News", "description": "BBC 뉴스 - 세계 및 영국 뉴스"},
        "sport": {"display_name": "BBC Sport", "description": "BBC 스포츠 - 모든 스포츠 뉴스"},
        "business": {"display_name": "BBC Business", "description": "BBC 비즈니스 - 경제 및 금융 뉴스"},
        "technology": {"display_name": "BBC Technology", "description": "BBC 기술 - 과학기술 뉴스"},
        "health": {"display_name": "BBC Health", "description": "BBC 건강 - 의료 및 건강 뉴스"},
        "science": {"display_name": "BBC Science", "description": "BBC 과학 - 과학 연구 및 발견"},
        "entertainment": {"display_name": "BBC Entertainment", "description": "BBC 연예 - 문화 및 연예 뉴스"},
        
        # 스포츠 세부 섹션 (확장됨)
        "football": {"display_name": "BBC Football", "description": "BBC 축구 - 프리미어리그, 챔피언스리그 등"},
        "rugby-union": {"display_name": "BBC Rugby Union", "description": "BBC 럭비 유니온 - 6네이션스, 월드컵 등"},
        "rugby-league": {"display_name": "BBC Rugby League", "description": "BBC 럭비 리그 - 슈퍼리그 등"},
        "cricket": {"display_name": "BBC Cricket", "description": "BBC 크리켓 - 테스트, T20, 월드컵"},
        "tennis": {"display_name": "BBC Tennis", "description": "BBC 테니스 - 윔블던, 그랜드슬램"},
        "golf": {"display_name": "BBC Golf", "description": "BBC 골프 - 마스터스, 메이저 대회"},
        "formula1": {"display_name": "BBC Formula 1", "description": "BBC F1 - 포뮬러원 뉴스"},
        "boxing": {"display_name": "BBC Boxing", "description": "BBC 복싱 - 월드 타이틀 매치"},
        "athletics": {"display_name": "BBC Athletics", "description": "BBC 육상 - 올림픽, 세계선수권"},
        "swimming": {"display_name": "BBC Swimming", "description": "BBC 수영 - 올림픽, 세계선수권"},
        "cycling": {"display_name": "BBC Cycling", "description": "BBC 사이클링 - 투르 드 프랑스"},
        "motorsport": {"display_name": "BBC Motorsport", "description": "BBC 모터스포츠 - F1, MotoGP"},
        "winter-sports": {"display_name": "BBC Winter Sports", "description": "BBC 윈터스포츠 - 스키, 스케이팅"},
        "horse-racing": {"display_name": "BBC Horse Racing", "description": "BBC 경마 - 그랜드내셔널"},
        "snooker": {"display_name": "BBC Snooker", "description": "BBC 스누커 - 월드챔피언십"},
        "darts": {"display_name": "BBC Darts", "description": "BBC 다트 - PDC 월드챔피언십"},
        
        # 뉴스 세부 섹션
        "world": {"display_name": "BBC World News", "description": "BBC 세계뉴스 - 국제 뉴스"},
        "uk": {"display_name": "BBC UK News", "description": "BBC 영국뉴스 - 영국 국내 뉴스"},
        "politics": {"display_name": "BBC Politics", "description": "BBC 정치 - 영국 및 세계 정치"},
        "education": {"display_name": "BBC Education", "description": "BBC 교육 - 교육 정책 및 뉴스"},
        "science-environment": {"display_name": "BBC Science & Environment", "description": "BBC 과학환경 - 기후변화, 환경"},
        "entertainment-arts": {"display_name": "BBC Entertainment & Arts", "description": "BBC 연예예술 - 문화, 예술"},
        "disability": {"display_name": "BBC Disability", "description": "BBC 장애 - 장애인 관련 뉴스"},
        
        # 지역별 뉴스
        "england": {"display_name": "BBC England", "description": "BBC 잉글랜드 - 잉글랜드 지역 뉴스"},
        "scotland": {"display_name": "BBC Scotland", "description": "BBC 스코틀랜드 - 스코틀랜드 뉴스"},
        "wales": {"display_name": "BBC Wales", "description": "BBC 웨일스 - 웨일스 뉴스"},
        "northern-ireland": {"display_name": "BBC Northern Ireland", "description": "BBC 북아일랜드 - 북아일랜드 뉴스"}
    }
    
    main_section = ""
    subsection = ""
    
    if len(path_parts) >= 1:
        main_section = path_parts[0].lower()
        
    if len(path_parts) >= 2:
        subsection = path_parts[1].lower()
    
    # 주 섹션과 서브섹션 조합으로 찾기
    combined_key = f"{main_section}-{subsection}" if subsection else main_section
    
    if combined_key in bbc_section_map:
        section_info = bbc_section_map[combined_key]
        return {
            "section": main_section,
            "subsection": subsection,
            "display_name": section_info["display_name"],
            "description": section_info["description"]
        }
    elif main_section in bbc_section_map:
        section_info = bbc_section_map[main_section]
        return {
            "section": main_section,
            "subsection": subsection,
            "display_name": section_info["display_name"],
            "description": section_info["description"]
        }
    else:
        # 알 수 없는 섹션
        display_name = f"BBC {main_section.title()}" if main_section else "BBC News"
        if subsection:
            display_name += f" - {subsection.title()}"
            
        return {
            "section": main_section or "general",
            "subsection": subsection,
            "display_name": display_name,
            "description": f"BBC {main_section} 섹션" if main_section else "BBC 콘텐츠"
        }

def parse_relative_time(relative_str: str) -> str:
    """상대 시간 파싱 ('2 hours ago' 등)"""
    try:
        import re
        now = datetime.now()
        
        # "X hours ago", "X minutes ago" 등 파싱
        match = re.search(r'(\d+)\s*(hour|minute|day|week)s?\s*ago', relative_str.lower())
        if match:
            value = int(match.group(1))
            unit = match.group(2)
            
            if unit == 'minute':
                result_time = now - timedelta(minutes=value)
            elif unit == 'hour':
                result_time = now - timedelta(hours=value)
            elif unit == 'day':
                result_time = now - timedelta(days=value)
            elif unit == 'week':
                result_time = now - timedelta(weeks=value)
            else:
                result_time = now
                
            return result_time.strftime('%Y.%m.%d %H:%M')
        
        return datetime.now().strftime('%Y.%m.%d %H:%M')
    except:
        return datetime.now().strftime('%Y.%m.%d %H:%M')

def is_bbc_domain(url: str) -> bool:
    """URL이 BBC 도메인인지 간단 확인"""
    
    if not url:
        return False
    
    url_lower = url.lower()
    return 'bbc.com' in url_lower or 'bbc.co.uk' in url_lower

# ================================
# 🛡️ 안정성 우선 BBC 설정
# ================================

# 🔥 Fallback 선택자 (안정성 우선)
BBC_STABLE_SELECTORS = {
    # Level 1: 최신 BBC 컴포넌트 (시도해볼 가치 있음)
    'level1_primary': [
        '[data-testid="liverpool-card"]',
        '[data-testid="edinburgh-card"]', 
        '.gs-c-promo',
    ],
    
    # Level 2: 검증된 BBC 선택자 (신뢰도 높음)
    'level2_reliable': [
        '.media',
        'article[class*="promo"]',
        '.gel-layout__item article',
        '.qa-heading-link',
    ],
    
    # Level 3: 일반적인 구조 (거의 항상 작동)
    'level3_general': [
        'article',
        'h2 a[href*="/"]',
        'h3 a[href*="/"]', 
        '.story-promo',
    ],
    
    # Level 4: 링크 기반 (매우 관대함)
    'level4_links': [
        'a[href*="/news/"]',
        'a[href*="/sport/"]',
        'a[href*="/business/"]',
        'a[href*="/technology/"]',
    ],
    
    # Level 5: 최후의 수단 (모든 링크)
    'level5_emergency': [
        'a[href]',
    ]
}

# 🎯 BBC 섹션별 특화 설정 (단순화됨)
BBC_SECTION_CONFIG = {
    'news': {
        'expected_count': 15,
        'sub_sections': ['world', 'uk', 'politics', 'health', 'education'],
        'quality_threshold': 0.3,  # 더 관대함
    },
    'sport': {
        'expected_count': 12,
        'sub_sections': ['football', 'cricket', 'tennis', 'golf', 'darts', 'rugby'],
        'quality_threshold': 0.2,  # 매우 관대함
    },
    'business': {
        'expected_count': 8,
        'sub_sections': ['economy', 'companies', 'markets'],
        'quality_threshold': 0.3,
    },
    'technology': {
        'expected_count': 6,
        'sub_sections': ['science', 'health'],
        'quality_threshold': 0.3,
    }
}

# 🚫 최소한의 필터링만 (안정성 우선)
BBC_MINIMAL_FILTERS = {
    'min_title_length': 8,  # 더 관대함
    'max_title_length': 300,  # 더 관대함
    'exclude_exact_matches': [  # 정확히 일치하는 것만 제외
        'BBC', 'Home', 'Menu', 'Search', 'Sign in', 'Sport', 'News',
        'More', 'Live', 'Video', 'Audio', 'Weather', 'Travel'
    ]
}

# BBC URL 패턴 정의
BBC_URL_PATTERNS = {
    'main_sections': [
        r'bbc\.com/news',
        r'bbc\.com/sport', 
        r'bbc\.com/business',
        r'bbc\.com/technology',
        r'bbc\.co\.uk/news',
        r'bbc\.co\.uk/sport'
    ],
    'sport_subsections': [
        r'bbc\.com/sport/football',
        r'bbc\.com/sport/cricket', 
        r'bbc\.com/sport/tennis',
        r'bbc\.com/sport/golf',
        r'bbc\.com/sport/rugby-union',
        r'bbc\.com/sport/rugby-league',
        r'bbc\.com/sport/formula1',
        r'bbc\.com/sport/athletics',
        r'bbc\.com/sport/cycling',
        r'bbc\.com/sport/boxing',
        r'bbc\.com/sport/darts',
        r'bbc\.com/sport/snooker'
    ],
    'news_subsections': [
        r'bbc\.com/news/world',
        r'bbc\.com/news/uk', 
        r'bbc\.com/news/politics',
        r'bbc\.com/news/business',
        r'bbc\.com/news/health',
        r'bbc\.com/news/education',
        r'bbc\.com/news/science-environment',
        r'bbc\.com/news/technology',
        r'bbc\.com/news/entertainment-arts'
    ]
}

# ================================
# 🛡️ 안정성 우선 BBC 크롤러
# ================================

class StableBBCCrawler:
    """안정성을 최우선으로 하는 BBC 크롤러"""
    
    def __init__(self):
        self.session = None
        if AIOHTTP_AVAILABLE:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=25),  # 더 여유로운 타임아웃
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Connection': 'keep-alive',
                }
            )
        self.seen_titles = set()
        self.seen_urls = set()
        self.fallback_stats = {'level1': 0, 'level2': 0, 'level3': 0, 'level4': 0, 'level5': 0}
    
    async def crawl_with_maximum_stability(self, board_url: str, limit: int = 50,
                                         start_index: int = 1, end_index: int = 20,
                                         websocket=None) -> List[Dict]:
        """최대 안정성 보장 크롤링"""
        
        start_time = time.time()
        all_articles = []
        
        # aiohttp 사용 가능성 확인
        if not AIOHTTP_AVAILABLE or not self.session:
            error_msg = "BBC 크롤러를 사용할 수 없습니다. aiohttp 라이브러리를 설치하세요: pip install aiohttp"
            logger.error(error_msg)
            raise Exception(error_msg)
        
        try:
            logger.info(f"🛡️ 안정성 우선 BBC 크롤링 시작: {board_url}")
            
            # 🔥 1단계: 메인 페이지 크롤링
            main_articles = await self._crawl_with_fallback_levels(board_url, websocket)
            all_articles.extend(main_articles)
            
            # 🔥 2단계: 세부 섹션 자동 탐지 및 크롤링
            if len(all_articles) < (end_index - start_index + 1) * 2:  # 부족하면 세부 섹션 탐색
                sub_articles = await self._auto_discover_and_crawl_subsections(board_url, websocket)
                all_articles.extend(sub_articles)
            
            # 🔥 3단계: 관대한 필터링 적용
            filtered_articles = self._apply_minimal_filtering(all_articles)
            
            # 🔥 4단계: 정렬 (클라이언트 사이드)
            sorted_articles = self._simple_client_side_sort(filtered_articles)
            
            # 🔥 5단계: 범위 적용 및 번호 부여
            final_articles = self._apply_range_safely(sorted_articles, start_index, end_index)
            
            logger.info(f"✅ 안정성 우선 크롤링 완료: {len(final_articles)}개")
            return final_articles
            
        except Exception as e:
            logger.error(f"안정성 크롤링 오류: {e}")
            # 🚨 최후의 응급 크롤링
            return await self._emergency_crawl(board_url, start_index, end_index)
    
    async def _crawl_with_fallback_levels(self, url: str, websocket=None) -> List[Dict]:
        """5단계 Fallback 크롤링"""
        
        try:
            async with self.session.get(url) as response:
                if response.status != 200:
                    raise Exception(f"HTTP {response.status}")
                
                content = await response.text()
                soup = BeautifulSoup(content, 'html.parser')
                
                # Level 1: 최신 BBC 컴포넌트 시도
                articles = await self._try_level1_extraction(soup, url)
                if len(articles) >= 3:
                    self.fallback_stats['level1'] = len(articles)
                    logger.info(f"✅ Level 1 성공: {len(articles)}개")
                    return articles
                
                # Level 2: 검증된 선택자
                articles = await self._try_level2_extraction(soup, url)
                if len(articles) >= 3:
                    self.fallback_stats['level2'] = len(articles)
                    logger.info(f"✅ Level 2 성공: {len(articles)}개")
                    return articles
                
                # Level 3: 일반적인 구조
                articles = await self._try_level3_extraction(soup, url)
                if len(articles) >= 2:
                    self.fallback_stats['level3'] = len(articles)
                    logger.info(f"✅ Level 3 성공: {len(articles)}개")
                    return articles
                
                # Level 4: 링크 기반
                articles = await self._try_level4_extraction(soup, url)
                if len(articles) >= 1:
                    self.fallback_stats['level4'] = len(articles)
                    logger.info(f"✅ Level 4 성공: {len(articles)}개")
                    return articles
                
                # Level 5: 응급 모드
                articles = await self._try_level5_extraction(soup, url)
                self.fallback_stats['level5'] = len(articles)
                logger.info(f"🚨 Level 5 응급모드: {len(articles)}개")
                return articles
                
        except Exception as e:
            logger.error(f"Fallback 크롤링 오류: {e}")
            return []
    
    async def _try_level1_extraction(self, soup, base_url: str) -> List[Dict]:
        """Level 1: 최신 BBC 컴포넌트"""
        articles = []
        
        for selector in BBC_STABLE_SELECTORS['level1_primary']:
            try:
                containers = soup.select(selector)
                for container in containers[:15]:  # 적당한 제한
                    article = self._extract_from_container_safe(container, base_url, "Level1")
                    if article:
                        articles.append(article)
                        
                if len(articles) >= 5:  # 충분히 찾았으면 중단
                    break
                    
            except Exception as e:
                logger.debug(f"Level 1 선택자 '{selector}' 실패: {e}")
                continue
        
        return articles
    
    async def _try_level2_extraction(self, soup, base_url: str) -> List[Dict]:
        """Level 2: 검증된 선택자"""
        articles = []
        
        for selector in BBC_STABLE_SELECTORS['level2_reliable']:
            try:
                containers = soup.select(selector)
                for container in containers[:20]:
                    article = self._extract_from_container_safe(container, base_url, "Level2")
                    if article:
                        articles.append(article)
                        
                if len(articles) >= 8:
                    break
                    
            except Exception as e:
                logger.debug(f"Level 2 선택자 '{selector}' 실패: {e}")
                continue
        
        return articles
    
    async def _try_level3_extraction(self, soup, base_url: str) -> List[Dict]:
        """Level 3: 일반적인 구조"""
        articles = []
        
        for selector in BBC_STABLE_SELECTORS['level3_general']:
            try:
                containers = soup.select(selector)
                for container in containers[:30]:
                    article = self._extract_from_container_safe(container, base_url, "Level3")
                    if article:
                        articles.append(article)
                        
                if len(articles) >= 10:
                    break
                    
            except Exception as e:
                logger.debug(f"Level 3 선택자 '{selector}' 실패: {e}")
                continue
        
        return articles
    
    async def _try_level4_extraction(self, soup, base_url: str) -> List[Dict]:
        """Level 4: 링크 기반 (관대함)"""
        articles = []
        
        for selector in BBC_STABLE_SELECTORS['level4_links']:
            try:
                links = soup.select(selector)
                for link in links[:50]:
                    title = link.get_text(strip=True)
                    href = link.get('href', '')
                    
                    if title and len(title) > BBC_MINIMAL_FILTERS['min_title_length']:
                        article = self._create_article_safe(title, href, base_url, "Level4")
                        if article:
                            articles.append(article)
                            
                if len(articles) >= 5:
                    break
                    
            except Exception as e:
                logger.debug(f"Level 4 선택자 '{selector}' 실패: {e}")
                continue
        
        return articles
    
    async def _try_level5_extraction(self, soup, base_url: str) -> List[Dict]:
        """Level 5: 최후의 수단 (모든 링크)"""
        articles = []
        
        try:
            all_links = soup.find_all('a', href=True)
            
            for link in all_links[:100]:  # 최대 100개까지만
                title = link.get_text(strip=True)
                href = link.get('href', '')
                
                # 매우 기본적인 필터링만
                if (title and 
                    len(title) >= BBC_MINIMAL_FILTERS['min_title_length'] and 
                    len(title) <= BBC_MINIMAL_FILTERS['max_title_length'] and
                    title not in BBC_MINIMAL_FILTERS['exclude_exact_matches']):
                    
                    article = self._create_article_safe(title, href, base_url, "Level5-Emergency")
                    if article:
                        articles.append(article)
                        
                if len(articles) >= 3:  # 최소한만 확보
                    break
                    
        except Exception as e:
            logger.error(f"Level 5 응급 추출 실패: {e}")
        
        return articles
    
    def _extract_from_container_safe(self, container, base_url: str, method: str) -> Optional[Dict]:
        """안전한 컨테이너 추출"""
        try:
            # 제목 찾기 (여러 방법 시도)
            title = ""
            url = ""
            
            # 방법 1: 링크 텍스트
            link = container.find('a', href=True)
            if link:
                title = link.get_text(strip=True)
                url = urljoin(base_url, link.get('href', ''))
            
            # 방법 2: 헤딩 태그
            if not title:
                for tag in ['h1', 'h2', 'h3', 'h4', 'h5']:
                    heading = container.find(tag)
                    if heading:
                        title = heading.get_text(strip=True)
                        break
            
            # 방법 3: 컨테이너 전체 텍스트 (축약)
            if not title:
                full_text = container.get_text(strip=True)
                if full_text:
                    title = full_text[:100] + "..." if len(full_text) > 100 else full_text
            
            if title:
                return self._create_article_safe(title, url, base_url, method, container)
                
        except Exception as e:
            logger.debug(f"컨테이너 추출 실패: {e}")
        
        return None
    
    def _extract_bbc_datetime(self, container, base_url: str) -> str:
        """BBC 특화 날짜/시간 추출 함수"""
        try:
            # BBC 날짜 선택자들 (우선순위 순)
            date_selectors = [
                '[data-testid="timestamp"]',
                'time[datetime]',
                '.date',
                '.timestamp',
                '[datetime]',
                '.gel-body-copy time'
            ]
            
            for selector in date_selectors:
                date_elem = container.select_one(selector)
                if date_elem:
                    # datetime 속성 우선 확인
                    if date_elem.get('datetime'):
                        return self._parse_bbc_datetime(date_elem.get('datetime'))
                    # 텍스트 내용 파싱
                    elif date_elem.get_text(strip=True):
                        return self._parse_bbc_datetime(date_elem.get_text(strip=True))
            
            # 기본값: 현재 시간
            return datetime.now().strftime('%Y.%m.%d %H:%M')
        
        except Exception as e:
            logger.debug(f"BBC 날짜 추출 실패: {e}")
            return datetime.now().strftime('%Y.%m.%d %H:%M')

    def _parse_bbc_datetime(self, date_str: str) -> str:
        """BBC 날짜 형식 파싱"""
        try:
            # BBC 일반적인 형식들
            formats = [
                '%Y-%m-%dT%H:%M:%S.%fZ',  # ISO format
                '%Y-%m-%dT%H:%M:%SZ',     # ISO without microseconds
                '%d %B %Y',               # "11 June 2025"
                '%B %d, %Y',              # "June 11, 2025"
                '%d %b %Y',               # "11 Jun 2025"
                '%Y-%m-%d',               # "2025-06-11"
            ]
            
            for fmt in formats:
                try:
                    dt = datetime.strptime(date_str.strip(), fmt)
                    return dt.strftime('%Y.%m.%d %H:%M')
                except ValueError:
                    continue
            
            # 상대 시간 처리 ("2 hours ago", "1 day ago" 등)
            if 'ago' in date_str.lower():
                return parse_relative_time(date_str)
            
            # 파싱 실패시 현재 시간
            return datetime.now().strftime('%Y.%m.%d %H:%M')
        
        except Exception:
            return datetime.now().strftime('%Y.%m.%d %H:%M')

    def _create_article_safe(self, title: str, url: str, base_url: str, method: str, container = None) -> Optional[Dict]:
        """안전한 기사 객체 생성"""
        try:
            # 기본 검증
            if not title or len(title) < BBC_MINIMAL_FILTERS['min_title_length']:
                return None
            
            if title in BBC_MINIMAL_FILTERS['exclude_exact_matches']:
                return None
            
            # 중복 검사 (해시 기반)
            title_hash = hashlib.md5(title.encode()).hexdigest()
            if title_hash in self.seen_titles:
                return None
            self.seen_titles.add(title_hash)
            
            # URL 정규화
            if url:
                # 상대 URL 처리
                if url.startswith('/'):
                    parsed_base = urlparse(base_url)
                    url = f"{parsed_base.scheme}://{parsed_base.netloc}{url}"
                # 프로토콜 없는 URL 처리
                elif not url.startswith('http'):
                    url = urljoin(base_url, url)
                # 이미 완전한 URL인 경우 그대로 사용
            else:
                # URL이 없으면 기사 제목으로 BBC 검색 URL 생성
                search_query = title.replace(' ', '+')
                url = f"https://www.bbc.com/search?q={search_query}"
            
            date_info = self._extract_bbc_datetime(container, base_url) if container else datetime.now().strftime('%Y.%m.%d %H:%M')
            
            # 기사 객체 생성
            article = {
                "번호": 0,  # 나중에 부여
                "원제목": title,
                "번역제목": None,  # 번역은 별도 처리
                "링크": url,
                "원문URL": url,
                "썸네일 URL": "",
                "본문": "",
                "조회수": 0,
                "추천수": 0,
                "댓글수": 0,
                "작성일": date_info,
                "작성자": "BBC News",
                "사이트": "bbc.com",
                "콘텐츠타입": "news",
                "섹션": self._detect_section_from_url(url or base_url),
                "품질점수": 5.0,  # 기본 점수
                "추출방법": method,
                "크롤링방식": "BBC-Stable-MultiLevel",
                "분류신뢰도": 0.9,
                "키워드": ["bbc", "news"],
                "감정": "neutral"
            }
            
            return article
            
        except Exception as e:
            logger.debug(f"기사 생성 실패: {e}")
            return None
    
    async def _auto_discover_and_crawl_subsections(self, main_url: str, websocket=None) -> List[Dict]:
        """세부 섹션 자동 탐지 및 크롤링"""
        
        subsection_articles = []
        
        try:
            # URL에서 섹션 감지
            section = self._detect_section_from_url(main_url)
            section_config = BBC_SECTION_CONFIG.get(section, {})
            sub_sections = section_config.get('sub_sections', [])
            
            # 각 세부 섹션 크롤링 시도
            for idx, sub_section in enumerate(sub_sections[:3]):  # 최대 3개까지만
                try:
                    sub_url = self._construct_subsection_url(main_url, sub_section)
                    logger.info(f"🔍 세부섹션 크롤링: {sub_url}")
                    
                    sub_articles = await self._crawl_with_fallback_levels(sub_url)
                    
                    # 세부섹션 표시 추가
                    for article in sub_articles:
                        article['섹션'] = f"{section}-{sub_section}"
                        article['추출방법'] += f"-SubSection({sub_section})"
                    
                    subsection_articles.extend(sub_articles[:5])  # 각 섹션에서 최대 5개
                    
                    # 너무 많이 수집했으면 중단
                    if len(subsection_articles) >= 15:
                        break
                        
                except Exception as e:
                    logger.debug(f"세부섹션 '{sub_section}' 크롤링 실패: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"세부섹션 탐색 오류: {e}")
        
        logger.info(f"세부섹션 크롤링 완료: {len(subsection_articles)}개")
        return subsection_articles
    
    def _construct_subsection_url(self, main_url: str, sub_section: str) -> str:
        """세부섹션 URL 생성"""
        try:
            parsed = urlparse(main_url)
            base = f"{parsed.scheme}://{parsed.netloc}"
            
            # BBC URL 패턴에 따른 세부섹션 URL 생성
            if '/sport' in main_url:
                return f"{base}/sport/{sub_section}"
            elif '/news' in main_url:
                return f"{base}/news/{sub_section}"
            elif '/business' in main_url:
                return f"{base}/business/{sub_section}"
            elif '/technology' in main_url:
                return f"{base}/technology"  # 기술은 세분화 안됨
            else:
                return f"{base}/{sub_section}"
                
        except Exception as e:
            logger.debug(f"세부섹션 URL 생성 실패: {e}")
            return main_url
    
    def _detect_section_from_url(self, url: str) -> str:
        """URL에서 섹션 감지"""
        if not url:
            return 'general'
        
        url_lower = url.lower()
        if '/sport' in url_lower:
            return 'sport'
        elif '/news' in url_lower:
            return 'news'
        elif '/business' in url_lower:
            return 'business'
        elif '/technology' in url_lower:
            return 'technology'
        else:
            return 'general'
    
    def _apply_minimal_filtering(self, articles: List[Dict]) -> List[Dict]:
        """최소한의 필터링만 적용 (안정성 우선)"""
        
        filtered = []
        seen_titles = set()
        
        for article in articles:
            title = article.get('원제목', '')
            
            # 매우 기본적인 필터링만
            if (title and 
                len(title) >= BBC_MINIMAL_FILTERS['min_title_length'] and
                len(title) <= BBC_MINIMAL_FILTERS['max_title_length'] and
                title not in BBC_MINIMAL_FILTERS['exclude_exact_matches']):
                
                # 중복 제거
                title_key = title.lower().strip()
                if title_key not in seen_titles:
                    seen_titles.add(title_key)
                    filtered.append(article)
        
        logger.info(f"최소 필터링: {len(articles)} → {len(filtered)} 기사")
        return filtered
    
    def _simple_client_side_sort(self, articles: List[Dict]) -> List[Dict]:
        """간단한 클라이언트 사이드 정렬 (BBC는 실제 정렬 API 없음)"""
        
        try:
            # 품질점수와 추출방법 기준으로 안정적 정렬
            def sort_key(article):
                quality = article.get('품질점수', 0)
                method = article.get('추출방법', '')
                
                # 추출방법별 가중치
                method_weight = 0
                if 'Level1' in method:
                    method_weight = 5
                elif 'Level2' in method:
                    method_weight = 4
                elif 'Level3' in method:
                    method_weight = 3
                elif 'Level4' in method:
                    method_weight = 2
                else:
                    method_weight = 1
                
                return quality + method_weight
            
            sorted_articles = sorted(articles, key=sort_key, reverse=True)
            logger.info(f"클라이언트 정렬 완료: {len(sorted_articles)}개")
            
            return sorted_articles
            
        except Exception as e:
            logger.error(f"정렬 오류: {e}")
            return articles  # 정렬 실패시 원본 반환
    
    def _apply_range_safely(self, articles: List[Dict], start_index: int, end_index: int) -> List[Dict]:
        """안전한 범위 적용"""
        
        try:
            # 범위 보정
            start_idx = max(0, start_index - 1)
            end_idx = min(len(articles), end_index)
            
            if start_idx >= len(articles):
                # 시작 인덱스가 범위를 벗어나면 마지막 몇 개라도 반환
                final_articles = articles[-3:] if len(articles) >= 3 else articles
            else:
                final_articles = articles[start_idx:end_idx]
            
            # 번호 부여
            for idx, article in enumerate(final_articles):
                article['번호'] = start_index + idx
            
            logger.info(f"범위 적용: {start_index}-{end_index} → {len(final_articles)}개")
            return final_articles
            
        except Exception as e:
            logger.error(f"범위 적용 오류: {e}")
            # 오류 시 처음 몇 개라도 반환
            safe_articles = articles[:5] if len(articles) >= 5 else articles
            for idx, article in enumerate(safe_articles):
                article['번호'] = idx + 1
            return safe_articles
    
    async def _emergency_crawl(self, url: str, start_index: int, end_index: int) -> List[Dict]:
        """🚨 최후의 응급 크롤링 (무조건 성공)"""
        
        emergency_articles = []
        
        try:
            logger.warning("🚨 응급 크롤링 모드 활성화")
            
            # 매우 간단한 요청으로 기본 정보라도 추출
            async with self.session.get(url) as response:
                if response.status == 200:
                    content = await response.text()
                    
                    # HTML에서 title 태그라도 추출
                    soup = BeautifulSoup(content, 'html.parser')
                    page_title = soup.find('title')
                    if page_title:
                        main_title = page_title.get_text(strip=True)
                        
                        # 기본 기사 객체 생성
                        emergency_article = {
                            "번호": 1,
                            "원제목": f"BBC 페이지: {main_title}",
                            "번역제목": None,
                            "링크": url,
                            "원문URL": url,
                            "썸네일 URL": "",
                            "본문": "상세 내용을 보려면 링크를 클릭하세요.",
                            "조회수": 0,
                            "추천수": 0,
                            "댓글수": 0,
                            "작성일": datetime.now().strftime('%Y.%m.%d %H:%M'),
                            "작성자": "BBC News",
                            "사이트": "bbc.com",
                            "콘텐츠타입": "news",
                            "섹션": self._detect_section_from_url(url),
                            "품질점수": 3.0,
                            "추출방법": "Emergency-Mode",
                            "크롤링방식": "BBC-Emergency-Fallback",
                            "분류신뢰도": 0.7,
                            "키워드": ["bbc", "news", "emergency"],
                            "감정": "neutral"
                        }
                        
                        emergency_articles.append(emergency_article)
            
            # 최소한이라도 반환
            if not emergency_articles:
                # 정말 최후의 수단: 하드코딩된 기본 기사
                default_article = {
                    "번호": 1,
                    "원제목": "BBC News - 콘텐츠를 불러올 수 없습니다",
                    "번역제목": None,
                    "링크": url,
                    "원문URL": url,
                    "썸네일 URL": "",
                    "본문": "현재 BBC 뉴스 콘텐츠를 불러올 수 없습니다. 직접 링크를 방문해 주세요.",
                    "조회수": 0,
                    "추천수": 0,
                    "댓글수": 0,
                    "작성일": datetime.now().strftime('%Y.%m.%d %H:%M'),
                    "작성자": "BBC News",
                    "사이트": "bbc.com",
                    "콘텐츠타입": "news",
                    "섹션": "general",
                    "품질점수": 1.0,
                    "추출방법": "Hardcoded-Fallback",
                    "크롤링방식": "BBC-Absolute-Emergency",
                    "분류신뢰도": 0.5,
                    "키워드": ["bbc", "news", "fallback"],
                    "감정": "neutral"
                }
                emergency_articles.append(default_article)
            
            logger.warning(f"🚨 응급 크롤링 완료: {len(emergency_articles)}개")
            return emergency_articles
            
        except Exception as e:
            logger.error(f"응급 크롤링마저 실패: {e}")
            # 정말 최후의 수단: 빈 리스트 대신 기본 메시지
            return [{
                "번호": 1,
                "원제목": "크롤링 실패 - BBC 사이트에 접근할 수 없습니다",
                "번역제목": None,
                "링크": url,
                "원문URL": url,
                "썸네일 URL": "",
                "본문": f"죄송합니다. 현재 BBC 사이트 크롤링에 실패했습니다. 오류: {str(e)}",
                "조회수": 0,
                "추천수": 0,
                "댓글수": 0,
                "작성일": datetime.now().strftime('%Y.%m.%d %H:%M'),
                "작성자": "System",
                "사이트": "bbc.com",
                "콘텐츠타입": "error",
                "섹션": "error",
                "품질점수": 0.0,
                "추출방법": "Error-Fallback",
                "크롤링방식": "BBC-Error-Handler",
                "분류신뢰도": 0.1,
                "키워드": ["error", "fallback"],
                "감정": "neutral"
            }]
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

# ================================
# 🛡️ 메인 함수 - 안정성 극대화
# ================================

async def crawl_bbc_board(board_url: str, limit: int = 50, sort: str = "recent",
                         min_views: int = 0, min_likes: int = 0, min_comments: int = 0,
                         time_filter: str = "all", start_date: str = None, 
                         end_date: str = None, websocket=None, board_name: str = "",
                         enforce_date_limit: bool = False, start_index: int = 1, 
                         end_index: int = 20) -> List[Dict]:
    """안정성 극대화 BBC 크롤링 메인 함수"""
    
    start_time = time.time()
    
    # aiohttp 사용 가능성 확인
    if not AIOHTTP_AVAILABLE:
        error_msg = "BBC 크롤러를 사용할 수 없습니다. aiohttp 라이브러리를 설치하세요: pip install aiohttp"
        logger.error(error_msg)
        raise Exception(error_msg)
    
    async with StableBBCCrawler() as crawler:
        try:
            logger.info(f"🛡️ 안정성 우선 BBC 크롤링 시작: {board_url}")
            
            # BBC 사이트 확인 (관대하게)
            if 'bbc' not in board_url.lower():
                logger.warning("BBC 사이트가 아닐 수 있지만 크롤링 시도")
            
            # 🛡️ 최대 안정성 크롤링 실행
            articles = await crawler.crawl_with_maximum_stability(
                board_url, limit, start_index, end_index, websocket
            )
            
            # 📅 날짜 필터링 (선택적, 실패해도 계속)
            if start_date and end_date and articles:
                try:
                    original_count = len(articles)
                    articles = filter_bbc_by_date_safe(articles, start_date, end_date)
                        
                except Exception as e:
                    logger.warning(f"날짜 필터링 실패하지만 계속 진행: {e}")
                    # 날짜 필터링 실패해도 원본 articles 유지
            
            logger.info(f"✅ BBC 안정성 크롤링 성공: {len(articles)}개")
            return articles
            
        except Exception as e:
            logger.error(f"BBC 크롤링 오류: {e}")
            
            # 🚨 오류 발생시에도 최소한의 결과 제공
            emergency_result = await crawler._emergency_crawl(board_url, start_index, end_index)
            
            return emergency_result

def filter_bbc_by_date_safe(articles: List[Dict], start_date: str, end_date: str) -> List[Dict]:
    """안전한 BBC 날짜 필터링 (실패해도 원본 반환)"""
    
    try:
        from datetime import datetime
        
        # 관대한 날짜 파싱
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        end_dt = end_dt.replace(hour=23, minute=59, second=59)
        
        filtered = []
        
        for article in articles:
            try:
                date_str = article.get('작성일', '')
                
                # 날짜 파싱 실패시 포함 (관대함)
                if not date_str:
                    filtered.append(article)
                    continue
                
                # 간단한 날짜 형식만 처리
                if re.match(r'\d{4}\.\d{2}\.\d{2}', date_str):
                    date_part = date_str.split()[0]
                    article_date = datetime.strptime(date_part, '%Y.%m.%d')
                    
                    if start_dt <= article_date <= end_dt:
                        filtered.append(article)
                else:
                    # 파싱 불가능하면 포함 (안전)
                    filtered.append(article)
                    
            except Exception:
                # 개별 기사 날짜 처리 실패시 포함
                filtered.append(article)
                continue
        
        logger.info(f"안전 날짜 필터링: {len(articles)} → {len(filtered)}")
        return filtered if filtered else articles  # 결과가 없으면 원본 반환
        
    except Exception as e:
        logger.warning(f"날짜 필터링 완전 실패, 원본 반환: {e}")
        return articles

# ================================
# 🔧 유틸리티 함수들 (단순화)
# ================================

def parse_bbc_article(url: str) -> Dict:
    """간단한 BBC 기사 파싱 (실패 방지)"""
    try:
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        response = session.get(url, timeout=20)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 매우 간단한 제목 추출
        title = ""
        title_selectors = ['h1', 'title', '[data-testid="headline"]']
        for selector in title_selectors:
            elem = soup.select_one(selector)
            if elem:
                title = elem.get_text(strip=True)
                break
        
        # 매우 간단한 본문 추출
        content = ""
        content_selectors = ['[data-component="text-block"]', 'p', '.story-body']
        for selector in content_selectors:
            elements = soup.select(selector)
            if elements:
                content = '\n'.join([elem.get_text(strip=True) for elem in elements[:3]])
                break
        
        return {
            "title": title or "BBC 기사",
            "content": content or "내용을 불러올 수 없습니다",
            "meta": {"author": "BBC News"},
            "url": url,
            "source": "BBC News Stable"
        }
        
    except Exception as e:
        logger.error(f"BBC 기사 파싱 실패: {e}")
        return {
            "title": "파싱 실패",
            "content": f"기사를 불러올 수 없습니다. 직접 링크를 방문해 주세요: {url}",
            "meta": {"error": str(e)},
            "url": url,
            "source": "BBC News Stable"
        }

def is_bbc_url(url: str) -> bool:
    """BBC URL 여부 확인 (향상된 감지)"""
    if not url:
        return False
    
    url_lower = url.lower()
    
    # 기본 BBC 도메인 체크
    if 'bbc.com' in url_lower or 'bbc.co.uk' in url_lower:
        return True
    
    # 패턴 기반 체크
    all_patterns = (BBC_URL_PATTERNS['main_sections'] + 
                   BBC_URL_PATTERNS['sport_subsections'] + 
                   BBC_URL_PATTERNS['news_subsections'])
    
    for pattern in all_patterns:
        if re.search(pattern, url_lower):
            return True
    
    return False

# 모듈 정보 (동적 탐지를 위한 메타데이터)
DISPLAY_NAME = "BBC Crawler"
DESCRIPTION = "BBC 뉴스 및 스포츠 크롤러"
VERSION = "2.0.0"
SUPPORTED_DOMAINS = ["bbc.com", "www.bbc.com", "bbc.co.uk", "www.bbc.co.uk"]
KEYWORDS = ["bbc", "british broadcasting"]

# 모듈 로드 시 초기화
logger.info("🛡️ 안정성 우선 BBC 크롤러 v2.0 로드 완료")
logger.info(f"📊 지원 섹션: {len(BBC_SECTION_CONFIG)}개")
logger.info(f"🎯 Fallback 레벨: {len(BBC_STABLE_SELECTORS)}단계")
if not AIOHTTP_AVAILABLE:
    logger.warning("⚠️ aiohttp가 설치되지 않았습니다. BBC 크롤러가 작동하지 않습니다.")