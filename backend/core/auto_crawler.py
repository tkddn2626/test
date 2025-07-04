# auto_crawler.py 개선 - Universal 크롤러에 이미지/영상 추출 기능 추가

import requests
import re
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Any
import asyncio
import logging
from urllib.parse import urlparse, urljoin, quote, unquote
import time
from dataclasses import dataclass
import hashlib
from pathlib import Path
import os

# 🔥 언어팩 시스템 import 추가
from core.messages import create_localized_message

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ================================
# 🔥 Universal 미디어 추출 설정
# ================================

# 지원하는 미디어 파일 확장자
SUPPORTED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.svg', '.tiff', '.avif'}
SUPPORTED_VIDEO_EXTENSIONS = {'.mp4', '.webm', '.mov', '.avi', '.mkv', '.flv', '.wmv', '.m4v', '.ogv'}
SUPPORTED_AUDIO_EXTENSIONS = {'.mp3', '.wav', '.ogg', '.m4a', '.flac', '.aac', '.wma'}

# 미디어 호스팅 도메인들
MEDIA_HOSTING_DOMAINS = {
    # 이미지 호스팅
    'imgur.com', 'i.imgur.com', 'gyazo.com', 'i.gyazo.com',
    'prnt.sc', 'postimg.cc', 'i.postimg.cc', 'imgbb.com', 'i.imgbb.com',
    'flickr.com', 'farm1.staticflickr.com', 'farm2.staticflickr.com',
    'photobucket.com', 'tinypic.com', 'imageshack.us',
    
    # 소셜 미디어 이미지
    'pbs.twimg.com', 'scontent.cdninstagram.com', 'i.redd.it',
    'external-preview.redd.it', 'preview.redd.it',
    
    # 비디오 호스팅
    'youtube.com', 'youtu.be', 'vimeo.com', 'dailymotion.com',
    'v.redd.it', 'gfycat.com', 'streamable.com', 'streamja.com',
    
    # CDN 및 일반 호스팅
    'cdn.discordapp.com', 'media.discordapp.net', 'i.4cdn.org',
    'files.catbox.moe', 'cdn.jsdelivr.net', 'raw.githubusercontent.com'
}

# 이미지/영상을 자주 포함하는 HTML 셀렉터들
MEDIA_SELECTORS = [
    'img[src]',                          # 직접 이미지
    'video[src]', 'video source[src]',   # 비디오
    'audio[src]', 'audio source[src]',   # 오디오
    'a[href*=".jpg"]', 'a[href*=".jpeg"]', 'a[href*=".png"]',  # 이미지 링크
    'a[href*=".gif"]', 'a[href*=".webp"]', 'a[href*=".mp4"]',
    'a[href*=".webm"]', 'a[href*=".mov"]',
    '[data-src]',                        # 지연 로딩 이미지
    '[style*="background-image"]',       # CSS 배경 이미지
    '.image img', '.photo img', '.picture img',  # 클래스 기반
    '.gallery img', '.media img', '.attachment img',
    '[class*="image"] img', '[class*="photo"] img',
    '[class*="picture"] img', '[class*="media"] img'
]

