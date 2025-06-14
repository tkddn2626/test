import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime, timedelta
from urllib.parse import urljoin, urlparse, quote
import logging
from typing import List, Dict, Optional, Tuple, Union
import time
from dataclasses import dataclass
import asyncio
from collections import Counter
import concurrent.futures
from functools import lru_cache
import hashlib
import json
import threading
from urllib.robotparser import RobotFileParser
import mimetypes
from pathlib import Path

try:
    import xml.etree.ElementTree as ET
except ImportError:
    print("⚠️ xml.etree.ElementTree 모듈이 필요합니다")

try:
    from dateutil import parser as date_parser
except ImportError:
    print("💡 python-dateutil 설치 권장: pip install python-dateutil")
    date_parser = None

# ================================
# 🔥 설정 상수들
# ================================

DEFAULT_TIMEOUT = 15
MAX_PAGES = 20
MAX_POSTS_PER_PAGE = 100
MAX_RETRIES = 3
REQUEST_DELAY = 1.0

# 로깅 설정
if not logging.getLogger(__name__).handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
logger = logging.getLogger(__name__)

COMMON_EXCLUDE_PATTERNS = [
    r'\.js$', r'\.css$', r'\.jpg$', r'\.png$', r'\.gif$',
    r'\.pdf$', r'\.zip$', r'\.exe$', r'\.mp4$', r'\.mp3$'
]

# 사이트별 특화 설정
SITE_CONFIGS = {
    'default': {
        'delay': 1.0,
        'timeout': 15,
        'max_pages': 20,
        'respect_robots': True,
        'user_agent_rotation': True
    },
    'forum': {
        'delay': 0.8,
        'timeout': 20,
        'max_pages': 30,
        'respect_robots': True
    },
    'news': {
        'delay': 0.5,
        'timeout': 25,
        'max_pages': 50,
        'api_first': False
    }
}

# User-Agent 로테이션
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0'
]

# 제외할 파일 확장자
EXCLUDE_EXTENSIONS = {
    '.js', '.css', '.jpg', '.jpeg', '.png', '.gif', '.svg', '.ico',
    '.pdf', '.zip', '.exe', '.dmg', '.mp4', '.mp3', '.wav', '.avi'
}

# 에러 메시지 템플릿
ERROR_TEMPLATES = {
    'connection': "🌐 연결 오류: 웹사이트에 접근할 수 없습니다",
    'timeout': "⏰ 시간 초과: 응답이 너무 느립니다",
    'forbidden': "🚫 접근 금지: 로그인이 필요하거나 차단되었습니다",
    'not_found': "❓ 페이지 없음: URL을 확인해주세요",
    'server_error': "🔧 서버 오류: 사이트에 일시적 문제가 있습니다",
    'parsing_error': "📄 파싱 오류: 페이지 구조를 분석할 수 없습니다",
    'no_content': "📭 콘텐츠 없음: 게시물을 찾을 수 없습니다",
    'rate_limit': "🚦 속도 제한: 너무 빠른 요청으로 제한되었습니다"
}

# ================================
# 🔥 향상된 기능 함수들 (이전 stub에서 완전 구현으로)
# ================================

def _extract_enhanced_views(crawler, element, template):
    """향상된 조회수 추출"""
    try:
        # 기본 선택자로 시도
        views_text = crawler.extract_with_selectors(element, template.view_selectors)
        if views_text:
            # 숫자 추출 및 한국어 단위 처리
            views = _parse_korean_number(views_text)
            if views > 0:
                return views
        
        # 대안 선택자들 시도
        alt_selectors = [
            '[class*="view"]', '[class*="hit"]', '[class*="read"]',
            '.count', '.num', '[title*="조회"]', '[title*="view"]'
        ]
        
        for selector in alt_selectors:
            alt_element = element.select_one(selector)
            if alt_element:
                alt_text = alt_element.get_text(strip=True)
                views = _parse_korean_number(alt_text)
                if views > 0:
                    return views
        
        return 0
        
    except Exception as e:
        logger.debug(f"조회수 추출 오류: {e}")
        return 0

def _extract_enhanced_likes(crawler, element, template):
    """향상된 추천수 추출"""
    try:
        # 기본 선택자로 시도
        likes_text = crawler.extract_with_selectors(element, template.like_selectors)
        if likes_text:
            likes = _parse_korean_number(likes_text)
            if likes > 0:
                return likes
        
        # 대안 선택자들 시도
        alt_selectors = [
            '[class*="like"]', '[class*="recommend"]', '[class*="thumb"]',
            '.vote', '.score', '[title*="추천"]', '[title*="like"]'
        ]
        
        for selector in alt_selectors:
            alt_element = element.select_one(selector)
            if alt_element:
                alt_text = alt_element.get_text(strip=True)
                likes = _parse_korean_number(alt_text)
                if likes > 0:
                    return likes
        
        return 0
        
    except Exception as e:
        logger.debug(f"추천수 추출 오류: {e}")
        return 0

def _extract_enhanced_comments(crawler, element, template):
    """향상된 댓글수 추출"""
    try:
        # 기본 선택자로 시도
        comments_text = crawler.extract_with_selectors(element, template.comment_selectors)
        if comments_text:
            comments = _parse_korean_number(comments_text)
            if comments > 0:
                return comments
        
        # 대안 선택자들 시도
        alt_selectors = [
            '[class*="comment"]', '[class*="reply"]', '[class*="response"]',
            '.count', '[title*="댓글"]', '[title*="comment"]'
        ]
        
        for selector in alt_selectors:
            alt_element = element.select_one(selector)
            if alt_element:
                alt_text = alt_element.get_text(strip=True)
                comments = _parse_korean_number(alt_text)
                if comments > 0:
                    return comments
        
        return 0
        
    except Exception as e:
        logger.debug(f"댓글수 추출 오류: {e}")
        return 0

def _parse_korean_number(text: str) -> int:
    """한국어 숫자 표현 파싱 (만, 천 등)"""
    if not text:
        return 0
    
    try:
        # 쉼표 제거
        text = text.replace(',', '')
        
        # 순수 숫자 추출
        numbers = re.findall(r'[\d.]+', text)
        if not numbers:
            return 0
        
        number_str = numbers[0]
        base_number = float(number_str)
        
        # 한국어 단위 처리
        if '만' in text:
            return int(base_number * 10000)
        elif '천' in text:
            return int(base_number * 1000)
        elif 'k' in text.lower() or 'K' in text:
            return int(base_number * 1000)
        elif 'm' in text.lower() or 'M' in text:
            return int(base_number * 1000000)
        else:
            return int(base_number)
    
    except Exception:
        return 0

def _is_valid_universal_post(crawler, element, template):
    """범용 게시물 유효성 검사"""
    try:
        # 제목 추출 및 검증
        title = crawler.extract_with_selectors(element, template.title_selectors)
        if not title or len(title.strip()) < 3:
            return False
        
        # UI 요소 필터링
        if crawler.content_filter.is_ui_element(title, element):
            return False
        
        # 게시물 구조 확인
        element_text = element.get_text(strip=True)
        if len(element_text) < 10:
            return False
        
        # 링크 존재 여부 (선택적)
        has_link = bool(element.find('a', href=True))
        
        # 점수 기반 판정
        score = crawler.content_filter.calculate_post_score(title, element_text, element)
        
        return score >= 3 or has_link
        
    except Exception as e:
        logger.debug(f"게시물 유효성 검사 오류: {e}")
        return False

def _generate_post_id(crawler, link, title, date=None):
    """게시물 고유 ID 생성"""
    try:
        # 링크 기반 ID 생성 우선
        if link and link.startswith('http'):
            base = link
        else:
            # 제목 + 날짜 기반 ID 생성
            base = f"{title}_{date}" if date else title
        
        # MD5 해시 생성
        return hashlib.md5(base.encode('utf-8')).hexdigest()[:12]
        
    except Exception:
        # 실패시 타임스탬프 기반 ID
        return f"post_{int(time.time())}"

# ================================
# 🔥 핵심 크롤링 함수들 완전 구현
# ================================

async def _crawl_single_page_with_conditions(crawler, current_url, template=None, condition_checker=None, websocket=None):
    """단일 페이지 조건부 크롤링 - 완전 구현"""
    try:
        logger.info(f"단일 페이지 크롤링 시작: {current_url}")
        
        # HTTP 요청
        response = crawler.session.get(current_url, timeout=15)
        response.raise_for_status()
        
        # HTML 파싱
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 템플릿이 없으면 자동 생성
        if not template:
            template, _ = crawler.detect_site_structure(current_url, soup)
        
        # 게시물 추출
        posts = await _extract_posts_from_page_with_validation(
            crawler, soup, template, current_url, condition_checker
        )
        
        logger.info(f"단일 페이지에서 {len(posts)}개 게시물 추출")
        return posts
        
    except Exception as e:
        logger.error(f"단일 페이지 크롤링 오류: {e}")
        return []

async def _extract_posts_from_page_with_validation(crawler, soup, template, page_url, condition_checker=None):
    """페이지에서 게시물 추출 및 검증 - 완전 구현"""
    try:
        # 의미있는 게시물 요소 추출
        post_elements = crawler.extract_meaningful_posts(soup, template)
        validated_posts = []
        
        logger.info(f"페이지에서 {len(post_elements)}개 게시물 요소 발견")
        
        for idx, element in enumerate(post_elements):
            try:
                # 향상된 게시물 데이터 추출
                post_data = await _extract_enhanced_universal_post_data(
                    crawler, element, template, page_url
                )
                
                if not post_data:
                    continue
                
                # 기본 유효성 검사
                if not _is_valid_universal_post(crawler, element, template):
                    continue
                
                # 조건 검사 (있는 경우)
                if condition_checker:
                    is_valid, reason = condition_checker.check_post_conditions(post_data)
                    if not is_valid:
                        logger.debug(f"조건 불만족: {reason}")
                        continue
                
                # 번호 할당
                post_data['번호'] = len(validated_posts) + 1
                validated_posts.append(post_data)
                
            except Exception as e:
                logger.debug(f"게시물 {idx} 추출 중 오류: {e}")
                continue
        
        logger.info(f"검증 완료: {len(validated_posts)}개 유효한 게시물")
        return validated_posts
        
    except Exception as e:
        logger.error(f"페이지 게시물 추출 오류: {e}")
        return []

async def _extract_enhanced_universal_post_data(crawler, element, template, page_url):
    """향상된 범용 게시물 데이터 추출 - 완전 구현"""
    try:
        # 기본 정보 추출
        title = crawler.extract_with_selectors(element, template.title_selectors)
        if not title or len(title.strip()) < 3:
            return None
        
        # 링크 추출 및 정규화
        link = crawler.extract_with_selectors(element, template.link_selectors, "href")
        if link and not link.startswith('http'):
            link = urljoin(page_url, link)
        
        # 향상된 메트릭 추출
        views = _extract_enhanced_views(crawler, element, template)
        likes = _extract_enhanced_likes(crawler, element, template)
        comments = _extract_enhanced_comments(crawler, element, template)
        
        # 날짜 추출 및 정규화
        date_text = crawler.extract_with_selectors(element, template.date_selectors)
        normalized_date = crawler.normalize_date(date_text)
        
        # 작성자 추출
        author = crawler.extract_with_selectors(element, template.author_selectors) or "익명"
        
        # 썸네일 추출
        thumbnail = crawler.extract_thumbnail(element, page_url, template.thumbnail_selectors)
        
        # 본문 미리보기 추출
        content_preview = _extract_content_preview(element)
        
        # 콘텐츠 분류
        classification = crawler.content_classifier.classify_content(title, content_preview)
        
        # 메타데이터 생성
        domain = urlparse(page_url).netloc
        post_id = _generate_post_id(crawler, link, title, normalized_date)
        
        return {
            "원제목": title,
            "번역제목": None,
            "링크": link or page_url,
            "원문URL": link or page_url,
            "썸네일 URL": thumbnail,
            "본문": content_preview,
            "조회수": views,
            "추천수": likes,
            "댓글수": comments,
            "작성일": normalized_date,
            "작성자": author,
            "사이트": domain,
            "게시물ID": post_id,
            "콘텐츠타입": classification.type,
            "분류신뢰도": classification.confidence,
            "키워드": classification.keywords,
            "감정": classification.sentiment,
            "크롤링방식": "Universal-Enhanced"
        }
        
    except Exception as e:
        logger.debug(f"게시물 데이터 추출 오류: {e}")
        return None

def _extract_content_preview(element, max_length=200):
    """게시물 본문 미리보기 추출"""
    try:
        # 본문 관련 요소들 찾기
        content_selectors = [
            '.content', '.body', '.text', '.description',
            '[class*="content"]', '[class*="body"]', 'p'
        ]
        
        content_text = ""
        
        for selector in content_selectors:
            content_elem = element.select_one(selector)
            if content_elem:
                content_text = content_elem.get_text(strip=True)
                if len(content_text) > 20:
                    break
        
        # 내용이 없으면 전체 텍스트에서 추출
        if not content_text:
            all_text = element.get_text(strip=True)
            # 제목 제거 시도
            lines = all_text.split('\n')
            if len(lines) > 1:
                content_text = '\n'.join(lines[1:])
            else:
                content_text = all_text
        
        # 길이 제한 적용
        if len(content_text) > max_length:
            content_text = content_text[:max_length] + "..."
        
        return content_text or None
        
    except Exception:
        return None

