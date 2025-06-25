#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🚀 PickPost Auto Build Optimizer
frontend/backend 분리 구조에 최적화된 배포 자동화

📁 PickPost/
├── build.py ← 이 파일
├── frontend/ ← 프론트엔드 최적화
└── backend/ ← 백엔드 최적화
"""

import os
import re
import sys
import json
from pathlib import Path
from typing import List, Dict, Set

class PickPostOptimizer:
    def __init__(self):
        self.root = Path('.')
        self.frontend_dir = self.root / 'frontend'
        self.backend_dir = self.root / 'backend'
        self.env = self.detect_environment()
        
        # 보호할 패턴들 정의
        self.protected_patterns = {
            'language_keywords': [
                'const languages', 'window.languages', 'ko:', 'en:', 'ja:',
                'siteNames:', 'boardPlaceholders:', 'errorMessages:', 'completionMessages:',
                'crawlingProgress:', 'cancellationMessages:', 'crawlButtonMessages:',
                'crawlingStatus:', 'notifications:', 'feedbackTitle:', 'messages:'
            ],
            'backend_imports': [
                'from fastapi', 'from core', 'from crawlers', 'import asyncio',
                'from pathlib', 'from typing', 'from pydantic', 'import importlib'
            ],
            'critical_functions': [
                'async def', 'def __init__', 'class ', 'def discover_', 'def create_',
                'CRAWL_FUNCTIONS', 'AVAILABLE_CRAWLERS', 'AUTO_CRAWLER_AVAILABLE'
            ]
        }
        
        print(f"🎯 PickPost 프로젝트 최적화 시작")
        print(f"🔍 감지된 환경: {self.env}")
        print(f"📁 Frontend: {self.frontend_dir.exists()}")
        print(f"📁 Backend: {self.backend_dir.exists()}")
    
    def detect_environment(self):
        """배포 환경 자동 감지"""
        if os.getenv('NETLIFY'):
            return 'netlify'
        elif os.getenv('RENDER'):
            return 'render'  
        elif os.getenv('VERCEL'):
            return 'vercel'
        elif Path('netlify.toml').exists():
            return 'netlify'
        elif Path('render.yaml').exists():
            return 'render'
        else:
            return 'local'
    
    def is_protected_content(self, line: str, file_type: str) -> bool:
        """보호해야 하는 내용인지 확인"""
        if file_type == 'js':
            # 언어팩 관련 라인은 항상 보호
            if any(keyword in line for keyword in self.protected_patterns['language_keywords']):
                return True
            # URL이나 API 관련 라인 보호
            if any(pattern in line for pattern in ['http://', 'https://', 'API_BASE_URL', 'WS_BASE_URL']):
                return True
            # 중요한 객체 리터럴 보호
            if re.search(r'^\s*[a-zA-Z_]+\s*:\s*{', line):
                return True
                
        elif file_type == 'py':
            # 백엔드 import문 보호
            if any(keyword in line for keyword in self.protected_patterns['backend_imports']):
                return True
            # 중요한 함수와 클래스 보호
            if any(keyword in line for keyword in self.protected_patterns['critical_functions']):
                return True
            # 설정 관련 라인 보호
            if any(pattern in line for pattern in ['DEEPL_API_KEY', 'REDDIT_', 'DEBUG', 'LOG_LEVEL']):
                return True
                
        return False
    
    def optimize_frontend_files(self):
        """프론트엔드 파일들 최적화"""
        if not self.frontend_dir.exists():
            print("❌ frontend 폴더가 없습니다.")
            return 0
        
        print("\n🌐 Frontend 최적화 시작...")
        total_saved = 0
        
        # JavaScript 파일들
        js_files = list(self.frontend_dir.glob('js/*.js')) + [self.frontend_dir / 'main.js']
        for js_file in js_files:
            if js_file.exists():
                saved = self.optimize_js_file(js_file)
                total_saved += saved
        
        # CSS 파일들
        css_files = list(self.frontend_dir.glob('css/*.css')) + [self.frontend_dir / 'style.css']
        for css_file in css_files:
            if css_file.exists():
                saved = self.optimize_css_file(css_file)
                total_saved += saved
        
        # HTML 파일들
        html_files = list(self.frontend_dir.glob('*.html'))
        for html_file in html_files:
            saved = self.optimize_html_file(html_file)
            total_saved += saved
        
        return total_saved
    
    def optimize_backend_files(self):
        """백엔드 파일들 최적화"""
        if not self.backend_dir.exists():
            print("❌ backend 폴더가 없습니다.")
            return 0
        
        print("\n⚙️ Backend 최적화 시작...")
        total_saved = 0
        
        # 메인 Python 파일들
        py_files = [
            self.backend_dir / 'main.py',
            self.backend_dir / 'progress_ws.py'
        ]
        
        # core 폴더 내 파일들
        core_dir = self.backend_dir / 'core'
        if core_dir.exists():
            py_files.extend(core_dir.glob('*.py'))
        
        # crawlers 폴더 내 파일들
        crawlers_dir = self.backend_dir / 'crawlers'
        if crawlers_dir.exists():
            py_files.extend(crawlers_dir.glob('*.py'))
        
        for py_file in py_files:
            if py_file.exists() and py_file.name != '__init__.py':
                saved = self.optimize_py_file(py_file)
                total_saved += saved
        
        return total_saved
    
    def optimize_js_file(self, file_path):
        """JavaScript 파일 최적화 - 언어팩과 기능 완전 보호"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_size = len(content)
            
            # 백업 생성 (항상)
            backup_path = file_path.with_suffix('.js.backup')
            with open(backup_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # 1. 전체 파일 멀티라인 주석 해제 확인 및 처리
            content = self.unwrap_multiline_comments(content, file_path.name)
            
            # 2. 파일별 특별 처리
            if file_path.name == 'languages.js':
                print(f"  🌐 언어팩 파일: {file_path.name} - 보호 모드로 최적화")
                content = self.safe_optimize_language_file(content)
            elif file_path.name in ['main.js', 'modal.js', 'announcements.js', 'feedback.js']:
                print(f"  🔧 핵심 기능 파일: {file_path.name} - 안전 모드로 최적화")
                content = self.safe_optimize_core_js_file(content)
            else:
                print(f"  📄 일반 파일: {file_path.name} - 표준 최적화")
                content = self.standard_optimize_js_file(content)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            new_size = len(content)
            saved = original_size - new_size
            reduction = (saved / original_size * 100) if original_size > 0 else 0
            
            print(f"    ✅ {original_size:,}→{new_size:,} (-{reduction:.1f}%) [백업: {backup_path.name}]")
            return saved
            
        except Exception as e:
            print(f"  ❌ {file_path.relative_to(self.root)}: {e}")
            return 0
    
    def unwrap_multiline_comments(self, content, filename):
        """전체 파일이 /* */ 주석으로 감싸진 경우 해제"""
        # 파일 시작과 끝의 공백 제거 후 확인
        stripped_content = content.strip()
        
        # 전체 파일이 /* */로 감싸져 있는지 확인
        if stripped_content.startswith('/*') and stripped_content.endswith('*/'):
            print(f"    🔓 전체 파일 멀티라인 주석 감지됨: {filename}")
            
            # /* */를 제거하고 내용 추출
            unwrapped = stripped_content[2:-2].strip()
            
            # 내용이 실제 JavaScript 코드인지 간단히 확인
            js_indicators = [
                'function', 'const', 'let', 'var', 'class', 'if', 'for', 'while',
                'window.', 'document.', '=', '{', '}', ';'
            ]
            
            if any(indicator in unwrapped for indicator in js_indicators):
                print(f"    ✅ 유효한 JavaScript 코드 확인됨, 주석 해제")
                return unwrapped
            else:
                print(f"    ⚠️ JavaScript 코드로 보이지 않음, 원본 유지")
                return content
        
        # 부분적 멀티라인 주석 해제 (여러 개의 /*...*/ 블록)
        elif '/*' in content and '*/' in content:
            print(f"    🔧 부분 멀티라인 주석 처리: {filename}")
            
            # 중첩된 멀티라인 주석 안전하게 처리
            result = ""
            i = 0
            in_comment = False
            comment_depth = 0
            
            while i < len(content):
                if i < len(content) - 1 and content[i:i+2] == '/*':
                    if not in_comment:
                        in_comment = True
                        comment_depth = 1
                    else:
                        comment_depth += 1
                    i += 2
                elif i < len(content) - 1 and content[i:i+2] == '*/' and in_comment:
                    comment_depth -= 1
                    if comment_depth <= 0:
                        in_comment = False
                        comment_depth = 0
                    i += 2
                else:
                    if not in_comment:
                        result += content[i]
                    i += 1
            
            return result
        
        return content
    
    def safe_optimize_language_file(self, content):
        """언어팩 파일 안전 최적화 - 멀티라인 주석 제거 포함, 내부 주석도 제거"""
        # 1. 먼저 멀티라인 주석 제거 (언어팩 데이터는 보호)
        content = self.remove_multiline_comments_safe(content)
        
        lines = content.split('\n')
        result_lines = []
        in_language_data_block = False
        brace_count = 0
        
        for line in lines:
            stripped = line.strip()
            
            # 언어 데이터 블록 감지 (ko:, en:, ja: 등)
            if re.match(r'^\s*(ko|en|ja)\s*:\s*{', line):
                in_language_data_block = True
                brace_count = line.count('{') - line.count('}')
                result_lines.append(line)
                continue
            
            # 언어 데이터 블록 내부 - 주석 제거하면서 데이터는 보호
            if in_language_data_block:
                brace_count += line.count('{') - line.count('}')
                
                # 블록 내부에서도 주석 제거
                if stripped.startswith('//'):
                    # URL 포함된 주석은 보존
                    if any(url in line for url in ['http://', 'https://', 'www.']):
                        result_lines.append(line)
                    else:
                        pass  # 주석 제거 (구분선 포함)
                else:
                    # 데이터 라인은 보존 (줄 끝 공백만 제거)
                    result_lines.append(line.rstrip())
                
                if brace_count <= 0:
                    in_language_data_block = False
                continue
            
            # 언어팩 관련 중요 키워드가 포함된 라인은 보호
            if any(keyword in line for keyword in self.protected_patterns['language_keywords']):
                result_lines.append(line)
                continue
            
            # 함수 정의나 중요한 구조는 보호
            if any(pattern in stripped for pattern in [
                'function ', 'const ', 'let ', 'var ', 'window.', 'export'
            ]):
                result_lines.append(line)
                continue
            
            # 단순한 한줄 주석만 제거 (URL 포함된 주석은 보존)
            if stripped.startswith('//'):
                if any(url in line for url in ['http://', 'https://', 'www.']):
                    result_lines.append(line)  # URL 포함된 주석은 보존
                else:
                    continue  # 일반 주석은 제거 (구분선 포함)
            
            # 빈 줄 정리 (연속된 빈 줄은 하나로)
            if stripped == '':
                if result_lines and result_lines[-1].strip() == '':
                    continue  # 연속된 빈 줄 건너뛰기
                else:
                    result_lines.append('')  # 첫 번째 빈 줄은 유지
                continue
            
            # 나머지 라인은 줄 끝 공백만 제거
            result_lines.append(line.rstrip())
        
        return '\n'.join(result_lines)
    
    def remove_multiline_comments_safe(self, content):
        """멀티라인 주석을 안전하게 제거 (문자열 내부는 보호)"""
        result = []
        i = 0
        in_string = False
        string_char = None
        in_comment = False
        
        while i < len(content):
            char = content[i]
            
            # 문자열 처리
            if not in_comment and char in ['"', "'", '`']:
                if not in_string:
                    in_string = True
                    string_char = char
                elif char == string_char and (i == 0 or content[i-1] != '\\'):
                    in_string = False
                    string_char = None
            
            # 문자열 내부에서는 주석 처리하지 않음
            if in_string:
                result.append(char)
                i += 1
                continue
            
            # 멀티라인 주석 시작
            if not in_comment and i < len(content) - 1 and content[i:i+2] == '/*':
                in_comment = True
                i += 2
                continue
            
            # 멀티라인 주석 끝
            if in_comment and i < len(content) - 1 and content[i:i+2] == '*/':
                in_comment = False
                i += 2
                continue
            
            # 주석 내부가 아니면 문자 추가
            if not in_comment:
                result.append(char)
            
            i += 1
        
        return ''.join(result)
    
    def safe_optimize_core_js_file(self, content):
        """핵심 기능 파일 안전 최적화"""
        lines = content.split('\n')
        result_lines = []
        in_protected_block = False
        brace_count = 0
        
        for line in lines:
            # 보호 블록 감지
            if self.is_protected_content(line, 'js'):
                in_protected_block = True
                brace_count = line.count('{') - line.count('}')
            elif in_protected_block:
                brace_count += line.count('{') - line.count('}')
                if brace_count <= 0:
                    in_protected_block = False
            
            # 보호 블록 내부는 수정하지 않음
            if in_protected_block:
                result_lines.append(line.rstrip())
                continue
            
            # 개발용 로그만 안전하게 제거
            if re.match(r'^\s*console\.(log|warn|debug)\s*\([^)]*\)\s*;?\s*$', line):
                continue
            if re.match(r'^\s*debugger\s*;?\s*$', line):
                continue
            
            # 단순 주석 제거 (URL 제외) - 구분선 주석도 포함
            if line.strip().startswith('//') and not any(url in line for url in ['http://', 'https://']):
                continue  # =로 된 구분선이나 일반 주석 모두 제거
            
            # 줄 끝 공백 제거
            result_lines.append(line.rstrip())
        
        return '\n'.join(result_lines)
    
    def standard_optimize_js_file(self, content):
        """일반 JavaScript 파일 표준 최적화"""
        lines = content.split('\n')
        result_lines = []
        
        for line in lines:
            # 보호 대상 확인
            if self.is_protected_content(line, 'js'):
                result_lines.append(line.rstrip())
                continue
            
            # 주석 제거 - 구분선과 일반 주석 모두 포함
            if line.strip().startswith('//'):
                continue  # =로 된 구분선이나 일반 주석 모두 제거
            
            # 개발용 로그 제거
            if re.match(r'^\s*console\.(log|warn|debug)\s*\([^)]*\)\s*;?\s*$', line):
                continue
            
            # 불필요한 공백 제거
            processed_line = re.sub(r'[ \t]+', ' ', line.strip())
            if processed_line:
                result_lines.append(processed_line)
        
        return '\n'.join(result_lines)
    
    def optimize_py_file(self, file_path):
        """Python 파일 최적화 - 백엔드 기능 보호"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_size = len(content)
            
            # 백업 생성
            backup_path = file_path.with_suffix('.py.backup')
            with open(backup_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            lines = content.split('\n')
            optimized = []
            skip_test = False
            in_protected_block = False
            
            for line in lines:
                # 테스트 코드 블록만 제거
                if 'if __name__ == "__main__":' in line:
                    skip_test = True
                    continue
                if skip_test:
                    # 테스트 코드 내부의 실제 실행은 주석 처리
                    if line.strip() and not line.strip().startswith('#'):
                        optimized.append(f'    # {line.strip()}')
                    continue
                
                # 보호 대상 확인
                if self.is_protected_content(line, 'py'):
                    in_protected_block = True
                
                # 보호 블록은 수정하지 않음
                if in_protected_block and (line.strip() == '' or not line.startswith(' ')):
                    in_protected_block = False
                
                if in_protected_block:
                    optimized.append(line.rstrip())
                    continue
                
                # 개발용 로깅만 제거 (에러 로그는 유지)
                if any(pattern in line for pattern in [
                    'logger.debug', 'print(f"📝', 'print(f"🧪',
                    'print("📝', 'print("🧪'
                ]) and 'error' not in line.lower():
                    continue
                
                # TODO, FIXME 주석 제거
                if re.match(r'^\s*#\s*(TODO|FIXME)', line):
                    continue
                
                # 프로덕션 설정 적용
                if 'DEBUG = True' in line and self.env != 'local':
                    line = line.replace('True', 'False')
                elif 'LOG_LEVEL = "DEBUG"' in line and self.env != 'local':
                    line = line.replace('"DEBUG"', '"WARNING"')
                
                # 과도한 빈 줄 제거
                if line.strip() == '' and optimized and optimized[-1].strip() == '':
                    continue
                
                optimized.append(line.rstrip())
            
            content = '\n'.join(optimized)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            new_size = len(content)
            saved = original_size - new_size
            reduction = (saved / original_size * 100) if original_size > 0 else 0
            
            print(f"  ✅ {file_path.relative_to(self.root)}: {original_size:,}→{new_size:,} (-{reduction:.1f}%)")
            return saved
            
        except Exception as e:
            print(f"  ❌ {file_path.relative_to(self.root)}: {e}")
            return 0
    
    def optimize_css_file(self, file_path):
        """CSS 파일 최적화 - 멀티라인 주석 해제 포함"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_size = len(content)
            
            # 백업 생성
            backup_path = file_path.with_suffix('.css.backup')
            with open(backup_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # 1. 전체 파일 멀티라인 주석 해제 확인
            content = self.unwrap_css_multiline_comments(content, file_path.name)
            
            # 2. 일반 주석 제거
            content = re.sub(r'/\*[\s\S]*?\*/', '', content)
            
            # 3. 공백 최적화 (환경별)
            if self.env != 'local':
                content = re.sub(r'\s+', ' ', content)
                content = re.sub(r';\s*}', ';}', content)
                content = re.sub(r'{\s*', '{', content)
                content = re.sub(r'}\s*', '}', content)
                content = re.sub(r':\s*', ':', content)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content.strip())
            
            new_size = len(content)
            saved = original_size - new_size
            reduction = (saved / original_size * 100) if original_size > 0 else 0
            
            print(f"  ✅ {file_path.relative_to(self.root)}: {original_size:,}→{new_size:,} (-{reduction:.1f}%)")
            return saved
            
        except Exception as e:
            print(f"  ❌ {file_path.relative_to(self.root)}: {e}")
            return 0
    
    def unwrap_css_multiline_comments(self, content, filename):
        """CSS 파일의 전체 멀티라인 주석 해제"""
        stripped_content = content.strip()
        
        # 전체 파일이 /* */로 감싸져 있는지 확인
        if stripped_content.startswith('/*') and stripped_content.endswith('*/'):
            print(f"    🔓 CSS 전체 파일 멀티라인 주석 감지됨: {filename}")
            
            # /* */를 제거하고 내용 추출
            unwrapped = stripped_content[2:-2].strip()
            
            # 내용이 실제 CSS 코드인지 간단히 확인
            css_indicators = [
                '{', '}', ':', ';', 'color', 'background', 'margin', 'padding',
                'width', 'height', 'font', 'border', 'display', 'position'
            ]
            
            if any(indicator in unwrapped for indicator in css_indicators):
                print(f"    ✅ 유효한 CSS 코드 확인됨, 주석 해제")
                return unwrapped
            else:
                print(f"    ⚠️ CSS 코드로 보이지 않음, 원본 유지")
                return content
        
        return content
    
    def optimize_html_file(self, file_path):
        """HTML 파일 최적화"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_size = len(content)
            
            # 개발용 주석만 제거 (중요한 주석은 유지)
            content = re.sub(r'<!--(?!.*?(?:copyright|license|TODO|FIXME))[\s\S]*?-->', '', content)
            
            # 개발용 속성 제거
            content = re.sub(r'\s*data-debug[^=]*=[^>\s]*', '', content)
            
            # 공백 최적화 (적절히)
            if self.env != 'local':
                content = re.sub(r'>\s+<', '> <', content)
                content = re.sub(r'\s{2,}', ' ', content)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content.strip())
            
            new_size = len(content)
            saved = original_size - new_size
            reduction = (saved / original_size * 100) if original_size > 0 else 0
            
            print(f"  ✅ {file_path.relative_to(self.root)}: {original_size:,}→{new_size:,} (-{reduction:.1f}%)")
            return saved
            
        except Exception as e:
            print(f"  ❌ {file_path.relative_to(self.root)}: {e}")
            return 0
    
    def create_environment_files(self):
        """환경별 설정 파일 생성/업데이트"""
        if self.env == 'netlify':
            self.create_netlify_config()
        elif self.env == 'render':
            self.create_render_config()
    
    def create_netlify_config(self):
        """Netlify 설정 파일 생성"""
        netlify_config = """[build]
  command = "python build.py"
  publish = "frontend"

[build.environment]
  PYTHON_VERSION = "3.9"

# API 프록시 (백엔드 연결)
[[redirects]]
  from = "/api/*"
  to = "https://pickpost.onrender.com/api/:splat"
  status = 200
  force = true

# WebSocket 프록시
[[redirects]]
  from = "/ws/*"
  to = "https://pickpost.onrender.com/ws/:splat"
  status = 200
  force = true

# 정적 파일 캐싱
[[headers]]
  for = "/css/*"
  [headers.values]
    Cache-Control = "public, max-age=31536000"
    
[[headers]]
  for = "/js/*" 
  [headers.values]
    Cache-Control = "public, max-age=31536000"

# 보안 헤더
[[headers]]
  for = "/*"
  [headers.values]
    X-Frame-Options = "DENY"
    X-XSS-Protection = "1; mode=block"
    X-Content-Type-Options = "nosniff"
    Referrer-Policy = "strict-origin-when-cross-origin"
"""
        
        with open('netlify.toml', 'w') as f:
            f.write(netlify_config)
        print("📝 netlify.toml 업데이트됨")
    
    def create_render_config(self):
        """Render 설정 파일 생성"""
        render_config = """services:
  - type: web
    name: pickpost-backend
    env: python
    region: frankfurt
    plan: starter
    buildCommand: "cd backend && pip install -r requirements.txt && cd .. && python build.py"
    startCommand: "cd backend && python main.py"
    healthCheckPath: "/health"
    
    envVars:
      # 기본 설정
      - key: APP_ENV
        value: production
      - key: DEBUG
        value: false
      - key: LOG_LEVEL
        value: WARNING
      - key: PORT
        value: 8000
      
      # API 키들 (Render UI에서 수동 설정 필요)
      - key: DEEPL_API_KEY
        sync: false
      - key: REDDIT_CLIENT_ID
        sync: false
      - key: REDDIT_CLIENT_SECRET
        sync: false
      - key: REDDIT_USER_AGENT
        value: PickPost/2.1
      
      # 보안
      - key: SECRET_KEY
        generateValue: true
      - key: CORS_ORIGINS
        value: https://pickpost.netlify.app
"""
        
        requirements = """fastapi==0.104.1
uvicorn[standard]==0.24.0
websockets==12.0
aiofiles==23.2.1
python-multipart==0.0.6
pydantic==2.5.0
httpx==0.25.2
beautifulsoup4==4.12.2
lxml==4.9.3
selenium==4.15.2
requests==2.31.0
python-dotenv==1.0.0
"""
        
        with open('render.yaml', 'w') as f:
            f.write(render_config)
        print("📝 render.yaml 업데이트됨")
        
        if not (self.backend_dir / 'requirements.txt').exists():
            with open(self.backend_dir / 'requirements.txt', 'w') as f:
                f.write(requirements)
            print("📝 backend/requirements.txt 생성됨")
    
    def verify_critical_files(self):
        """중요 파일들의 무결성 검증 - 멀티라인 주석 해제 포함"""
        print("\n🔍 중요 파일 무결성 검증...")
        
        critical_checks = []
        
        # 전체 파일 주석 처리 확인
        self.check_commented_files()
        
        # 언어팩 검증
        lang_file = self.frontend_dir / 'js' / 'languages.js'
        if lang_file.exists():
            with open(lang_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 전체 파일이 주석처리되어 있는지 확인
            if content.strip().startswith('/*') and content.strip().endswith('*/'):
                print(f"  ⚠️ 언어팩 파일이 전체 주석처리되어 있음")
                critical_checks.append("언어팩 파일이 주석처리됨")
            
            missing_keys = []
            for key in ['ko:', 'en:', 'ja:', 'errorMessages:', 'completionMessages:']:
                if key not in content:
                    missing_keys.append(key)
            
            if missing_keys:
                print(f"  ⚠️ 언어팩 누락 키: {missing_keys}")
                critical_checks.append(f"언어팩 누락: {missing_keys}")
            else:
                print(f"  ✅ 언어팩 무결성 확인")
        
        # 백엔드 main.py 검증
        main_file = self.backend_dir / 'main.py'
        if main_file.exists():
            with open(main_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            missing_imports = []
            for imp in ['from fastapi', 'from core', 'CRAWL_FUNCTIONS']:
                if imp not in content:
                    missing_imports.append(imp)
            
            if missing_imports:
                print(f"  ⚠️ 백엔드 누락 요소: {missing_imports}")
                critical_checks.append(f"백엔드 누락: {missing_imports}")
            else:
                print(f"  ✅ 백엔드 무결성 확인")
        
        return critical_checks
    
    def check_commented_files(self):
        """전체가 주석처리된 파일들 확인"""
        print("\n🔍 전체 주석처리된 파일 검사...")
        
        # JavaScript 파일들 확인
        if self.frontend_dir.exists():
            js_files = list(self.frontend_dir.glob('js/*.js')) + [self.frontend_dir / 'main.js']
            for js_file in js_files:
                if js_file.exists():
                    with open(js_file, 'r', encoding='utf-8') as f:
                        content = f.read().strip()
                    
                    if content.startswith('/*') and content.endswith('*/'):
                        print(f"  🔓 전체 주석처리 발견: {js_file.name}")
        
        # CSS 파일들 확인
        if self.frontend_dir.exists():
            css_files = list(self.frontend_dir.glob('css/*.css')) + [self.frontend_dir / 'style.css']
            for css_file in css_files:
                if css_file.exists():
                    with open(css_file, 'r', encoding='utf-8') as f:
                        content = f.read().strip()
                    
                    if content.startswith('/*') and content.endswith('*/'):
                        print(f"  🔓 전체 주석처리 발견: {css_file.name}")
    
    def run_optimization(self):
        """전체 최적화 실행"""
        print("🚀 PickPost 프로젝트 최적화 시작")
        print("=" * 50)
        
        frontend_saved = self.optimize_frontend_files()
        backend_saved = self.optimize_backend_files()
        total_saved = frontend_saved + backend_saved
        
        # 환경별 설정 파일 생성
        self.create_environment_files()
        
        # 무결성 검증
        critical_issues = self.verify_critical_files()
        
        print("\n" + "=" * 50)
        print(f"🎉 PickPost 최적화 완료!")
        print(f"📊 Frontend 절약: {frontend_saved:,} bytes ({frontend_saved/1024:.1f} KB)")
        print(f"📊 Backend 절약: {backend_saved:,} bytes ({backend_saved/1024:.1f} KB)")
        print(f"📊 총 절약: {total_saved:,} bytes ({total_saved/1024:.1f} KB)")
        
        if critical_issues:
            print(f"\n⚠️ 발견된 문제점: {len(critical_issues)}개")
            for issue in critical_issues:
                print(f"   - {issue}")
            print("💡 백업 파일에서 복원하거나 원본을 확인하세요.")
        else:
            print("\n✅ 모든 중요 기능 무결성 확인됨")
        
        if self.env == 'netlify':
            print("\n🌐 Netlify 프론트엔드 배포 준비 완료!")
            print("📡 백엔드 API 프록시 설정됨")
        elif self.env == 'render':
            print("\n⚙️ Render 백엔드 배포 준비 완료!")
            print("🔧 FastAPI + WebSocket 최적화됨")
        else:
            print(f"\n🛠️ {self.env.upper()} 환경 최적화 완료!")
        
        print("\n💡 백업 파일들이 생성되었습니다")
        print("   문제 발생 시 .backup 파일에서 복원하세요.")
        print("   예: cp frontend/js/languages.js.backup frontend/js/languages.js")

def main():
    optimizer = PickPostOptimizer()
    optimizer.run_optimization()

if __name__ == "__main__":
    main()