# backend/database.py - Supabase 연결 및 피드백 저장 모듈

import os
import logging
from datetime import datetime
from typing import Dict, Optional, List
from fastapi import HTTPException

try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    logging.warning("supabase 패키지가 설치되지 않았습니다. pip install supabase로 설치하세요.")

# 로깅 설정
logger = logging.getLogger(__name__)

# Supabase 설정
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

# Supabase 클라이언트 초기화
supabase: Optional[Client] = None

if SUPABASE_AVAILABLE and SUPABASE_URL and SUPABASE_ANON_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
        logger.info("✅ Supabase 연결 성공")
    except Exception as e:
        logger.error(f"❌ Supabase 연결 실패: {e}")
        supabase = None
else:
    if not SUPABASE_AVAILABLE:
        logger.warning("⚠️ Supabase 패키지가 설치되지 않음")
    else:
        logger.warning("⚠️ Supabase 환경변수가 설정되지 않음 (SUPABASE_URL, SUPABASE_ANON_KEY)")

class DatabaseManager:
    """데이터베이스 관리 클래스"""
    
    def __init__(self):
        self.supabase = supabase
        self.is_available = supabase is not None
    
    async def save_feedback(self, feedback_data: Dict) -> Dict:
        """피드백을 Supabase에 저장"""
        
        if not self.is_available:
            raise HTTPException(
                status_code=500, 
                detail="데이터베이스 연결을 사용할 수 없습니다"
            )
        
        try:
            # 저장할 데이터 준비
            db_data = {
                "description": feedback_data.get("description", ""),
                "has_file": feedback_data.get("hasFile", False),
                "file_name": feedback_data.get("fileName"),
                "file_size": feedback_data.get("fileSize"),
                "system_info": feedback_data.get("systemInfo", {}),
                "current_language": feedback_data.get("currentLanguage", "ko"),
                "current_site": feedback_data.get("currentSite"),
                "url": feedback_data.get("url", ""),
                "user_agent": feedback_data.get("systemInfo", {}).get("userAgent"),
                "screen_resolution": feedback_data.get("systemInfo", {}).get("screenResolution"),
                "timezone": feedback_data.get("systemInfo", {}).get("timezone"),
                "status": "received",
                "metadata": feedback_data  # 전체 원본 데이터도 저장
            }
            
            # Supabase에 저장
            result = self.supabase.table('feedback').insert(db_data).execute()
            
            if result.data and len(result.data) > 0:
                feedback_id = result.data[0]['id']
                logger.info(f"✅ 피드백 저장 성공: ID {feedback_id}")
                return {
                    "feedback_id": feedback_id,
                    "status": "success",
                    "message": "피드백이 성공적으로 저장되었습니다"
                }
            else:
                raise Exception("저장 결과가 없습니다")
                
        except Exception as e:
            logger.error(f"❌ 피드백 저장 실패: {e}")
            raise HTTPException(
                status_code=500, 
                detail=f"피드백 저장 실패: {str(e)}"
            )
    
    async def get_feedback_list(self, limit: int = 50, offset: int = 0) -> Dict:
        """피드백 목록 조회 (관리자용)"""
        
        if not self.is_available:
            raise HTTPException(
                status_code=500,
                detail="데이터베이스 연결을 사용할 수 없습니다"
            )
        
        try:
            result = self.supabase.table('feedback')\
                .select("*")\
                .order('created_at', desc=True)\
                .range(offset, offset + limit - 1)\
                .execute()
            
            return {
                "success": True,
                "data": result.data,
                "count": len(result.data) if result.data else 0
            }
            
        except Exception as e:
            logger.error(f"❌ 피드백 조회 실패: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"피드백 조회 실패: {str(e)}"
            )
    
    async def update_feedback_status(self, feedback_id: int, status: str) -> Dict:
        """피드백 상태 업데이트"""
        
        if not self.is_available:
            raise HTTPException(
                status_code=500,
                detail="데이터베이스 연결을 사용할 수 없습니다"
            )
        
        try:
            result = self.supabase.table('feedback')\
                .update({"status": status})\
                .eq('id', feedback_id)\
                .execute()
            
            if result.data:
                logger.info(f"✅ 피드백 상태 업데이트: ID {feedback_id} -> {status}")
                return {
                    "success": True,
                    "message": f"피드백 상태가 {status}로 업데이트되었습니다"
                }
            else:
                raise Exception("업데이트할 피드백을 찾을 수 없습니다")
                
        except Exception as e:
            logger.error(f"❌ 피드백 상태 업데이트 실패: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"상태 업데이트 실패: {str(e)}"
            )

    def get_connection_status(self) -> Dict:
        """데이터베이스 연결 상태 반환"""
        return {
            "supabase_available": SUPABASE_AVAILABLE,
            "connection_active": self.is_available,
            "url_configured": bool(SUPABASE_URL),
            "key_configured": bool(SUPABASE_ANON_KEY)
        }

# 전역 데이터베이스 매니저 인스턴스
db_manager = DatabaseManager()

# 편의 함수들
async def save_feedback_to_database(feedback_data: Dict) -> Dict:
    """피드백 저장 편의 함수"""
    return await db_manager.save_feedback(feedback_data)

async def get_feedback_from_database(limit: int = 50, offset: int = 0) -> Dict:
    """피드백 조회 편의 함수"""
    return await db_manager.get_feedback_list(limit, offset)

def get_database_status() -> Dict:
    """데이터베이스 상태 조회 편의 함수"""
    return db_manager.get_connection_status()