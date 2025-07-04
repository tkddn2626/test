# ==================== First Visitor API Endpoints ====================
# PickPost 첫 번째 방문자 관리 API

import sqlite3
import os
import hashlib
import secrets
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# APIRouter 및 보안 스키마
first_visitor_router = APIRouter()
security = HTTPBearer(auto_error=False)

# ==================== 환경변수 기반 설정 ====================
class Config:
    # 관리자 계정 (환경변수에서 읽기)
    ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD_HASH = os.getenv(
        "ADMIN_PASSWORD_HASH", 
        "601fc315b0ca91461cc66a1b48899208e67a8e123818e24d1a26f7ac31b6f8f9"  # pickpost2025!
    )
    SECRET_KEY = os.getenv("SECRET_KEY", "change-this-in-production-32-chars-min")
    TOKEN_EXPIRY = int(os.getenv("TOKEN_EXPIRY", "7200"))  # 2시간

# ==================== 데이터 모델 ====================
class AdminLogin(BaseModel):
    username: str
    password: str

class AdminLoginResponse(BaseModel):
    success: bool
    token: str
    message: str
    expiresIn: int

class FirstVisitorClaim(BaseModel):
    name: str
    timestamp: str
    url: str
    userAgent: str
    language: str
    fingerprint: str

class FirstVisitorResponse(BaseModel):
    isFirstVisitor: bool

class ClaimResponse(BaseModel):
    success: bool
    message: str

# ==================== 인증 함수 ====================
def hash_password(password: str) -> str:
    """비밀번호 SHA256 해시화"""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password: str, hashed: str) -> bool:
    """비밀번호 검증"""
    return hash_password(password) == hashed

def generate_admin_token() -> str:
    """관리자 토큰 생성"""
    return f"admin_{secrets.token_urlsafe(32)}_{int(datetime.now().timestamp())}"

def verify_admin_token(token: str) -> bool:
    """관리자 토큰 검증"""
    if not token or not token.startswith("admin_"):
        return False
    
    try:
        parts = token.split("_")
        if len(parts) < 3:
            return False
        
        timestamp = int(parts[-1])
        current_time = int(datetime.now().timestamp())
        
        # 토큰 만료 체크
        return (current_time - timestamp) < Config.TOKEN_EXPIRY
    except:
        return False

async def verify_admin(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """관리자 인증 의존성"""
    if not credentials:
        raise HTTPException(
            status_code=401, 
            detail="인증이 필요합니다",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    if not verify_admin_token(credentials.credentials):
        raise HTTPException(
            status_code=401, 
            detail="유효하지 않거나 만료된 토큰입니다",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    return credentials.credentials

# ==================== 데이터베이스 관리 ====================
class FirstVisitorDB:
    def __init__(self, db_path: str = "pickpost.db"):
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        """데이터베이스 테이블 초기화"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS first_visitor (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        url TEXT,
                        user_agent TEXT,
                        language TEXT,
                        fingerprint TEXT,
                        ip_address TEXT,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.commit()
                logger.info("첫 번째 방문자 테이블 초기화 완료")
        except Exception as e:
            logger.error(f"데이터베이스 초기화 실패: {e}")
            raise
    
    def has_first_visitor(self) -> bool:
        """첫 번째 방문자 등록 여부 확인"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM first_visitor LIMIT 1")
                count = cursor.fetchone()[0]
                return count > 0
        except Exception as e:
            logger.error(f"첫 번째 방문자 체크 실패: {e}")
            raise
    
    def claim_first_visitor(self, claim_data: FirstVisitorClaim, ip_address: str) -> bool:
        """첫 번째 방문자 등록 시도"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 동시성 문제 방지를 위한 재확인
                cursor.execute("SELECT COUNT(*) FROM first_visitor")
                count = cursor.fetchone()[0]
                
                if count > 0:
                    return False  # 이미 등록됨
                
                # 첫 번째 방문자 등록
                cursor.execute("""
                    INSERT INTO first_visitor 
                    (name, timestamp, url, user_agent, language, fingerprint, ip_address)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    claim_data.name,
                    claim_data.timestamp,
                    claim_data.url,
                    claim_data.userAgent,
                    claim_data.language,
                    claim_data.fingerprint,
                    ip_address
                ))
                
                conn.commit()
                logger.info(f"첫 번째 방문자 등록 성공: {claim_data.name}")
                return True
                
        except Exception as e:
            logger.error(f"첫 번째 방문자 등록 실패: {e}")
            raise
    
    def get_first_visitor_info(self) -> Optional[dict]:
        """첫 번째 방문자 정보 조회"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM first_visitor 
                    ORDER BY created_at ASC 
                    LIMIT 1
                """)
                
                row = cursor.fetchone()
                if row:
                    columns = [description[0] for description in cursor.description]
                    return dict(zip(columns, row))
                return None
                
        except Exception as e:
            logger.error(f"첫 번째 방문자 정보 조회 실패: {e}")
            raise

