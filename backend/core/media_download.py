# core/media_download.py
# 미디어 파일 다운로드 및 압축 모듈 - 사이트 타입 무관

import os
import asyncio
import aiohttp
import aiofiles
import zipfile
import tempfile
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable
from urllib.parse import urlparse, unquote
from datetime import datetime
import logging
import re

# import
from core.messages import create_localized_error_message, create_message_response

# 로깅 설정
logger = logging.getLogger(__name__)

# ==================== 설정 및 상수 ====================

# 미디어 다운로드 설정
MEDIA_CONFIG = {
    'max_file_size_mb': 100,           # 개별 파일 최대 크기 (MB)
    'max_total_size_mb': 900,         # 전체 ZIP 최대 크기 (MB)
    'download_timeout': 30,            # 다운로드 타임아웃 (초)
    'max_concurrent_downloads': 5,     # 동시 다운로드 수
    'retry_attempts': 3,               # 재시도 횟수
    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# 지원하는 미디어 타입
SUPPORTED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.svg'}
SUPPORTED_VIDEO_EXTENSIONS = {'.mp4', '.webm', '.mov', '.avi', '.mkv', '.flv', '.wmv'}
SUPPORTED_AUDIO_EXTENSIONS = {'.mp3', '.wav', '.ogg', '.m4a', '.flac', '.aac'}

# 임시 다운로드 디렉토리
TEMP_DOWNLOAD_DIR = Path(tempfile.gettempdir()) / "pickpost_media_downloads"
TEMP_DOWNLOAD_DIR.mkdir(exist_ok=True)

# ==================== 유틸리티 함수 ====================

def get_file_extension_from_url(url: str) -> str:
    """URL에서 파일 확장자 추출"""
    try:
        parsed = urlparse(url)
        path = unquote(parsed.path)
        return Path(path).suffix.lower()
    except Exception:
        return ''

def get_media_type(extension: str) -> str:
    """확장자로 미디어 타입 결정"""
    if extension in SUPPORTED_IMAGE_EXTENSIONS:
        return 'image'
    elif extension in SUPPORTED_VIDEO_EXTENSIONS:
        return 'video'
    elif extension in SUPPORTED_AUDIO_EXTENSIONS:
        return 'audio'
    else:
        return 'unknown'

def sanitize_filename(filename: str) -> str:
    """파일명 안전하게 정리"""
    # 위험한 문자 제거
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # 연속된 밑줄 제거
    sanitized = re.sub(r'_+', '_', sanitized)
    # 앞뒤 밑줄/공백 제거
    sanitized = sanitized.strip('_. ')
    # 빈 문자열 방지
    return sanitized if sanitized else 'untitled'

def is_valid_media_url(url: str) -> bool:
    """유효한 미디어 URL인지 확인"""
    if not url or not isinstance(url, str):
        return False
    
    # 기본 URL 형식 확인
    if not url.startswith(('http://', 'https://')):
        return False
    
    # 확장자 확인
    extension = get_file_extension_from_url(url)
    if extension:
        all_extensions = SUPPORTED_IMAGE_EXTENSIONS | SUPPORTED_VIDEO_EXTENSIONS | SUPPORTED_AUDIO_EXTENSIONS
        return extension in all_extensions
    
    # 확장자가 없어도 알려진 미디어 호스팅 도메인이면 허용
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        
        # 알려진 미디어 호스팅 도메인들
        media_domains = {
            'i.imgur.com', 'imgur.com',
            'i.redd.it', 'v.redd.it',
            'i.pinimg.com', 'pinimg.com',  # Pinterest 추가
            'youtube.com', 'youtu.be',
            'vimeo.com',
            'streamable.com',
            'gfycat.com',
            'giphy.com',
            'media.discordapp.net',
            'cdn.discordapp.com'
        }
        
        return any(domain.endswith(md) for md in media_domains)
        
    except Exception:
        return False

def cleanup_old_downloads(max_age_hours: int = 4) -> int:
    """오래된 다운로드 파일 정리"""
    if not TEMP_DOWNLOAD_DIR.exists():
        return 0
    
    cleaned_count = 0
    cutoff_time = datetime.now().timestamp() - (max_age_hours * 3600)
    
    try:
        for file_path in TEMP_DOWNLOAD_DIR.iterdir():
            if file_path.is_file():
                try:
                    if file_path.stat().st_mtime < cutoff_time:
                        file_path.unlink()
                        cleaned_count += 1
                        logger.debug(f"🗑️ Cleaned: {file_path.name}")
                except Exception as e:
                    logger.warning(f"⚠️ File cleanup failed: {file_path.name} - {e}")
                    
    except Exception as e:
        logger.error(f"❌ Directory cleanup error: {e}")
    
    if cleaned_count > 0:
        logger.info(f"🧹 Cleaned up {cleaned_count} old files")
    
    return cleaned_count

# ==================== 미디어 URL 추출 함수 ====================

def extract_media_from_posts(posts: List[Dict]) -> List[Dict]:
    """
    크롤링된 게시물에서 미디어 URL들만 추출
    사이트 타입 무관하게 동작
    """
    media_list = []
    
    for i, post in enumerate(posts):
        try:
            # 각 게시물에서 미디어 URL 필드들 확인
            media_fields = [
                '썸네일 URL',
                '이미지 URL', 
                'thumbnail_url',
                'image_url',
                'media_url',
                'attachment_url'
            ]
            
            for field in media_fields:
                url = post.get(field, '')
                if url and url.startswith('http') and is_valid_media_url(url):
                    # 파일명 생성
                    try:
                        filename = Path(urlparse(url).path).name
                        if not filename or '.' not in filename:
                            extension = get_file_extension_from_url(url)
                            filename = f"media_{i}_{abs(hash(url)) % 1000}{extension}"
                        filename = sanitize_filename(filename)
                    except:
                        filename = f"media_{i}_{abs(hash(url)) % 1000}.jpg"
                    
                    media_info = {
                        'type': get_media_type(get_file_extension_from_url(url)),
                        'original_url': url,
                        'thumbnail_url': url,  # 썸네일과 원본이 같을 수 있음
                        'filename': filename,
                        'post_title': post.get('원제목') or post.get('title') or post.get('제목', 'Untitled'),
                        'post_link': post.get('링크') or post.get('link') or post.get('url', ''),
                        'extracted_at': datetime.now().isoformat(),
                        'source_field': field
                    }
                    
                    # 중복 체크 (같은 URL이 여러 필드에 있을 수 있음)
                    if not any(m['original_url'] == url for m in media_list):
                        media_list.append(media_info)
            
        except Exception as e:
            logger.warning(f"⚠️ Post {i} media extraction failed: {e}")
    
    logger.info(f"📦 Extracted {len(media_list)} media URLs from {len(posts)} posts")
    return media_list

# ==================== 메인 미디어 다운로드 매니저 ====================

class MediaDownloadManager:
    def __init__(self, user_lang: str = "en"):
        self.user_lang = user_lang
        self.session = None
        self.download_semaphore = asyncio.Semaphore(MEDIA_CONFIG['max_concurrent_downloads'])
        self.downloaded_size = 0
        self.max_total_size = MEDIA_CONFIG['max_total_size_mb'] * 1024 * 1024
    
    async def __aenter__(self):
        """비동기 컨텍스트 매니저 진입"""
        connector = aiohttp.TCPConnector(
            limit=MEDIA_CONFIG['max_concurrent_downloads'] * 2,
            limit_per_host=MEDIA_CONFIG['max_concurrent_downloads'],
            ttl_dns_cache=300,
            use_dns_cache=True
        )
        
        timeout = aiohttp.ClientTimeout(
            total=MEDIA_CONFIG['download_timeout'],
            connect=10,
            sock_read=30
        )
        
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={'User-Agent': MEDIA_CONFIG['user_agent']}
        )
        
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """비동기 컨텍스트 매니저 종료"""
        if self.session:
            await self.session.close()
    
    async def download_media_from_posts(
        self, 
        posts: List[Dict], 
        site_type: str = None,  # 이제 사용 안함
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """게시물들에서 미디어 추출 및 다운로드 - 사이트 타입 무관"""
        
        if not posts:
            return {
                'success': False,
                'error': 'No posts provided',
                'downloaded_files': 0,
                'failed_files': 0
            }
        
        # 1. 모든 게시물에서 미디어 URL 추출 (사이트 타입 무관)
        logger.info(f"🔍 Extracting media from {len(posts)} posts")
        
        media_list = extract_media_from_posts(posts)
        
        if not media_list:
            return {
                'success': False,
                'error': 'No media URLs found in posts',
                'downloaded_files': 0,
                'failed_files': 0
            }
        
        logger.info(f"📦 Found {len(media_list)} media URLs")
        
        # 2. 다운로드 디렉토리 생성
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        download_dir = TEMP_DOWNLOAD_DIR / f"media_{timestamp}"
        download_dir.mkdir(exist_ok=True)
        
        # 3. 병렬 다운로드
        logger.info(f"⬇️ Starting download of {len(media_list)} files")
        download_tasks = []
        
        for media_info in media_list:
            task = self.download_single_file(media_info, download_dir)
            download_tasks.append(task)
        
        # 병렬 실행
        download_results = await asyncio.gather(*download_tasks, return_exceptions=True)
        
        # 4. 결과 집계
        successful_files = []
        failed_count = 0
        
        for i, result in enumerate(download_results):
            if progress_callback:
                progress = int((i + 1) / len(download_results) * 80)  # 80%까지 다운로드
                await progress_callback(progress, len(download_results))
            
            if isinstance(result, Exception):
                logger.error(f"❌ Download task error: {result}")
                failed_count += 1
            elif result is not None:
                successful_files.append(result)
            else:
                failed_count += 1
        
        if not successful_files:
            return {
                'success': False,
                'error': 'All file downloads failed',
                'downloaded_files': 0,
                'failed_files': failed_count
            }
        
        # 5. ZIP 파일 생성
        if progress_callback:
            await progress_callback(90, len(successful_files))
        
        zip_path = await self.create_zip_file(successful_files, download_dir, timestamp)
        
        if progress_callback:
            await progress_callback(100, len(successful_files))
        
        # 6. 임시 파일들 정리
        try:
            for file_path in successful_files:
                if file_path.exists():
                    file_path.unlink()
            
            # 빈 디렉토리 제거
            if download_dir.exists() and not any(download_dir.iterdir()):
                download_dir.rmdir()
                
        except Exception as e:
            logger.warning(f"⚠️ Temporary file cleanup failed: {e}")
        
        # 7. 결과 반환
        zip_size_mb = zip_path.stat().st_size / (1024 * 1024) if zip_path.exists() else 0
        
        logger.info(f"✅ Media download complete: {len(successful_files)} successful, {failed_count} failed")
        logger.info(f"📁 ZIP file created: {zip_path.name} ({zip_size_mb:.2f}MB)")
        
        return {
            'success': True,
            'download_url': f'/api/download-file/{zip_path.name}',
            'zip_filename': zip_path.name,
            'downloaded_files': len(successful_files),
            'failed_files': failed_count,
            'zip_size_mb': round(zip_size_mb, 2),
            'total_media_found': len(media_list),
            'unique_media_count': len(media_list)
        }
    
    async def download_single_file(self, media_info: Dict, download_dir: Path) -> Optional[Path]:
        """단일 미디어 파일 다운로드"""
        url = media_info['original_url']
        filename = media_info['filename']
        
        async with self.download_semaphore:
            for attempt in range(MEDIA_CONFIG['retry_attempts']):
                try:
                    # HEAD 요청으로 파일 크기 확인
                    async with self.session.head(url) as response:
                        if response.status != 200:
                            logger.warning(f"⚠️ File access failed: {url} (status: {response.status})")
                            return None
                        
                        content_length = response.headers.get('content-length')
                        if content_length:
                            file_size = int(content_length)
                            file_size_mb = file_size / (1024 * 1024)
                            
                            # 개별 파일 크기 제한
                            if file_size_mb > MEDIA_CONFIG['max_file_size_mb']:
                                logger.warning(f"⚠️ File size exceeded: {filename} ({file_size_mb:.1f}MB)")
                                return None
                            
                            # 전체 다운로드 크기 제한
                            if self.downloaded_size + file_size > self.max_total_size:
                                logger.warning(f"⚠️ Total download size limit reached: {filename}")
                                return None
                    
                    # 실제 파일 다운로드
                    async with self.session.get(url) as response:
                        if response.status == 200:
                            file_path = download_dir / filename
                            
                            # 파일명 중복 처리
                            counter = 1
                            original_path = file_path
                            while file_path.exists():
                                name_parts = original_path.stem, counter, original_path.suffix
                                file_path = original_path.parent / f"{name_parts[0]}_{name_parts[1]}{name_parts[2]}"
                                counter += 1
                            
                            async with aiofiles.open(file_path, 'wb') as f:
                                async for chunk in response.content.iter_chunked(8192):
                                    await f.write(chunk)
                            
                            # 다운로드된 크기 추가
                            actual_size = file_path.stat().st_size
                            self.downloaded_size += actual_size
                            
                            logger.debug(f"✅ Download completed: {file_path.name}")
                            return file_path
                        else:
                            logger.warning(f"⚠️ Download failed: {url} (status: {response.status})")
                            
                except asyncio.TimeoutError:
                    logger.warning(f"⚠️ Download timeout: {url} (attempt {attempt + 1}/{MEDIA_CONFIG['retry_attempts']})")
                except Exception as e:
                    logger.warning(f"⚠️ Download error: {url} - {e} (attempt {attempt + 1}/{MEDIA_CONFIG['retry_attempts']})")
                
                if attempt < MEDIA_CONFIG['retry_attempts'] - 1:
                    await asyncio.sleep(1)  # 재시도 전 대기
        
        return None
    
    async def create_zip_file(
        self, 
        file_paths: List[Path], 
        download_dir: Path, 
        timestamp: str
    ) -> Path:
        """다운로드된 파일들을 ZIP으로 압축"""
        zip_filename = f"pickpost_media_{timestamp}.zip"
        zip_path = TEMP_DOWNLOAD_DIR / zip_filename
        
        def create_zip():
            try:
                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as zipf:
                    for file_path in file_paths:
                        if file_path.exists():
                            # ZIP 내부에서의 파일명
                            zipf.write(file_path, file_path.name)
            except Exception as e:
                logger.error(f"❌ ZIP creation error: {e}")
                raise
        
        # CPU 집약적인 ZIP 생성을 별도 스레드에서 실행
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, create_zip)
        
        logger.info(f"📁 ZIP compression complete: {zip_path.name} ({len(file_paths)} files)")
        return zip_path
    
    def get_manager_info(self) -> Dict[str, Any]:
        """매니저 정보 반환"""
        return {
            'config': MEDIA_CONFIG,
            'temp_dir': str(TEMP_DOWNLOAD_DIR),
            'language': self.user_lang,
            'supported_extensions': {
                'images': list(SUPPORTED_IMAGE_EXTENSIONS),
                'videos': list(SUPPORTED_VIDEO_EXTENSIONS),
                'audio': list(SUPPORTED_AUDIO_EXTENSIONS)
            }
        }

