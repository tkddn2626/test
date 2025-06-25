// ==================== 모달 관리 모듈 (Modal.js) ====================
// 모든 모달 관련 기능을 담당하는 독립 모듈
// Version: 2.0.0
// Dependencies: languages.js, main.js (PickPostGlobals)

class ModalManager {
    constructor() {
        this.modals = new Map();
        this.currentOpenModal = null;
        this.savedScrollPosition = 0;
        this.lastFocusedElement = null;
        this.isModalOpen = false;
        this.init();
    }

    init() {
        this.setupGlobalListeners();
        this.registerModals();
        console.log('✅ ModalManager 초기화 완료');
    }

    // 전역 이벤트 리스너 설정
    setupGlobalListeners() {
        // ESC 키로 모달 닫기
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.currentOpenModal) {
                this.closeModal(this.currentOpenModal);
            }
        });

        // 모달 외부 클릭시 닫기
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('modal') && this.currentOpenModal) {
                this.closeModal(this.currentOpenModal);
            }
        });

        // 브라우저 뒤로가기 버튼 처리
        window.addEventListener('popstate', () => {
            if (this.isModalOpen && this.currentOpenModal) {
                this.closeModal(this.currentOpenModal);
            }
        });

        // 모바일 화면 회전 시 모달 위치 조정
        window.addEventListener('orientationchange', () => {
            if (this.isModalOpen) {
                setTimeout(() => {
                    console.log('📱 화면 회전 감지, 모달 위치 재조정');
                }, 100);
            }
        });

        console.log('✅ 전역 이벤트 리스너 설정 완료');
    }

    // 모달들 등록
    registerModals() {
        try {
            this.modals.set('bugReport', new BugReportModal());
            this.modals.set('terms', new TermsModal());
            this.modals.set('privacy', new PrivacyModal());
            this.modals.set('business', new BusinessModal());
            this.modals.set('shortcut', new ShortcutModal());
            
            console.log('✅ 모든 모달 등록 완료:', Array.from(this.modals.keys()));
        } catch (error) {
            console.error('❌ 모달 등록 중 오류:', error);
        }
    }

    // 모달 열기
    openModal(modalType, options = {}) {
        try {
            // 크롤링 중 제한 확인 (특정 모달만)
            if (['bugReport', 'shortcut'].includes(modalType)) {
                const isLoading = window.PickPostGlobals?.getIsLoading() || false;
                if (isLoading) {
                    const lang = this.getLanguagePack();
                    const message = lang.crawlingStatus?.cantChangeSettings || 
                                   '크롤링 중에는 설정을 변경할 수 없습니다';
                    window.PickPostGlobals?.showMessage(message, 'warning');
                    return;
                }
            }

            const modal = this.modals.get(modalType);
            if (modal) {
                this.saveCurrentState();
                this.currentOpenModal = modalType;
                modal.open(options);
                this.updateModalAria(modal.modalId, true);
                console.log(`✅ 모달 열림: ${modalType}`);
            } else {
                console.error(`❌ 모달을 찾을 수 없음: ${modalType}`);
                this.showModalError('모달을 찾을 수 없습니다.');
            }
        } catch (error) {
            console.error(`❌ 모달 열기 오류 (${modalType}):`, error);
            this.showModalError('모달을 여는 중 오류가 발생했습니다.');
        }
    }

    // 모달 닫기
    closeModal(modalType) {
    try {
        const modal = this.modals.get(modalType);
        if (modal) {
            const shouldClose = modal.beforeClose();
            if (shouldClose === false) {
                return; // 닫기 취소
            }

            // 1. 모달 내부에 포커스된 요소가 aria-hidden 이전에 바깥으로 나가도록 처리
            if (this.lastFocusedElement && typeof this.lastFocusedElement.focus === 'function') {
                this.lastFocusedElement.focus();
            } else {
                document.activeElement.blur(); // 강제로 포커스 제거
            }

            // 2. 모달 시각적으로 닫기
            modal.close();

            // 3. aria-hidden 처리
            this.updateModalAria(modal.modalId, false);

            // 4. 기타 상태 복원
            this.restoreCurrentState();

            this.currentOpenModal = null;
            console.log(`✅ 모달 닫힘: ${modalType}`);
        }
    } catch (error) {
        console.error("❌ 모달 닫기 오류:", error);
    }
    }


    // 현재 상태 저장
    saveCurrentState() {
        this.savedScrollPosition = window.pageYOffset || document.documentElement.scrollTop;
        this.lastFocusedElement = document.activeElement;
        
        // body 스크롤 잠금
        document.body.style.overflow = 'hidden';
        document.body.style.position = 'fixed';
        document.body.style.top = `-${this.savedScrollPosition}px`;
        document.body.style.width = '100%';
        
        this.isModalOpen = true;
        console.log(`💾 모달 상태 저장: 스크롤 위치 ${this.savedScrollPosition}px`);
    }

    // 현재 상태 복원
    restoreCurrentState() {
        // body 스크롤 복원
        document.body.style.overflow = '';
        document.body.style.position = '';
        document.body.style.top = '';
        document.body.style.width = '';
        
        // 스크롤 위치 복원
        window.scrollTo(0, this.savedScrollPosition);
        
        // 포커스 복원
        setTimeout(() => {
            if (this.lastFocusedElement && this.lastFocusedElement.focus) {
                try {
                    this.lastFocusedElement.focus();
                } catch (e) {
                    console.warn('포커스 복원 실패:', e);
                }
            }
        }, 100);
        
        this.isModalOpen = false;
        console.log(`🔄 모달 상태 복원: 스크롤 위치 ${this.savedScrollPosition}px로 복원`);
    }

    // ARIA 속성 업데이트
    updateModalAria(modalId, isOpen) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.setAttribute('aria-hidden', !isOpen);
            if (isOpen) {
                modal.setAttribute('aria-modal', 'true');
                modal.setAttribute('role', 'dialog');
            } else {
                modal.removeAttribute('aria-modal');
                modal.removeAttribute('role');
            }
        }
        
        // 백그라운드 요소들 숨기기
        const mainContent = document.querySelector('main');
            if (mainContent && mainContent !== modal) {
                mainContent.setAttribute('aria-hidden', isOpen);
            }
    }

    // 모달 오류 표시
    showModalError(message) {
        if (window.PickPostGlobals?.showMessage) {
            window.PickPostGlobals.showMessage(message, 'error');
        } else {
            alert(message);
        }
    }

    // 현재 언어 가져오기
    getCurrentLanguage() {
        return window.PickPostGlobals?.getCurrentLanguage() || 'en';
    }

    // 언어팩 가져오기
    getLanguagePack() {
        const lang = this.getCurrentLanguage();
        return window.languages?.[lang] || window.languages?.en || {};
    }

    // 모달 시스템 상태 확인
    validateSystem() {
        const results = {
            languagesLoaded: !!window.languages,
            modalsRegistered: this.modals.size,
            globalsFunctional: !!window.PickPostGlobals,
            errors: []
        };

        if (!window.languages) {
            results.errors.push('Languages.js가 로드되지 않았습니다');
        }

        if (this.modals.size === 0) {
            results.errors.push('등록된 모달이 없습니다');
        }

        if (!window.PickPostGlobals) {
            results.errors.push('PickPostGlobals가 설정되지 않았습니다');
        }

        return results;
    }
}