# 전역 데이터베이스 인스턴스
first_visitor_db = FirstVisitorDB()

# ==================== 유틸리티 함수 ====================
def get_client_ip(request: Request) -> str:
    """클라이언트 IP 주소 추출"""
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    return request.client.host if request.client else "unknown"

# ==================== API 엔드포인트 ====================

@first_visitor_router.post("/api/admin/login", response_model=AdminLoginResponse)
async def admin_login(login_data: AdminLogin):
    """관리자 로그인"""
    try:
        # 사용자명 및 비밀번호 검증
        if (login_data.username != Config.ADMIN_USERNAME or
            not verify_password(login_data.password, Config.ADMIN_PASSWORD_HASH)):
            raise HTTPException(status_code=401, detail="사용자명 또는 비밀번호가 올바르지 않습니다")
        
        # 토큰 생성
        token = generate_admin_token()
        
        logger.info(f"관리자 로그인 성공: {login_data.username}")
        
        return AdminLoginResponse(
            success=True,
            token=token,
            message="로그인 성공",
            expiresIn=Config.TOKEN_EXPIRY
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"관리자 로그인 API 오류: {e}")
        raise HTTPException(status_code=500, detail="서버 오류가 발생했습니다")

@first_visitor_router.get("/api/check-first-visitor", response_model=FirstVisitorResponse)
async def check_first_visitor():
    """첫 번째 방문자 등록 여부 확인"""
    try:
        has_first = first_visitor_db.has_first_visitor()
        # isFirstVisitor는 아직 첫 번째 방문자가 없을 때 true
        is_first_visitor = not has_first
        
        logger.info(f"첫 번째 방문자 체크: isFirstVisitor={is_first_visitor}")
        
        return FirstVisitorResponse(isFirstVisitor=is_first_visitor)
        
    except Exception as e:
        logger.error(f"첫 번째 방문자 체크 API 오류: {e}")
        raise HTTPException(status_code=500, detail="서버 오류가 발생했습니다")

@first_visitor_router.post("/api/claim-first-visitor", response_model=ClaimResponse)
async def claim_first_visitor(claim_data: FirstVisitorClaim, request: Request):
    """첫 번째 방문자 등록"""
    try:
        # 입력 검증
        if not claim_data.name or len(claim_data.name.strip()) == 0:
            raise HTTPException(status_code=400, detail="이름을 입력해주세요")
        
        if len(claim_data.name.strip()) > 50:
            raise HTTPException(status_code=400, detail="이름은 50자 이내로 입력해주세요")
        
        # 클라이언트 IP 추출
        client_ip = get_client_ip(request)
        
        # 첫 번째 방문자 등록 시도
        success = first_visitor_db.claim_first_visitor(claim_data, client_ip)
        
        if success:
            logger.info(f"첫 번째 방문자 등록 성공: {claim_data.name} (IP: {client_ip})")
            return ClaimResponse(
                success=True, 
                message="축하합니다! 당신이 첫 번째 방문자입니다!"
            )
        else:
            logger.warning(f"첫 번째 방문자 등록 실패 - 이미 등록됨: {claim_data.name}")
            raise HTTPException(
                status_code=409, 
                detail="이미 다른 분이 첫 번째 방문자로 등록되었습니다"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"첫 번째 방문자 등록 API 오류: {e}")
        raise HTTPException(status_code=500, detail="서버 오류가 발생했습니다")

@first_visitor_router.get("/api/admin/first-visitor-info")
async def get_first_visitor_info(token: str = Depends(verify_admin)):
    """첫 번째 방문자 정보 조회 (관리자 전용)"""
    try:
        first_visitor_info = first_visitor_db.get_first_visitor_info()
        
        if first_visitor_info:
            # 민감한 정보 제외하고 반환
            safe_info = {
                "id": first_visitor_info["id"],
                "name": first_visitor_info["name"],
                "timestamp": first_visitor_info["timestamp"],
                "language": first_visitor_info["language"],
                "created_at": first_visitor_info["created_at"]
            }
            logger.info(f"관리자가 첫 번째 방문자 정보 조회: {first_visitor_info['name']}")
            return safe_info
        else:
            return {"message": "아직 첫 번째 방문자가 등록되지 않았습니다"}
        
    except Exception as e:
        logger.error(f"첫 번째 방문자 정보 조회 API 오류: {e}")
        raise HTTPException(status_code=500, detail="서버 오류가 발생했습니다")

