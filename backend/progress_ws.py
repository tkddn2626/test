'''# 📁 backend/websockets/progress_ws.py
from fastapi import WebSocket
import asyncio

# 테스트용 WebSocket 엔드포인트: 1~100까지 전송 (실제 적용 시 fetch_posts 내부에서 전송해야 함)
async def websocket_progress(websocket: WebSocket):
    await websocket.accept()
    try:
        for i in range(1, 101):
            await websocket.send_json({"progress": i})
            await asyncio.sleep(0.1)
    except Exception as e:
        print("WebSocket Error:", e)
    finally:
        await websocket.close()'''



from fastapi import WebSocket
import asyncio
from universal import crawl_universal_board

# 범용 크롤러용 WebSocket 엔드포인트
async def websocket_universal_progress(websocket: WebSocket):
    await websocket.accept()
    try:
        raw = await websocket.receive_text()
        import json
        config = json.loads(raw)

        url = config.get("board")
        limit = config.get("limit", 20)
        min_views = config.get("min_views", 0)
        min_likes = config.get("min_likes", 0)
        start_date = config.get("start_date")
        end_date = config.get("end_date")

        # 크롤링 실행
        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(None, crawl_universal_board, url, limit, min_views, min_likes, start_date, end_date)
        await websocket.send_json({"progress": 100})
        await websocket.send_json({"done": True, "data": data})

    except Exception as e:
        await websocket.send_json({"error": str(e)})
    finally:
        await websocket.close()
