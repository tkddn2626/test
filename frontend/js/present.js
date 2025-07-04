// ==================== Present System ====================
// 첫 번째 방문자 이후 모든 방문자들을 위한 랜덤 축하 시스템 (동적 갯수 처리)

// ==================== 설정 및 상수 ====================
const PRESENT_CONFIG = {
    // 도메인 체크
    TARGET_DOMAINS: ['pick-post.com', 'www.pick-post.com'],
    
    // API 엔드포인트
    CHECK_FIRST_VISITOR_ENDPOINT: '/api/check-first-visitor',
    
    // localStorage 키
    CELEBRATION_COOLDOWN_KEY: 'pickpost_last_celebration',
    
    // 축하 메시지 쿨다운 (밀리초)
    CELEBRATION_COOLDOWN: {
        DAILY: 24 * 60 * 60 * 1000,        // 24시간
        WEEKLY: 7 * 24 * 60 * 60 * 1000    // 7일
    },
    
    // 랜덤 축하 확률 (1/N 확률)
    CELEBRATION_PROBABILITY: 50,
    
    // 이미지 및 문구 설정
    ASSETS: {
        // 이미지 파일 경로 패턴
        IMAGE_PATH: 'images/present/',
        IMAGE_PREFIX: 'bg-',
        IMAGE_EXTENSION: '.jpg',
        
        // 동적 갯수 설정 (0으로 설정하면 자동 감지)
        MAX_IMAGES: 0,      // 0 = 자동 감지, 숫자 = 고정 갯수
        MAX_MESSAGES: 0,    // 0 = 자동 감지, 숫자 = 고정 갯수
        
        // 문구 데이터 (번호는 1부터 시작, 자동으로 갯수 계산)
        MESSAGES: {
            1: { icon: "🎉", title: "You're today's lucky visitor!" },
            2: { icon: "⭐", title: "Welcome back, special one!" },
            3: { icon: "🌟", title: "You've been chosen for today!" },
            4: { icon: "🎊", title: "Congratulations! You're our featured visitor!" },
            5: { icon: "✨", title: "Today is your lucky day!" },
            6: { icon: "🎁", title: "You found a special moment!" },
            7: { icon: "💎", title: "You are precious to us!" },
            8: { icon: "🌈", title: "Rainbow luck is with you!" }
            // 새 문구 추가 시 여기에 계속 번호 증가시켜서 추가
            // 9: { icon: "🌺", title: "Flowers bloom for you today!" },
            // 10: { icon: "🎪", title: "Step right up to your special moment!" }
        }
    }
};

// ==================== Present 시스템 ====================
class PresentSystem {
    constructor() {
        this.isValidDomain = this.checkDomain();
        this.availableImages = 0;
        this.availableMessages = 0;
        this.assetsInitialized = false;
        this.init();
    }

    /**
     * 도메인 체크 - pick-post.com 도메인인지 확인
     */
    checkDomain() {
        const hostname = window.location.hostname.toLowerCase();
        return PRESENT_CONFIG.TARGET_DOMAINS.includes(hostname);
    }

    /**
     * 시스템 초기화
     */
    async init() {
        if (!this.isValidDomain) {
            console.log('🎁 Present System: 대상 도메인이 아닙니다');
            return;
        }

        try {
            // 에셋 갯수 초기화
            await this.initializeAssets();
            
            // 서버에서 첫 번째 방문자 상태 확인
            const isFirstVisitor = await this.checkFirstVisitorFromServer();
            
            if (isFirstVisitor) {
                console.log('🎁 Present System: 아직 첫 번째 방문자가 등록되지 않았습니다');
                return;
            }

            // DOM 로드 후 실행
            if (document.readyState === 'loading') {
                document.addEventListener('DOMContentLoaded', () => this.checkForPresent());
            } else {
                this.checkForPresent();
            }
        } catch (error) {
            console.error('Present System: 서버 체크 실패', error);
            // 서버 오류 시에도 present 시스템은 작동 (안전한 fallback)
            await this.initializeAssets();
            if (document.readyState === 'loading') {
                document.addEventListener('DOMContentLoaded', () => this.checkForPresent());
            } else {
                this.checkForPresent();
            }
        }
    }

