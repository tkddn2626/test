// ==================== First One System ====================
// 맨 첫 번째 방문자 전용 시스템 (서버 기반 진정한 최초 방문자 체크)

// ==================== 설정 및 상수 ====================
const FIRST_ONE_CONFIG = {
    // 도메인 체크
    TARGET_DOMAINS: ['pick-post.com', 'www.pick-post.com'],
    
    // API 엔드포인트
    CHECK_FIRST_VISITOR_ENDPOINT: '/api/check-first-visitor',
    CLAIM_FIRST_VISITOR_ENDPOINT: '/api/claim-first-visitor',
    
    // 이미지 설정
    MODAL_IMAGES: {
        // 정적 이미지 URL (frontend/images 폴더의 이미지 사용)
        STATIC_URL: '/images/first-one.webp',
        
        // Base64 인코딩된 이미지 (작은 이미지 권장)
        BASE64_IMAGE: null,
        
        // 동적 생성 여부
        USE_DYNAMIC: false
    }
};

// ==================== 첫 번째 방문자 시스템 ====================
class FirstOneSystem {
    constructor() {
        this.isValidDomain = this.checkDomain();
        this.init();
    }

    /**
     * 도메인 체크 - pick-post.com 도메인인지 확인
     */
    checkDomain() {
        const hostname = window.location.hostname.toLowerCase();
        return FIRST_ONE_CONFIG.TARGET_DOMAINS.includes(hostname);
    }

