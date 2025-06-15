# reddit.py - 통합 메시지 시스템 적용

import time
import praw
import logging
import requests
from datetime import datetime
import os
import re
from typing import Tuple
from dotenv import load_dotenv

# 통합 메시지 시스템 import
from core.messages import (
    create_progress_message, create_error_message, create_complete_message,
    create_collecting_message, create_filtering_message, create_translation_message,
    CrawlStep, SiteType, ErrorCode, SuccessType, quick_progress, quick_error
)

# 환경변수 로드
load_dotenv()

# 로그 설정
logging.basicConfig(
    filename="log.txt",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# Reddit API 설정
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
    reddit = praw.Reddit(
        client_id="CKTo0QVk-WwjAFuqn4s4eA",
        client_secret="xTHOniOa516bvOnyvbluzCl7Xff-3g",
        user_agent="TIL Excel Crawler/0.1 by u/PerspectivePutrid665",
    )

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

# DeepL 번역 함수
def deepl_translate(text: str, target_lang: str = "KO") -> str:
    try:
        if not text or not text.strip():
            return ""

        deepl_api_key = os.getenv("DEEPL_API_KEY")
        if not deepl_api_key:
            logging.warning("DEEPL_API_KEY가 설정되지 않았습니다.")
            return "(번역 실패: API 키 없음)"

        if len(text) > 4000:
            text = text[:4000] + "..."

        response = requests.post(
            "https://api-free.deepl.com/v2/translate",
            data={
                "auth_key": deepl_api_key,
                "text": text,
                "target_lang": target_lang.upper()
            },
            timeout=10
        )

        if response.status_code == 200:
            result = response.json()
            if "translations" in result and len(result["translations"]) > 0:
                return result["translations"][0]["text"]
            else:
                logging.warning("DeepL API 응답에 번역 결과가 없습니다.")
                return "(번역 실패: 응답 오류)"
        else:
            logging.error(f"DeepL API 오류: {response.status_code} - {response.text}")
            return "(번역 실패: API 오류)"

    except requests.exceptions.Timeout:
        logging.warning("DeepL API 타임아웃")
        return "(번역 실패: 타임아웃)"
    except requests.exceptions.RequestException as e:
        logging.error(f"DeepL API 요청 오류: {e}")
        return "(번역 실패: 네트워크 오류)"
    except Exception as e:
        logging.error(f"DeepL 번역 오류: {e}")
        return "(번역 실패)"

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
    강화된 Reddit 게시물 크롤링 함수 - 통합 메시지 시스템 적용
    """
    start_time = time.time()
    
    try:
        logging.info(f"Reddit 크롤링 시작: r/{subreddit_name} (범위: {start_index}-{end_index})")

        # 초기화 메시지
        if websocket:
            await websocket.send_json(create_progress_message(
                progress=5,
                step=CrawlStep.INITIALIZING,
                site=SiteType.REDDIT,
                board=subreddit_name,
                details={"sort": sort, "time_filter": time_filter}
            ))

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

        # 연결 메시지
        if websocket:
            await websocket.send_json(create_progress_message(
                progress=15,
                step=CrawlStep.CONNECTING,
                site=SiteType.REDDIT,
                board=subreddit_name,
                details={"fetch_limit": fetch_limit, "time_filter": actual_time_filter}
            ))

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

        # 게시물 수집 시작
        if websocket:
            await websocket.send_json(create_collecting_message(
                progress=25,
                site=SiteType.REDDIT,
                board=subreddit_name,
                sort_method=sort,
                found_posts=0
            ))

        all_posts = list(posts_generator)
        logging.info(f"초기 수집: {len(all_posts)}개 from r/{subreddit_name}")

        if websocket:
            await websocket.send_json(create_progress_message(
                progress=45,
                step=CrawlStep.PROCESSING,
                site=SiteType.REDDIT,
                board=subreddit_name,
                details={"collected_posts": len(all_posts)}
            ))

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

        # 조건 기반 필터링
        if websocket:
            await websocket.send_json(create_filtering_message(
                progress=60,
                matched_posts=0,
                total_checked=0,
                site=SiteType.REDDIT,
                min_views=min_views,
                min_likes=min_likes,
                min_comments=min_comments
            ))

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

            # 주기적 진행률 업데이트
            if websocket and i % 50 == 0:
                await websocket.send_json(create_filtering_message(
                    progress=60 + int((i / len(all_posts)) * 15),
                    matched_posts=len(matched_posts),
                    total_checked=i + 1,
                    site=SiteType.REDDIT
                ))

        logging.info(f"조건 필터링 후: {len(matched_posts)}개 매칭됨")

        # 최종 범위 적용
        if not enforce_date_limit:
            final_posts = matched_posts[start_index-1:end_index] if len(matched_posts) >= start_index else []
        else:
            final_posts = matched_posts

        if websocket:
            await websocket.send_json(create_progress_message(
                progress=80,
                step=CrawlStep.PROCESSING,
                site=SiteType.REDDIT,
                board=subreddit_name,
                details={"final_posts": len(final_posts)}
            ))

        data = []
        total_posts = len(final_posts)

        if total_posts == 0:
            logging.warning("필터링 후 게시물이 없음")
            if websocket:
                await websocket.send_json(quick_error(
                    ErrorCode.NO_POSTS_FOUND,
                    SiteType.REDDIT,
                    f"r/{subreddit_name}에서 조건에 맞는 게시물이 없습니다"
                ))
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

                # 본문 내용 구성
                content_parts = []
                if score > 0:
                    content_parts.append(f"스코어: {score}")
                if num_comments > 0:
                    content_parts.append(f"댓글: {num_comments}")
                if flair:
                    content_parts.append(f"플레어: {flair}")
                content_parts.extend([f"작성자: {author}", f"작성일: {created_date}"])

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

                # 주기적 진행률 업데이트
                if websocket and idx % 5 == 0:
                    progress = 80 + int((idx / total_posts) * 15)
                    await websocket.send_json(create_progress_message(
                        progress=progress,
                        step=CrawlStep.PROCESSING,
                        site=SiteType.REDDIT,
                        board=subreddit_name,
                        details={"processed": idx, "total": total_posts}
                    ))

                time.sleep(0.1)

            except Exception as e:
                logging.error(f"게시물 처리 오류 {idx}: {e}")
                continue

        elapsed_time = time.time() - start_time
        logging.info(f"Reddit 크롤링 완료: {len(data)}개 게시물 ({start_index}-{start_index+len(data)-1}위)")

        # 완료 메시지
        if websocket:
            await websocket.send_json(create_complete_message(
                total_count=len(data),
                site=SiteType.REDDIT,
                board=subreddit_name,
                start_rank=start_index,
                end_rank=start_index + len(data) - 1,
                elapsed_time=elapsed_time,
                metadata={
                    "sort_method": sort,
                    "time_filter": time_filter,
                    "original_posts": len(all_posts),
                    "matched_posts": len(matched_posts),
                    "final_posts": len(data)
                }
            ))

        return data

    except Exception as e:
        logging.error(f"Reddit 크롤링 오류: {e}")
        if websocket:
            await websocket.send_json(quick_error(
                ErrorCode.CRAWLING_ERROR,
                SiteType.REDDIT,
                str(e)
            ))
        handle_reddit_errors(e, subreddit_name)
