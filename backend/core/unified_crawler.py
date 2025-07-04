# core/unified_crawler.py
"""
🔥 통합 크롤링 시스템
모든 사이트 크롤러를 하나의 인터페이스로 통합 관리
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional, Callable
import inspect

logger = logging.getLogger(__name__)

class UnifiedCrawlerManager:
    """통합 크롤링 매니저"""
    
    def __init__(self):
        # 🔥 사이트별 크롤러 함수와 지원 매개변수 매핑
        self.crawler_registry = {
            'reddit': {
                'module': 'reddit',
                'function': 'fetch_posts',
                'params': {
                    'required': ['subreddit_name'],
                    'optional': [
                        'limit', 'sort', 'time_filter', 'websocket',
                        'min_views', 'min_likes', 'start_date', 'end_date',
                        'enforce_date_limit', 'start_index', 'end_index'
                    ],
                    'mapping': {
                        'board_identifier': 'subreddit_name',
                        'board_input': 'subreddit_name',
                        'board_url': 'subreddit_name'
                    }
                }
            },
            'lemmy': {
                'module': 'lemmy',
                'function': 'crawl_lemmy_board',
                'params': {
                    'required': ['community_input'],
                    'optional': [
                        'limit', 'sort', 'min_views', 'min_likes',
                        'time_filter', 'start_date', 'end_date', 'websocket',
                        'enforce_date_limit', 'start_index', 'end_index'
                    ],
                    'mapping': {
                        'board_identifier': 'community_input',
                        'board_input': 'community_input',
                        'board_url': 'community_input'
                    }
                }
            },
            'dcinside': {
                'module': 'dcinside',
                'function': 'crawl_dcinside_board',
                'params': {
                    'required': ['board_name'],
                    'optional': [
                        'limit', 'sort', 'min_views', 'min_likes',
                        'time_filter', 'start_date', 'end_date', 'websocket',
                        'enforce_date_limit', 'start_index', 'end_index'
                    ],
                    'mapping': {
                        'board_identifier': 'board_name',
                        'board_input': 'board_name',
                        'board_url': 'board_name'
                    }
                }
            },
            'blind': {
                'module': 'blind',
                'function': 'crawl_blind_board',
                'params': {
                    'required': ['board_input'],
                    'optional': [
                        'limit', 'sort', 'min_views', 'min_likes',
                        'time_filter', 'start_date', 'end_date', 'websocket',
                        'enforce_date_limit', 'start_index', 'end_index'
                    ],
                    'mapping': {
                        'board_identifier': 'board_input',
                        'board_name': 'board_input',
                        'board_url': 'board_input'
                    }
                }
            },
            'bbc': {
                'module': 'bbc',
                'function': 'crawl_bbc_board',
                'params': {
                    'required': ['board_url'],
                    'optional': [
                        'limit', 'sort', 'min_views', 'min_likes', 'min_comments',
                        'time_filter', 'start_date', 'end_date', 'websocket',
                        'board_name', 'enforce_date_limit', 'start_index', 'end_index'
                    ],
                    'mapping': {
                        'board_identifier': 'board_url',
                        'board_input': 'board_url',
                        'board_name': 'board_url'
                    }
                }
            },
            'universal': {
                'module': 'universal',
                'function': 'crawl_universal_board',
                'params': {
                    'required': ['board_url'],
                    'optional': [
                        'limit', 'sort', 'min_views', 'min_likes', 'min_comments',
                        'time_filter', 'start_date', 'end_date', 'websocket',
                        'board_name', 'enforce_date_limit', 'start_index', 'end_index'
                    ],
                    'mapping': {
                        'board_identifier': 'board_url',
                        'board_input': 'board_url',
                        'board_name': 'board_url'
                    }
                }
            }
        }
        
        # 크롤러 함수 캐시
        self._crawler_cache = {}
    
    async def unified_crawl(self, site_type: str, target_input: str, **kwargs) -> List[Dict]:
        """
        통합 크롤링 함수
        
        Args:
            site_type: 사이트 타입 (reddit, lemmy, dcinside, etc.)
            target_input: 크롤링 대상 (게시판명, URL 등)
            **kwargs: 크롤링 옵션들
        
        Returns:
            크롤링 결과 리스트
        """
        if site_type not in self.crawler_registry:
            raise ValueError(f"지원하지 않는 사이트: {site_type}")
        
        # 1. 크롤러 함수 로드
        crawler_func = await self._get_crawler_function(site_type)
        
        # 2. 매개변수 매핑 및 필터링
        filtered_params = self._prepare_parameters(site_type, target_input, **kwargs)
        
        # 3. 크롤링 실행
        logger.info(f"🚀 통합 크롤링 시작: {site_type} -> {target_input}")
        logger.debug(f"   매개변수: {filtered_params}")
        
        try:
            if asyncio.iscoroutinefunction(crawler_func):
                result = await crawler_func(**filtered_params)
            else:
                result = crawler_func(**filtered_params)
            
            logger.info(f"✅ 크롤링 완료: {len(result) if result else 0}개 결과")
            return result or []
            
        except Exception as e:
            logger.error(f"❌ 크롤링 오류 ({site_type}): {e}")
            raise
    
    async def _get_crawler_function(self, site_type: str) -> Callable:
        """크롤러 함수를 동적으로 로드"""
        if site_type in self._crawler_cache:
            return self._crawler_cache[site_type]
        
        config = self.crawler_registry[site_type]
        module_name = config['module']
        function_name = config['function']
        
        try:
            # 동적 모듈 임포트
            module = __import__(module_name, fromlist=[function_name])
            crawler_func = getattr(module, function_name)
            
            # 캐시에 저장
            self._crawler_cache[site_type] = crawler_func
            
            logger.debug(f"크롤러 함수 로드: {module_name}.{function_name}")
            return crawler_func
            
        except (ImportError, AttributeError) as e:
            logger.error(f"크롤러 함수 로드 실패: {module_name}.{function_name} - {e}")
            raise ImportError(f"크롤러를 찾을 수 없습니다: {site_type}")
    
    def _prepare_parameters(self, site_type: str, target_input: str, **kwargs) -> Dict[str, Any]:
        """사이트별 지원 매개변수만 필터링하여 준비"""
        config = self.crawler_registry[site_type]
        required_params = config['params']['required']
        optional_params = config['params']['optional']
        param_mapping = config['params']['mapping']
        
        # 1. 기본 매개변수 설정
        filtered_params = {}
        
        # 2. 필수 매개변수 설정 (타겟 입력)
        main_param = required_params[0]  # 첫 번째 필수 매개변수
        filtered_params[main_param] = target_input
        
        # 3. 매개변수 매핑 적용
        for source_key, target_key in param_mapping.items():
            if source_key in kwargs:
                filtered_params[target_key] = kwargs[source_key]
        
        # 4. 직접 매핑되는 매개변수들
        for param in optional_params:
            if param in kwargs and kwargs[param] is not None:
                filtered_params[param] = kwargs[param]
        
        # 5. 공통 매개변수 매핑
        common_mappings = {
            'start': 'start_index',
            'end': 'end_index',
            'board': main_param,
            'input': main_param,
            'board_identifier': main_param
        }
        
        for source, target in common_mappings.items():
            if source in kwargs and target in optional_params:
                filtered_params[target] = kwargs[source]
        
        # 6. 사이트별 특수 처리
        filtered_params = self._apply_site_specific_processing(
            site_type, filtered_params, **kwargs
        )
        
        # 7. None 값 제거
        filtered_params = {k: v for k, v in filtered_params.items() if v is not None}
        
        logger.debug(f"매개변수 필터링 완료 ({site_type}): {list(filtered_params.keys())}")
        return filtered_params
    
    def _apply_site_specific_processing(self, site_type: str, params: Dict, **kwargs) -> Dict:
        """사이트별 특수 처리"""
        
        if site_type == 'reddit':
            # Reddit 정렬 방식 매핑
            sort_mapping = {
                "popular": "hot", "recommend": "top", "recent": "new",
                "comments": "top"
            }
            if 'sort' in params and params['sort'] in sort_mapping:
                params['sort'] = sort_mapping[params['sort']]
        
        elif site_type == 'lemmy':
            # Lemmy 커뮤니티 형식 처리
            if 'community_input' in params:
                community = params['community_input']
                if '@' not in community and '.' not in community:
                    params['community_input'] = f"{community}@lemmy.world"
        
        elif site_type == 'bbc':
            # BBC는 board_name이 빈 문자열로 필요할 수 있음
            if 'board_name' not in params:
                params['board_name'] = ""
        
        return params
    
    def get_supported_parameters(self, site_type: str) -> Dict[str, List[str]]:
        """사이트별 지원 매개변수 목록 반환"""
        if site_type not in self.crawler_registry:
            return {}
        
        config = self.crawler_registry[site_type]
        return {
            'required': config['params']['required'],
            'optional': config['params']['optional'],
            'all': config['params']['required'] + config['params']['optional']
        }
    
    def validate_parameters(self, site_type: str, **kwargs) -> tuple[bool, List[str]]:
        """매개변수 유효성 검사"""
        if site_type not in self.crawler_registry:
            return False, [f"지원하지 않는 사이트: {site_type}"]
        
        config = self.crawler_registry[site_type]
        required_params = config['params']['required']
        optional_params = config['params']['optional']
        all_supported = required_params + optional_params
        
        errors = []
        
        # 지원하지 않는 매개변수 확인
        unsupported = [k for k in kwargs.keys() if k not in all_supported and k not in ['board_identifier', 'board_input', 'board_url', 'input', 'start', 'end']]
        if unsupported:
            errors.append(f"{site_type}에서 지원하지 않는 매개변수: {unsupported}")
        
        return len(errors) == 0, errors
    
    def get_registry_info(self) -> Dict[str, Any]:
        """레지스트리 정보 반환"""
        return {
            'total_sites': len(self.crawler_registry),
            'supported_sites': list(self.crawler_registry.keys()),
            'parameters_by_site': {
                site: self.get_supported_parameters(site)
                for site in self.crawler_registry.keys()
            }
        }

# 전역 인스턴스
unified_crawler = UnifiedCrawlerManager()

# 편의 함수들
async def crawl_any_site(site_type: str, target: str, **options) -> List[Dict]:
    """모든 사이트 크롤링을 위한 편의 함수"""
    return await unified_crawler.unified_crawl(site_type, target, **options)

def get_site_parameters(site_type: str) -> Dict[str, List[str]]:
    """사이트별 지원 매개변수 조회"""
    return unified_crawler.get_supported_parameters(site_type)

def validate_crawl_request(site_type: str, **params) -> tuple[bool, List[str]]:
    """크롤링 요청 유효성 검사"""
    return unified_crawler.validate_parameters(site_type, **params)