class UniversalMediaExtractor:
    """Universal 사이트에서 이미지/영상 링크를 추출하는 클래스"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def extract_media_from_post(self, post: Dict) -> List[Dict]:
        """
        게시물에서 미디어 정보 추출 (4chan 스타일)
        
        Args:
            post: 크롤링된 게시물 정보
            
        Returns:
            미디어 정보 리스트 [{'type': 'image/video/audio', 'original_url': '', 'thumbnail_url': '', 'filename': ''}]
        """
        media_list = []
        
        try:
            # 1. 게시물에서 이미 추출된 미디어 URL 확인
            existing_media = self._extract_existing_media_urls(post)
            media_list.extend(existing_media)
            
            # 2. 게시물 링크에서 추가 미디어 추출
            post_url = post.get('링크', '') or post.get('원문URL', '')
            if post_url:
                page_media = self._extract_media_from_page(post_url)
                media_list.extend(page_media)
            
            # 3. 본문에서 미디어 URL 패턴 매칭
            content = post.get('본문', '')
            if content:
                content_media = self._extract_media_from_content(content)
                media_list.extend(content_media)
            
            # 4. 중복 제거 및 정리
            unique_media = self._deduplicate_media(media_list)
            
            logger.debug(f"📸 추출된 미디어: {len(unique_media)}개 (게시물: {post.get('원제목', 'Unknown')[:50]}...)")
            
            return unique_media
            
        except Exception as e:
            logger.error(f"❌ 미디어 추출 오류: {e}")
            return []
    
    def _extract_existing_media_urls(self, post: Dict) -> List[Dict]:
        """게시물에서 이미 추출된 미디어 URL들 처리"""
        media_list = []
        
        # 썸네일 URL (기존)
        thumbnail_url = post.get('썸네일 URL', '')
        if thumbnail_url and thumbnail_url.startswith('http'):
            media_info = self._create_media_info(thumbnail_url, 'thumbnail')
            if media_info:
                media_list.append(media_info)
        
        # 이미지 URL (4chan 스타일)
        image_url = post.get('이미지 URL', '')
        if image_url and image_url.startswith('http'):
            media_info = self._create_media_info(image_url, 'original')
            if media_info:
                media_list.append(media_info)
        
        return media_list
    
    def _extract_media_from_page(self, url: str) -> List[Dict]:
        """웹페이지에서 미디어 추출 (HTML 파싱)"""
        media_list = []
        
        try:
            response = self.session.get(url, timeout=10)
            if response.status_code != 200:
                return media_list
            
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # 각 미디어 셀렉터로 요소 찾기
            for selector in MEDIA_SELECTORS:
                try:
                    elements = soup.select(selector)
                    for element in elements:
                        media_info = self._extract_media_from_element(element, url)
                        if media_info:
                            media_list.append(media_info)
                except Exception as e:
                    logger.debug(f"셀렉터 {selector} 처리 실패: {e}")
            
            # Open Graph 이미지 추출
            og_media = self._extract_opengraph_media(soup, url)
            media_list.extend(og_media)
            
            # JSON-LD 미디어 추출
            jsonld_media = self._extract_jsonld_media(soup, url)
            media_list.extend(jsonld_media)
            
        except Exception as e:
            logger.debug(f"페이지 미디어 추출 실패 ({url}): {e}")
        
        return media_list
    
    def _extract_media_from_element(self, element, base_url: str) -> Optional[Dict]:
        """HTML 요소에서 미디어 정보 추출"""
        try:
            media_url = None
            
            # src 속성
            if element.has_attr('src'):
                media_url = element['src']
            
            # href 속성 (링크)
            elif element.has_attr('href'):
                media_url = element['href']
            
            # data-src 속성 (지연 로딩)
            elif element.has_attr('data-src'):
                media_url = element['data-src']
            
            # style 속성에서 background-image 추출
            elif element.has_attr('style'):
                style = element['style']
                bg_match = re.search(r'background-image:\s*url\(["\']?([^"\')]+)["\']?\)', style)
                if bg_match:
                    media_url = bg_match.group(1)
            
            if media_url:
                # 상대 URL을 절대 URL로 변환
                absolute_url = urljoin(base_url, media_url)
                return self._create_media_info(absolute_url, 'page_extracted')
            
        except Exception as e:
            logger.debug(f"요소 미디어 추출 실패: {e}")
        
        return None
    
    def _extract_media_from_content(self, content: str) -> List[Dict]:
        """텍스트 본문에서 미디어 URL 패턴 매칭"""
        media_list = []
        
        # URL 패턴들
        url_patterns = [
            # 직접 미디어 파일 URL
            r'https?://[^\s]+\.(?:jpg|jpeg|png|gif|webp|bmp|svg|mp4|webm|mov|avi|mp3|wav|ogg)\b',
            
            # 미디어 호스팅 도메인
            r'https?://(?:i\.)?imgur\.com/[^\s]+',
            r'https?://gyazo\.com/[^\s]+',
            r'https?://[^\s]*\.(?:twimg|redd|imgur)\.com/[^\s]+',
            
            # 일반적인 이미지 URL 패턴
            r'https?://[^\s]+/[^\s]*(?:image|img|photo|picture|media)[^\s]*\.[a-z]{2,4}',
        ]
        
        for pattern in url_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                url = match.group(0)
                media_info = self._create_media_info(url, 'content_extracted')
                if media_info:
                    media_list.append(media_info)
        
        return media_list
    
    def _extract_opengraph_media(self, soup, base_url: str) -> List[Dict]:
        """Open Graph 메타태그에서 미디어 추출"""
        media_list = []
        
        # Open Graph 이미지
        og_image = soup.find('meta', property='og:image')
        if og_image and og_image.get('content'):
            url = urljoin(base_url, og_image['content'])
            media_info = self._create_media_info(url, 'og_image')
            if media_info:
                media_list.append(media_info)
        
        # Open Graph 비디오
        og_video = soup.find('meta', property='og:video')
        if og_video and og_video.get('content'):
            url = urljoin(base_url, og_video['content'])
            media_info = self._create_media_info(url, 'og_video')
            if media_info:
                media_list.append(media_info)
        
        # Twitter Card 이미지
        twitter_image = soup.find('meta', attrs={'name': 'twitter:image'})
        if twitter_image and twitter_image.get('content'):
            url = urljoin(base_url, twitter_image['content'])
            media_info = self._create_media_info(url, 'twitter_image')
            if media_info:
                media_list.append(media_info)
        
        return media_list
    
    def _extract_jsonld_media(self, soup, base_url: str) -> List[Dict]:
        """JSON-LD 구조화 데이터에서 미디어 추출"""
        media_list = []
        
        jsonld_scripts = soup.find_all('script', type='application/ld+json')
        for script in jsonld_scripts:
            try:
                data = json.loads(script.string)
                
                # 이미지 추출
                images = []
                if isinstance(data, dict):
                    if 'image' in data:
                        if isinstance(data['image'], list):
                            images.extend(data['image'])
                        else:
                            images.append(data['image'])
                    
                    # 중첩된 구조에서도 이미지 찾기
                    if 'mainEntity' in data and isinstance(data['mainEntity'], dict):
                        if 'image' in data['mainEntity']:
                            images.append(data['mainEntity']['image'])
                
                for img in images:
                    img_url = img if isinstance(img, str) else img.get('url', '') if isinstance(img, dict) else ''
                    if img_url:
                        url = urljoin(base_url, img_url)
                        media_info = self._create_media_info(url, 'jsonld')
                        if media_info:
                            media_list.append(media_info)
                            
            except (json.JSONDecodeError, AttributeError):
                continue
        
        return media_list
    
    def _create_media_info(self, url: str, source_type: str) -> Optional[Dict]:
        """URL에서 미디어 정보 객체 생성 (4chan 스타일)"""
        try:
            if not url or not url.startswith('http'):
                return None
            
            # URL 정리
            clean_url = url.strip().split('?')[0]  # 쿼리 파라미터 제거
            
            # 파일 확장자 추출
            parsed = urlparse(clean_url)
            path = unquote(parsed.path)
            extension = Path(path).suffix.lower()
            
            # 미디어 타입 결정
            media_type = self._get_media_type(extension, clean_url)
            if media_type == 'unknown':
                # 확장자가 없어도 미디어 호스팅 도메인이면 허용
                if not any(domain in parsed.netloc.lower() for domain in MEDIA_HOSTING_DOMAINS):
                    return None
                media_type = 'image'  # 기본값으로 이미지 취급
            
            # 파일명 생성
            filename = self._generate_filename(url, extension, media_type)
            
            # 썸네일 URL 생성 (원본과 동일하게 설정, 4chan 스타일)
            thumbnail_url = self._generate_thumbnail_url(clean_url, media_type)
            
            return {
                'type': media_type,
                'original_url': clean_url,
                'thumbnail_url': thumbnail_url,
                'filename': filename,
                'source': source_type,
                'domain': parsed.netloc,
                'extension': extension
            }
            
        except Exception as e:
            logger.debug(f"미디어 정보 생성 실패 ({url}): {e}")
            return None
    
    def _get_media_type(self, extension: str, url: str) -> str:
        """확장자와 URL로 미디어 타입 결정"""
        if extension in SUPPORTED_IMAGE_EXTENSIONS:
            return 'image'
        elif extension in SUPPORTED_VIDEO_EXTENSIONS:
            return 'video'
        elif extension in SUPPORTED_AUDIO_EXTENSIONS:
            return 'audio'
        
        # 확장자가 없는 경우 URL 패턴으로 추정
        url_lower = url.lower()
        if any(keyword in url_lower for keyword in ['image', 'img', 'photo', 'picture', 'thumbnail']):
            return 'image'
        elif any(keyword in url_lower for keyword in ['video', 'vid', 'movie', 'film']):
            return 'video'
        elif any(keyword in url_lower for keyword in ['audio', 'sound', 'music', 'song']):
            return 'audio'
        
        return 'unknown'
    
    def _generate_filename(self, url: str, extension: str, media_type: str) -> str:
        """안전한 파일명 생성"""
        try:
            parsed = urlparse(url)
            path = unquote(parsed.path)
            
            # 기존 파일명이 있으면 사용
            if path and path != '/':
                filename = Path(path).name
                if filename and len(filename) > 1:
                    return self._sanitize_filename(filename)
            
            # URL 해시를 이용한 고유 파일명 생성
            url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
            
            # 확장자 결정
            if not extension:
                if media_type == 'image':
                    extension = '.jpg'
                elif media_type == 'video':
                    extension = '.mp4'
                elif media_type == 'audio':
                    extension = '.mp3'
                else:
                    extension = '.bin'
            
            return f"{media_type}_{url_hash}{extension}"
            
        except Exception:
            return f"media_{int(time.time())}.bin"
    
    def _generate_thumbnail_url(self, original_url: str, media_type: str) -> str:
        """썸네일 URL 생성 (4chan 스타일 - 원본과 동일)"""
        # 4chan 스타일: 썸네일 URL을 원본 이미지와 동일하게 설정
        return original_url
    
    def _sanitize_filename(self, filename: str) -> str:
        """파일명에서 위험한 문자 제거"""
        # 위험한 문자들 제거
        unsafe_chars = r'[<>:"/\\|?*\x00-\x1f]'
        safe_filename = re.sub(unsafe_chars, '_', filename)
        
        # 길이 제한
        if len(safe_filename) > 100:
            name, ext = os.path.splitext(safe_filename)
            safe_filename = name[:95] + ext
        
        return safe_filename
    
    def _deduplicate_media(self, media_list: List[Dict]) -> List[Dict]:
        """중복 미디어 제거"""
        seen_urls = set()
        unique_media = []
        
        for media in media_list:
            url = media.get('original_url', '')
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_media.append(media)
        
        return unique_media

# ================================
# 🔥 AutoCrawler 클래스 확장
# ================================

class AutoCrawler:
    """🔥 통합 자동 크롤러 (미디어 추출 기능 강화)"""
    
    def __init__(self):
        # 기존 초기화 코드...
        self.site_detector = None
        self.unified_crawler = None
        self._crawlers_cache = {}
        self._initialization_attempted = False
        
        # 🔥 Universal 미디어 추출기 추가
        self.universal_media_extractor = UniversalMediaExtractor()
        
        # 🔥 지원하는 사이트 목록에 'x' 추가
        self.supported_sites = [
            'reddit', 'lemmy', 'dcinside', 'blind', 'bbc', 'x', '4chan','universal'
        ]
        
        # 사이트별 매개변수 매핑 (기존 코드 유지)
        self.site_param_mapping = {
            'reddit': {
                'target_param': 'subreddit_name',
                'module': 'crawlers.reddit',
                'function': 'fetch_posts',
                'supported_params': [
                    'limit', 'sort', 'time_filter', 'websocket',
                    'min_views', 'min_likes', 'start_date', 'end_date',
                    'enforce_date_limit', 'start_index', 'end_index'
                ],
                'unsupported_params': ['min_comments']
            },
            'lemmy': {
                'target_param': 'community_input',
                'module': 'crawlers.lemmy',
                'function': 'crawl_lemmy_board',
                'supported_params': [
                    'limit', 'sort', 'min_views', 'min_likes',
                    'time_filter', 'start_date', 'end_date', 'websocket',
                    'enforce_date_limit', 'start_index', 'end_index'
                ],
                'unsupported_params': ['min_comments']
            },
            'dcinside': {
                'target_param': 'board_name',
                'module': 'crawlers.dcinside',
                'function': 'crawl_dcinside_board',
                'supported_params': [
                    'limit', 'sort', 'min_views', 'min_likes', 'min_comments',
                    'time_filter', 'start_date', 'end_date', 'websocket',
                    'enforce_date_limit', 'start_index', 'end_index'
                ],
                'unsupported_params': []
            },
            'blind': {
                'target_param': 'board_name',
                'module': 'crawlers.blind',
                'function': 'crawl_blind_board',
                'supported_params': [
                    'limit', 'sort', 'min_views', 'min_likes', 'min_comments',
                    'time_filter', 'start_date', 'end_date', 'websocket',
                    'enforce_date_limit', 'start_index', 'end_index'
                ],
                'unsupported_params': []
            },
            'bbc': {
                'target_param': 'board_name',
                'module': 'crawlers.bbc',
                'function': 'crawl_bbc_board',
                'supported_params': [
                    'limit', 'sort', 'min_views', 'min_likes',
                    'time_filter', 'start_date', 'end_date', 'websocket',
                    'enforce_date_limit', 'start_index', 'end_index'
                ],
                'unsupported_params': ['min_comments']
            },
            'x': {
                'target_param': 'board_name',
                'module': 'crawlers.x',
                'function': 'crawl_x_board',
                'supported_params': [
                    'limit', 'sort', 'min_views', 'min_likes', 'min_comments',
                    'time_filter', 'start_date', 'end_date', 'websocket',
                    'enforce_date_limit', 'start_index', 'end_index'
                ],
                'unsupported_params': []
            },
            '4chan': {
                'target_param': 'board_input',
                'module': 'crawlers.4chan',
                'function': 'crawl_4chan_board',
                'supported_params': [
                    'limit', 'sort', 'min_views', 'min_likes', 'min_comments',
                    'time_filter', 'start_date', 'end_date', 'websocket',
                    'enforce_date_limit', 'start_index', 'end_index'
                ],
                'unsupported_params': []
            },
            'universal': {
                'target_param': 'input_data',
                'module': 'core.auto_crawler',
                'function': 'crawl',
                'supported_params': [
                    'limit', 'sort', 'min_views', 'min_likes', 'min_comments',
                    'time_filter', 'start_date', 'end_date', 'websocket',
                    'enforce_date_limit', 'start_index', 'end_index',
                    'include_media', 'include_images', 'include_videos'  # 🔥 미디어 관련 매개변수 추가
                ],
                'unsupported_params': []
            }
        }

    async def crawl(self, input_data: str, **config) -> List[Dict]:
        """
        통합 크롤링 메인 메서드
        
        Args:
            input_data: 크롤링 대상 (게시판명, URL)
            **config: 크롤링 설정 (force_site_type 포함 가능)
        
        Returns:
            크롤링 결과 리스트
        """
        start_time = datetime.now()
        
        try:
            # 의존성 초기화
            self._initialize_dependencies()
            
            # 1. 사이트 감지 - force_site_type이 있으면 사용 (재감지 방지)
            force_applied = False
            if 'force_site_type' in config:
                site_type = config.pop('force_site_type')
                force_applied = True
                logger.info(f"🎯 강제 지정된 사이트: {site_type}")
            else:
                site_type = await self._detect_site_type(input_data)
                logger.info(f"🔍 자동 감지된 사이트: {site_type}")
            
            # 2. 게시판 식별자 추출
            board_identifier = self._extract_board_identifier(input_data, site_type)
            logger.info(f"📋 게시판 식별자: {board_identifier}")
            
            # 3. 크롤링 설정 준비
            crawl_config = self._prepare_crawl_config(site_type, board_identifier, **config)
            
            # 4. 크롤링 실행
            try:
                logger.info(f"🚀 AutoCrawler 크롤링 실행: {site_type}")
                results = await self._execute_crawl(site_type, **crawl_config)
            except Exception as e:
                if force_applied:
                    logger.error(f"❌ force_site_type={site_type} 크롤링 실패, 폴백 금지")
                    raise e
                
                # 기존 로직: 자동 감지된 경우에만 폴백 허용
                logger.warning(f"AutoCrawler 실패, 통합 크롤러로 폴백: {e}")
                if self.unified_crawler:
                    logger.info(f"🚀 통합 크롤링 폴백 실행: {site_type}")
                    results = await self.unified_crawler.unified_crawl(
                        site_type, 
                        board_identifier, 
                        **crawl_config
                    )
                else:
                    raise e
            
            # 5. 결과 후처리
            processed_results = self._post_process_results(results, site_type, config)
            
            elapsed = (datetime.now() - start_time).total_seconds()
            logger.info(f"✅ 크롤링 완료: {len(processed_results)}개 결과 ({elapsed:.2f}초)")
            
            return processed_results
                
        except Exception as e:
            elapsed = (datetime.now() - start_time).total_seconds()
            logger.error(f"❌ AutoCrawler 오류 ({elapsed:.2f}초): {e}")
            raise

    def _initialize_dependencies(self):
        """의존성들을 지연 로드 (한 번만 시도)"""
        if self._initialization_attempted:
            return
        
        self._initialization_attempted = True
        
        try:
            # SiteDetector 로드
            from .site_detector import SiteDetector
            self.site_detector = SiteDetector()
            logger.info("✅ SiteDetector 로드 성공")
        except ImportError as e:
            logger.warning(f"⚠️ SiteDetector 로드 실패: {e}")
            self.site_detector = None
        
        try:
            # UnifiedCrawler 로드 (선택적)
            from .unified_crawler import unified_crawler
            self.unified_crawler = unified_crawler
            logger.info("✅ UnifiedCrawler 로드 성공")
        except ImportError as e:
            logger.warning(f"⚠️ UnifiedCrawler 로드 실패 (폴백 사용): {e}")
            self.unified_crawler = None

    def _is_dynamic_site(self, url: str) -> bool:
        """동적 사이트 감지 (JavaScript 기반)"""
        dynamic_patterns = [
            'imginn.com', 'picuki.com', 'instagram.com',
            'tiktok.com', 'twitter.com', 'x.com',
            'youtube.com', 'facebook.com', 'pinterest.com'
        ]
        return any(pattern in url.lower() for pattern in dynamic_patterns)
    
    async def _try_dynamic_crawling(self, url: str) -> List[Dict]:
        """동적 크롤링 시도 (Playwright 우선, Selenium 폴백)"""
        
        # 1. Playwright 시도
        try:
            from playwright.async_api import async_playwright
            
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                
                await page.goto(url, wait_until='domcontentloaded')
                await page.wait_for_timeout(5000)  # 5초 대기
                
                # 이미지 추출
                images = await page.query_selector_all('img[src]')
                results = []
                
                for i, img in enumerate(images[:20]):  # 최대 20개
                    src = await img.get_attribute('src')
                    alt = await img.get_attribute('alt') or f'Image {i+1}'
                    
                    if src and src.startswith('http'):
                        results.append({
                            '번호': str(i + 1),
                            '원제목': alt,
                            '번역제목': '',
                            '링크': url,
                            '원문URL': url,
                            '이미지 URL': src,
                            '썸네일 URL': src,
                            '본문': alt,
                            '조회수': 0, '추천수': 0, '댓글수': 0,
                            '작성일': '', '작성자': '',
                            '사이트': urlparse(url).netloc,
                            '미디어타입': 'image',
                            '미디어개수': 1,
                            '크롤링방식': 'AutoCrawler-Dynamic-Playwright',
                            '플랫폼': 'universal'
                        })
                
                await browser.close()
                logger.info(f"✅ Playwright 동적 크롤링 성공: {len(results)}개")
                return results
                
        except ImportError:
            logger.debug("Playwright 없음, Selenium 시도")
        except Exception as e:
            logger.debug(f"Playwright 실패: {e}")
        
        # 2. Selenium 시도
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.common.by import By
            import time
            
            options = Options()
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            
            driver = webdriver.Chrome(options=options)
            driver.get(url)
            time.sleep(5)  # 5초 대기
            
            images = driver.find_elements(By.TAG_NAME, "img")
            results = []
            
            for i, img in enumerate(images[:20]):
                src = img.get_attribute('src')
                alt = img.get_attribute('alt') or f'Image {i+1}'
                
                if src and src.startswith('http'):
                    results.append({
                        '번호': str(i + 1),
                        '원제목': alt,
                        '번역제목': '',
                        '링크': url,
                        '원문URL': url,
                        '이미지 URL': src,
                        '썸네일 URL': src,
                        '본문': alt,
                        '조회수': 0, '추천수': 0, '댓글수': 0,
                        '작성일': '', '작성자': '',
                        '사이트': urlparse(url).netloc,
                        '미디어타입': 'image',
                        '미디어개수': 1,
                        '크롤링방식': 'AutoCrawler-Dynamic-Selenium',
                        '플랫폼': 'universal'
                    })
            
            driver.quit()
            logger.info(f"✅ Selenium 동적 크롤링 성공: {len(results)}개")
            return results
            
        except ImportError:
            logger.debug("Selenium 없음")
        except Exception as e:
            logger.debug(f"Selenium 실패: {e}")
        
        return []
    
    async def _detect_site_type(self, input_data: str) -> str:
        """사이트 타입 감지"""
        if self.site_detector:
            try:
                return await self.site_detector.detect_site_type(input_data)
            except Exception as e:
                logger.warning(f"SiteDetector 오류, 폴백 사용: {e}")
        
        # 폴백 사이트 감지
        return self._fallback_site_detection(input_data)
    
    def _extract_board_identifier(self, input_data: str, site_type: str) -> str:
        """게시판 식별자 추출"""
        if self.site_detector:
            try:
                return self.site_detector.extract_board_identifier(input_data, site_type)
            except Exception as e:
                logger.warning(f"식별자 추출 오류, 원본 사용: {e}")
        
        # 폴백: 간단한 식별자 추출
        return self._fallback_extract_identifier(input_data, site_type)
    
    def _fallback_site_detection(self, input_data: str) -> str:
        """폴백 사이트 감지"""
        input_lower = input_data.lower()
        
        # URL 기반 감지
        if input_data.startswith('http'):
            parsed = urlparse(input_data)
            domain = parsed.netloc.lower()
            
            if 'reddit.com' in domain:
                return 'reddit'
            elif 'x.com' in domain or 'twitter.com' in domain:
                return 'x'
            elif any(chan_domain in domain for chan_domain in ['4chan.org', '4channel.org', 'boards.4chan']):
                return '4chan'
            elif 'dcinside.com' in domain:
                return 'dcinside'
            elif 'teamblind.com' in domain or 'blind.com' in domain:
                return 'blind'
            elif 'bbc.com' in domain or 'bbc.co.uk' in domain:
                return 'bbc'
            elif any(lemmy_domain in domain for lemmy_domain in ['lemmy.', 'beehaw.', 'sh.itjust.works']):
                return 'lemmy'
            else:
                logger.info(f"🌐 Universal 사이트로 감지: {input_data}")
                return 'universal'
        
        # 키워드 기반 감지
        if any(word in input_lower for word in ['reddit', 'subreddit']):
            return 'reddit'
        elif any(word in input_lower for word in ['lemmy', '레미']):
            return 'lemmy'
        elif any(word in input_lower for word in ['dcinside', 'dc', '디시', '갤러리']):
            return 'dcinside'
        elif any(word in input_lower for word in ['blind', '블라인드']):
            return 'blind'
        elif any(word in input_lower for word in ['bbc', 'british']):
            return 'bbc'
        elif any(word in input_lower for word in ['x.com', 'twitter.com', 'tweet', '@']) or input_lower == 'x':
            return 'x'
        elif any(word in input_lower for word in ['4chan', '4channel', 'imageboard', '/g/', '/v/', '/a/', '/pol/']):
            return '4chan'
        else:
            logger.info(f"🌐 키워드 매칭 실패, Universal로 처리: {input_data}")
            return 'universal'
    
    def _fallback_extract_identifier(self, input_data: str, site_type: str) -> str:
        """폴백 식별자 추출"""
        if site_type == 'reddit' and '/r/' in input_data:
            import re
            match = re.search(r'/r/([^/]+)', input_data)
            return match.group(1) if match else input_data
        elif site_type == 'lemmy' and '/c/' in input_data:
            parts = input_data.split('/c/')
            if len(parts) > 1:
                from urllib.parse import urlparse
                try:
                    domain = urlparse(input_data).netloc
                    community = parts[1].split('/')[0]
                    return f"{community}@{domain}"
                except:
                    pass
        elif site_type == 'dcinside' and '?id=' in input_data:
            import re
            match = re.search(r'[?&]id=([^&]+)', input_data)
            return match.group(1) if match else input_data
        
        elif site_type == '4chan':
            import re
            # https://boards.4chan.org/a/ → a
            # https://boards.4chan.org/g/thread/12345 → g
            match = re.search(r'(?:4chan\.org|4channel\.org)/([a-z0-9]+)', input_data)
            if match:
                return match.group(1)  # 게시판명 (a, g, v 등)
            else:
                return input_data  # 게시판명만 입력된 경우
        
        return input_data
    
    def _prepare_crawl_config(self, site_type: str, board_identifier: str, **config) -> Dict[str, Any]:
        """사이트별 크롤링 설정 준비"""
        if site_type not in self.site_param_mapping:
            raise ValueError(f"지원하지 않는 사이트: {site_type}")
        
        site_config = self.site_param_mapping[site_type]
        
        # 기본 설정
        crawl_config = {
            site_config['target_param']: board_identifier
        }
        
        # 지원하는 매개변수만 추가
        for param in site_config['supported_params']:
            if param in config and config[param] is not None:
                crawl_config[param] = config[param]
        
        # 공통 매개변수 매핑
        common_mappings = {
            'start': 'start_index',
            'end': 'end_index',
            'board': site_config['target_param'],
            'input': site_config['target_param'],
            'board_identifier': site_config['target_param']
        }
        
        for source, target in common_mappings.items():
            if source in config and target in site_config['supported_params']:
                crawl_config[target] = config[source]
        
        # 사이트별 특수 처리
        crawl_config = self._apply_site_specific_processing(site_type, crawl_config, **config)
        
        # 지원하지 않는 매개변수 제거 및 경고
        unsupported = site_config['unsupported_params']
        for param in unsupported:
            if param in crawl_config:
                removed_value = crawl_config.pop(param)
                logger.warning(f"⚠️ {site_type}에서 지원하지 않는 매개변수 제거: {param}={removed_value}")
        
        # None 값 제거
        crawl_config = {k: v for k, v in crawl_config.items() if v is not None}
        
        logger.debug(f"크롤링 설정 준비 완료 ({site_type}): {list(crawl_config.keys())}")
        return crawl_config
    
    def _apply_site_specific_processing(self, site_type: str, config: Dict, **original_config) -> Dict:
        """사이트별 특수 처리"""
        
        if site_type == 'reddit':
            # Reddit 정렬 방식 매핑
            sort_mapping = {
                "popular": "hot", "recommend": "top", "recent": "new",
                "comments": "top"
            }
            if 'sort' in config and config['sort'] in sort_mapping:
                config['sort'] = sort_mapping[config['sort']]
                
            # Reddit은 subreddit 이름에서 /r/ 제거
            if 'subreddit_name' in config:
                subreddit = config['subreddit_name']
                if subreddit.startswith('/r/'):
                    config['subreddit_name'] = subreddit[3:]
                elif subreddit.startswith('r/'):
                    config['subreddit_name'] = subreddit[2:]
        
        elif site_type == 'lemmy':
            # Lemmy 커뮤니티 형식 처리
            if 'community_input' in config:
                community = config['community_input']
                if '@' not in community and not community.startswith('http'):
                    # 인스턴스가 없으면 기본값 추가
                    config['community_input'] = f"{community}@lemmy.world"
        
        elif site_type == 'bbc':
            # BBC는 board_name이 빈 문자열로 필요할 수 있음
            if 'board_name' not in config:
                config['board_name'] = ""
        
        elif site_type == 'universal':
            # Universal도 board_name 처리
            if 'board_name' not in config:
                config['board_name'] = ""
        
        return config
    
    async def _execute_crawl(self, site_type: str, **config) -> List[Dict]:
        """크롤링 실행"""
        if site_type == 'universal':
            # Universal 크롤링은 AutoCrawler 내부에서 직접 처리
            return await self._crawl_universal_internal(**config)
        else:
            # 다른 사이트는 직접 크롤러 호출
            return await self._direct_crawl(site_type, **config)
    
    async def _crawl_universal_internal(self, **config) -> List[Dict]:
        """Universal 크롤링 내부 구현 (동적 사이트 지원 추가)"""
        board_url = config.get('input_data', '') or config.get('board_url', '')
        include_media = config.get('include_media', True)
        
        if not board_url:
            logger.warning("Universal 크롤링: URL이 제공되지 않음")
            return []
        
        # URL 정규화
        if not board_url.startswith('http'):
            board_url = 'https://' + board_url
        
        logger.info(f"🌐 Universal 크롤링 시작: {board_url}")
        
        # 🔥 동적 사이트 감지 및 처리
        if self._is_dynamic_site(board_url):
            logger.info(f"🎯 동적 사이트 감지: {urlparse(board_url).netloc}")
            
            # 동적 크롤링 시도
            try:
                dynamic_results = await self._try_dynamic_crawling(board_url)
                if dynamic_results:
                    return dynamic_results
                else:
                    logger.warning("⚠️ 동적 크롤링 실패, 정적 방식으로 폴백")
            except Exception as e:
                logger.warning(f"⚠️ 동적 크롤링 오류: {e}, 정적 방식으로 폴백")
        
        try:
            # 기존 정적 크롤링 로직
            import requests
            from bs4 import BeautifulSoup
            import re
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            logger.info(f"📡 정적 크롤링 요청: {board_url}")
            
            response = requests.get(board_url, headers=headers, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # 일반적인 링크 패턴 찾기
            results = []
            
            # 다양한 셀렉터로 링크 찾기
            selectors = [
                'a[href]',  # 모든 링크
                'h1 a, h2 a, h3 a, h4 a',  # 제목 링크
                '.title a, .headline a, .article-title a',  # 클래스 기반
                '[class*="title"] a, [class*="headline"] a'  # 부분 클래스 매칭
            ]
            
            all_links = []
            for selector in selectors:
                links = soup.select(selector)
                all_links.extend(links)
            
            # 중복 제거 (href 기준)
            seen_hrefs = set()
            unique_links = []
            for link in all_links:
                href = link.get('href')
                if href and href not in seen_hrefs:
                    seen_hrefs.add(href)
                    unique_links.append(link)
            
            logger.info(f"🔗 발견된 고유 링크: {len(unique_links)}개")
            
            # 제목이 될 수 있는 요소들 처리
            for i, link in enumerate(unique_links[:config.get('limit', 20)]):
                href = link.get('href')
                if not href:
                    continue
                    
                # 상대 URL을 절대 URL로 변환
                full_url = urljoin(board_url, href)
                
                # 링크 텍스트 추출
                title = link.get_text(strip=True)
                
                # 제목이 너무 짧거나 의미없는 경우 스킵
                if not title or len(title) < 5:
                    continue
                
                # 공통적으로 제외할 텍스트들
                skip_patterns = ['more', 'read more', '더보기', 'click here', '클릭', 'home', 'menu']
                if any(pattern in title.lower() for pattern in skip_patterns):
                    continue
                
                # 🔥 기본 정보 추출 및 미디어 추출
                result = {
                    '번호': str(i + 1),
                    '원제목': title,
                    '번역제목': '',
                    '링크': full_url,
                    '원문URL': full_url,
                    '본문': '',
                    '조회수': 0,
                    '추천수': 0,
                    '댓글수': 0,
                    '작성일': '',
                    '작성자': '',
                    '사이트': urlparse(board_url).netloc,
                    '크롤링방식': 'AutoCrawler-Universal-Enhanced',
                    '플랫폼': 'universal'
                }
                
                # 🔥 미디어 추출 및 추가 (4chan 스타일)
                if include_media:
                    try:
                        media_list = self.universal_media_extractor.extract_media_from_post(result)
                        if media_list:
                            # 첫 번째 미디어를 대표 이미지로 설정
                            first_media = media_list[0]
                            result['이미지 URL'] = first_media['original_url']
                            result['썸네일 URL'] = first_media['thumbnail_url']
                            result['파일명'] = first_media['filename']
                            result['미디어타입'] = first_media['type']
                            result['미디어개수'] = len(media_list)
                            
                            logger.debug(f"📸 미디어 추출 완료: {len(media_list)}개 ({title[:30]}...)")
                        else:
                            # 미디어가 없는 경우 기본값
                            result['이미지 URL'] = ""
                            result['썸네일 URL'] = ""
                            result['파일명'] = ""
                            result['미디어타입'] = ""
                            result['미디어개수'] = 0
                    except Exception as e:
                        logger.warning(f"⚠️ 미디어 추출 실패 ({title[:30]}...): {e}")
                        result['이미지 URL'] = ""
                        result['썸네일 URL'] = ""
                        result['미디어개수'] = 0
                
                results.append(result)
            
            logger.info(f"✅ Universal 크롤링 완료: {len(results)}개 링크")
            
            if include_media:
                media_count = sum(1 for r in results if r.get('미디어개수', 0) > 0)
                logger.info(f"🖼️ 미디어 포함 게시물: {media_count}/{len(results)}개")
            
            if not results:
                logger.warning(f"⚠️ {board_url}에서 유효한 링크를 찾을 수 없습니다")
            
            return results
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Universal 크롤링 네트워크 오류: {e}")
            return []
        except Exception as e:
            logger.error(f"❌ Universal 크롤링 오류: {e}")
            return []

    async def _direct_crawl(self, site_type: str, **config) -> List[Dict]:
        """직접 크롤러 호출 (폴백)"""
        site_config = self.site_param_mapping[site_type]
        module_name = site_config['module']
        function_name = site_config['function']
        
        if not module_name:
            raise ValueError(f"모듈이 지정되지 않은 사이트: {site_type}")
        
        try:
            # 크롤러 모듈을 캐시에서 가져오거나 새로 로드
            if module_name not in self._crawlers_cache:
                crawler_module = __import__(module_name, fromlist=[function_name])
                crawler_function = getattr(crawler_module, function_name)
                self._crawlers_cache[module_name] = crawler_function
                logger.debug(f"크롤러 모듈 로드: {module_name}.{function_name}")
            
            crawler_function = self._crawlers_cache[module_name]
            
            # 크롤링 실행
            if asyncio.iscoroutinefunction(crawler_function):
                result = await crawler_function(**config)
            else:
                result = crawler_function(**config)
            
            return result or []
                
        except ImportError as e:
            logger.error(f"크롤러 모듈 import 실패 ({site_type}): {e}")
            return []
        except Exception as e:
            logger.error(f"직접 크롤링 오류 ({site_type}): {e}")
            raise
    
    def _post_process_results(self, results: List[Dict], site_type: str, config: Dict) -> List[Dict]:
        """결과 후처리"""
        if not results:
            return []
        
        processed_results = []
        
        for result in results:
            # 기본 필드 정규화
            normalized_result = self._normalize_result_fields(result, site_type)
            
            # 추가 후처리
            if config.get('translate', False):
                # 번역 관련 처리는 여기서 수행하지 않음 (상위 레벨에서 처리)
                pass
            
            processed_results.append(normalized_result)
        
        # 정렬 및 필터링
        processed_results = self._apply_final_filters(processed_results, config)
        
        return processed_results
    
    def _normalize_result_fields(self, result: Dict, site_type: str) -> Dict:
        """결과 필드 정규화"""
        # 이미 정규화된 결과라면 그대로 반환
        if all(key in result for key in ['원제목', '링크', '작성일']):
            return result
        
        # 사이트별 필드 매핑 (필요한 경우)
        normalized = result.copy()
        
        # 기본 필드들이 없는 경우 빈 값으로 설정
        default_fields = {
            '번호': '',
            '원제목': '',
            '번역제목': '',
            '링크': '',
            '본문': '',
            '조회수': 0,
            '추천수': 0,
            '댓글수': 0,
            '작성일': ''
        }
        
        for field, default_value in default_fields.items():
            if field not in normalized:
                normalized[field] = default_value
        
        return normalized
    
    def _apply_final_filters(self, results: List[Dict], config: Dict) -> List[Dict]:
        """최종 필터링 및 정렬"""
        filtered_results = results
        
        # 범위 필터링
        start_index = config.get('start_index', config.get('start', 1))
        end_index = config.get('end_index', config.get('end', len(results)))
        
        if start_index > 1 or end_index < len(results):
            # 1-based index를 0-based로 변환
            start_idx = max(0, start_index - 1)
            end_idx = min(len(results), end_index)
            filtered_results = filtered_results[start_idx:end_idx]
        
        return filtered_results

    def get_universal_media_extractor_info(self) -> Dict[str, Any]:
        """Universal 미디어 추출기 정보 반환"""
        return {
            'supported_image_extensions': list(SUPPORTED_IMAGE_EXTENSIONS),
            'supported_video_extensions': list(SUPPORTED_VIDEO_EXTENSIONS),
            'supported_audio_extensions': list(SUPPORTED_AUDIO_EXTENSIONS),
            'media_hosting_domains': list(MEDIA_HOSTING_DOMAINS),
            'media_selectors': MEDIA_SELECTORS,
            'extraction_methods': [
                'existing_urls',  # 게시물에 이미 있는 URL
                'page_parsing',   # HTML 페이지 파싱
                'content_regex',  # 본문 정규표현식 매칭
                'opengraph',      # Open Graph 메타태그
                'jsonld',         # JSON-LD 구조화 데이터
                'css_background'  # CSS 배경 이미지
            ],
            'features': [
                '4chan_style_image_extraction',
                'automatic_thumbnail_generation', 
                'multiple_media_types_support',
                'deduplication',
                'safe_filename_generation'
            ]
        }

# ================================
# 🔥 Universal 크롤러를 위한 미디어 추출 함수 (media_download.py 호환)
# ================================

def extract_universal_media(post: Dict) -> List[Dict]:
    """
    Universal 크롤러 게시물에서 미디어 추출
    media_download.py의 동적 추출기 시스템과 호환되는 함수
    
    Args:
        post: 크롤링된 게시물 정보
        
    Returns:
        미디어 정보 리스트 (media_download.py 형식)
    """
    try:
        # UniversalMediaExtractor 인스턴스 생성
        extractor = UniversalMediaExtractor()
        
        # 미디어 추출
        media_list = extractor.extract_media_from_post(post)
        
        # media_download.py 형식으로 변환
        converted_media = []
        for media in media_list:
            converted = {
                'type': media['type'],
                'original_url': media['original_url'],
                'thumbnail_url': media['thumbnail_url'],
                'filename': media['filename'],
                'source': f"universal_{media['source']}",
                'title': post.get('원제목', ''),
                'post_url': post.get('링크', ''),
                'domain': media.get('domain', ''),
                'extension': media.get('extension', ''),
                'post_number': post.get('번호', ''),
                'site_type': 'universal'
            }
            converted_media.append(converted)
        
        logger.debug(f"📸 Universal 미디어 추출: {len(converted_media)}개")
        return converted_media
        
    except Exception as e:
        logger.error(f"❌ Universal 미디어 추출 실패: {e}")
        return []

# ================================
# 🔥 메인 크롤링 함수 업데이트
# ================================

async def crawl_universal_with_media(input_data: str, limit: int = 50, sort: str = "recent",
                                   min_views: int = 0, min_likes: int = 0, min_comments: int = 0,
                                   start_date: str = None, end_date: str = None,
                                   include_media: bool = True, include_images: bool = True, 
                                   include_videos: bool = True, include_audio: bool = False,
                                   time_filter: str = None,
                                   websocket=None, start_index: int = 1, end_index: int = 20, 
                                   user_lang: str = "en") -> List[Dict]:
    """
    Universal 크롤링 + 미디어 추출 통합 함수
    
    Args:
        input_data: 크롤링할 URL
        include_media: 미디어 추출 여부
        include_images: 이미지 포함 여부
        include_videos: 비디오 포함 여부  
        include_audio: 오디오 포함 여부
        ... (기타 매개변수들)
    
    Returns:
        미디어 정보가 포함된 게시물 리스트
    """
    
    crawler = AutoCrawler()
    
    try:
        logger.info(f"🌐 Universal 미디어 크롤링 시작: {input_data}")
        
        if websocket:
            message = create_localized_message(
                progress=20,
                status_key="crawlingProgress.site_connecting",
                lang=user_lang,
                status_data={"site": "Universal"}
            )
            await websocket.send_json(message)
        
        # 크롤링 설정
        config = {
            'input_data': input_data,
            'limit': max(end_index + 10, limit),
            'include_media': include_media,
            'include_images': include_images,
            'include_videos': include_videos,
            'include_audio': include_audio
        }
        
        # Universal 크롤링 실행
        posts = await crawler._crawl_universal_internal(**config)
        
        if not posts:
            error_msg = f"""
