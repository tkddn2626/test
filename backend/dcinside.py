# dcinside.py - DCInside 크롤링 및 필터링 완전 구현

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
DCINSIDE_JSON_PATH = os.path.join("id_data", "galleries.json")

def load_gallery_map() -> dict:
    """갤러리 맵핑 데이터 로드"""
    if not os.path.exists(DCINSIDE_JSON_PATH):
        print(f"Error: {DCINSIDE_JSON_PATH} not found")
        return {}

    try:
        with open(DCINSIDE_JSON_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            print(f"Loaded galleries.json ({len(data)} entries)")
            return data
    except Exception as e:
        print(f"Error parsing galleries.json: {e}")
        return {}

def resolve_dc_board_id(board_name: str) -> Tuple[str, str]:
    """갤러리 이름을 ID와 타입으로 변환"""
    board_name = board_name.strip().lower()
    gallery_map = load_gallery_map()
    
    if not gallery_map:
        raise Exception("Error: galleries.json not found or empty. Run the builder script first.")
    
    # 직접 매치 시도
    for name, info in gallery_map.items():
        if board_name == name.lower() or board_name == info['id']:
            return info['id'], info['type']
    
    # 부분 매치 시도
    matches = [(name, info) for name, info in gallery_map.items() 
               if board_name in name.lower()]
    
    if not matches:
        raise Exception(f"No matching gallery for '{board_name}'.")
    
    name, info = matches[0]
    print(f"📋 Found gallery: {name} (ID: {info['id']}, TYPE: {info['type']})")
    return info['id'], info['type']

def extract_post_metrics(item) -> Tuple[int, int, int]:
    """게시물에서 조회수, 추천수, 댓글수 추출 (강화버전)"""
    views = 0
    likes = 0
    comments = 0

    try:
        # 조회수 추출
        view_selectors = [
            '.gall_count', '.view_count', '.hit', 
            '[class*="hit"]', '[class*="view"]'
        ]
        for selector in view_selectors:
            elements = item.select(selector)
            for element in elements:
                text = element.text.strip()
                numbers = re.findall(r'\d+', text)
                if numbers:
                    views = int(numbers[0])
                    break
            if views > 0:
                break

        # 추천수 추출
        like_selectors = [
            '.gall_recommend', '.recommend_count', '.up_num',
            '[class*="recommend"]', '[class*="up"]'
        ]
        for selector in like_selectors:
            elements = item.select(selector)
            for element in elements:
                text = element.text.strip()
                numbers = re.findall(r'\d+', text)
                if numbers:
                    likes = int(numbers[0])
                    break
            if likes > 0:
                break

        # 댓글수 추출
        comment_selectors = [
            '.gall_reply_num', '.reply_num', '.comment_count',
            '[class*="reply"]', '[class*="comment"]'
        ]
        for selector in comment_selectors:
            elements = item.select(selector)
            for element in elements:
                text = element.text.strip()
                numbers = re.findall(r'\d+', text)
                if numbers:
                    comments = int(numbers[0])
                    break
            if comments > 0:
                break

    except Exception as e:
        print(f"Error extracting metrics: {e}")

    return views, likes, comments

def extract_post_date(item) -> str:
    """게시물 작성일 추출"""
    date_selectors = [
        '.gall_date', '.date', '.posting_time', 
        '[class*="date"]', '[class*="time"]'
    ]
    
    for selector in date_selectors:
        element = item.select_one(selector)
        if element:
            return element.text.strip()
    
    return "날짜 정보 없음"

def extract_post_author(item) -> str:
    """게시물 작성자 추출"""
    author_selectors = [
        '.gall_writer', '.writer', '.nickname',
        '[class*="writer"]', '[class*="nick"]'
    ]
    
    for selector in author_selectors:
        element = item.select_one(selector)
        if element:
            return element.text.strip()
    
    return "익명"

def extract_comments_count(item) -> int:
    """댓글수만 별도로 추출"""
    _, _, comments = extract_post_metrics(item)
    return comments

def _parse_dc_date(date_text: str) -> Optional[datetime]:
    """DCInside 날짜 파싱 (상대적/절대적 날짜 모두 지원)"""
    if not date_text:
        return None
    
    try:
        now = datetime.now()
        
        # 상대적 시간 파싱
        if '분전' in date_text or '분 전' in date_text:
            minutes = int(re.findall(r'\d+', date_text)[0])
            return now - timedelta(minutes=minutes)
        elif '시간전' in date_text or '시간 전' in date_text:
            hours = int(re.findall(r'\d+', date_text)[0])
            return now - timedelta(hours=hours)
        elif '일전' in date_text or '일 전' in date_text:
            days = int(re.findall(r'\d+', date_text)[0])
            return now - timedelta(days=days)
        
        # 절대적 날짜 파싱 (MM.DD, YYYY.MM.DD 등)
        date_patterns = [
            r'(\d{4})\.(\d{1,2})\.(\d{1,2})',  # YYYY.MM.DD
            r'(\d{1,2})\.(\d{1,2})',          # MM.DD (올해)
            r'(\d{4})-(\d{1,2})-(\d{1,2})',   # YYYY-MM-DD
            r'(\d{1,2})-(\d{1,2})'            # MM-DD (올해)
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, date_text)
            if match:
                groups = match.groups()
                if len(groups) == 3:  # YYYY.MM.DD
                    year, month, day = map(int, groups)
                elif len(groups) == 2:  # MM.DD
                    year = now.year
                    month, day = map(int, groups)
                else:
                    continue
                
                return datetime(year, month, day)
    
    except Exception as e:
        print(f"Date parsing error: {e}")
    
    return None

class DCInsideConditionChecker:
    """DCInside 게시물 조건 체크 클래스"""
    
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
                post_date = _parse_dc_date(post.get('작성일', ''))
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

def _extract_dcinside_post_data(item) -> Optional[Dict]:
    """개별 DCInside 게시물 데이터 추출"""
    try:
        # 제목 추출
        title_selectors = [
            '.gall_tit a', '.ub-word a', 'td.gall_tit a',
            '.title a', '.subject a'
        ]
        title_element = None
        for selector in title_selectors:
            title_element = item.select_one(selector)
            if title_element:
                break
        
        if not title_element:
            return None
        
        title = title_element.text.strip()
        link = title_element.get('href', '')
        
        # 절대 URL로 변환
        if link.startswith('/'):
            link = f"https://gall.dcinside.com{link}"
        elif not link.startswith('http'):
            link = f"https://gall.dcinside.com/{link}"
        
        # 메트릭 추출
        views, likes, comments = extract_post_metrics(item)
        
        # 날짜 및 작성자 추출
        date_str = extract_post_date(item)
        author = extract_post_author(item)
        
        return {
            "원제목": title,
            "번역제목": None,
            "링크": link,
            "본문": "",  # DCInside는 목록에서 본문 미제공
            "썸네일 URL": None,
            "조회수": views,
            "추천수": likes,
            "댓글수": comments,
            "작성일": date_str,
            "작성자": author,
            "크롤링방식": "DCInside-Enhanced"
        }
    
    except Exception as e:
        print(f"Error extracting post data: {e}")
        return None

async def _crawl_dcinside_page(base_url: str, page: int, websocket=None) -> List[Dict]:
    """DCInside 단일 페이지 크롤링"""
    page_url = f"{base_url}{'&' if '?' in base_url else '?'}page={page}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        response = requests.get(page_url, headers=headers, timeout=10)
        if response.status_code != 200:
            return []
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 다양한 게시물 리스트 셀렉터 시도
        item_selectors = [
            'tr.ub-content',  # 일반 갤러리
            'tr.us-post',     # 마이너 갤러리  
            '.gall_list tr',  # 기본 갤러리 리스트
            'tbody tr'        # 일반적인 테이블 행
        ]
        
        items = []
        for selector in item_selectors:
            items = soup.select(selector)
            if items:
                break
        
        posts = []
        for item in items:
            try:
                post_data = _extract_dcinside_post_data(item)
                if post_data:
                    posts.append(post_data)
            except Exception as e:
                print(f"Error extracting post: {e}")
                continue
        
        return posts
    
    except Exception as e:
        print(f"Error crawling page {page}: {e}")
        return []

async def _execute_intelligent_dcinside_crawling(
    board_name: str, condition_checker, required_limit: int, sort: str,
    start_index: int, end_index: int, websocket=None, enforce_date_limit=False
) -> List[Dict]:
    """지능형 DCInside 크롤링 실행"""
    
    board_id, board_type = resolve_dc_board_id(board_name)
    
    # URL 구성
    if board_type == "mgallery":
        base_url = f"https://gall.dcinside.com/mgallery/board/lists/?id={board_id}"
    else:
        base_url = f"https://gall.dcinside.com/board/lists/?id={board_id}"
    
    # 정렬 파라미터 추가
    sort_params = get_dcinside_sort_params(sort)
    if sort_params:
        base_url += f"&{sort_params}"
        
        if websocket:
            await websocket.send_json(
                create_progress_message(
                    progress=15,
                    step=CrawlStep.CONNECTING,
                    site=SiteType.DCINSIDE,
                    board=board_name,
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
                site=SiteType.DCINSIDE,
                board=board_name,
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
                        site=SiteType.DCINSIDE,
                        board=board_name,
                        details={
                            "current_page": page,
                            "matched_posts": len(matched_posts),
                            "target_range": f"{start_index}-{end_index}"
                        }
                    )
                )
            
            page_posts = await _crawl_dcinside_page(base_url, page, websocket)
            
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

def get_dcinside_sort_params(sort_method: str) -> str:
    """DCInside 정렬 파라미터 생성"""
    dc_sort_map = {
        "recommend": "sort_type=recommend&order=desc",     # 추천순
        "popular": "sort_type=hit&order=desc",             # 조회수순  
        "comments": "sort_type=reply&order=desc",          # 댓글순
        "recent": "",  # 기본 정렬 (최신순)
    }
    
    return dc_sort_map.get(sort_method, "")

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
        else:
            return posts
    except Exception as e:
        print(f"정렬 오류: {e}")
        return posts

def filter_by_time_period(posts, time_filter):
    """시간 기간으로 게시물 필터링"""
    if time_filter == "all":
        return posts
    
    # DC의 경우 시간 필터링이 제한적이므로 현재는 모든 게시물 반환
    # 실제 구현시 게시물의 작성일 정보를 파싱해야 함
    print(f"Time filtering ({time_filter}): {len(posts)} posts (no filtering applied for DCInside)")
    return posts

# ==================== 메인 크롤링 함수 ====================

async def crawl_dcinside_board(
    board_name: str, limit: int = 50, sort: str = "recent", 
    min_views: int = 0, min_likes: int = 0, min_comments: int = 0,
    time_filter: str = "all", start_date: str = None, 
    end_date: str = None, websocket=None, enforce_date_limit=False,
    start_index: int = 1, end_index: int = 20
) -> List[Dict]:
    """강화된 조건 기반 지능형 DCInside 크롤링"""
    
    try:
        if websocket:
            await websocket.send_json(
                create_progress_message(
                    progress=5,
                    step=CrawlStep.INITIALIZING,
                    site=SiteType.DCINSIDE,
                    board=board_name,
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
        condition_checker = DCInsideConditionChecker(
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
                    site=SiteType.DCINSIDE,
                    board=board_name,
                    details={"filters_applied": has_filters}
                )
            )
        
        # 지능형 크롤링 실행
        final_posts = await _execute_intelligent_dcinside_crawling(
            board_name, condition_checker, required_limit, sort,
            start_index, end_index, websocket, enforce_date_limit
        )
        
        if websocket:
            await websocket.send_json(
                create_complete_message(
                    total_count=len(final_posts),
                    site=SiteType.DCINSIDE,
                    board=board_name,
                    start_rank=start_index,
                    end_rank=start_index + len(final_posts) - 1 if final_posts else start_index
                )
            )
        
        print(f"DCInside 크롤링 완료: {len(final_posts)}개 게시물 ({start_index}-{start_index+len(final_posts)-1}위)")
        return final_posts
    
    except Exception as e:
        error_msg = f"DCInside 크롤링 오류: {str(e)}"
        print(error_msg)
        
        if websocket:
            await websocket.send_json(
                create_error_message(
                    error_code=ErrorCode.CRAWLING_ERROR,
                    error_detail=error_msg,
                    site=SiteType.DCINSIDE
                )
            )
        
        return []

# ==================== 유틸리티 함수들 ====================

def test_dcinside_sort_urls(board_name: str) -> dict:
    """DCInside 정렬 URL 테스트 함수"""
    board_id, board_type = resolve_dc_board_id(board_name)
    
    if board_type == "mgallery":
        base_url = f"https://gall.dcinside.com/mgallery/board/lists/?id={board_id}"
    else:
        base_url = f"https://gall.dcinside.com/board/lists/?id={board_id}"
    
    test_urls = {
        "기본": base_url,
        "추천순_v1": f"{base_url}&sort_type=recommend&order=desc",
        "추천순_v2": f"{base_url}&s=recommend&o=desc",
        "추천순_v3": f"{base_url}&sort=recommend",
        "조회수순_v1": f"{base_url}&sort_type=hit&order=desc",
        "조회수순_v2": f"{base_url}&s=hit&o=desc", 
        "조회수순_v3": f"{base_url}&sort=view",
        "댓글순_v1": f"{base_url}&sort_type=reply&order=desc",
        "댓글순_v2": f"{base_url}&s=reply&o=desc",
        "댓글순_v3": f"{base_url}&sort=reply"
    }
    
    return test_urls

def parse_dcinside(url: str) -> dict:
    """게시글 본문 추출 (선택적)"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        raise ValueError("요청 실패: 올바른 URL인지 확인하세요")

    soup = BeautifulSoup(response.text, 'html.parser')
    title_tag = soup.select_one('span.title_subject')
    content_tag = soup.select_one('div.write_div')

    if not title_tag or not content_tag:
        raise ValueError("게시글 구조를 파싱할 수 없습니다")

    return {
        "title": title_tag.text.strip(),
        "content": content_tag.text.strip()
    }

def list_available_galleries() -> None:
    """로드 가능한 모든 갤러리를 출력합니다."""
    gallery_map = load_gallery_map()

    if not gallery_map:
        print("❌ 로드된 갤러리가 없습니다.")
        return

    print(f"\n📋 총 {len(gallery_map)}개의 갤러리:")
    for i, (name, info) in enumerate(sorted(gallery_map.items()), 1):
        print(f"{i:3d}. {name} (ID: {info['id']}, TYPE: {info['type']})")

def search_galleries(keyword: str) -> None:
    """키워드로 갤러리를 검색합니다."""
    keyword = keyword.strip().lower()
    gallery_map = load_gallery_map()

    if not gallery_map:
        print("❌ 로드된 갤러리가 없습니다.")
        return

    matches = [(name, info) for name, info in gallery_map.items() 
               if keyword in name.lower() or keyword == info["id"]]

    if not matches:
        print(f"❌ '{keyword}'와 일치하는 갤러리를 찾을 수 없습니다.")
        return

    print(f"\n🔍 '{keyword}' 검색 결과 ({len(matches)}개):")
    for i, (name, info) in enumerate(matches, 1):
        print(f"{i:3d}. {name} (ID: {info['id']}, TYPE: {info['type']})")
