# reddit.py - 순수 크롤링 로직만 (메시지 처리는 main.py에서)

import time
import logging
import requests
from datetime import datetime
import os
import re
from typing import Tuple, Optional
from dotenv import load_dotenv

# praw 임포트를 try-except로 보호
try:
    import praw
    PRAW_AVAILABLE = True
except ImportError:
    PRAW_AVAILABLE = False
    praw = None
    logging.warning("praw 라이브러리가 설치되지 않았습니다. pip install praw로 설치하세요.")

# 환경변수 로드
load_dotenv()

# 로그 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# Reddit API 설정
reddit = None
if PRAW_AVAILABLE:
    try:
        reddit = praw.Reddit(
            client_id=os.getenv("REDDIT_CLIENT_ID"),
            client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
            user_agent=os.getenv("REDDIT_USER_AGENT", "Community Crawler/1.0"),
        )
        reddit.user.me()
        logging.info("Reddit API 연결 성공")
    except Exception as e:
        logging.error(f"Reddit API 연결 실패: {e}")
        print("⚠️  Reddit API 설정을 확인하세요. .env 파일에 올바른 API 키가 있는지 확인하세요.")
        try:
            reddit = praw.Reddit(
                client_id="CKTo0QVk-WwjAFuqn4s4eA",
                client_secret="xTHOniOa516bvOnyvbluzCl7Xff-3g",
                user_agent="TIL Excel Crawler/0.1 by u/PerspectivePutrid665",
            )
        except Exception as fallback_error:
            logging.error(f"폴백 Reddit API 설정도 실패: {fallback_error}")
            reddit = None

def handle_reddit_errors(e, subreddit_name):
    """Reddit 특화 에러 처리"""
    msg = str(e)
    if "received 403 HTTP response" in msg:
        raise Exception(f"서브레딧 r/{subreddit_name}에 접근할 수 없습니다. 비공개이거나 존재하지 않을 수 있습니다.")
    elif "received 404 HTTP response" in msg:
        raise Exception(f"서브레딧 r/{subreddit_name}을(를) 찾을 수 없습니다.")
    elif "Redirect to login page" in msg:
        raise Exception("Reddit API 인증에 실패했습니다. .env 파일의 API 키를 확인하세요.")
    else:
        raise Exception(f"Reddit 크롤링 중 오류가 발생했습니다: {msg}")

class RedditConditionChecker:
    def __init__(self, min_views: int = 0, min_likes: int = 0, min_comments: int = 0,
                 start_date: str = None, end_date: str = None):
        self.min_views = min_views
        self.min_likes = min_likes
        self.min_comments = min_comments
        self.start_dt = self._parse_date(start_date)
        self.end_dt = self._parse_date(end_date)

    def _parse_date(self, date_str: str):
        if not date_str:
            return None
        try:
            return datetime.strptime(date_str, '%Y-%m-%d')
        except Exception:
            return None

    def check_post_conditions(self, post) -> Tuple[bool, str]:
        """Reddit 게시물 조건 검사"""
        views = post.num_comments
        likes = max(0, post.score)
        comments = post.num_comments

        if views < self.min_views:
            return False, f"조회수 부족: {views} < {self.min_views}"
        if likes < self.min_likes:
            return False, f"추천수 부족: {likes} < {self.min_likes}"
        if comments < self.min_comments:
            return False, f"댓글수 부족: {comments} < {self.min_comments}"

        # 날짜 검사
        if self.start_dt and self.end_dt:
            post_date = datetime.fromtimestamp(post.created_utc)
            if not (self.start_dt <= post_date <= (self.end_dt.replace(hour=23, minute=59, second=59))):
                return False, "날짜 범위 벗어남"

        return True, "조건 만족"

def format_reddit_date(timestamp):
    """Reddit 타임스탬프를 보기 좋은 날짜 형식으로 변환"""
    try:
        dt = datetime.fromtimestamp(timestamp)
        return dt.strftime('%Y.%m.%d %H:%M')
    except Exception as e:
        logging.error(f"Date formatting error: {e}")
        return ""