    /**
     * 에셋 갯수 동적 초기화
     */
    async initializeAssets() {
        try {
            // 메시지 갯수 계산 (MESSAGES 객체의 키 갯수)
            const messageKeys = Object.keys(PRESENT_CONFIG.ASSETS.MESSAGES);
            this.availableMessages = PRESENT_CONFIG.ASSETS.MAX_MESSAGES > 0 
                ? PRESENT_CONFIG.ASSETS.MAX_MESSAGES 
                : messageKeys.length;

            // 이미지 갯수 동적 감지
            this.availableImages = PRESENT_CONFIG.ASSETS.MAX_IMAGES > 0 
                ? PRESENT_CONFIG.ASSETS.MAX_IMAGES 
                : await this.detectAvailableImages();

            console.log(`🎁 Present System: 에셋 초기화 완료`);
            console.log(`   📷 이미지: ${this.availableImages}개`);
            console.log(`   💬 문구: ${this.availableMessages}개`);
            console.log(`   🎲 총 조합: ${this.availableImages * this.availableMessages}가지`);

            this.assetsInitialized = true;
        } catch (error) {
            console.error('에셋 초기화 실패:', error);
            // 폴백: 기본값 사용
            this.availableImages = 5;
            this.availableMessages = Object.keys(PRESENT_CONFIG.ASSETS.MESSAGES).length;
            this.assetsInitialized = true;
        }
    }

    /**
     * 사용 가능한 이미지 갯수 동적 감지
     */
    async detectAvailableImages() {
        const config = PRESENT_CONFIG.ASSETS;
        let imageCount = 0;
        let consecutiveFailures = 0;
        const maxConsecutiveFailures = 3; // 연속 3번 실패하면 중단

        // 1번부터 시작해서 이미지가 존재하는지 확인
        for (let i = 1; i <= 50; i++) { // 최대 50개까지 확인
            const imagePath = `${config.IMAGE_PATH}${config.IMAGE_PREFIX}${i}${config.IMAGE_EXTENSION}`;
            
            try {
                const exists = await this.checkImageExists(imagePath);
                if (exists) {
                    imageCount = i;
                    consecutiveFailures = 0; // 성공하면 실패 카운트 리셋
                } else {
                    consecutiveFailures++;
                    if (consecutiveFailures >= maxConsecutiveFailures) {
                        break; // 연속 실패가 많으면 중단
                    }
                }
            } catch (error) {
                consecutiveFailures++;
                if (consecutiveFailures >= maxConsecutiveFailures) {
                    break;
                }
            }
        }

        return imageCount || 5; // 최소 5개 보장
    }

    /**
     * 이미지 존재 여부 확인
     */
    checkImageExists(imagePath) {
        return new Promise((resolve) => {
            const img = new Image();
            img.onload = () => resolve(true);
            img.onerror = () => resolve(false);
            
            // 타임아웃 설정 (2초)
            setTimeout(() => resolve(false), 2000);
            
            img.src = imagePath;
        });
    }

    /**
     * 랜덤 조합 생성
     */
    generateRandomCombination() {
        if (!this.assetsInitialized) {
            console.warn('에셋이 초기화되지 않았습니다. 기본값 사용');
            return this.getDefaultCombination();
        }

        // 랜덤 이미지 번호 (1부터 시작)
        const imageNumber = Math.floor(Math.random() * this.availableImages) + 1;
        
        // 랜덤 메시지 번호 (1부터 시작)
        const messageKeys = Object.keys(PRESENT_CONFIG.ASSETS.MESSAGES);
        const randomMessageKey = messageKeys[Math.floor(Math.random() * messageKeys.length)];
        const messageNumber = parseInt(randomMessageKey);

        const config = PRESENT_CONFIG.ASSETS;
        const imageUrl = `${config.IMAGE_PATH}${config.IMAGE_PREFIX}${imageNumber}${config.IMAGE_EXTENSION}`;
        const message = PRESENT_CONFIG.ASSETS.MESSAGES[messageNumber];

        const combination = {
            imageUrl: imageUrl,
            message: message,
            combinationId: `${imageNumber}-${messageNumber}`,
            imageNumber: imageNumber,
            messageNumber: messageNumber
        };

        console.log(`🎲 Present 조합 생성: 이미지 ${imageNumber}, 메시지 ${messageNumber}`);
        return combination;
    }

