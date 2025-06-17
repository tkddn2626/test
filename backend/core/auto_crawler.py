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
        
        # 지원하는 사이트 목록
        self.supported_sites = [
            'reddit', 'lemmy', 'dcinside', 'blind', 'bbc', 'universal'
        ]
        
        # 사이트별 매개변수 매핑
        self.site_param_mapping = {
            'reddit': {
                'target_param': 'subreddit_name',
                'module': 'reddit',
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
                'module': 'lemmy',
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
                'module': 'dcinside',
                'function': 'crawl_dcinside_board',
                'supported_params': [
                    'limit', 'sort', 'min_views', 'min_likes',
                    'time_filter', 'start_date', 'end_date', 'websocket',
                    'enforce_date_limit', 'start_index', 'end_index'
                ],
                'unsupported_params': ['min_comments']
            },
            'blind': {
                'target_param': 'board_input',
                'module': 'blind',
                'function': 'crawl_blind_board',
                'supported_params': [
                    'limit', 'sort', 'min_views', 'min_likes',
                    'time_filter', 'start_date', 'end_date', 'websocket',
                    'enforce_date_limit', 'start_index', 'end_index'
                ],
                'unsupported_params': ['min_comments']
            },
            'bbc': {
                'target_param': 'board_url',
                'module': 'bbc',
                'function': 'crawl_bbc_board',
                'supported_params': [
                    'limit', 'sort', 'min_views', 'min_likes', 'min_comments',
                    'time_filter', 'start_date', 'end_date', 'websocket',
                    'board_name', 'enforce_date_limit', 'start_index', 'end_index'
                ],
                'unsupported_params': []
            },
            'universal': {
                'target_param': 'board_url',
                'module': 'universal',
                'function': 'crawl_universal_board',
                'supported_params': [
                    'limit', 'sort', 'min_views', 'min_likes', 'min_comments',
                    'time_filter', 'start_date', 'end_date', 'websocket',
                    'board_name', 'enforce_date_limit', 'start_index', 'end_index'
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
            input_data: 크롤링 대상 (URL, 게시판명 등)
            **config: 크롤링 설정
        
        Returns:
            크롤링 결과 리스트
        """
        start_time = datetime.now()
        
        try:
            # 의존성 초기화
            self._initialize_dependencies()
            
            # 1. 사이트 감지
            site_type = await self._detect_site_type(input_data)
            logger.info(f"🎯 감지된 사이트: {site_type}")
            
            # 2. 게시판 식별자 추출
            board_identifier = self._extract_board_identifier(input_data, site_type)
            logger.info(f"📋 게시판 식별자: {board_identifier}")
            
            # 3. 크롤링 설정 준비
            crawl_config = self._prepare_crawl_config(site_type, board_identifier, **config)
            
            # 4. 크롤링 실행
            if self.unified_crawler:
                # 통합 크롤러 사용
                logger.info(f"🚀 통합 크롤링 실행: {site_type}")
                results = await self.unified_crawler.unified_crawl(
                    site_type, 
                    board_identifier, 
                    **crawl_config
                )
            else:
                # 직접 크롤러 호출 (폴백)
                logger.info(f"🚀 직접 크롤링 실행: {site_type}")
                results = await self._direct_crawl(site_type, **crawl_config)
            
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
        if 'reddit.com' in input_lower or '/r/' in input_lower:
            return 'reddit'
        elif any(lemmy_domain in input_lower for lemmy_domain in [
            'lemmy.world', 'lemmy.ml', 'beehaw.org', 'sh.itjust.works',
            'feddit.de', 'lemm.ee', 'sopuli.xyz', 'lemmy.ca'
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
        else:
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
    
    async def _direct_crawl(self, site_type: str, **config) -> List[Dict]:
        """직접 크롤러 호출 (폴백)"""
        site_config = self.site_param_mapping[site_type]
        module_name = site_config['module']
        function_name = site_config['function']
        
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
            'cached_crawlers': list(self._crawlers_cache.keys())
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
                'notes': '완전한 URL을 입력하세요'
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
                'module': site_config['module'],
                'function': site_config['function']
            }
        })
        
        return base_help
        