def extract_reddit_media_urls(post) -> Tuple[Optional[str], Optional[str]]:
    """
    Reddit 게시물에서 썸네일 URL과 원본 이미지/비디오 URL을 추출
    4chan.py 스타일로 구현 - 썸네일과 원본을 분리
    
    Returns:
        Tuple[썸네일_URL, 원본_이미지_URL]
    """
    thumbnail_url = None
    original_image_url = None
    
    try:
        # 1. 썸네일 URL 추출 (기존 방식 유지)
        if hasattr(post, 'thumbnail') and post.thumbnail.startswith('http'):
            thumbnail_url = post.thumbnail
        
        # 2. 원본 이미지/비디오 URL 추출 (새로운 방식)
        
        # 2-1. Reddit 호스팅 이미지 (i.redd.it)
        if hasattr(post, 'url') and post.url:
            url = post.url
            
            # Reddit 이미지 도메인들
            reddit_image_domains = ['i.redd.it', 'i.imgur.com', 'imgur.com']
            reddit_video_domains = ['v.redd.it']
            
            # 직접 이미지 URL인 경우
            if any(domain in url for domain in reddit_image_domains):
                if url.endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')):
                    original_image_url = url
                elif 'imgur.com' in url and not url.endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')):
                    # Imgur 링크를 직접 이미지 URL로 변환
                    if '/a/' not in url:  # 앨범이 아닌 경우
                        img_id = url.split('/')[-1].split('.')[0]
                        original_image_url = f"https://i.imgur.com/{img_id}.jpg"
            
            # Reddit 비디오인 경우
            elif any(domain in url for domain in reddit_video_domains):
                original_image_url = url  # 비디오 URL 그대로 사용
        
        # 2-2. Preview 이미지에서 고해상도 이미지 추출
        if not original_image_url and hasattr(post, 'preview'):
            try:
                preview_images = post.preview.get('images', [])
                if preview_images:
                    # 가장 높은 해상도의 이미지 선택
                    resolutions = preview_images[0].get('resolutions', [])
                    source = preview_images[0].get('source', {})
                    
                    # 원본 이미지 URL (최고 해상도)
                    if source and 'url' in source:
                        original_image_url = source['url'].replace('&amp;', '&')
                    # 해상도별 이미지 중 가장 큰 것 선택
                    elif resolutions:
                        highest_res = max(resolutions, key=lambda x: x.get('width', 0) * x.get('height', 0))
                        original_image_url = highest_res['url'].replace('&amp;', '&')
            except Exception as e:
                logging.debug(f"Preview 이미지 추출 실패: {e}")
        
        # 2-3. Gallery 이미지 처리 (Reddit 갤러리)
        if not original_image_url and hasattr(post, 'is_gallery') and post.is_gallery:
            try:
                if hasattr(post, 'media_metadata'):
                    # 첫 번째 갤러리 이미지 사용
                    for media_id, media_data in post.media_metadata.items():
                        if 's' in media_data and 'u' in media_data['s']:
                            original_image_url = media_data['s']['u'].replace('&amp;', '&')
                            break
            except Exception as e:
                logging.debug(f"갤러리 이미지 추출 실패: {e}")
        
        # 2-4. Reddit 비디오 처리
        if not original_image_url and hasattr(post, 'is_video') and post.is_video:
            try:
                if hasattr(post, 'media') and post.media:
                    reddit_video = post.media.get('reddit_video', {})
                    if 'fallback_url' in reddit_video:
                        original_image_url = reddit_video['fallback_url']
                    elif 'dash_url' in reddit_video:
                        original_image_url = reddit_video['dash_url']
            except Exception as e:
                logging.debug(f"Reddit 비디오 추출 실패: {e}")
        
        # 3. 썸네일이 없는 경우 원본 이미지를 썸네일로 사용 (4chan 방식)
        if not thumbnail_url and original_image_url:
            # 이미지인 경우에만 썸네일로 사용
            if any(ext in original_image_url.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']):
                thumbnail_url = original_image_url
        
        # 4. 로깅 (디버깅용)
        if original_image_url:
            logging.debug(f"원본 이미지 URL 추출 성공: {original_image_url}")
        if thumbnail_url:
            logging.debug(f"썸네일 URL 추출 성공: {thumbnail_url}")
            
    except Exception as e:
        logging.error(f"미디어 URL 추출 중 오류: {e}")
    
    return thumbnail_url, original_image_url

def get_reddit_media_type(post) -> str:
    """Reddit 게시물의 미디어 타입 판별"""
    try:
        if hasattr(post, 'is_video') and post.is_video:
            return "video"
        elif hasattr(post, 'is_gallery') and post.is_gallery:
            return "gallery"
        elif hasattr(post, 'url') and post.url:
            url = post.url.lower()
            if any(ext in url for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']):
                return "image"
            elif any(ext in url for ext in ['.mp4', '.webm', '.mov']):
                return "video"
            elif 'v.redd.it' in url:
                return "video"
            elif any(domain in url for domain in ['imgur.com', 'i.imgur.com']):
                return "image"
        return "text"
    except Exception:
        return "text"

async def fetch_posts(subreddit_name, limit=50, sort='top', time_filter='day', websocket=None, 
                     cancel_event=None, min_views=0, min_likes=0, min_comments=0,
                     start_date=None, end_date=None, enforce_date_limit=False, 
                     start_index=1, end_index=20):
    """
    Reddit 게시물 크롤링 함수 - 순수 크롤링 로직만
    """
    start_time = time.time()
    
    # praw 사용 가능성 확인
    if not PRAW_AVAILABLE or reddit is None:
        error_msg = "Reddit 크롤러를 사용할 수 없습니다. praw 라이브러리를 설치하고 API 키를 설정하세요."
        logging.error(error_msg)
        raise Exception(error_msg)
    
    try:
        logging.info(f"Reddit 크롤링 시작: r/{subreddit_name} (범위: {start_index}-{end_index})")

        subreddit = reddit.subreddit(subreddit_name)

        # 수집 전략 결정
        if enforce_date_limit and start_date and end_date:
            fetch_limit = 2000
            actual_time_filter = 'all'
        else:
            if min_views > 0 or min_likes > 0 or min_comments > 0:
                fetch_limit = end_index * 3
            else:
                fetch_limit = end_index + 10
            actual_time_filter = time_filter

        # Reddit API 호출
        if sort == 'top':
            posts_generator = subreddit.top(time_filter=actual_time_filter, limit=fetch_limit)
        elif sort == 'hot':
            posts_generator = subreddit.hot(limit=fetch_limit)
        elif sort == 'new':
            posts_generator = subreddit.new(limit=fetch_limit)
        elif sort == 'rising':
            posts_generator = subreddit.rising(limit=fetch_limit)
        elif sort == 'best':
            posts_generator = subreddit.best(limit=fetch_limit)
        else:
            posts_generator = subreddit.top(time_filter=actual_time_filter, limit=fetch_limit)

        all_posts = list(posts_generator)
        logging.info(f"초기 수집: {len(all_posts)}개 from r/{subreddit_name}")

        # 조건 검사기 생성
        condition_checker = RedditConditionChecker(
            min_views=min_views,
            min_likes=min_likes,
            min_comments=min_comments,
            start_date=start_date,
            end_date=end_date
        )

        matched_posts = []
        consecutive_fails = 0
        target_count = end_index - start_index + 1

        for i, post in enumerate(all_posts):
            if cancel_event and cancel_event.is_set():
                break

            is_valid, reason = condition_checker.check_post_conditions(post)
            if is_valid:
                matched_posts.append(post)
                consecutive_fails = 0
                if len(matched_posts) >= target_count and not enforce_date_limit:
                    break
            else:
                consecutive_fails += 1
                if consecutive_fails >= 20:
                    break

        logging.info(f"조건 필터링 후: {len(matched_posts)}개 매칭됨")

        # 최종 범위 적용
        if not enforce_date_limit:
            final_posts = matched_posts[start_index-1:end_index] if len(matched_posts) >= start_index else []
        else:
            final_posts = matched_posts

        data = []
        total_posts = len(final_posts)

        if total_posts == 0:
            logging.warning("필터링 후 게시물이 없음")
            return []

        # 게시물 데이터 구성
        for idx, post in enumerate(final_posts, start=1):
            if cancel_event and cancel_event.is_set():
                break
            
            try:
                title = post.title
                original_url = post.url if post.url.startswith("http") else f"https://reddit.com{post.permalink}"
                reddit_url = f"https://reddit.com{post.permalink}"

                # 🔥 향상된 미디어 URL 추출 (4chan 방식 적용)
                thumbnail_url, original_image_url = extract_reddit_media_urls(post)
                
                # 미디어 타입 판별
                media_type = get_reddit_media_type(post)

                created_date = format_reddit_date(post.created_utc)
                score = max(0, post.score)
                num_comments = post.num_comments

                # 작성자 정보
                try:
                    author = str(post.author) if post.author else "[deleted]"
                except:
                    author = "[deleted]"

                # 게시물 플레어 추출
                flair = ""
                if hasattr(post, 'link_flair_text') and post.link_flair_text:
                    flair = post.link_flair_text

                post_id = post.id

                # 본문 내용 구성 - 작성자와 미디어 타입 표시
                content_parts = [f"Author: {author}"]
                if media_type != "text":
                    content_parts.append(f"Media: {media_type}")

                is_external_link = original_url != reddit_url and not original_url.startswith('https://reddit.com')

                # 파일 정보 추가 (4chan 스타일)
                file_info = {}
                if original_image_url:
                    file_info.update({
                        "파일URL": original_image_url,
                        "미디어타입": media_type
                    })

                data_entry = {
                    "번호": start_index + idx - 1,
                    "원제목": title,
                    "번역제목": None,
                    "링크": reddit_url,
                    "원문URL": original_url if is_external_link else reddit_url,
                    "썸네일 URL": thumbnail_url,
                    "이미지 URL": original_image_url,  # 🔥 4chan 스타일 원본 이미지 URL
                    "본문": " | ".join(content_parts),
                    "조회수": num_comments,
                    "추천수": score,
                    "댓글수": num_comments,
                    "작성일": created_date,
                    "작성자": author,
                    "플레어": flair,
                    "게시물ID": post_id,
                    "서브레딧": subreddit_name,
                    "upvotes": post.ups if hasattr(post, 'ups') else score,
                    "downvotes": post.downs if hasattr(post, 'downs') else 0,
                    "upvote_ratio": post.upvote_ratio if hasattr(post, 'upvote_ratio') else 0,
                    "nsfw": post.over_18 if hasattr(post, 'over_18') else False,
                    "stickied": post.stickied if hasattr(post, 'stickied') else False,
                    "미디어타입": media_type,  # 🔥 새로운 필드
                    "정렬방식": sort,
                    "시간필터": time_filter,
                    "크롤링방식": "Reddit-Enhanced-API-v2",  # 🔥 버전 업그레이드
                    "플랫폼": "reddit"  # 🔥 4chan 스타일 플랫폼 표시
                }

                # 파일 정보가 있으면 추가
                data_entry.update(file_info)

                data.append(data_entry)

                time.sleep(0.1)

            except Exception as e:
                logging.error(f"게시물 처리 오류 {idx}: {e}")
                continue

        elapsed_time = time.time() - start_time
        logging.info(f"Reddit 크롤링 완료: {len(data)}개 게시물 ({start_index}-{start_index+len(data)-1}위)")

        return data

    except Exception as e:
        logging.error(f"Reddit 크롤링 오류: {e}")
        handle_reddit_errors(e, subreddit_name)

# ================================
# 🔥 유틸리티 함수들 (4chan 스타일)
# ================================

def detect_reddit_url_and_extract_info(url: str) -> dict:
    """Reddit URL 감지 및 정보 추출 (4chan 스타일)"""
    reddit_patterns = [
        r'^(?:https?://)?(?:www\.|old\.|new\.)?reddit\.com/r/([^/]+)/?$',
        r'^(?:https?://)?(?:www\.|old\.|new\.)?reddit\.com/r/([^/]+)/.*$',
        r'^r/([^/]+)/?$',
        r'^([a-zA-Z][a-zA-Z0-9_]{2,20})$'  # 서브레딧 이름만
    ]
    
    for pattern in reddit_patterns:
        match = re.match(pattern, url.strip(), re.IGNORECASE)
        if match:
            subreddit_name = match.group(1)
            return {
                "is_reddit": True,
                "subreddit_name": subreddit_name,
                "parsed_url": f"https://reddit.com/r/{subreddit_name}",
                "input_type": "subreddit"
            }
    
    return {"is_reddit": False}

def is_reddit_url(url: str) -> bool:
    """Reddit URL인지 확인"""
    if not url:
        return False
    return detect_reddit_url_and_extract_info(url).get("is_reddit", False)

# 모듈 정보 (동적 탐지를 위한 메타데이터)
DISPLAY_NAME = "Reddit Crawler Enhanced"
DESCRIPTION = "Reddit 서브레딧 크롤러 (이미지/비디오 지원)"
VERSION = "2.1.0"  # 🔥 버전 업그레이드
SUPPORTED_DOMAINS = ["reddit.com", "www.reddit.com", "old.reddit.com", "new.reddit.com"]
KEYWORDS = ["reddit", "subreddit", "/r/"]

# 모듈 로드 확인
logging.info("🔥 Reddit 크롤러 Enhanced v2.1 로드 완료")
logging.info("📊 지원 미디어: 이미지, 비디오, 갤러리")
logging.info("🎯 API: Reddit PRAW + 향상된 미디어 추출")
logging.info("🔍 URL 지원: 썸네일 + 원본 이미지 분리")
logging.info("🖼️ 4chan 스타일 이미지 처리 적용 완료")