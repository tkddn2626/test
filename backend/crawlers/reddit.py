# reddit.py - 순수 크롤링 로직만 (메시지 처리는 main.py에서)

import time
import logging
import requests
from datetime import datetime
import os
import re
from typing import Tuple
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

                # 썸네일 URL 추출
                thumbnail_url = None
                if hasattr(post, 'thumbnail') and post.thumbnail.startswith('http'):
                    thumbnail_url = post.thumbnail
                elif hasattr(post, 'preview') and 'images' in post.preview:
                    try:
                        thumbnail_url = post.preview['images'][0]['source']['url']
                    except:
                        pass

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

                # 본문 내용 구성 - 작성자만 표시
                content_parts = [f"Author: {author}"]

                is_external_link = original_url != reddit_url and not original_url.startswith('https://reddit.com')

                data.append({
                    "번호": start_index + idx - 1,
                    "원제목": title,
                    "번역제목": None,
                    "링크": reddit_url,
                    "원문URL": original_url if is_external_link else reddit_url,
                    "썸네일 URL": thumbnail_url,
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
                    "정렬방식": sort,
                    "시간필터": time_filter,
                    "크롤링방식": "Reddit-Enhanced-API"
                })

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

# 모듈 정보 (동적 탐지를 위한 메타데이터)
DISPLAY_NAME = "Reddit Crawler"
DESCRIPTION = "Reddit 서브레딧 크롤러"
VERSION = "2.0.0"
SUPPORTED_DOMAINS = ["reddit.com", "www.reddit.com", "old.reddit.com", "new.reddit.com"]
KEYWORDS = ["reddit", "subreddit", "/r/"]