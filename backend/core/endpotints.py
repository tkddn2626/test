# core/simple_endpoints.py - 레지스트리 없는 단순 버전

import asyncio
import importlib
import inspect
import logging
import os
import re
import time
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
from fastapi import WebSocket
from datetime import datetime
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# endpoints.py 상단에 추가
import sys
import os
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

class SimpleEndpointManager:
    def __init__(self, app, crawl_manager):
        self.app = app
        self.crawl_manager = crawl_manager
        self.crawlers = {}
        
        # 기존 크롤러 명시적 등록
        self._register_explicit_crawlers()
        
        # 엔드포인트 생성
        self._create_endpoints()
    
    def _register_explicit_crawlers(self):
        """기존 크롤러들을 명시적으로 등록"""
        explicit_crawlers = {
            'reddit': {'module': 'reddit', 'function': 'fetch_posts'},
            'dcinside': {'module': 'dcinside', 'function': 'crawl_dcinside_board'},
            'blind': {'module': 'blind', 'function': 'crawl_blind_board'},
            'bbc': {'module': 'bbc', 'function': 'crawl_bbc_board'},
            'lemmy': {'module': 'lemmy', 'function': 'crawl_lemmy_board'},
            'universal': {'module': 'universal', 'function': 'crawl_universal_board'}
        }
        
        for site_type, info in explicit_crawlers.items():
            try:
                module = __import__(info['module'])
                crawl_func = getattr(module, info['function'])
                
                self.crawlers[site_type] = {
                    "crawl_function": crawl_func,
                    "metadata": {"module_name": info['module']}
                }
                logger.info(f"✅ 명시적 크롤러 등록: {site_type}")
                
            except Exception as e:
                logger.warning(f"크롤러 등록 실패 {site_type}: {e}")

# ==================== 🔥 단순한 자동 엔드포인트 매니저 ====================