// ==================== 기본 모달 클래스 ====================
class BaseModal {
    constructor(modalId) {
        this.modalId = modalId;
        this.element = document.getElementById(modalId);
        this.keyboardTrapHandler = null;
        this.validateElement();
    }

    validateElement() {
        if (!this.element) {
            console.error(`❌ Modal element not found: ${this.modalId}`);
            return false;
        }
        return true;
    }

    open(options = {}) {
        if (!this.validateElement()) {
            window.modalManager?.showModalError(`모달 요소를 찾을 수 없습니다: ${this.modalId}`);
            return;
        }
        
        try {
            this.beforeOpen(options);
            this.element.classList.add('show');
            this.setupKeyboardTrap();
            this.afterOpen(options);
        } catch (error) {
            console.error(`❌ 모달 열기 오류 (${this.modalId}):`, error);
            window.modalManager?.showModalError('모달을 여는 중 오류가 발생했습니다.');
        }
    }

    close() {
        if (!this.validateElement()) return;
        
        try {
            this.beforeClose();
            this.element.classList.remove('show');
            this.cleanupKeyboardTrap();
            this.afterClose();
        } catch (error) {
            console.error(`❌ 모달 닫기 오류 (${this.modalId}):`, error);
        }
    }

    beforeOpen(options) {
        // 하위 클래스에서 구현
    }

    afterOpen(options) {
        // 하위 클래스에서 구현
    }

    beforeClose() {
        // 하위 클래스에서 구현
        return true; // 기본적으로 닫기 허용
    }

    afterClose() {
        // 하위 클래스에서 구현
    }

    // 강화된 키보드 트랩 설정
    setupKeyboardTrap() {
        const focusableElements = this.element.querySelectorAll(
            'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"]):not([disabled])'
        );
        
        if (focusableElements.length === 0) return;

        const firstElement = focusableElements[0];
        const lastElement = focusableElements[focusableElements.length - 1];

        this.keyboardTrapHandler = (e) => {
            if (e.key === 'Tab') {
                if (e.shiftKey) {
                    if (document.activeElement === firstElement) {
                        lastElement.focus();
                        e.preventDefault();
                    }
                } else {
                    if (document.activeElement === lastElement) {
                        firstElement.focus();
                        e.preventDefault();
                    }
                }
            }
        };

        this.element.addEventListener('keydown', this.keyboardTrapHandler);
        
        // 첫 번째 요소에 포커스
        setTimeout(() => {
            try {
                firstElement?.focus();
            } catch (e) {
                console.warn('초기 포커스 설정 실패:', e);
            }
        }, 100);
    }

    // 키보드 트랩 정리
    cleanupKeyboardTrap() {
        if (this.keyboardTrapHandler) {
            this.element.removeEventListener('keydown', this.keyboardTrapHandler);
            this.keyboardTrapHandler = null;
        }
    }

    updateTranslations() {
        const lang = window.modalManager?.getLanguagePack() || {};
        this.applyTranslations(lang);
    }

