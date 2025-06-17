# core/auto_crawler.py - 통합 시스템 사용 버전
"""
🔥 통합 자동 크롤러 (간소화 버전)
통합 크롤링 시스템을 사용하여 모든 사이트를 처리합니다.
"""

import logging
from typing import List, Dict, Any
from .site_detector import SiteDetector
from .unified_crawler import unified_crawler

logger = logging.getLogger(__name__)

class AutoCrawler:
    """🔥 통합 자동 크롤러 (간소화 버전)"""
    
    def __init__(self):
        self.site_detector = SiteDetector()
    
    async def crawl(self, input_data: str, **config) -> List[Dict]:
        """
        통합 크롤링 메인 메서드
        
        Args:
            input_data: 크롤링 대상 (URL, 게시판명 등)
            **config: 크롤링 설정
        
        Returns:
            크롤링 결과 리스트
        """
        try:
            # 1. 사이트 감지
            site_type = await self.site_detector.detect_site_type(input_data)
            logger.info(f"🎯 감지된 사이트: {site_type}")
            
            # 2. 게시판 식별자 추출
            if site_type not in ['universal', 'bbc']:
                board_identifier = self.site_detector.extract_board_identifier(input_data, site_type)
            else:
                board_identifier = input_data
            
            # 3. 크롤링 설정 준비
            crawl_config = self._prepare_crawl_config(site_type, **config)
            
            # 4. 🔥 통합 크롤링 시스템 사용
            logger.info(f"🚀 통합 크롤링 실행: {site_type} -> {board_identifier}")
            results = await unified_crawler.unified_crawl(
                site_type, 
                board_identifier, 
                **crawl_config
            )
            
            logger.info(f"✅ 크롤링 완료: {len(results)}개 결과")
            return results
                
        except Exception as e:
            logger.error(f"AutoCrawler 오류: {e}")
            raise
    
    def _prepare_crawl_config(self, site_type: str, **config) -> Dict[str, Any]:
        """사이트별 크롤링 설정 준비"""
        
        # 기본 설정
        base_config = {
            'websocket': config.get('websocket'),
            'sort': config.get('sort', 'recent'),
            'min_views': config.get('min_views', 0),
            'min_likes': config.get('min_likes', 0),
            'min_comments': config.get('min_comments', 0),  # 통합 시스템에서 자동 필터링
            'time_filter': config.get('time_filter', 'day'),
            'start_date': config.get('start_date'),
            'end_date': config.get('end_date'),
            'start_index': config.get('start_index', config.get('start', 1)),
            'end_index': config.get('end_index', config.get('end', 20)),
            'enforce_date_limit': config.get('enforce_date_limit', False)
        }
        
        # 사이트별 특수 처리
        if site_type == 'reddit':
            # Reddit 정렬 방식 매핑
            sort_mapping = {
                "popular": "hot", "recommend": "top", "recent": "new",
                "comments": "top"
            }
            sort = base_config.get('sort', 'top')
            base_config['sort'] = sort_mapping.get(sort, sort)
            
            # 필터링에 따른 제한 설정
            has_filters = (base_config['min_views'] > 0 or 
                          base_config['min_likes'] > 0 or 
                          (base_config['start_date'] and base_config['end_date']))
            
            base_config['limit'] = (
                min(base_config['end_index'] * 5, 500) if has_filters 
                else base_config['end_index'] + 5
            )
        
        elif site_type == 'lemmy':
            # Lemmy 커뮤니티 형식 처리는 통합 시스템에서 자동 처리됨
            has_filters = (base_config['min_views'] > 0 or 
                          base_config['min_likes'] > 0 or 
                          (base_config['start_date'] and base_config['end_date']))
            
            base_config['limit'] = (
                min(base_config['end_index'] * 5, 200) if has_filters 
                else base_config['end_index'] + 5
            )
        
        elif site_type in ['dcinside', 'blind']:
            has_filters = (base_config['min_views'] > 0 or 
                          base_config['min_likes'] > 0 or 
                          (base_config['start_date'] and base_config['end_date']))
            
            base_config['limit'] = (
                min(base_config['end_index'] * 5, 500) if has_filters 
                else base_config['end_index'] + 5
            )
        
        elif site_type in ['bbc', 'universal']:
            has_filters = (base_config['min_views'] > 0 or 
                          base_config['min_likes'] > 0 or 
                          (base_config['start_date'] and base_config['end_date']))
            
            base_config['limit'] = (
                min(base_config['end_index'] * 5, 500) if has_filters 
                else base_config['end_index'] + 5
            )
            
            # BBC는 board_name 필요
            if site_type == 'bbc':
                base_config['board_name'] = ""
        
        # None 값 제거
        cleaned_config = {k: v for k, v in base_config.items() if v is not None}
        
        logger.debug(f"크롤링 설정 준비 완료 ({site_type}): {list(cleaned_config.keys())}")
        return cleaned_config
    
    def get_supported_crawlers(self) -> List[str]:
        """지원되는 크롤러 목록 반환"""
        return unified_crawler.get_registry_info()['supported_sites']
    
    def get_crawler_info(self) -> Dict[str, Any]:
        """크롤러 정보 반환"""
        registry_info = unified_crawler.get_registry_info()
        
        return {
            'total_crawlers': registry_info['total_sites'],
            'supported_sites': registry_info['supported_sites'],
            'auto_detection': True,
            'unified_interface': True,
            'unified_system': True,
            'parameter_filtering': True,
            'parameters_by_site': registry_info['parameters_by_site']
        }
    
    async def validate_crawl_request(self, input_data: str, **config) -> tuple[bool, List[str]]:
        """크롤링 요청 유효성 검사"""
        errors = []
        
        try:
            # 1. 입력 데이터 검증
            if not input_data or not input_data.strip():
                errors.append("크롤링 대상이 입력되지 않았습니다")
                return False, errors
            
            # 2. 사이트 감지
            site_type = await self.site_detector.detect_site_type(input_data)
            if not site_type:
                errors.append("지원하지 않는 사이트입니다")
                return False, errors
            
            # 3. 통합 시스템을 통한 매개변수 검증
            is_valid, param_errors = unified_crawler.validate_parameters(site_type, **config)
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
    
    def get_site_specific_help(self, site_type: str) -> Dict[str, Any]:
        """사이트별 도움말 정보"""
        help_info = {
            'reddit': {
                'format': 'subreddit_name or /r/subreddit_name',
                'examples': ['python', 'askreddit', '/r/programming'],
                'notes': 'URL형태도 지원됩니다'
            },
            'lemmy': {
                'format': 'community@instance',
                'examples': ['technology@lemmy.world', 'asklemmy@lemmy.ml'],
                'notes': '인스턴스가 없으면 자동으로 @lemmy.world 추가됩니다'
            },
            'dcinside': {
                'format': 'gallery_name',
                'examples': ['programming', '싱글벙글', '유머'],
                'notes': '갤러리 ID 또는 이름을 입력하세요'
            },
            'blind': {
                'format': 'topic_name',
                'examples': ['회사생활', '개발자', '블라블라'],
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
        
        # 지원 매개변수 정보 추가
        params = unified_crawler.get_supported_parameters(site_type)
        if params:
            base_help['supported_parameters'] = params
        
        return base_help