class SimpleEndpointManager:
    """레지스트리 없는 단순 엔드포인트 매니저"""
    
    def __init__(self, app, crawl_manager):
        self.app = app
        self.crawl_manager = crawl_manager
        self.crawlers = {}  # {site_type: {crawl_func, detect_func, metadata}}
        self.origin_validator = OriginValidator()
        
        # 크롤러 자동 발견
        self._discover_crawlers()
        
        # 엔드포인트 생성
        self._create_endpoints()
        
        logger.info(f"🚀 단순 엔드포인트 매니저 초기화: {len(self.crawlers)}개 크롤러")
    
    def _discover_crawlers(self):
        """크롤러 파일들을 자동으로 발견하고 등록"""
        crawler_dirs = [
            Path(__file__).parent.parent,  # 프로젝트 루트
            Path(__file__).parent / "sites",  # sites 디렉토리
        ]
        
        for crawler_dir in crawler_dirs:
            if not crawler_dir.exists():
                continue
                
            for py_file in crawler_dir.glob("*.py"):
                if py_file.stem.startswith("_") or py_file.stem == "__init__":
                    continue
                
                try:
                    self._register_crawler_from_file(py_file)
                except Exception as e:
                    logger.warning(f"크롤러 등록 실패 {py_file}: {e}")
    
    def _register_crawler_from_file(self, py_file: Path):
        """파이썬 파일에서 크롤러 정보를 추출하고 등록"""
        module_name = py_file.stem
        
        try:
            # 동적 모듈 임포트
            spec = importlib.util.spec_from_file_location(module_name, py_file)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # 사이트 타입 추출
            site_type = getattr(module, 'SITE_TYPE', module_name.lower())
            
            # 크롤링 함수 찾기
            crawl_function = self._find_crawl_function(module, module_name, site_type)
            if not crawl_function:
                return
            
            # 감지 함수 찾기 (선택사항)
            detect_function = self._find_detect_function(module, module_name, site_type)
            
            # 메타데이터 구성
            metadata = {
                "module_name": module_name,
                "display_name": getattr(module, 'DISPLAY_NAME', site_type.title()),
                "description": getattr(module, 'DESCRIPTION', f"{site_type} 크롤러"),
                "version": getattr(module, 'VERSION', "1.0.0"),
            }
            
            # 크롤러 등록
            self.crawlers[site_type] = {
                "crawl_function": crawl_function,
                "detect_function": detect_function,
                "metadata": metadata
            }
            
            logger.info(f"✅ 크롤러 등록: {site_type} ({module_name})")
            
        except Exception as e:
            logger.debug(f"모듈 {module_name} 처리 중 오류: {e}")
    
    def _find_crawl_function(self, module, module_name: str, site_type: str):
        """크롤링 함수 찾기"""
        patterns = [
            f"crawl_{module_name}_board",
            f"crawl_{site_type}_board",
            "crawl_board", 
            "crawl",
            "fetch_posts"
        ]
        
        for pattern in patterns:
            if hasattr(module, pattern):
                return getattr(module, pattern)
        return None
    
    def _find_detect_function(self, module, module_name: str, site_type: str):
        """감지 함수 찾기"""
        patterns = [
            f"detect_{module_name}_url_and_extract_info",
            f"detect_{site_type}_url_and_extract_info",
            "detect_url_and_extract_info"
        ]
        
        for pattern in patterns:
            if hasattr(module, pattern):
                return getattr(module, pattern)
        return None
    
    def _create_endpoints(self):
        """엔드포인트들 생성"""
        
        # 1. 통합 크롤링 엔드포인트
        @self.app.websocket("/ws/crawl")
        async def unified_crawl_endpoint(websocket: WebSocket):
            await self._handle_unified_crawl(websocket)
        
        # 2. 사이트 분석 엔드포인트  
        @self.app.websocket("/ws/analyze")
        async def analyze_endpoint(websocket: WebSocket):
            await self._handle_site_analysis(websocket)
        
        # 3. 개별 사이트 엔드포인트들 (하위 호환성)
        for site_type in self.crawlers.keys():
            self._create_site_endpoint(site_type)
    
    def _create_site_endpoint(self, site_type: str):
        """개별 사이트 엔드포인트 생성"""
        endpoint_path = f"/ws/{site_type}-crawl"
        
        @self.app.websocket(endpoint_path)
        async def site_endpoint(websocket: WebSocket):
            await self._handle_site_crawl(websocket, site_type)
        
        logger.info(f"📡 엔드포인트 생성: {endpoint_path}")
    
    async def _handle_unified_crawl(self, websocket: WebSocket):
        """통합 크롤링 처리"""
        if not await self.origin_validator.validate_origin(websocket):
            return
        
        await websocket.accept()
        crawl_id = f"unified_{id(websocket)}_{int(time.time())}"
        
        try:
            config = await websocket.receive_json()
            input_data = config.get("input", "")
            
            # 사이트 자동 감지
            detected_site = await self._detect_site(input_data)
            if not detected_site:
                raise Exception("지원되지 않는 사이트입니다.")
            
            # 감지된 사이트 정보 전송
            await websocket.send_json({
                "detected_site": detected_site["site_type"],
                "board_identifier": detected_site.get("board_identifier"),
                "auto_detected": True,
                "progress": 20
            })
            
            # 해당 크롤러로 크롤링 실행
            results = await self._execute_crawl(detected_site["site_type"], input_data, websocket, config)
            
            # 결과 전송
            await websocket.send_json({
                "done": True,
                "data": results,
                "summary": f"크롤링 완료: {len(results)}개 게시물"
            })
            
        except Exception as e:
            logger.error(f"❌ 통합 크롤링 오류: {e}")
            await websocket.send_json({"error": str(e)})
        finally:
            await websocket.close()
    
    async def _detect_site(self, input_data: str):
        """사이트 감지"""
        # 1. 등록된 크롤러들의 감지 함수 시도
        for site_type, crawler_info in self.crawlers.items():
            detect_func = crawler_info.get("detect_function")
            if detect_func:
                try:
                    if asyncio.iscoroutinefunction(detect_func):
                        result = await detect_func(input_data)
                    else:
                        result = detect_func(input_data)
                    
                    if result and (result.get(f"is_{site_type}") or result.get("detected_site") == site_type):
                        return {
                            "site_type": site_type,
                            "board_identifier": result.get("board_identifier"),
                            "confidence": result.get("confidence", 1.0)
                        }
                except Exception as e:
                    logger.debug(f"감지 실패 ({site_type}): {e}")
        
        # 2. 폴백 감지 (간단한 URL/키워드 매칭)
        return self._fallback_detect(input_data)
    
    def _fallback_detect(self, input_data: str):
        """폴백 사이트 감지"""
        input_lower = input_data.lower()
        
        # 간단한 패턴 매칭
        patterns = {
            "reddit": ["reddit.com", "r/", "/r/"],
            "dcinside": ["dcinside.com", "갤러리", "dc"],
            "blind": ["teamblind.com", "blind", "블라인드"],
            "bbc": ["bbc.com", "bbc.co.uk"],
            "lemmy": ["lemmy.", "beehaw.org", "sh.itjust.works"]
        }
        
        for site_type, keywords in patterns.items():
            for keyword in keywords:
                if keyword in input_lower:
                    return {
                        "site_type": site_type,
                        "confidence": 0.7
                    }
        
        return None
    
    async def _execute_crawl(self, site_type: str, input_data: str, websocket: WebSocket, config: dict):
        """크롤링 실행"""
        crawler_info = self.crawlers.get(site_type)
        if not crawler_info:
            raise Exception(f"크롤러를 찾을 수 없습니다: {site_type}")
        
        crawl_func = crawler_info["crawl_function"]
        
        # 함수 매개변수 매핑
        sig = inspect.signature(crawl_func)
        params = {}
        
        # 매개변수 자동 매핑
        param_mapping = {
            'subreddit_name': input_data,  # Reddit
            'board_input': input_data,     # DCInside/Blind
            'board_url': input_data,       # BBC/Universal
            'websocket': websocket,
            'start_index': config.get('start', 1),
            'end_index': config.get('end', 20),
            'limit': config.get('limit', 20),
            'sort': config.get('sort', 'recent'),
            'min_views': config.get('min_views', 0),
            'min_likes': config.get('min_likes', 0),
            'time_filter': config.get('time_filter', 'day'),
        }
        
        for param_name in sig.parameters:
            if param_name in param_mapping:
                params[param_name] = param_mapping[param_name]
        
        # 크롤링 실행
        if asyncio.iscoroutinefunction(crawl_func):
            return await crawl_func(**params)
        else:
            return crawl_func(**params)
    
    async def _handle_site_analysis(self, websocket: WebSocket):
        """사이트 분석 처리"""
        if not await self.origin_validator.validate_origin(websocket):
            return
        
        await websocket.accept()
        
        try:
            data = await websocket.receive_json()
            input_data = data.get("input", "")
            
            detected = await self._detect_site(input_data)
            
            await websocket.send_json({
                "analysis_complete": True,
                "detected_site": detected["site_type"] if detected else "unknown",
                "board_identifier": detected.get("board_identifier") if detected else None
            })
        except Exception as e:
            await websocket.send_json({"error": str(e)})
        finally:
            await websocket.close()
    
    async def _handle_site_crawl(self, websocket: WebSocket, site_type: str):
        """개별 사이트 크롤링 처리"""
        if not await self.origin_validator.validate_origin(websocket):
            return
        
        await websocket.accept()
        
        try:
            config = await websocket.receive_json()
            input_data = config.get("board", "") or config.get("input", "")
            
            results = await self._execute_crawl(site_type, input_data, websocket, config)
            
            await websocket.send_json({
                "done": True,
                "data": results,
                "summary": f"{site_type} 크롤링 완료: {len(results)}개 게시물"
            })
        except Exception as e:
            await websocket.send_json({"error": str(e)})
        finally:
            await websocket.close()
    
    def get_endpoint_info(self):
        """엔드포인트 정보 반환"""
        return {
            "crawlers": {
                site: info["metadata"]
                for site, info in self.crawlers.items()
            },
            "endpoints": {
                "unified": "/ws/crawl",
                "analyze": "/ws/analyze",
                "individual": {
                    site: f"/ws/{site}-crawl"
                    for site in self.crawlers.keys()
                }
            }
        }

# ==================== Origin 검증기 ====================
class OriginValidator:
    def __init__(self):
        self.app_env = os.getenv("APP_ENV", "development")
    
    async def validate_origin(self, websocket: WebSocket) -> bool:
        origin = websocket.headers.get("origin", "")
        
        if self.app_env == "production":
            allowed = any(pattern in origin for pattern in ["netlify.app", "onrender.com"])
        else:
            allowed = True  # 개발 환경에서는 모든 origin 허용
        
        if not allowed:
            await websocket.close(code=1008, reason="Invalid origin")
            return False
        
        return True

# ==================== 팩토리 함수 ====================
def create_simple_endpoint_manager(app, crawl_manager):
    """단순 엔드포인트 매니저 생성"""
    return SimpleEndpointManager(app, crawl_manager)