    applyTranslations(lang) {
        // 하위 클래스에서 구현
    }

    // 안전한 메시지 가져오기
    getLocalizedMessage(keyPath, fallback, variables = {}) {
        try {
            const lang = window.modalManager?.getLanguagePack() || {};
            const keys = keyPath.split('.');
            let value = lang;
            
            for (const key of keys) {
                value = value?.[key];
                if (value === undefined) break;
            }
            
            let message = value || fallback;
            
            // 변수 치환
            if (variables && typeof message === 'string') {
                Object.keys(variables).forEach(key => {
                    message = message.replace(new RegExp(`\\{${key}\\}`, 'g'), variables[key]);
                });
            }
            
            return message;
        } catch (error) {
            console.warn('메시지 번역 오류:', error);
            return fallback;
        }
    }
}

// ==================== 피드백 모달 ====================
class BugReportModal extends BaseModal {
    constructor() {
        super('bugReportModal');
        this.attachedFile = null;
        this.init();
    }

    init() {
        this.setupEventListeners();
    }

    setupEventListeners() {
        if (!this.validateElement()) return;

        const textarea = document.getElementById('bugReportDescription');
        const fileInput = document.getElementById('fileInput');
        const submitBtn = document.getElementById('bugReportSubmitBtn');
        const cancelBtn = document.getElementById('bugReportCancelBtn');

        if (textarea) {
            textarea.addEventListener('input', () => {
                this.updateCharacterCount();
                this.updateSubmitButton();
            });
        }

        if (fileInput) {
            fileInput.addEventListener('change', (e) => this.handleFileUpload(e));
        }

        if (submitBtn) {
            submitBtn.addEventListener('click', () => this.submitFeedback());
        }

        if (cancelBtn) {
            cancelBtn.addEventListener('click', () => window.modalManager?.closeModal('bugReport'));
        }
    }

    beforeOpen() {
        this.updateTranslations();
        this.resetForm();
    }

    afterOpen() {
        const textarea = document.getElementById('bugReportDescription');
        setTimeout(() => textarea?.focus(), 300);
    }

    beforeClose() {
        const description = document.getElementById('bugReportDescription')?.value?.trim();
        if (description && description.length > 0) {
            const confirmMessage = this.getLocalizedMessage('confirmClose', 'Are you sure you want to close? Your changes will be lost.');
            return confirm(confirmMessage);
        }
        return true;
    }

    afterClose() {
        setTimeout(() => this.resetForm(), 300);
    }

    applyTranslations(lang) {
        const elements = [
            { id: 'bugReportTitleText', key: 'feedbackTitle', default: 'Send Feedback to PickPost' },
            { id: 'bugReportDescLabel', key: 'feedbackDescLabel', default: 'Please describe your feedback. (Required)' },
            { id: 'screenshotTitle', key: 'fileAttachTitle', default: 'Attach a photo to help PickPost better understand your feedback.' },
            { id: 'bugReportWarningText', key: 'warningTitle', default: 'Do not include sensitive information' },
            { id: 'bugReportWarningDetail', key: 'warningDetail', default: 'Do not include personal information, passwords, financial information, etc.' },
            { id: 'bugReportCancelBtn', key: 'cancel', default: 'Cancel' },
            { id: 'bugReportSubmitBtn', key: 'submit', default: 'Submit' }
        ];

        elements.forEach(({ id, key, default: defaultText }) => {
            const element = document.getElementById(id);
            if (element) {
                element.textContent = lang[key] || defaultText;
            }
        });

        // 플레이스홀더 업데이트
        const textarea = document.getElementById('bugReportDescription');
        if (textarea) {
            textarea.placeholder = lang.feedbackPlaceholder || 'Please tell us why you are providing this feedback. Specific descriptions are very helpful for improvement.';
        }

        const screenshotBtnText = document.getElementById('screenshotBtnText');
        if (screenshotBtnText) {
            screenshotBtnText.textContent = lang.fileAttach || 'Attach Photo';
        }
    }

    updateCharacterCount() {
        const textarea = document.getElementById('bugReportDescription');
        const charCount = document.getElementById('charCount');
        
        if (!textarea || !charCount) return;

        const currentLength = textarea.value.length;
        charCount.textContent = currentLength;

        if (currentLength > 900) {
            charCount.style.color = '#d93025';
        } else if (currentLength > 800) {
            charCount.style.color = '#f57c00';
        } else {
            charCount.style.color = '#5f6368';
        }
    }

    updateSubmitButton() {
        const description = document.getElementById('bugReportDescription')?.value?.trim();
        const submitBtn = document.getElementById('bugReportSubmitBtn');
        
        if (!submitBtn) return;

        const isValid = description && description.length >= 10; // 최소 10자
        submitBtn.disabled = !isValid;

        if (isValid) {
            submitBtn.style.opacity = '1';
            submitBtn.style.transform = 'scale(1)';
        } else {
            submitBtn.style.opacity = '0.6';
            submitBtn.style.transform = 'scale(0.95)';
        }
    }