@first_visitor_router.delete("/api/admin/reset-first-visitor")
async def reset_first_visitor(token: str = Depends(verify_admin)):
    """첫 번째 방문자 데이터 삭제 (관리자 전용)"""
    try:
        # 현재 첫 번째 방문자 정보 백업 (로깅용)
        current_visitor = first_visitor_db.get_first_visitor_info()
        
        if not current_visitor:
            return {"success": False, "message": "삭제할 첫 번째 방문자 데이터가 없습니다"}
        
        # 데이터 삭제
        with sqlite3.connect(first_visitor_db.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM first_visitor")
            deleted_count = cursor.rowcount
            conn.commit()
        
        if deleted_count > 0:
            logger.warning(f"관리자가 첫 번째 방문자 데이터 삭제: {current_visitor['name']} (ID: {current_visitor['id']})")
            return {
                "success": True, 
                "message": f"첫 번째 방문자 '{current_visitor['name']}' 데이터가 삭제되었습니다",
                "deletedVisitor": {
                    "name": current_visitor['name'],
                    "registeredAt": current_visitor['created_at']
                }
            }
        else:
            return {"success": False, "message": "삭제할 데이터가 없습니다"}
        
    except Exception as e:
        logger.error(f"첫 번째 방문자 데이터 삭제 API 오류: {e}")
        raise HTTPException(status_code=500, detail="데이터 삭제 중 오류가 발생했습니다")

@first_visitor_router.post("/api/feedback")
async def enhanced_feedback(feedback_data: dict, request: Request):
    """피드백 API (첫 번째 방문자 정보 포함)"""
    try:
        client_ip = get_client_ip(request)
        
        # 피드백 데이터 강화
        enhanced_data = {
            **feedback_data,
            "client_ip": client_ip,
            "received_at": datetime.now().isoformat()
        }
        
        # 첫 번째 방문자 관련 피드백 로깅
        if feedback_data.get("type") == "first_visitor":
            logger.info(f"첫 번째 방문자 피드백: {feedback_data.get('name', 'Unknown')}")
        elif feedback_data.get("type") == "present_visitor":
            logger.info(f"선물 방문자 피드백: {feedback_data.get('name', 'Unknown')}")
        
        # 실제 환경에서는 여기서 데이터베이스 저장 또는 이메일 발송
        logger.info(f"피드백 수신: {feedback_data.get('description', 'No description')[:50]}...")
        
        return {"success": True, "message": "피드백이 성공적으로 전송되었습니다"}
        
    except Exception as e:
        logger.error(f"피드백 API 오류: {e}")
        raise HTTPException(status_code=500, detail="피드백 전송 중 오류가 발생했습니다")

# ==================== 개발용 유틸리티 ====================
def reset_first_visitor_data():
    """첫 번째 방문자 데이터 초기화 (개발용)"""
    try:
        with sqlite3.connect(first_visitor_db.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM first_visitor")
            conn.commit()
        logger.info("첫 번째 방문자 데이터 초기화 완료")
        return True
    except Exception as e:
        logger.error(f"데이터 초기화 실패: {e}")
        return False

# ==================== 메인 실행 및 테스트 ====================
if __name__ == "__main__":
    print("🌟 PickPost 첫 번째 방문자 시스템")
    print("=" * 50)
    
    # 데이터베이스 초기화
    print("📊 데이터베이스 초기화 중...")
    try:
        db = FirstVisitorDB()
        print("✅ 데이터베이스 초기화 완료")
    except Exception as e:
        print(f"❌ 데이터베이스 초기화 실패: {e}")
        exit(1)
    
    # 현재 상태 확인
    print("\n📋 현재 상태:")
    try:
        has_first = db.has_first_visitor()
        if has_first:
            info = db.get_first_visitor_info()
            print(f"✅ 첫 번째 방문자: {info['name']}")
            print(f"📅 등록 시간: {info['created_at']}")
        else:
            print("⏳ 첫 번째 방문자 대기 중")
    except Exception as e:
        print(f"❌ 상태 확인 실패: {e}")
    
    # 환경변수 상태 확인
    print(f"\n🔐 환경변수 상태:")
    print(f"  ADMIN_USERNAME: {'✅ 설정됨' if 'ADMIN_USERNAME' in os.environ else '❌ 기본값'}")
    print(f"  ADMIN_PASSWORD_HASH: {'✅ 설정됨' if 'ADMIN_PASSWORD_HASH' in os.environ else '❌ 기본값'}")
    print(f"  SECRET_KEY: {'✅ 설정됨' if 'SECRET_KEY' in os.environ else '❌ 기본값'}")
    
    if Config.SECRET_KEY == "change-this-in-production-32-chars-min":
        print("\n⚠️ 프로덕션 환경에서는 SECRET_KEY를 변경하세요!")
    
    print(f"\n💡 기본 로그인 정보:")
    print(f"  사용자명: {Config.ADMIN_USERNAME}")
    print(f"  비밀번호: pickpost2025!")
    
    print("\n🚀 시스템 준비 완료!")