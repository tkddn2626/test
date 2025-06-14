# core/auto_crawler.py
"""
🔥 통합 자동 크롤러
사이트를 자동으로 감지하고 적절한 크롤러를 선택하여 실행합니다.
"""

import logging
from typing import List, Dict, Any
from .site_detector import SiteDetector

logger = logging.getLogger(__name__)

class AutoCrawler:
    """🔥 통합 자동 크롤러"""
    
    def __init__(self):
        self.site_detector = SiteDetector()
        self.site_crawlers = {
            'reddit': self._crawl_reddit,
            'dcinside': self._crawl_dcinside,
            'blind': self._crawl_blind,
            'bbc': self._crawl_bbc,
            'lemmy': self._crawl_lemmy,
            'universal': self._crawl_universal
        }
    
    async def crawl(self, input_data: str, **config) -> List[Dict]:
        """통합 크롤링 메인 메서드"""
        try:
            # 1. 사이트 감지
            site_type = await self.site_detector.detect_site_type(input_data)
            logger.info(f"🎯 감지된 사이트: {site_type}")
            
            # 2. 게시판 식별자 추출
            if site_type not in ['universal', 'bbc']:
                board_identifier = self.site_detector.extract_board_identifier(input_data, site_type)
            else:
                board_identifier = input_data
            
            # 3. 적절한 크롤러 선택 및 실행
            if site_type in self.site_crawlers:
                crawler_func = self.site_crawlers[site_type]
                return await crawler_func(board_identifier, site_type, **config)
            else:
                # 알 수 없는 사이트는 범용 크롤러로 처리
                return await self._crawl_universal(input_data, 'universal', **config)
                
        except Exception as e:
            logger.error(f"AutoCrawler 오류: {e}")
            raise
    
    async def _crawl_reddit(self, board_identifier: str, site_type: str, **config) -> List[Dict]:
        """Reddit 크롤링"""
        from reddit import fetch_posts
        
        websocket = config.get('websocket')
        sort = config.get('sort', 'top')
        time_filter = config.get('time_filter', 'day')
        min_views = config.get('min_views', 0)
        min_likes = config.get('min_likes', 0)
        start_date = config.get('start_date')
        end_date = config.get('end_date')
        start_index = config.get('start_index', 1)
        end_index = config.get('end_index', 20)
        crawl_id = config.get('crawl_id')
        
        # Reddit 정렬 매핑
        reddit_sort_map = {
            "popular": "hot", "recommend": "top", "recent": "new",
            "comments": "top", "top": "top", "hot": "hot", 
            "new": "new", "rising": "rising", "best": "best"
        }
        reddit_sort = reddit_sort_map.get(sort, "top")
        
        # 필터 조건에 따른 제한 설정
        has_filters = min_views > 0 or min_likes > 0 or (start_date and end_date)
        required_limit = min(end_index * 5, 500) if has_filters else end_index + 5
        
        logger.info(f"🔴 Reddit 크롤링 시작: {board_identifier}")
        
        return await fetch_posts(
            subreddit_name=board_identifier,
            limit=required_limit,
            sort=reddit_sort,
            time_filter=time_filter,
            websocket=websocket,
            min_views=min_views,
            min_likes=min_likes,
            start_date=start_date,
            end_date=end_date,
            enforce_date_limit=has_filters,
            start_index=start_index,
            end_index=end_index
        )
    
    async def _crawl_dcinside(self, board_identifier: str, site_type: str, **config) -> List[Dict]:
        """DCInside 크롤링"""
        from dcinside import crawl_dcinside_board
        
        websocket = config.get('websocket')
        sort = config.get('sort', 'recent')
        min_views = config.get('min_views', 0)
        min_likes = config.get('min_likes', 0)
        time_filter = config.get('time_filter', 'day')
        start_date = config.get('start_date')
        end_date = config.get('end_date')
        start_index = config.get('start_index', 1)
        end_index = config.get('end_index', 20)
        
        has_filters = min_views > 0 or min_likes > 0 or (start_date and end_date)
        required_limit = min(end_index * 5, 500) if has_filters else end_index + 5
        
        logger.info(f"🟢 DCInside 크롤링 시작: {board_identifier}")
        
        return await crawl_dcinside_board(
            board_name=board_identifier,
            limit=required_limit,
            sort=sort,
            min_views=min_views,
            min_likes=min_likes,
            time_filter=time_filter,
            start_date=start_date,
            end_date=end_date,
            websocket=websocket,
            enforce_date_limit=has_filters,
            start_index=start_index,
            end_index=end_index
        )
    
    async def _crawl_blind(self, board_identifier: str, site_type: str, **config) -> List[Dict]:
        """Blind 크롤링"""
        from blind import crawl_blind_board
        
        websocket = config.get('websocket')
        sort = config.get('sort', 'recent')
        min_views = config.get('min_views', 0)
        min_likes = config.get('min_likes', 0)
        time_filter = config.get('time_filter', 'day')
        start_date = config.get('start_date')
        end_date = config.get('end_date')
        start_index = config.get('start_index', 1)
        end_index = config.get('end_index', 20)
        
        has_filters = min_views > 0 or min_likes > 0 or (start_date and end_date)
        required_limit = min(end_index * 5, 500) if has_filters else end_index + 5
        
        logger.info(f"🔵 Blind 크롤링 시작: {board_identifier}")
        
        return await crawl_blind_board(
            board_input=board_identifier,
            limit=required_limit,
            sort=sort,
            min_views=min_views,
            min_likes=min_likes,
            time_filter=time_filter,
            start_date=start_date,
            end_date=end_date,
            websocket=websocket,
            enforce_date_limit=has_filters,
            start_index=start_index,
            end_index=end_index
        )
    
    async def _crawl_bbc(self, board_identifier: str, site_type: str, **config) -> List[Dict]:
        """BBC 크롤링"""
        from bbc import crawl_bbc_board
        
        websocket = config.get('websocket')
        sort = config.get('sort', 'recent')
        min_views = config.get('min_views', 0)
        min_likes = config.get('min_likes', 0)
        time_filter = config.get('time_filter', 'day')
        start_date = config.get('start_date')
        end_date = config.get('end_date')
        start_index = config.get('start_index', 1)
        end_index = config.get('end_index', 20)
        
        has_filters = min_views > 0 or min_likes > 0 or (start_date and end_date)
        required_limit = min(end_index * 5, 500) if has_filters else end_index + 5
        
        logger.info(f"🟠 BBC 크롤링 시작: {board_identifier}")
        
        return await crawl_bbc_board(
            board_url=board_identifier,
            limit=required_limit,
            sort=sort,
            min_views=min_views,
            min_likes=min_likes,
            min_comments=0,
            time_filter=time_filter,
            start_date=start_date,
            end_date=end_date,
            websocket=websocket,
            board_name="",
            enforce_date_limit=has_filters,
            start_index=start_index,
            end_index=end_index
        )
    
    async def _crawl_lemmy(self, board_identifier: str, site_type: str, **config) -> List[Dict]:
        """Lemmy 크롤링"""
        from lemmy import crawl_lemmy_board
        
        websocket = config.get('websocket')
        sort = config.get('sort', 'Hot')
        min_views = config.get('min_views', 0)
        min_likes = config.get('min_likes', 0)
        time_filter = config.get('time_filter', 'day')
        start_date = config.get('start_date')
        end_date = config.get('end_date')
        start_index = config.get('start_index', 1)
        end_index = config.get('end_index', 20)
        
        # @ 기호가 없으면 기본 인스턴스 추가
        if '@' not in board_identifier and '.' not in board_identifier:
            board_identifier = f"{board_identifier}@lemmy.world"
        
        has_filters = min_views > 0 or min_likes > 0 or (start_date and end_date)
        required_limit = min(end_index * 5, 200) if has_filters else end_index + 5
        
        logger.info(f"🟡 Lemmy 크롤링 시작: {board_identifier}")
        
        return await crawl_lemmy_board(
            community_input=board_identifier,
            limit=required_limit,
            sort=sort,
            min_views=min_views,
            min_likes=min_likes,
            time_filter=time_filter,
            start_date=start_date,
            end_date=end_date,
            websocket=websocket,
            enforce_date_limit=has_filters,
            start_index=start_index,
            end_index=end_index
        )
    
    async def _crawl_universal(self, board_identifier: str, site_type: str, **config) -> List[Dict]:
        """범용 크롤링"""
        from universal import crawl_universal_board
        
        websocket = config.get('websocket')
        sort = config.get('sort', 'recent')
        min_views = config.get('min_views', 0)
        min_likes = config.get('min_likes', 0)
        time_filter = config.get('time_filter', 'all')
        start_date = config.get('start_date')
        end_date = config.get('end_date')
        start_index = config.get('start_index', 1)
        end_index = config.get('end_index', 20)
        
        # URL과 게시판명 분리
        if ' ' in board_identifier:
            parts = board_identifier.split(' ', 1)
            target_url = parts[0]
            target_board_name = parts[1]
        else:
            target_url = board_identifier
            target_board_name = ""
        
        has_filters = min_views > 0 or min_likes > 0 or (start_date and end_date)
        required_limit = min(end_index * 5, 500) if has_filters else end_index + 5
        
        logger.info(f"⚪ Universal 크롤링 시작: {target_url}")
        
        return await crawl_universal_board(
            board_url=target_url,
            limit=required_limit,
            sort=sort,
            min_views=min_views,
            min_likes=min_likes,
            time_filter=time_filter,
            start_date=start_date,
            end_date=end_date,
            websocket=websocket,
            board_name=target_board_name,
            enforce_date_limit=has_filters,
            start_index=start_index,
            end_index=end_index
        )
    
    def get_supported_crawlers(self) -> List[str]:
        """지원되는 크롤러 목록 반환"""
        return list(self.site_crawlers.keys())
    
    def get_crawler_info(self) -> Dict[str, Any]:
        """크롤러 정보 반환"""
        return {
            'total_crawlers': len(self.site_crawlers),
            'supported_sites': list(self.site_crawlers.keys()),
            'auto_detection': True,
            'unified_interface': True
        }