    handleFileUpload(event) {
        const file = event.target.files[0];
        if (!file) return;

        const maxSize = 5 * 1024 * 1024; // 5MB

        // 안전한 메시지 가져오기
        const getErrorMessage = (key, fallback) => {
            return this.getLocalizedMessage(`messages.feedback.${key}`, fallback);
        };

        if (file.size > maxSize) {
            const message = getErrorMessage('fileTooLarge', 'File size must be less than 5MB');
            window.PickPostGlobals?.showMessage(message, 'error');
            event.target.value = '';
            return;
        }

        if (!file.type.startsWith('image/')) {
            const message = getErrorMessage('invalidFileType', 'Please select an image file');
            window.PickPostGlobals?.showMessage(message, 'error');
            event.target.value = '';
            return;
        }

        this.attachedFile = file;
        this.updateFilePreview(file);
    }

    updateFilePreview(file) {
        const fileName = document.getElementById('fileName');
        const filePreview = document.getElementById('filePreview');
        const screenshotBtn = document.getElementById('screenshotBtn');
        const screenshotBtnText = document.getElementById('screenshotBtnText');

        if (fileName) fileName.textContent = file.name;
        if (filePreview) filePreview.style.display = 'block';
        if (screenshotBtn) screenshotBtn.classList.add('active');

        const fileAttachedText = this.getLocalizedMessage('fileAttached', 'File Attached');
        if (screenshotBtnText) {
            screenshotBtnText.textContent = '✓ ' + fileAttachedText;
        }
    }

    removeFile() {
        const fileInput = document.getElementById('fileInput');
        const filePreview = document.getElementById('filePreview');
        const screenshotBtn = document.getElementById('screenshotBtn');
        const screenshotBtnText = document.getElementById('screenshotBtnText');

        if (fileInput) fileInput.value = '';
        if (filePreview) filePreview.style.display = 'none';
        if (screenshotBtn) screenshotBtn.classList.remove('active');

        const fileAttachText = this.getLocalizedMessage('fileAttach', 'Attach Photo');
        if (screenshotBtnText) {
            screenshotBtnText.textContent = fileAttachText;
        }

        this.attachedFile = null;
    }

    async submitFeedback() {
        const description = document.getElementById('bugReportDescription')?.value?.trim();

        if (!description) {
            const message = this.getLocalizedMessage('messages.feedback.required', 'Please enter your feedback');
            window.PickPostGlobals?.showMessage(message, 'error');
            return;
        }

        if (description.length < 10) {
            window.PickPostGlobals?.showMessage('피드백은 최소 10자 이상 입력해주세요.', 'error');
            return;
        }

        const submitBtn = document.getElementById('bugReportSubmitBtn');
        const originalText = submitBtn?.textContent;

        if (submitBtn) {
            submitBtn.disabled = true;
            const sendingText = this.getLocalizedMessage('messages.feedback.sending', 'Sending...');
            submitBtn.textContent = sendingText;
        }

        try {
            const feedbackData = this.buildFeedbackData(description);
            await this.sendFeedbackToServer(feedbackData);

            const successMessage = this.getLocalizedMessage('messages.feedback.success', 'Feedback sent successfully. Thank you!');
            window.PickPostGlobals?.showMessage(successMessage, 'success');

            window.modalManager?.closeModal('bugReport');

        } catch (error) {
            console.error('피드백 전송 오류:', error);
            
            const errorMessage = this.getLocalizedMessage('messages.feedback.error', 'Failed to send feedback. Please try again.');
            window.PickPostGlobals?.showMessage(errorMessage, 'error');
            
            // 로컬에 저장
            this.saveFeedbackLocally(this.buildFeedbackData(description));
            
        } finally {
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.textContent = originalText;
            }
        }
    }

    buildFeedbackData(description) {
        const systemInfo = {
            userAgent: navigator.userAgent,
            language: navigator.language,
            platform: navigator.platform,
            cookieEnabled: navigator.cookieEnabled,
            onLine: navigator.onLine,
            screenResolution: `${screen.width}x${screen.height}`,
            viewportSize: `${window.innerWidth}x${window.innerHeight}`,
            timestamp: new Date().toISOString()
        };

        return {
            description: description,
            hasFile: !!this.attachedFile,
            fileName: this.attachedFile?.name || null,
            fileSize: this.attachedFile?.size || null,
            systemInfo: systemInfo,
            currentLanguage: window.modalManager?.getCurrentLanguage() || 'en',
            currentSite: window.PickPostGlobals?.getCurrentSite() || null,
            url: window.location.href,
            timestamp: new Date().toISOString()
        };
    }

    async sendFeedbackToServer(feedbackData) {
        const API_BASE_URL = window.PickPostGlobals?.API_BASE_URL;
        if (!API_BASE_URL) {
            throw new Error('API URL not available');
        }

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

    saveFeedbackLocally(feedbackData) {
        try {
            const localData = {
                ...feedbackData,
                localSavedAt: new Date().toISOString(),
                status: 'pending_upload'
            };
            
            const saved = JSON.parse(localStorage.getItem('pending_feedback') || '[]');
            saved.push(localData);
            
            // 최대 10개까지만 저장
            if (saved.length > 10) {
                saved.splice(0, saved.length - 10);
            }
            
            localStorage.setItem('pending_feedback', JSON.stringify(saved));
            console.log('💾 피드백 로컬 저장 완료');
            
        } catch (error) {
            console.error('로컬 저장 실패:', error);
        }
    }

    resetForm() {
        const textarea = document.getElementById('bugReportDescription');
        const charCount = document.getElementById('charCount');

        if (textarea) textarea.value = '';
        if (charCount) {
            charCount.textContent = '0';
            charCount.style.color = '#5f6368';
        }

        this.removeFile();
        this.updateSubmitButton();
    }
}

