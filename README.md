# PickPost - 커뮤니티 크롤링 & 번역 웹앱

Reddit, DCInside, Blind, Lemmy, BBC 등 다양한 커뮤니티에서 게시물을 조건 기반으로 크롤링하고, 번역 및 분석할 수 있는 웹 플랫폼입니다.

## 기능 요약
- 조건 기반 크롤링 (조회수, 추천수, 날짜 필터 등)
- 번역 기능 (DeepL API)
- 웹소켓 기반 진행률 표시
- 다양한 사이트 자동 인식 및 처리

## 설치 방법

```bash
git clone https://github.com/your-username/pickpost.git
cd pickpost/backend

# 가상 환경 설정 (선택)
python -m venv venv
source venv/bin/activate  # 또는 venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt

# 환경변수 설정
cp .env.template .env
# 그리고 .env 파일을 직접 수정하세요
```

## 실행

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

프론트엔드는 `/frontend/index.html`을 브라우저에서 열거나, Netlify 등에 업로드하면 됩니다.

## 보안 주의
`.env` 파일에는 개인 API 키가 들어있습니다. 공개 저장소에 업로드하지 마세요.
