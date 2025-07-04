# dcinside.py - 순수 크롤링 기능만 수행

import requests
from bs4 import BeautifulSoup
import json
import os
import re
import asyncio
from datetime import datetime, timedelta
from typing import Tuple, List, Dict, Optional

# ==================== 설정 및 경로 ====================

# JSON 파일 경로들
GALLERIES_JSON_PATH = os.path.join("crawlers", "id_data", "id_data", "galleries.json")
MGALLERIES_JSON_PATH = os.path.join("crawlers", "id_data", "id_data", "mgalleries.json")

# 크롤링 설정
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

# ==================== 갤러리 데이터 관리 ====================

def load_separated_gallery_data() -> Tuple[dict, dict]:
    """일반 갤러리와 마이너 갤러리를 분리해서 로드"""
    galleries_data = {}
    mgalleries_data = {}
    
    # 일반 갤러리 로드
    if os.path.exists(GALLERIES_JSON_PATH):
        try:
            with open(GALLERIES_JSON_PATH, "r", encoding="utf-8") as f:
                raw_data = json.load(f)
                for gallery_name, gallery_id in raw_data.items():
                    galleries_data[gallery_name] = {
                        "id": gallery_id,
                        "type": "gallery"
                    }
                print(f"✅ 일반 갤러리 로드: {len(galleries_data)}개")
        except Exception as e:
            print(f"❌ galleries.json 파싱 오류: {e}")
    
    # 마이너 갤러리 로드
    if os.path.exists(MGALLERIES_JSON_PATH):
        try:
            with open(MGALLERIES_JSON_PATH, "r", encoding="utf-8") as f:
                raw_data = json.load(f)
                for gallery_name, gallery_id in raw_data.items():
                    mgalleries_data[gallery_name] = {
                        "id": gallery_id,
                        "type": "mgallery"
                    }
                print(f"✅ 마이너 갤러리 로드: {len(mgalleries_data)}개")
        except Exception as e:
            print(f"❌ mgalleries.json 파싱 오류: {e}")
    
    return galleries_data, mgalleries_data

def resolve_dc_board_id(board_input: str) -> Tuple[str, str]:
    """갤러리명/ID를 실제 갤러리 ID와 타입으로 변환"""
    if not board_input:
        raise Exception("갤러리명 또는 ID를 입력해주세요.")
    
    board_input = board_input.strip()
    board_input_lower = board_input.lower()
    
    galleries_data, mgalleries_data = load_separated_gallery_data()
    
    if not galleries_data and not mgalleries_data:
        raise Exception("갤러리 데이터를 로드할 수 없습니다.")
    
    def search_in_gallery_data(gallery_data: dict, gallery_type: str) -> Optional[Tuple[str, str]]:
        # 1. 정확한 ID 매치
        for name, info in gallery_data.items():
            if board_input_lower == info['id'].lower():
                return info['id'], gallery_type
        
        # 2. 정확한 갤러리명 매치
        for name, info in gallery_data.items():
            if board_input_lower == name.lower():
                return info['id'], gallery_type
        
        # 3. 부분 매치
        matches = []
        for name, info in gallery_data.items():
            name_lower = name.lower()
            if board_input_lower in name_lower or name_lower.startswith(board_input_lower):
                matches.append((name, info))
        
        if matches:
            best_match = min(matches, key=lambda x: len(x[0]))
            return best_match[1]['id'], gallery_type
            
        return None
    
    # 마이너 갤러리 우선 검색
    if mgalleries_data:
        result = search_in_gallery_data(mgalleries_data, "mgallery")
        if result:
            return result
    
    # 일반 갤러리 검색
    if galleries_data:
        result = search_in_gallery_data(galleries_data, "gallery")
        if result:
            return result
    
    raise Exception(f"'{board_input}'와 매칭되는 갤러리를 찾을 수 없습니다.")

# ==================== 게시물 데이터 추출 ====================

