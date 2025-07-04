from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import json
import re
import os

def crawl_galleries():
    # 현재 파일의 위치를 기준으로 저장 경로 설정
    current_dir = os.path.dirname(os.path.abspath(__file__))
    save_dir = os.path.join(current_dir, "id_data")
    save_path = os.path.join(save_dir, "galleries.json")

    # 크롬 옵션 설정
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=options)
    driver.get("https://gall.dcinside.com/")

    try:
        all_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), '갤러리 전체보기')]"))
        )
        all_btn.click()

        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.key_search_area ul li a"))
        )
    except Exception as e:
        print("❌ 초기 로딩 실패:", e)
        driver.quit()
        return

    gallery_map = {}

    try:
        consonant_buttons = driver.find_elements(By.CSS_SELECTOR, "div.key_search_area ul li a")
        if len(consonant_buttons) < 15:
            print(f"⚠️ 버튼이 {len(consonant_buttons)}개만 탐색됨 → 1회 자동 재시도")
            WebDriverWait(driver, 3).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.key_search_area ul li a"))
            )
            consonant_buttons = driver.find_elements(By.CSS_SELECTOR, "div.key_search_area ul li a")

        button_labels = sorted(set(btn.text.strip() for btn in consonant_buttons if btn.text.strip()))

        if len(button_labels) < 15:
            print(f"\n❗ 여전히 {len(button_labels)}개 자음/영문 버튼만 탐색됨")
            retry_input = input("⏳ 마지막으로 다시 시도할까요? (y/n): ").strip().lower()
            if retry_input == "y":
                print("🔁 최종 탐색 재시도 중...")
                WebDriverWait(driver, 3).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div.key_search_area ul li a"))
                )
                consonant_buttons = driver.find_elements(By.CSS_SELECTOR, "div.key_search_area ul li a")
                button_labels = sorted(set(btn.text.strip() for btn in consonant_buttons if btn.text.strip()))
            else:
                print("🚫 사용자 선택으로 탐색 중단. 프로그램 종료.")
                driver.quit()
                return

        if len(button_labels) < 15:
            print(f"❌ 최종적으로 {len(button_labels)}개만 확보됨 → 15개 미만으로 종료합니다.")
            driver.quit()
            return

        print(f"🔍 최종 {len(button_labels)}개 자음/영문 버튼 정렬 완료.")
    except Exception as e:
        print("❌ 버튼 수집 실패:", e)
        driver.quit()
        return

    clicked_labels = set()
    failed_labels = []

    def process_button(label, force_refind=False):
        try:
            if force_refind:
                btn_xpath = f"//a[normalize-space(text())='{label}']"
                element = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, btn_xpath))
                )
            else:
                element = next(
                    btn for btn in driver.find_elements(By.CSS_SELECTOR, "div.key_search_area ul li a")
                    if btn.text.strip() == label
                )

            prev_html = driver.find_element(By.ID, "searchList").get_attribute("innerHTML")

            print(f"\n➡️ '{label}' 버튼 클릭 시도")
            driver.execute_script("arguments[0].scrollIntoView(true);", element)
            WebDriverWait(driver, 5).until(EC.element_to_be_clickable(element))
            driver.execute_script("arguments[0].click();", element)

            WebDriverWait(driver, 10).until(
                lambda d: d.find_element(By.ID, "searchList").get_attribute("innerHTML") != prev_html
            )

            first_result = driver.find_element(By.CSS_SELECTOR, "#searchList .result_list")
            a_tags = first_result.find_elements(By.TAG_NAME, "a")

            count = 0
            for a_tag in a_tags:
                name = a_tag.text.strip()
                href = a_tag.get_attribute("href")

                board_id = re.sub(
                    r"""^\s*javascript:page_move\(\s*['"]\d+['"]\s*,\s*['"]([^'"]+)['"]\s*\)\s*;?\s*$""",
                    r"\1",
                    href,
                    flags=re.VERBOSE
                )

                if board_id and name:
                    gallery_map[name] = board_id
                    count += 1

            print(f"✅ '{label}' → {count}개 저장됨")
            clicked_labels.add(label)

        except Exception as e:
            print(f"❌ '{label}' 처리 중 오류: {e}")
            failed_labels.append(label)

    for label in button_labels:
        process_button(label)

    if failed_labels:
        print(f"\n🔁 실패한 버튼 재시도: {failed_labels}")
        for label in failed_labels:
            if label not in clicked_labels:
                process_button(label, force_refind=True)

    driver.quit()

    # 폴더 생성 후 JSON 저장
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    with open(save_path, "w", encoding="utf-8") as f:
        json.dump(gallery_map, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 최종 저장 완료: {len(gallery_map)}개 갤러리 → {save_path}")

if __name__ == "__main__":
    crawl_galleries()