Universal 크롤링에서 게시물을 찾을 수 없습니다: {input_data}

가능한 원인:
1. 웹사이트에 접근할 수 없음
2. 링크나 콘텐츠가 없는 페이지
3. 동적 로딩이나 JavaScript가 필요한 사이트
4. 로봇 차단 (robots.txt, Cloudflare 등)

권장사항:
• 완전한 URL을 입력하세요 (https:// 포함)
• 정적 콘텐츠가 있는 사이트를 사용하세요
• 포럼, 블로그, 뉴스 사이트 등이 적합합니다
            """
            raise Exception(error_msg.strip())
        
        if websocket:
            message = create_localized_message(
                progress=80,
                status_key="crawlingProgress.media_processing",
                lang=user_lang
            )
            await websocket.send_json(message)
        
        # 미디어 필터링
        if include_media:
            filtered_posts = []
            for post in posts:
                media_count = post.get('미디어개수', 0)
                media_type = post.get('미디어타입', '')
                
                # 미디어 타입별 필터링
                include_post = True
                if media_count > 0:
                    if media_type == 'image' and not include_images:
                        include_post = False
                    elif media_type == 'video' and not include_videos:
                        include_post = False
                    elif media_type == 'audio' and not include_audio:
                        include_post = False
                
                if include_post:
                    filtered_posts.append(post)
            
            posts = filtered_posts
        
        # 범위 적용
        if posts and len(posts) >= end_index:
            posts = posts[start_index-1:end_index]
            
            # 번호 재부여
            for idx, post in enumerate(posts):
                post['번호'] = start_index + idx
        
        logger.info(f"✅ Universal 미디어 크롤링 완료: {len(posts)}개 게시물")
        
        if include_media:
            media_posts = sum(1 for p in posts if p.get('미디어개수', 0) > 0)
            logger.info(f"🖼️ 미디어 포함 게시물: {media_posts}/{len(posts)}개")
        
        return posts
        
    except Exception as e:
        logger.error(f"❌ Universal 미디어 크롤링 오류: {e}")
        raise

# ================================
# 🔥 기존 호환성 함수들 (프로젝트 파일과 호환)
# ================================

async def validate_crawl_request(input_data: str, **config) -> Tuple[bool, List[str]]:
    """크롤링 요청 유효성 검사 (기존 코드 호환)"""
    crawler = AutoCrawler()
    return await crawler.validate_crawl_request(input_data, **config)

def get_site_help_info(site_type: str) -> Dict[str, Any]:
    """사이트별 도움말 정보 반환 (기존 코드 호환)"""
    crawler = AutoCrawler()
    return crawler.get_site_help_info(site_type)

def get_supported_sites() -> List[str]:
    """지원하는 사이트 목록 반환 (기존 코드 호환)"""
    return AutoCrawler().supported_sites

# ================================
# 🔥 추가된 유효성 검사 메서드들 (누락된 코드 복원)
# ================================

async def validate_crawl_request(self, input_data: str, **config) -> Tuple[bool, List[str]]:
    """크롤링 요청 유효성 검사"""
    errors = []
    
    try:
        # 1. 입력 데이터 검증
        if not input_data or not input_data.strip():
            errors.append("크롤링 대상이 입력되지 않았습니다")
            return False, errors
        
        # 2. 사이트 감지
        site_type = await self._detect_site_type(input_data)
        if site_type not in self.supported_sites:
            errors.append(f"지원하지 않는 사이트입니다: {site_type}")
            return False, errors
        
        # 3. 매개변수 검증
        is_valid, param_errors = self._validate_parameters(site_type, **config)
        if not is_valid:
            errors.extend(param_errors)
        
        # 4. 범위 검증
        start_index = config.get('start_index', config.get('start', 1))
        end_index = config.get('end_index', config.get('end', 20))
        
        if start_index < 1:
            errors.append("시작 인덱스는 1 이상이어야 합니다")
        if end_index < start_index:
            errors.append("끝 인덱스는 시작 인덱스보다 크거나 같아야 합니다")
        if end_index - start_index > 100:
            errors.append("한 번에 최대 100개까지만 크롤링할 수 있습니다")
        
        return len(errors) == 0, errors
        
    except Exception as e:
        errors.append(f"유효성 검사 중 오류: {e}")
        return False, errors

def _validate_parameters(self, site_type: str, **config) -> Tuple[bool, List[str]]:
    """매개변수 유효성 검사"""
    errors = []
    
    if site_type not in self.site_param_mapping:
        errors.append(f"매개변수 정보가 없는 사이트: {site_type}")
        return False, errors
    
    site_config = self.site_param_mapping[site_type]
    unsupported_params = site_config['unsupported_params']
    
    # 지원하지 않는 매개변수 검사
    for param in unsupported_params:
        if param in config and config[param] is not None:
            errors.append(f"{site_type}에서 지원하지 않는 매개변수: {param}")
    
    # 값 범위 검사
    if 'limit' in config:
        limit = config['limit']
        if not isinstance(limit, int) or limit < 1 or limit > 200:
            errors.append("limit은 1-200 사이의 정수여야 합니다")
    
    # 날짜 형식 검사
    for date_param in ['start_date', 'end_date']:
        if date_param in config and config[date_param]:
            try:
                datetime.strptime(config[date_param], "%Y-%m-%d")
            except ValueError:
                errors.append(f"{date_param}는 YYYY-MM-DD 형식이어야 합니다")
    
    return len(errors) == 0, errors

def get_site_help_info(self, site_type: str) -> Dict[str, Any]:
    """사이트별 도움말 정보 반환"""
    if site_type not in self.supported_sites:
        raise ValueError(f"지원하지 않는 사이트: {site_type}")
    
    site_config = self.site_param_mapping[site_type]
    
    help_info = {
        'reddit': {
            'format': 'subreddit_name or /r/subreddit_name or full URL',
            'examples': ['python', '/r/programming', 'https://reddit.com/r/askreddit'],
            'notes': 'Reddit 서브레딧 이름 또는 URL을 입력하세요'
        },
        'lemmy': {
            'format': 'community@instance or full URL',
            'examples': ['technology@lemmy.world', 'asklemmy@lemmy.ml', 'https://lemmy.world/c/technology'],
            'notes': '인스턴스가 없으면 자동으로 @lemmy.world가 추가됩니다'
        },
        'dcinside': {
            'format': 'gallery_name or gallery_id or full URL',
            'examples': ['programming', '프로그래밍', 'https://gall.dcinside.com/board/lists/?id=programming'],
            'notes': '갤러리 ID 또는 이름을 입력하세요'
        },
        'blind': {
            'format': 'topic_name or full URL',
            'examples': ['회사생활', '개발자', 'https://www.teamblind.com/kr/topics/회사생활'],
            'notes': '토픽 이름을 입력하세요'
        },
        'bbc': {
            'format': 'section_url',
            'examples': ['https://www.bbc.com/news', 'https://www.bbc.com/technology'],
            'notes': 'BBC 섹션 URL을 입력하세요'
        },
        'x': {
            'format': 'username or hashtag or full URL',
            'examples': ['@username', '#hashtag', 'https://x.com/username'],
            'notes': 'X(Twitter) 사용자명이나 해시태그를 입력하세요'
        },
        '4chan': {
            'format': 'board_name or full URL',
            'examples': ['g', 'a', 'pol', 'https://boards.4chan.org/g/'],
            'notes': '4chan 게시판 이름을 입력하세요 (예: g, a, v, pol)'
        },
        'universal': {
            'format': 'full_url',
            'examples': ['https://example.com/forum', 'https://news.site.com'],
            'notes': '완전한 URL을 입력하세요. AutoCrawler가 자동으로 링크를 추출합니다.'
        }
    }
    
    base_help = help_info.get(site_type, {
        'format': 'site_specific_input',
        'examples': ['example'],
        'notes': '사이트별 형식을 확인하세요'
    })
    
    # 매개변수 정보 추가
    base_help.update({
        'target_parameter': site_config['target_param'],
        'supported_parameters': site_config['supported_params'],
        'unsupported_parameters': site_config['unsupported_params'],
        'module_info': {
            'module': site_config['module'] or 'AutoCrawler Internal',
            'function': site_config['function']
        }
    })
    
    return base_help

# ================================
# 🔥 모듈 메타데이터 (media_download.py 동적 탐지용)
# ================================

# Universal 크롤러 미디어 추출기 정보
UNIVERSAL_MEDIA_EXTRACTOR_INFO = {
    'name': 'Universal Media Extractor',
    'version': '1.0.0',
    'description': 'Universal 사이트 미디어 추출기 (4chan 스타일)',
    'supported_sites': ['universal'],
    'supported_media_types': ['image', 'video', 'audio'],
    'extraction_function': extract_universal_media,
    'features': [
        'html_parsing',
        'opengraph_extraction', 
        'jsonld_extraction',
        'css_background_extraction',
        'content_regex_matching',
        'automatic_deduplication'
    ]
}

# media_download.py가 이 함수를 자동으로 찾을 수 있도록 함수명 표준화
def get_media_from_post(post: Dict) -> List[Dict]:
    """media_download.py 표준 인터페이스"""
    return extract_universal_media(post)

# ================================
# 🔥 메인 실행부
# ================================

if __name__ == "__main__":
    import asyncio
    
    # 로깅 레벨 설정
    logging.getLogger().setLevel(logging.INFO)
    
    print("🔥 Universal 미디어 크롤러 테스트 시작")
    print("📸 4chan 스타일 이미지 추출 기능 포함")
    print("🌐 media_download.py 호환 인터페이스 제공")
    print("-" * 60)
    
# 모듈 로드 확인
logger.info("🔥 Universal 미디어 크롤러 Enhanced v1.0 로드 완료")
logger.info(f"📊 지원 미디어 타입: {len(SUPPORTED_IMAGE_EXTENSIONS | SUPPORTED_VIDEO_EXTENSIONS | SUPPORTED_AUDIO_EXTENSIONS)}개")
logger.info(f"🎯 미디어 호스팅 도메인: {len(MEDIA_HOSTING_DOMAINS)}개")
logger.info(f"🔍 HTML 셀렉터: {len(MEDIA_SELECTORS)}개")
logger.info("🖼️ 4chan 스타일 이미지 추출 방식 적용")
logger.info("⚙️ media_download.py 동적 추출기 시스템 호환")