// ==================== 약관 모달 ====================
class TermsModal extends BaseModal {
    constructor() {
        super('termsModal');
    }

    beforeOpen() {
        this.updateTranslations();
    }

    applyTranslations(lang) {
        const currentLang = window.modalManager?.getCurrentLanguage() || 'en';
        const policy = window.policies?.[currentLang]?.terms || 
                      window.policies?.en?.terms || {};

        const titleElement = document.getElementById('termsModalTitle');
        const contentElement = document.getElementById('termsModalContent');
        const closeBtn = document.getElementById('closeTermsBtn');

        if (titleElement) {
            titleElement.textContent = policy.title || 'Terms of Service';
        }

        if (contentElement) {
            contentElement.innerHTML = policy.content || '<p>Terms of service content not available.</p>';
        }

        if (closeBtn) {
            closeBtn.textContent = lang.ok || 'OK';
        }
    }
}

// ==================== 개인정보처리방침 모달 ====================
class PrivacyModal extends BaseModal {
    constructor() {
        super('privacyModal');
    }

    beforeOpen() {
        this.updateTranslations();
    }

    applyTranslations(lang) {
        const currentLang = window.modalManager?.getCurrentLanguage() || 'en';
        const policy = window.policies?.[currentLang]?.privacy || 
                      window.policies?.en?.privacy || {};

        const titleElement = document.getElementById('privacyModalTitle');
        const contentElement = document.getElementById('privacyModalContent');
        const closeBtn = document.getElementById('closePrivacyBtn');

        if (titleElement) {
            titleElement.textContent = policy.title || 'Privacy Policy';
        }

        if (contentElement) {
            contentElement.innerHTML = policy.content || '<p>Privacy policy content not available.</p>';
        }

        if (closeBtn) {
            closeBtn.textContent = lang.ok || 'OK';
        }
    }
}

// ==================== 비즈니스 모달 ====================
class BusinessModal extends BaseModal {
    constructor() {
        super('businessModal');
    }

    beforeOpen() {
        this.updateTranslations();
    }

    applyTranslations(lang) {
        const currentLang = window.modalManager?.getCurrentLanguage() || 'en';
        const policy = window.policies?.[currentLang]?.business || 
                      window.policies?.en?.business || {};

        const titleElement = document.getElementById('businessModalTitle');
        const contentElement = document.getElementById('businessModalContent');
        const closeBtn = document.getElementById('closeBusinessBtn');

        if (titleElement) {
            titleElement.textContent = policy.title || '💼 Business Information';
        }

        if (contentElement) {
            contentElement.innerHTML = policy.content || '<p>Business information not available.</p>';
        }

        if (closeBtn) {
            closeBtn.textContent = lang.ok || 'OK';
        }
    }
}

// ==================== 바로가기 모달 ====================
class ShortcutModal extends BaseModal {
    constructor() {
        super('shortcutModal');
        this.init();
    }

    init() {
        this.setupEventListeners();
    }

    setupEventListeners() {
        if (!this.validateElement()) return;

        const nameInput = document.getElementById('shortcutNameInput');
        const urlInput = document.getElementById('shortcutUrlInput');
        const saveBtn = document.querySelector('#shortcutModal .btn:last-child');
        const cancelBtn = document.querySelector('#shortcutModal .btn:first-child');

        if (nameInput) {
            nameInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    urlInput?.focus();
                }
            });
        }

        if (urlInput) {
            urlInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    this.saveShortcut();
                }
            });
        }

        if (saveBtn) {
            saveBtn.addEventListener('click', () => this.saveShortcut());
        }

        if (cancelBtn) {
            cancelBtn.addEventListener('click', () => window.modalManager?.closeModal('shortcut'));
        }
    }

    beforeOpen() {
        this.updateTranslations();
        this.resetForm();
    }

    afterOpen() {
        const nameInput = document.getElementById('shortcutNameInput');
        setTimeout(() => nameInput?.focus(), 100);
    }

    afterClose() {
        this.resetForm();
    }

    applyTranslations(lang) {
        const header = this.element?.querySelector('.shortcut-modal-header');
        const nameInput = document.getElementById('shortcutNameInput');
        const urlInput = document.getElementById('shortcutUrlInput');
        const buttons = this.element?.querySelectorAll('.shortcut-modal-buttons .btn');

        if (header) {
            header.textContent = lang.shortcutModalTitle || 'Add Site';
        }

        if (nameInput) {
            nameInput.placeholder = lang.shortcutName || 'Site Name';
        }

        if (urlInput) {
            urlInput.placeholder = lang.shortcutUrl || 'Board URL or Name';
        }

        if (buttons && buttons.length >= 2) {
            buttons[0].textContent = lang.cancel || 'Cancel';
            buttons[1].textContent = lang.save || 'Save';
        }
    }

    saveShortcut() {
        const name = document.getElementById('shortcutNameInput')?.value?.trim();
        const url = document.getElementById('shortcutUrlInput')?.value?.trim();
        const lang = window.modalManager?.getLanguagePack() || {};

        if (!name || !url) {
            const message = this.getLocalizedMessage('fillAllFields', 'Please fill in both name and URL.');
            window.PickPostGlobals?.showMessage(message, 'error');
            return;
        }

        // 바로가기 개수 제한 확인
        const shortcuts = window.PickPostGlobals?.getShortcuts() || [];
        if (shortcuts.length >= 5) {
            const message = this.getLocalizedMessage('maxShortcuts', 'You can add up to 5 shortcuts.');
            window.PickPostGlobals?.showMessage(message, 'error');
            return;
        }

        // 새 바로가기 추가
        const shortcut = { name, url, site: 'universal' };
        shortcuts.push(shortcut);
        
        // 저장
        window.PickPostGlobals?.setShortcuts(shortcuts);
        localStorage.setItem('pickpost_shortcuts', JSON.stringify(shortcuts));

        // UI 새로고침
        if (window.loadShortcuts) {
            window.loadShortcuts();
        }

        // 모달 닫기
        window.modalManager?.closeModal('shortcut');

        console.log('✅ 바로가기 저장 완료:', shortcut);
    }

    resetForm() {
        const nameInput = document.getElementById('shortcutNameInput');
        const urlInput = document.getElementById('shortcutUrlInput');

        if (nameInput) nameInput.value = '';
        if (urlInput) urlInput.value = '';
    }
}