    /**
     * 기본 조합 반환 (폴백용)
     */
    getDefaultCombination() {
        return {
            imageUrl: `${PRESENT_CONFIG.ASSETS.IMAGE_PATH}${PRESENT_CONFIG.ASSETS.IMAGE_PREFIX}1${PRESENT_CONFIG.ASSETS.IMAGE_EXTENSION}`,
            message: PRESENT_CONFIG.ASSETS.MESSAGES[1] || { icon: "🎁", title: "You found a special moment!" },
            combinationId: "1-1",
            imageNumber: 1,
            messageNumber: 1
        };
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
            const response = await fetch(`${API_BASE_URL}${PRESENT_CONFIG.CHECK_FIRST_VISITOR_ENDPOINT}`, {
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
     * 선물(축하) 메시지 체크
     */
    checkForPresent() {
        const lastCelebration = localStorage.getItem(PRESENT_CONFIG.CELEBRATION_COOLDOWN_KEY);
        const now = Date.now();
        
        // 쿨다운 체크
        if (lastCelebration) {
            const timeDiff = now - parseInt(lastCelebration);
            const cooldownPeriod = this.getRandomCooldownPeriod();
            
            if (timeDiff < cooldownPeriod) {
                console.log('🎁 Present System: 아직 쿨다운 중입니다');
                return; // 아직 쿨다운 중
            }
        }
        
        // 확률 체크
        const shouldShowPresent = Math.random() < (1 / PRESENT_CONFIG.CELEBRATION_PROBABILITY);
        
        if (shouldShowPresent) {
            this.showPresentModal();
            localStorage.setItem(PRESENT_CONFIG.CELEBRATION_COOLDOWN_KEY, now.toString());
        }
    }

    /**
     * 랜덤 쿨다운 기간 반환 (1일 또는 1주일)
     */
    getRandomCooldownPeriod() {
        return Math.random() < 0.7 ? 
            PRESENT_CONFIG.CELEBRATION_COOLDOWN.DAILY : 
            PRESENT_CONFIG.CELEBRATION_COOLDOWN.WEEKLY;
    }

    /**
     * 선물 모달 표시
     */
    showPresentModal() {
        // 랜덤 조합 생성
        const combination = this.generateRandomCombination();
        
        // 모달 생성
        const modal = this.createPresentModal(combination);
        document.body.appendChild(modal);
        
        // 애니메이션과 함께 표시
        setTimeout(() => {
            modal.classList.add('show');
        }, 150);

        console.log(`🎁 Present System: 모달 표시 (조합: ${combination.combinationId})`);
    }

    /**
     * 선물 모달 HTML 생성 (개선된 UI)
     */
    createPresentModal(combination) {
        const modal = document.createElement('div');
        modal.className = 'present-modal';
        modal.id = 'presentModal';
        modal.dataset.combination = combination.combinationId; // 디버깅용
        
        modal.innerHTML = `
            <div class="present-modal-overlay"></div>
            <div class="present-modal-content">
                <!-- 이미지 저장 버튼 (오른쪽 상단) -->
                <div class="present-save-btn" onclick="presentSystem.saveImage()" title="Save Image">
                    💾
                </div>
                
                <!-- 메인 컨텐츠 -->
                <div class="present-content">
                    <!-- 이미지 영역 -->
                    <div class="present-image-container">
                        <img 
                            src="${combination.imageUrl}" 
                            alt="Present Special Image" 
                            class="present-modal-image"
                            loading="lazy"
                            onerror="this.style.display='none'; this.nextElementSibling.style.display='flex'"
                        />
                        <div class="present-image-placeholder" style="display: none;">
                            ${combination.message.icon}
                            <div class="present-image-note">
                                특별한 이미지가 여기에 표시됩니다
                            </div>
                        </div>
                    </div>
                    
                    <!-- 메시지 -->
                    <div class="present-message">
                        ${combination.message.title}
                    </div>
                    
                    <!-- 이름 입력 섹션 -->
                    <div class="present-name-section">
                        <!-- 입력창 위에 라벨 추가 -->
                        <div class="present-input-label">
                            I want to know your one and only name.
                        </div>
                        <div class="present-input-container">
                            <input 
                                type="text" 
                                id="presentName" 
                                class="present-input"
                                placeholder="Enter your name here..."
                                maxlength="50"
                            />
                            <button 
                                class="present-submit-btn" 
                                onclick="presentSystem.submitName()"
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
     * 모달 이벤트 리스너 설정
     */
    setupModalEventListeners(modal) {
        const nameInput = modal.querySelector('#presentName');
        const submitBtn = modal.querySelector('.present-submit-btn');

        // 입력값 변경 시 버튼 활성화
        nameInput.addEventListener('input', () => {
            const hasValue = nameInput.value.trim().length > 0;
            submitBtn.disabled = !hasValue;
            submitBtn.classList.toggle('active', hasValue);
        });

        // Enter 키 처리
        nameInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !submitBtn.disabled) {
                this.submitName();
            }
        });

        // 포커스 설정
        setTimeout(() => nameInput.focus(), 500);
    }

    /**
     * 이름 제출
     */
    async submitName() {
        const nameInput = document.getElementById('presentName');
        const submitBtn = document.querySelector('.present-submit-btn');
        
        if (!nameInput || !nameInput.value.trim()) {
            return;
        }

        const name = nameInput.value.trim();
        
        // 버튼 비활성화 및 로딩 상태
        submitBtn.disabled = true;
        submitBtn.textContent = '⏳';

        try {
            // 피드백 시스템으로 전송
            await this.sendToFeedbackSystem(name);
            
            // 성공 메시지 표시
            this.showSuccessMessage();
            
            // 모달 닫기
            setTimeout(() => {
                this.closeModal();
            }, 2000);

        } catch (error) {
            console.error('Present System: 이름 전송 실패', error);
            
            // 에러 메시지 표시
            this.showErrorMessage();
            
            // 버튼 복구
            submitBtn.disabled = false;
            submitBtn.textContent = '→';
        }
    }

    /**
     * 피드백 시스템으로 데이터 전송
     */
    async sendToFeedbackSystem(name) {
        const API_BASE_URL = window.PickPostGlobals?.API_BASE_URL || 'http://localhost:8000';
        
        // 현재 모달의 조합 정보 가져오기
        const modal = document.getElementById('presentModal');
        const combinationId = modal?.dataset.combination || 'unknown';
        
        const feedbackData = {
            description: `[PRESENT VISITOR] Special visitor name: ${name} (조합: ${combinationId})`,
            type: 'present_visitor',
            name: name,
            combinationId: combinationId,
            timestamp: new Date().toISOString(),
            url: window.location.href,
            userAgent: navigator.userAgent,
            language: window.modalManager?.getCurrentLanguage() || 'en'
        };

        const response = await fetch(`${API_BASE_URL}/api/feedback`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(feedbackData)
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        return response.json();
    }

    /**
     * 성공 메시지 표시
     */
    showSuccessMessage() {
        const content = document.querySelector('.present-content');
        if (content) {
            content.innerHTML = `
                <div class="present-success">
                    <div class="present-success-icon">🎁</div>
                    <div class="present-success-message">
                        Thank you for sharing your name!
                        <br>
                        You made this moment special.
                    </div>
                </div>
            `;
        }
    }

    /**
     * 에러 메시지 표시
     */
    showErrorMessage() {
        const content = document.querySelector('.present-name-section');
        if (content) {
            // 에러 메시지 추가
            let errorDiv = content.querySelector('.present-error');
            if (!errorDiv) {
                errorDiv = document.createElement('div');
                errorDiv.className = 'present-error';
                content.appendChild(errorDiv);
            }
            
            errorDiv.textContent = 'Failed to send. Please try again.';
            errorDiv.style.display = 'block';
            
            // 3초 후 에러 메시지 숨김
            setTimeout(() => {
                errorDiv.style.display = 'none';
            }, 3000);
        }
    }

    /**
     * 이미지 저장 기능 (HTML2Canvas 사용) - 개선됨
     */
    async saveImage() {
        try {
            console.log('💾 Present System: 이미지 저장 시작');
            
            const modal = document.getElementById('presentModal');
            const saveBtn = document.querySelector('.present-save-btn');
            
            if (!modal) {
                console.error('모달을 찾을 수 없습니다');
                this.showTempMessage('모달을 찾을 수 없습니다 ❌', 'error');
                return;
            }

            // 저장 버튼 상태 변경
            if (saveBtn) {
                saveBtn.innerHTML = '⏳';
                saveBtn.style.pointerEvents = 'none';
            }

            // html2canvas가 로드되어 있는지 확인
            if (typeof html2canvas === 'undefined') {
                console.log('html2canvas 라이브러리 로딩 중...');
                await this.loadHtml2Canvas();
            }

            // 캡처 대상 요소 선택
            const modalContent = modal.querySelector('.present-modal-content');
            if (!modalContent) {
                throw new Error('모달 콘텐츠를 찾을 수 없습니다');
            }

            // 이미지가 완전히 로드될 때까지 대기
            const img = modal.querySelector('.present-modal-image');
            if (img && !img.complete) {
                await new Promise(resolve => {
                    img.onload = resolve;
                    img.onerror = resolve;
                    setTimeout(resolve, 2000); // 2초 타임아웃
                });
            }

            // 모달 캡처 옵션 (개선됨)
            const options = {
                backgroundColor: '#ffffff',
                scale: 2, // 고화질
                useCORS: true,
                allowTaint: true,
                removeContainer: true,
                imageTimeout: 15000, // 15초로 증가
                logging: false, // 콘솔 로그 줄이기
                ignoreElements: (element) => {
                    // 저장 버튼 제외
                    return element.classList && element.classList.contains('present-save-btn');
                },
                onclone: (clonedDoc) => {
                    // 클론된 문서에서 저장 버튼 완전히 제거
                    const clonedSaveBtn = clonedDoc.querySelector('.present-save-btn');
                    if (clonedSaveBtn) {
                        clonedSaveBtn.remove();
                    }
                    
                    // 이미지 로딩 상태 확인
                    const images = clonedDoc.querySelectorAll('img');
                    images.forEach(img => {
                        if (!img.complete || img.naturalHeight === 0) {
                            console.warn('이미지 로딩 미완료:', img.src);
                        }
                    });
                }
            };

            console.log('html2canvas 캡처 시작...');
            
            // 모달 콘텐츠 캡처
            const capturedCanvas = await html2canvas(modalContent, options);
            
            console.log('캡처 완료, 이미지 변환 중...');
            
            // Canvas를 이미지로 변환 (PNG, 최고 품질)
            const imageData = capturedCanvas.toDataURL('image/png', 1.0);
            
            // 파일명 생성 (조합 정보 포함)
            const now = new Date();
            const timestamp = now.toISOString().replace(/[:.]/g, '-').slice(0, 19);
            const combinationId = modal.dataset.combination || 'unknown';
            const filename = `pickpost-present-${combinationId}-${timestamp}.png`;
            
            // 이미지 다운로드 실행
            this.downloadImage(imageData, filename);
            
            // 성공 메시지 표시
            const successMsg = 'Image saved successfully! 💾';
            if (window.PickPostGlobals?.showMessage) {
                window.PickPostGlobals.showMessage(successMsg, 'success');
            } else {
                this.showTempMessage('Image saved! 💾', 'success');
            }
            
            console.log('✅ Present System: 이미지 저장 완료 -', filename);

        } catch (error) {
            console.error('❌ Present System: 이미지 저장 실패', error);
            
            const errorMsg = 'Failed to save image. Please try again.';
            if (window.PickPostGlobals?.showMessage) {
                window.PickPostGlobals.showMessage(errorMsg, 'error');
            } else {
                this.showTempMessage('Save failed ❌', 'error');
            }
        } finally {
            // 저장 버튼 복구
            const saveBtn = document.querySelector('.present-save-btn');
            if (saveBtn) {
                saveBtn.innerHTML = '💾';
                saveBtn.style.pointerEvents = 'auto';
            }
        }
    }

    /**
     * html2canvas 라이브러리 동적 로드 (안정성 개선)
     */
    async loadHtml2Canvas() {
        return new Promise((resolve, reject) => {
            // 이미 로드된 경우
            if (typeof html2canvas !== 'undefined') {
                resolve();
                return;
            }

            // 이미 로딩 중인 스크립트가 있는지 확인
            const existingScript = document.querySelector('script[src*="html2canvas"]');
            if (existingScript) {
                // 기존 스크립트 로딩 완료 대기
                existingScript.onload = resolve;
                existingScript.onerror = reject;
                return;
            }

            const script = document.createElement('script');
            script.src = 'https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js';
            script.async = true;
            script.onload = () => {
                console.log('✅ html2canvas 라이브러리 로드됨');
                resolve();
            };
            script.onerror = (error) => {
                console.error('❌ html2canvas 라이브러리 로드 실패', error);
                reject(new Error('html2canvas 로드 실패'));
            };
            
            document.head.appendChild(script);
        });
    }

    /**
     * 이미지 파일 다운로드 (개선됨)
     */
    downloadImage(imageData, filename) {
        try {
            // Blob 방식으로 개선
            const byteCharacters = atob(imageData.split(',')[1]);
            const byteNumbers = new Array(byteCharacters.length);
            for (let i = 0; i < byteCharacters.length; i++) {
                byteNumbers[i] = byteCharacters.charCodeAt(i);
            }
            const byteArray = new Uint8Array(byteNumbers);
            const blob = new Blob([byteArray], {type: 'image/png'});
            
            // URL 생성 및 다운로드
            const url = URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = filename;
            
            // 임시로 DOM에 추가하여 클릭
            document.body.appendChild(link);
            link.click();
            
            // 정리
            document.body.removeChild(link);
            URL.revokeObjectURL(url);
            
            console.log('📥 이미지 다운로드 완료:', filename);
        } catch (error) {
            console.error('다운로드 실패:', error);
            
            // 폴백: 기존 방식
            try {
                const link = document.createElement('a');
                link.href = imageData;
                link.download = filename;
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
                console.log('📥 이미지 다운로드 완료 (폴백):', filename);
            } catch (fallbackError) {
                console.error('폴백 다운로드도 실패:', fallbackError);
                throw error;
            }
        }
    }

    /**
     * 임시 메시지 표시 (전역 메시지 시스템이 없을 때 사용)
     */
    showTempMessage(message, type = 'info') {
        const tempMsg = document.createElement('div');
        tempMsg.className = `temp-message temp-message-${type}`;
        tempMsg.textContent = message;
        tempMsg.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: ${type === 'success' ? '#4caf50' : type === 'error' ? '#f44336' : '#2196f3'};
            color: white;
            padding: 12px 20px;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 500;
            z-index: 10000;
            box-shadow: 0 4px 12px rgba(0,0,0,0.2);
            opacity: 0;
            transition: opacity 0.3s ease;
        `;
        
        document.body.appendChild(tempMsg);
        
        // 애니메이션 표시
        setTimeout(() => {
            tempMsg.style.opacity = '1';
        }, 100);
        
        // 3초 후 제거
        setTimeout(() => {
            tempMsg.style.opacity = '0';
            setTimeout(() => {
                if (tempMsg.parentNode) {
                    tempMsg.parentNode.removeChild(tempMsg);
                }
            }, 300);
        }, 3000);
    }

    /**
     * 모달 닫기
     */
    closeModal() {
        const modal = document.getElementById('presentModal');
        if (modal) {
            modal.classList.remove('show');
            setTimeout(() => {
                modal.remove();
            }, 300);
        }
    }

    /**
     * 에셋 상태 확인 (디버깅용)
     */
    getAssetStatus() {
        return {
            initialized: this.assetsInitialized,
            availableImages: this.availableImages,
            availableMessages: this.availableMessages,
            totalCombinations: this.availableImages * this.availableMessages,
            config: PRESENT_CONFIG.ASSETS,
            domain: window.location.hostname,
            isValidDomain: this.isValidDomain
        };
    }

    /**
     * 수동으로 Present 모달 표시 (테스트용)
     */
    showPresentModalManually() {
        console.log('🧪 Present System: 수동 모달 표시 (테스트용)');
        this.showPresentModal();
    }

    /**
     * 쿨다운 초기화 (테스트용)
     */
    resetCooldown() {
        localStorage.removeItem(PRESENT_CONFIG.CELEBRATION_COOLDOWN_KEY);
        console.log('🔄 Present System: 쿨다운 초기화됨');
    }
}

// ==================== CSS 스타일 추가 ====================
function addPresentStyles() {
    if (document.getElementById('presentStyles')) {
        return; // 이미 추가됨
    }

    const style = document.createElement('style');
    style.id = 'presentStyles';
    style.textContent = `
        /* Present Modal Styles - 개선된 스타일 */
        .present-modal {
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            z-index: 9999;
            opacity: 0;
            visibility: hidden;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }

        .present-modal.show {
            opacity: 1;
            visibility: visible;
        }

        .present-modal-overlay {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.8);
            backdrop-filter: blur(8px);
        }

        .present-modal-content {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: white;
            border-radius: 16px;
            box-shadow: 0 24px 48px rgba(0, 0, 0, 0.3);
            max-width: 480px;
            width: 90vw;
            max-height: 90vh;
            overflow: hidden;
            position: relative;
        }

        .present-save-btn {
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
            font-size: 18px;
            transition: all 0.2s ease;
            z-index: 10;
            border: 2px solid rgba(26, 115, 232, 0.2);
        }

        .present-save-btn:hover {
            background: rgba(26, 115, 232, 0.1);
            transform: scale(1.1);
        }

        .present-content {
            padding: 32px 24px;
            text-align: center;
        }

        .present-image-container {
            margin-bottom: 24px;
        }

        /* 모달 이미지 스타일 (개선됨) */
        .present-modal-image {
            width: 200px;
            height: 200px;
            border-radius: 12px;
            margin: 0 auto;
            display: block;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
            border: 2px solid #f8f9fa;
            object-fit: cover; /* 이미지 비율 유지하면서 크기 맞춤 */
            background: #f8f9fa; /* 로딩 중 배경색 */
            transition: all 0.3s ease;
        }

        .present-modal-image:hover {
            transform: scale(1.02);
            box-shadow: 0 6px 16px rgba(0, 0, 0, 0.2);
        }

        .present-image-placeholder {
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
            font-size: 48px;
            background: #f8f9fa;
        }

        .present-image-note {
            font-size: 12px;
            margin-top: 8px;
            color: #9aa0a6;
        }

        .present-message {
            font-size: 24px;
            font-weight: 500;
            color: #202124;
            margin-bottom: 32px;
            line-height: 1.4;
        }

        .present-name-section {
            max-width: 360px;
            margin: 0 auto;
        }

        .present-input-label {
            font-size: 16px;
            color: #5f6368;
            margin-bottom: 16px;
            font-weight: 400;
            text-align: center;
            font-style: italic;
            line-height: 1.4;
        }

        .present-input-container {
            display: flex;
            gap: 12px;
            align-items: center;
        }

        .present-input {
            flex: 1;
            height: 48px;
            border: 2px solid #dadce0;
            border-radius: 24px;
            padding: 0 20px;
            font-size: 16px;
            outline: none;
            transition: all 0.2s ease;
        }

        .present-input::placeholder {
            color: #9aa0a6;
            font-style: italic;
        }

        .present-input:focus {
            border-color: #1a73e8;
            box-shadow: 0 0 0 3px rgba(26, 115, 232, 0.1);
        }

        .present-input:focus::placeholder {
            color: transparent;
        }

        .present-submit-btn {
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

        .present-submit-btn:disabled {
            cursor: not-allowed;
            opacity: 0.5;
        }

        .present-submit-btn.active {
            background: #1a73e8;
            transform: scale(1.05);
        }

        .present-submit-btn.active:hover {
            background: #1557b0;
            transform: scale(1.1);
        }

        .present-error {
            color: #d93025;
            font-size: 14px;
            margin-top: 12px;
            display: none;
        }

        .present-success {
            padding: 48px 24px;
        }

        .present-success-icon {
            font-size: 48px;
            margin-bottom: 24px;
        }

        .present-success-message {
            font-size: 18px;
            color: #1a73e8;
            line-height: 1.5;
        }

        /* 고해상도 디스플레이 최적화 */
        @media (min-resolution: 2dppx) {
            .present-modal-image {
                image-rendering: -webkit-optimize-contrast;
                image-rendering: crisp-edges;
            }
        }

        /* 반응형 디자인 */
        @media (max-width: 480px) {
            .present-modal-content {
                width: 95vw;
            }
            
            .present-content {
                padding: 24px 16px;
            }
            
            .present-modal-image,
            .present-image-placeholder {
                width: 150px;
                height: 150px;
                font-size: 36px;
            }
            
            .present-message {
                font-size: 20px;
            }
        }

        /* 태블릿 최적화 */
        @media (max-width: 1024px) and (min-width: 481px) {
            .present-modal-image,
            .present-image-placeholder {
                width: 180px;
                height: 180px;
            }
        }

        /* 다크모드 지원 */
        @media (prefers-color-scheme: dark) {
            .present-modal-content {
                background: #1f1f1f;
                color: #e8eaed;
            }
            
            .present-message {
                color: #e8eaed;
            }
            
            .present-input-label {
                color: #9aa0a6;
            }
            
            .present-input {
                background: #2d2d2d;
                border-color: #5f6368;
                color: #e8eaed;
            }
            
            .present-input:focus {
                border-color: #8ab4f8;
            }
        }

        /* 접근성 개선 - 움직임 줄이기 */
        @media (prefers-reduced-motion: reduce) {
            .present-modal,
            .present-modal-image,
            .present-submit-btn {
                transition: none;
            }
            
            .present-modal-image:hover {
                transform: none;
            }
        }
    `;
    
    document.head.appendChild(style);
}

// ==================== 초기화 ====================
// 스타일 추가
addPresentStyles();

// 전역 인스턴스 생성
const presentSystem = new PresentSystem();

// 전역 접근을 위한 window 객체에 등록
window.presentSystem = presentSystem;

// ==================== 개발자 도구용 전역 함수 ====================
// 콘솔에서 테스트할 수 있는 함수들
window.debugPresentSystem = {
    // 에셋 상태 확인
    status: () => presentSystem.getAssetStatus(),
    
    // 수동 모달 표시
    show: () => presentSystem.showPresentModalManually(),
    
    // 쿨다운 초기화
    resetCooldown: () => presentSystem.resetCooldown(),
    
    // 랜덤 조합 생성
    generateCombination: () => presentSystem.generateRandomCombination(),
    
    // 이미지 존재 확인 테스트
    checkImage: (imageNumber) => {
        const config = PRESENT_CONFIG.ASSETS;
        const imagePath = `${config.IMAGE_PATH}${config.IMAGE_PREFIX}${imageNumber}${config.IMAGE_EXTENSION}`;
        return presentSystem.checkImageExists(imagePath);
    }
};

// ==================== 내보내기 ====================
// 다른 모듈에서 사용할 수 있도록
if (typeof module !== 'undefined' && module.exports) {
    module.exports = PresentSystem;
}

console.log('🎁 Present System v2.0 로드 완료 - 동적 갯수 처리 및 랜덤 조합 시스템');
console.log('💡 디버깅: window.debugPresentSystem 사용 가능');
console.log('📊 상태 확인: window.debugPresentSystem.status()');
console.log('🧪 테스트 모달: window.debugPresentSystem.show()');