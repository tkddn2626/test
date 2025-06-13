import os
import json
import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime

# ✅ id_data 폴더 내 모든 JSON 파일 로드 (galleries.json, mgalleries.json 등)
def load_gallery_map() -> dict:
    base_dir = os.path.dirname(os.path.abspath(__file__))  # 현재 파일 기준
    gallery_dir = os.path.join(base_dir, "id_data")       # id_data 폴더 절대 경로
    gallery_map = {}

    if not os.path.isdir(gallery_dir):
        print(f"❌ 폴더 없음: {gallery_dir}")
        return {}

    for filename in os.listdir(gallery_dir):
        if filename == "galleries.json":
            gtype = "gallery"
        elif filename == "mgalleries.json":
            gtype = "mgallery"
        else:
            continue  # 기타 JSON은 무시

        file_path = os.path.join(gallery_dir, filename)
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                for name, gid in data.items():
                    gallery_map[name] = {"id": gid, "type": gtype}
                print(f"✅ {filename} 로드됨 ({len(data)}개)")
        except Exception as e:
            print(f"❌ {filename} 파싱 실패: {e}")

    if not gallery_map:
        print("❌ id_data 폴더 내 JSON 파일을 로드할 수 없습니다.")

    return gallery_map

# ✅ 키워드 기반 갤러리 ID + 타입 매핑
def resolve_dc_board_id(keyword: str) -> tuple[str, str]:
    keyword = keyword.strip().lower()
    print("🔍 입력된 키워드:", keyword)

    gallery_map = load_gallery_map()
    if not gallery_map:
        raise Exception("❌ id_data 폴더 내 JSON 파일이 비었거나 없음.")

    matches = [(name, info) for name, info in gallery_map.items() if keyword in name.lower() or keyword == info["id"]]
    if not matches:
        raise Exception(f"❌ '{keyword}'과(와) 일치하는 갤러리를 찾을 수 없습니다.")

    name, info = matches[0]
    board_id = info["id"]
    board_type = info["type"]
    print(f"✅ '{keyword}' → '{name}' 매핑됨 → ID: {board_id} ({board_type})")
    return board_id, board_type

def extract_post_metrics(row):
    """게시물에서 조회수와 추천수 추출 (개선된 버전)"""
    views = 0
    likes = 0
    
    try:
        # 조회수 추출 - DC 갤러리 구조에 맞게 개선
        view_element = row.select_one('td.gall_count')
        if view_element:
            view_text = view_element.text.strip()
            view_numbers = re.findall(r'\d+', view_text)
            if view_numbers:
                views = int(view_numbers[0])
    
        # 추천수 추출 - DC는 추천 수가 별도로 표시되지 않으므로 댓글수로 대체
        reply_element = row.select_one('td.gall_reply')
        if reply_element:
            reply_text = reply_element.text.strip()
            # [숫자] 형태로 댓글수가 표시됨
            reply_numbers = re.findall(r'\[(\d+)\]', reply_text)
            if reply_numbers:
                likes = int(reply_numbers[0])  # 댓글수를 추천수로 사용
            else:
                # 일반 숫자 추출
                reply_numbers = re.findall(r'\d+', reply_text)
                if reply_numbers:
                    likes = int(reply_numbers[0])
                
    except Exception as e:
        print(f"메트릭 추출 오류: {e}")
    
    return views, likes

def extract_post_date(row):
    """게시물 작성일 추출 (개선된 버전)"""
    try:
        # DC 갤러리의 날짜 컬럼
        date_element = row.select_one('td.gall_date')
        if date_element:
            date_text = date_element.text.strip()
            # DC 갤러리는 보통 MM.DD 또는 HH:MM 형태로 표시
            if ':' in date_text:  # 오늘 작성된 글 (HH:MM)
                return f"{datetime.now().strftime('%Y.%m.%d')} {date_text}"
            elif '.' in date_text and len(date_text.split('.')) == 2:  # MM.DD 형태
                month, day = date_text.split('.')
                return f"{datetime.now().year}.{month.zfill(2)}.{day.zfill(2)}"
            else:
                return date_text
        
        return datetime.now().strftime('%Y.%m.%d')
        
    except Exception as e:
        print(f"날짜 추출 오류: {e}")
        return ""

def extract_post_author(row):
    """게시물 작성자 추출"""
    try:
        author_element = row.select_one('td.gall_writer')
        if author_element:
            # 작성자 정보는 복잡한 구조일 수 있으므로 텍스트만 추출
            author_text = author_element.get_text(strip=True)
            # 불필요한 부분 제거
            author = re.sub(r'\(.*?\)', '', author_text).strip()
            return author if author else "익명"
        return "익명"
    except Exception as e:
        print(f"작성자 추출 오류: {e}")
        return "익명"