// ==================== 모듈 초기화 및 전역 노출 ====================
let modalManager;

// DOM 로드 완료 시 초기화
document.addEventListener('DOMContentLoaded', () => {
    try {
        modalManager = new ModalManager();
        window.modalManager = modalManager;
        
        // 시스템 유효성 검사
        const validation = modalManager.validateSystem();
        if (validation.errors.length > 0) {
            console.warn('⚠️ Modal 시스템 검증 결과:', validation);
            validation.errors.forEach(error => console.warn(`  - ${error}`));
        } else {
            console.log('✅ Modal 시스템 검증 완료:', {
                언어팩: validation.languagesLoaded ? '로드됨' : '미로드',
                등록된모달: validation.modalsRegistered,
                전역함수: validation.globalsFunctional ? '사용가능' : '불가능'
            });
        }
        
    } catch (error) {
        console.error('❌ ModalManager 초기화 실패:', error);
        
        // 사용자에게 알림
        setTimeout(() => {
            if (window.PickPostGlobals?.showMessage) {
                window.PickPostGlobals.showMessage(
                    '모달 시스템 초기화에 실패했습니다. 페이지를 새로고침해주세요.', 
                    'error'
                );
            } else {
                alert('모달 시스템 오류가 발생했습니다. 페이지를 새로고침해주세요.');
            }
        }, 1000);
    }
});

// ==================== 전역 호환성 함수들 ====================
// main.js와의 호환성을 위한 전역 함수들

// 피드백 모달 함수들
window.openBugReportModal = () => {
    if (modalManager) {
        modalManager.openModal('bugReport');
    } else {
        console.error('❌ ModalManager가 초기화되지 않았습니다');
        alert('모달 기능을 사용할 수 없습니다. 페이지를 새로고침해주세요.');
    }
};

window.closeBugReportModal = () => modalManager?.closeModal('bugReport');

window.updateCharacterCount = () => {
    const bugReportModal = modalManager?.modals.get('bugReport');
    if (bugReportModal && bugReportModal.updateCharacterCount) {
        bugReportModal.updateCharacterCount();
    } else {
        // 폴백: 직접 처리
        const textarea = document.getElementById('bugReportDescription');
        const charCount = document.getElementById('charCount');
        if (textarea && charCount) {
            const length = textarea.value.length;
            charCount.textContent = length;
            charCount.style.color = length > 900 ? '#d93025' : length > 800 ? '#f57c00' : '#5f6368';
        }
    }
};

window.updateBugReportButton = () => {
    const bugReportModal = modalManager?.modals.get('bugReport');
    if (bugReportModal && bugReportModal.updateSubmitButton) {
        bugReportModal.updateSubmitButton();
    } else {
        // 폴백: 직접 처리
        const description = document.getElementById('bugReportDescription')?.value?.trim();
        const submitBtn = document.getElementById('bugReportSubmitBtn');
        if (submitBtn) {
            const isValid = description && description.length >= 10;
            submitBtn.disabled = !isValid;
            submitBtn.style.opacity = isValid ? '1' : '0.6';
        }
    }
};

window.handleFileUpload = (event) => {
    const bugReportModal = modalManager?.modals.get('bugReport');
    if (bugReportModal && bugReportModal.handleFileUpload) {
        bugReportModal.handleFileUpload(event);
    } else {
        console.warn('파일 업로드 기능을 사용할 수 없습니다');
    }
};

window.removeFile = () => {
    const bugReportModal = modalManager?.modals.get('bugReport');
    if (bugReportModal && bugReportModal.removeFile) {
        bugReportModal.removeFile();
    } else {
        // 폴백: 직접 처리
        const fileInput = document.getElementById('fileInput');
        const filePreview = document.getElementById('filePreview');
        if (fileInput) fileInput.value = '';
        if (filePreview) filePreview.style.display = 'none';
    }
};

