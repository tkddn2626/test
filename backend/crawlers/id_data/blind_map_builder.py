# blind_map_builder.py - Selenium으로 블라인드 토픽 목록 수집
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import json
import os

def crawl_blind_boards():
    url = "https://www.teamblind.com/kr/topics/%ED%86%A0%ED%94%BD-%EC%A0%84%EC%B2%B4"

    # 현재 파일 위치 기준으로 저장 경로 설정
    current_dir = os.path.dirname(os.path.abspath(__file__))
    save_dir = os.path.join(current_dir, "id_data")
    save_path = os.path.join(save_dir, "boards.json")

    options = Options()
    # options.add_argument("--headless")  # 디버깅 시에는 주석 해제
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    # Headless 탐지 우회 설정
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)

    driver = webdriver.Chrome(options=options)

    # webdriver 감지 방지용 스크립트 실행
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": """
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        });
        """
    })

    driver.get(url)

    try:
        # 디버깅용 로그
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.topic")))
        print("✅ div.topic 로드됨")

        select_box = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.topic select"))
        )
        print("✅ select 태그 로드됨")

        options_list = select_box.find_elements(By.TAG_NAME, "option")

        board_map = {}
        for option in options_list:
            name = option.text.strip()
            value = option.get_attribute("value").strip()
            if value and name:
                board_map[name] = value

        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(board_map, f, ensure_ascii=False, indent=2)

        print(f"✅ {len(board_map)}개 블라인드 토픽 저장 완료 → {save_path}")

    except Exception as e:
        print("❌ 블라인드 토픽 목록 수집 실패:", repr(e))

    finally:
        driver.quit()

if __name__ == "__main__":
    crawl_blind_boards()
