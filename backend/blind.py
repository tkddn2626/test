
# blind.py - Enhanced Blind crawling and filtering

import requests
from bs4 import BeautifulSoup
import json
import os
import re
from datetime import datetime, timedelta
from typing import Tuple, List, Dict, Optional

# JSON file path
BLIND_JSON_PATH = os.path.join("id_data", "boards.json")

def load_blind_map() -> dict:
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

def extract_post_metrics(item) -> Tuple[int, int]:
    """Extract views and likes from a post (enhanced)"""
    views = 0
    likes = 0

    try:
        view_selectors = [
            '.view-count', '.views', '[class*="view"]',
            '.count', '[data-view]', '.meta .count'
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

        like_selectors = [
            '.like-count', '.likes', '.recommend', '[class*="like"]',
            '[class*="thumb"]', '.vote', '[data-like]', '.reaction'
        ]
        for selector in like_selectors:
            like_elements = item.select(selector)
            for element in like_elements:
                text = element.text.strip()
                numbers = re.findall(r'\d+', text)
                if numbers and ('좋아요' in text or '추천' in text or 'like' in text.lower()):
                    likes = int(numbers[0])
                    break
            if likes > 0:
                break
    except Exception as e:
        print(f"Error extracting metrics: {e}")

    return views, likes

def _parse_blind_date(date_text: str) -> Optional[datetime]:
    """Parse dates (relative and absolute) from Blind"""
    if not date_text:
        return None
    try:
        now = datetime.now()
        if '분 전' in date_text:
            minutes = int(re.findall(r'\d+', date_text)[0])
            return now - timedelta(minutes=minutes)
        elif '시간 전' in date_text:
            hours = int(re.findall(r'\d+', date_text)[0])
            return now - timedelta(hours=hours)
        elif '일 전' in date_text:
            days = int(re.findall(r'\d+', date_text)[0])
            return now - timedelta(days=days)

        date_formats = [
            '%Y.%m.%d %H:%M',
            '%Y-%m-%d %H:%M',
            '%Y.%m.%d',
            '%Y-%m-%d'
        ]
        for fmt in date_formats:
            try:
                return datetime.strptime(date_text.strip(), fmt)
            except ValueError:
                continue
        return None
    except Exception:
        return None

def extract_post_date(item) -> str:
    """Extract the post's date (enhanced)"""
    try:
        date_selectors = [
            '.date', '.time', '[class*="date"]', '[class*="time"]',
            '.created', '.posted', '.timestamp', '[data-date]'
        ]
        for selector in date_selectors:
            date_element = item.select_one(selector)
            if date_element:
                date_text = date_element.text.strip()
                if date_text:
                    if '전' in date_text:
                        parsed = _parse_blind_date(date_text)
                        return parsed.strftime('%Y.%m.%d %H:%M') if parsed else date_text
                    elif re.search(r'\d{4}[-./]\d{1,2}[-./]\d{1,2}', date_text):
                        return date_text
                    elif re.search(r'\d{1,2}[-./]\d{1,2}', date_text):
                        return f"{datetime.now().year}.{date_text}"
                    else:
                        return date_text
        return datetime.now().strftime('%Y.%m.%d')
    except Exception as e:
        print(f"Error extracting date: {e}")
        return ""

def filter_by_date_range(posts: List[Dict], start_date_str: str, end_date_str: str) -> List[Dict]:
    """Filter posts by date range"""
    if not start_date_str or not end_date_str:
        return posts
    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
        end_date = end_date.replace(hour=23, minute=59, second=59)
        filtered_posts = []
        for post in posts:
            filtered_posts.append(post)
        print(f"Date filtering: {len(posts)} -> {len(filtered_posts)} posts")
        return filtered_posts
    except Exception as e:
        print(f"Date filtering error: {e}")
        return posts

def filter_by_time_period(posts: List[Dict], time_filter: str) -> List[Dict]:
    """Filter posts by time period"""
    if time_filter == "all":
        return posts
    print(f"Time filtering ({time_filter}): {len(posts)} posts (no filtering applied for Blind)")
    return posts

def sort_posts(posts: List[Dict], sort_method: str) -> List[Dict]:
    """Sort posts, including by comments"""
    if not posts:
        return posts
    try:
        if sort_method == "popular":
            return sorted(posts, key=lambda x: x.get('조회수', 0), reverse=True)
        elif sort_method == "recommend":
            return sorted(posts, key=lambda x: x.get('추천수', 0), reverse=True)
        elif sort_method == "comments":
            return sorted(posts, key=lambda x: x.get('댓글수', 0), reverse=True)
        elif sort_method == "recent":
            return posts
        else:
            return posts
    except Exception as e:
        print(f"Sort error: {e}")
        return posts

class BlindConditionChecker:
    """Condition checker for Blind postings"""

    def __init__(self, min_views: int = 0, min_likes: int = 0, min_comments: int = 0,
                 start_date: str = None, end_date: str = None):
        self.min_views = min_views
        self.min_likes = min_likes
        self.min_comments = min_comments
        self.start_dt = self._parse_date(start_date)
        self.end_dt = self._parse_date(end_date)
        if self.end_dt:
            self.end_dt = self.end_dt.replace(hour=23, minute=59, second=59)

    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        if not date_str:
            return None
        try:
            return datetime.strptime(date_str, '%Y-%m-%d')
        except Exception:
            return None

    def _extract_post_date(self, post: Dict) -> Optional[datetime]:
        date_str = post.get('작성일', '')
        return _parse_blind_date(date_str)

    def check_post_conditions(self, post: dict) -> Tuple[bool, str]:
        views = post.get('조회수', 0)
        likes = post.get('추천수', 0)
        comments = post.get('댓글수', 0)
        if views < self.min_views:
            return False, f"조회수 부족: {views} < {self.min_views}"
        if likes < self.min_likes:
            return False, f"추천수 부족: {likes} < {self.min_likes}"
        if comments < self.min_comments:
            return False, f"댓글수 부족: {comments} < {self.min_comments}"
        if self.start_dt and self.end_dt:
            post_date = self._extract_post_date(post)
            if post_date:
                if not (self.start_dt <= post_date <= self.end_dt):
                    return False, "날짜 범위 벗어남"
        return True, "조건 만족"

    def should_stop_crawling(self, consecutive_fails: int, has_date_filter: bool) -> Tuple[bool, str]:
        fail_threshold = 10 if has_date_filter else 20
        if consecutive_fails >= fail_threshold:
            return True, "조건 불만족으로 중단"
        return False, "계속 진행"

def _extract_blind_post_data(item) -> Optional[Dict]:
    """Extract individual Blind post data"""
    title_tag = item.select_one("h3 > a")
    body_tag = item.select_one("p.pre-txt > a")
    if not title_tag or not body_tag:
        return None
    views, likes = extract_post_metrics(item)
    comments = 0
    comment_elements = item.select('.comment-count, .comments, [class*="comment"], .reply')
    for element in comment_elements:
        comment_text = element.text.strip()
        comment_numbers = re.findall(r'\d+', comment_text)
        if comment_numbers:
            comments = int(comment_numbers[0])
            break
    date_str = extract_post_date(item)
    author = _extract_author(item)
    return {
        "원제목": title_tag.text.strip(),
        "번역제목": None,
        "링크": "https://www.teamblind.com" + title_tag.get("href"),
        "본문": body_tag.text.strip(),
        "썸네일 URL": None,
        "조회수": views,
        "추천수": likes,
        "댓글수": comments,
        "작성일": date_str,
        "작성자": author,
        "크롤링방식": "Blind-Enhanced"
    }

def _extract_author(item) -> str:
    author_element = item.select_one('.author, .writer, [class*="author"], [class*="writer"]')
    return author_element.text.strip() if author_element else "익명"

async def _crawl_blind_page(base_url: str, page: int, websocket=None) -> List[Dict]:
    """"Crawl a single Blind page"""""
    page_url = f"{base_url}{'&' if '?' in base_url else '?'}page={page}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    response = requests.get(page_url, headers=headers)
    if response.status_code != 200:
        return []
    soup = BeautifulSoup(response.text, "html.parser")
    items = soup.select("div.article-list-pre")
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

async def _execute_intelligent_blind_crawling(board_input: str, condition_checker,
    required_limit: int, sort: str, start_index: int, end_index: int,
    websocket=None, enforce_date_limit=False) -> List[Dict]:
    """"Execute intelligent Blind crawling"""""
    board_id = resolve_blind_board_id(board_input)
    sort_params = get_blind_sort_params(sort)
    base_url = f"https://www.teamblind.com/kr/topics/{board_id}"
    if sort_params:
        base_url += f"?{sort_params}"
    all_posts = []
    matched_posts = []
    consecutive_fails = 0
    page = 1
    max_pages = 200 if enforce_date_limit else min(20, (end_index // 20) + 3)
    while page <= max_pages:
        try:
            page_posts = await _crawl_blind_page(base_url, page, websocket)
            if not page_posts:
                consecutive_fails += 1
                if consecutive_fails >= 3: break
                page += 1
                continue
            consecutive_fails = 0
            for post in page_posts:
                all_posts.append(post)
                is_valid, reason = condition_checker.check_post_conditions(post)
                if is_valid:
                    matched_posts.append(post)
                    if len(matched_posts) >= (end_index - start_index + 1):
                        break
            should_stop, stop_reason = condition_checker.should_stop_crawling(
                consecutive_fails, bool(condition_checker.start_dt and condition_checker.end_dt)
            )
            if should_stop:
                break
            if len(matched_posts) >= (end_index - start_index + 1):
                break
            page += 1
        except Exception as e:
            print(f"Error on page {page}: {e}")
            page += 1
            if consecutive_fails > 5: break
    final_posts = matched_posts[start_index-1:end_index] if start_index <= len(matched_posts) else matched_posts
    for idx, post in enumerate(final_posts):
        post['번호'] = start_index + idx
    return final_posts

async def crawl_blind_board(board_input: str, limit: int = 50, sort: str = "recent",
    min_views: int = 0, min_likes: int = 0, min_comments: int = 0,
    time_filter: str = "all", start_date: str = None, end_date: str = None,
    websocket=None, enforce_date_limit=False, start_index: int = 1, end_index: int = 20) -> List[Dict]:
    """Enhanced condition-based intelligent Blind crawling"""
    condition_checker = BlindConditionChecker(
        min_views=min_views, min_likes=min_likes, min_comments=min_comments,
        start_date=start_date, end_date=end_date
    )
    has_filters = (min_views > 0 or min_likes > 0 or min_comments > 0 or (start_date and end_date))
    if has_filters:
        required_limit = min(end_index * 5, 500)
        enforce_date_limit = True
    else:
        required_limit = end_index + 10
        enforce_date_limit = False
    return await _execute_intelligent_blind_crawling(
        board_input, condition_checker, required_limit, sort,
        start_index, end_index, websocket, enforce_date_limit
    )

def get_blind_sort_params(sort_method: str) -> str:
    """Generate Blind sort parameters"""
    blind_sort_map = {
        "popular": "sort=popular&order=desc",
        "recommend": "sort=recommend&order=desc",
        "comments": "sort=reply&order=desc",
        "recent": "sort=recent&order=desc",
        "hot": "sort=hot&order=desc",
    }
    return blind_sort_map.get(sort_method, "")

def test_blind_sort_urls(board_input: str) -> dict:
    """Test various sort URLs for a given Blind board"""
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

def resolve_blind_board_id(keyword: str) -> str:
    """Automatically map a keyword to a Blind board ID using boards.json"""
    keyword = keyword.strip().lower()
    if not os.path.exists(BLIND_JSON_PATH):
        raise Exception("Error: boards.json not found. Run the builder script first.")
    with open(BLIND_JSON_PATH, "r", encoding="utf-8") as f:
        board_map = json.load(f)
    if not board_map:
        raise Exception("Error: boards.json is empty. Run the builder script first.")
    matches = [(name, board_id) for name, board_id in board_map.items() if keyword in name.lower()]
    if not matches:
        raise Exception(f"No matching Blind topic for '{keyword}'.")
    name, board_id = matches[0]
    return board_id

def list_available_topics() -> None:
    """Print all available Blind topics"""
    board_map = load_blind_map()
    if not board_map:
        print("No Blind topics loaded.")
        return
    print(f"Total {len(board_map)} Blind topics:")
    for i, (name, board_id) in enumerate(sorted(board_map.items()), 1):
        print(f"{i}. {name} (ID: {board_id})")

def search_topics(keyword: str) -> None:
    """Search Blind topics by keyword"""
    keyword = keyword.strip().lower()
    board_map = load_blind_map()
    if not board_map:
        print("No Blind topics loaded.")
        return
    matches = [(name, board_id) for name, board_id in board_map.items() if keyword in name.lower()]
    if not matches:
        print(f"No topics match '{keyword}'.")
        return
    print(f"Search results for '{keyword}' ({len(matches)}):")
    for i, (name, board_id) in enumerate(matches, 1):
        print(f"{i}. {name} (ID: {board_id})")