window.submitBugReport = () => {
    const bugReportModal = modalManager?.modals.get('bugReport');
    if (bugReportModal && bugReportModal.submitFeedback) {
        bugReportModal.submitFeedback();
    } else {
        console.error('피드백 전송 기능을 사용할 수 없습니다');
    }
};

// 약관/정책 모달 함수들
window.openTermsModal = () => modalManager?.openModal('terms');
window.closeTermsModal = () => modalManager?.closeModal('terms');
window.openPrivacyModal = () => modalManager?.openModal('privacy');
window.closePrivacyModal = () => modalManager?.closeModal('privacy');
window.openBusinessModal = () => modalManager?.openModal('business');
window.closeBusinessModal = () => modalManager?.closeModal('business');

// 바로가기 모달 함수들
window.openShortcutModal = () => modalManager?.openModal('shortcut');
window.closeShortcutModal = () => modalManager?.closeModal('shortcut');

window.saveShortcut = () => {
    const shortcutModal = modalManager?.modals.get('shortcut');
    if (shortcutModal && shortcutModal.saveShortcut) {
        shortcutModal.saveShortcut();
    } else {
        console.error('바로가기 저장 기능을 사용할 수 없습니다');
    }
};

// ==================== 유틸리티 함수들 ====================

// 대기 중인 피드백 재전송 함수
async function retryPendingFeedback() {
    try {
        const pending = JSON.parse(localStorage.getItem('pending_feedback') || '[]');
        
        if (pending.length > 0) {
            console.log(`📤 대기 중인 피드백 ${pending.length}개 발견, 재전송 시도 중...`);
            
            const API_BASE_URL = window.PickPostGlobals?.API_BASE_URL;
            if (!API_BASE_URL) {
                console.warn('API_BASE_URL이 설정되지 않아 재전송을 건너뜁니다');
                return;
            }
            
            for (let i = pending.length - 1; i >= 0; i--) {
                const feedback = pending[i];
                
                try {
                    const response = await fetch(`${API_BASE_URL}/api/feedback`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify(feedback)
                    });
                    
                    if (response.ok) {
                        console.log('✅ 대기 피드백 전송 성공:', feedback.localSavedAt);
                        pending.splice(i, 1);
                    } else {
                        console.log(`❌ 대기 피드백 재전송 실패 (${response.status})`);
                        break; // 네트워크 문제일 가능성이 높으므로 중단
                    }
                    
                } catch (error) {
                    console.log('❌ 대기 피드백 재전송 실패:', error.message);
                    break;
                }
                
                // 요청 간 간격
                await new Promise(resolve => setTimeout(resolve, 500));
            }
            
            localStorage.setItem('pending_feedback', JSON.stringify(pending));
            
            if (pending.length === 0) {
                console.log('✅ 모든 대기 피드백 전송 완료');
            } else {
                console.log(`⏳ ${pending.length}개 피드백이 아직 대기 중입니다`);
            }
        }
        
    } catch (error) {
        console.warn('대기 피드백 처리 오류:', error);
    }
}

// 페이지 로드 시 대기 중인 피드백 재전송 시도
window.addEventListener('load', () => {
    setTimeout(retryPendingFeedback, 2000); // 2초 후 시도
});

// ==================== 레거시 지원 함수들 ====================
// 이전 버전과의 완전한 호환성을 위한 함수들

// 토글 스크린샷 함수 (기존 main.js에 있던 함수)
window.toggleScreenshot = function() {
    const screenshotBtn = document.getElementById('screenshotBtn');
    const screenshotBtnText = document.getElementById('screenshotBtnText');
    
    if (!screenshotBtn || !screenshotBtnText) {
        console.warn('스크린샷 버튼 요소를 찾을 수 없습니다');
        return;
    }
    
    const isActive = screenshotBtn.classList.toggle('active');
    const lang = window.modalManager?.getLanguagePack() || {};
    
    if (isActive) {
        screenshotBtnText.textContent = '✓ ' + (lang.screenshotCapture || '스크린샷 캡처');
        screenshotBtn.setAttribute('aria-label', '스크린샷 캡처 활성화됨');
    } else {
        screenshotBtnText.textContent = lang.screenshotCapture || '스크린샷 캡처';
        screenshotBtn.setAttribute('aria-label', '스크린샷 캡처');
    }
};

// 버그 리포트 모달 리셋 함수 (기존 호환성)
window.resetBugReportModal = function() {
    const bugReportModal = modalManager?.modals.get('bugReport');
    if (bugReportModal && bugReportModal.resetForm) {
        bugReportModal.resetForm();
    } else {
        // 폴백: 직접 리셋
        try {
            const textarea = document.getElementById('bugReportDescription');
            const charCount = document.getElementById('charCount');
            const fileInput = document.getElementById('fileInput');
            const filePreview = document.getElementById('filePreview');
            
            if (textarea) textarea.value = '';
            if (charCount) {
                charCount.textContent = '0';
                charCount.style.color = '#5f6368';
            }
            if (fileInput) fileInput.value = '';
            if (filePreview) filePreview.style.display = 'none';
            
        } catch (error) {
            console.error('모달 리셋 중 오류:', error);
        }
    }
};

