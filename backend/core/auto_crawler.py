# core/auto_crawler.py - 완전한 통합 자동 크롤러
"""
🔥 통합 자동 크롤러 (순환 import 해결 버전)
모든 사이트를 자동으로 감지하고 적절한 크롤러로 크롤링을 수행합니다.
"""

import logging
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

class AutoCrawler:
    """🔥 통합 자동 크롤러"""
    
    def __init__(self):
        # 지연 import로 순환 참조 방지
        self.site_detector = None
        self.unified_crawler = None
        self._crawlers_cache = {}
        self._initialization_attempted = False
        
        # 🔥 지원하는 사이트 목록에 'x' 추가
        self.supported_sites = [
            'reddit', 'lemmy', 'dcinside', 'blind', 'bbc', 'x', 'universal'  # ← 'x' 추가!
        ]
        
        # 🔥 사이트별 매개변수 매핑에 X 추가
        self.site_param_mapping = {
            'reddit': {
                'target_param': 'subreddit_name',
                'module': 'crawlers.reddit',
                'function': 'fetch_posts',
                'supported_params': [
                    'limit', 'sort', 'time_filter', 'websocket',
                    'min_views', 'min_likes', 'start_date', 'end_date',
                    'enforce_date_limit', 'start_index', 'end_index'
                ],
                'unsupported_params': ['min_comments']
            },
            'lemmy': {
                'target_param': 'community_input',
                'module': 'crawlers.lemmy',
                'function': 'crawl_lemmy_board',
                'supported_params': [
                    'limit', 'sort', 'min_views', 'min_likes',
                    'time_filter', 'start_date', 'end_date', 'websocket',
                    'enforce_date_limit', 'start_index', 'end_index'
                ],
                'unsupported_params': ['min_comments']
            },
            'dcinside': {
                'target_param': 'board_name',
                'module': 'crawlers.dcinside',
                'function': 'crawl_dcinside_board',
                'supported_params': [
                    'limit', 'sort', 'min_views', 'min_likes', 'min_comments',
                    'time_filter', 'start_date', 'end_date', 'websocket',
                    'enforce_date_limit', 'start_index', 'end_index'
                ],
                'unsupported_params': []
            },
            'blind': {
                'target_param': 'board_name',
                'module': 'crawlers.blind',
                'function': 'crawl_blind_board',
                'supported_params': [
                    'limit', 'sort', 'min_views', 'min_likes', 'min_comments',
                    'time_filter', 'start_date', 'end_date', 'websocket',
                    'enforce_date_limit', 'start_index', 'end_index'
                ],
                'unsupported_params': []
            },
            'bbc': {
                'target_param': 'board_name',
                'module': 'crawlers.bbc',
                'function': 'crawl_bbc_board',
                'supported_params': [
                    'limit', 'sort', 'min_views', 'min_likes', 'min_comments',
                    'time_filter', 'start_date', 'end_date', 'websocket',
                    'board_name', 'enforce_date_limit', 'start_index', 'end_index'
                ],
                'unsupported_params': []
            },
            # 🔥 X 사이트 매핑 추가
            'x': {
                'target_param': 'board_input',
                'module': 'crawlers.x',
                'function': 'crawl_x_board',
                'supported_params': [
                    'limit', 'sort', 'min_views', 'min_likes', 'min_retweets',
                    'time_filter', 'start_date', 'end_date', 'websocket',
                    'enforce_date_limit', 'start_index', 'end_index',
                    'include_media', 'include_nsfw'
                ],
                'unsupported_params': ['min_comments']  # X는 min_comments 대신 min_retweets 사용
            },
            'universal': {
                'target_param': 'input_data',
                'module': 'core.auto_crawler',
                'function': 'crawl',
                'supported_params': [
                    'limit', 'sort', 'min_views', 'min_likes', 'min_comments',
                    'time_filter', 'start_date', 'end_date', 'websocket',
                    'enforce_date_limit', 'start_index', 'end_index'
                ],
                'unsupported_params': []
            }
        }

    
    def _initialize_dependencies(self):
        """의존성들을 지연 로드 (한 번만 시도)"""
        if self._initialization_attempted:
            return
        
        self._initialization_attempted = True
        
        try:
            # SiteDetector 로드
            from .site_detector import SiteDetector
            self.site_detector = SiteDetector()
            logger.info("✅ SiteDetector 로드 성공")
        except ImportError as e:
            logger.warning(f"⚠️ SiteDetector 로드 실패: {e}")
            self.site_detector = None
        
        try:
            # UnifiedCrawler 로드 (선택적)
            from .unified_crawler import unified_crawler
            self.unified_crawler = unified_crawler
            logger.info("✅ UnifiedCrawler 로드 성공")
        except ImportError as e:
            logger.warning(f"⚠️ UnifiedCrawler 로드 실패 (폴백 사용): {e}")
            self.unified_crawler = None
  
    async def crawl(self, input_data: str, **config) -> List[Dict]:
        """
        통합 크롤링 메인 메서드
        
        Args:
            input_data: 크롤링 대상 (게시판명, URL)
            **config: 크롤링 설정 (force_site_type 포함 가능)
        
        Returns:
            크롤링 결과 리스트
        """
        start_time = datetime.now()
        
        try:
            # 의존성 초기화
            self._initialize_dependencies()
            
            # 1. 사이트 감지 - force_site_type이 있으면 사용 (재감지 방지)
            force_applied = False  # 🔥 추가: force_site_type 적용 여부 추적
            if 'force_site_type' in config:
                site_type = config.pop('force_site_type')
                force_applied = True  # 🔥 추가
                logger.info(f"🎯 강제 지정된 사이트: {site_type}")
            else:
                site_type = await self._detect_site_type(input_data)
                logger.info(f"🔍 자동 감지된 사이트: {site_type}")
            
            # 2. 게시판 식별자 추출
            board_identifier = self._extract_board_identifier(input_data, site_type)
            logger.info(f"📋 게시판 식별자: {board_identifier}")
            
            # 3. 크롤링 설정 준비
            crawl_config = self._prepare_crawl_config(site_type, board_identifier, **config)
            
            # 4. 크롤링 실행
            try:
                logger.info(f"🚀 AutoCrawler 크롤링 실행: {site_type}")
                results = await self._execute_crawl(site_type, **crawl_config)
            except Exception as e:
                # 🔥 수정: force_site_type이 적용된 경우 폴백하지 않음
                if force_applied:
                    logger.error(f"❌ force_site_type={site_type} 크롤링 실패, 폴백 금지")
                    raise e  # 🔥 수정: 바로 오류 발생
                
                # 기존 로직: 자동 감지된 경우에만 폴백 허용
                logger.warning(f"AutoCrawler 실패, 통합 크롤러로 폴백: {e}")
                if self.unified_crawler:
                    # 통합 크롤러 폴백
                    logger.info(f"🚀 통합 크롤링 폴백 실행: {site_type}")
                    results = await self.unified_crawler.unified_crawl(
                        site_type, 
                        board_identifier, 
                        **crawl_config
                    )
                else:
                    raise e
            
            # 5. 결과 후처리
            processed_results = self._post_process_results(results, site_type, config)
            
            elapsed = (datetime.now() - start_time).total_seconds()
            logger.info(f"✅ 크롤링 완료: {len(processed_results)}개 결과 ({elapsed:.2f}초)")
            
            return processed_results
                
        except Exception as e:
            elapsed = (datetime.now() - start_time).total_seconds()
            logger.error(f"❌ AutoCrawler 오류 ({elapsed:.2f}초): {e}")
            raise
        
    async def _detect_site_type(self, input_data: str) -> str:
        """사이트 타입 감지"""
        if self.site_detector:
            try:
                return await self.site_detector.detect_site_type(input_data)
            except Exception as e:
                logger.warning(f"SiteDetector 오류, 폴백 사용: {e}")
        
        # 폴백 사이트 감지
        return self._fallback_site_detection(input_data)
    
    def _extract_board_identifier(self, input_data: str, site_type: str) -> str:
        """게시판 식별자 추출"""
        if self.site_detector:
            try:
                return self.site_detector.extract_board_identifier(input_data, site_type)
            except Exception as e:
                logger.warning(f"식별자 추출 오류, 원본 사용: {e}")
        
        # 폴백: 간단한 식별자 추출
        return self._fallback_extract_identifier(input_data, site_type)
    
    def _fallback_site_detection(self, input_data: str) -> str:
        """폴백 사이트 감지"""
        input_lower = input_data.lower()
        
        # URL 기반 감지
        if input_data.startswith('http'):
            parsed = urlparse(input_data)
            domain = parsed.netloc.lower()
            
            if 'reddit.com' in domain:
                return 'reddit'
            elif 'x.com' in domain or 'twitter.com' in domain:  # 🔥 X 도메인 추가
                return 'x'
            elif 'dcinside.com' in domain:
                return 'dcinside'
            elif 'teamblind.com' in domain or 'blind.com' in domain:
                return 'blind'
            elif 'bbc.com' in domain or 'bbc.co.uk' in domain:
                return 'bbc'
            elif any(lemmy_domain in domain for lemmy_domain in ['lemmy.', 'beehaw.', 'sh.itjust.works']):
                return 'lemmy'
            else:
                logger.info(f"🌐 Universal 사이트로 감지: {input_data}")
                return 'universal'
        
        # 키워드 기반 감지
        if any(word in input_lower for word in ['reddit', 'subreddit']):
            return 'reddit'
        elif any(word in input_lower for word in ['lemmy', '레미']):
            return 'lemmy'
        elif any(word in input_lower for word in ['dcinside', 'dc', '디시', '갤러리']):
            return 'dcinside'
        elif any(word in input_lower for word in ['blind', '블라인드']):
            return 'blind'
        elif any(word in input_lower for word in ['bbc', 'british']):
            return 'bbc'
        # 🔥 X 키워드 감지 추가
        elif any(word in input_lower for word in ['x.com', 'twitter.com', 'tweet', '@']) or input_lower == 'x':
            return 'x'
        else:
            logger.info(f"🌐 키워드 매칭 실패, Universal로 처리: {input_data}")
            return 'universal'
    
    def _fallback_extract_identifier(self, input_data: str, site_type: str) -> str:
        """폴백 식별자 추출"""
        if site_type == 'reddit' and '/r/' in input_data:
            import re
            match = re.search(r'/r/([^/]+)', input_data)
            return match.group(1) if match else input_data
        elif site_type == 'lemmy' and '/c/' in input_data:
            parts = input_data.split('/c/')
            if len(parts) > 1:
                from urllib.parse import urlparse
                try:
                    domain = urlparse(input_data).netloc
                    community = parts[1].split('/')[0]
                    return f"{community}@{domain}"
                except:
                    pass
        elif site_type == 'dcinside' and '?id=' in input_data:
            import re
            match = re.search(r'[?&]id=([^&]+)', input_data)
            return match.group(1) if match else input_data
        
        return input_data
    
    def _prepare_crawl_config(self, site_type: str, board_identifier: str, **config) -> Dict[str, Any]:
        """사이트별 크롤링 설정 준비"""
        if site_type not in self.site_param_mapping:
            raise ValueError(f"지원하지 않는 사이트: {site_type}")
        
        site_config = self.site_param_mapping[site_type]
        
        # 기본 설정
        crawl_config = {
            site_config['target_param']: board_identifier
        }
        
        # 지원하는 매개변수만 추가
        for param in site_config['supported_params']:
            if param in config and config[param] is not None:
                crawl_config[param] = config[param]
        
        # 공통 매개변수 매핑
        common_mappings = {
            'start': 'start_index',
            'end': 'end_index',
            'board': site_config['target_param'],
            'input': site_config['target_param'],
            'board_identifier': site_config['target_param']
        }
        
        for source, target in common_mappings.items():
            if source in config and target in site_config['supported_params']:
                crawl_config[target] = config[source]
        
        # 사이트별 특수 처리
        crawl_config = self._apply_site_specific_processing(site_type, crawl_config, **config)
        
        # 지원하지 않는 매개변수 제거 및 경고
        unsupported = site_config['unsupported_params']
        for param in unsupported:
            if param in crawl_config:
                removed_value = crawl_config.pop(param)
                logger.warning(f"⚠️ {site_type}에서 지원하지 않는 매개변수 제거: {param}={removed_value}")
        
        # None 값 제거
        crawl_config = {k: v for k, v in crawl_config.items() if v is not None}
        
        logger.debug(f"크롤링 설정 준비 완료 ({site_type}): {list(crawl_config.keys())}")
        return crawl_config
    
    def _apply_site_specific_processing(self, site_type: str, config: Dict, **original_config) -> Dict:
        """사이트별 특수 처리"""
        
        if site_type == 'reddit':
            # Reddit 정렬 방식 매핑
            sort_mapping = {
                "popular": "hot", "recommend": "top", "recent": "new",
                "comments": "top"
            }
            if 'sort' in config and config['sort'] in sort_mapping:
                config['sort'] = sort_mapping[config['sort']]
                
            # Reddit은 subreddit 이름에서 /r/ 제거
            if 'subreddit_name' in config:
                subreddit = config['subreddit_name']
                if subreddit.startswith('/r/'):
                    config['subreddit_name'] = subreddit[3:]
                elif subreddit.startswith('r/'):
                    config['subreddit_name'] = subreddit[2:]
        
        elif site_type == 'lemmy':
            # Lemmy 커뮤니티 형식 처리
            if 'community_input' in config:
                community = config['community_input']
                if '@' not in community and not community.startswith('http'):
                    # 인스턴스가 없으면 기본값 추가
                    config['community_input'] = f"{community}@lemmy.world"
        
        elif site_type == 'bbc':
            # BBC는 board_name이 빈 문자열로 필요할 수 있음
            if 'board_name' not in config:
                config['board_name'] = ""
        
        elif site_type == 'universal':
            # Universal도 board_name 처리
            if 'board_name' not in config:
                config['board_name'] = ""
        
        return config
    
    async def _execute_crawl(self, site_type: str, **config) -> List[Dict]:
        """크롤링 실행"""
        if site_type == 'universal':
            # Universal 크롤링은 AutoCrawler 내부에서 직접 처리
            return await self._crawl_universal_internal(**config)
        else:
            # 다른 사이트는 직접 크롤러 호출
            return await self._direct_crawl(site_type, **config)
    
    async def _crawl_universal_internal(self, **config) -> List[Dict]:
        """Universal 크롤링 내부 구현"""
        board_url = config.get('board_url', '')
        
        if not board_url:
            logger.warning("Universal 크롤링: URL이 제공되지 않음")
            return []
        
        logger.info(f"🌐 Universal 크롤링 시작: {board_url}")
        
        try:
            # 간단한 웹페이지 크롤링 구현
            import requests
            from bs4 import BeautifulSoup
            import re
            from urllib.parse import urljoin, urlparse
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            # URL이 http로 시작하지 않으면 https 추가
            if not board_url.startswith('http'):
                board_url = 'https://' + board_url
            
            logger.info(f"📡 요청 URL: {board_url}")
            
            response = requests.get(board_url, headers=headers, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # 일반적인 링크 패턴 찾기
            results = []
            
            # 다양한 셀렉터로 링크 찾기
            selectors = [
                'a[href]',  # 모든 링크
                'h1 a, h2 a, h3 a, h4 a',  # 제목 링크
                '.title a, .headline a, .article-title a',  # 클래스 기반
                '[class*="title"] a, [class*="headline"] a'  # 부분 클래스 매칭
            ]
            
            all_links = []
            for selector in selectors:
                links = soup.select(selector)
                all_links.extend(links)
            
            # 중복 제거 (href 기준)
            seen_hrefs = set()
            unique_links = []
            for link in all_links:
                href = link.get('href')
                if href and href not in seen_hrefs:
                    seen_hrefs.add(href)
                    unique_links.append(link)
            
            logger.info(f"🔗 발견된 고유 링크: {len(unique_links)}개")
            
            # 제목이 될 수 있는 요소들 처리
            for i, link in enumerate(unique_links[:config.get('limit', 20)]):
                href = link.get('href')
                if not href:
                    continue
                    
                # 상대 URL을 절대 URL로 변환
                full_url = urljoin(board_url, href)
                
                # 링크 텍스트 추출
                title = link.get_text(strip=True)
                
                # 제목이 너무 짧거나 의미없는 경우 스킵
                if not title or len(title) < 5:
                    continue
                
                # 공통적으로 제외할 텍스트들
                skip_patterns = ['more', 'read more', '더보기', 'click here', '클릭', 'home', 'menu']
                if any(pattern in title.lower() for pattern in skip_patterns):
                    continue
                
                # 기본 정보 추출
                result = {
                    '번호': str(i + 1),
                    '원제목': title,
                    '번역제목': '',
                    '링크': full_url,
                    '본문': '',
                    '조회수': 0,
                    '추천수': 0,
                    '댓글수': 0,
                    '작성일': '',
                    '작성자': '',
                    '사이트': urlparse(board_url).netloc,
                    '크롤링방식': 'AutoCrawler-Universal'
                }
                
                results.append(result)
            
            logger.info(f"✅ Universal 크롤링 완료: {len(results)}개 링크")
            
            if not results:
                logger.warning(f"⚠️ {board_url}에서 유효한 링크를 찾을 수 없습니다")
            
            return results
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Universal 크롤링 네트워크 오류: {e}")
            return []
        except Exception as e:
            logger.error(f"❌ Universal 크롤링 오류: {e}")
            return []
    
    async def _direct_crawl(self, site_type: str, **config) -> List[Dict]:
        """직접 크롤러 호출 (폴백)"""
        site_config = self.site_param_mapping[site_type]
        module_name = site_config['module']
        function_name = site_config['function']
        
        if not module_name:
            raise ValueError(f"모듈이 지정되지 않은 사이트: {site_type}")
        
        try:
            # 크롤러 모듈을 캐시에서 가져오거나 새로 로드
            if module_name not in self._crawlers_cache:
                crawler_module = __import__(module_name, fromlist=[function_name])
                crawler_function = getattr(crawler_module, function_name)
                self._crawlers_cache[module_name] = crawler_function
                logger.debug(f"크롤러 모듈 로드: {module_name}.{function_name}")
            
            crawler_function = self._crawlers_cache[module_name]
            
            # 크롤링 실행
            if asyncio.iscoroutinefunction(crawler_function):
                result = await crawler_function(**config)
            else:
                result = crawler_function(**config)
            
            return result or []
                
        except ImportError as e:
            logger.error(f"크롤러 모듈 import 실패 ({site_type}): {e}")
            return []
        except Exception as e:
            logger.error(f"직접 크롤링 오류 ({site_type}): {e}")
            raise
    
    def _post_process_results(self, results: List[Dict], site_type: str, config: Dict) -> List[Dict]:
        """결과 후처리"""
        if not results:
            return []
        
        processed_results = []
        
        for result in results:
            # 기본 필드 정규화
            normalized_result = self._normalize_result_fields(result, site_type)
            
            # 추가 후처리
            if config.get('translate', False):
                # 번역 관련 처리는 여기서 수행하지 않음 (상위 레벨에서 처리)
                pass
            
            processed_results.append(normalized_result)
        
        # 정렬 및 필터링
        processed_results = self._apply_final_filters(processed_results, config)
        
        return processed_results
    
    def _normalize_result_fields(self, result: Dict, site_type: str) -> Dict:
        """결과 필드 정규화"""
        # 이미 정규화된 결과라면 그대로 반환
        if all(key in result for key in ['원제목', '링크', '작성일']):
            return result
        
        # 사이트별 필드 매핑 (필요한 경우)
        normalized = result.copy()
        
        # 기본 필드들이 없는 경우 빈 값으로 설정
        default_fields = {
            '번호': '',
            '원제목': '',
            '번역제목': '',
            '링크': '',
            '본문': '',
            '조회수': 0,
            '추천수': 0,
            '댓글수': 0,
            '작성일': ''
        }
        
        for field, default_value in default_fields.items():
            if field not in normalized:
                normalized[field] = default_value
        
        return normalized
    
    def _apply_final_filters(self, results: List[Dict], config: Dict) -> List[Dict]:
        """최종 필터링 및 정렬"""
        filtered_results = results
        
        # 범위 필터링
        start_index = config.get('start_index', config.get('start', 1))
        end_index = config.get('end_index', config.get('end', len(results)))
        
        if start_index > 1 or end_index < len(results):
            # 1-based index를 0-based로 변환
            start_idx = max(0, start_index - 1)
            end_idx = min(len(results), end_index)
            filtered_results = filtered_results[start_idx:end_idx]
        
        return filtered_results
    
    async def validate_crawl_request(self, input_data: str, **config) -> Tuple[bool, List[str]]:
        """크롤링 요청 유효성 검사"""
        errors = []
        
        try:
            # 1. 입력 데이터 검증
            if not input_data or not input_data.strip():
                errors.append("크롤링 대상이 입력되지 않았습니다")
                return False, errors
            
            # 2. 사이트 감지
            site_type = await self._detect_site_type(input_data)
            if site_type not in self.supported_sites:
                errors.append(f"지원하지 않는 사이트입니다: {site_type}")
                return False, errors
            
            # 3. 매개변수 검증
            is_valid, param_errors = self._validate_parameters(site_type, **config)
            if not is_valid:
                errors.extend(param_errors)
            
            # 4. 범위 검증
            start_index = config.get('start_index', config.get('start', 1))
            end_index = config.get('end_index', config.get('end', 20))
            
            if start_index < 1:
                errors.append("시작 인덱스는 1 이상이어야 합니다")
            
            if end_index < start_index:
                errors.append("종료 인덱스는 시작 인덱스보다 크거나 같아야 합니다")
            
            if end_index - start_index > 100:
                errors.append("한 번에 요청할 수 있는 게시물은 최대 100개입니다")
            
            return len(errors) == 0, errors
            
        except Exception as e:
            errors.append(f"검증 중 오류: {str(e)}")
            return False, errors
    
    def _validate_parameters(self, site_type: str, **config) -> Tuple[bool, List[str]]:
        """매개변수 유효성 검사"""
        if site_type not in self.site_param_mapping:
            return False, [f"지원하지 않는 사이트: {site_type}"]
        
        site_config = self.site_param_mapping[site_type]
        all_supported = site_config['supported_params'] + [site_config['target_param']]
        unsupported = site_config['unsupported_params']
        
        errors = []
        
        # 지원하지 않는 매개변수 확인
        common_alternatives = ['start', 'end', 'board', 'input', 'board_identifier']
        unsupported_params = [
            k for k in config.keys() 
            if k not in all_supported and k not in common_alternatives
        ]
        
        if unsupported_params:
            errors.append(f"{site_type}에서 지원하지 않는 매개변수: {unsupported_params}")
        
        # 명시적으로 지원하지 않는 매개변수 확인
        explicitly_unsupported = [k for k in config.keys() if k in unsupported]
        if explicitly_unsupported:
            errors.append(f"{site_type}에서 명시적으로 지원하지 않는 매개변수: {explicitly_unsupported}")
        
        return len(errors) == 0, errors
    
    def get_supported_crawlers(self) -> List[str]:
        """지원되는 크롤러 목록 반환"""
        if self.unified_crawler:
            try:
                registry_info = self.unified_crawler.get_registry_info()
                return registry_info.get('supported_sites', self.supported_sites)
            except:
                pass
        
        return self.supported_sites
    
    def get_crawler_info(self) -> Dict[str, Any]:
        """크롤러 정보 반환"""
        self._initialize_dependencies()
        
        return {
            'version': '2.0.0',
            'site_detector_available': self.site_detector is not None,
            'unified_crawler_available': self.unified_crawler is not None,
            'supported_sites': self.get_supported_crawlers(),
            'site_param_mapping': self.site_param_mapping,
            'auto_detection': True,
            'fallback_mode': self.unified_crawler is None,
            'cached_crawlers': list(self._crawlers_cache.keys()),
            'universal_support': 'Built-in AutoCrawler Universal'
        }
    
    def get_site_specific_help(self, site_type: str) -> Dict[str, Any]:
        """사이트별 도움말 정보"""
        if site_type not in self.site_param_mapping:
            return {"error": f"지원하지 않는 사이트: {site_type}"}
        
        site_config = self.site_param_mapping[site_type]
        
        help_info = {
            'reddit': {
                'format': 'subreddit_name or /r/subreddit_name or full URL',
                'examples': ['python', '/r/programming', 'https://reddit.com/r/askreddit'],
                'notes': 'Reddit 서브레딧 이름 또는 URL을 입력하세요'
            },
            'lemmy': {
                'format': 'community@instance or full URL',
                'examples': ['technology@lemmy.world', 'asklemmy@lemmy.ml', 'https://lemmy.world/c/technology'],
                'notes': '인스턴스가 없으면 자동으로 @lemmy.world가 추가됩니다'
            },
            'dcinside': {
                'format': 'gallery_name or gallery_id or full URL',
                'examples': ['programming', '프로그래밍', 'https://gall.dcinside.com/board/lists/?id=programming'],
                'notes': '갤러리 ID 또는 이름을 입력하세요'
            },
            'blind': {
                'format': 'topic_name or full URL',
                'examples': ['회사생활', '개발자', 'https://www.teamblind.com/kr/topics/회사생활'],
                'notes': '토픽 이름을 입력하세요'
            },
            'bbc': {
                'format': 'section_url',
                'examples': ['https://www.bbc.com/news', 'https://www.bbc.com/technology'],
                'notes': 'BBC 섹션 URL을 입력하세요'
            },
            'universal': {
                'format': 'full_url',
                'examples': ['https://example.com/forum', 'https://news.site.com'],
                'notes': '완전한 URL을 입력하세요. AutoCrawler가 자동으로 링크를 추출합니다.'
            }
        }
        
        base_help = help_info.get(site_type, {
            'format': 'site_specific_input',
            'examples': ['example'],
            'notes': '사이트별 형식을 확인하세요'
        })
        
        # 매개변수 정보 추가
        base_help.update({
            'target_parameter': site_config['target_param'],
            'supported_parameters': site_config['supported_params'],
            'unsupported_parameters': site_config['unsupported_params'],
            'module_info': {
                'module': site_config['module'] or 'AutoCrawler Internal',
                'function': site_config['function']
            }
        })
        
        return base_help