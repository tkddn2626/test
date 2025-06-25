# core/site_detector.py - 통합 동적 사이트 감지기
"""
🔍 통합 동적 사이트 감지기
- 자동으로 URL/입력에서 사이트 타입 감지
- 동적 크롤러 탐지 및 등록
- 실제 사용 가능한 크롤러와 연동
"""

import logging
import importlib.util
from urllib.parse import urlparse
from pathlib import Path
from typing import Optional, Dict, Set, List, Tuple, Any
import asyncio
import aiohttp

logger = logging.getLogger(__name__)

class DynamicSiteDetector:
    """통합 동적 사이트 감지기"""
    
    def __init__(self, crawlers_dir: Optional[Path] = None):
        """
        Args:
            crawlers_dir: 크롤러 디렉토리 경로 (기본값: backend/crawlers/)
        """
        # 크롤러 디렉토리 설정
        if crawlers_dir:
            self.crawlers_dir = crawlers_dir
        else:
            # main.py에서 호출될 때의 기본 경로
            current_file = Path(__file__).parent  # core/
            self.crawlers_dir = current_file.parent / "crawlers"  # backend/crawlers/
        
        # 동적으로 발견된 정보
        self.available_crawlers: Set[str] = set()
        self.crawl_functions: Dict[str, Any] = {}
        self.crawler_metadata: Dict[str, Dict] = {}
        
        # 기본 사이트 패턴 (백업용)
        self.fallback_patterns = {
            'reddit': {
                'domains': ['reddit.com', 'www.reddit.com', 'old.reddit.com', 'new.reddit.com'],
                'keywords': ['reddit', 'subreddit', '/r/'],
                'url_patterns': [r'/r/([^/]+)']
            },
            'dcinside': {
                'domains': ['dcinside.com', 'gall.dcinside.com', 'm.dcinside.com'],
                'keywords': ['dcinside', 'dcin', '디시', '갤러리'],
                'url_patterns': [r'[?&]id=([^&]+)']
            },
            'blind': {
                'domains': ['teamblind.com', 'blind.com', 'www.teamblind.com'],
                'keywords': ['blind', '블라인드', 'teamblind'],
                'url_patterns': []
            },
            'bbc': {
                'domains': ['bbc.com', 'www.bbc.com', 'bbc.co.uk', 'www.bbc.co.uk'],
                'keywords': ['bbc', 'british broadcasting'],
                'url_patterns': []
            },
            'lemmy': {
                'domains': [
                    'lemmy.world', 'lemmy.ml', 'beehaw.org', 'sh.itjust.works',
                    'feddit.de', 'lemm.ee', 'sopuli.xyz', 'lemmy.ca'
                ],
                'keywords': ['lemmy', 'fediverse', '@lemmy'],
                'url_patterns': [r'/c/([^/]+)']
            }
        }
        
        # Lemmy 인스턴스 캐시
        self.lemmy_instances_cache = set()
        self.cache_initialized = False
        
        # 초기화
        self._initialize()
    
    def _initialize(self):
        """초기화: 동적 크롤러 탐지"""
        logger.info(f"🔍 동적 사이트 감지기 초기화: {self.crawlers_dir}")
        
        # 1. 크롤러 파일 탐지
        self._discover_crawlers()
        
        # 2. 크롤러 함수 로드
        self._load_crawler_functions()
        
        # 3. 로그 출력
        logger.info(f"✅ 발견된 크롤러: {sorted(self.available_crawlers)}")
        logger.info(f"✅ 로드된 함수: {list(self.crawl_functions.keys())}")
    
    def _discover_crawlers(self):
        """크롤러 파일들을 동적으로 발견"""
        if not self.crawlers_dir.exists():
            logger.warning(f"⚠️ 크롤러 디렉토리 없음: {self.crawlers_dir}")
            return
        
        for py_file in self.crawlers_dir.glob("*.py"):
            # 제외할 파일들
            if py_file.name.startswith('_') or py_file.stem == '__init__':
                continue
            
            crawler_name = py_file.stem
            
            try:
                # 파일에서 크롤링 함수 확인
                spec = importlib.util.spec_from_file_location(f"crawlers.{crawler_name}", py_file)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    # 크롤링 함수 패턴 확인
                    crawl_function_patterns = [
                        f'crawl_{crawler_name}_board',
                        f'fetch_posts',
                        f'crawl_{crawler_name}',
                        f'{crawler_name}_crawl'
                    ]
                    
                    has_crawl_function = any(hasattr(module, func) for func in crawl_function_patterns)
                    
                    if has_crawl_function:
                        self.available_crawlers.add(crawler_name)
                        
                        # 메타데이터 수집
                        self.crawler_metadata[crawler_name] = {
                            'file_path': str(py_file),
                            'display_name': getattr(module, 'DISPLAY_NAME', crawler_name.title()),
                            'description': getattr(module, 'DESCRIPTION', f'{crawler_name} 크롤러'),
                            'version': getattr(module, 'VERSION', '1.0.0'),
                            'supported_domains': getattr(module, 'SUPPORTED_DOMAINS', []),
                            'keywords': getattr(module, 'KEYWORDS', [])
                        }
                        
                        logger.debug(f"✅ 크롤러 발견: {crawler_name}")
                    else:
                        logger.debug(f"⚠️ 크롤링 함수 없음: {crawler_name}")
            
            except Exception as e:
                logger.debug(f"⚠️ 크롤러 확인 실패 {crawler_name}: {e}")
        
        # AutoCrawler universal 기능 추가
        self.available_crawlers.add('universal')
        self.crawler_metadata['universal'] = {
            'display_name': 'Universal Crawler',
            'description': 'AutoCrawler 범용 크롤링',
            'version': '2.0.0',
            'supported_domains': ['*'],
            'keywords': ['universal', 'generic']
        }
    
    def _load_crawler_functions(self):
        """크롤러 함수들을 동적으로 로드"""
        # 개별 크롤러 함수들 import 시도
        crawler_imports = {
            'reddit': ('crawlers.reddit', 'fetch_posts'),
            'dcinside': ('crawlers.dcinside', 'crawl_dcinside_board'),
            'blind': ('crawlers.blind', 'crawl_blind_board'),
            'lemmy': ('crawlers.lemmy', 'crawl_lemmy_board'),
            'bbc': ('crawlers.bbc', 'crawl_bbc_board')
        }
        
        for crawler_name, (module_path, function_name) in crawler_imports.items():
            if crawler_name in self.available_crawlers:
                try:
                    module = __import__(module_path, fromlist=[function_name])
                    crawler_function = getattr(module, function_name)
                    self.crawl_functions[crawler_name] = crawler_function
                    logger.debug(f"✅ {crawler_name} 함수 로드 성공")
                    
                    # BBC의 경우 추가 함수도 로드
                    if crawler_name == 'bbc' and hasattr(module, 'detect_bbc_url_and_extract_info'):
                        self.crawl_functions['detect_bbc_url_and_extract_info'] = getattr(module, 'detect_bbc_url_and_extract_info')
                
                except ImportError as e:
                    logger.debug(f"⚠️ {crawler_name} 함수 로드 실패: {e}")
                except Exception as e:
                    logger.debug(f"⚠️ {crawler_name} 처리 오류: {e}")
    
    async def detect_site_type(self, url_or_input: str) -> str:
        """URL 또는 입력에서 사이트 타입 자동 감지"""
        if not url_or_input:
            return "universal"
        
        url_or_input = url_or_input.lower().strip()
        
        # 1. URL 기반 감지
        if url_or_input.startswith('http'):
            detected = await self._detect_by_url(url_or_input)
            if detected != 'universal':
                return detected
        
        # 2. 키워드 기반 감지
        detected = self._detect_by_keyword(url_or_input)
        if detected != 'universal':
            return detected
        
        # 3. 동적 크롤러 메타데이터 기반 감지
        detected = self._detect_by_crawler_metadata(url_or_input)
        if detected != 'universal':
            return detected
        
        # 4. 기본값
        logger.info(f"❓ 알 수 없는 입력: {url_or_input[:50]} → universal로 처리")
        return 'universal'
    
    async def _detect_by_url(self, url: str) -> str:
        """URL 기반 사이트 감지"""
        try:
            domain = urlparse(url).netloc.lower()
            
            # 1. 기본 패턴 확인
            for site_type, patterns in self.fallback_patterns.items():
                if any(domain_pattern in domain for domain_pattern in patterns['domains']):
                    logger.debug(f"🎯 도메인 매칭: {site_type} ({domain})")
                    return site_type
            
            # 2. 동적 크롤러 메타데이터 확인
            for crawler_name, metadata in self.crawler_metadata.items():
                supported_domains = metadata.get('supported_domains', [])
                if any(supported_domain in domain for supported_domain in supported_domains):
                    logger.debug(f"🎯 동적 크롤러 도메인 매칭: {crawler_name} ({domain})")
                    return crawler_name
            
            # 3. Lemmy 인스턴스 동적 확인
            if await self._is_lemmy_instance(domain):
                logger.info(f"🎯 Lemmy 인스턴스 감지: {domain}")
                return 'lemmy'
            
            return 'universal'
        
        except Exception as e:
            logger.warning(f"URL 분석 오류: {e}")
            return 'universal'
    
    def _detect_by_keyword(self, input_text: str) -> str:
        """키워드 기반 사이트 감지"""
        input_lower = input_text.lower()
        
        # 1. 기본 키워드 패턴
        for site_type, patterns in self.fallback_patterns.items():
            if any(keyword in input_lower for keyword in patterns['keywords']):
                logger.debug(f"🎯 키워드 매칭: {site_type}")
                return site_type
        
        # 2. 동적 크롤러 키워드
        for crawler_name, metadata in self.crawler_metadata.items():
            keywords = metadata.get('keywords', [])
            if any(keyword.lower() in input_lower for keyword in keywords):
                logger.debug(f"🎯 동적 키워드 매칭: {crawler_name}")
                return crawler_name
        
        return 'universal'
    
    def _detect_by_crawler_metadata(self, input_text: str) -> str:
        """크롤러 메타데이터 기반 감지"""
        input_lower = input_text.lower()
        
        # 크롤러 이름 자체로 매칭
        for crawler_name in self.available_crawlers:
            if crawler_name.lower() in input_lower:
                logger.debug(f"🎯 크롤러명 매칭: {crawler_name}")
                return crawler_name
        
        return 'universal'
    
    async def _is_lemmy_instance(self, domain: str) -> bool:
        """Lemmy 인스턴스인지 동적 확인"""
        if domain in self.lemmy_instances_cache:
            return True
        
        try:
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.get(
                        f"https://{domain}/api/v3/site", 
                        timeout=aiohttp.ClientTimeout(total=5)
                    ) as response:
                        if response.status == 200:
                            data = await response.json()
                            if 'site_view' in data or 'version' in data:
                                self.lemmy_instances_cache.add(domain)
                                logger.debug(f"🆕 새로운 Lemmy 인스턴스 발견: {domain}")
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
            
            elif site_type == 'lemmy':
                if '/c/' in url:
                    parts = url.split('/c/')
                    if len(parts) > 1:
                        community_part = parts[1].split('/')[0]
                        domain = urlparse(url).netloc
                        return f"{community_part}@{domain}"
                return url
            
            elif site_type in ['blind', 'bbc']:
                return url
            
            else:
                return url
        
        except Exception as e:
            logger.warning(f"게시판 식별자 추출 오류: {e}")
            return url
    
    def is_crawler_functional(self, site_type: str) -> bool:
        """크롤러가 실제로 사용 가능한지 확인"""
        return site_type in self.crawl_functions or site_type == 'universal'
    
    def get_crawler_priority(self, site_type: str) -> Tuple[str, str]:
        """
        크롤러 우선순위 결정
        Returns: (priority_type, reason)
        """
        if site_type in self.crawl_functions and site_type != 'universal':
            return ('direct', f'{site_type} 전용 크롤러 사용 가능')
        elif site_type in self.available_crawlers:
            return ('auto_crawler', f'{site_type} AutoCrawler로 처리')
        else:
            return ('universal', 'Universal 크롤러로 처리')
    
    def get_supported_sites(self) -> List[str]:
        """지원되는 사이트 목록 반환"""
        return sorted(list(self.available_crawlers))
    
    def get_functional_crawlers(self) -> List[str]:
        """실제 작동하는 크롤러 목록 반환"""
        functional = list(self.crawl_functions.keys())
        if 'universal' not in functional:
            functional.append('universal')
        return sorted(functional)
    
    def get_crawler_info(self, site_type: str) -> Dict[str, Any]:
        """크롤러 정보 반환"""
        base_info = {
            'site_type': site_type,
            'available': site_type in self.available_crawlers,
            'functional': self.is_crawler_functional(site_type)
        }
        
        if site_type in self.crawler_metadata:
            base_info.update(self.crawler_metadata[site_type])
        
        priority, reason = self.get_crawler_priority(site_type)
        base_info.update({
            'priority': priority,
            'priority_reason': reason
        })
        
        return base_info
    
    def get_system_status(self) -> Dict[str, Any]:
        """시스템 상태 반환"""
        return {
            'crawlers_dir': str(self.crawlers_dir),
            'crawlers_dir_exists': self.crawlers_dir.exists(),
            'total_discovered': len(self.available_crawlers),
            'functional_count': len(self.get_functional_crawlers()),
            'available_crawlers': list(self.available_crawlers),
            'functional_crawlers': self.get_functional_crawlers(),
            'crawler_metadata': self.crawler_metadata,
            'lemmy_instances_discovered': len(self.lemmy_instances_cache),
            'discovery_method': 'Dynamic file scanning + metadata analysis'
        }

# 백워드 호환성을 위한 기존 SiteDetector 클래스
class SiteDetector(DynamicSiteDetector):
    """기존 SiteDetector와의 호환성을 위한 래퍼"""
    
    def __init__(self):
        super().__init__()
        logger.info("📡 SiteDetector (호환성 모드) 초기화 완료")