// 바로가기 모달 키다운 핸들러 (기존 호환성)
window.handleShortcutModalKeydown = function(e) {
    if (e.key === 'Enter') {
        e.preventDefault();
        if (e.target.id === 'shortcutNameInput') {
            const urlInput = document.getElementById('shortcutUrlInput');
            if (urlInput) urlInput.focus();
        } else if (e.target.id === 'shortcutUrlInput') {
            window.saveShortcut();
        }
    } else if (e.key === 'Escape') {
        window.closeShortcutModal();
    }
};

// 모달 키보드 트랩 설정 함수 (기존 호환성)
window.setupModalKeyboardTrap = function(modal) {
    if (!modal) {
        console.warn('setupModalKeyboardTrap: 모달 요소가 없습니다');
        return;
    }
    
    // modal.js의 BaseModal 방식 사용 시도
    const modalInstance = Object.values(modalManager?.modals || {}).find(m => 
        m.element === modal
    );
    
    if (modalInstance && modalInstance.setupKeyboardTrap) {
        modalInstance.setupKeyboardTrap();
        return;
    }
    
    // 폴백: 직접 키보드 트랩 구현
    const focusableElements = modal.querySelectorAll(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );
    
    if (focusableElements.length === 0) return;

    const firstElement = focusableElements[0];
    const lastElement = focusableElements[focusableElements.length - 1];

    // 기존 이벤트 리스너 제거 (중복 방지)
    if (modal._keydownHandler) {
        modal.removeEventListener('keydown', modal._keydownHandler);
    }
    
    // 새 핸들러 생성 및 저장
    modal._keydownHandler = function(e) {
        if (e.key === 'Escape') {
            // 모달 종류에 따라 적절한 닫기 함수 호출
            const modalId = modal.id;
            if (modalId === 'bugReportModal') window.closeBugReportModal();
            else if (modalId === 'termsModal') window.closeTermsModal();
            else if (modalId === 'privacyModal') window.closePrivacyModal();
            else if (modalId === 'businessModal') window.closeBusinessModal();
            else if (modalId === 'shortcutModal') window.closeShortcutModal();
            return;
        }
        
        if (e.key === 'Tab') {
            if (e.shiftKey) {
                if (document.activeElement === firstElement) {
                    lastElement.focus();
                    e.preventDefault();
                }
            } else {
                if (document.activeElement === lastElement) {
                    firstElement.focus();
                    e.preventDefault();
                }
            }
        }
    };
    
    modal.addEventListener('keydown', modal._keydownHandler);
    
    // 첫 번째 요소에 포커스
    setTimeout(() => firstElement?.focus(), 100);
};

// ==================== 개발자 도구 및 디버깅 ====================

// 개발자를 위한 모달 시스템 상태 확인 함수
window.debugModalSystem = function() {
    if (!modalManager) {
        console.log('❌ ModalManager가 초기화되지 않았습니다');
        return;
    }
    
    const status = {
        manager: '✅ 로드됨',
        modals: {},
        currentOpen: modalManager.currentOpenModal || '없음',
        validation: modalManager.validateSystem()
    };
    
    // 각 모달 상태 확인
    modalManager.modals.forEach((modal, key) => {
        status.modals[key] = {
            class: modal.constructor.name,
            element: modal.element ? '✅ 존재함' : '❌ 없음',
            id: modal.modalId
        };
    });
    
    console.log('🔍 Modal System Status:', status);
    return status;
};

// 모든 모달 강제 닫기 (비상용)
window.closeAllModals = function() {
    if (!modalManager) return;
    
    if (modalManager.currentOpenModal) {
        modalManager.closeModal(modalManager.currentOpenModal);
        console.log('🔒 모든 모달이 닫혔습니다');
    } else {
        console.log('📭 열린 모달이 없습니다');
    }
};

// ==================== 최종 초기화 확인 ====================

// 페이지 완전 로드 후 시스템 검증
window.addEventListener('load', function() {
    setTimeout(() => {
        if (window.modalManager) {
            const validation = window.modalManager.validateSystem();
            
            if (validation.errors.length === 0) {
                console.log('🎉 Modal.js 시스템이 완전히 로드되었습니다!');
                console.log(`📊 통계: ${validation.modalsRegistered}개 모달 등록, 언어팩 ${validation.languagesLoaded ? '로드됨' : '미로드'}`);
            } else {
                console.warn('⚠️ Modal 시스템에 일부 문제가 있습니다:', validation.errors);
            }
        } else {
            console.error('❌ Modal.js 로드 실패 - 페이지를 새로고침해주세요');
        }
    }, 1000);
});

console.log('✅ Modal.js v2.0.0 로드 완료 - 완전한 독립 모듈');

// ==================== 익스포트 (모듈 시스템 지원 시) ====================
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { ModalManager, BaseModal, BugReportModal, TermsModal, PrivacyModal, BusinessModal, ShortcutModal };
}

if (typeof exports !== 'undefined') {
    exports.ModalManager = ModalManager;
    exports.BaseModal = BaseModal;
}