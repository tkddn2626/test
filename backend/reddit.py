import time
import praw
import logging
import requests
from datetime import datetime
import os
import re
from typing import Tuple
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv()

# 로그 설정
logging.basicConfig(
    filename="log.txt",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# Reddit API 설정 - .env에서 로드
try:
    reddit = praw.Reddit(
        client_id=os.getenv("REDDIT_CLIENT_ID"),
        client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
        user_agent=os.getenv("REDDIT_USER_AGENT", "Community Crawler/1.0"),
    )
    # 연결 테스트
    reddit.user.me()
    logging.info("Reddit API 연결 성공")
except Exception as e:
    logging.error(f"Reddit API 연결 실패: {e}")
    print("⚠️  Reddit API 설정을 확인하세요. .env 파일에 올바른 API 키가 있는지 확인하세요.")
    # 기본 설정으로 fallback (제한된 기능)
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
        # 조회수 (댓글수로 대체)
        views = post.num_comments
        # 추천수 (스코어)
        likes = max(0, post.score)
        # 댓글수
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
    """
    DeepL API를 사용한 번역 함수

    Args:
        text: 번역할 텍스트
        target_lang: 목표 언어 (KO, EN, JA 등)

    Returns:
        번역된 텍스트 또는 오류 메시지
    """
    try:
        if not text or not text.strip():
            return ""

        deepl_api_key = os.getenv("DEEPL_API_KEY")
        if not deepl_api_key:
            logging.warning("DEEPL_API_KEY가 설정되지 않았습니다.")
            return "(번역 실패: API 키 없음)"

        # 텍스트 길이 제한 (DeepL 무료 계정: 5000자)
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

def filter_by_date_range(posts, start_date_str, end_date_str):
    """날짜 범위로 게시물 필터링"""
    if not start_date_str or not end_date_str:
        return posts

    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').replace(hour=23, minute=59, second=59)

        filtered_posts = []
        for post in posts:
            post_date = datetime.fromtimestamp(post.created_utc)
            if start_date <= post_date <= end_date:
                filtered_posts.append(post)

        logging.info(f"Date filtering: {len(posts)} -> {len(filtered_posts)} posts ({start_date_str} to {end_date_str})")
        return filtered_posts
    except Exception as e:
        logging.error(f"Date filtering error: {e}")
        return posts

def filter_by_metrics(posts, min_views=0, min_likes=0):
    """조회수와 추천수로 게시물 필터링"""
    if min_views <= 0 and min_likes <= 0:
        return posts

    filtered_posts = []
    for post in posts:
        views = post.num_comments  # 댓글 수를 조회수 대용으로 사용
        likes = max(0, post.score)  # 음수 점수 방지

        if views >= min_views and likes >= min_likes:
            filtered_posts.append(post)

    logging.info(f"Metrics filtering: {len(posts)} -> {len(filtered_posts)} posts (min_views: {min_views}, min_likes: {min_likes})")
    return filtered_posts

def filter_by_time_period(posts, time_filter):
    """시간 기간으로 게시물 필터링 (사용자 지정 시간 필터용)"""
    if time_filter == "all":
        return posts

    try:
        now = datetime.now()
        time_limits = {
            "hour": now.timestamp() - 3600,
            "day": now.timestamp() - 86400,
            "week": now.timestamp() - 604800,
            "month": now.timestamp() - 2592000,
            "year": now.timestamp() - 31536000
        }

        if time_filter in time_limits:
            limit_timestamp = time_limits[time_filter]
            filtered_posts = []
            for post in posts:
                if post.created_utc >= limit_timestamp:
                    filtered_posts.append(post)
            logging.info(f"Time filtering ({time_filter}): {len(posts)} -> {len(filtered_posts)} posts")
            return filtered_posts
    except Exception as e:
        logging.error(f"Time filtering error: {e}")

    return posts

def sort_posts(posts_data, sort_method):
    """게시물 정렬 함수 (Reddit은 API 레벨에서 정렬하므로 주로 호환성용)"""
    if not posts_data:
        return posts_data

    try:
        if sort_method == "popular":
            # 조회수(댓글수) 기준 내림차순 정렬
            return sorted(posts_data, key=lambda x: x.get('조회수', 0), reverse=True)
        elif sort_method == "recommend":
            # 추천수(스코어) 기준 내림차순 정렬
            return sorted(posts_data, key=lambda x: x.get('추천수', 0), reverse=True)
        elif sort_method == "recent":
            # 작성일 기준 내림차순 정렬 (최신순)
            return sorted(posts_data, key=lambda x: x.get('작성일', ''), reverse=True)
        else:
            # Reddit API 정렬 방식 (top, hot, new, best, rising)은 이미 API에서 처리됨
            return posts_data
    except Exception as e:
        logging.error(f"정렬 오류: {e}")
        return posts_data

def format_reddit_date(timestamp):
    """Reddit 타임스탬프를 보기 좋은 날짜 형식으로 변환"""
    try:
        dt = datetime.fromtimestamp(timestamp)
        return dt.strftime('%Y.%m.%d %H:%M')
    except Exception as e:
        logging.error(f"Date formatting error: {e}")
        return ""

def extract_post_id_from_url(url):
    """Reddit URL에서 게시물 ID 추출"""
    try:
        match = re.search(r'/comments/([a-zA-Z0-9]+)/', url)
        if match:
            return match.group(1)
        return ""
    except Exception as e:
        logging.error(f"Post ID extraction error: {e}")
        return ""

# 비동기 크롤링 함수 - DeepL 번역 적용 및 개선된 메타데이터
async def fetch_posts(subreddit_name, limit=50, sort='top', time_filter='day', websocket=None, 
                     cancel_event=None, min_views=0, min_likes=0, min_comments=0,
                     start_date=None, end_date=None, enforce_date_limit=False, 
                     start_index=1, end_index=20):
    """
    강화된 Reddit 게시물 크롤링 함수 - 정확한 범위 및 조건 기반 필터링 지원

    Args:
        subreddit_name: 서브레딧 이름
        limit: 가져올 게시물 수 (enforce_date_limit=True면 무시됨)
        sort: 정렬 방식 ('top', 'hot', 'new', 'rising', 'best')
        time_filter: 시간 필터 ('hour', 'day', 'week', 'month', 'year', 'all')
        websocket: WebSocket 연결 (진행률 전송용)
        cancel_event: 취소 이벤트
        min_views: 최소 조회수 (댓글 수로 대체)
        min_likes: 최소 추천수 (스코어)
        min_comments: 최소 댓글 수
        start_date: 시작 날짜 (YYYY-MM-DD)
        end_date: 종료 날짜 (YYYY-MM-DD)
        enforce_date_limit: 날짜 범위 내 전체 게시물 수집 여부
        start_index: 시작 순위
        end_index: 끝 순위
    """
    try:
        logging.info(f"Reddit 크롤링 시작: r/{subreddit_name} (범위: {start_index}-{end_index})")

        subreddit = reddit.subreddit(subreddit_name)

        # 🔥 날짜 필터링이 있는 경우 대량 수집
        if enforce_date_limit and start_date and end_date:
            fetch_limit = 2000  # Reddit API 제한 고려
            actual_time_filter = 'all'  # 전체 기간에서 검색
        else:
            # 🔥 일반 크롤링: 정확한 개수만 수집
            if min_views > 0 or min_likes > 0 or min_comments > 0:
                fetch_limit = end_index * 3  # 필터링 고려한 여유분
            else:
                fetch_limit = end_index + 10  # 약간의 여유만
            actual_time_filter = time_filter

        # 진행률 업데이트
        if websocket:
            await websocket.send_json({
                "status": f"🔍 Reddit API 호출 중... (목표: {start_index}-{end_index}위)",
                "progress": 20
            })

        # 🚀 Reddit 자체 정렬 시스템 활용
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

        # 게시물을 리스트로 변환
        all_posts = list(posts_generator)
        logging.info(f"초기 수집: {len(all_posts)}개 from r/{subreddit_name}")

        if websocket:
            await websocket.send_json({
                "status": f"📦 {len(all_posts)}개 게시물 수집 완료, 조건 기반 필터링 중...",
                "progress": 40
            })

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

        # 게시물 처리 및 조건 검사
        for post in all_posts:
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

            # WebSocket 업데이트
            if websocket:
                try:
                    progress = 40 + int((len(matched_posts) / max(target_count, 1)) * 30)
                    await websocket.send_json({
                        "progress": progress,
                        "status": f"조건 만족 게시물: {len(matched_posts)}개, 연속 실패: {consecutive_fails}"
                    })
                except:
                    pass

        logging.info(f"조건 필터링 후: {len(matched_posts)}개 매칭됨")

        # 🔥 최종 범위 자르기
        if not enforce_date_limit:
            final_posts = matched_posts[start_index-1:end_index] if len(matched_posts) >= start_index else []
        else:
            final_posts = matched_posts

        if websocket:
            await websocket.send_json({
                "status": f"✅ 최종 {len(final_posts)}개 게시물 처리 시작",
                "progress": 70
            })

        data = []
        total_posts = len(final_posts)

        if total_posts == 0:
            logging.warning("필터링 후 게시물이 없음")
            return []

        # 메타데이터 보강 및 데이터 구성
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

                # 날짜 포맷팅 개선
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

                # 게시물 ID 추출
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

                # 원문 URL과 Reddit URL 구분
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

                # WebSocket 진행률 업데이트
                if websocket:
                    try:
                        progress = 70 + int((idx / total_posts) * 25)
                        await websocket.send_json({
                            "progress": progress,
                            "status": f"게시물 처리 중... ({idx}/{total_posts})"
                        })
                    except:
                        pass

                # API 호출 간격 조정
                time.sleep(0.1)

            except Exception as e:
                logging.error(f"게시물 처리 오류 {idx}: {e}")
                continue

        logging.info(f"Reddit 크롤링 완료: {len(data)}개 게시물 ({start_index}-{start_index+len(data)-1}위)")

        # 🔥 최종 정렬 적용
        if len(data) > 1:
            if sort == 'top' and min_likes > 0:
                data.sort(key=lambda x: x.get('추천수', 0), reverse=True)
            elif sort == 'hot' and min_views > 0:
                data.sort(key=lambda x: x.get('댓글수', 0), reverse=True)

        # 로깅 통계
        logging.info(f"조건 통계 - 전체: {len(all_posts)}, 조건만족: {len(matched_posts)}, 최종: {len(data)}")
        if len(all_posts) > 0:
            efficiency = (len(matched_posts) / len(all_posts) * 100)
            logging.info(f"필터링 효율: {efficiency:.1f}%")

        return data

    except Exception as e:
        logging.error(f"Reddit 크롤링 오류: {e}")
        handle_reddit_errors(e, subreddit_name)
