import os
import json
import re
import time
import logging
import warnings
import sys
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException

# 강력한 로그 억제
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['CUDA_VISIBLE_DEVICES'] = ''
os.environ['PYTHONWARNINGS'] = 'ignore'
os.environ['CHROME_LOG_FILE'] = 'nul' if os.name == 'nt' else '/dev/null'
os.environ['GOOGLE_API_KEY'] = ''
os.environ['SPEECH_DISPATCHER_LOG_LEVEL'] = '0'
warnings.filterwarnings('ignore')

# ABSL 로그 억제
import logging
logging.getLogger('absl').setLevel(logging.ERROR)
logging.getLogger('tensorflow').setLevel(logging.ERROR)


@dataclass
class CrawlConfig:
    """크롤링 설정"""
    base_url: str = "https://gall.dcinside.com/m"
    wait_timeout: int = 20
    retry_attempts: int = 3
    headless: bool = True
    save_dir: str = "id_data"
    save_filename: str = "mgalleries.json"
    category_wait_time: float = 3.0


class DCGalleryCrawler:
    """DC인사이드 갤러리 크롤러 (URL 직접 접근 방식)"""
    
    def __init__(self, config: CrawlConfig = None):
        self.config = config or CrawlConfig()
        self.driver: Optional[webdriver.Chrome] = None
        self.wait: Optional[WebDriverWait] = None
        self.gallery_map: Dict[str, str] = {}
        self._setup_logging()
    
    def _setup_logging(self):
        """로깅 설정"""
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)
        
        handlers = []
        
        try:
            file_handler = logging.FileHandler('crawler.log', encoding='utf-8')
            file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
            handlers.append(file_handler)
        except:
            pass
        
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
        handlers.append(console_handler)
        
        logging.basicConfig(level=logging.INFO, handlers=handlers, force=True)
        self.logger = logging.getLogger(__name__)
    
    def _create_chrome_options(self) -> Options:
        """Chrome 옵션 생성 (완전 억제)"""
        options = Options()
        
        if self.config.headless:
            options.add_argument("--headless=new")
        
        # 핵심 음성 기능 차단
        options.add_argument("--disable-features=VoiceTranscription,AudioServiceOutOfProcess,MediaSession,SpeechSynthesis,WebSpeech")
        options.add_argument("--disable-speech-api")
        options.add_argument("--mute-audio")
        
        # 성능 최적화
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-plugins")
        options.add_argument("--disable-images")
        options.add_argument("--disable-logging")
        options.add_argument("--log-level=3")
        options.add_argument("--silent")
        
        # 실험적 옵션
        options.add_experimental_option('excludeSwitches', ['enable-logging', 'enable-automation'])
        options.add_experimental_option('useAutomationExtension', False)
        
        options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        
        return options
    
    def _setup_driver(self) -> bool:
        """웹드라이버 설정"""
        try:
            options = self._create_chrome_options()
            
            # stderr 완전 억제
            with open(os.devnull, 'w') as devnull:
                original_stderr = sys.stderr
                sys.stderr = devnull
                self.driver = webdriver.Chrome(options=options)
                sys.stderr = original_stderr
            
            self.wait = WebDriverWait(self.driver, self.config.wait_timeout)
            self.logger.info("웹드라이버 초기화 완료")
            return True
            
        except Exception as e:
            self.logger.error(f"웹드라이버 초기화 실패: {e}")
            return False
    
    def _get_all_categories_fresh(self) -> List[str]:
        """매번 새로운 페이지 로드로 카테고리 목록 가져오기"""
        try:
            # 완전히 새로운 페이지 로드
            self.driver.get(self.config.base_url)
            time.sleep(3)
            
            # 갤러리 전체보기 클릭
            all_btn = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), '갤러리 전체보기')]"))
            )
            all_btn.click()
            time.sleep(3)
            
            # 카테고리 버튼들 가져오기
            self.wait.until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".category_solt_area .inner ul li a"))
            )
            time.sleep(2)
            
            buttons = self.driver.find_elements(By.CSS_SELECTOR, ".category_solt_area .inner ul li a")
            labels = []
            
            for btn in buttons:
                try:
                    text = btn.text.strip()
                    if text and btn.is_displayed():
                        labels.append(text)
                except:
                    continue
            
            unique_labels = sorted(set(labels))
            self.logger.info(f"✅ {len(unique_labels)}개 카테고리 발견: {', '.join(unique_labels[:5])}...")
            return unique_labels
            
        except Exception as e:
            self.logger.error(f"카테고리 목록 가져오기 실패: {e}")
            return []
    
    def _process_category_fresh(self, label: str) -> Tuple[int, bool]:
        """매번 새로운 페이지 로드로 카테고리 처리"""
        try:
            self.logger.info(f"🔄 카테고리 '{label}' 처리 시작 (완전 새로고침)")
            
            # 1. 완전히 새로운 페이지 로드
            self.driver.get(self.config.base_url)
            time.sleep(3)
            
            # 2. 갤러리 전체보기 클릭
            all_btn = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), '갤러리 전체보기')]"))
            )
            all_btn.click()
            time.sleep(3)
            
            # 3. 카테고리 영역 로드 대기
            self.wait.until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".category_solt_area .inner ul li a"))
            )
            time.sleep(2)
            
            # 4. 타겟 카테고리 버튼 찾기
            buttons = self.driver.find_elements(By.CSS_SELECTOR, ".category_solt_area .inner ul li a")
            target_btn = None
            
            for btn in buttons:
                try:
                    if btn.text.strip() == label and btn.is_displayed():
                        target_btn = btn
                        break
                except:
                    continue
            
            if not target_btn:
                self.logger.error(f"카테고리 버튼 찾을 수 없음: {label}")
                return 0, False
            
            # 5. 카테고리 버튼 클릭
            self.driver.execute_script("arguments[0].scrollIntoView(true);", target_btn)
            time.sleep(1)
            self.driver.execute_script("arguments[0].click();", target_btn)
            self.logger.info(f"카테고리 '{label}' 클릭 완료")
            
           # 6. 결과 로드 대기 (디버그 강화)
            self.logger.info(f"'{label}' 결과 로드 대기 시작...")
            time.sleep(3)  # 초기 대기

            # 7. 결과 확인 (더 관대한 조건)
            start_time = time.time()
            max_wait = 25  # 15초 → 25초로 증가

            while time.time() - start_time < max_wait:
                try:
                    # 현재 상태 확인
                    result_boxes = self.driver.find_elements(By.CSS_SELECTOR, "#searchList .result_list .result_box")
                    gallery_links = self.driver.find_elements(By.CSS_SELECTOR, "#searchList .result_list .result_box a")
                    
                    elapsed = time.time() - start_time
                    
                    # 상세한 진행 상황 로깅
                    if int(elapsed) % 3 == 0:  # 3초마다
                        self.logger.info(f"'{label}' 대기 중... ({elapsed:.1f}초) - 결과박스: {len(result_boxes)}개, 링크: {len(gallery_links)}개")
                    
                    # 성공 조건 체크 (더 관대하게)
                    if len(result_boxes) >= 1 and len(gallery_links) >= 1:  # 최소 1개만 있어도 OK
                        # 유효성 검증
                        valid_links = []
                        for link in gallery_links:
                            try:
                                href = link.get_attribute("href")
                                text = link.text.strip()
                                if href and "list.php?id=" in href and text:
                                    valid_links.append((text, href))
                            except:
                                continue
                        
                        if len(valid_links) >= 1:  # 최소 1개 유효한 링크만 있으면 성공
                            self.logger.info(f"✅ '{label}' 로드 성공: {len(valid_links)}개 유효한 갤러리 발견")
                            
                            # 유효한 링크들 미리보기 (처음 3개)
                            for i, (name, href) in enumerate(valid_links[:3]):
                                gallery_id = re.search(r'id=([^&]+)', href)
                                if gallery_id:
                                    self.logger.info(f"  - {name} (ID: {gallery_id.group(1)})")
                            
                            time.sleep(1)  # 추가 안정화
                            break
                    
                    time.sleep(1)
                    
                except Exception as e:
                    self.logger.debug(f"로드 확인 중 오류: {e}")
                    time.sleep(1)
            else:
                # 타임아웃 시 더 자세한 디버그 정보
                try:
                    final_boxes = self.driver.find_elements(By.CSS_SELECTOR, "#searchList .result_list .result_box")
                    final_links = self.driver.find_elements(By.CSS_SELECTOR, "#searchList .result_list .result_box a")
                    search_list = self.driver.find_element(By.ID, "searchList")
                    
                    self.logger.error(f"'{label}' 타임아웃 상세 정보:")
                    self.logger.error(f"  - 결과 박스: {len(final_boxes)}개")
                    self.logger.error(f"  - 갤러리 링크: {len(final_links)}개")
                    self.logger.error(f"  - searchList 존재: {search_list is not None}")
                    
                    # searchList의 내용 일부 출력
                    if search_list:
                        content = search_list.text[:200] if search_list.text else "내용 없음"
                        self.logger.error(f"  - 내용 미리보기: {content}...")
                    
                    # 타임아웃이어도 링크가 있으면 진행 시도
                    if len(final_links) >= 1:
                        self.logger.warning(f"타임아웃이지만 {len(final_links)}개 링크 발견, 진행 시도")
                        # 계속 진행하여 추출 시도
                    else:
                        self.logger.error(f"'{label}' 완전 실패 - 링크 없음")
                        return 0, False
                        
                except Exception as e:
                    self.logger.error(f"타임아웃 디버그 중 오류: {e}")
                    return 0, False
            
            # 8. 갤러리 정보 추출
            try:
                a_tags = self.driver.find_elements(By.CSS_SELECTOR, "#searchList .result_list .result_box a")
                
                if not a_tags:
                    self.logger.warning(f"'{label}'에서 갤러리 링크 없음")
                    return 0, False
                
                count = self._extract_gallery_info(a_tags)
                
                if count > 0:
                    self.logger.info(f"✅ {label} → {count}개 갤러리 추출 완료")
                    return count, True
                else:
                    self.logger.warning(f"'{label}'에서 유효한 갤러리 추출 실패")
                    return 0, False
                    
            except Exception as e:
                self.logger.error(f"갤러리 정보 추출 오류: {e}")
                return 0, False
            
        except Exception as e:
            self.logger.error(f"카테고리 '{label}' 처리 중 오류: {e}")
            return 0, False
    
    def _extract_gallery_info(self, a_tags: List) -> int:
        """갤러리 정보 추출"""
        count = 0
        pattern = re.compile(r'list\.php\?id=([a-zA-Z0-9_]+)')
        
        for a_tag in a_tags:
            try:
                name = a_tag.text.strip()
                href = a_tag.get_attribute("href")
                
                if not name or not href:
                    continue
                
                match = pattern.search(href)
                if match:
                    board_id = match.group(1)
                    if name not in self.gallery_map:  # 중복 방지
                        self.gallery_map[name] = board_id
                        count += 1
                        
            except Exception as e:
                continue
        
        return count
    
    def _save_results(self) -> bool:
        """결과 저장"""
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            save_dir = os.path.join(current_dir, self.config.save_dir)
            save_path = os.path.join(save_dir, self.config.save_filename)
            
            os.makedirs(save_dir, exist_ok=True)
            
            sorted_map = dict(sorted(self.gallery_map.items()))
            
            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(sorted_map, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"📦 총 {len(sorted_map)}개 갤러리 저장 완료 → {save_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"결과 저장 실패: {e}")
            return False
    
    def crawl(self) -> bool:
        """메인 크롤링 실행"""
        start_time = time.time()
        
        try:
            self.logger.info("🚀 DC인사이드 갤러리 크롤링 시작 (새로운 방식)")
            
            if not self._setup_driver():
                return False
            
            # 카테고리 목록 가져오기
            categories = self._get_all_categories_fresh()
            if not categories:
                self.logger.error("카테고리 목록을 가져올 수 없음")
                return False
            
            total_galleries = 0
            failed_categories = []
            
            # 각 카테고리 처리
            for i, category in enumerate(categories, 1):
                self.logger.info(f"📂 진행률: {i}/{len(categories)} - 카테고리: {category}")
                
                count, success = self._process_category_fresh(category)
                
                if success:
                    total_galleries += count
                else:
                    failed_categories.append(category)
                
                # 카테고리 간 대기
                time.sleep(self.config.category_wait_time)
            
            # 실패한 카테고리 재시도
            if failed_categories:
                self.logger.info(f"🔁 실패한 카테고리 재시도: {len(failed_categories)}개")
                for category in failed_categories[:]:
                    count, success = self._process_category_fresh(category)
                    if success:
                        total_galleries += count
                        failed_categories.remove(category)
                    time.sleep(self.config.category_wait_time)
            
            # 결과 저장
            save_success = self._save_results()
            
            elapsed_time = time.time() - start_time
            self.logger.info(f"✅ 크롤링 완료 - 총 {total_galleries}개 갤러리 (소요시간: {elapsed_time:.1f}초)")
            
            if failed_categories:
                self.logger.warning(f"최종 실패한 카테고리: {', '.join(failed_categories)}")
            
            return save_success
            
        except Exception as e:
            self.logger.error(f"크롤링 중 예상치 못한 오류: {e}")
            return False
            
        finally:
            if self.driver:
                self.driver.quit()


def main():
    """메인 실행 함수"""
    print("🚀 DC인사이드 갤러리 크롤링을 시작합니다 (새로운 방식)...")
    print("📝 매 카테고리마다 페이지를 새로 로드하여 안정성을 확보합니다.")
    print()
    
    config = CrawlConfig(
        headless=True,           # 필요시 False로 바꿔서 브라우저 직접 확인
        wait_timeout=30,         # 25 → 30초로 증가
        retry_attempts=3,        # 2 → 3회로 증가
        category_wait_time=5.0   # 3.0 → 5.0초로 증가
    )
    
    try:
        # stderr 완전 억제로 실행
        import contextlib
        with contextlib.redirect_stderr(open(os.devnull, 'w')):
            crawler = DCGalleryCrawler(config)
            success = crawler.crawl()
            
    except KeyboardInterrupt:
        print("\n⚠️  사용자에 의해 중단되었습니다.")
        success = False
    except Exception as e:
        print(f"\n❌ 크롤링 중 오류: {e}")
        success = False
    
    print()
    
    if success:
        print("✅ 크롤링이 성공적으로 완료되었습니다!")
        print("📁 결과 파일: id_data/mgalleries.json")
    else:
        print("❌ 크롤링 중 오류가 발생했습니다.")
        print("📋 자세한 내용은 crawler.log 파일을 확인해주세요.")


if __name__ == "__main__":
    main()