#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🚀 PickPost 해시 기반 빌드 시스템
내용 기반 해시로 브라우저 캐시 문제 해결
"""

import os
import sys
import hashlib
import re
import shutil
from pathlib import Path
from typing import Dict, List, Tuple

class HashBasedBuilder:
    def __init__(self):
        self.root = Path('.')
        self.frontend_dir = self.root / 'frontend'
        self.backend_dir = self.root / 'backend'
        self.env = self.detect_environment()
        self.file_mappings = {}  # 원본파일명 -> 해시파일명 매핑
        
        print(f"🚀 PickPost 해시 기반 빌드 시작")
        print(f"🔍 환경: {self.env}")
        print(f"📁 Frontend: {self.frontend_dir}")
    
    def detect_environment(self):
        """배포 환경 감지"""
        if os.getenv('NETLIFY'):
            return 'netlify'
        elif os.getenv('RENDER'):
            return 'render'
        elif Path('netlify.toml').exists():
            return 'netlify'
        elif Path('render.yaml').exists():
            return 'render'
        else:
            return 'local'
    
    def generate_file_hash(self, file_path: Path) -> str:
        """파일 내용 기반 8자리 해시 생성"""
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
            return hashlib.md5(content).hexdigest()[:8]
        except Exception as e:
            print(f"❌ 해시 생성 실패 {file_path}: {e}")
            return "00000000"
    
    def backup_original_files(self):
        """원본 파일들 백업"""
        backup_dir = self.root / 'build_backup'
        if backup_dir.exists():
            shutil.rmtree(backup_dir)
        
        backup_dir.mkdir(exist_ok=True)
        
        # Frontend 전체 백업
        if self.frontend_dir.exists():
            shutil.copytree(self.frontend_dir, backup_dir / 'frontend')
            print(f"💾 Frontend 백업 완료: {backup_dir / 'frontend'}")
    
    def get_static_files(self) -> List[Path]:
        """해시 적용할 정적 파일들 수집"""
        static_files = []
        
        if not self.frontend_dir.exists():
            print(f"❌ Frontend 디렉토리가 없습니다: {self.frontend_dir}")
            return static_files
        
        # CSS 파일들
        css_files = list(self.frontend_dir.glob('**/*.css'))
        static_files.extend(css_files)
        
        # JavaScript 파일들 (announcements 폴더 제외)
        js_files = list(self.frontend_dir.glob('**/*.js'))
        # announcements 폴더의 파일들은 제외 (동적 로드 때문)
        js_files = [f for f in js_files if 'announcements' not in str(f)]
        static_files.extend(js_files)
        
        print(f"📁 수집된 정적 파일: {len(static_files)}개")
        for file in static_files:
            rel_path = file.relative_to(self.frontend_dir)
            print(f"  📄 {rel_path}")
        
        return static_files
    
    def create_hashed_files(self, static_files: List[Path]) -> Dict[str, str]:
        """해시가 포함된 새 파일들 생성"""
        file_mappings = {}
        
        for file_path in static_files:
            try:
                # 파일 해시 생성
                file_hash = self.generate_file_hash(file_path)
                
                # 새 파일명 생성
                stem = file_path.stem
                suffix = file_path.suffix
                new_name = f"{stem}.{file_hash}{suffix}"
                new_path = file_path.parent / new_name
                
                # 기존 파일을 새 이름으로 복사
                shutil.copy2(file_path, new_path)
                
                # 매핑 정보 저장 (상대 경로로)
                rel_original = file_path.relative_to(self.frontend_dir)
                rel_new = new_path.relative_to(self.frontend_dir)
                
                file_mappings[str(rel_original)] = str(rel_new)
                
                print(f"  ✅ {rel_original} → {rel_new}")
                
            except Exception as e:
                print(f"  ❌ 파일 생성 실패 {file_path}: {e}")
        
        return file_mappings
    
    def update_html_references(self, file_mappings: Dict[str, str]):
        """HTML 파일의 CSS/JS 참조 경로 업데이트"""
        html_files = list(self.frontend_dir.glob('**/*.html'))
        
        for html_file in html_files:
            try:
                with open(html_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                original_content = content
                
                # CSS 링크 업데이트
                for original, hashed in file_mappings.items():
                    if original.endswith('.css'):
                        # href="css/style.css" → href="css/style.abc12345.css"
                        pattern = f'href=[\'"]{re.escape(original)}[\'"]'
                        replacement = f'href="{hashed}"'
                        content = re.sub(pattern, replacement, content)
                
                # JavaScript 스크립트 업데이트  
                for original, hashed in file_mappings.items():
                    if original.endswith('.js'):
                        # src="js/main.js" → src="js/main.abc12345.js"
                        pattern = f'src=[\'"]{re.escape(original)}[\'"]'
                        replacement = f'src="{hashed}"'
                        content = re.sub(pattern, replacement, content)
                
                # 변경사항이 있으면 파일 업데이트
                if content != original_content:
                    with open(html_file, 'w', encoding='utf-8') as f:
                        f.write(content)
                    
                    rel_path = html_file.relative_to(self.frontend_dir)
                    print(f"  ✅ HTML 업데이트: {rel_path}")
                
            except Exception as e:
                print(f"  ❌ HTML 업데이트 실패 {html_file}: {e}")
    
    def update_js_dynamic_imports(self, file_mappings: Dict[str, str]):
        """JavaScript 파일의 동적 import 경로 업데이트"""
        js_files = []
        
        # 해시된 JS 파일들만 수집
        for original, hashed in file_mappings.items():
            if hashed.endswith('.js'):
                js_path = self.frontend_dir / hashed
                if js_path.exists():
                    js_files.append(js_path)
        
        for js_file in js_files:
            try:
                with open(js_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                original_content = content
                
                # ⚠️ announcements 폴더는 동적 로드이므로 건드리지 않음
                # 일반적인 상대 경로 import만 업데이트
                for original, hashed in file_mappings.items():
                    if original.endswith('.js') and 'announcements' not in original:
                        # './main.js' → './main.abc12345.js'
                        original_name = Path(original).name
                        hashed_name = Path(hashed).name
                        
                        pattern = f'[\'"`]\./{re.escape(original_name)}[\'"`]'
                        replacement = f'"./{hashed_name}"'
                        content = re.sub(pattern, replacement, content)
                
                # 변경사항이 있으면 파일 업데이트
                if content != original_content:
                    with open(js_file, 'w', encoding='utf-8') as f:
                        f.write(content)
                    
                    rel_path = js_file.relative_to(self.frontend_dir)
                    print(f"  ✅ JS 동적 import 업데이트: {rel_path}")
                
            except Exception as e:
                print(f"  ❌ JS 업데이트 실패 {js_file}: {e}")
    
    def remove_original_files(self, static_files: List[Path]):
        """원본 정적 파일들 제거 (해시된 파일로 대체됨)"""
        removed_count = 0
        
        for file_path in static_files:
            try:
                if file_path.exists():
                    file_path.unlink()
                    removed_count += 1
                    
                    rel_path = file_path.relative_to(self.frontend_dir)
                    print(f"  🗑️ 원본 제거: {rel_path}")
                    
            except Exception as e:
                print(f"  ❌ 파일 제거 실패 {file_path}: {e}")
        
        print(f"🗑️ 총 {removed_count}개 원본 파일 제거됨")
    
    def validate_build(self, file_mappings: Dict[str, str]) -> bool:
        """빌드 결과 검증"""
        print("\n🔍 빌드 결과 검증 중...")
        
        # 해시된 파일들이 실제로 존재하는지 확인
        missing_files = []
        for original, hashed in file_mappings.items():
            hashed_path = self.frontend_dir / hashed
            if not hashed_path.exists():
                missing_files.append(hashed)
        
        if missing_files:
            print(f"❌ 누락된 해시 파일들: {missing_files}")
            return False
        
        # HTML 파일에서 해시된 파일 참조 확인
        html_files = list(self.frontend_dir.glob('**/*.html'))
        for html_file in html_files:
            try:
                with open(html_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 원본 파일명이 아직 참조되고 있는지 확인
                for original in file_mappings.keys():
                    if f'"{original}"' in content or f"'{original}'" in content:
                        rel_path = html_file.relative_to(self.frontend_dir)
                        print(f"⚠️ {rel_path}에서 여전히 원본 파일 참조: {original}")
                
            except Exception as e:
                print(f"❌ HTML 검증 실패 {html_file}: {e}")
        
        print("✅ 빌드 검증 완료")
        return True
    
    def create_mapping_file(self, file_mappings: Dict[str, str]):
        """파일 매핑 정보를 JSON으로 저장 (디버깅용)"""
        import json
        
        mapping_file = self.root / 'file-mappings.json'
        try:
            with open(mapping_file, 'w', encoding='utf-8') as f:
                json.dump(file_mappings, f, indent=2, ensure_ascii=False)
            
            print(f"📝 파일 매핑 정보 저장: {mapping_file}")
            
        except Exception as e:
            print(f"❌ 매핑 파일 저장 실패: {e}")
    
    def run_hash_build(self):
        """해시 기반 빌드 실행"""
        print("🚀 해시 기반 빌드 시작")
        print("=" * 60)
        
        try:
            # 1. 원본 파일 백업
            print("\n📦 1단계: 원본 파일 백업")
            self.backup_original_files()
            
            # 2. 정적 파일 수집
            print("\n📁 2단계: 정적 파일 수집")
            static_files = self.get_static_files()
            
            if not static_files:
                print("❌ 처리할 정적 파일이 없습니다.")
                return False
            
            # 3. 해시된 파일 생성
            print("\n🔨 3단계: 해시된 파일 생성")
            file_mappings = self.create_hashed_files(static_files)
            
            if not file_mappings:
                print("❌ 해시 파일 생성에 실패했습니다.")
                return False
            
            # 4. HTML 참조 업데이트
            print("\n📝 4단계: HTML 파일 참조 업데이트")
            self.update_html_references(file_mappings)
            
            # 5. JavaScript 동적 import 업데이트
            print("\n⚡ 5단계: JavaScript 동적 import 업데이트")
            self.update_js_dynamic_imports(file_mappings)
            
            # 6. 원본 파일 제거
            print("\n🗑️ 6단계: 원본 파일 제거")
            self.remove_original_files(static_files)
            
            # 7. 빌드 검증
            print("\n✅ 7단계: 빌드 검증")
            validation_success = self.validate_build(file_mappings)
            
            # 8. 매핑 파일 생성
            print("\n📝 8단계: 매핑 파일 생성")
            self.create_mapping_file(file_mappings)
            
            # 결과 출력
            print("\n" + "=" * 60)
            if validation_success:
                print("🎉 해시 기반 빌드 성공!")
                print(f"📊 처리된 파일: {len(file_mappings)}개")
                print(f"🌍 배포 환경: {self.env}")
                print("🚀 브라우저 캐시 문제 해결됨!")
                
                print("\n📋 처리된 파일들:")
                for original, hashed in file_mappings.items():
                    print(f"  {original} → {hashed}")
                    
            else:
                print("❌ 빌드 검증 실패")
                return False
            
            print("=" * 60)
            return True
            
        except Exception as e:
            print(f"\n❌ 빌드 중 치명적 오류 발생: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def restore_from_backup(self):
        """백업에서 원본 파일 복원"""
        backup_dir = self.root / 'build_backup'
        
        if not backup_dir.exists():
            print("❌ 백업 디렉토리가 없습니다.")
            return False
        
        try:
            if self.frontend_dir.exists():
                shutil.rmtree(self.frontend_dir)
            
            shutil.copytree(backup_dir / 'frontend', self.frontend_dir)
            print("✅ 백업에서 복원 완료")
            return True
            
        except Exception as e:
            print(f"❌ 복원 실패: {e}")
            return False

def main():
    """메인 실행 함수"""
    builder = HashBasedBuilder()
    
    # 복원 옵션 확인
    if len(sys.argv) > 1 and sys.argv[1] == '--restore':
        print("🔄 백업에서 복원 중...")
        builder.restore_from_backup()
        return
    
    # 일반 빌드 실행
    success = builder.run_hash_build()
    
    if not success:
        print("\n💡 복원이 필요한 경우: python build.py --restore")
        sys.exit(1)

if __name__ == "__main__":
    main()