# ==================== 정리 함수 ====================

def cleanup_old_downloads_with_logging(max_age_hours: int = 4) -> int:
    """로깅과 함께 오래된 다운로드 파일 정리"""
    try:
        cleaned_count = cleanup_old_downloads(max_age_hours)
        return cleaned_count
    except Exception as e:
        logger.error(f"❌ Error during file cleanup: {e}")
        return 0

# ==================== 모듈 초기화 ====================

# 모듈 로드 시 정리 작업 수행 - 4시간으로 변경
cleanup_old_downloads(max_age_hours=4)

logger.info("📦 Simple media download module loaded successfully")
logger.info(f"📁 Temp directory: {TEMP_DOWNLOAD_DIR}")
logger.info(f"⚙️ Config: Max {MEDIA_CONFIG['max_file_size_mb']}MB/file, {MEDIA_CONFIG['max_concurrent_downloads']} concurrent downloads")
logger.info("🔄 Direct URL extraction from crawled posts")
logger.info("🧹 Temp file cleanup: Auto-delete after 4 hours")

# 전역 매니저 인스턴스 생성 (main.py에서 사용)
_global_media_manager = None

def get_media_download_manager(user_lang: str = "en") -> MediaDownloadManager:
    """전역 미디어 다운로드 매니저 반환 (언어 설정 포함)"""
    global _global_media_manager
    if _global_media_manager is None:
        _global_media_manager = MediaDownloadManager(user_lang=user_lang)
        logger.info("🎯 Media extraction: Direct from post fields")
    else:
        # 언어 설정 업데이트
        _global_media_manager.user_lang = user_lang
    return _global_media_manager