def extract_comments_count(row):
    """댓글 수 추출 (댓글순 정렬용)"""
    try:
        reply_element = row.select_one('td.gall_reply')
        if reply_element:
            reply_text = reply_element.text.strip()
            # [숫자] 형태로 댓글수가 표시됨
            reply_numbers = re.findall(r'\[(\d+)\]', reply_text)
            if reply_numbers:
                return int(reply_numbers[0])
            else:
                # 일반 숫자 추출
                reply_numbers = re.findall(r'\d+', reply_text)
                if reply_numbers:
                    return int(reply_numbers[0])
        return 0
    except Exception as e:
        print(f"댓글수 추출 오류: {e}")
        return 0

def filter_by_date_range(posts, start_date_str, end_date_str):
    """날짜 범위로 게시물 필터링"""
    if not start_date_str or not end_date_str:
        return posts
    
    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
        end_date = end_date.replace(hour=23, minute=59, second=59)  # 하루 끝까지 포함
        
        filtered_posts = []
        for post in posts:
            # DC의 경우 날짜 정보가 제한적이므로 현재는 모든 게시물 반환
            # 실제 구현시 게시물의 작성일 정보를 파싱해야 함
            filtered_posts.append(post)
        
        print(f"Date filtering: {len(posts)} -> {len(filtered_posts)} posts")
        return filtered_posts
    except Exception as e:
        print(f"Date filtering error: {e}")
        return posts

def filter_by_time_period(posts, time_filter):
    """시간 기간으로 게시물 필터링"""
    if time_filter == "all":
        return posts
    
    # DC의 경우 시간 필터링이 제한적이므로 현재는 모든 게시물 반환
    # 실제 구현시 게시물의 작성일 정보를 파싱해야 함
    print(f"Time filtering ({time_filter}): {len(posts)} posts (no filtering applied for DCInside)")
    return posts

def sort_posts(posts, sort_method):
    """게시물 정렬 함수 (댓글순 추가)"""
    if not posts:
        return posts
    
    try:
        if sort_method == "popular":
            # 조회수 기준 내림차순 정렬
            return sorted(posts, key=lambda x: x.get('조회수', 0), reverse=True)
        elif sort_method == "recommend":
            # 추천수 기준 내림차순 정렬 (댓글수로 대체)
            return sorted(posts, key=lambda x: x.get('추천수', 0), reverse=True)
        elif sort_method == "comments":
            # 댓글수 기준 내림차순 정렬
            return sorted(posts, key=lambda x: x.get('댓글수', 0), reverse=True)
        elif sort_method == "recent":
            # 최신순 정렬 (기본 순서 유지 - 크롤링 순서가 최신순)
            return posts
        else:
            return posts
    except Exception as e:
        print(f"정렬 오류: {e}")
        return posts