async def _crawl_multiple_pages_with_conditions(crawler, initial_url, template, condition_checker, max_pages, site_type, websocket=None):
    """조건 기반 다중 페이지 크롤링 - 완전 구현"""
    all_posts = []
    current_url = initial_url
    page_count = 0
    consecutive_fails = 0
    max_consecutive_fails = 5 if site_type == "spa" else 3
    
    logger.info(f"다중 페이지 크롤링 시작: {initial_url} (최대 {max_pages}페이지)")
    
    while current_url and page_count < max_pages:
        try:
            page_count += 1
            logger.info(f"페이지 {page_count}/{max_pages} 크롤링: {current_url}")
            
            # 진행상황 보고
            if websocket:
                progress = 30 + (page_count / max_pages) * 40
                await websocket.send_json({
                    "progress": progress,
                    "status": f"📄 페이지 {page_count}/{max_pages} 크롤링 중",
                    "details": f"현재까지 {len(all_posts)}개 수집",
                    "current_page": page_count,
                    "total_pages": max_pages
                })
            
            # 페이지 요청
            response = crawler.session.get(current_url, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 해당 페이지에서 게시물 추출
            page_posts = await _extract_posts_from_page_with_validation(
                crawler, soup, template, current_url, condition_checker
            )
            
            if not page_posts:
                consecutive_fails += 1
                logger.warning(f"페이지 {page_count}에서 게시물을 찾지 못함 (연속 실패: {consecutive_fails})")
                
                # 연속 실패 임계값 도달시 중단
                if consecutive_fails >= max_consecutive_fails:
                    logger.info(f"연속 {max_consecutive_fails}페이지 실패로 크롤링 중단")
                    break
            else:
                consecutive_fails = 0  # 성공시 카운터 리셋
                all_posts.extend(page_posts)
                logger.info(f"페이지 {page_count}에서 {len(page_posts)}개 게시물 수집")
                
                # 충분한 게시물 확보시 조기 종료
                if len(all_posts) >= max_pages * 15:  # 페이지당 평균 15개 기준
                    logger.info("충분한 게시물 확보로 조기 종료")
                    break
            
            # 날짜 기반 조기 종료 확인
            if condition_checker and condition_checker.start_dt and page_posts:
                oldest_date = _get_oldest_post_date(page_posts, crawler)
                if oldest_date and oldest_date < condition_checker.start_dt:
                    logger.info(f"날짜 범위 초과로 크롤링 중단: {oldest_date} < {condition_checker.start_dt}")
                    break
            
            # 다음 페이지 URL 찾기
            next_url = crawler.pagination_handler.find_next_page_url(soup, current_url)
            if not next_url or next_url == current_url:
                logger.info("다음 페이지가 없어 크롤링 종료")
                break
            
            current_url = next_url
            
            # 서버 부하 고려 딜레이
            await asyncio.sleep(REQUEST_DELAY)
            
        except requests.exceptions.RequestException as e:
            logger.error(f"페이지 {page_count} 요청 오류: {e}")
            consecutive_fails += 1
            if consecutive_fails >= max_consecutive_fails:
                break
        except Exception as e:
            logger.error(f"페이지 {page_count} 처리 오류: {e}")
            consecutive_fails += 1
            if consecutive_fails >= max_consecutive_fails:
                break
    
    logger.info(f"다중 페이지 크롤링 완료: 총 {page_count}페이지, {len(all_posts)}개 게시물")
    return all_posts

def _get_oldest_post_date(posts, crawler):
    """게시물 목록에서 가장 오래된 날짜 추출"""
    try:
        dates = []
        for post in posts:
            date_str = post.get('작성일', '')
            if date_str:
                post_date = crawler.parse_post_date(date_str)
                if post_date:
                    dates.append(post_date)
        
        return min(dates) if dates else None
        
    except Exception as e:
        logger.debug(f"날짜 추출 오류: {e}")
        return None

# ================================
# 🔥 RSS/API 자동 발견 함수들 구현
# ================================

async def _try_rss_auto_discovery(crawler, url):
    """RSS 피드 자동 발견 및 크롤링"""
    try:
        logger.info("RSS 피드 자동 발견 시도")
        
        # 일반적인 RSS URL 패턴들
        rss_patterns = [
            "/rss", "/rss.xml", "/feed", "/feed.xml", "/feeds/all.atom.xml",
            "/atom.xml", "/index.xml", "/.rss", "/rss/", "/feeds/"
        ]
        
        base_url = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
        
        for pattern in rss_patterns:
            try:
                rss_url = base_url + pattern
                response = crawler.session.get(rss_url, timeout=10)
                
                if response.status_code == 200 and ('xml' in response.headers.get('content-type', '') or 
                                                   'rss' in response.text.lower()[:200]):
                    
                    posts = _parse_rss_feed(response.text, rss_url)
                    if posts:
                        logger.info(f"RSS 피드에서 {len(posts)}개 게시물 발견: {rss_url}")
                        return posts
                        
            except Exception as e:
                logger.debug(f"RSS URL {pattern} 시도 실패: {e}")
                continue
        
        # HTML에서 RSS 링크 찾기
        try:
            response = crawler.session.get(url, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            rss_links = soup.find_all('link', {'type': ['application/rss+xml', 'application/atom+xml']})
            for link in rss_links:
                href = link.get('href')
                if href:
                    if not href.startswith('http'):
                        href = urljoin(url, href)
                    
                    rss_response = crawler.session.get(href, timeout=10)
                    posts = _parse_rss_feed(rss_response.text, href)
                    if posts:
                        logger.info(f"HTML 링크 RSS에서 {len(posts)}개 게시물 발견")
                        return posts
        
        except Exception as e:
            logger.debug(f"HTML RSS 링크 파싱 오류: {e}")
        
        return None
        
    except Exception as e:
        logger.debug(f"RSS 자동 발견 오류: {e}")
        return None

def _parse_rss_feed(xml_content, feed_url):
    """RSS/Atom 피드 파싱"""
    try:
        root = ET.fromstring(xml_content)
        posts = []
        
        # RSS 2.0 형식
        if root.tag == 'rss':
            items = root.findall('.//item')
            for idx, item in enumerate(items[:20]):  # 최대 20개
                title = item.find('title')
                link = item.find('link')
                description = item.find('description')
                pubDate = item.find('pubDate')
                
                post = {
                    "번호": idx + 1,
                    "원제목": title.text if title is not None else f"RSS 게시물 {idx + 1}",
                    "번역제목": None,
                    "링크": link.text if link is not None else feed_url,
                    "원문URL": link.text if link is not None else feed_url,
                    "썸네일 URL": None,
                    "본문": description.text[:200] + "..." if description is not None and len(description.text) > 200 else description.text if description is not None else "",
                    "조회수": 0,
                    "추천수": 0,
                    "댓글수": 0,
                    "작성일": _parse_rss_date(pubDate.text if pubDate is not None else ""),
                    "작성자": "RSS",
                    "사이트": urlparse(feed_url).netloc,
                    "콘텐츠타입": "rss",
                    "분류신뢰도": 0.7,
                    "키워드": [],
                    "감정": "neutral",
                    "크롤링방식": "RSS"
                }
                posts.append(post)
        
        # Atom 형식
        elif 'atom' in root.tag:
            entries = root.findall('.//{http://www.w3.org/2005/Atom}entry')
            for idx, entry in enumerate(entries[:20]):
                title = entry.find('.//{http://www.w3.org/2005/Atom}title')
                link = entry.find('.//{http://www.w3.org/2005/Atom}link')
                summary = entry.find('.//{http://www.w3.org/2005/Atom}summary')
                updated = entry.find('.//{http://www.w3.org/2005/Atom}updated')
                
                href = link.get('href') if link is not None else feed_url
                
                post = {
                    "번호": idx + 1,
                    "원제목": title.text if title is not None else f"Atom 게시물 {idx + 1}",
                    "번역제목": None,
                    "링크": href,
                    "원문URL": href,
                    "썸네일 URL": None,
                    "본문": summary.text[:200] + "..." if summary is not None and len(summary.text) > 200 else summary.text if summary is not None else "",
                    "조회수": 0,
                    "추천수": 0,
                    "댓글수": 0,
                    "작성일": _parse_rss_date(updated.text if updated is not None else ""),
                    "작성자": "Atom",
                    "사이트": urlparse(feed_url).netloc,
                    "콘텐츠타입": "atom",
                    "분류신뢰도": 0.7,
                    "키워드": [],
                    "감정": "neutral",
                    "크롤링방식": "Atom"
                }
                posts.append(post)
        
        return posts
        
    except Exception as e:
        logger.debug(f"RSS 피드 파싱 오류: {e}")
        return []

def _parse_rss_date(date_str):
    """RSS 날짜 형식 파싱"""
    try:
        if not date_str:
            return datetime.now().strftime('%Y.%m.%d %H:%M')
        
        # RFC 2822 형식 (RSS 2.0)
        if '+' in date_str or 'GMT' in date_str:
            dt = datetime.strptime(date_str.split('+')[0].split('GMT')[0].strip(), '%a, %d %b %Y %H:%M:%S')
            return dt.strftime('%Y.%m.%d %H:%M')
        
        # ISO 8601 형식 (Atom)
        if 'T' in date_str:
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00').split('+')[0].split('-')[0])
            return dt.strftime('%Y.%m.%d %H:%M')
        
        return date_str
        
    except Exception:
        return datetime.now().strftime('%Y.%m.%d %H:%M')

async def _try_api_auto_discovery(crawler, url):
    """API 엔드포인트 자동 발견"""
    try:
        logger.info("API 엔드포인트 자동 발견 시도")
        
        # 일반적인 API 패턴들
        api_patterns = [
            "/api/posts", "/api/articles", "/api/feed", "/api/content",
            "/wp-json/wp/v2/posts", "/api/v1/posts", "/api/v2/posts"
        ]
        
        base_url = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
        
        for pattern in api_patterns:
            try:
                api_url = base_url + pattern
                response = crawler.session.get(api_url, timeout=10)
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        if isinstance(data, list) and data:
                            posts = _parse_api_response(data, api_url)
                            if posts:
                                logger.info(f"API에서 {len(posts)}개 게시물 발견: {api_url}")
                                return posts
                    except json.JSONDecodeError:
                        continue
                        
            except Exception as e:
                logger.debug(f"API URL {pattern} 시도 실패: {e}")
                continue
        
        return None
        
    except Exception as e:
        logger.debug(f"API 자동 발견 오류: {e}")
        return None

def _parse_api_response(data, api_url):
    """API 응답 파싱"""
    try:
        posts = []
        
        for idx, item in enumerate(data[:20]):  # 최대 20개
            if not isinstance(item, dict):
                continue
            
            # 일반적인 필드명들 시도
            title = (item.get('title') or item.get('subject') or 
                    item.get('name') or f"API 게시물 {idx + 1}")
            
            if isinstance(title, dict):
                title = title.get('rendered', title.get('value', str(title)))
            
            link = (item.get('link') or item.get('url') or 
                   item.get('permalink') or api_url)
            
            content = item.get('content', item.get('excerpt', item.get('summary', '')))
            if isinstance(content, dict):
                content = content.get('rendered', content.get('value', str(content)))
            
            date_field = (item.get('date') or item.get('created_at') or 
                         item.get('published') or item.get('updated'))
            
            post = {
                "번호": idx + 1,
                "원제목": str(title)[:200],
                "번역제목": None,
                "링크": str(link),
                "원문URL": str(link),
                "썸네일 URL": item.get('thumbnail', item.get('image')),
                "본문": str(content)[:200] + "..." if len(str(content)) > 200 else str(content),
                "조회수": item.get('views', item.get('view_count', 0)),
                "추천수": item.get('likes', item.get('like_count', 0)),
                "댓글수": item.get('comments', item.get('comment_count', 0)),
                "작성일": _parse_api_date(date_field),
                "작성자": str(item.get('author', item.get('writer', 'API'))),
                "사이트": urlparse(api_url).netloc,
                "콘텐츠타입": "api",
                "분류신뢰도": 0.8,
                "키워드": [],
                "감정": "neutral",
                "크롤링방식": "API"
            }
            posts.append(post)
        
        return posts
        
    except Exception as e:
        logger.debug(f"API 응답 파싱 오류: {e}")
        return []

def _parse_api_date(date_field):
    """API 날짜 필드 파싱"""
    try:
        if not date_field:
            return datetime.now().strftime('%Y.%m.%d %H:%M')
        
        if isinstance(date_field, str):
            # ISO 형식 시도
            if 'T' in date_field:
                dt = datetime.fromisoformat(date_field.replace('Z', '+00:00').split('+')[0])
                return dt.strftime('%Y.%m.%d %H:%M')
        
        return str(date_field)
        
    except Exception:
        return datetime.now().strftime('%Y.%m.%d %H:%M')

async def _try_mobile_version(crawler, url):
    """모바일 버전 시도"""
    try:
        logger.info("모바일 버전 크롤링 시도")
        
        parsed_url = urlparse(url)
        domain = parsed_url.netloc
        
        # 모바일 도메인 패턴들
        mobile_patterns = [
            f"m.{domain}",
            f"mobile.{domain}",
            domain.replace('www.', 'm.', 1) if domain.startswith('www.') else f"m.{domain}"
        ]
        
        for mobile_domain in mobile_patterns:
            try:
                mobile_url = f"{parsed_url.scheme}://{mobile_domain}{parsed_url.path}"
                
                # 모바일 User-Agent 사용
                headers = {
                    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_7_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Mobile/15E148 Safari/604.1'
                }
                
                response = crawler.session.get(mobile_url, headers=headers, timeout=10)
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # 간단한 템플릿으로 추출 시도
                    mobile_template, _ = crawler.detect_site_structure(mobile_url, soup)
                    posts = await _extract_posts_from_page_with_validation(
                        crawler, soup, mobile_template, mobile_url, None
                    )
                    
                    if posts:
                        logger.info(f"모바일 버전에서 {len(posts)}개 게시물 발견")
                        return posts
                        
            except Exception as e:
                logger.debug(f"모바일 도메인 {mobile_domain} 시도 실패: {e}")
                continue
        
        return None
        
    except Exception as e:
        logger.debug(f"모바일 버전 시도 오류: {e}")
        return None

# ================================
# 🔥 범용 크롤러 조건 검사기
# ================================

class UniversalConditionChecker:
    
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
    
    def check_post_conditions(self, post: dict) -> Tuple[bool, str]:
        """범용 게시물 조건 검사"""
        views = post.get('조회수', 0)
        likes = post.get('추천수', 0)
        comments = post.get('댓글수', 0)
        
        if views < self.min_views:
            return False, f"조회수 부족: {views} < {self.min_views}"
        if likes < self.min_likes:
            return False, f"추천수 부족: {likes} < {self.min_likes}"
        if comments < self.min_comments:
            return False, f"댓글수 부족: {comments} < {self.min_comments}"
        
        # 날짜 검사 (다양한 형식 지원)
        if self.start_dt and self.end_dt:
            post_date = self._extract_universal_post_date(post)
            if post_date:
                if not (self.start_dt <= post_date <= self.end_dt):
                    return False, f"날짜 범위 벗어남"
        
        return True, "조건 만족"
    
    def _extract_universal_post_date(self, post: dict) -> Optional[datetime]:
        """범용 날짜 추출 (다양한 형식 지원)"""
        date_str = post.get('작성일', '')
        if not date_str:
            return None
        
        # 기존 UniversalCrawler의 parse_post_date 메서드 활용
        crawler = UniversalCrawler()
        return crawler.parse_post_date(date_str)
    
    def should_stop_crawling(self, consecutive_fails: int, has_date_filter: bool, 
                           site_type: str = "general") -> Tuple[bool, str]:
        """크롤링 중단 여부 판단 (사이트 타입별 최적화)"""
        
        # 사이트 타입별 임계값 조정
        if site_type == "spa":  # SPA 사이트는 더 관대하게
            fail_threshold = 5 if has_date_filter else 10
        elif site_type == "forum":  # 포럼은 중간 정도
            fail_threshold = 15 if has_date_filter else 30
        else:  # 일반 사이트
            fail_threshold = 10 if has_date_filter else 20
        
        if consecutive_fails >= fail_threshold:
            return True, "조건 불만족으로 중단"
        
        return False, "계속 진행"

# ================================
# 🔥 데이터 클래스들
# ================================

@dataclass
class CrawlProgress:
    """크롤링 진행 상태"""
    progress: int
    status: str
    details: str
    found_posts: int = 0
    current_page: int = 1
    total_pages: int = 1
    errors: List[str] = None

@dataclass
class ContentClassification:
    """콘텐츠 분류 결과"""
    type: str  # news, discussion, question, review, announcement, etc.
    confidence: float  # 0.0 ~ 1.0
    keywords: List[str]
    sentiment: str  # positive, negative, neutral

@dataclass
class SiteTemplate:
    """사이트별 HTML 구조 템플릿"""
    name: str
    post_selectors: List[str]
    title_selectors: List[str]
    link_selectors: List[str]
    view_selectors: List[str]
    like_selectors: List[str]
    comment_selectors: List[str]  # 추가됨
    date_selectors: List[str]
    author_selectors: List[str]
    thumbnail_selectors: List[str]
    exclude_selectors: List[str]
    pagination_selectors: List[str] = None

# ================================
# 🔥 핵심 클래스들 (기존 유지하되 일부 메서드 수정)
# ================================

class SmartContentClassifier:
    """스마트 콘텐츠 분류기"""
    
    def __init__(self):
        self.content_patterns = {
            'question': {
                'keywords': ['what', 'how', 'why', 'when', 'where', 'who', 'which', 'can', 'should', 'would',
                           '무엇', '어떻게', '왜', '언제', '어디', '누구', '어느', '할 수', '해야', '하면'],
                'patterns': [r'\?$', r'^(what|how|why|when|where|who|which)\b', r'\b(질문|문의|궁금)\b'],
                'weight': 1.0
            },
            'discussion': {
                'keywords': ['discussion', 'debate', 'opinion', 'thoughts', 'views', 'community',
                           '토론', '논의', '의견', '생각', '견해', '커뮤니티'],
                'patterns': [r'\b(discuss|debate|opinion|thoughts)\b', r'\b(토론|논의|의견)\b'],
                'weight': 0.8
            },
            'news': {
                'keywords': ['breaking', 'news', 'report', 'announce', 'official', 'update',
                           '속보', '뉴스', '보도', '발표', '공식', '업데이트'],
                'patterns': [r'\b(breaking|news|report|announced?)\b', r'\b(속보|뉴스|발표)\b'],
                'weight': 0.9
            },
            'review': {
                'keywords': ['review', 'rating', 'opinion', 'experience', 'recommend',
                           '리뷰', '평점', '후기', '경험', '추천'],
                'patterns': [r'\b(review|rating|stars?)\b', r'\b(리뷰|후기|평점)\b'],
                'weight': 0.8
            },
            'tutorial': {
                'keywords': ['guide', 'tutorial', 'how-to', 'tips', 'help', 'manual',
                           '가이드', '튜토리얼', '방법', '팁', '도움말', '매뉴얼'],
                'patterns': [r'\b(guide|tutorial|how.?to|tips)\b', r'\b(가이드|튜토리얼|방법)\b'],
                'weight': 0.7
            },
            'announcement': {
                'keywords': ['announcement', 'notice', 'important', 'alert', 'warning',
                           '공지', '알림', '중요', '경고', '안내'],
                'patterns': [r'\b(announcement|notice|important|alert)\b', r'\b(공지|알림|중요)\b'],
                'weight': 0.9
            }
        }
        
        self.sentiment_keywords = {
            'positive': ['good', 'great', 'excellent', 'amazing', 'wonderful', 'love', 'best',
                        '좋은', '훌륭한', '대단한', '놀라운', '좋아', '최고'],
            'negative': ['bad', 'terrible', 'awful', 'worst', 'hate', 'disappointing',
                        '나쁜', '끔찍한', '최악', '싫어', '실망'],
            'neutral': ['okay', 'fine', 'normal', 'average', '괜찮은', '보통', '일반적인']
        }
    
    def classify_content(self, title: str, content: str = "") -> ContentClassification:
        """콘텐츠를 분류하고 메타데이터 추출"""
        try:
            text = (title + " " + content).lower()
            
            type_scores = {}
            matched_keywords = []
            
            for content_type, data in self.content_patterns.items():
                score = 0.0
                
                for keyword in data['keywords']:
                    if keyword.lower() in text:
                        score += 0.1
                        matched_keywords.append(keyword)
                
                for pattern in data['patterns']:
                    if re.search(pattern, text, re.IGNORECASE):
                        score += 0.3
                
                type_scores[content_type] = score * data['weight']
            
            if type_scores:
                best_type = max(type_scores.keys(), key=lambda k: type_scores[k])
                confidence = min(type_scores[best_type], 1.0)
            else:
                best_type = 'general'
                confidence = 0.5
            
            sentiment = self._analyze_sentiment(text)
            
            return ContentClassification(
                type=best_type,
                confidence=confidence,
                keywords=list(set(matched_keywords)),
                sentiment=sentiment
            )
            
        except Exception as e:
            logger.warning(f"콘텐츠 분류 오류: {e}")
            return ContentClassification(
                type='general',
                confidence=0.0,
                keywords=[],
                sentiment='neutral'
            )
    
    def _analyze_sentiment(self, text: str) -> str:
        """간단한 감정 분석"""
        sentiment_scores = {'positive': 0, 'negative': 0, 'neutral': 0}
        
        for sentiment, keywords in self.sentiment_keywords.items():
            for keyword in keywords:
                if keyword.lower() in text:
                    sentiment_scores[sentiment] += 1
        
        if sentiment_scores['positive'] > sentiment_scores['negative']:
            return 'positive'
        elif sentiment_scores['negative'] > sentiment_scores['positive']:
            return 'negative'
        else:
            return 'neutral'

class AdvancedSiteDetector:
    """고급 사이트 감지기"""
    
    def __init__(self):
        self.cache = {}
    
    def detect_site_characteristics(self, url: str, soup: BeautifulSoup) -> Dict[str, bool]:
        """사이트 특성 감지"""
        try:
            characteristics = {
                'is_spa': self._is_problematic_spa(soup),
                'requires_login': self._requires_login(soup),
                'has_infinite_scroll': self._has_infinite_scroll(soup),
                'is_dynamic': self._is_dynamic_content(soup),
                'has_pagination': self._has_pagination(soup),
                'is_mobile_optimized': self._is_mobile_optimized(soup),
                'has_content': self._has_meaningful_content(soup),
                'is_crawlable': self._is_crawlable(soup)
            }
            
            logger.info(f"사이트 특성: {characteristics}")
            return characteristics
            
        except Exception as e:
            logger.warning(f"사이트 특성 감지 실패: {e}")
            return {'is_crawlable': True}
    
    def _is_problematic_spa(self, soup: BeautifulSoup) -> bool:
        """문제가 되는 SPA인지 확인"""
        try:
            spa_indicators = [
                'data-reactroot', 'ng-app', 'v-app', '__NEXT_DATA__',
                'data-server-rendered', 'data-vue-meta'
            ]
            
            has_spa_framework = False
            for indicator in spa_indicators:
                if soup.find(attrs={indicator: True}) or soup.find(id=indicator):
                    has_spa_framework = True
                    break
            
            if not has_spa_framework:
                scripts = soup.find_all('script')
                for script in scripts:
                    script_text = script.get_text().lower()
                    if any(framework in script_text for framework in ['react', 'vue', 'angular', 'next']):
                        has_spa_framework = True
                        break
            
            if has_spa_framework:
                return not self._has_meaningful_content(soup)
            
            return False
            
        except Exception:
            return False
    
    def _has_meaningful_content(self, soup: BeautifulSoup) -> bool:
        """의미있는 콘텐츠가 있는지 확인"""
        try:
            text_content = soup.get_text(strip=True)
            if len(text_content) < 100:
                return False
            
            content_indicators = [
                'article', '.post', '.item', '.entry', '.card',
                '.content', '.main', '.thread', '.comment',
                'h1', 'h2', 'h3', 'p'
            ]
            
            meaningful_elements = 0
            for indicator in content_indicators:
                elements = soup.select(indicator)
                for element in elements:
                    element_text = element.get_text(strip=True)
                    if len(element_text) > 20:
                        meaningful_elements += 1
            
            return meaningful_elements >= 3
            
        except Exception:
            return True
    
    def _is_crawlable(self, soup: BeautifulSoup) -> bool:
        """크롤링 가능 여부 종합 판단"""
        try:
            if self._requires_login(soup):
                return False
            
            if self._has_meaningful_content(soup):
                return True
            
            if self._has_ssr_content(soup):
                return True
            
            return False
            
        except Exception:
            return True
    
    def _has_ssr_content(self, soup: BeautifulSoup) -> bool:
        """서버사이드 렌더링된 콘텐츠 확인"""
        try:
            ssr_indicators = [
                'data-server-rendered="true"',
                'data-ssr="true"',
                '__NEXT_DATA__',
                'window.__INITIAL_STATE__'
            ]
            
            page_html = str(soup)
            for indicator in ssr_indicators:
                if indicator in page_html:
                    return True
            
            main_content = soup.select_one('main, #main, .main, .content, #content')
            if main_content:
                content_text = main_content.get_text(strip=True)
                return len(content_text) > 200
            
            return False
            
        except Exception:
            return False
    
    def _requires_login(self, soup: BeautifulSoup) -> bool:
        """로그인 필요 여부 감지"""
        login_indicators = [
            'login', 'sign in', 'log in', 'authenticate', 'please log in',
            '로그인', '로그인이 필요', '인증이 필요'
        ]
        
        page_text = soup.get_text().lower()
        for indicator in login_indicators:
            if indicator in page_text:
                if soup.find('form') and soup.find(['input'], attrs={'type': 'password'}):
                    return True
        
        return False
    
    def _has_infinite_scroll(self, soup: BeautifulSoup) -> bool:
        """무한 스크롤 감지"""
        infinite_scroll_indicators = [
            'infinite-scroll', 'lazy-load', 'scroll-load', 'pagination-infinite'
        ]
        
        for indicator in infinite_scroll_indicators:
            if soup.find(class_=re.compile(indicator, re.I)) or soup.find(id=re.compile(indicator, re.I)):
                return True
        
        return False
    
    def _is_dynamic_content(self, soup: BeautifulSoup) -> bool:
        """동적 콘텐츠 로딩 감지"""
        dynamic_indicators = [
            'loading', 'spinner', 'skeleton', 'placeholder'
        ]
        
        for indicator in dynamic_indicators:
            if soup.find(class_=re.compile(indicator, re.I)):
                return True
        
        scripts = soup.find_all('script')
        for script in scripts:
            script_text = script.get_text().lower()
            if any(keyword in script_text for keyword in ['fetch(', 'axios', 'xmlhttprequest', '$.ajax']):
                return True
        
        return False
    
    def _has_pagination(self, soup: BeautifulSoup) -> bool:
        """페이지네이션 존재 여부 감지"""
        pagination_indicators = [
            'pagination', 'page-nav', 'pager', 'next', 'previous', 'more'
        ]
        
        for indicator in pagination_indicators:
            if soup.find(class_=re.compile(indicator, re.I)) or soup.find(id=re.compile(indicator, re.I)):
                return True
        
        return False
    
    def _is_mobile_optimized(self, soup: BeautifulSoup) -> bool:
        """모바일 최적화 여부 감지"""
        meta_viewport = soup.find('meta', attrs={'name': 'viewport'})
        if meta_viewport:
            return True
        
        styles = soup.find_all('style')
        for style in styles:
            if '@media' in style.get_text():
                return True
        
        return False

class UltraSmartContentFilter:
    """초정밀 콘텐츠 필터링 클래스"""
    
    def __init__(self):
        self.ui_keywords = {
            'navigation': [
                'home', 'about', 'contact', 'login', 'register', 'sign up', 'sign in', 
                'log in', 'log out', 'profile', 'settings', 'help', 'faq', 'search', 
                'menu', 'navigation', 'nav', 'header', 'footer', 'sidebar', 'sort', 
                'filter', 'view all', 'more', 'next', 'previous', 'page', 'pages',
                'activity', 'votes', 'comments', 'new', 'all activity', 'subscribe',
                'follow', 'unfollow', 'bookmark', 'share', 'report', 'block',
                'create post', 'submit', 'post', 'reply', 'edit', 'delete', 'save', 
                'hide', 'crosspost', 'permalink', 'source', 'embed', 'give award',
                'like', 'dislike', 'upvote', 'downvote', 'trending', 'popular', 
                'hot', 'rising', 'controversial', 'top', 'best', 'random'
            ],
            'korean': [
                '홈', '소개', '연락처', '로그인', '회원가입', '가입', '로그아웃',
                '프로필', '설정', '도움말', '검색', '메뉴', '네비게이션', '헤더',
                '푸터', '사이드바', '정렬', '필터', '전체보기', '더보기', '다음',
                '이전', '페이지', '활동', '투표', '댓글', '새글', '전체활동',
                '구독', '팔로우', '언팔로우', '북마크', '공유', '신고', '차단',
                '글쓰기', '작성', '등록', '답글', '수정', '삭제', '저장', '숨기기',
                '퍼가기', '링크', '소스', '임베드', '추천', '비추천', '좋아요', 
                '싫어요', '인기', '핫', '상승', '논란', '탑', '베스트', '최신', 
                '랜덤', '트렌딩'
            ]
        }
        
        self.exact_exclude_texts = {
            'home', 'about', 'contact', 'login', 'register', 'sign up', 'sign in', 
            'log in', 'log out', 'profile', 'settings', 'help', 'faq', 'search', 
            'menu', 'navigation', 'activity', 'votes', 'comments', 'new', 
            'all activity', 'subscribe', 'submit', 'post', 'reply', 'edit', 
            'delete', 'save', 'hide', 'share', 'report', 'block', 'follow', 
            'unfollow', 'popular', 'hot', 'rising', 'top', 'best', 'random', 
            'trending', 'upvote', 'downvote', 'like', 'dislike', 'bookmark',
            '홈', '소개', '연락처', '로그인', '회원가입', '가입', '로그아웃',
            '프로필', '설정', '도움말', '검색', '메뉴', '네비게이션', '활동',
            '투표', '댓글', '새글', '전체활동', '구독', '글쓰기', '작성', '등록', 
            '답글', '수정', '삭제', '저장', '숨기기', '공유', '신고', '차단', 
            '팔로우', '언팔로우', '인기', '핫', '상승', '탑', '베스트', '최신', 
            '랜덤', '추천', '비추천', '좋아요', '싫어요', '북마크', '트렌딩'
        }
        
        self.ui_patterns = [
            r'^(home|about|contact|login|register)$',
            r'^(로그인|회원가입|홈|소개)$',
            r'^\d+\s*(comments?|댓글|개)$',
            r'^\d+\s*(points?|포인트|점수)$',
            r'^\d+\s*(votes?|투표)$',
            r'^(upvote|downvote|추천|비추천)$',
            r'^(subscribe|구독|팔로우)$',
            r'^(create|작성|등록)\s+(post|글)$',
            r'^(sign\s+up|sign\s+in|log\s+in|log\s+out)$',
            r'^\w+\s*→\s*\w+$',
            r'^\d+\s*\/\s*\d+$',
        ]
        
        self.title_frequency = Counter()
    
    def is_ui_element(self, text: str, element) -> bool:
        """종합적인 UI 요소 판단"""
        if not text:
            return True
        
        text_clean = text.strip().lower()
        
        if self.is_exact_ui_element(text_clean):
            return True
        
        if len(text_clean) < 3 or len(text_clean) > 500:
            return True
        
        for pattern in self.ui_patterns:
            if re.match(pattern, text_clean, re.IGNORECASE):
                return True
        
        if self.is_navigation_structure(element):
            return True
        
        self.title_frequency[text_clean] += 1
        if self.title_frequency[text_clean] > 2:
            return True
        
        return False
    
    def is_meaningful_post(self, title: str, content: str = "", element=None) -> bool:
        """의미있는 게시물인지 종합 판단"""
        try:
            if not title:
                return False
            
            if self.is_ui_element(title, element):
                return False
            
            title_clean = title.strip()
            
            if len(title_clean) < 5 or len(title_clean) > 300:
                return False
            
            meaningful_words = len([word for word in title_clean.split() if len(word) > 2])
            if meaningful_words < 2:
                return False
            
            post_score = self.calculate_post_score(title_clean, content, element)
            
            return post_score >= 3
            
        except Exception:
            return False
    
    def calculate_post_score(self, title: str, content: str = "", element=None) -> float:
        """게시물 점수 계산"""
        score = 1.0
        
        try:
            # 길이 점수
            if 10 <= len(title) <= 150:
                score += 2.0
            elif 5 <= len(title) <= 200:
                score += 1.0
            
            # 질문형 보너스
            if '?' in title or any(word in title.lower() for word in 
                                 ['what', 'how', 'why', 'when', 'where', 'who', 'which',
                                  '무엇', '어떻게', '왜', '언제', '어디', '누구', '어느']):
                score += 3.0
            
            # 뉴스/정보성 콘텐츠 보너스
            news_indicators = [
                'news', 'breaking', 'report', 'study', 'research', 'analysis',
                '뉴스', '속보', '보고서', '연구', '분석', '발표'
            ]
            if any(indicator in title.lower() for indicator in news_indicators):
                score += 2.0
            
            # 토론/의견 콘텐츠 보너스
            discussion_indicators = [
                'opinion', 'thoughts', 'discussion', 'debate', 'view', 'think',
                '의견', '생각', '토론', '논의', '견해'
            ]
            if any(indicator in title.lower() for indicator in discussion_indicators):
                score += 2.0
            
            # UI 요소 페널티
            if self.is_exact_ui_element(title.lower()):
                score -= 10.0
            
            # 구조적 위치 점수
            if element:
                if self.is_navigation_structure(element):
                    score -= 5.0
                
                if element.find('a', href=True):
                    score += 1.0
                
                if self.has_post_metadata(element):
                    score += 2.0
            
            return score
            
        except Exception:
            return 0.0
    
    def has_post_metadata(self, element) -> bool:
        """게시물 메타데이터 존재 여부 확인"""
        try:
            element_text = element.get_text().lower()
            
            date_patterns = [
                r'\d{4}[-./]\d{1,2}[-./]\d{1,2}',
                r'\d{1,2}[-./]\d{1,2}[-./]\d{4}',
                r'\d+\s*(분|시간|일|달|년)\s*전',
                r'\d+\s*(minutes?|hours?|days?|months?|years?)\s*ago'
            ]
            
            for pattern in date_patterns:
                if re.search(pattern, element_text):
                    return True
            
            meta_selectors = [
                '.meta', '.info', '.details', '.timestamp', '.author',
                '.date', '.time', '.stats', '.score', '.votes'
            ]
            
            for selector in meta_selectors:
                if element.select_one(selector):
                    return True
            
            return False
            
        except Exception:
            return False
        
    def is_exact_ui_element(self, text: str) -> bool:
        """정확히 UI 요소 텍스트인지 확인"""
        if not text:
            return True
        
        text_clean = text.strip().lower()
        return text_clean in self.exact_exclude_texts
    
    def is_navigation_structure(self, element) -> bool:
        """HTML 구조상 네비게이션 요소인지 확인"""
        try:
            nav_parents = ['nav', 'header', 'footer', 'aside']
            current = element.parent if hasattr(element, 'parent') else None
            depth = 0
            
            while current and depth < 4:
                if hasattr(current, 'name') and current.name in nav_parents:
                    return True
                
                if hasattr(current, 'get') and (current.get('class') or current.get('id')):
                    class_id = ' '.join(current.get('class', []) + [current.get('id', '')]).lower()
                    nav_indicators = ['nav', 'menu', 'tab', 'breadcrumb', 'pagination', 'toolbar', 'controls']
                    if any(indicator in class_id for indicator in nav_indicators):
                        return True
                
                current = getattr(current, 'parent', None)
                depth += 1
            
            return False
        except Exception:
            return False

class PaginationHandler:
    """페이지네이션 처리기"""
    
    def __init__(self, crawler):
        self.crawler = crawler
        self.max_pages = 20
    
    def find_next_page_url(self, soup: BeautifulSoup, current_url: str) -> Optional[str]:
        """다음 페이지 URL 찾기"""
        try:
            next_patterns = [
                'a:contains("다음")', 'a:contains("Next")', 'a:contains(">")',
                'a:contains("▶")', 'a:contains("→")', 'a:contains("more")',
                '.next', '.page-next', '#next', '.pagination-next',
                '.pager-next', '.btn-next', '.arrow-next',
                'a[rel="next"]', 'a[aria-label*="next"]', 'a[title*="next"]',
                'a[title*="다음"]', 'a[class*="next"]',
                '.pagination a', '.pager a', '.page-numbers a'
            ]
            
            for pattern in next_patterns:
                try:
                    if pattern.startswith('a:contains'):
                        text_to_find = pattern.split('"')[1]
                        links = soup.find_all('a', string=lambda text: text and text_to_find in text)
                        if links:
                            next_link = links[0]
                        else:
                            continue
                    else:
                        next_link = soup.select_one(pattern)
                        if not next_link:
                            continue
                    
                    href = next_link.get('href')
                    if href:
                        if href.startswith('http'):
                            return href
                        else:
                            return urljoin(current_url, href)
                            
                except Exception as e:
                    logger.debug(f"패턴 '{pattern}' 처리 중 오류: {e}")
                    continue
            
            return self._find_next_by_page_number(soup, current_url)
            
        except Exception as e:
            logger.warning(f"다음 페이지 URL 찾기 실패: {e}")
            return None
    
    def _find_next_by_page_number(self, soup: BeautifulSoup, current_url: str) -> Optional[str]:
        """페이지 번호 기반으로 다음 페이지 찾기"""
        try:
            current_page = self._extract_page_number(current_url)
            if current_page is None:
                return None
            
            next_page = current_page + 1
            
            if 'page=' in current_url:
                return re.sub(r'page=\d+', f'page={next_page}', current_url)
            elif 'p=' in current_url:
                return re.sub(r'p=\d+', f'p={next_page}', current_url)
            elif '/page/' in current_url:
                return re.sub(r'/page/\d+', f'/page/{next_page}', current_url)
            elif current_url.endswith(str(current_page)):
                return current_url.replace(str(current_page), str(next_page))
            else:
                separator = '&' if '?' in current_url else '?'
                return f"{current_url}{separator}page={next_page}"
                
        except Exception as e:
            logger.debug(f"페이지 번호 기반 URL 생성 실패: {e}")
            return None
    
    def _extract_page_number(self, url: str) -> Optional[int]:
        """URL에서 현재 페이지 번호 추출"""
        try:
            patterns = [
                r'page=(\d+)',
                r'p=(\d+)',
                r'/page/(\d+)',
                r'&page=(\d+)',
                r'\?page=(\d+)'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, url)
                if match:
                    return int(match.group(1))
            
            url_parts = url.rstrip('/').split('/')
            if url_parts and url_parts[-1].isdigit():
                return int(url_parts[-1])
            
            return 1
            
        except Exception:
            return None

class UniversalCrawler:
    """궁극의 범용 웹사이트 크롤러"""
    
    def __init__(self):
        """크롤러 초기화"""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': self._get_random_user_agent(),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
        
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=10,
            pool_maxsize=20,
            max_retries=3,
            pool_block=False
        )
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)
        
        self.content_classifier = SmartContentClassifier()
        self.site_detector = AdvancedSiteDetector()
        self.content_filter = UltraSmartContentFilter()
        self.pagination_handler = PaginationHandler(self)
        
        self.template_cache = {}
        self.site_config_cache = {}
        self.robots_cache = {}
        
        self.stats = {
            'requests_made': 0,
            'cache_hits': 0,
            'total_time': 0,
            'errors': 0
        }
        
        import os
        max_workers = min(8, (os.cpu_count() or 1) + 2)
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)
    
    def _get_random_user_agent(self) -> str:
        """랜덤 User-Agent 반환"""
        import random
        return random.choice(USER_AGENTS)
    
    @lru_cache(maxsize=128)
    def _get_site_config(self, domain: str) -> Dict:
        """사이트별 설정 캐싱"""
        # 포럼/커뮤니티 사이트
        forum_indicators = ['forum', 'board', 'community', 'discuss', 'cafe', 'club']
        if any(indicator in domain.lower() for indicator in forum_indicators):
            return SITE_CONFIGS.get('forum', SITE_CONFIGS['default'])
        
        # 뉴스 사이트
        news_indicators = ['news', 'press', 'media', 'journal', 'times', 'post', 'herald']
        if any(indicator in domain.lower() for indicator in news_indicators):
            return SITE_CONFIGS.get('news', SITE_CONFIGS['default'])
        
        return SITE_CONFIGS['default']
    
    def detect_site_structure(self, url: str, soup: BeautifulSoup) -> Tuple[SiteTemplate, Dict]:
        """사이트 구조 감지 및 템플릿 생성"""
        try:
            domain = urlparse(url).netloc.lower()
            
            # 캐시 확인
            cache_key = f"{domain}_template"
            if cache_key in self.template_cache:
                self.stats['cache_hits'] += 1
                template = self.template_cache[cache_key]
                characteristics = self.site_detector.detect_site_characteristics(url, soup)
                return template, characteristics
            
            # 사이트 특성 감지
            characteristics = self.site_detector.detect_site_characteristics(url, soup)
            
            # 템플릿 생성
            template = self._create_adaptive_template(soup, domain)
            
            # 캐시 저장
            self.template_cache[cache_key] = template
            
            return template, characteristics
            
        except Exception as e:
            logger.error(f"사이트 구조 감지 실패: {e}")
            # 기본 템플릿 반환
            default_template = SiteTemplate(
                name="기본",
                post_selectors=["article", ".post", ".item", "tr", "li"],
                title_selectors=["h1", "h2", "h3", ".title", ".subject"],
                link_selectors=["a[href]"],
                view_selectors=[".views", ".view-count", ".hit"],
                like_selectors=[".likes", ".like-count", ".recommend"],
                comment_selectors=[".comments", ".comment-count", ".reply"],
                date_selectors=[".date", ".time", ".timestamp"],
                author_selectors=[".author", ".writer", ".name"],
                thumbnail_selectors=["img", ".thumbnail"],
                exclude_selectors=[".nav", ".menu", ".header", ".footer", ".ad"]
            )
            return default_template, {'is_crawlable': True}
    
    def _create_adaptive_template(self, soup: BeautifulSoup, domain: str) -> SiteTemplate:
        """적응형 템플릿 생성"""
        
        domain_patterns = {
            'cafe.naver.com': {
                'post_selectors': ['.board-list tr', '.article-board tr'],
                'title_selectors': ['.board-list .title a', '.article-board .title a'],
                'link_selectors': ['.title a[href]'],
                'view_selectors': ['.view-count', '.hit'],
                'comment_selectors': ['.comment-count', '.reply-count'],
                'date_selectors': ['.date', '.time']
            },
            'cafe.daum.net': {
                'post_selectors': ['.board_list tr', '.list_table tr'],
                'title_selectors': ['.subject a', '.title a'],
                'link_selectors': ['.subject a[href]', '.title a[href]'],
                'view_selectors': ['.read_count', '.views'],
                'comment_selectors': ['.comment_count', '.reply_count'],
                'date_selectors': ['.date', '.reg_date']
            },
            'clien.net': {
                'post_selectors': ['.list_item', '.board_main_view'],
                'title_selectors': ['.subject_fixed', '.list_subject'],
                'link_selectors': ['.list_subject a[href]'],
                'view_selectors': ['.hit', '.view_count'],
                'comment_selectors': ['.comment_count', '.reply_count'],
                'date_selectors': ['.timestamp', '.date']
            }
        }
        
        if domain in domain_patterns:
            patterns = domain_patterns[domain]
            template_name = domain
        else:
            patterns = self._auto_detect_patterns(soup)
            template_name = "자동감지"
        
        return SiteTemplate(
            name=template_name,
            post_selectors=patterns.get('post_selectors', ["article", ".post", ".item", ".entry", "tr", "li"]),
            title_selectors=patterns.get('title_selectors', ["h1", "h2", "h3", ".title", "[class*='title']", ".subject"]),
            link_selectors=patterns.get('link_selectors', ["a[href]"]),
            view_selectors=patterns.get('view_selectors', [".views", ".view-count", "[class*='view']", ".hit"]),
            like_selectors=patterns.get('like_selectors', [".likes", ".like-count", "[class*='like']", ".recommend"]),
            comment_selectors=patterns.get('comment_selectors', [".comments", ".comment-count", "[class*='comment']", ".reply"]),
            date_selectors=patterns.get('date_selectors', [".date", ".time", "[class*='date']", ".timestamp"]),
            author_selectors=patterns.get('author_selectors', [".author", ".writer", "[class*='author']", ".name"]),
            thumbnail_selectors=patterns.get('thumbnail_selectors', ["img", ".thumbnail", "[class*='thumb']"]),
            exclude_selectors=patterns.get('exclude_selectors', [".nav", ".menu", ".header", ".footer", ".ad", ".advertisement", ".sidebar"])
        )

    def _auto_detect_patterns(self, soup: BeautifulSoup) -> Dict:
        """자동 패턴 감지"""
        patterns = {
            'post_selectors': [],
            'title_selectors': [],
            'link_selectors': ["a[href]"],
            'view_selectors': [],
            'like_selectors': [],
            'comment_selectors': [],
            'date_selectors': [],
            'author_selectors': [],
            'thumbnail_selectors': ["img"],
            'exclude_selectors': [".nav", ".menu", ".header", ".footer", ".ad", ".sidebar"]
        }
        
        potential_posts = []
        
        # 테이블 기반 게시판 감지
        table_rows = soup.select('table tr')
        if len(table_rows) > 5:
            content_rows = [row for row in table_rows if len(row.get_text(strip=True)) > 20]
            if len(content_rows) >= 3:
                potential_posts.extend(['tbody tr', 'table tr:not(:first-child)', 'tr'])
        
        # 아티클 기반 콘텐츠
        articles = soup.select('article')
        if len(articles) >= 3:
            potential_posts.extend(['article', 'article[class*="post"]', 'article[class*="item"]'])
        
        # 리스트 아이템
        list_items = soup.select('ul li, ol li')
        meaningful_items = [li for li in list_items if len(li.get_text(strip=True)) > 30]
        if len(meaningful_items) >= 5:
            potential_posts.extend(['ul li', 'ol li', 'li'])
        
        # 클래스 빈도 분석
        class_frequency = Counter()
        for element in soup.find_all(class_=True):
            for cls in element.get('class', []):
                if any(keyword in cls.lower() for keyword in ['post', 'item', 'entry', 'article', 'thread']):
                    class_frequency[f'.{cls}'] += 1
        
        for cls, count in class_frequency.items():
            if count >= 3:
                potential_posts.append(cls)
        
        patterns['post_selectors'] = potential_posts or ["article", ".post", ".item", "tr", "li"]
        
        return patterns

    def extract_meaningful_posts(self, soup: BeautifulSoup, template: SiteTemplate) -> List:
        """의미있는 게시물 요소 추출"""
        all_elements = []
        
        self._remove_ui_sections(soup)
        
        all_selectors = template.post_selectors
        
        for selector in all_selectors:
            try:
                elements = soup.select(selector)
                if elements:
                    logger.info(f"선택자 '{selector}'로 {len(elements)}개 요소 발견")
                    
                    filtered_elements = []
                    for element in elements:
                        if self._is_valid_post_element(element, template):
                            filtered_elements.append(element)
                    
                    if filtered_elements:
                        all_elements.extend(filtered_elements)
                        logger.info(f"필터링 후 {len(filtered_elements)}개 유효한 게시물")
                        
                        if len(all_elements) >= 10:
                            break
                            
            except Exception as e:
                logger.warning(f"선택자 '{selector}' 처리 중 오류: {e}")
                continue
        
        quality_posts = []
        for element in all_elements[:50]:
            title = self.extract_with_selectors(element, template.title_selectors)
            if title and self.content_filter.is_meaningful_post(title, "", element):
                quality_posts.append(element)
        
        unique_posts = self._remove_duplicate_posts(quality_posts, template)
        
        logger.info(f"최종 추출된 게시물 요소: {len(unique_posts)}개")
        
        return unique_posts[:30]

    def _remove_ui_sections(self, soup: BeautifulSoup):
        """명확한 UI 섹션 제거"""
        try:
            ui_selectors = [
                'nav', 'header', 'footer', '.navbar', '.header', '.footer',
                '.navigation', '.menu', '.sidebar', '.controls', '.toolbar',
                '.breadcrumb', '.pagination', '.tabs', '.tab-content',
                '.ad', '.advertisement', '.sponsor', '.promoted'
            ]
            
            for selector in ui_selectors:
                elements = soup.select(selector)
                for element in elements:
                    element.decompose()
            
            logger.debug("UI 섹션 제거 완료")
            
        except Exception as e:
            logger.warning(f"UI 섹션 제거 중 오류: {e}")

    def _is_valid_post_element(self, element, template: SiteTemplate) -> bool:
        """게시물 요소의 유효성 검사"""
        try:
            element_text = element.get_text(strip=True)
            if len(element_text) < 10:
                return False
            
            title = self.extract_with_selectors(element, template.title_selectors)
            if not title:
                return False
            
            if self.content_filter.is_ui_element(title, element):
                return False
            
            has_link = bool(element.find('a', href=True))
            if not has_link:
                if len(element_text) < 50:
                    return False
            
            if self._has_post_structure(element):
                return True
            
            score = self.content_filter.calculate_post_score(title, element_text, element)
            return score >= 3
            
        except Exception as e:
            logger.debug(f"게시물 요소 검사 중 오류: {e}")
            return False

    def _has_post_structure(self, element) -> bool:
        """게시물 구조 확인"""
        try:
            post_indicators = [
                'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
                '.title', '.subject', '.headline',
                '.meta', '.info', '.stats',
                '.content', '.body', '.text',
                '.author', '.username', '.user',
                '.date', '.time', '.timestamp',
                '.votes', '.score', '.points'
            ]
            
            found_indicators = 0
            for indicator in post_indicators:
                if element.select_one(indicator):
                    found_indicators += 1
            
            return found_indicators >= 2
            
        except Exception:
            return False

    def _remove_duplicate_posts(self, elements: List, template: SiteTemplate) -> List:
        """중복 게시물 제거"""
        try:
            seen_titles = set()
            unique_elements = []
            
            for element in elements:
                title = self.extract_with_selectors(element, template.title_selectors)
                if title:
                    normalized_title = re.sub(r'\s+', ' ', title.lower().strip())
                    
                    if normalized_title not in seen_titles:
                        seen_titles.add(normalized_title)
                        unique_elements.append(element)
            
            logger.info(f"중복 제거: {len(elements)} -> {len(unique_elements)}개")
            return unique_elements
            
        except Exception as e:
            logger.warning(f"중복 제거 중 오류: {e}")
            return elements

    def extract_with_selectors(self, element, selectors: List[str], attribute: str = None) -> str:
        """다중 선택자로 텍스트 추출"""
        for selector in selectors:
            try:
                found = element.select_one(selector)
                if found:
                    if attribute:
                        return found.get(attribute, "")
                    else:
                        text = found.get_text(strip=True)
                        if text and len(text) > 2:
                            return text
            except Exception:
                continue
        return ""
    
    def extract_number(self, text: str) -> int:
        """텍스트에서 숫자 추출"""
        if not text:
            return 0
        try:
            numbers = re.findall(r'\d+', str(text))
            return int(numbers[0]) if numbers else 0
        except Exception:
            return 0
    
    def extract_thumbnail(self, element, base_url: str, selectors: List[str]) -> Optional[str]:
        """썸네일 이미지 URL 추출"""
        for selector in selectors:
            try:
                img = element.select_one(selector)
                if img:
                    src = img.get('src') or img.get('data-src') or img.get('data-original')
                    if src:
                        if src.startswith('http'):
                            return src
                        else:
                            return urljoin(base_url, src)
            except Exception:
                continue
        return None
    
    def normalize_date(self, date_text: str) -> str:
        """날짜 정규화"""
        if not date_text:
            return ""
        
        try:
            now = datetime.now()
            
            if '분 전' in date_text or '분전' in date_text:
                return now.strftime('%Y.%m.%d %H:%M')
            elif '시간 전' in date_text or '시간전' in date_text:
                return now.strftime('%Y.%m.%d %H:%M')
            elif '일 전' in date_text or '일전' in date_text:
                days_ago = self.extract_number(date_text)
                target_date = now - timedelta(days=days_ago)
                return target_date.strftime('%Y.%m.%d')
            else:
                return date_text.strip()
                
        except Exception:
            return date_text

    def parse_post_date(self, date_text: str) -> Optional[datetime]:
        """게시물 날짜 파싱"""
        if not date_text:
            return None
        
        try:
            # 상대적 시간 처리
            now = datetime.now()
            
            if '분 전' in date_text or '분전' in date_text:
                minutes_ago = self.extract_number(date_text)
                return now - timedelta(minutes=minutes_ago)
            elif '시간 전' in date_text or '시간전' in date_text:
                hours_ago = self.extract_number(date_text)
                return now - timedelta(hours=hours_ago)
            elif '일 전' in date_text or '일전' in date_text:
                days_ago = self.extract_number(date_text)
                return now - timedelta(days=days_ago)
            
            # 절대 날짜 파싱
            date_patterns = [
                '%Y.%m.%d %H:%M',
                '%Y-%m-%d %H:%M',
                '%Y.%m.%d',
                '%Y-%m-%d',
                '%m.%d %H:%M',
                '%m-%d %H:%M'
            ]
            
            for pattern in date_patterns:
                try:
                    return datetime.strptime(date_text.strip(), pattern)
                except ValueError:
                    continue
            
            return None
            
        except Exception:
            return None

    async def extract_posts_multithread(self, elements: List, template: SiteTemplate, base_url: str) -> List[Dict]:
        """멀티스레드로 게시물 정보 추출"""
        posts = []
        
        def extract_single_post(element, idx):
            try:
                title = self.extract_with_selectors(element, template.title_selectors)
                if not title or len(title.strip()) < 3:
                    return None
                
                link = self.extract_with_selectors(element, template.link_selectors, "href")
                if link and not link.startswith('http'):
                    link = urljoin(base_url, link)
                
                views_text = self.extract_with_selectors(element, template.view_selectors)
                likes_text = self.extract_with_selectors(element, template.like_selectors)
                comments_text = self.extract_with_selectors(element, template.comment_selectors)
                date_text = self.extract_with_selectors(element, template.date_selectors)
                author = self.extract_with_selectors(element, template.author_selectors)
                thumbnail = self.extract_thumbnail(element, base_url, template.thumbnail_selectors)
                
                views = _parse_korean_number(views_text) if views_text else 0
                likes = _parse_korean_number(likes_text) if likes_text else 0
                comments = _parse_korean_number(comments_text) if comments_text else 0
                
                classification = self.content_classifier.classify_content(title)
                
                return {
                    "번호": idx + 1,
                    "원제목": title,
                    "번역제목": None,
                    "링크": link or base_url,
                    "원문URL": link or base_url,
                    "썸네일 URL": thumbnail,
                    "본문": None,
                    "조회수": views,
                    "추천수": likes,
                    "댓글수": comments,
                    "작성일": self.normalize_date(date_text),
                    "작성자": author or "익명",
                    "사이트": urlparse(base_url).netloc,
                    "콘텐츠타입": classification.type,
                    "분류신뢰도": classification.confidence,
                    "키워드": classification.keywords,
                    "감정": classification.sentiment
                }
                
            except Exception as e:
                logger.warning(f"게시물 {idx} 추출 오류: {e}")
                return None
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            future_to_idx = {executor.submit(extract_single_post, element, idx): idx 
                           for idx, element in enumerate(elements)}
            
            for future in concurrent.futures.as_completed(future_to_idx):
                result = future.result()
                if result:
                    posts.append(result)
        
        return posts
    
    def filter_by_metrics(self, posts: List[Dict], min_views: int, min_likes: int) -> List[Dict]:
        """메트릭으로 게시물 필터링"""
        if min_views <= 0 and min_likes <= 0:
            return posts
        
        filtered = []
        for post in posts:
            views = post.get('조회수', 0)
            likes = post.get('추천수', 0)
            
            if views >= min_views and likes >= min_likes:
                filtered.append(post)
        
        logger.info(f"메트릭 필터링: {len(posts)} -> {len(filtered)} 게시물")
        return filtered

    def filter_by_date_range_exact(self, posts: List[Dict], start_date: str, end_date: str) -> List[Dict]:
        """정확한 날짜 범위로 필터링"""
        try:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            end_dt = end_dt.replace(hour=23, minute=59, second=59)
            
            filtered = []
            for post in posts:
                date_str = post.get('작성일', '')
                post_date = self.parse_post_date(date_str)
                
                if post_date and start_dt <= post_date <= end_dt:
                    filtered.append(post)
            
            logger.info(f"날짜 필터링: {len(posts)} -> {len(filtered)} 게시물")
            return filtered
            
        except Exception as e:
            logger.error(f"날짜 필터링 오류: {e}")
            return posts
    
    def sort_posts(self, posts: List[Dict], method: str) -> List[Dict]:
        """게시물 정렬"""
        if not posts:
            return posts
        
        try:
            if method == "popular":
                return sorted(posts, key=lambda x: x.get('조회수', 0), reverse=True)
            elif method == "recommend":
                return sorted(posts, key=lambda x: x.get('추천수', 0), reverse=True)
            elif method == "comments":
                return sorted(posts, key=lambda x: x.get('댓글수', 0), reverse=True)
            elif method == "recent":
                return sorted(posts, key=lambda x: x.get('작성일', ''), reverse=True)
            elif method == "confidence":
                return sorted(posts, key=lambda x: x.get('분류신뢰도', 0), reverse=True)
            elif method == "content_type":
                return sorted(posts, key=lambda x: x.get('콘텐츠타입', 'general'))
            else:
                return posts
        except Exception as e:
            logger.error(f"정렬 오류: {e}")
            return posts

    async def try_alternative_crawling(self, soup: BeautifulSoup, template: SiteTemplate, base_url: str) -> List[Dict]:
        """대안적 크롤링 시도"""
        try:
            logger.info("대안 크롤링 시도 중...")
            
            posts = []
            
            # JSON-LD 구조화 데이터
            json_ld_posts = self._extract_from_json_ld(soup)
            if json_ld_posts:
                posts.extend(json_ld_posts)
            
            # 메타 태그
            meta_posts = self._extract_from_meta_tags(soup, base_url)
            if meta_posts:
                posts.extend(meta_posts)
            
            # 잠재적 게시물 요소들
            potential_elements = soup.find_all(['div', 'li', 'tr'])
            filtered_elements = [elem for elem in potential_elements if self._is_potential_post(elem)]
            
            for idx, element in enumerate(filtered_elements[:20]):
                post_data = self._extract_alternative_post_data(element, idx, base_url)
                if post_data:
                    posts.append(post_data)
            
            return posts
            
        except Exception as e:
            logger.error(f"대안 크롤링 실패: {e}")
            return []

    def _extract_from_json_ld(self, soup: BeautifulSoup) -> List[Dict]:
        """JSON-LD 구조화 데이터에서 정보 추출"""
        try:
            posts = []
            json_scripts = soup.find_all('script', type='application/ld+json')
            
            for script in json_scripts:
                try:
                    data = json.loads(script.string)
                    if isinstance(data, list):
                        data = data[0] if data else {}
                    
                    if data.get('@type') in ['Article', 'BlogPosting', 'NewsArticle']:
                        post = {
                            "번호": len(posts) + 1,
                            "원제목": data.get('headline', data.get('name', '제목 없음')),
                            "번역제목": None,
                            "링크": data.get('url', ''),
                            "원문URL": data.get('url', ''),
                            "썸네일 URL": self._extract_image_from_schema(data),
                            "본문": data.get('description', data.get('text', ''))[:200],
                            "조회수": 0,
                            "추천수": 0,
                            "댓글수": 0,
                            "작성일": self._format_schema_date(data.get('datePublished')),
                            "작성자": self._extract_author_from_schema(data),
                            "사이트": urlparse(data.get('url', '')).netloc if data.get('url') else '',
                            "콘텐츠타입": "article",
                            "분류신뢰도": 0.8,
                            "키워드": [],
                            "감정": "neutral",
                            "크롤링방식": "JSON-LD"
                        }
                        posts.append(post)
                        
                except json.JSONDecodeError:
                    continue
            
            return posts
            
        except Exception as e:
            logger.debug(f"JSON-LD 추출 오류: {e}")
            return []
    
    def _extract_from_meta_tags(self, soup: BeautifulSoup, base_url: str) -> List[Dict]:
        """메타 태그에서 정보 추출"""
        try:
            title = ""
            description = ""
            image = ""
            
            og_title = soup.find('meta', property='og:title')
            twitter_title = soup.find('meta', name='twitter:title')
            page_title = soup.find('title')
            
            if og_title:
                title = og_title.get('content', '')
            elif twitter_title:
                title = twitter_title.get('content', '')
            elif page_title:
                title = page_title.get_text(strip=True)
            
            og_desc = soup.find('meta', property='og:description')
            twitter_desc = soup.find('meta', name='twitter:description')
            meta_desc = soup.find('meta', name='description')
            
            if og_desc:
                description = og_desc.get('content', '')
            elif twitter_desc:
                description = twitter_desc.get('content', '')
            elif meta_desc:
                description = meta_desc.get('content', '')
            
            og_image = soup.find('meta', property='og:image')
            twitter_image = soup.find('meta', name='twitter:image')
            
            if og_image:
                image = og_image.get('content', '')
            elif twitter_image:
                image = twitter_image.get('content', '')
            
            if title:
                return [{
                    "번호": 1,
                    "원제목": title,
                    "번역제목": None,
                    "링크": base_url,
                    "원문URL": base_url,
                    "썸네일 URL": image if image.startswith('http') else None,
                    "본문": description,
                    "조회수": 0,
                    "추천수": 0,
                    "댓글수": 0,
                    "작성일": datetime.now().strftime('%Y.%m.%d'),
                    "작성자": "익명",
                    "사이트": urlparse(base_url).netloc,
                    "콘텐츠타입": "page",
                    "분류신뢰도": 0.6,
                    "키워드": [],
                    "감정": "neutral",
                    "크롤링방식": "메타태그"
                }]
            
            return []
            
        except Exception as e:
            logger.debug(f"메타태그 추출 오류: {e}")
            return []

    def _extract_image_from_schema(self, data: Dict) -> Optional[str]:
        """스키마 데이터에서 이미지 URL 추출"""
        try:
            image = data.get('image')
            if isinstance(image, dict):
                return image.get('url')
            elif isinstance(image, list) and image:
                return image[0].get('url') if isinstance(image[0], dict) else str(image[0])
            elif isinstance(image, str):
                return image
            return None
        except Exception:
            return None
    
    def _extract_author_from_schema(self, data: Dict) -> str:
        """스키마 데이터에서 작성자 추출"""
        try:
            author = data.get('author')
            if isinstance(author, dict):
                return author.get('name', '익명')
            elif isinstance(author, str):
                return author
            return '익명'
        except Exception:
            return '익명'
    
    def _format_schema_date(self, date_str: str) -> str:
        """스키마 날짜 형식을 표준 형식으로 변환"""
        try:
            if not date_str:
                return datetime.now().strftime('%Y.%m.%d')
            
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return dt.strftime('%Y.%m.%d %H:%M')
        except Exception:
            return datetime.now().strftime('%Y.%m.%d')

    def _is_potential_post(self, element) -> bool:
        """요소가 게시물일 가능성 확인"""
        try:
            text = element.get_text(strip=True)
            if len(text) < 10 or len(text) > 1000:
                return False
            
            has_link = bool(element.find('a', href=True))
            has_heading = bool(element.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']))
            
            class_id = ' '.join(element.get('class', []) + [element.get('id', '')])
            has_post_indicator = any(keyword in class_id.lower() for keyword in 
                                   ['post', 'item', 'entry', 'article', 'thread', 'message'])
            
            score = 0
            if has_link: score += 2
            if has_heading: score += 2  
            if has_post_indicator: score += 3
            if 20 <= len(text) <= 200: score += 2
            
            return score >= 3
            
        except Exception:
            return False
    
    def _extract_alternative_post_data(self, element, idx: int, base_url: str) -> Optional[Dict]:
        """대안 방식으로 게시물 데이터 추출"""
        try:
            title = ""
            title_selectors = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', '.title', '[class*="title"]', 'strong', 'b']
            for selector in title_selectors:
                title_elem = element.select_one(selector)
                if title_elem:
                    title = title_elem.get_text(strip=True)
                    if len(title) > 5:
                        break
            
            if not title:
                all_text = element.get_text(strip=True)
                sentences = all_text.split('.')
                title = sentences[0][:100] if sentences else all_text[:100]
            
            link_elem = element.find('a', href=True)
            link = ""
            if link_elem:
                href = link_elem.get('href')
                if href:
                    if href.startswith('http'):
                        link = href
                    else:
                        link = urljoin(base_url, href)
            
            date_text = ""
            date_patterns = [r'\d{4}[-./]\d{1,2}[-./]\d{1,2}', r'\d{1,2}[-./]\d{1,2}[-./]\d{4}']
            element_text = element.get_text()
            for pattern in date_patterns:
                match = re.search(pattern, element_text)
                if match:
                    date_text = match.group()
                    break
            
            numbers = re.findall(r'\b\d+\b', element_text)
            views = int(numbers[0]) if numbers else 0
            likes = int(numbers[1]) if len(numbers) > 1 else 0
            
            return {
                "번호": idx + 1,
                "원제목": title or f"게시물 {idx + 1}",
                "번역제목": None,
                "링크": link or base_url,
                "원문URL": link or base_url,
                "썸네일 URL": None,
                "본문": element.get_text(strip=True)[:200] + "..." if len(element.get_text(strip=True)) > 200 else element.get_text(strip=True),
                "조회수": views,
                "추천수": likes,
                "댓글수": views,
                "작성일": self.normalize_date(date_text) or datetime.now().strftime('%Y.%m.%d'),
                "작성자": "익명",
                "사이트": urlparse(base_url).netloc,
                "콘텐츠타입": "general",
                "분류신뢰도": 0.5,
                "키워드": [],
                "감정": "neutral",
                "크롤링방식": "대안"
            }
            
        except Exception as e:
            logger.debug(f"대안 데이터 추출 오류: {e}")
            return None

    def get_crawling_suggestions(self, url: str) -> str:
        """크롤링 실패 시 제안사항 생성"""
        try:
            domain = urlparse(url).netloc.lower()
            
            suggestions = []
            
            suggestions.extend([
                f"🛠️ **일반적인 해결방법:**",
                f"   • robots.txt 확인: {urlparse(url).scheme}://{domain}/robots.txt",
                f"   • sitemap.xml 확인: {urlparse(url).scheme}://{domain}/sitemap.xml",
                f"   • 브라우저 개발자 도구로 네트워크 요청 분석",
                f"",
                f"🔍 **디버깅 방법:**",
                f"   • 페이지 소스 보기 (Ctrl+U)",
                f"   • JavaScript 콘솔 확인 (F12)",
                f"   • 네트워크 탭에서 API 호출 확인",
                f"   • 요소 검사로 실제 HTML 구조 확인",
                f"",
                f"📱 **모바일/대안 버전 시도:**",
                f"   • m.{domain} (모바일 버전)",
                f"   • old.{domain} (구버전 인터페이스)",
                f"   • 앱 API 엔드포인트 확인"
            ])
            
            return '\n'.join(suggestions)
            
        except Exception as e:
            logger.debug(f"제안사항 생성 오류: {e}")
            return """💡 **일반적인 해결방법:**
   • URL이 올바른 게시판 페이지인지 확인
   • 해당 사이트에 실제로 게시물이 있는지 확인  
   • 필터 조건이 너무 엄격하지 않은지 확인
   • 사이트의 robots.txt나 API 문서 확인
   • 브라우저에서 직접 접근해보기"""

    def get_performance_stats(self) -> Dict:
        """성능 통계 반환"""
        avg_time = self.stats['total_time'] / max(1, self.stats['requests_made'])
        success_rate = (self.stats['requests_made'] - self.stats['errors']) / max(1, self.stats['requests_made'])
        
        return {
            'requests_made': self.stats['requests_made'],
            'cache_hits': self.stats['cache_hits'],
            'total_time': round(self.stats['total_time'], 2),
            'average_time': round(avg_time, 2),
            'errors': self.stats['errors'],
            'success_rate': round(success_rate * 100, 1),
            'cache_hit_rate': round(self.stats['cache_hits'] / max(1, self.stats['requests_made']) * 100, 1)
        }
    
    def clear_cache(self):
        """캐시 초기화"""
        self.template_cache.clear()
        self.site_config_cache.clear()
        self.robots_cache.clear()
        self._get_site_config.cache_clear()
        logger.info("캐시 초기화 완료")
    
    def __del__(self):
        """리소스 정리"""
        try:
            if hasattr(self, 'executor'):
                self.executor.shutdown(wait=False)
            if hasattr(self, 'session'):
                self.session.close()
        except Exception:
            pass

# ================================
# 🔥 핵심 크롤링 전략 및 실행 함수들 - 완전 구현
# ================================

async def _determine_crawling_strategy(characteristics: Dict, condition_checker, 
                                     start_index: int, end_index: int, 
                                     enforce_date_limit: bool) -> Dict:
    """크롤링 전략 결정 - 완전 구현"""
    
    has_filters = (condition_checker.min_views > 0 or 
                  condition_checker.min_likes > 0 or 
                  condition_checker.min_comments > 0 or
                  (condition_checker.start_dt and condition_checker.end_dt))
    
    has_pagination = characteristics.get('has_pagination', False)
    is_dynamic = characteristics.get('is_dynamic', False)
    is_spa = characteristics.get('is_spa', False)
    
    # 전략 결정 로직
    if is_spa:
        return {
            "name": "SPA 대응",
            "method": "single_page_alternative",
            "max_pages": 1,
            "reason": "Single Page Application 감지됨"
        }
    elif has_pagination and (has_filters or enforce_date_limit):
        # 페이지네이션이 있고 필터가 있으면 다중 페이지
        max_pages = min(50, max(10, (end_index // 10) * 2))
        return {
            "name": "다중페이지 필터링",
            "method": "multi_page",
            "max_pages": max_pages,
            "reason": "페이지네이션 + 필터 조건"
        }
    elif has_pagination and not has_filters:
        # 페이지네이션이 있지만 필터가 없으면 제한적 다중 페이지
        max_pages = min(10, max(3, (end_index // 20) + 2))
        return {
            "name": "제한적 다중페이지",
            "method": "multi_page", 
            "max_pages": max_pages,
            "reason": "페이지네이션, 필터 없음"
        }
    elif is_dynamic:
        # 동적 사이트는 단일 페이지 + 대안 시도
        return {
            "name": "동적사이트 대응",
            "method": "single_page_alternative",
            "max_pages": 1,
            "reason": "JavaScript 동적 로딩"
        }
    else:
        # 기본: 단일 페이지
        return {
            "name": "단일페이지",
            "method": "single_page",
            "max_pages": 1,
            "reason": "정적 사이트"
        }

def _determine_universal_site_type(characteristics: Dict, url: str) -> str:
    """범용 사이트 타입 결정 - 완전 구현"""
    
    if characteristics.get('is_spa'):
        return "spa"
    elif characteristics.get('has_pagination'):
        return "forum"
    elif characteristics.get('is_dynamic'):
        return "dynamic"
    else:
        return "static"

def _summarize_characteristics(characteristics: Dict) -> str:
    """사이트 특성 요약 - 완전 구현"""
    active_characteristics = [k.replace('_', ' ') for k, v in characteristics.items() if v]
    return ", ".join(active_characteristics[:3]) if active_characteristics else "기본"

async def _handle_problematic_site(crawler, soup: BeautifulSoup, template, 
                                 board_url: str, start_index: int, end_index: int, 
                                 websocket=None) -> List[Dict]:
    """문제가 있는 사이트 처리 (SPA, 동적 로딩 등) - 완전 구현"""
    
    if websocket:
        await websocket.send_json({
            "progress": 40,
            "status": "⚠️ 문제 사이트 감지 - 대안 시도",
            "details": "JavaScript/SPA 사이트입니다. 가능한 콘텐츠를 추출합니다."
        })
    
    # 1단계: 기존 대안 크롤링 시도
    alternative_posts = await crawler.try_alternative_crawling(soup, template, board_url)
    
    if alternative_posts:
        logger.info(f"대안 크롤링 성공: {len(alternative_posts)}개 게시물")
        
        # 범위 적용
        if start_index <= len(alternative_posts):
            result_posts = alternative_posts[start_index-1:end_index]
            for idx, post in enumerate(result_posts):
                post['번호'] = start_index + idx
            return result_posts
        else:
            return []
    
    # 2단계: 고급 대안 시도
    advanced_posts = await _try_advanced_alternatives(crawler, soup, board_url, websocket)
    
    if advanced_posts:
        # 범위 적용
        if start_index <= len(advanced_posts):
            result_posts = advanced_posts[start_index-1:end_index]
            for idx, post in enumerate(result_posts):
                post['번호'] = start_index + idx
            return result_posts
    
    # 3단계: 실패 시 상세한 가이드 제공
    suggestions = crawler.get_crawling_suggestions(board_url)
    raise Exception(f"""이 사이트는 고급 JavaScript 동적 로딩으로 인해 크롤링이 제한됩니다.

💡 해결 방법:
{suggestions}

🔧 추가 시도사항:
- 해당 사이트의 RSS 피드 확인
- 모바일 버전 URL 시도
- API 엔드포인트 직접 접근
- 사이트의 sitemap.xml 확인""")

async def _try_advanced_alternatives(crawler, soup: BeautifulSoup, board_url: str, websocket=None) -> List[Dict]:
    """고급 대안 크롤링 시도 - 완전 구현"""
    
    posts = []
    
    try:
        # RSS/Atom 피드 자동 감지
        rss_posts = await _try_rss_auto_discovery(crawler, board_url)
        if rss_posts:
            posts.extend(rss_posts)
        
        # API 엔드포인트 자동 감지
        api_posts = await _try_api_auto_discovery(crawler, board_url)
        if api_posts:
            posts.extend(api_posts)
        
        # 모바일 버전 시도
        mobile_posts = await _try_mobile_version(crawler, board_url)
        if mobile_posts:
            posts.extend(mobile_posts)
        
        return posts
        
    except Exception as e:
        logger.debug(f"고급 대안 크롤링 오류: {e}")
        return []
    
async def _enhance_universal_post_metadata(posts: List[Dict], board_url: str, site_type: str) -> List[Dict]:
    """범용 게시물 메타데이터 보강 - 완전 구현"""
    
    domain = urlparse(board_url).netloc
    
    for post in posts:
        # 기본 메타데이터 보강
        post['사이트타입'] = site_type
        post['도메인'] = domain
        post['크롤링시간'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 품질 점수 계산
        post['품질점수'] = _calculate_universal_post_quality(post)
        
        # URL 정규화
        if post.get('링크') and not post['링크'].startswith('http'):
            post['링크'] = urljoin(board_url, post['링크'])
        
        # 추가 분류
        post['게시물길이'] = len(post.get('원제목', ''))
        post['신뢰도등급'] = _classify_reliability_grade(post)
    
    return posts

def _calculate_universal_post_quality(post: Dict) -> float:
    """범용 게시물 품질 점수 계산 - 완전 구현"""
    score = 0.0
    
    # 제목 품질
    title = post.get('원제목', '')
    if 10 <= len(title) <= 150:
        score += 3.0
    elif 5 <= len(title) <= 200:
        score += 2.0
    
    # 메트릭 품질
    views = post.get('조회수', 0)
    likes = post.get('추천수', 0)
    comments = post.get('댓글수', 0)
    
    if views > 0:
        score += min(2.0, views / 100)
    if likes > 0:
        score += min(2.0, likes / 10)
    if comments > 0:
        score += min(1.0, comments / 5)
    
    # 메타데이터 완성도
    if post.get('작성자') != '익명':
        score += 1.0
    if post.get('썸네일 URL'):
        score += 1.0
    if post.get('링크') and post['링크'].startswith('http'):
        score += 1.0
    
    # 분류 신뢰도
    confidence = post.get('분류신뢰도', 0)
    score += confidence * 2
    
    return min(10.0, score)

def _classify_reliability_grade(post: Dict) -> str:
    """신뢰도 등급 분류 - 완전 구현"""
    quality = post.get('품질점수', 0)
    
    if quality >= 8.0:
        return "A"
    elif quality >= 6.0:
        return "B"
    elif quality >= 4.0:
        return "C"
    else:
        return "D"

async def _execute_intelligent_universal_crawling(crawler, board_url: str, template, 
                                                condition_checker, crawling_strategy: dict,
                                                site_type: str, start_index: int, 
                                                end_index: int, websocket=None, sort: str = "recent"):
    """지능적 범용 크롤링 실행 - 완전 구현"""
    
    all_posts = []
    matched_posts = []
    consecutive_fails = 0
    
    try:
        logger.info(f"지능적 크롤링 시작: {crawling_strategy['name']} 전략")
        
        # 크롤링 전략에 따른 실행 분기
        if crawling_strategy['method'] == 'multi_page':
            # 다중 페이지 크롤링
            all_posts = await _crawl_multiple_pages_with_conditions(
                crawler, board_url, template, condition_checker, 
                crawling_strategy['max_pages'], site_type, websocket
            )
        elif crawling_strategy['method'] == 'single_page_alternative':
            # SPA/동적 사이트 처리
            response = crawler.session.get(board_url, timeout=15)
            soup = BeautifulSoup(response.text, 'html.parser')
            all_posts = await _handle_problematic_site(
                crawler, soup, template, board_url, start_index, end_index, websocket
            )
            # 이미 범위가 적용된 결과이므로 바로 반환
            return all_posts
        else:
            # 단일 페이지 크롤링
            all_posts = await _crawl_single_page_with_conditions(
                crawler, board_url, template, condition_checker, websocket
            )
        
        if websocket:
            await websocket.send_json({
                "progress": 70,
                "status": "🔧 조건 기반 필터링 중...",
                "details": f"{len(all_posts)}개 게시물 수집 완료"
            })
        
        # 조건 기반 필터링
        for post in all_posts:
            if condition_checker:
                is_valid, reason = condition_checker.check_post_conditions(post)
                
                if is_valid:
                    matched_posts.append(post)
                    consecutive_fails = 0
                    
                    # 목표 달성시 조기 종료
                    if len(matched_posts) >= (end_index - start_index + 1) * 2:  # 여유분 포함
                        break
                else:
                    consecutive_fails += 1
                    logger.debug(f"조건 불만족: {reason}")
                
                # 중단 조건 검사
                should_stop, stop_reason = condition_checker.should_stop_crawling(
                    consecutive_fails, bool(condition_checker.start_dt and condition_checker.end_dt), site_type
                )
                
                if should_stop:
                    logger.info(f"필터링 중단: {stop_reason}")
                    break
            else:
                # 조건 검사기가 없으면 모든 게시물 포함
                matched_posts.extend(all_posts)
                break
        
        # 정렬 적용
        if matched_posts:
            matched_posts = crawler.sort_posts(matched_posts, sort)
        
        # 정확한 범위 적용
        final_posts = matched_posts[start_index-1:end_index] if start_index <= len(matched_posts) else matched_posts
        
        # 번호 재부여
        for idx, post in enumerate(final_posts):
            post['번호'] = start_index + idx
        
        # 메타데이터 보강
        final_posts = await _enhance_universal_post_metadata(final_posts, board_url, site_type)
        
        if websocket:
            await websocket.send_json({
                "progress": 100,
                "status": "✅ 범용 크롤링 완료!",
                "details": f"{len(final_posts)}개 게시물 반환 ({start_index}-{start_index+len(final_posts)-1}위)"
            })
        
        logger.info(f"지능적 크롤링 완료: {len(final_posts)}개 게시물 반환")
        return final_posts
        
    except Exception as e:
        logger.error(f"지능적 크롤링 실행 오류: {e}")
        raise

# ================================
# 🔥 메인 크롤링 함수 - 완전 구현
# ================================

async def crawl_universal_board(board_url: str, limit: int = 50, sort: str = "recent",
                         min_views: int = 0, min_likes: int = 0, min_comments: int = 0,
                         time_filter: str = "all", start_date: str = None, 
                         end_date: str = None, websocket=None, board_name: str = "",
                         enforce_date_limit: bool = False, start_index: int = 1, 
                         end_index: int = 20) -> List[Dict]:
    """🔥 강화된 조건 기반 지능적 범용 크롤링 - 완전 구현"""
    
    crawler = UniversalCrawler()
    
    try:
        logger.info(f"범용 지능적 크롤링 시작: {board_url} (범위: {start_index}-{end_index})")
        
        # 1단계: 조건 검사기 생성
        condition_checker = UniversalConditionChecker(
            min_views=min_views,
            min_likes=min_likes,
            min_comments=min_comments,
            start_date=start_date,
            end_date=end_date
        )
        
        # 2단계: 사이트 분석 및 전략 수립
        if websocket:
            await websocket.send_json({
                "progress": 5,
                "status": "🔍 사이트 구조 분석 중...",
                "details": f"목표: {start_index}-{end_index}위 게시물"
            })
        
        response = crawler.session.get(board_url, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        template, characteristics = crawler.detect_site_structure(board_url, soup)
        
        # 사이트 타입 결정
        site_type = _determine_universal_site_type(characteristics, board_url)
        
        if websocket:
            await websocket.send_json({
                "progress": 15,
                "status": f"🏗️ 사이트 분석 완료: {template.name}",
                "details": f"타입: {site_type}, 특성: {_summarize_characteristics(characteristics)}"
            })
        
        # 3단계: 크롤링 전략 결정
        crawling_strategy = await _determine_crawling_strategy(
            characteristics, condition_checker, start_index, end_index, enforce_date_limit
        )
        
        if websocket:
            await websocket.send_json({
                "progress": 25,
                "status": f"🎯 크롤링 전략: {crawling_strategy['name']}",
                "details": f"예상 페이지: {crawling_strategy['max_pages']}, 방식: {crawling_strategy['method']}"
            })
        
        # 4단계: 사이트 접근 가능성 검증
        if characteristics.get('requires_login'):
            raise Exception("이 사이트는 로그인이 필요합니다. 공개 게시판 URL을 사용해주세요.")
        
        if not characteristics.get('is_crawlable', True):
            return await _handle_problematic_site(
                crawler, soup, template, board_url, start_index, end_index, websocket
            )
        
        # 5단계: 지능적 크롤링 실행
        return await _execute_intelligent_universal_crawling(
            crawler, board_url, template, condition_checker, crawling_strategy,
            site_type, start_index, end_index, websocket, sort
        )
        
    except Exception as e:
        logger.error(f"범용 크롤링 오류: {e}")
        if websocket:
            await websocket.send_json({
                "progress": 0,
                "status": "❌ 오류 발생",
                "details": str(e)
            })
        raise Exception(f"범용 크롤링 중 오류가 발생했습니다: {str(e)}")
    
    finally:
        if hasattr(crawler, 'executor'):
            crawler.executor.shutdown(wait=False)

# ================================
# 🔥 개별 게시글 파싱 함수
# ================================

def parse_generic(url: str) -> dict:
    """개별 게시글 상세 파싱 함수"""
    try:
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        response = session.get(url, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        title_selectors = [
            "h1", "h2", ".title", "[class*='title']", ".subject", 
            "[class*='subject']", ".post-title", ".article-title",
            ".entry-title", ".page-title"
        ]
        
        title = None
        for selector in title_selectors:
            element = soup.select_one(selector)
            if element and element.get_text(strip=True):
                title = element.get_text(strip=True)
                break
        
        content_selectors = [
            ".content", "[class*='content']", ".post-body", 
            ".article-body", ".text", ".description", "article",
            ".entry-content", ".post-content", ".main-content"
        ]
        
        content = None
        for selector in content_selectors:
            element = soup.select_one(selector)
            if element and element.get_text(strip=True):
                for unwanted in element.select('.ad, .advertisement, .sidebar, nav, header, footer'):
                    unwanted.decompose()
                
                content = element.get_text(strip=True)
                break
        
        meta_info = {}
        
        date_selectors = [".date", ".time", "[class*='date']", ".created", ".published"]
        for selector in date_selectors:
            element = soup.select_one(selector)
            if element:
                meta_info['date'] = element.get_text(strip=True)
                break
        
        author_selectors = [".author", ".writer", "[class*='author']", ".byline"]
        for selector in author_selectors:
            element = soup.select_one(selector)
            if element:
                meta_info['author'] = element.get_text(strip=True)
                break
        
        return {
            "title": title or "제목을 찾을 수 없습니다",
            "content": content or "본문을 찾을 수 없습니다",
            "meta": meta_info,
            "url": url
        }
        
    except requests.exceptions.RequestException as e:
        logger.error(f"HTTP 요청 오류: {e}")
        return {
            "title": "네트워크 오류",
            "content": f"페이지를 불러올 수 없습니다: {str(e)}",
            "meta": {},
            "url": url
        }
    except Exception as e:
        logger.error(f"게시글 파싱 오류: {e}")
        return {
            "title": "파싱 실패",
            "content": f"게시글을 분석할 수 없습니다: {str(e)}",
            "meta": {},
            "url": url
        }

# ================================
# 🔥 레거시 함수들 (하위 호환성 유지)
# ================================

def crawl_generic_board(board_input: str, limit: int = 20, sort: str = "recent", 
                       min_views: int = 0, min_likes: int = 0, time_filter: str = "all", 
                       start_date: str = None, end_date: str = None) -> list:
    """
    하위 호환성을 위한 레거시 함수
    
    @deprecated: crawl_universal_board 사용을 권장합니다
    """
    logger.warning("crawl_generic_board는 deprecated됩니다. crawl_universal_board를 사용하세요.")
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(crawl_universal_board(
            board_url=board_input,
            limit=limit,
            sort=sort, 
            min_views=min_views,
            min_likes=min_likes,
            time_filter=time_filter,
            start_date=start_date,
            end_date=end_date,
            enforce_date_limit=bool(start_date and end_date)
        ))
        return result
    finally:
        loop.close()

# ================================
# 🔥 유틸리티 함수들
# ================================

def validate_url(url: str) -> bool:
    """URL 유효성 검사"""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False

def extract_domain(url: str) -> str:
    """URL에서 도메인 추출"""
    try:
        return urlparse(url).netloc.lower()
    except Exception:
        return ""

def is_same_domain(url1: str, url2: str) -> bool:
    """두 URL이 같은 도메인인지 확인"""
    return extract_domain(url1) == extract_domain(url2)

def get_supported_site_types() -> List[str]:
    """지원되는 사이트 타입 목록"""
    return [
        "포럼/커뮤니티 사이트",
        "뉴스 사이트", 
        "블로그",
        "게시판",
        "카페",
        "일반 웹사이트"
    ]

def get_common_board_patterns() -> List[str]:
    """일반적인 게시판 URL 패턴"""
    return [
        "/board/",
        "/forum/",
        "/community/",
        "/bbs/",
        "/discuss/",
        "/posts/",
        "/articles/"
    ]

def detect_board_type(url: str, soup: BeautifulSoup = None) -> str:
    """게시판 타입 감지"""
    domain = extract_domain(url).lower()
    path = urlparse(url).path.lower()
    
    # 도메인 기반 감지
    if 'cafe' in domain:
        return 'cafe'
    elif 'forum' in domain or 'board' in domain:
        return 'forum'
    elif 'news' in domain or 'press' in domain:
        return 'news'
    elif 'blog' in domain:
        return 'blog'
    
    # 경로 기반 감지
    if any(pattern in path for pattern in ['/board/', '/forum/', '/bbs/']):
        return 'forum'
    elif any(pattern in path for pattern in ['/news/', '/article/', '/post/']):
        return 'news'
    elif '/blog/' in path:
        return 'blog'
    
    return 'general'

# ================================
# 🔥 배치 처리 클래스
# ================================

class BatchProcessor:
    """배치 처리 시스템 (대량 URL 처리용)"""
    
    def __init__(self, crawler: UniversalCrawler, max_concurrent: int = 5):
        self.crawler = crawler
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
    
    async def process_urls(self, urls: List[str], **crawl_kwargs) -> List[Dict]:
        """여러 URL을 비동기로 병렬 처리"""
        tasks = []
        for url in urls:
            task = self._process_single_url(url, **crawl_kwargs)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        successful_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning(f"URL {urls[i]} 처리 실패: {result}")
            elif result:
                successful_results.extend(result)
        
        return successful_results
    
    async def _process_single_url(self, url: str, **crawl_kwargs) -> List[Dict]:
        """단일 URL 처리 (세마포어 사용)"""
        async with self.semaphore:
            try:
                return await crawl_universal_board(url, **crawl_kwargs)
            except Exception as e:
                logger.error(f"URL {url} 처리 중 오류: {e}")
                return []

class ResultPostProcessor:
    """결과 후처리 및 품질 향상"""
    
    @staticmethod
    def deduplicate_posts(posts: List[Dict], similarity_threshold: float = 0.8) -> List[Dict]:
        """중복 게시물 제거 (유사도 기반)"""
        if not posts:
            return posts
        
        unique_posts = []
        seen_signatures = set()
        
        for post in posts:
            title = post.get('원제목', '').lower().strip()
            signature = ResultPostProcessor._generate_signature(title)
            
            is_duplicate = False
            for seen_sig in seen_signatures:
                if ResultPostProcessor._calculate_similarity(signature, seen_sig) > similarity_threshold:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                seen_signatures.add(signature)
                unique_posts.append(post)
        
        logger.info(f"중복 제거: {len(posts)} -> {len(unique_posts)} 게시물")
        return unique_posts
    
    @staticmethod
    def _generate_signature(title: str) -> str:
        """게시물 시그니처 생성"""
        import re
        signature = re.sub(r'[^\w\s]', '', title)
        signature = re.sub(r'\s+', ' ', signature)
        return signature.strip()
    
    @staticmethod
    def _calculate_similarity(sig1: str, sig2: str) -> float:
        """문자열 유사도 계산 (Jaccard similarity)"""
        if not sig1 or not sig2:
            return 0.0
        
        set1 = set(sig1.split())
        set2 = set(sig2.split())
        
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        
        return intersection / union if union > 0 else 0.0
    
    @staticmethod
    def enhance_metadata(posts: List[Dict]) -> List[Dict]:
        """메타데이터 향상"""
        for post in posts:
            post['제목길이'] = len(post.get('원제목', ''))
            
            link = post.get('링크', '')
            if link:
                try:
                    domain = urlparse(link).netloc
                    post['도메인'] = domain
                except Exception:
                    post['도메인'] = '알 수 없음'
            
            post['크롤링시간'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            post['품질점수'] = ResultPostProcessor._calculate_quality_score(post)
        
        return posts
    
    @staticmethod
    def _calculate_quality_score(post: Dict) -> float:
        """게시물 품질 점수 계산"""
        score = 0.0
        
        title = post.get('원제목', '')
        if 10 <= len(title) <= 100:
            score += 2.0
        elif 5 <= len(title) <= 150:
            score += 1.0
        
        views = post.get('조회수', 0)
        likes = post.get('추천수', 0)
        comments = post.get('댓글수', 0)
        
        if views > 0:
            score += 1.0
        if likes > 0:
            score += 1.0
        if comments > 0:
            score += 1.0
        
        link = post.get('링크', '')
        if link and link.startswith('http'):
            score += 1.0
        
        content_type = post.get('콘텐츠타입', 'general')
        confidence = post.get('분류신뢰도', 0)
        
        if content_type != 'general':
            score += confidence * 2
        
        return min(10.0, score)

# ================================
# 🔥 설정 및 상수
# ================================

SUPPORTED_SORT_METHODS = [
    "recent", "popular", "recommend", "comments", 
    "confidence", "content_type"
]

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    test_url = "https://example.com"
    if validate_url(test_url):
        print(f"✅ URL 유효: {test_url}")
        print(f"🌐 도메인: {extract_domain(test_url)}")
        print(f"📋 게시판 타입: {detect_board_type(test_url)}")
    else:
        print(f"❌ URL 무효: {test_url}")
    
    # 지원 기능 출력
    print(f"\n🔧 지원되는 사이트 타입: {', '.join(get_supported_site_types())}")
    print(f"📊 지원되는 정렬 방법: {', '.join(SUPPORTED_SORT_METHODS)}")
    print(f"🔍 일반 게시판 패턴: {', '.join(get_common_board_patterns())}")

# ================================
# 🔥 완성! Universal Crawler v2.0
# ================================