    /**
     * 시스템 초기화
     */
    init() {
        if (!this.isValidDomain) {
            console.log('🏠 First One System: 대상 도메인이 아닙니다');
            return;
        }

        // DOM 로드 후 실행
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.checkVisitorStatus());
        } else {
            this.checkVisitorStatus();
        }
    }

    /**
     * 방문자 상태 확인 및 모달 표시
     */
    async checkVisitorStatus() {
        try {
            // 서버에서 첫 번째 방문자 상태 확인
            const isFirstVisitor = await this.checkFirstVisitorFromServer();
            
            if (isFirstVisitor) {
                // 진정한 첫 번째 방문자 - 모달 표시
                this.showFirstVisitorModal();
            } else {
                // 이미 첫 번째 방문자가 등록됨
                console.log('🏠 First One System: 이미 첫 번째 방문자가 등록되었습니다');
            }
        } catch (error) {
            console.error('First One System: 서버 체크 실패', error);
            // 서버 오류 시 조용히 넘어감 (모달 표시하지 않음)
        }
    }

    /**
     * 서버에서 첫 번째 방문자 여부 확인
     */
    async checkFirstVisitorFromServer() {
        const API_BASE_URL = (() => {
            // 전역 설정이 있으면 사용
            if (window.PickPostGlobals?.API_BASE_URL) {
                return window.PickPostGlobals.API_BASE_URL;
            }
            
            // 도메인에 따른 자동 설정
            const hostname = window.location.hostname;
            
            if (hostname === 'pick-post.com' || hostname === 'www.pick-post.com') {
                return 'https://pickpost.onrender.com';
            } else if (hostname === 'localhost' || hostname === '127.0.0.1') {
                return 'http://localhost:8000';
            } else {
                return 'https://pickpost.onrender.com'; // 기본값
            }
        })();
        
        try {
            const response = await fetch(`${API_BASE_URL}${FIRST_ONE_CONFIG.CHECK_FIRST_VISITOR_ENDPOINT}`, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const result = await response.json();
            return result.isFirstVisitor; // true면 첫 번째 방문자

        } catch (error) {
            console.error('첫 번째 방문자 체크 API 오류:', error);
            throw error;
        }
    }

    /**
     * 서버에 첫 번째 방문자 등록
     */
    async claimFirstVisitorToServer(name) {
        const API_BASE_URL = window.PickPostGlobals?.API_BASE_URL || 'https://pickpost.onrender.com';
        
        try {
            const response = await fetch(`${API_BASE_URL}${FIRST_ONE_CONFIG.CLAIM_FIRST_VISITOR_ENDPOINT}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    name: name.trim(),
                    timestamp: new Date().toISOString()
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const result = await response.json();
            return result.success;

        } catch (error) {
            console.error('첫 번째 방문자 등록 API 오류:', error);
            throw error;
        }
    }

    /**
     * 이름 해시 생성 (개인정보 보호)
     */
    async generateNameHash(str) {
        const encoder = new TextEncoder();
        const data = encoder.encode(str);
        const hashBuffer = await crypto.subtle.digest('SHA-256', data);
        const hashArray = Array.from(new Uint8Array(hashBuffer));
        const hashHex = hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
        return hashHex.substring(0, 16); // 16자리로 축약
    }

    /**
     * 첫 번째 방문자 모달 표시
     */
    showFirstVisitorModal() {
        // 모달 생성
        const modal = this.createFirstVisitorModal();
        document.body.appendChild(modal);
        
        // 정적 이미지 사용으로 변경 (동적 이미지 생성 코드 제거)
        
        // 애니메이션과 함께 표시
        setTimeout(() => {
            modal.classList.add('show');
        }, 150);

        console.log('🌟 First One System: 첫 번째 방문자 모달 표시');
    }

    /**
     * 첫 번째 방문자 모달 HTML 생성 (개선된 UI)
     */
    createFirstVisitorModal() {
        const modal = document.createElement('div');
        modal.className = 'first-one-modal';
        modal.id = 'firstOneModal';
        
        modal.innerHTML = `
            <div class="first-one-modal-overlay"></div>
            <div class="first-one-modal-content">
                <!-- 이미지 저장 버튼 (오른쪽 상단) -->
                <div class="first-one-save-btn" onclick="firstOneSystem.saveImage()" title="Save Image">
                    💾
                </div>
                
                <!-- 메인 컨텐츠 -->
                <div class="first-one-content">
                    <!-- 이미지 영역 -->
                    <div class="first-one-image-container">
                        ${this.createImageContent()}
                    </div>
                    
                    <!-- 메시지 -->
                    <div class="first-one-message">
                        You are the only one who chose me.
                    </div>
                    
                    <!-- 이름 입력 섹션 -->
                    <div class="first-one-name-section">
                        <div class="first-one-input-label">
                            I want to know your one and only name.
                        </div>
                        <div class="first-one-input-container">
                            <input 
                                type="text" 
                                id="firstOneName" 
                                class="first-one-input"
                                placeholder="Enter your name here..."
                                maxlength="50"
                            />
                            <button 
                                class="first-one-submit-btn" 
                                onclick="firstOneSystem.submitName()"
                                disabled
                            >
                                →
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // 이벤트 리스너 설정
        this.setupModalEventListeners(modal);
        
        return modal;
    }

    /**
     * 이미지 컨텐츠 생성 - 정적 이미지 사용
     */
    createImageContent() {
        const config = FIRST_ONE_CONFIG.MODAL_IMAGES;
        
        // 정적 이미지 URL 사용 (frontend/images 폴더의 이미지)
        if (config.STATIC_URL) {
            return `
                <img 
                    src="${config.STATIC_URL}" 
                    alt="You are the only one who chose me" 
                    class="first-one-modal-image"
                    onerror="this.style.display='none'; this.nextElementSibling.style.display='flex'"
                />
                <div class="first-one-image-placeholder" style="display: none;">
                    ✨ 이미지 공간 ✨
                    <div class="first-one-image-note">
                        특별한 이미지가 여기에 표시됩니다
                    </div>
                </div>
            `;
        }
        
        // 방법 2: Base64 이미지 사용
        else if (config.BASE64_IMAGE) {
            return `
                <img 
                    src="${config.BASE64_IMAGE}" 
                    alt="You are the only one who chose me" 
                    class="first-one-modal-image"
                />
            `;
        }
        
        // 방법 3: 플레이스홀더 (폴백)
        else {
            return `
                <div class="first-one-image-placeholder">
                    ✨ 이미지 공간 ✨
                    <div class="first-one-image-note">
                        특별한 이미지가 여기에 표시됩니다
                    </div>
                </div>
            `;
        }
    }

    /**
     * 모달 이벤트 리스너 설정
     */
    setupModalEventListeners(modal) {
        // 입력 필드 이벤트
        const nameInput = modal.querySelector('#firstOneName');
        const submitBtn = modal.querySelector('.first-one-submit-btn');
        
        if (nameInput && submitBtn) {
            // 실시간 입력 검증
            nameInput.addEventListener('input', (e) => {
                const value = e.target.value.trim();
                const isValid = value.length >= 1 && value.length <= 50;
                
                // 버튼 상태 업데이트
                submitBtn.disabled = !isValid;
                submitBtn.classList.toggle('active', isValid);
                
                // 에러 메시지 숨김
                const errorDiv = modal.querySelector('.first-one-error');
                if (errorDiv) {
                    errorDiv.style.display = 'none';
                }
            });
            
            // Enter 키 처리
            nameInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter' && !submitBtn.disabled) {
                    this.submitName();
                }
            });
        }
        
        // 모달 외부 클릭시 닫기 비활성화 (첫 번째 방문자는 특별하므로)
        modal.addEventListener('click', (e) => {
            if (e.target === modal || e.target.classList.contains('first-one-modal-overlay')) {
                // 외부 클릭 시에도 닫히지 않음
                e.stopPropagation();
            }
        });
    }

    /**
     * 이름 제출 처리
     */
    async submitName() {
        const nameInput = document.getElementById('firstOneName');
        const submitBtn = document.querySelector('.first-one-submit-btn');
        
        if (!nameInput || !submitBtn) {
            console.error('입력 요소를 찾을 수 없습니다');
            return;
        }
        
        const name = nameInput.value.trim();
        
        // 유효성 검사
        if (!name || name.length < 1 || name.length > 50) {
            this.showErrorMessage('Please enter a valid name (1-50 characters)');
            return;
        }
        
        // 버튼 비활성화
        submitBtn.disabled = true;
        submitBtn.innerHTML = '⏳';
        nameInput.disabled = true;
        
        try {
            // 서버에 첫 번째 방문자 등록
            const success = await this.claimFirstVisitorToServer(name);
            
            if (success) {
                // 성공 시 성공 화면 표시
                this.showSuccessMessage(name);
                console.log(`✅ First One System: 첫 번째 방문자 등록 완료 - ${name}`);
            } else {
                // 이미 등록된 경우
                this.showErrorMessage('Someone already claimed the first position. But you\'re still special! ✨');
            }
            
        } catch (error) {
            console.error('첫 번째 방문자 등록 실패:', error);
            this.showErrorMessage('Failed to register. Please try again.');
            
            // 버튼 복구
            submitBtn.disabled = false;
            submitBtn.innerHTML = '→';
            nameInput.disabled = false;
        }
    }

    /**
     * 성공 메시지 표시
     */
    showSuccessMessage(name) {
        const modal = document.getElementById('firstOneModal');
        const content = modal.querySelector('.first-one-content');
        
        if (content) {
            content.innerHTML = `
                <div class="first-one-success">
                    <div class="first-one-success-icon">🌟</div>
                    <div class="first-one-success-message">
                        Welcome, <strong>${name}</strong>!<br>
                        Your name has been remembered.
                    </div>
                </div>
            `;
        }
    }

    /**
     * 에러 메시지 표시
     */
    showErrorMessage(message = 'Failed to send. Please try again.') {
        const content = document.querySelector('.first-one-name-section');
        if (content) {
            // 에러 메시지 추가
            let errorDiv = content.querySelector('.first-one-error');
            if (!errorDiv) {
                errorDiv = document.createElement('div');
                errorDiv.className = 'first-one-error';
                content.appendChild(errorDiv);
            }
            
            errorDiv.textContent = message;
            errorDiv.style.display = 'block';
            
            // 5초 후 에러 메시지 숨김
            setTimeout(() => {
                errorDiv.style.display = 'none';
            }, 5000);
        }
    }

    /**
     * 이미지 저장 기능 - 정적 이미지 다운로드
     */
    async saveImage() {
        try {
            console.log('💾 First One System: 이미지 저장 시작');
            
            const saveBtn = document.querySelector('.first-one-save-btn');
            
            // 저장 버튼 상태 변경
            if (saveBtn) {
                saveBtn.innerHTML = '⏳';
                saveBtn.style.pointerEvents = 'none';
            }

            // 정적 이미지 URL에서 직접 다운로드
            const imageUrl = FIRST_ONE_CONFIG.MODAL_IMAGES.STATIC_URL;
            
            if (imageUrl) {
                // 파일명 생성
                const now = new Date();
                const timestamp = now.toISOString().replace(/[:.]/g, '-').slice(0, 19);
                const filename = `pickpost-first-one-${timestamp}.png`;
                
                // 이미지를 fetch로 가져와서 다운로드
                const response = await fetch(imageUrl);
                const blob = await response.blob();
                
                // Blob을 데이터 URL로 변환
                const reader = new FileReader();
                reader.onload = () => {
                    this.downloadImage(reader.result, filename);
                };
                reader.readAsDataURL(blob);
                
                // 성공 메시지 표시
                const successMsg = 'Image saved successfully! 💾';
                if (window.PickPostGlobals?.showMessage) {
                    window.PickPostGlobals.showMessage(successMsg, 'success');
                } else {
                    this.showTempMessage('Image saved! 💾', 'success');
                }
                
                console.log('✅ First One System: 이미지 저장 완료 -', filename);
            } else {
                throw new Error('이미지 URL을 찾을 수 없습니다');
            }

        } catch (error) {
            console.error('❌ First One System: 이미지 저장 실패', error);
            
            const errorMsg = 'Failed to save image. Please try again.';
            if (window.PickPostGlobals?.showMessage) {
                window.PickPostGlobals.showMessage(errorMsg, 'error');
            } else {
                this.showTempMessage('Save failed ❌', 'error');
            }
        } finally {
            // 저장 버튼 복구
            const saveBtn = document.querySelector('.first-one-save-btn');
            if (saveBtn) {
                saveBtn.innerHTML = '💾';
                saveBtn.style.pointerEvents = 'auto';
            }
        }
    }

    /**
     * 이미지 다운로드 실행
     */
    downloadImage(dataUrl, filename) {
        const link = document.createElement('a');
        link.href = dataUrl;
        link.download = filename;
        link.style.display = 'none';
        
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }

    /**
     * 임시 메시지 표시 (글로벌 메시지 시스템이 없을 때)
     */
    showTempMessage(message, type = 'info') {
        // 기존 임시 메시지 제거
        const existing = document.querySelector('.first-one-temp-message');
        if (existing) {
            existing.remove();
        }

        // 새 메시지 생성
        const messageDiv = document.createElement('div');
        messageDiv.className = `first-one-temp-message first-one-temp-${type}`;
        messageDiv.textContent = message;
        messageDiv.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: ${type === 'success' ? '#4caf50' : type === 'error' ? '#f44336' : '#2196f3'};
            color: white;
            padding: 12px 24px;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 500;
            z-index: 10001;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            transform: translateX(100%);
            transition: transform 0.3s ease;
        `;

        document.body.appendChild(messageDiv);

        // 애니메이션
        setTimeout(() => {
            messageDiv.style.transform = 'translateX(0)';
        }, 100);

        // 3초 후 제거
        setTimeout(() => {
            messageDiv.style.transform = 'translateX(100%)';
            setTimeout(() => {
                if (messageDiv.parentNode) {
                    messageDiv.remove();
                }
            }, 300);
        }, 3000);
    }

    /**
     * 동적 이미지 생성 (사용하지 않음 - 정적 이미지 사용)
     */
    createModalImage() {
        // 정적 이미지 사용으로 인해 이 함수는 더 이상 사용하지 않음
        console.log('🖼️ 정적 이미지 사용 중 - 동적 생성 건너뜀');
    }
}

// ==================== 스타일 추가 ====================
function addFirstOneStyles() {
    // 이미 추가된 경우 중복 방지
    if (document.getElementById('firstOneStyles')) {
        return;
    }

    const style = document.createElement('style');
    style.id = 'firstOneStyles';
    style.textContent = `
        .first-one-modal {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            z-index: 10000;
            opacity: 0;
            visibility: hidden;
            transition: all 0.3s ease;
        }

        .first-one-modal.show {
            opacity: 1;
            visibility: visible;
        }

        .first-one-modal-overlay {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.8);
            backdrop-filter: blur(5px);
        }

        .first-one-modal-content {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            max-width: 500px;
            width: 90vw;
            max-height: 90vh;
            overflow: hidden;
        }

        .first-one-save-btn {
            position: absolute;
            top: 16px;
            right: 16px;
            width: 40px;
            height: 40px;
            background: rgba(255, 255, 255, 0.9);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            font-size: 16px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
            transition: all 0.2s ease;
            z-index: 10;
            backdrop-filter: blur(10px);
        }

        .first-one-save-btn:hover {
            background: rgba(255, 255, 255, 1);
            transform: scale(1.1);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
        }

        .first-one-content {
            padding: 48px 32px;
            text-align: center;
        }

        .first-one-image-container {
            margin-bottom: 32px;
        }

        .first-one-modal-image {
            width: 200px;
            height: 200px;
            object-fit: cover;
            border-radius: 12px;
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
            margin: 0 auto;
            display: block;
        }

        .first-one-image-placeholder {
            width: 200px;
            height: 200px;
            border: 2px dashed #dadce0;
            border-radius: 12px;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            margin: 0 auto;
            color: #5f6368;
            font-size: 18px;
            background: #f8f9fa;
        }

        .first-one-image-note {
            font-size: 12px;
            margin-top: 8px;
            color: #9aa0a6;
        }

        .first-one-message {
            font-size: 24px;
            font-weight: 500;
            color: #202124;
            margin-bottom: 32px;
            line-height: 1.4;
        }

        .first-one-name-section {
            max-width: 360px;
            margin: 0 auto;
        }

        .first-one-input-label {
            font-size: 16px;
            color: #5f6368;
            margin-bottom: 16px;
            font-weight: 400;
            text-align: center;
            font-style: italic;
            line-height: 1.4;
        }

        .first-one-input-container {
            display: flex;
            gap: 12px;
            align-items: center;
        }

        .first-one-input {
            flex: 1;
            height: 48px;
            border: 2px solid #dadce0;
            border-radius: 24px;
            padding: 0 20px;
            font-size: 16px;
            outline: none;
            transition: all 0.2s ease;
        }

        .first-one-input::placeholder {
            color: #9aa0a6;
            font-style: italic;
        }

        .first-one-input:focus {
            border-color: #1a73e8;
            box-shadow: 0 0 0 3px rgba(26, 115, 232, 0.1);
        }

        .first-one-input:focus::placeholder {
            color: transparent;
        }

        .first-one-submit-btn {
            width: 48px;
            height: 48px;
            border: none;
            border-radius: 50%;
            background: #dadce0;
            color: white;
            font-size: 20px;
            cursor: pointer;
            transition: all 0.2s ease;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .first-one-submit-btn:disabled {
            cursor: not-allowed;
            opacity: 0.5;
        }

        .first-one-submit-btn.active {
            background: #1a73e8;
            transform: scale(1.05);
        }

        .first-one-submit-btn.active:hover {
            background: #1557b0;
            transform: scale(1.1);
        }

        .first-one-error {
            color: #d93025;
            font-size: 14px;
            margin-top: 12px;
            display: none;
        }

        .first-one-success {
            padding: 48px 24px;
        }

        .first-one-success-icon {
            font-size: 48px;
            margin-bottom: 24px;
        }

        .first-one-success-message {
            font-size: 18px;
            color: #1a73e8;
            line-height: 1.5;
        }

        /* 반응형 디자인 */
        @media (max-width: 480px) {
            .first-one-modal-content {
                width: 95vw;
            }
            
            .first-one-content {
                padding: 24px 16px;
            }
            
            .first-one-modal-image,
            .first-one-image-placeholder {
                width: 150px;
                height: 150px;
                font-size: 16px;
            }
            
            .first-one-message {
                font-size: 20px;
            }
        }
    `;
    
    document.head.appendChild(style);
}

// ==================== 초기화 ====================
// 스타일 추가
addFirstOneStyles();

// 전역 인스턴스 생성
const firstOneSystem = new FirstOneSystem();

// 전역 접근을 위한 window 객체에 등록
window.firstOneSystem = firstOneSystem;

// ==================== 내보내기 ====================
// 다른 모듈에서 사용할 수 있도록
if (typeof module !== 'undefined' && module.exports) {
    module.exports = FirstOneSystem;
}

console.log('🌟 First One System v2.2 로드 완료 - 정적 이미지 사용 및 다운로드 기능 개선');