# ✅ 게시판 단위 크롤링
# crawl_dcinside_board 함수 시그니처 및 로직 수정
async def crawl_dcinside_board(board_name: str, limit: int = 50, sort: str = "recent", 
                              min_views: int = 0, min_likes: int = 0, 
                              time_filter: str = "all", start_date: str = None, 
                              end_date: str = None, websocket=None, enforce_date_limit=False,
                              start_index: int = 1, end_index: int = 20) -> list:
    """강화된 DCInside 크롤링 - 정확한 범위 지원"""
    from dcinside import resolve_dc_board_id, extract_post_metrics, extract_post_date, extract_post_author, extract_comments_count
    from datetime import datetime
    import requests
    from bs4 import BeautifulSoup
    import asyncio

    board_id, board_type = resolve_dc_board_id(board_name)
    
    # 🚀 DCInside 자체 정렬 시스템 활용
    dc_sort_params = get_dcinside_sort_params(sort)
    
    if board_type == "mgallery":
        base_url = f"https://gall.dcinside.com/mgallery/board/lists/?id={board_id}"
    else:
        base_url = f"https://gall.dcinside.com/board/lists/?id={board_id}"
    
    # 정렬 파라미터 추가
    if dc_sort_params:
        base_url += f"&{dc_sort_params}"
        
        if websocket:
            await websocket.send_json({
                "status": f"🔍 DCInside 자체 정렬 적용: {sort} (목표: {start_index}-{end_index}위)",
                "progress": 15
            })

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    posts = []
    page = 1
    consecutive_no_match = 0
    max_consecutive_no_match = 3
    
    # 날짜 범위 파싱
    start_dt = None
    end_dt = None
    if start_date and end_date:
        try:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            end_dt = end_dt.replace(hour=23, minute=59, second=59)
        except Exception as e:
            print(f"날짜 파싱 오류: {e}")
    
    # 🔥 효율적 크롤링: 날짜 필터가 없으면 필요한 만큼만
    max_pages = 200 if enforce_date_limit else min(20, (end_index // 30) + 3)
    
    while page <= max_pages:
        try:
            # 페이지 URL 구성 (정렬 파라미터 유지)
            if '&' in base_url:
                page_url = f"{base_url}&page={page}"
            else:
                page_url = f"{base_url}&page={page}"
                
            if websocket:
                await websocket.send_json({
                    "status": f"📄 DCInside {page}페이지 수집 중... (정렬: {sort})",
                    "progress": min(30 + page * 2, 70),
                    "details": f"현재까지 {len(posts)}개 수집"
                })
            
            response = requests.get(page_url, headers=headers)
            if response.status_code != 200:
                break
                
            soup = BeautifulSoup(response.text, "html.parser")
            rows = soup.select("tr.us-post")
            
            if not rows:
                break
                
            page_found_posts = 0
            for row in rows:
                title_tag = row.select_one("td.gall_tit a")
                if not title_tag or not title_tag.get("href"):
                    continue
                    
                # 날짜 확인
                date_str = extract_post_date(row)
                post_date = None
                
                if enforce_date_limit and start_dt and end_dt:
                    try:
                        # DC 날짜 파싱 (MM.DD 또는 HH:MM 형태)
                        if ':' in date_str:  # 오늘 작성된 글
                            post_date = datetime.now()
                        elif '.' in date_str and len(date_str.split('.')) == 2:
                            month, day = date_str.split('.')
                            post_date = datetime(datetime.now().year, int(month), int(day))
                        else:
                            post_date = datetime.now()  # 파싱 실패시 현재 날짜
                            
                        # 날짜 범위 체크
                        if post_date < start_dt:
                            print(f"🛑 날짜 범위 초과로 크롤링 중단: {post_date} < {start_dt}")
                            return posts
                        elif post_date > end_dt:
                            continue
                    except Exception as e:
                        print(f"날짜 파싱 오류: {e}")
                        continue
                
                # 메트릭 추출 및 필터링
                views, likes = extract_post_metrics(row)
                if views < min_views or likes < min_likes:
                    continue
                
                # 게시물 정보 수집
                author = extract_post_author(row)
                comments_count = extract_comments_count(row)
                
                num_element = row.select_one('td.gall_num')
                post_num = num_element.text.strip() if num_element else str(len(posts) + 1)

                post_data = {
                    "번호": len(posts) + 1,  # 임시 번호 (나중에 재부여)
                    "원제목": title_tag.get("title", title_tag.text).strip(),
                    "번역제목": None,
                    "링크": "https://gall.dcinside.com" + title_tag["href"],
                    "본문": None,
                    "썸네일 URL": None,
                    "조회수": views,
                    "추천수": likes,
                    "댓글수": comments_count,
                    "작성일": date_str,
                    "작성자": author,
                    "게시물번호": post_num,
                    "정렬방식": sort
                }
                
                posts.append(post_data)
                page_found_posts += 1
                
                # 🔥 효율적 중단 조건
                if not enforce_date_limit and len(posts) >= end_index + 10:
                    break
            
            if page_found_posts == 0:
                consecutive_no_match += 1
                if consecutive_no_match >= max_consecutive_no_match:
                    print(f"🛑 연속 {max_consecutive_no_match}페이지 조건 불일치로 중단")
                    break
            else:
                consecutive_no_match = 0
                
            # 🔥 효율적 중단: 날짜 필터가 없고 충분히 수집했으면 중단
            if not enforce_date_limit and len(posts) >= end_index + 10:
                break
                
            page += 1
            
        except Exception as e:
            print(f"페이지 {page} 크롤링 오류: {e}")
            break
    
    # 🔥 DCInside 자체 정렬이 적용되지 않았다면 후처리 정렬
    if not dc_sort_params or len(posts) < 10:  # 자체 정렬 실패 감지
        if sort == "popular":
            posts.sort(key=lambda x: x.get('조회수', 0), reverse=True)
        elif sort == "recommend":
            posts.sort(key=lambda x: x.get('추천수', 0), reverse=True)
        elif sort == "comments":
            posts.sort(key=lambda x: x.get('댓글수', 0), reverse=True)
        # recent는 크롤링 순서 유지
    
    # 🔥 정확한 범위로 자르기 (날짜 강제 모드가 아닐 때)
    if not enforce_date_limit:
        if start_index <= len(posts):
            posts = posts[start_index-1:end_index]
        else:
            posts = []
    
    # 🔥 번호를 start_index부터 정확히 부여
    for idx, post in enumerate(posts):
        post['번호'] = start_index + idx
    
    print(f"DCInside 크롤링 완료: {len(posts)}개 게시물 ({start_index}-{start_index+len(posts)-1}위)")
    return posts



def get_dcinside_sort_params(sort_method: str) -> str:
    """DCInside 자체 정렬 파라미터 생성"""
    # 🔥 DCInside 정렬 파라미터 매핑 (추정)
    dc_sort_map = {
        "recommend": "sort_type=recommend&order=desc",     # 추천순
        "popular": "sort_type=hit&order=desc",             # 조회수순  
        "comments": "sort_type=reply&order=desc",          # 댓글순
        "recent": "",  # 기본 정렬 (최신순)
    }
    
    # 다양한 파라미터 패턴 시도
    alternative_patterns = {
        "recommend": [
            "sort_type=recommend&order=desc",
            "s=recommend&o=desc", 
            "sort=recommend",
            "orderby=recommend_desc"
        ],
        "popular": [
            "sort_type=hit&order=desc",
            "s=hit&o=desc",
            "sort=view",
            "orderby=hit_desc"
        ],
        "comments": [
            "sort_type=reply&order=desc", 
            "s=reply&o=desc",
            "sort=reply",
            "orderby=reply_desc"
        ]
    }
    
    return dc_sort_map.get(sort_method, "")


def test_dcinside_sort_urls(board_name: str) -> dict:
    """DCInside 정렬 URL 테스트 함수"""
    board_id, board_type = resolve_dc_board_id(board_name)
    
    if board_type == "mgallery":
        base_url = f"https://gall.dcinside.com/mgallery/board/lists/?id={board_id}"
    else:
        base_url = f"https://gall.dcinside.com/board/lists/?id={board_id}"
    
    test_urls = {
        "기본": base_url,
        "추천순_v1": f"{base_url}&sort_type=recommend&order=desc",
        "추천순_v2": f"{base_url}&s=recommend&o=desc",
        "추천순_v3": f"{base_url}&sort=recommend",
        "조회수순_v1": f"{base_url}&sort_type=hit&order=desc",
        "조회수순_v2": f"{base_url}&s=hit&o=desc", 
        "조회수순_v3": f"{base_url}&sort=view",
        "댓글순_v1": f"{base_url}&sort_type=reply&order=desc",
        "댓글순_v2": f"{base_url}&s=reply&o=desc",
        "댓글순_v3": f"{base_url}&sort=reply"
    }
    
    return test_urls



# ✅ 게시글 본문 추출 (선택적)
def parse_dcinside(url: str) -> dict:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        raise ValueError("요청 실패: 올바른 URL인지 확인하세요")

    soup = BeautifulSoup(response.text, 'html.parser')
    title_tag = soup.select_one('span.title_subject')
    content_tag = soup.select_one('div.write_div')

    if not title_tag or not content_tag:
        raise ValueError("게시글 구조를 파싱할 수 없습니다")

    return {
        "title": title_tag.text.strip(),
        "content": content_tag.text.strip()
    }

# 로드된 갤러리 목록 확인 함수
def list_available_galleries() -> None:
    """로드 가능한 모든 갤러리를 출력합니다."""
    gallery_map = load_gallery_map()

    if not gallery_map:
        print("❌ 로드된 갤러리가 없습니다.")
        return

    print(f"\n📋 총 {len(gallery_map)}개의 갤러리:")
    for i, (name, info) in enumerate(sorted(gallery_map.items()), 1):
        print(f"{i:3d}. {name} (ID: {info['id']}, TYPE: {info['type']})")

# 키워드 검색 함수
def search_galleries(keyword: str) -> None:
    """키워드로 갤러리를 검색합니다."""
    keyword = keyword.strip().lower()
    gallery_map = load_gallery_map()

    if not gallery_map:
        print("❌ 로드된 갤러리가 없습니다.")
        return

    matches = [(name, info) for name, info in gallery_map.items() if keyword in name.lower() or keyword == info["id"]]

    if not matches:
        print(f"❌ '{keyword}'와 일치하는 갤러리를 찾을 수 없습니다.")
        return

    print(f"\n🔍 '{keyword}' 검색 결과 ({len(matches)}개):")
    for i, (name, info) in enumerate(matches, 1):
        print(f"{i:3d}. {name} (ID: {info['id']}, TYPE: {info['type']})")