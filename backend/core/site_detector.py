# core/site_detector.py
"""
🔍 사이트 감지기 모듈
자동으로 URL 또는 입력에서 사이트 타입을 감지합니다.
"""

import logging
from urllib.parse import urlparse
from typing import Optional

logger = logging.getLogger(__name__)

class SiteDetector:
    """사이트 타입 자동 감지기"""
    
    def __init__(self):
        # 사이트별 도메인 패턴
        self.site_patterns = {
            'reddit': [
                'reddit.com', 'www.reddit.com', 'old.reddit.com', 'new.reddit.com'
            ],
            'dcinside': [
                'dcinside.com', 'gall.dcinside.com', 'm.dcinside.com'
            ],
            'blind': [
                'teamblind.com', 'blind.com', 'www.teamblind.com'
            ],
            'bbc': [
                'bbc.com', 'www.bbc.com', 'bbc.co.uk', 'www.bbc.co.uk'
            ],
            'lemmy': [
                # 주요 Lemmy 인스턴스들
                'lemmy.world', 'lemmy.ml', 'beehaw.org', 'sh.itjust.works',
                'feddit.de', 'lemm.ee', 'sopuli.xyz', 'lemmy.ca'
            ]
        }
        
        # 키워드 기반 매칭
        self.keyword_patterns = {
            'reddit': ['reddit', 'subreddit', '/r/'],
            'dcinside': ['dcinside', 'dcin', '디시', '갤러리'],
            'blind': ['blind', '블라인드', 'teamblind'],
            'bbc': ['bbc', 'british broadcasting'],
            'lemmy': ['lemmy', 'fediverse']
        }
    
    async def detect_site_type(self, url_or_input: str) -> str:
        """URL 또는 입력에서 사이트 타입 자동 감지"""
        if not url_or_input:
            return "universal"
        
        url_or_input = url_or_input.lower().strip()
        
        # URL이 아닌 경우 키워드로 처리
        if not url_or_input.startswith('http'):
            return self._detect_by_keyword(url_or_input)
        
        try:
            domain = urlparse(url_or_input).netloc.lower()
            
            # 도메인 기반 매칭
            for site_type, domains in self.site_patterns.items():
                if any(domain_pattern in domain for domain_pattern in domains):
                    logger.info(f"🎯 사이트 감지: {site_type} (도메인: {domain})")
                    return site_type
            
            # Lemmy 인스턴스 추가 확인 (동적 감지)
            if await self._is_lemmy_instance(domain):
                logger.info(f"🎯 Lemmy 인스턴스 감지: {domain}")
                return 'lemmy'
            
            # 알 수 없는 사이트는 범용으로 처리
            logger.info(f"❓ 알 수 없는 사이트: {domain} → universal로 처리")
            return 'universal'
                
        except Exception as e:
            logger.warning(f"URL 파싱 오류: {e}")
            return 'universal'
    
    def _detect_by_keyword(self, input_text: str) -> str:
        """키워드 기반 사이트 감지"""
        input_lower = input_text.lower()
        
        for site_type, keywords in self.keyword_patterns.items():
            if any(keyword in input_lower for keyword in keywords):
                logger.info(f"🎯 키워드 기반 감지: {site_type}")
                return site_type
        
        return "keyword"
    
    async def _is_lemmy_instance(self, domain: str) -> bool:
        """Lemmy 인스턴스인지 확인 (API 호출)"""
        try:
            # Lemmy 인스턴스는 보통 /api/v3/site 엔드포인트를 가집니다
            import aiohttp
            
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.get(
                        f"https://{domain}/api/v3/site", 
                        timeout=aiohttp.ClientTimeout(total=5)
                    ) as response:
                        if response.status == 200:
                            data = await response.json()
                            # Lemmy 응답 구조 확인
                            if 'site_view' in data or 'version' in data:
                                return True
                except:
                    pass
            
            return False
            
        except Exception:
            return False
    
    def extract_board_identifier(self, url: str, site_type: str) -> str:
        """URL에서 게시판 식별자 추출"""
        try:
            if site_type == 'reddit':
                import re
                match = re.search(r'/r/([^/]+)', url)
                return match.group(1) if match else url
                
            elif site_type == 'dcinside':
                import re
                match = re.search(r'[?&]id=([^&]+)', url)
                return match.group(1) if match else url
                
            elif site_type == 'blind':
                return url
                
            elif site_type == 'bbc':
                return url
                
            elif site_type == 'lemmy':
                if '/c/' in url:
                    parts = url.split('/c/')
                    if len(parts) > 1:
                        community_part = parts[1].split('/')[0]
                        domain = urlparse(url).netloc
                        return f"{community_part}@{domain}"
                return url
                
            else:
                return url
                
        except Exception as e:
            logger.warning(f"게시판 식별자 추출 오류: {e}")
            return url
    
    def get_supported_sites(self) -> list:
        """지원되는 사이트 목록 반환"""
        return list(self.site_patterns.keys()) + ['universal']
    
    def get_site_info(self, site_type: str) -> dict:
        """사이트 정보 반환"""
        site_info = {
            'reddit': {
                'name': 'Reddit',
                'description': 'The front page of the internet',
                'example_url': 'https://reddit.com/r/python'
            },
            'dcinside': {
                'name': 'DCInside',
                'description': '디시인사이드 갤러리',
                'example_url': 'https://gall.dcinside.com/board/lists/?id=programming'
            },
            'blind': {
                'name': 'Blind',
                'description': '직장인 익명 커뮤니티',
                'example_url': 'https://www.teamblind.com/kr/topics'
            },
            'bbc': {
                'name': 'BBC',
                'description': 'British Broadcasting Corporation',
                'example_url': 'https://www.bbc.com/news'
            },
            'lemmy': {
                'name': 'Lemmy',
                'description': 'Fediverse 기반 분산 포럼',
                'example_url': 'https://lemmy.world/c/technology'
            },
            'universal': {
                'name': 'Universal',
                'description': '범용 웹사이트 크롤러',
                'example_url': 'https://example.com/board'
            }
        }
        
        return site_info.get(site_type, {
            'name': 'Unknown',
            'description': '알 수 없는 사이트',
            'example_url': ''
        })