def extract_post_metrics(item) -> Tuple[int, int, int]:
    """게시물에서 조회수, 추천수, 댓글수 추출"""
    views = likes = comments = 0

    try:
        # 조회수 추출
        view_selectors = ['.gall_count', '.view_count', '.hit']
        for selector in view_selectors:
            elements = item.select(selector)
            for element in elements:
                numbers = re.findall(r'\d+', element.text.strip())
                if numbers:
                    views = int(numbers[0])
                    break
            if views > 0:
                break

        # 추천수 추출
        like_selectors = ['.gall_recommend', '.recommend_count', '.up_num']
        for selector in like_selectors:
            elements = item.select(selector)
            for element in elements:
                numbers = re.findall(r'\d+', element.text.strip())
                if numbers:
                    likes = int(numbers[0])
                    break
            if likes > 0:
                break

        # 댓글수 추출
        comment_selectors = ['.gall_reply_num', '.reply_num', '.comment_count']
        for selector in comment_selectors:
            elements = item.select(selector)
            for element in elements:
                numbers = re.findall(r'\d+', element.text.strip())
                if numbers:
                    comments = int(numbers[0])
                    break
            if comments > 0:
                break

    except Exception as e:
        print(f"메트릭 추출 오류: {e}")

    return views, likes, comments

def extract_dcinside_post_data(item) -> Optional[Dict]:
    """개별 DCInside 게시물 데이터 추출"""
    try:
        # 제목 추출
        title_selectors = ['.gall_tit a', '.ub-word a', 'td.gall_tit a', '.title a', '.subject a']
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
        
        # 작성일 추출
        date_element = item.select_one('.gall_date, .date, .posting_time')
        date_str = date_element.text.strip() if date_element else "날짜 정보 없음"
        
        # 작성자 추출
        author_element = item.select_one('.gall_writer, .writer, .nickname')
        author = author_element.text.strip() if author_element else "익명"
        
        return {
            "원제목": title,
            "번역제목": None,
            "링크": link,
            "본문": "",
            "썸네일 URL": None,
            "조회수": views,
            "추천수": likes,
            "댓글수": comments,
            "작성일": date_str,
            "작성자": author,
            "크롤링방식": "DCInside-Enhanced"
        }
    
    except Exception as e:
        print(f"게시물 데이터 추출 오류: {e}")
        return None

# ==================== 날짜 및 조건 처리 ====================

def parse_dc_date(date_text: str) -> Optional[datetime]:
    """DCInside 날짜 파싱"""
    if not date_text:
        return None
    
    try:
        now = datetime.now()
        date_text = date_text.strip()
        
        # 상대적 시간 파싱
        if '분전' in date_text or '분 전' in date_text:
            numbers = re.findall(r'\d+', date_text)
            if numbers:
                minutes = int(numbers[0])
                return now - timedelta(minutes=minutes)
        elif '시간전' in date_text or '시간 전' in date_text:
            numbers = re.findall(r'\d+', date_text)
            if numbers:
                hours = int(numbers[0])
                return now - timedelta(hours=hours)
        elif '일전' in date_text or '일 전' in date_text:
            numbers = re.findall(r'\d+', date_text)
            if numbers:
                days = int(numbers[0])
                return now - timedelta(days=days)
        
        # 절대적 날짜 파싱
        date_patterns = [
            r'(\d{4})\.(\d{1,2})\.(\d{1,2})',  # YYYY.MM.DD
            r'(\d{1,2})\.(\d{1,2})',          # MM.DD (올해)
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, date_text)
            if match:
                groups = match.groups()
                try:
                    if len(groups) == 3:
                        year, month, day = map(int, groups)
                    elif len(groups) == 2:
                        year = now.year
                        month, day = map(int, groups)
                        if month > 12:
                            month, day = day, month
                    else:
                        continue
                    
                    return datetime(year, month, day)
                except ValueError:
                    continue
    
    except Exception:
        pass
    
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
                post_date = parse_dc_date(post.get('작성일', ''))
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

# ==================== 크롤링 실행 ====================

async def crawl_dcinside_page(base_url: str, page: int) -> List[Dict]:
    """DCInside 단일 페이지 크롤링"""
    page_url = f"{base_url}{'&' if '?' in base_url else '?'}page={page}"
    
    try:
        response = requests.get(page_url, headers=HEADERS, timeout=10)
        if response.status_code != 200:
            return []
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 게시물 리스트 셀렉터
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
            post_data = extract_dcinside_post_data(item)
            if post_data:
                posts.append(post_data)
        
        return posts
    
    except Exception as e:
        print(f"페이지 {page} 크롤링 오류: {e}")
        return []

def get_dcinside_sort_params(sort_method: str) -> str:
    """DCInside 정렬 파라미터 생성"""
    dc_sort_map = {
        "recommend": "sort_type=recommend&order=desc",
        "popular": "sort_type=hit&order=desc",
        "comments": "sort_type=reply&order=desc",
        "recent": "",
    }
    return dc_sort_map.get(sort_method, "")

