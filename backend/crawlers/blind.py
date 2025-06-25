# blind.py - Blind 크롤링 및 필터링 완전 구현

import requests
from bs4 import BeautifulSoup
import json
import os
import re
import asyncio
from datetime import datetime, timedelta
from typing import Tuple, List, Dict, Optional

# 메시지 시스템 임포트
from core.messages import (
    create_progress_message, create_status_message, create_error_message,
    create_success_message, create_complete_message, create_localized_message,
    CrawlStep, SiteType, ErrorCode, SuccessType,
    quick_progress, quick_error, quick_complete
)

# JSON 파일 경로
BLIND_JSON_PATH = os.path.join("id_data", "boards.json")

def load_blind_map() -> dict:
    """Blind 토픽 맵핑 데이터 로드"""
    if not os.path.exists(BLIND_JSON_PATH):
        print(f"Error: {BLIND_JSON_PATH} not found")
        return {}

    try:
        with open(BLIND_JSON_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            print(f"Loaded boards.json ({len(data)} entries)")
            return data
    except Exception as e:
        print(f"Error parsing boards.json: {e}")
        return {}

def resolve_blind_board_id(keyword: str) -> str:
    """키워드를 Blind 보드 ID로 자동 매핑"""
    keyword = keyword.strip().lower()
    
    if not os.path.exists(BLIND_JSON_PATH):
        raise Exception("Error: boards.json not found. Run the builder script first.")
    
    with open(BLIND_JSON_PATH, "r", encoding="utf-8") as f:
        board_map = json.load(f)
    
    if not board_map:
        raise Exception("Error: boards.json is empty. Run the builder script first.")
    
    # 직접 매치 시도
    if keyword in board_map:
        return board_map[keyword]
    
    # 부분 매치 시도
    matches = [(name, board_id) for name, board_id in board_map.items() 
               if keyword in name.lower()]
    
    if not matches:
        raise Exception(f"No matching Blind topic for '{keyword}'.")
    
    name, board_id = matches[0]
    print(f"📋 Found topic: {name} (ID: {board_id})")
    return board_id

def extract_post_metrics(item) -> Tuple[int, int]:
    """게시물에서 조회수와 좋아요수 추출 (강화버전)"""
    views = 0
    likes = 0

    try:
        # 조회수 추출
        view_selectors = [
            '.view-count', '.views', '[class*="view"]',
            '.count', '[data-view]', '.meta .count',
            '.stats .view', '.post-stats .views'
        ]
        for selector in view_selectors:
            view_elements = item.select(selector)
            for element in view_elements:
                text = element.text.strip()
                numbers = re.findall(r'\d+', text)
                if numbers and ('조회' in text or 'view' in text.lower() or len(numbers) == 1):
                    views = int(numbers[0])
                    break
            if views > 0:
                break

        # 좋아요/추천수 추출
        like_selectors = [
            '.like-count', '.likes', '.recommend', '[class*="like"]',
            '[class*="thumb"]', '.vote', '[data-like]', '.reaction',
            '.post-stats .likes', '.upvote'
        ]
        for selector in like_selectors:
            like_elements = item.select(selector)
            for element in like_elements:
                text = element.text.strip()
                numbers = re.findall(r'\d+', text)
                if numbers and ('좋아요' in text or '추천' in text or 'like' in text.lower() or '👍' in text):
                    likes = int(numbers[0])
                    break
            if likes > 0:
                break
                
    except Exception as e:
        print(f"Error extracting metrics: {e}")

    return views, likes

def extract_post_date(item) -> str:
    """게시물 작성일 추출"""
    date_selectors = [
        '.date', '.time', '.posting-time', '.created-at',
        '[class*="date"]', '[class*="time"]', '.meta .date',
        '.post-meta .date', '.timestamp'
    ]
    
    for selector in date_selectors:
        element = item.select_one(selector)
        if element:
            return element.text.strip()
    
    return "날짜 정보 없음"

def _parse_blind_date(date_text: str) -> Optional[datetime]:
    """Blind 날짜 파싱 (상대적/절대적 날짜 모두 지원)"""
    if not date_text:
        return None
    
    try:
        now = datetime.now()
        
        # 상대적 시간 파싱
        if '분 전' in date_text or '분전' in date_text:
            minutes = int(re.findall(r'\d+', date_text)[0])
            return now - timedelta(minutes=minutes)
        elif '시간 전' in date_text or '시간전' in date_text:
            hours = int(re.findall(r'\d+', date_text)[0])
            return now - timedelta(hours=hours)
        elif '일 전' in date_text or '일전' in date_text:
            days = int(re.findall(r'\d+', date_text)[0])
            return now - timedelta(days=days)
        elif '주 전' in date_text or '주전' in date_text:
            weeks = int(re.findall(r'\d+', date_text)[0])
            return now - timedelta(weeks=weeks)
        elif '개월 전' in date_text or '달 전' in date_text:
            months = int(re.findall(r'\d+', date_text)[0])
            return now - timedelta(days=months * 30)  # 근사치
        
        # 영어 상대시간
        if 'minute' in date_text.lower():
            minutes = int(re.findall(r'\d+', date_text)[0])
            return now - timedelta(minutes=minutes)
        elif 'hour' in date_text.lower():
            hours = int(re.findall(r'\d+', date_text)[0])
            return now - timedelta(hours=hours)
        elif 'day' in date_text.lower():
            days = int(re.findall(r'\d+', date_text)[0])
            return now - timedelta(days=days)
        elif 'week' in date_text.lower():
            weeks = int(re.findall(r'\d+', date_text)[0])
            return now - timedelta(weeks=weeks)
        
        # 절대적 날짜 파싱
        date_patterns = [
            r'(\d{4})\.(\d{1,2})\.(\d{1,2})',  # YYYY.MM.DD
            r'(\d{1,2})\.(\d{1,2})',          # MM.DD (올해)
            r'(\d{4})-(\d{1,2})-(\d{1,2})',   # YYYY-MM-DD
            r'(\d{1,2})-(\d{1,2})',           # MM-DD (올해)
            r'(\d{4})/(\d{1,2})/(\d{1,2})',   # YYYY/MM/DD
            r'(\d{1,2})/(\d{1,2})'            # MM/DD (올해)
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, date_text)
            if match:
                groups = match.groups()
                if len(groups) == 3:  # YYYY.MM.DD 형태
                    year, month, day = map(int, groups)
                elif len(groups) == 2:  # MM.DD 형태 (올해)
                    year = now.year
                    month, day = map(int, groups)
                else:
                    continue
                
                return datetime(year, month, day)
    
    except Exception as e:
        print(f"Date parsing error: {e}")
    
    return None

class BlindConditionChecker:
    """Blind 게시물 조건 체크 클래스"""
    
    def __init__(self, min_views: int = 0, min_likes: int = 0, min_comments: int = 0,
                 start_date: str = None, end_date: str = None):
        self.min_views = min_views
        self.min_likes = min_likes
        self.min_comments = min_comments
        
        # 날짜 범위 파싱
        self.start_dt = None
        self.end_dt = None
        if start_date and end_date:
            try:
                self.start_dt = datetime.strptime(start_date, '%Y-%m-%d')
                self.end_dt = datetime.strptime(end_date, '%Y-%m-%d')
                self.end_dt = self.end_dt.replace(hour=23, minute=59, second=59)
            except Exception as e:
                print(f"날짜 파싱 오류: {e}")

    def check_post_conditions(self, post: Dict) -> Tuple[bool, str]:
        """게시물이 조건을 만족하는지 확인"""
        try:
            # 조회수 체크
            if post.get('조회수', 0) < self.min_views:
                return False, f"조회수 부족: {post.get('조회수', 0)} < {self.min_views}"
            
            # 추천수 체크
            if post.get('추천수', 0) < self.min_likes:
                return False, f"추천수 부족: {post.get('추천수', 0)} < {self.min_likes}"
            
            # 댓글수 체크
            if post.get('댓글수', 0) < self.min_comments:
                return False, f"댓글수 부족: {post.get('댓글수', 0)} < {self.min_comments}"
            
            # 날짜 범위 체크
            if self.start_dt and self.end_dt:
                post_date = _parse_blind_date(post.get('작성일', ''))
                if not post_date:
                    return False, "날짜 파싱 실패"
                
                if not (self.start_dt <= post_date <= self.end_dt):
                    return False, "날짜 범위 벗어남"
            
            return True, "조건 만족"
        
        except Exception as e:
            return False, f"조건 체크 오류: {e}"

    def should_stop_crawling(self, consecutive_fails: int, has_date_filter: bool) -> Tuple[bool, str]:
        """크롤링 중단 여부 결정"""
        fail_threshold = 10 if has_date_filter else 20
        if consecutive_fails >= fail_threshold:
            return True, "조건 불만족으로 중단"
        return False, "계속 진행"

def _extract_blind_post_data(item) -> Optional[Dict]:
    """개별 Blind 게시물 데이터 추출"""
    try:
        # 제목 및 링크 추출
        title_selectors = [
            "h3 > a", ".title a", ".subject a", 
            ".post-title a", ".article-title a"
        ]
        title_element = None
        for selector in title_selectors:
            title_element = item.select_one(selector)
            if title_element:
                break
        
        # 본문 미리보기 추출
        body_selectors = [
            "p.pre-txt > a", ".preview", ".excerpt", 
            ".post-preview", ".content-preview"
        ]
        body_element = None
        for selector in body_selectors:
            body_element = item.select_one(selector)
            if body_element:
                break
        
        if not title_element:
            return None
        
        title = title_element.text.strip()
        link = title_element.get("href", "")
        
        # 절대 URL로 변환
        if link.startswith('/'):
            link = f"https://www.teamblind.com{link}"
        elif not link.startswith('http'):
            link = f"https://www.teamblind.com/{link}"
        
        # 메트릭 추출
        views, likes = extract_post_metrics(item)
        
        # 댓글수 추출
        comments = 0
        comment_selectors = [
            '.comment-count', '.comments', '[class*="comment"]', 
            '.reply', '.replies', '[class*="reply"]'
        ]
        for selector in comment_selectors:
            comment_elements = item.select(selector)
            for element in comment_elements:
                comment_text = element.text.strip()
                comment_numbers = re.findall(r'\d+', comment_text)
                if comment_numbers:
                    comments = int(comment_numbers[0])
                    break
            if comments > 0:
                break
        
        # 날짜 및 작성자 추출
        date_str = extract_post_date(item)
        author = _extract_author(item)
        
        # 본문 미리보기
        body_text = body_element.text.strip() if body_element else ""
        
        return {
            "원제목": title,
            "번역제목": None,
            "링크": link,
            "본문": body_text,
            "썸네일 URL": None,
            "조회수": views,
            "추천수": likes,
            "댓글수": comments,
            "작성일": date_str,
            "작성자": author,
            "크롤링방식": "Blind-Enhanced"
        }
    
    except Exception as e:
        print(f"Error extracting post data: {e}")
        return None

def _extract_author(item) -> str:
    """작성자 정보 추출"""
    author_selectors = [
        '.author', '.writer', '[class*="author"]', 
        '[class*="writer"]', '.nickname', '.user'
    ]
    
    for selector in author_selectors:
        author_element = item.select_one(selector)
        if author_element:
            return author_element.text.strip()
    
    return "익명"

async def _crawl_blind_page(base_url: str, page: int, websocket=None) -> List[Dict]:
    """Blind 단일 페이지 크롤링"""
    page_url = f"{base_url}{'&' if '?' in base_url else '?'}page={page}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        response = requests.get(page_url, headers=headers, timeout=10)
        if response.status_code != 200:
            return []
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        # 다양한 게시물 리스트 셀렉터 시도
        item_selectors = [
            "div.article-list-pre",  # 기본 Blind 리스트
            ".post-item", ".article-item", 
            ".topic-item", ".list-item"
        ]
        
        items = []
        for selector in item_selectors:
            items = soup.select(selector)
            if items:
                break
        
        posts = []
        for item in items:
            try:
                post_data = _extract_blind_post_data(item)
                if post_data:
                    posts.append(post_data)
            except Exception as e:
                print(f"Error extracting post: {e}")
                continue
        
        return posts
    
    except Exception as e:
        print(f"Error crawling page {page}: {e}")
        return []

async def _execute_intelligent_blind_crawling(
    board_input: str, condition_checker, required_limit: int, sort: str,
    start_index: int, end_index: int, websocket=None, enforce_date_limit=False
) -> List[Dict]:
    """지능형 Blind 크롤링 실행"""
    
    board_id = resolve_blind_board_id(board_input)
    
    # URL 구성
    base_url = f"https://www.teamblind.com/kr/topics/{board_id}"
    
    # 정렬 파라미터 추가
    sort_params = get_blind_sort_params(sort)
    if sort_params:
        base_url += f"?{sort_params}"
        
        if websocket:
            await websocket.send_json(
                create_progress_message(
                    progress=15,
                    step=CrawlStep.CONNECTING,
                    site=SiteType.BLIND,
                    board=board_input,
                    details={"sort_applied": sort}
                )
            )

    all_posts = []
    matched_posts = []
    consecutive_fails = 0
    page = 1
    max_pages = 200 if enforce_date_limit else min(20, (end_index // 20) + 3)
    
    if websocket:
        await websocket.send_json(
            create_progress_message(
                progress=25,
                step=CrawlStep.COLLECTING,
                site=SiteType.BLIND,
                board=board_input,
                details={"max_pages": max_pages}
            )
        )
    
    while page <= max_pages:
        try:
            if websocket:
                progress = min(25 + (page / max_pages) * 50, 75)
                await websocket.send_json(
                    create_progress_message(
                        progress=int(progress),
                        step=CrawlStep.COLLECTING,
                        site=SiteType.BLIND,
                        board=board_input,
                        details={
                            "current_page": page,
                            "matched_posts": len(matched_posts),
                            "target_range": f"{start_index}-{end_index}"
                        }
                    )
                )
            
            page_posts = await _crawl_blind_page(base_url, page, websocket)
            
            if not page_posts:
                consecutive_fails += 1
                if consecutive_fails >= 3:
                    break
                page += 1
                continue
            
            consecutive_fails = 0
            
            for post in page_posts:
                all_posts.append(post)
                
                # 조건 체크
                is_valid, reason = condition_checker.check_post_conditions(post)
                if is_valid:
                    matched_posts.append(post)
                    
                    # 목표 개수 달성시 중단
                    if len(matched_posts) >= (end_index - start_index + 1):
                        break
            
            # 중단 조건 체크
            should_stop, stop_reason = condition_checker.should_stop_crawling(
                consecutive_fails, bool(condition_checker.start_dt and condition_checker.end_dt)
            )
            if should_stop:
                break
            
            # 목표 개수 달성시 중단
            if len(matched_posts) >= (end_index - start_index + 1):
                break
            
            page += 1
            
        except Exception as e:
            print(f"Error on page {page}: {e}")
            page += 1
            if consecutive_fails > 5:
                break
    
    # 최종 결과 슬라이싱
    final_posts = matched_posts[start_index-1:end_index] if start_index <= len(matched_posts) else matched_posts
    
    # 번호 부여
    for idx, post in enumerate(final_posts):
        post['번호'] = start_index + idx
    
    return final_posts

def get_blind_sort_params(sort_method: str) -> str:
    """Blind 정렬 파라미터 생성"""
    blind_sort_map = {
        "popular": "sort=popular&order=desc",
        "recommend": "sort=recommend&order=desc",
        "comments": "sort=reply&order=desc",
        "recent": "sort=recent&order=desc",
        "hot": "sort=hot&order=desc",
    }
    
    return blind_sort_map.get(sort_method, "")

def sort_posts(posts, sort_method):
    """게시물 정렬 함수"""
    if not posts:
        return posts
    
    try:
        if sort_method == "popular":
            # 조회수 기준 내림차순 정렬
            return sorted(posts, key=lambda x: x.get('조회수', 0), reverse=True)
        elif sort_method == "recommend":
            # 추천수 기준 내림차순 정렬
            return sorted(posts, key=lambda x: x.get('추천수', 0), reverse=True)
        elif sort_method == "comments":
            # 댓글수 기준 내림차순 정렬
            return sorted(posts, key=lambda x: x.get('댓글수', 0), reverse=True)
        elif sort_method == "recent":
            # 최신순 정렬 (기본 순서 유지)
            return posts
        elif sort_method == "hot":
            # 인기순 (조회수와 추천수 조합)
            return sorted(posts, key=lambda x: x.get('조회수', 0) + x.get('추천수', 0) * 2, reverse=True)
        else:
            return posts
    except Exception as e:
        print(f"정렬 오류: {e}")
        return posts

# ==================== 메인 크롤링 함수 ====================

async def crawl_blind_board(
    board_input: str, limit: int = 50, sort: str = "recent",
    min_views: int = 0, min_likes: int = 0, min_comments: int = 0,
    time_filter: str = "all", start_date: str = None, end_date: str = None,
    websocket=None, enforce_date_limit=False, start_index: int = 1, end_index: int = 20
) -> List[Dict]:
    """강화된 조건 기반 지능형 Blind 크롤링"""
    
    try:
        if websocket:
            await websocket.send_json(
                create_progress_message(
                    progress=5,
                    step=CrawlStep.INITIALIZING,
                    site=SiteType.BLIND,
                    board=board_input,
                    details={
                        "sort": sort,
                        "range": f"{start_index}-{end_index}",
                        "filters": {
                            "min_views": min_views,
                            "min_likes": min_likes,
                            "min_comments": min_comments
                        }
                    }
                )
            )
        
        # 조건 체커 초기화
        condition_checker = BlindConditionChecker(
            min_views=min_views,
            min_likes=min_likes,
            min_comments=min_comments,
            start_date=start_date,
            end_date=end_date
        )
        
        # 필터 적용 여부 확인
        has_filters = (min_views > 0 or min_likes > 0 or min_comments > 0 or 
                      (start_date and end_date))
        
        if has_filters:
            required_limit = min(end_index * 5, 500)
            enforce_date_limit = True
        else:
            required_limit = end_index + 10
            enforce_date_limit = False
        
        if websocket:
            await websocket.send_json(
                create_progress_message(
                    progress=10,
                    step=CrawlStep.DETECTING_SITE,
                    site=SiteType.BLIND,
                    board=board_input,
                    details={"filters_applied": has_filters}
                )
            )
        
        # 지능형 크롤링 실행
        final_posts = await _execute_intelligent_blind_crawling(
            board_input, condition_checker, required_limit, sort,
            start_index, end_index, websocket, enforce_date_limit
        )
        
        if websocket:
            await websocket.send_json(
                create_complete_message(
                    total_count=len(final_posts),
                    site=SiteType.BLIND,
                    board=board_input,
                    start_rank=start_index,
                    end_rank=start_index + len(final_posts) - 1 if final_posts else start_index
                )
            )
        
        print(f"Blind 크롤링 완료: {len(final_posts)}개 게시물 ({start_index}-{start_index+len(final_posts)-1}위)")
        return final_posts
    
    except Exception as e:
        error_msg = f"Blind 크롤링 오류: {str(e)}"
        print(error_msg)
        
        if websocket:
            await websocket.send_json(
                create_error_message(
                    error_code=ErrorCode.CRAWLING_ERROR,
                    error_detail=error_msg,
                    site=SiteType.BLIND
                )
            )
        
        return []

# ==================== 유틸리티 함수들 ====================

def test_blind_sort_urls(board_input: str) -> dict:
    """다양한 정렬 URL 테스트"""
    board_id = resolve_blind_board_id(board_input)
    base_url = f"https://www.teamblind.com/kr/topics/{board_id}"
    
    test_urls = {
        "default": base_url,
        "popular1": f"{base_url}?sort=popular&order=desc",
        "popular2": f"{base_url}?s=popular&o=desc",
        "recommend1": f"{base_url}?sort=recommend&order=desc",
        "recommend2": f"{base_url}?s=recommend&o=desc",
        "comments1": f"{base_url}?sort=reply&order=desc",
        "comments2": f"{base_url}?s=reply&o=desc",
        "recent1": f"{base_url}?sort=recent&order=desc",
        "recent2": f"{base_url}?s=latest&o=desc",
        "hot1": f"{base_url}?sort=hot&order=desc",
        "hot2": f"{base_url}?s=hot&o=desc"
    }
    
    return test_urls

def list_available_topics() -> None:
    """사용 가능한 모든 Blind 토픽 출력"""
    board_map = load_blind_map()
    
    if not board_map:
        print("❌ 로드된 Blind 토픽이 없습니다.")
        return
    
    print(f"\n📋 총 {len(board_map)}개의 Blind 토픽:")
    for i, (name, board_id) in enumerate(sorted(board_map.items()), 1):
        print(f"{i:3d}. {name} (ID: {board_id})")

def search_topics(keyword: str) -> None:
    """키워드로 Blind 토픽 검색"""
    keyword = keyword.strip().lower()
    board_map = load_blind_map()
    
    if not board_map:
        print("❌ 로드된 Blind 토픽이 없습니다.")
        return
    
    matches = [(name, board_id) for name, board_id in board_map.items() 
               if keyword in name.lower()]
    
    if not matches:
        print(f"❌ '{keyword}'와 일치하는 토픽을 찾을 수 없습니다.")
        return
    
    print(f"\n🔍 '{keyword}' 검색 결과 ({len(matches)}개):")
    for i, (name, board_id) in enumerate(matches, 1):
        print(f"{i:3d}. {name} (ID: {board_id})")

def filter_by_time_period(posts, time_filter):
    """시간 기간으로 게시물 필터링"""
    if time_filter == "all":
        return posts
    
    now = datetime.now()
    
    if time_filter == "day":
        cutoff = now - timedelta(days=1)
    elif time_filter == "week":
        cutoff = now - timedelta(weeks=1)
    elif time_filter == "month":
        cutoff = now - timedelta(days=30)
    elif time_filter == "year":
        cutoff = now - timedelta(days=365)
    else:
        return posts
    
    filtered_posts = []
    for post in posts:
        post_date = _parse_blind_date(post.get('작성일', ''))
        if post_date and post_date >= cutoff:
            filtered_posts.append(post)
    
    print(f"Time filtering ({time_filter}): {len(filtered_posts)}/{len(posts)} posts")
    return filtered_posts