async def execute_dcinside_crawling(
    board_name: str, condition_checker: DCInsideConditionChecker, 
    sort: str, start_index: int, end_index: int, websocket=None, enforce_date_limit=False
) -> List[Dict]:
    """DCInside 크롤링 실행"""
    
    # 갤러리 ID 및 타입 해결
    board_id, board_type = resolve_dc_board_id(board_name)
    
    # URL 구성
    if board_type == "mgallery":
        base_url = f"https://gall.dcinside.com/mgallery/board/lists/?id={board_id}"
        print(f"🎯 마이너 갤러리 접근: mgallery/{board_id}")
    else:
        base_url = f"https://gall.dcinside.com/board/lists/?id={board_id}"
        print(f"🎯 일반 갤러리 접근: board/{board_id}")
    
    # 정렬 파라미터 추가
    sort_params = get_dcinside_sort_params(sort)
    if sort_params:
        base_url += f"&{sort_params}"

    all_posts = []
    matched_posts = []
    consecutive_fails = 0
    page = 1
    max_pages = 200 if enforce_date_limit else min(20, (end_index // 20) + 3)
    
    while page <= max_pages:
        try:
            # 페이지별 진행률 메시지 (WebSocket으로 중간 진행률 전송)
            if websocket:
                page_progress = 25 + int((page / max_pages) * 50)  # 25%~75% 구간
                try:
                    await websocket.send_json({
                        "progress": page_progress,
                        "status": f"DCInside 페이지 {page}/{max_pages} 수집 중... (매칭: {len(matched_posts)}개)"
                    })
                except Exception as ws_error:
                    print(f"WebSocket 메시지 전송 오류: {ws_error}")
            
            page_posts = await crawl_dcinside_page(base_url, page)
            
            if not page_posts:
                consecutive_fails += 1
                if consecutive_fails >= 3:
                    break
                page += 1
                continue
            
            consecutive_fails = 0
            print(f"✅ 페이지 {page}: {len(page_posts)}개 게시물 수집")
            
            # 게시물 처리 및 필터링
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
            print(f"❌ 페이지 {page} 처리 오류: {e}")
            consecutive_fails += 1
            page += 1
            if consecutive_fails > 5:
                break
    
    # 최종 결과 슬라이싱 및 번호 부여
    final_posts = matched_posts[start_index-1:end_index] if start_index <= len(matched_posts) else matched_posts
    
    for idx, post in enumerate(final_posts):
        post['번호'] = start_index + idx
    
    print(f"✅ DCInside 크롤링 완료: 전체 {len(all_posts)}개 → 매칭 {len(matched_posts)}개 → 최종 {len(final_posts)}개")
    
    return final_posts

# ==================== 메인 크롤링 함수 ====================

async def crawl_dcinside_board(
    board_name: str, limit: int = 50, sort: str = "recent", 
    min_views: int = 0, min_likes: int = 0, min_comments: int = 0,
    time_filter: str = "all", start_date: str = None, 
    end_date: str = None, websocket=None, enforce_date_limit=False,
    start_index: int = 1, end_index: int = 20
) -> List[Dict]:
    """DCInside 크롤링 메인 함수"""
    
    try:
        print(f"🎯 DCInside 크롤링 시작 - 입력값: '{board_name}'")
        
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
            enforce_date_limit = True
        
        # 크롤링 실행
        final_posts = await execute_dcinside_crawling(
            board_name, condition_checker, sort,
            start_index, end_index, websocket, enforce_date_limit
        )
        
        print(f"✅ DCInside 크롤링 완료: {len(final_posts)}개 게시물")
        return final_posts
    
    except Exception as e:
        error_msg = f"DCInside 크롤링 오류: {str(e)}"
        print(error_msg)
        return []

# ==================== 모듈 정보 ====================

__all__ = [
    'crawl_dcinside_board',
    'resolve_dc_board_id',
    'get_gallery_statistics'
]

def get_gallery_statistics() -> Dict[str, any]:
    """갤러리 통계 정보 반환"""
    galleries_data, mgalleries_data = load_separated_gallery_data()
    
    return {
        "total_galleries": len(galleries_data) + len(mgalleries_data),
        "regular_galleries": len(galleries_data),
        "minor_galleries": len(mgalleries_data),
        "files_status": {
            "galleries_json": os.path.exists(GALLERIES_JSON_PATH),
            "mgalleries_json": os.path.exists(MGALLERIES_JSON_PATH)
        }
    }