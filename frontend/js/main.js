
    // ==================== 전역 변수 및 상태 관리 ====================
    // 애플리케이션의 전역 상태와 설정을 관리하는 변수들
    let currentSite = null;
    let currentLanguage = 'en';
    let autocompleteData = [];
    let siteAutocompleteData = [];
    let highlightIndex = -1;
    let siteHighlightIndex = -1;
    let isLoading = false;
    let searchInitiated = false;
    let currentSocket = null;
    let crawlResults = [];
    let shortcuts = [];
    let crawlStartTime = null;
    let isMouseDownOnAutocomplete = false;
    let isProgrammaticInput = false;
    let currentCrawlId = null;

    // 전역 오류 처리기
    window.addEventListener('error', function(e) {
        console.error('전역 JavaScript 오류:', {
            message: e.message,
            filename: e.filename,
            lineno: e.lineno,
            colno: e.colno,
            error: e.error
        });
        
        // 사용자에게 친화적인 메시지 표시
        if (e.message.includes('data is not defined')) {
            showTemporaryMessage('일시적인 데이터 처리 오류가 발생했습니다. 다시 시도해주세요.', 'error');
        }
    });

    // ==================== API 및 환경 설정 ====================
    // 환경별 API 설정을 반환하는 함수
    function getApiConfig() {
        const hostname = window.location.hostname;
        const protocol = window.location.protocol;
        
        console.log('현재 환경:', { hostname, protocol });

        // 개발 환경
        if (hostname === 'localhost' || hostname === '127.0.0.1') {
            return {
                API_BASE_URL: 'http://localhost:8000',
                WS_BASE_URL: 'ws://localhost:8000'
            };
        }
        
        // 프로덕션 환경 - HTTPS/WSS 사용
        const RENDER_DOMAIN = 'pickpost.onrender.com';
        
        return {
            API_BASE_URL: `https://${RENDER_DOMAIN}`,
            WS_BASE_URL: `wss://${RENDER_DOMAIN}`  // WSS 사용
        };
    }

    // WebSocket 연결을 재시도 로직과 함께 생성하는 함수
    async function createWebSocketWithRetry(endpoint, config, maxRetries = 3) {
        const { WS_BASE_URL } = getApiConfig();
        
        for (let retry = 0; retry < maxRetries; retry++) {
            try {
                console.log(`WebSocket 연결 시도 ${retry + 1}/${maxRetries}: ${WS_BASE_URL}`);
                
                const wsUrl = `${WS_BASE_URL}/ws/${endpoint}`;
                const ws = new WebSocket(wsUrl);
                
                // Origin 헤더 명시적 설정 (브라우저가 자동으로 설정하지만 명확히)
                console.log('연결 Origin:', window.location.origin);
                
                await new Promise((resolve, reject) => {
                    const timeout = setTimeout(() => {
                        ws.close();
                        reject(new Error('Connection timeout after 10s'));
                    }, 10000);  // 타임아웃 증가
                    
                    ws.onopen = () => {
                        clearTimeout(timeout);
                        console.log('✅ WebSocket 연결 성공');
                        resolve();
                    };
                    
                    ws.onerror = (error) => {
                        clearTimeout(timeout);
                        console.error('❌ WebSocket 연결 실패:', error);
                        reject(error);
                    };
                    
                    ws.onclose = (event) => {
                        clearTimeout(timeout);
                        console.log('WebSocket 연결 종료:', {
                            code: event.code,
                            reason: event.reason,
                            wasClean: event.wasClean
                        });
                    };
                });
                
                return ws;
                
            } catch (error) {
                console.warn(`연결 시도 ${retry + 1} 실패:`, error.message);
                
                if (retry < maxRetries - 1) {
                    const delay = 2000 * (retry + 1); // 지수 백오프
                    console.log(`${delay}ms 후 재시도...`);
                    await new Promise(resolve => setTimeout(resolve, delay));
                }
            }
        }
        
        throw new Error('모든 WebSocket 연결 시도 실패');
    }


    // API 연결 상태를 테스트하는 함수
    async function testApiConnection() {
        try {
            console.log('API 연결 테스트 시작...');
            const response = await fetch(`${API_BASE_URL}/health`);
            const data = await response.json();
            console.log('API 연결 성공:', data);
            return true;
        } catch (error) {
            console.error('API 연결 실패:', error);
            return false;
        }
    }

    // WebSocket 연결 상태를 테스트하는 함수
    function testWebSocketConnection() {
        return new Promise((resolve) => {
            console.log('WebSocket 연결 테스트 시작...');
            const testWs = new WebSocket(`${WS_BASE_URL}/ws/auto-crawl`);
            
            testWs.onopen = () => {
                console.log('WebSocket 연결 성공');
                testWs.close();
                resolve(true);
            };
            
            testWs.onerror = (error) => {
                console.error('WebSocket 연결 실패:', error);
                resolve(false);
            };
            
            setTimeout(() => {
                if (testWs.readyState === WebSocket.CONNECTING) {
                    testWs.close();
                    resolve(false);
                }
            }, 5000);
        });
    }

    // API 설정을 전역 변수로 저장
    const { API_BASE_URL, WS_BASE_URL } = getApiConfig();
    console.log('API 설정:', { API_BASE_URL, WS_BASE_URL });

    // ==================== 언어 및 라벨 관리 ====================
    // 현재 언어에 맞는 라벨을 반환하는 함수
    function getLabels() {
        return window.languages[currentLanguage] || window.languages.ko;
    }

    // 모든 UI 라벨을 현재 언어에 맞게 업데이트하는 함수
    function updateLabels() {
        const lang = window.languages?.[currentLanguage] || window.languages?.ko || {};
        
        function safeUpdateText(selector, text) {
            const el = document.querySelector(selector) || document.getElementById(selector);
            if (!el || text === undefined) return false;
            // badge 스팬만 따로 보관
            const badge = el.querySelector('#announcementBadge');
            el.textContent = text;
            if (badge) el.appendChild(badge);
            return true;
            }

        try {
            const currentPolicies = window.policies?.[currentLanguage];
            if (currentPolicies?.privacy && currentPolicies?.business) {
                const privacyModal = document.getElementById('privacyModal');
                if (privacyModal?.classList.contains('show')) {
                    const titleEl = document.getElementById('privacyModalTitle');
                    const contentEl = document.getElementById('privacyModalContent');
                    if (titleEl) titleEl.textContent = currentPolicies.privacy.title;
                    if (contentEl) contentEl.innerHTML = currentPolicies.privacy.content;
                }
                
                const businessModal = document.getElementById('businessModal');
                if (businessModal?.classList.contains('show')) {
                    const titleEl = document.getElementById('businessModalTitle');
                    const contentEl = document.getElementById('businessModalContent');
                    if (titleEl) titleEl.textContent = currentPolicies.business.title;
                    if (contentEl) contentEl.innerHTML = currentPolicies.business.content;
                }
                
                const termsModal = document.getElementById('termsModal');
                if (termsModal?.classList.contains('show')) {
                    const titleEl = document.getElementById('termsModalTitle');
                    const contentEl = document.getElementById('termsModalContent');
                    if (titleEl) titleEl.textContent = currentPolicies.terms.title;
                    if (contentEl) contentEl.innerHTML = currentPolicies.terms.content;
                }
            }
        } catch (error) {
            console.warn('모달 업데이트 중 오류:', error);
        }
        
        function safeUpdatePlaceholder(selector, placeholder) {
            const element = document.querySelector(selector) || document.getElementById(selector);
            if (element && placeholder !== undefined) {
                element.placeholder = placeholder;
                return true;
            }
            return false;
        }
        
        safeUpdateText('crawlBtn', lang.start);
        safeUpdateText('cancelBtn', lang.cancel);
        safeUpdateText('downloadBtn', lang.download);
        
        safeUpdatePlaceholder('siteInput', lang.sitePlaceholder);
        
        if (currentSite) {
            updateBoardPlaceholder(currentSite);
        } else {
            safeUpdatePlaceholder('boardInput', lang.boardPlaceholders.default);
        }
        
        safeUpdatePlaceholder('shortcutNameInput', lang.shortcutNamePlaceholder);
        safeUpdatePlaceholder('shortcutUrlInput', lang.shortcutUrlPlaceholder);
        
        safeUpdateText('minViewsLabel', lang.minViews);
        safeUpdateText('minRecommendLabel', lang.minRecommend);
        safeUpdateText('minCommentsLabel', lang.minComments);
        safeUpdateText('startRankLabel', lang.startRank);
        safeUpdateText('endRankLabel', lang.endRank);
        safeUpdateText('sortMethodLabel', lang.sortMethod);
        safeUpdateText('timePeriodLabel', lang.timePeriod);
        safeUpdateText('advancedSearchLabel', lang.advancedSearch);
        
        safeUpdateText('privacyLink', lang.privacy);
        safeUpdateText('termsLink', lang.terms); 
        safeUpdateText('bugReportLink', lang.feedback);
        safeUpdateText('businessLink', lang.business);
        safeUpdateText('shortcutModalHeader', lang.shortcutModalTitle);
        safeUpdateText('bugReportTitleText', lang.feedbackTitle);
        safeUpdateText('bugReportDescLabel', lang.feedbackDescLabel);
        safeUpdateText('screenshotTitle', lang.fileAttachTitle);
        safeUpdateText('bugReportWarningText', lang.warningTitle);
        safeUpdateText('bugReportWarningDetail', lang.warningDetail);
        safeUpdateText('bugReportCancelBtn', lang.cancel);
        safeUpdateText('bugReportSubmitBtn', lang.submit);

        // 진행 상황 라벨 업데이트
        safeUpdateText('postsLabel', lang.crawlingStatus?.found || '개 수집');
        safeUpdateText('pageLabel', lang.crawlingStatus?.page || '페이지');
        
        // progressEta 초기 텍스트 설정
        const progressEta = document.getElementById('progressEta');
        if (progressEta && !isLoading) {
            progressEta.textContent = (lang.crawlingStatus?.timeRemaining || '예상 시간') + ': ' + (lang.resultTexts?.calculating || '계산 중...');
        }
        

        const startDateLabel = document.getElementById('startDateLabel');
        const endDateLabel = document.getElementById('endDateLabel');
        if (startDateLabel) startDateLabel.textContent = lang.startDate + ':';
        if (endDateLabel) endDateLabel.textContent = lang.endDate + ':';
        
        const backButton = document.querySelector('.back-button');
        if (backButton) backButton.title = lang.backBtn;
        
        const timePeriodSelect = document.getElementById('timePeriod');
        if (timePeriodSelect && timePeriodSelect.options) {
            const options = timePeriodSelect.options;
            if (options[0]) options[0].text = lang.hour;
            if (options[1]) options[1].text = lang.day;
            if (options[2]) options[2].text = lang.week;
            if (options[3]) options[3].text = lang.month;
            if (options[4]) options[4].text = lang.year;
            if (options[5]) options[5].text = lang.all;
            if (options[6]) options[6].text = lang.custom;
        }
        
        const shortcutModal = document.getElementById('shortcutModal');
        if (shortcutModal) {
            const header = shortcutModal.querySelector('.shortcut-modal-header');
            if (header) header.textContent = lang.shortcutModalTitle;
            
            const buttons = shortcutModal.querySelectorAll('.shortcut-modal-buttons .btn');
            if (buttons.length >= 2) {
                buttons[0].textContent = lang.cancel;
                buttons[1].textContent = lang.save;  
            }
        }

        const screenshotBtnText = document.getElementById('screenshotBtnText');
        if (screenshotBtnText && !screenshotBtnText.textContent.includes('✓')) {
            screenshotBtnText.textContent = lang.fileAttach;
        }

        if (currentSite) {
            loadSiteSortOptions(currentSite, currentSite === 'universal' ? document.getElementById('boardInput')?.value : null);
        }

        updateCrawlButton();
        
        // 진행 상황 관련 텍스트 업데이트
        if (isLoading) {
            // 진행 중일 때도 언어 변경 반영
            const progressText = document.getElementById('progressText');
            const lang = window.languages[currentLanguage];
            
            if (progressText && progressText.textContent.includes('%')) {
                // 퍼센트 표시는 그대로 두고, 상태 텍스트만 업데이트는 별도 처리
            }
            
            // 라벨들 업데이트
            const postsLabel = document.getElementById('postsLabel');
            const pageLabel = document.getElementById('pageLabel');
            const progressEta = document.getElementById('progressEta');
            
            if (postsLabel) postsLabel.textContent = lang.crawlingStatus?.found || '개 수집';
            if (pageLabel) pageLabel.textContent = lang.crawlingStatus?.page || '페이지';
            if (progressEta && !progressEta.textContent.includes('0sec')) {
                progressEta.textContent = (lang.crawlingStatus?.timeRemaining || '예상 시간') + ': ' + (lang.resultTexts?.calculating || '계산 중...');
            }
        }

        try {
            loadShortcuts();
        } catch (error) {
            console.error('바로가기 로드 오류:', error);
        }
        console.log(`언어 변경 완료: ${currentLanguage}`);
    }

    // 언어 드롭다운을 표시/숨김하는 함수
    function toggleLanguageDropdown() {
        const dropdown = document.getElementById('languageDropdown');
        dropdown.classList.toggle('show');
    }

    // 언어 드롭다운을 숨기는 함수
    function hideLanguageDropdown() {
        document.getElementById('languageDropdown').classList.remove('show');
    }

    // 언어를 선택하고 UI를 업데이트하는 함수
    function selectLanguage(langCode, langName) {
        currentLanguage = langCode;
        document.getElementById('currentLang').textContent = langName;
        
        document.querySelectorAll('.language-option').forEach(option => {
            option.classList.remove('active');
        });
        event.target.classList.add('active');
        
        updateLabels();
        hideLanguageDropdown();
        
        console.log(`언어 변경됨: ${langCode} (${langName})`);
    }

    // ==================== 피드백 및 모달 관리 ====================
    // 피드백 모달을 여는 함수
    function openBugReportModal() {
        const modal = document.getElementById('bugReportModal');
        const textarea = document.getElementById('bugReportDescription');
        const lang = window.languages[currentLanguage];
        
        document.getElementById('bugReportTitleText').textContent = lang.feedbackTitle || 'PickPost에 의견 보내기';
        document.getElementById('bugReportDescLabel').textContent = lang.feedbackDescLabel || '의견을 설명해 주세요. (필수)';
        document.getElementById('screenshotTitle').textContent = lang.fileAttachTitle;
        document.getElementById('bugReportWarningText').textContent = lang.warningTitle || '민감한 정보는 포함하지 마세요';
        document.getElementById('bugReportWarningDetail').textContent = lang.warningDetail || '개인정보, 비밀번호, 금융정보 등은 포함하지 마세요...';
        document.getElementById('bugReportCancelBtn').textContent = lang.cancel;
        document.getElementById('bugReportSubmitBtn').textContent = lang.submit || '보내기';
        
        modal.classList.add('show');
        setTimeout(() => textarea.focus(), 300);
        setupModalKeyboardTrap(modal);
    }

    // 피드백 모달을 닫는 함수
    function closeBugReportModal() {
        const modal = document.getElementById('bugReportModal');
        
        const description = document.getElementById('bugReportDescription').value.trim();
        if (description.length > 0) {
            const confirmMessages = {
                ko: '작성 중인 내용이 있습니다. 정말 닫으시겠습니까?',
                en: 'There is content being written. Are you sure you want to close?',
                ja: '作成中の内容があります。本当に閉じますか？'
            };
            
            if (!confirm(confirmMessages[currentLanguage] || confirmMessages.ko)) {
                return;
            }
        }
        
        modal.classList.remove('show');
        
        setTimeout(() => {
            resetBugReportModal();
        }, 300);
    }

    // 서비스 약관 모달을 여는 함수
    function openTermsModal() {
        const modal = document.getElementById('termsModal');
        const terms = window.policies[currentLanguage].terms;
        
        document.getElementById('termsModalTitle').textContent = terms.title;
        document.getElementById('termsModalContent').innerHTML = terms.content;
        
        modal.classList.add('show');
        setupModalKeyboardTrap(modal);
    }

    // 서비스 약관 모달을 닫는 함수
    function closeTermsModal() {
        const modal = document.getElementById('termsModal');
        modal.classList.remove('show');
    }

    // 개인정보처리방침 모달을 여는 함수
    function openPrivacyModal() {
        const modal = document.getElementById('privacyModal');
        const policy = window.policies[currentLanguage].privacy;
        
        document.getElementById('privacyModalTitle').textContent = policy.title;
        document.getElementById('privacyModalContent').innerHTML = policy.content;
        
        modal.classList.add('show');
        setupModalKeyboardTrap(modal);
    }

    // 개인정보처리방침 모달을 닫는 함수
    function closePrivacyModal() {
        const modal = document.getElementById('privacyModal');
        modal.classList.remove('show');
    }

    // 비즈니스 모달을 여는 함수
    function openBusinessModal() {
        const modal = document.getElementById('businessModal');
        const policy = window.policies[currentLanguage].business;
        
        document.getElementById('businessModalTitle').textContent = policy.title;
        document.getElementById('businessModalContent').innerHTML = policy.content;
        
        modal.classList.add('show');
        setupModalKeyboardTrap(modal);
    }

    // 비즈니스 모달을 닫는 함수
    function closeBusinessModal() {
        const modal = document.getElementById('businessModal');
        modal.classList.remove('show');
    }

    // 스크린샷 버튼 상태를 토글하는 함수
    function toggleScreenshot() {
        const screenshotBtn = document.getElementById('screenshotBtn');
        const isActive = screenshotBtn.classList.toggle('active');
        
        const lang = window.languages[currentLanguage];
        if (isActive) {
            document.getElementById('screenshotBtnText').textContent = '✓ ' + (lang.screenshotCapture || '스크린샷 캡처');
        } else {
            document.getElementById('screenshotBtnText').textContent = lang.screenshotCapture || '스크린샷 캡처';
        }
    }

    // 피드백 전송 버튼 상태를 업데이트하는 함수
    function updateBugReportButton() {
        const description = document.getElementById('bugReportDescription').value.trim();
        const submitBtn = document.getElementById('bugReportSubmitBtn');
        
        const isValid = description.length > 0;
        submitBtn.disabled = !isValid;
        
        if (isValid) {
            submitBtn.style.opacity = '1';
            submitBtn.style.transform = 'scale(1)';
        } else {
            submitBtn.style.opacity = '0.6';
            submitBtn.style.transform = 'scale(0.95)';
        }
    }

    // 피드백을 서버로 전송하는 함수
    function submitBugReport() {
        const description = document.getElementById('bugReportDescription').value.trim();
        const fileInput = document.getElementById('fileInput');
        const hasFile = fileInput.files.length > 0;
        const lang = window.languages[currentLanguage];
        
        if (!description) {
            showTemporaryMessage('feedback_required', 'error');
            document.getElementById('bugReportDescription').focus();
            return;
        }
        
        const submitBtn = document.getElementById('bugReportSubmitBtn');
        const originalText = submitBtn.textContent;
        submitBtn.disabled = true;
        
        // 전송 중 텍스트 번역
        const sendingText = {
            ko: '전송 중...',
            en: 'Sending...',
            ja: '送信中...'
        };
        submitBtn.textContent = sendingText[currentLanguage] || sendingText.ko;
        
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
        
        const bugReport = {
            description: description,
            hasFile: hasFile,
            fileName: hasFile ? fileInput.files[0].name : null,
            fileSize: hasFile ? fileInput.files[0].size : null,
            systemInfo: systemInfo,
            currentLanguage: currentLanguage,
            currentSite: currentSite,
            url: window.location.href,
            timestamp: new Date().toISOString()
        };
        
        console.log('피드백 신고:', bugReport);
        
        setTimeout(() => {
            showTemporaryMessage(lang.messages.feedback.success || '피드백이 전송되었습니다. 감사합니다!', 'success');
            
            closeBugReportModal();
            
            submitBtn.disabled = false;
            submitBtn.textContent = originalText;
            
        }, 1000);
        sendBugReportToServer(bugReport);
    }

    // 글자 수 카운터를 업데이트하는 함수
    function updateCharacterCount() {
        const textarea = document.getElementById('bugReportDescription');
        const charCount = document.getElementById('charCount');
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

    // 파일 업로드를 처리하는 함수
    function handleFileUpload(event) {
        const file = event.target.files[0];
        if (file) {
            const maxSize = 5 * 1024 * 1024;
            
            if (file.size > maxSize) {
                const lang = labels[currentLanguage];
                showTemporaryMessage('file_too_large', 'error');
                
                event.target.value = '';
                return;
            }

            if (!file.type.startsWith('image/')) {
                showTemporaryMessage('invalid_file_type', 'error');
                
                event.target.value = '';
                return;
            }

            document.getElementById('fileName').textContent = file.name;
            document.getElementById('filePreview').style.display = 'block';
            
            const screenshotBtn = document.getElementById('screenshotBtn');
            screenshotBtn.classList.add('active');
            
            const lang = window.languages[currentLanguage];
            document.getElementById('screenshotBtnText').textContent = '✓ ' + (lang.fileAttached || '파일 첨부됨');
            
            screenshotBtn.setAttribute('aria-label', '파일이 첨부되었습니다. 클릭하여 다른 파일로 변경');
        }
    }

    // 첨부된 파일을 제거하는 함수
    function removeFile() {
        document.getElementById('fileInput').value = '';
        document.getElementById('filePreview').style.display = 'none';
        
        const screenshotBtn = document.getElementById('screenshotBtn');
        screenshotBtn.classList.remove('active');
        
        const lang = window.languages[currentLanguage];
        document.getElementById('screenshotBtnText').textContent = lang.fileAttach || '사진 첨부';
    }

    // 피드백을 서버로 전송하는 함수
    async function sendBugReportToServer(bugReport) {
        try {
            const response = await fetch(`${API_BASE_URL}/api/feedback`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(bugReport)
            });
            
            if (response.ok) {
                console.log('피드백 전송 성공');
            } else {
                console.warn('피드백 전송 실패:', response.status);
            }
        } catch (error) {
            console.error('피드백 전송 오류:', error);
        }
    }

    // 피드백 모달을 초기화하는 함수
    function resetBugReportModal() {
        document.getElementById('bugReportDescription').value = '';
        document.getElementById('charCount').textContent = '0';
        document.getElementById('charCount').style.color = '#5f6368';
        
        removeFile();
        
        updateBugReportButton();
    }

    // 모달에서 키보드 트랩을 설정하는 함수 (접근성)
    function setupModalKeyboardTrap(modal) {
        const focusableElements = modal.querySelectorAll(
            'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
        );
        const firstFocusableElement = focusableElements[0];
        const lastFocusableElement = focusableElements[focusableElements.length - 1];

        modal.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') {
                closeBugReportModal();
            }
            
            if (e.key === 'Tab') {
                if (e.shiftKey) {
                    if (document.activeElement === firstFocusableElement) {
                        lastFocusableElement.focus();
                        e.preventDefault();
                    }
                } else {
                    if (document.activeElement === lastFocusableElement) {
                        firstFocusableElement.focus();
                        e.preventDefault();
                    }
                }
            }
        });
    }

    // ==================== 페이지 초기화 및 이벤트 설정 ====================
    // 페이지를 새로고침하는 함수
    function refreshPage() {
        location.reload();
    }

    // 날짜 입력 필드를 초기화하는 함수
    function initializeDateInputs() {
        const today = new Date();
        const yesterday = new Date(today);
        yesterday.setDate(yesterday.getDate() - 1);
        
        document.getElementById('startDate').value = yesterday.toISOString().split('T')[0];
        document.getElementById('endDate').value = today.toISOString().split('T')[0];
        
        console.log('날짜 기본값 설정:', {
            start: yesterday.toISOString().split('T')[0],
            end: today.toISOString().split('T')[0]
        });
    }

    // 모든 이벤트 리스너를 설정하는 함수
    function setupEventListeners() {
        const siteInput = document.getElementById('siteInput');
        const boardInput = document.getElementById('boardInput');
        
        siteInput.addEventListener('input', function() {
            const value = this.value;
            
            document.getElementById('clearSiteBtn').style.display = value.trim() ? 'flex' : 'none';
            
            hideSiteAutocomplete();
        });

        siteInput.addEventListener('keydown', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                handleSiteSearch();
                setTimeout(() => {
                    if (currentSite && boardInput && isElementVisible(boardInput)) {
                        boardInput.focus();
                    }
                }, 500);
            } else if (e.key === 'Escape') {
                hideSiteAutocomplete();
            }
        });

        siteInput.addEventListener('blur', function() {
            hideSiteAutocomplete();
        });

        let originalBoardValue = '';
        
        function showSiteHelp(site) {
            if (site === 'lemmy') {
                showLemmyHelp();
            } else if (site === 'universal') {
                showUniversalHelp();
            }
        }

        function showLemmyHelp() {
            const boardInput = document.getElementById('boardInput');
            if (boardInput.value.trim()) {
                return;
            }
            
            showLemmyHelpContent();
        }

        boardInput.addEventListener('input', function() {
            if (isProgrammaticInput) {
                isProgrammaticInput = false;
                return;
            }
            
            const value = this.value.trim();
            
            if (value.length === 0 && currentSite === 'lemmy') {
                showLemmyHelp();
            } else if (value.length >= 2) {
                fetchAutocomplete(value);
            } else {
                hideAutocomplete();
            }
            
            document.getElementById('clearBoardBtn').style.display = value ? 'flex' : 'none';
            updateCrawlButton();
        });
        
        boardInput.addEventListener('focus', function() {
            if (!this.value.trim() && currentSite === 'lemmy') {
                showLemmyHelp();
            } else if (this.value.trim() && currentSite) {
                fetchAutocomplete(this.value);
            }
        });
        
        boardInput.addEventListener('keydown', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                if (highlightIndex >= 0 && autocompleteData.length > 0) {
                    selectAutocompleteItem(highlightIndex);
                } else if (this.value.trim() && currentSite) {
                    moveToNextInput();
                }
            } else if (e.key === 'Escape') {
                this.value = originalBoardValue;
                hideAutocomplete();
            } else {
                handleKeyNavigation(e);
            }
        });

        boardInput.addEventListener('blur', function() {
            if (!isMouseDownOnAutocomplete) {
                setTimeout(() => {
                    hideAutocomplete();
                }, 200);
            }
        });

        document.getElementById('timePeriod').addEventListener('change', function() {
            handleTimeSelection(this.value);
        });

        document.getElementById('timePeriod').addEventListener('keydown', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                moveToNextInput(this);
            }
        });

        const inputElements = [
            '#minViews', '#minRecommend', '#startRank', '#endRank', 
            '#startRankAdv', '#endRankAdv', '#minComments',
            '#sortMethod', '#startDate', '#endDate'
        ];
        
        inputElements.forEach(selector => {
            const element = document.querySelector(selector);
            if (element) {
                element.addEventListener('input', updateCrawlButton);
                element.addEventListener('change', updateCrawlButton);
                element.addEventListener('keydown', function(e) {
                    if (e.key === 'Enter') {
                        e.preventDefault();
                        moveToNextInput(this);
                    }
                });
            }
        });

        document.getElementById('advancedSearch').addEventListener('change', function() {
            toggleAdvancedSearch();
            updateCrawlButton();
        });

        document.addEventListener('click', function(e) {
            if (!e.target.closest('.language-selector')) {
                hideLanguageDropdown();
            }
            if (!e.target.closest('.board-search-container')) {
                hideAutocomplete();
            }
            if (!e.target.closest('.search-container')) {
                hideSiteAutocomplete();
            }
            if (!e.target.closest('.shortcut-modal-content') && !e.target.closest('.add-shortcut-btn')) {
                closeShortcutModal();
            }
        });

        document.getElementById('shortcutNameInput').addEventListener('keydown', handleShortcutModalKeydown);
        document.getElementById('shortcutUrlInput').addEventListener('keydown', handleShortcutModalKeydown);
    }

    // DOM 로드 완료 시 초기화를 실행하는 이벤트 리스너
    document.addEventListener('DOMContentLoaded', function() {
        currentLanguage = 'en';

        // 언어 버튼 텍스트 초기화
        document.getElementById('currentLang').textContent = 'English';
        
        // 언어 옵션 활성화 상태 변경
        document.querySelectorAll('.language-option').forEach(option => {
            option.classList.remove('active');
        });
        // 영어 옵션을 활성화
        document.querySelector('[onclick*="en"]').classList.add('active');
        
        updateLabels(); // 영어 라벨로 업데이트

        updateLabels();
        initializeDefaultShortcuts();
        setupEventListeners();
        initializeDateInputs();
        loadShortcuts();
    
        const logoImage = document.querySelector('.logo-image');
        if (logoImage) {
            logoImage.addEventListener('click', function() {
                location.reload();
            });
        }
        
        console.log('PickPost 시작, API 설정:', { API_BASE_URL, WS_BASE_URL });
        
        testApiConnection().then(apiConnected => {
            console.log('API 연결 상태:', apiConnected);
        });
        
        testWebSocketConnection().then(wsConnected => {
            console.log('WebSocket 연결 상태:', wsConnected);
        });

        // 피드백 시스템 초기화
        if (window.initializeFeedbackSystem) {
            window.initializeFeedbackSystem();
        }
        
        // ready 이벤트 발생
        window.dispatchEvent(new Event('PickPostReady'));

    });

    // ESC 키로 모달을 닫는 이벤트 리스너
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            const modal = document.getElementById('bugReportModal');
            if (modal.classList.contains('show')) {
                closeBugReportModal();
                return;
            }
            
            const termsModal = document.getElementById('termsModal');
            if (termsModal.classList.contains('show')) {
                closeTermsModal();
                return;
            }
            
            const privacyModal = document.getElementById('privacyModal');
            if (privacyModal.classList.contains('show')) {
                closePrivacyModal();
                return;
            }
            
            const businessModal = document.getElementById('businessModal');
            if (businessModal.classList.contains('show')) {
                closeBusinessModal();
                return;
            }
        }
    });

    // ==================== 바로가기 관리 시스템 ====================
    // 기본 사이트들을 포함한 초기 바로가기를 설정하는 함수
    function initializeDefaultShortcuts() {
        const stored = localStorage.getItem('pickpost_shortcuts');
        if (!stored) {
            const defaultShortcuts = [
                { name: 'Reddit', url: 'reddit.com', site: 'reddit' }, 
                { name: 'BBC', url: 'bbc.com', site: 'bbc' },
                { name: 'Lemmy', url: 'lemmy.world', site: 'lemmy' }
            ];
            localStorage.setItem('pickpost_shortcuts', JSON.stringify(defaultShortcuts));
            shortcuts = defaultShortcuts;
        } else {
            shortcuts = JSON.parse(stored);
        }
    }

    // 저장된 바로가기들을 화면에 로드하는 함수
    function loadShortcuts() {
        const container = document.getElementById('siteSelection');
        const lang = window.languages[currentLanguage];

        const siteColors = {
            reddit: '#ff4500',
            dcinside: '#00a8ff', 
            blind: '#00d2d3',
            bbc: '#bb1919',
            lemmy: '#00af54',
            universal: '#28a745'
        };
        
        const shortcutButtons = shortcuts.map((shortcut, index) => {
            let displayName = shortcut.name;
            
            if (window.innerWidth <= 768 && displayName.length > 6) {
                displayName = displayName.substring(0, 6) + '...';
            }
            
            return `
                <button class="site-btn" data-site="${shortcut.site}" onclick="useShortcut('${shortcut.site}', '${shortcut.url}')" title="${shortcut.name}">
                    <div class="site-icon" style="background: ${siteColors[shortcut.site] || '#6c757d'};"></div>
                    <span>${displayName}</span>
                    <span class="shortcut-remove" onclick="event.stopPropagation(); removeShortcut(${index})" title="삭제">×</span>
                </button>
            `;
        }).join('');
        
        const addButton = shortcuts.length < 5 ? `
            <button class="site-btn add-shortcut-btn" onclick="openShortcutModal()">
                ➕ ${lang.addShortcut || '추가'}
            </button>
        ` : '';
        
        container.innerHTML = shortcutButtons + addButton;
    }

    // 바로가기 추가 모달을 여는 함수
    function openShortcutModal() {
        const modal = document.getElementById('shortcutModal');
        if (!modal) {
            console.error('shortcutModal 요소를 찾을 수 없습니다');
            return;
        }

        const lang = window.languages[currentLanguage];

        const header = modal.querySelector('.shortcut-modal-header');
        if (header) {
            header.textContent = lang.shortcutModalTitle || '사이트 추가';
        }
        
        const nameInput = document.getElementById('shortcutNameInput');
        const urlInput = document.getElementById('shortcutUrlInput');
        if (nameInput) nameInput.placeholder = lang.shortcutNamePlaceholder || '사이트 이름';
        if (urlInput) urlInput.placeholder = lang.shortcutUrlPlaceholder || '사이트 URL';
        
        const buttons = modal.querySelectorAll('.shortcut-modal-buttons .btn');
        if (buttons.length >= 2) {
            buttons[0].textContent = lang.cancel || '취소';
            buttons[1].textContent = lang.save || '저장';
        }

        modal.classList.add('show');

        setTimeout(() => {
            const nameInput = document.getElementById('shortcutNameInput');
            if (nameInput) {
                nameInput.focus();
            }
        }, 100);
    }

    // 바로가기 추가 모달을 닫는 함수
    function closeShortcutModal() {
        const modal = document.getElementById('shortcutModal');
        modal.classList.remove('show');
        
        document.getElementById('shortcutNameInput').value = '';
        document.getElementById('shortcutUrlInput').value = '';
    }

    // 새로운 바로가기를 저장하는 함수
    function saveShortcut() {
        const name = document.getElementById('shortcutNameInput').value.trim();
        const url = document.getElementById('shortcutUrlInput').value.trim();
        
        if (!name || !url) {
            alert('이름과 URL을 모두 입력해주세요.');
            return;
        }
        
        if (shortcuts.length >= 5) {
            alert('바로가기는 최대 5개까지만 추가할 수 있습니다.');
            return;
        }
        
        const shortcut = { name, url, site: 'universal' };
        shortcuts.push(shortcut);
        localStorage.setItem('pickpost_shortcuts', JSON.stringify(shortcuts));
        
        loadShortcuts();
        closeShortcutModal();
    }

    // 바로가기를 삭제하는 함수
    function removeShortcut(index) {
        shortcuts.splice(index, 1);
        localStorage.setItem('pickpost_shortcuts', JSON.stringify(shortcuts));
        loadShortcuts();
    }

    // 바로가기를 사용하여 사이트를 선택하는 함수
    function useShortcut(site, url) {
        const siteInput = document.getElementById('siteInput');
        const siteNames = { 
            reddit: 'Reddit', 
            dcinside: 'DCInside', 
            blind: 'Blind',
            bbc: 'BBC',
            lemmy: 'Lemmy',
            universal: 'universal'
        };
        
        siteInput.value = siteNames[site] || site;
        document.getElementById('clearSiteBtn').style.display = 'flex';
        
        selectSite(site);
    }

    // 바로가기 모달에서 키보드 이벤트를 처리하는 함수
    function handleShortcutModalKeydown(e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            if (e.target.id === 'shortcutNameInput') {
                document.getElementById('shortcutUrlInput').focus();
            } else if (e.target.id === 'shortcutUrlInput') {
                saveShortcut();
            }
        }
    }


    // ==================== 사이트 검색 및 자동완성 ====================
    // 사이트 입력창을 클리어하는 함수
    function clearSiteInput() {
        const siteInput = document.getElementById('siteInput');
        siteInput.value = '';
        document.getElementById('clearSiteBtn').style.display = 'none';
        
        document.querySelectorAll('.site-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        
        currentSite = null;
        searchInitiated = false;
        
        hideSiteAutocomplete();
    }

    // 보드 입력을 안전하게 설정하는 함수 (프로그래밍 방식)
    function safeSetBoardInput(value) {
        const boardInput = document.getElementById('boardInput');
        
        isProgrammaticInput = true;
        
        boardInput.value = value;
        
        document.getElementById('clearBoardBtn').style.display = value ? 'flex' : 'none';
        hideAutocomplete();
        updateCrawlButton();
        
        setTimeout(() => {
            isProgrammaticInput = false;
        }, 0);
    }

    // 시간 선택을 처리하는 함수
    function handleTimeSelection(value) {
        const customDateContainer = document.getElementById('customDateContainer');
        
        if (value === 'custom') {
            customDateContainer.classList.add('show');
            console.log('사용자 지정 날짜 모드 활성화');
        } else {
            customDateContainer.classList.remove('show');
            console.log(`시간 필터 선택: ${value}`);
        }
        
        updateCrawlButton();
    }

    // 입력에서 URL을 추출하는 함수
    function extractURLFromInput(input) {
        const value = input.trim().toLowerCase();
        
        if (value.startsWith('http://') || value.startsWith('https://')) {
            return input.trim();
        }
        
        if (value.startsWith('www.')) {
            return 'https://' + input.trim();
        }
        
        if (value.includes('.') && value.includes('/')) {
            return 'https://' + input.trim();
        }
        
        if (value.includes('.') && !value.includes(' ')) {
            return 'https://' + input.trim();
        }
        
        return null;
    }

    // 사이트 자동완성을 표시하는 함수
    function showSiteAutocomplete(keyword) {
        if (!keyword || keyword.length < 1) {
            hideSiteAutocomplete();
            return;
        }
        
        const keywordLower = keyword.toLowerCase();
        const extractedURL = extractURLFromInput(keyword);
        
        const suggestions = [
        { name: 'Reddit', site: 'reddit', icon: '#ff4500', desc: 'reddit.com' },
        { name: 'DCInside', site: 'dcinside', icon: '#00a8ff', desc: 'dcinside.com' },
        { name: 'Blind', site: 'blind', icon: '#00d2d3', desc: 'teamblind.com' },
        { name: 'BBC', site: 'bbc', icon: '#bb1919', desc: 'bbc.com (British Broadcasting)' }, 
        { name: 'Lemmy', site: 'lemmy', icon: '#00af54', desc: 'lemmy federation network' }, 
        { name: 'Universal Crawler', site: 'universal', icon: '#28a745', desc: 'All websites (Direct URL input)' } 
        
        ].filter(item => {
            return item.name.toLowerCase().includes(keywordLower) ||
                item.site.toLowerCase().includes(keywordLower) ||
                item.desc.toLowerCase().includes(keywordLower) ||
                (keywordLower === '레딧' && item.site === 'reddit') ||
                (keywordLower.includes('디시') && item.site === 'dcinside') ||
                (keywordLower.includes('갤러리') && item.site === 'dcinside') ||
                (keywordLower.includes('블라인드') && item.site === 'blind') ||
                (keywordLower.includes('bbc') && item.site === 'bbc') ||
                (keywordLower.includes('뉴스') && item.site === 'bbc') ||
                (keywordLower.includes('영국') && item.site === 'bbc') ||
                (keywordLower.includes('레미') && item.site === 'lemmy') ||
                (keywordLower.includes('범용') && item.site === 'universal') ||
                extractedURL;
        });

        if (extractedURL) {
            const universalIndex = suggestions.findIndex(s => s.site === 'universal');
            if (universalIndex > -1) {
                const universal = suggestions.splice(universalIndex, 1)[0];
                universal.desc = `URL 감지됨: ${extractedURL}`;
                suggestions.unshift(universal);
            }
        }

        if (suggestions.length > 0) {
            siteAutocompleteData = suggestions;
            showSiteSuggestions(suggestions, keyword, extractedURL);
        } else {
            hideSiteAutocomplete();
        }
    }

    // 사이트 제안 목록을 표시하는 함수
    function showSiteSuggestions(suggestions, keyword, extractedURL = null) {
        const searchContainer = document.querySelector('.search-container');
        
        let existingDropdown = searchContainer.querySelector('.site-autocomplete');
        
        if (existingDropdown) {
            existingDropdown.remove();
        }

        searchContainer.classList.add('dropdown-active');

        const dropdown = document.createElement('div');
        dropdown.className = 'site-autocomplete';
        dropdown.innerHTML = suggestions.map((item, index) => {
            const nameHighlighted = item.name.replace(
                new RegExp(`(${keyword})`, 'gi'),
                '<mark style="background: #ffeb3b;">$1</mark>'
            );
            const descHighlighted = item.desc.replace(
                new RegExp(`(${keyword})`, 'gi'),
                '<mark style="background: #ffeb3b;">$1</mark>'
            );
            
            return `
                <div class="site-autocomplete-item" data-index="${index}" onclick="selectSiteAutocompleteItem(${index})">
                    <div class="site-icon" style="background: ${item.icon};"></div>
                    <div style="flex: 1;">
                        <div>${nameHighlighted}</div>
                        <div style="font-size: 12px; color: #70757a;">${descHighlighted}</div>
                    </div>
                </div>
            `;
        }).join('');

        searchContainer.appendChild(dropdown);
        siteHighlightIndex = -1;
    }

    // 사이트 자동완성을 숨기는 함수
    function hideSiteAutocomplete() {
        const searchContainer = document.querySelector('.search-container');
        const dropdown = searchContainer.querySelector('.site-autocomplete');
        
        if (dropdown) {
            dropdown.remove();
        }
        
        searchContainer.classList.remove('dropdown-active');
        
        siteAutocompleteData = [];
        siteHighlightIndex = -1;
    }

    // 사이트 자동완성에서 탐색하는 함수
    function navigateSiteAutocomplete(direction) {
        if (siteAutocompleteData.length === 0) return;

        if (direction === 'down') {
            siteHighlightIndex = Math.min(siteHighlightIndex + 1, siteAutocompleteData.length - 1);
        } else {
            siteHighlightIndex = Math.max(siteHighlightIndex - 1, -1);
        }

        updateSiteHighlight();
    }

    // 사이트 자동완성의 하이라이트를 업데이트하는 함수
    function updateSiteHighlight() {
        const siteInput = document.getElementById('siteInput');
        document.querySelectorAll('.site-autocomplete-item').forEach((item, index) => {
            item.classList.toggle('highlighted', index === siteHighlightIndex);
        });

        if (siteHighlightIndex >= 0 && siteHighlightIndex < siteAutocompleteData.length) {
            siteInput.value = siteAutocompleteData[siteHighlightIndex].name;
        }
    }

    // 사이트 자동완성 항목을 선택하는 함수
    function selectSiteAutocompleteItem(index) {
        if (index >= 0 && index < siteAutocompleteData.length) {
            const selectedSite = siteAutocompleteData[index];
            const originalInput = document.getElementById('siteInput').value;
            const extractedURL = extractURLFromInput(originalInput);
            
            if (selectedSite.site === 'universal' && extractedURL) {
                const siteName = extractSiteName(extractedURL);
                document.getElementById('siteInput').value = siteName;
                
                hideSiteAutocomplete();
                selectSite(selectedSite.site, extractedURL);
                
                setTimeout(() => {
                    document.getElementById('boardInput').value = extractedURL;
                    document.getElementById('clearBoardBtn').style.display = 'flex';
                    updateCrawlButton();
                }, 300);
                
            } else {
                document.getElementById('siteInput').value = selectedSite.name;
                hideSiteAutocomplete();
                selectSite(selectedSite.site);
            }
        }
    }

    // 고급 검색 모드를 토글하는 함수
    function toggleAdvancedSearch() {
        const advancedOptions = document.getElementById('advancedOptions');
        const basicOptions = document.getElementById('basicOptions');
        const checkbox = document.getElementById('advancedSearch');
        const optionsContainer = document.getElementById('optionsContainer');
        
        if (checkbox.checked) {
            basicOptions.style.display = 'none';
            advancedOptions.style.display = 'contents';
            optionsContainer.classList.add('advanced-mode');
            
            document.getElementById('startRankAdv').value = document.getElementById('startRank').value;
            document.getElementById('endRankAdv').value = document.getElementById('endRank').value;
        } else {
            advancedOptions.style.display = 'none';
            basicOptions.style.display = 'contents';
            optionsContainer.classList.remove('advanced-mode');
            
            document.getElementById('startRank').value = document.getElementById('startRankAdv').value;
            document.getElementById('endRank').value = document.getElementById('endRankAdv').value;
        }
    }

    // 다음 입력 필드로 포커스를 이동하는 함수
    function moveToNextInput(currentElement = null) {
        let targetElement = null;
        
        if (!currentElement) {
            targetElement = document.getElementById('sortMethod');
        } else {
            const isAdvancedMode = document.getElementById('advancedSearch').checked;
            
            let navigationOrder;
            if (isAdvancedMode) {
                navigationOrder = [
                    'sortMethod', 'timePeriod', 'minViews', 'minRecommend', 
                    'startRankAdv', 'endRankAdv', 'minComments', 'startDate', 'endDate'
                ];
            } else {
                navigationOrder = [
                    'sortMethod', 'timePeriod', 'startRank', 'endRank', 'startDate', 'endDate'
                ];
            }
            
            const currentIndex = navigationOrder.indexOf(currentElement.id);
            if (currentIndex >= 0 && currentIndex < navigationOrder.length - 1) {
                let nextIndex = currentIndex + 1;
                
                while (nextIndex < navigationOrder.length) {
                    const nextElement = document.getElementById(navigationOrder[nextIndex]);
                    if (nextElement && isElementVisible(nextElement)) {
                        targetElement = nextElement;
                        break;
                    }
                    nextIndex++;
                }
                
                if (!targetElement) {
                    if (!document.getElementById('crawlBtn').disabled) {
                        startCrawling();
                    }
                    return;
                }
            }
        }
        
        if (targetElement) {
            targetElement.focus();
            if (targetElement.select) {
                targetElement.select();
            }
        }
    }

    // 요소가 화면에 보이는지 확인하는 함수
    function isElementVisible(element) {
        return element.offsetParent !== null && !element.disabled;
    }

    // 사이트 검색을 처리하는 함수
    function handleSiteSearch() {
        const siteInputValue = document.getElementById('siteInput').value.trim();
        const extractedURL = extractURLFromInput(siteInputValue);
        
        if (extractedURL) {
            const siteName = extractSiteName(extractedURL);
            document.getElementById('siteInput').value = siteName;
            selectSite('universal', extractedURL);
            
            setTimeout(() => {
                document.getElementById('boardInput').value = extractedURL;
                document.getElementById('clearBoardBtn').style.display = 'flex';
                updateCrawlButton();
            }, 200);
            
        } else {
            if (siteInputValue.toLowerCase().includes('reddit')) {
                document.getElementById('siteInput').value = 'Reddit';
                selectSite('reddit');
            } else if (siteInputValue.toLowerCase().includes('dc') || siteInputValue.toLowerCase().includes('디시')) {
                document.getElementById('siteInput').value = 'DCInside';
                selectSite('dcinside');
            } else if (siteInputValue.toLowerCase().includes('blind') || siteInputValue.toLowerCase().includes('블라인드')) {
                document.getElementById('siteInput').value = 'Blind';
                selectSite('blind');
            } else if (siteInputValue.toLowerCase().includes('lemmy') || siteInputValue.toLowerCase().includes('레미')) {
                document.getElementById('siteInput').value = 'Lemmy';
                selectSite('lemmy');
            } else {
                document.getElementById('siteInput').value = siteInputValue;
                selectSite('universal');
            }
        }
    }

    // 퀵 사이트를 선택하는 함수
    function selectQuickSite(site) {
        const siteNames = {
            'reddit': 'Reddit',
            'dcinside': 'DCInside', 
            'blind': 'Blind',
            'lemmy': 'Lemmy'
        };
        
        document.getElementById('siteInput').value = siteNames[site];
        document.getElementById('clearSiteBtn').style.display = 'flex';
        hideSiteAutocomplete();
        selectSite(site);
    }

    // ==================== 사이트 선택 및 설정 ====================
    // 사이트를 선택하고 관련 설정을 적용하는 함수
    function selectSite(site, extractedURL = null) {
        autocompleteData = [];
        highlightIndex = -1;
        const container = document.getElementById('autocomplete');
        container.innerHTML = '';
        
        const boardInput = document.getElementById('boardInput');
        boardInput.value = '';
        
        if (searchInitiated && currentSite === site && !extractedURL) return;
        
        currentSite = site;
        searchInitiated = true;
        
        updateBoardPlaceholder(site);
        
        document.querySelectorAll('.site-btn').forEach(btn => {
            btn.classList.remove('active');
            if (btn.dataset.site === site) {
                btn.classList.add('active');
            }
        });

        loadSiteSortOptions(site, extractedURL);
        animateToSearchMode();
        
        setTimeout(() => {
            showBoardSearch();
            showOptions(site);
            
            if (extractedURL && site === 'universal') {
                boardInput.value = extractedURL;
                document.getElementById('clearBoardBtn').style.display = 'flex';
                updateCrawlButton();
            }
        }, 300);
    }

    // 사이트별 보드 입력창의 placeholder를 업데이트하는 함수
    function updateBoardPlaceholder(site) {
        const boardInput = document.getElementById('boardInput');
        const lang = window.languages[currentLanguage];
        
        if (boardInput && lang.boardPlaceholders) {
            const placeholder = lang.boardPlaceholders[site] || lang.boardPlaceholders.default;
            boardInput.placeholder = placeholder;
        }
    }

    // 사이트별 정렬 옵션을 로드하는 함수
    async function loadSiteSortOptions(site, url = null) {
        const sortSelect = document.getElementById('sortMethod');
        const lang = window.languages[currentLanguage];
        
        if (site === 'reddit') {
            sortSelect.innerHTML = `
                <option value="new">${lang.sortOptions.reddit.new}</option>
                <option value="top">${lang.sortOptions.reddit.top}</option>
                <option value="hot">${lang.sortOptions.reddit.hot}</option>
                <option value="best">${lang.sortOptions.reddit.best}</option>
                <option value="rising">${lang.sortOptions.reddit.rising}</option>
            `;
            sortSelect.value = "new";
            
        } else if (site === 'lemmy') {
            sortSelect.innerHTML = `
                <option value="New">${lang.sortOptions.lemmy.New}</option>
                <option value="Hot">${lang.sortOptions.lemmy.Hot}</option>
                <option value="Active">${lang.sortOptions.lemmy.Active}</option>
                <option value="TopDay">${lang.sortOptions.lemmy.TopDay}</option>
                <option value="TopWeek">${lang.sortOptions.lemmy.TopWeek}</option>
                <option value="TopMonth">${lang.sortOptions.lemmy.TopMonth}</option>
                <option value="TopYear">${lang.sortOptions.lemmy.TopYear}</option>
                <option value="TopAll">${lang.sortOptions.lemmy.TopAll}</option>
                <option value="MostComments">${lang.sortOptions.lemmy.MostComments}</option>
            `;
            sortSelect.value = "New";
            
        } else if (site === 'dcinside') {
            sortSelect.innerHTML = `
                <option value="recent">${lang.sortOptions.other.recent}</option>
                <option value="popular">${lang.sortOptions.other.popular}</option>
                <option value="recommend">${lang.sortOptions.other.recommend}</option>
                <option value="comments">${lang.sortOptions.other.comments}</option>
            `;
            sortSelect.value = "recent";
            
        } else if (site === 'blind') {
            sortSelect.innerHTML = `
                <option value="recent">${lang.sortOptions.other.recent}</option>
                <option value="popular">${lang.sortOptions.other.popular}</option>
                <option value="recommend">${lang.sortOptions.other.recommend}</option>
                <option value="comments">${lang.sortOptions.other.comments}</option>
            `;
            sortSelect.value = "recent";
            
        } else if (site === 'bbc') {
            sortSelect.innerHTML = `
                <option value="recent">${lang.sortOptions.other.recent}</option>
                <option value="popular">${lang.sortOptions.other.popular}</option>
            `;
            sortSelect.value = "recent";
            
        } else if (site === 'universal' && url) {
            try {
                const detectedSortOptions = await detectSiteSortOptions(url);
                if (detectedSortOptions && detectedSortOptions.length > 0) {
                    sortSelect.innerHTML = detectedSortOptions.map(option => 
                        `<option value="${option.value}">${option.label}</option>`
                    ).join('');
                    
                    if (detectedSortOptions.length > 0) {
                        sortSelect.value = detectedSortOptions[0].value;
                    }
                } else {
                    useDefaultSortOptions(sortSelect, lang);
                }
            } catch (error) {
                useDefaultSortOptions(sortSelect, lang);
            }
        } else {
            sortSelect.innerHTML = `
                <option value="recent">${lang.sortOptions.other.recent}</option>
                <option value="popular">${lang.sortOptions.other.popular}</option>
                <option value="recommend">${lang.sortOptions.other.recommend}</option>
                <option value="comments">${lang.sortOptions.other.comments}</option>
            `;
            sortSelect.value = "recent";
        }
        
        sortSelect.dispatchEvent(new Event('change'));
    }

    // 기본 정렬 옵션을 사용하는 함수
    function useDefaultSortOptions(sortSelect, lang) {
        sortSelect.innerHTML = `
            <option value="popular">${lang.sortOptions.other.popular}</option>
            <option value="recommend">${lang.sortOptions.other.recommend}</option>
            <option value="recent">${lang.sortOptions.other.recent}</option>
            <option value="comments">${lang.sortOptions.other.comments}</option>
        `;
    }

    // 사이트별 정렬 옵션을 감지하는 함수
    async function detectSiteSortOptions(url) {
        try {
            const domain = new URL(url).hostname.toLowerCase();
            
            if (domain.includes('lemmy') || url.includes('lemmy')) {
                return [
                    { value: 'Active', label: 'Active' },
                    { value: 'Hot', label: 'Hot' },
                    { value: 'New', label: 'New' },
                    { value: 'Old', label: 'Old' },
                    { value: 'TopDay', label: 'Top Day' },
                    { value: 'TopWeek', label: 'Top Week' },
                    { value: 'TopMonth', label: 'Top Month' },
                    { value: 'TopYear', label: 'Top Year' },
                    { value: 'TopAll', label: 'Top All Time' },
                    { value: 'MostComments', label: 'Most Comments' },
                    { value: 'NewComments', label: 'New Comments' }
                ];
            }
            
            if (domain.includes('news.ycombinator') || domain.includes('hackernews')) {
                return [
                    { value: 'top', label: 'Top' },
                    { value: 'new', label: 'New' },
                    { value: 'best', label: 'Best' },
                    { value: 'ask', label: 'Ask' },
                    { value: 'show', label: 'Show' },
                    { value: 'jobs', label: 'Jobs' }
                ];
            }
            
            if (await isDiscourseSite(url)) {
                return [
                    { value: 'latest', label: 'Latest' },
                    { value: 'top', label: 'Top' },
                    { value: 'new', label: 'New' },
                    { value: 'unread', label: 'Unread' },
                    { value: 'categories', label: 'Categories' }
                ];
            }
            
            if (domain.includes('phpbb') || url.includes('viewforum.php')) {
                return [
                    { value: 't', label: 'Last Post Time' },
                    { value: 'a', label: 'Author' },
                    { value: 's', label: 'Subject' },
                    { value: 'r', label: 'Replies' },
                    { value: 'v', label: 'Views' }
                ];
            }

            return [
                { value: 'newest', label: 'Newest' },
                { value: 'oldest', label: 'Oldest' },
                { value: 'popular', label: 'Popular' },
                { value: 'trending', label: 'Trending' },
                { value: 'top', label: 'Top' },
                { value: 'hot', label: 'Hot' }
            ];
            
        } catch (error) {
            console.warn('정렬 방식 감지 중 오류:', error);
            return null;
        }
    }

    // Discourse 사이트인지 확인하는 함수
    async function isDiscourseSite(url) {
        try {
            const discoursePatterns = [
                'discourse', 'forum', 'community', 'discuss'
            ];
            
            const domain = new URL(url).hostname.toLowerCase();
            return discoursePatterns.some(pattern => domain.includes(pattern));
        } catch {
            return false;
        }
    }

    // 검색 모드로 애니메이션하는 함수
    function animateToSearchMode() {
        const searchText = document.getElementById('siteInput').value.trim();
        if (!searchText) return;

        const logoContainer = document.getElementById('logoContainer');
        const mainContainer = document.getElementById('mainContainer');
        
        logoContainer.classList.add('compact');
        mainContainer.classList.add('compact');
    }

    // 보드 검색 인터페이스를 표시하는 함수
    function showBoardSearch(extractedURL = null) {
        const boardSearchContainer = document.getElementById('boardSearchContainer');
        const boardInput = document.getElementById('boardInput');
        
        boardSearchContainer.classList.add('show');
        
        setTimeout(() => {
            if (!boardInput.value.trim()) {
                boardInput.focus();
            }
        }, 200);
    }

    // 옵션 인터페이스를 표시하는 함수
    function showOptions(site) {
        const optionsContainer = document.getElementById('optionsContainer');
        const buttonContainer = document.getElementById('buttonContainer');
        
        setTimeout(() => {
            optionsContainer.classList.add('show');
            buttonContainer.classList.add('show');
        }, 200);

        updateCrawlButton();
    }

    // 뒤로가기 기능을 수행하는 함수
    function goBack() {
        currentSite = null;
        searchInitiated = false;
        
        const logoContainer = document.getElementById('logoContainer');
        const mainContainer = document.getElementById('mainContainer');
        const boardSearchContainer = document.getElementById('boardSearchContainer');
        const optionsContainer = document.getElementById('optionsContainer');
        const buttonContainer = document.getElementById('buttonContainer');
        
        logoContainer.classList.remove('compact');
        mainContainer.classList.remove('compact');
        
        boardSearchContainer.classList.remove('show');
        optionsContainer.classList.remove('show');
        buttonContainer.classList.remove('show');
        
        document.getElementById('siteInput').value = '';
        document.getElementById('boardInput').value = '';
        document.getElementById('clearSiteBtn').style.display = 'none';
        document.getElementById('clearBoardBtn').style.display = 'none';
        
        document.querySelectorAll('.site-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        
        document.getElementById('customDateContainer').classList.remove('show');
        document.getElementById('timePeriod').value = 'day';
        
        clearResults();
        hideProgress();
        hideSiteAutocomplete();
        hideAutocomplete();
    }

    // ==================== 자동완성 시스템 ====================
    // BBC 전용 자동완성을 표시하는 함수
    function showBBCAutocomplete(keyword) {
        const keywordLower = keyword.toLowerCase();
        
        const bbcSections = [
            { name: 'BBC News', url: 'https://www.bbc.com/news', desc: '최신 뉴스' },
            { name: 'BBC Business', url: 'https://www.bbc.com/business', desc: '비즈니스 뉴스' },
            { name: 'BBC Technology', url: 'https://www.bbc.com/technology', desc: '기술 뉴스' },
            { name: 'BBC Sport', url: 'https://www.bbc.com/sport', desc: '스포츠 뉴스' },
            { name: 'BBC Health', url: 'https://www.bbc.com/health', desc: '건강 뉴스' },
            { name: 'BBC Science', url: 'https://www.bbc.com/science', desc: '과학 뉴스' },
            { name: 'BBC Entertainment', url: 'https://www.bbc.com/entertainment', desc: '연예 뉴스' },
            { name: 'BBC World', url: 'https://www.bbc.com/news/world', desc: '세계 뉴스' },
            { name: 'BBC UK', url: 'https://www.bbc.com/news/uk', desc: '영국 뉴스' },
            { name: 'BBC Politics', url: 'https://www.bbc.com/news/politics', desc: '정치 뉴스' }
        ];

        const filtered = bbcSections.filter(section => {
            return section.name.toLowerCase().includes(keywordLower) ||
                section.desc.toLowerCase().includes(keywordLower) ||
                (keywordLower.includes('뉴스') && section.desc.includes('뉴스')) ||
                (keywordLower.includes('news') && section.name.includes('News')) ||
                (keywordLower.includes('비즈니스') && section.name.includes('Business')) ||
                (keywordLower.includes('기술') && section.name.includes('Technology')) ||
                (keywordLower.includes('스포츠') && section.name.includes('Sport')) ||
                (keywordLower.includes('건강') && section.name.includes('Health')) ||
                (keywordLower.includes('과학') && section.name.includes('Science')) ||
                (keywordLower.includes('연예') && section.name.includes('Entertainment'));
        });

        if (filtered.length > 0) {
            autocompleteData = filtered.map(section => section.url);
            showBBCAutocompleteDropdown(filtered, keyword);
        } else {
            const popularSections = bbcSections.slice(0, 5);
            autocompleteData = popularSections.map(section => section.url);
            showBBCAutocompleteDropdown(popularSections, keyword);
        }
    }

    // BBC 자동완성 드롭다운을 표시하는 함수
    function showBBCAutocompleteDropdown(sections, keyword) {
        const container = document.getElementById('autocomplete');
        const boardSearchContainer = document.getElementById('boardSearchContainer');
        
        boardSearchContainer.classList.add('dropdown-active');

        container.addEventListener('mousedown', function(e) {
            isMouseDownOnAutocomplete = true;
            e.preventDefault();
        });

        container.innerHTML = sections.map((section, index) => {
            const nameHighlighted = section.name.replace(
                new RegExp(`(${keyword})`, 'gi'),
                '<mark style="background: #ffeb3b;">$1</mark>'
            );
            const descHighlighted = section.desc.replace(
                new RegExp(`(${keyword})`, 'gi'),
                '<mark style="background: #ffeb3b;">$1</mark>'
            );
            
            return `
                <div class="autocomplete-item" data-index="${index}" onclick="selectBBCSection(${index})">
                    <div style="width: 20px; height: 20px; background: #bb1919; border-radius: 3px; display: flex; align-items: center; justify-content: center; color: white; font-size: 10px; font-weight: bold;">BBC</div>
                    <div style="flex: 1;">
                        <div>${nameHighlighted}</div>
                        <div style="font-size: 12px; color: #70757a;">${descHighlighted}</div>
                    </div>
                </div>
            `;
        }).join('');

        container.classList.add('show');
        highlightIndex = -1;
    }

    // BBC 섹션을 선택하는 함수
    function selectBBCSection(index) {
        if (index >= 0 && index < autocompleteData.length) {
            safeSetBoardInput(autocompleteData[index]);
        }
    }

    // 키워드에 따른 자동완성을 가져오는 함수
    async function fetchAutocomplete(keyword) {
        if (!keyword || keyword.trim().length < 2 || !currentSite) {
            if (currentSite === 'lemmy' && (!keyword || keyword.trim().length === 0)) {
                showLemmyHelp();
                return;
            }
            hideAutocomplete();
            return;
        }
        if (currentSite === 'universal') {
            if (keyword.startsWith('http://') || keyword.startsWith('https://')) {
                hideAutocomplete();
                updateCrawlButton();
            } else {
                showUniversalHelp();
            }
            return;
        }
        
        if (currentSite === 'bbc') {
            showBBCAutocomplete(keyword);
            return;
        }

        try {
            const response = await fetch(`${API_BASE_URL}/autocomplete/${currentSite}?keyword=${encodeURIComponent(keyword)}`);
            const data = await response.json();
            
            if (data.matches && data.matches.length > 0) {
                autocompleteData = data.matches;
                showAutocomplete(keyword);
            } else {
                hideAutocomplete();
            }
        } catch (error) {
            console.error('Autocomplete error:', error);
            useOfflineAutocomplete(keyword);
        }
    }

    // 오프라인 자동완성을 사용하는 함수
    function useOfflineAutocomplete(keyword) {
        if (!keyword.trim()) {
            hideAutocomplete();
            return;
        }

        const keywordLower = keyword.toLowerCase();
        let suggestions = [];

        if (currentSite === 'reddit') {
            const redditSubreddits = [
                'askreddit', 'todayilearned', 'funny', 'pics', 'worldnews', 'gaming', 
                'movies', 'music', 'science', 'technology', 'programming', 'python', 
                'javascript', 'webdev', 'machinelearning', 'artificial', 'lifeprotips', 
                'showerthoughts', 'mildlyinteresting', 'food', 'cooking', 'fitness', 
                'aww', 'videos', 'gifs', 'memes', 'explainlikeimfive', 'korea', 'korean'
            ];
            suggestions = redditSubreddits.filter(sub => sub.includes(keywordLower));
        } else if (currentSite === 'dcinside') {
            const dcGalleries = [
                '싱글벙글', '유머', '정치', '축구', '야구', '농구', '배구', '게임', 
                '리그오브레전드', '오버워치', '스타크래프트', '카운터스트라이크', 'PC게임', 
                '모바일게임', '애니메이션', '만화', '영화', '드라마', '음악', '아이돌', 
                '케이팝', '힙합', '요리', '여행', '사진', '자동차', '컴퓨터', '스마트폰'
            ];
            suggestions = dcGalleries.filter(gallery => gallery.includes(keywordLower));
        } else if (currentSite === 'blind') {
            const blindTopics = [
                '블라블라', '회사생활', '자유토크', '개발자', '경력개발', '취업/이직', 
                '스타트업', '회사와사람들', '디자인', '금융/재테크', '부동산', '결혼/육아', 
                '여행', '음식', '건강', '연애', '게임', '주식', '암호화폐', 'IT/기술'
            ];
            suggestions = blindTopics.filter(topic => topic.includes(keywordLower));
        } else if (currentSite === 'lemmy') {
            const lemmyCommunities = [
                'technology@lemmy.world',
                'worldnews@lemmy.ml', 
                'asklemmy@lemmy.ml',
                'programming@programming.dev',
                'linux@lemmy.ml',
                'privacy@lemmy.ml',
                'opensource@lemmy.ml',
                'science@lemmy.ml',
                'memes@lemmy.ml',
                'gaming@beehaw.org',
                'movies@lemm.ee',
                'music@lemmy.ml',
                'books@lemmy.ml',
                'photography@lemmy.ml',
                'art@lemmy.ml',
                'food@lemmy.world',
                'travel@lemmy.world',
                'fitness@lemmy.world',
                'diy@lemmy.world',
                'showerthoughts@lemmy.world',
                'todayilearned@lemmy.world',
                'funny@lemmy.world',
                'news@lemmy.world',
                'askscience@lemmy.world',
                'explainlikeimfive@lemmy.world'
            ];
            
            suggestions = lemmyCommunities.filter(community => {
                const [name, instance] = community.split('@');
                return name.toLowerCase().includes(keywordLower) || 
                    community.toLowerCase().includes(keywordLower) ||
                    instance.toLowerCase().includes(keywordLower);
            });
            
            if (keywordLower.length <= 2) {
                const popularSuggestions = [
                    'technology@lemmy.world',
                    'asklemmy@lemmy.ml', 
                    'worldnews@lemmy.ml',
                    'programming@programming.dev',
                    'gaming@beehaw.org'
                ];
                suggestions = [...new Set([...popularSuggestions, ...suggestions])];
            }
        }

        if (suggestions.length > 0) {
            autocompleteData = suggestions.slice(0, 10);
            showAutocomplete(keyword);
        } else {
            hideAutocomplete();
        }
    }

    // Lemmy 전용 도움말을 표시하는 함수
    function showLemmyHelpContent() {
        const container = document.getElementById('autocomplete');
        const boardSearchContainer = document.getElementById('boardSearchContainer');
        const lang = window.languages[currentLanguage];
        
        boardSearchContainer.classList.add('dropdown-active');
        
        container.innerHTML = `
            <div class="autocomplete-item" style="cursor: default; background: #f8f9fa;">
                <div style="flex: 1;">
                    <div style="font-weight: 500; color: #1a73e8;">${lang.lemmyHelp.title}</div>
                    <div style="font-size: 12px; color: #70757a; margin-top: 4px;">
                        ${lang.lemmyHelp.description.replace(/\n/g, '<br>')}
                    </div>
                </div>
            </div>
            <div class="autocomplete-item" onclick="setLemmyCommunity('technology@lemmy.world');">
                <div style="flex: 1;">
                    <div style="color: #1a73e8;">🔧 technology@lemmy.world</div>
                    <div style="font-size: 11px; color: #70757a;">${lang.lemmyHelp.examples.technology}</div>
                </div>
            </div>
            <div class="autocomplete-item" onclick="setLemmyCommunity('asklemmy@lemmy.ml');">
                <div style="flex: 1;">
                    <div style="color: #1a73e8;">❓ asklemmy@lemmy.ml</div>
                    <div style="font-size: 11px; color: #70757a;">${lang.lemmyHelp.examples.asklemmy}</div>
                </div>
            </div>
        `;
        
        container.classList.add('show');
    }

    // Lemmy 커뮤니티를 설정하는 함수
    function setLemmyCommunity(community) {
        safeSetBoardInput(community);
    }

    // 크롤링 버튼 상태를 업데이트하는 함수
    function updateCrawlButton() {
        const boardValue = document.getElementById('boardInput').value.trim();
        const crawlBtn = document.getElementById('crawlBtn');
        const lang = window.languages[currentLanguage];
        
        let isValid = false;
        let buttonText = lang.start;
        
        if (!currentSite) {
            buttonText = lang.crawlButtonMessages.siteNotSelected;
            isValid = false;
        } else if (!boardValue) {
            if (currentSite === 'universal') {
                buttonText = lang.crawlButtonMessages.universalEmpty;
            } else if (currentSite === 'lemmy') {
                buttonText = lang.crawlButtonMessages.lemmyEmpty;
            } else {
                buttonText = lang.crawlButtonMessages.boardEmpty;
            }
            isValid = false;
        } else {
            switch (currentSite) {
                case 'universal':
                    isValid = boardValue.startsWith('http://') || 
                            boardValue.startsWith('https://') ||
                            (boardValue.includes('.') && boardValue.includes('/'));
                    if (!isValid) {
                        buttonText = lang.crawlButtonMessages.universalUrlError;
                    }
                    break;
                
                case 'lemmy':
                    if (boardValue.includes('@') && boardValue.split('@').length === 2) {
                        const [community, instance] = boardValue.split('@');
                        isValid = community.length > 0 && instance.length > 0;
                    } else if (boardValue.startsWith('https://') && boardValue.includes('/c/')) {
                        isValid = true;
                    } else if (boardValue.length > 2) {
                        isValid = true;
                        buttonText = `${community_name}@lemmy.world로 시도`;
                    } else {
                        buttonText = lang.crawlButtonMessages.lemmyFormatError;
                        isValid = false;
                    }
                    break;
                    
                case 'reddit':
                    if (boardValue.includes('reddit.com') && !boardValue.includes('/r/')) {
                        buttonText = lang.crawlButtonMessages.redditFormatError;
                        isValid = false;
                    } else {
                        isValid = true;
                    }
                    break;
                    
                default:
                    isValid = boardValue.length > 0;
                    break;
            }
        }
        
        crawlBtn.disabled = !isValid || isLoading;
        
        if (!isLoading) {
            crawlBtn.textContent = buttonText;
        }
    }

    // 범용 크롤러 도움말을 표시하는 함수
    function showUniversalHelp() {
        const container = document.getElementById('autocomplete');
        const boardSearchContainer = document.getElementById('boardSearchContainer');
        const lang = window.languages[currentLanguage];
        
        boardSearchContainer.classList.add('dropdown-active');
        
        container.innerHTML = `
            <div class="autocomplete-item" style="cursor: default; background: #f8f9fa;">
                <div style="flex: 1;">
                    <div style="font-weight: 500; color: #1a73e8;">${lang.helpTexts.universalTitle}</div>
                    <div style="font-size: 12px; color: #70757a; margin-top: 4px;">
                        ${lang.helpTexts.universalDesc.replace(/\n/g, '<br>')}
                    </div>
                </div>
            </div>
        `;
        
        container.classList.add('show');
    }

    // 자동완성을 표시하는 함수
    function showAutocomplete(keyword) {
        const container = document.getElementById('autocomplete');
        const boardSearchContainer = document.getElementById('boardSearchContainer');
        
        if (autocompleteData.length === 0) {
            hideAutocomplete();
            return;
        }

        boardSearchContainer.classList.add('dropdown-active');

        container.innerHTML = autocompleteData.map((item, index) => {
            const highlighted = item.replace(
                new RegExp(`(${keyword})`, 'gi'),
                '<mark style="background: #ffeb3b;">$1</mark>'
            );
            return `
                <div class="autocomplete-item" data-index="${index}" onclick="selectAutocompleteItem(${index})">
                    <div style="flex: 1;">${highlighted}</div>
                </div>
            `;
        }).join('');

        container.classList.add('show');
        highlightIndex = -1;

        container.addEventListener('mousedown', function(e) {
            isMouseDownOnAutocomplete = true;
            e.preventDefault();
        });
        
        container.addEventListener('mouseup', function() {
            isMouseDownOnAutocomplete = false;
        });
        
        container.addEventListener('mouseleave', function() {
            isMouseDownOnAutocomplete = false;
        });
        
        container.innerHTML = autocompleteData.map((item, index) => {
            const highlighted = item.replace(
                new RegExp(`(${keyword})`, 'gi'),
                '<mark style="background: #ffeb3b;">$1</mark>'
            );
            return `
                <div class="autocomplete-item" 
                    data-index="${index}" 
                    onclick="selectAutocompleteItem(${index})"
                    onmouseenter="highlightIndex = ${index}; updateHighlight();"
                    style="cursor: pointer;">
                    <div style="flex: 1;">${highlighted}</div>
                </div>
            `;
        }).join('');
    }

    // 자동완성을 숨기는 함수
    function hideAutocomplete() {
        if (isMouseDownOnAutocomplete) {
            return;
        }

        const container = document.getElementById('autocomplete');
        const boardSearchContainer = document.getElementById('boardSearchContainer');
        
        container.classList.remove('show');
        boardSearchContainer.classList.remove('dropdown-active');
        
        highlightIndex = -1;
    }

    // 키보드 탐색을 처리하는 함수
    function handleKeyNavigation(e) {
        const container = document.getElementById('autocomplete');
        if (!container.classList.contains('show')) return;

        switch (e.key) {
            case 'ArrowDown':
                e.preventDefault();
                highlightIndex = Math.min(highlightIndex + 1, autocompleteData.length - 1);
                updateHighlight();
                break;
            case 'ArrowUp':
                e.preventDefault();
                highlightIndex = Math.max(highlightIndex - 1, -1);
                updateHighlight();
                break;
            case 'Escape':
                hideAutocomplete();
                break;
        }
    }

    // 자동완성 하이라이트를 업데이트하는 함수
    function updateHighlight() {
        const boardInput = document.getElementById('boardInput');
        document.querySelectorAll('.autocomplete-item').forEach((item, index) => {
            item.classList.toggle('highlighted', index === highlightIndex);
        });

        if (highlightIndex >= 0 && highlightIndex < autocompleteData.length) {
            boardInput.value = autocompleteData[highlightIndex];
        }
    }

    // 자동완성 항목을 선택하는 함수
    function selectAutocompleteItem(index) {
        if (index >= 0 && index < autocompleteData.length) {
            safeSetBoardInput(autocompleteData[index]);
        }
    }

    // ==================== 크롤링 시스템 ====================
    // 크롤링을 시작하는 메인 함수
    async function startCrawling() {
        if (isLoading) return;
        
        isLoading = true;
        crawlStartTime = Date.now();
        
        const lang = window.languages[currentLanguage];
        const crawlBtn = document.getElementById('crawlBtn');
            crawlBtn.textContent = lang.loadingTexts || lang.crawlingStatus?.crawling || '크롤링 중...';
            crawlBtn.disabled = true;
            
        const board = document.getElementById('boardInput').value.trim();
        const isAdvanced = document.getElementById('advancedSearch').checked;
        
        let start, end;
        if (isAdvanced) {
            start = parseInt(document.getElementById('startRankAdv').value) || 1;
            end = parseInt(document.getElementById('endRankAdv').value) || 20;
        } else {
            start = parseInt(document.getElementById('startRank').value) || 1;
            end = parseInt(document.getElementById('endRank').value) || 20;
        }
        
        const limit = Math.max(end, 50);
        
        let minViews = 0, minLikes = 0, minComments = 0;
        if (isAdvanced) {
            minViews = parseInt(document.getElementById('minViews').value) || 0;
            minLikes = parseInt(document.getElementById('minRecommend').value) || 0;
            minComments = parseInt(document.getElementById('minComments').value) || 0;
        }

        currentCrawlId = `crawl_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
        console.log(`크롤링 시작 ID: ${currentCrawlId}`);

        const timePeriod = document.getElementById('timePeriod').value;
        const startDateInput = document.getElementById('startDate').value;
        const endDateInput = document.getElementById('endDate').value;
        
        let actualStartDate = null;
        let actualEndDate = null;
        let actualTimeFilter = timePeriod;

        if (timePeriod === 'custom') {
            actualStartDate = startDateInput;
            actualEndDate = endDateInput;
            actualTimeFilter = 'custom';
        } else {
            actualStartDate = null;
            actualEndDate = null;
            actualTimeFilter = timePeriod;
        }

        const hasDateFilter = !!(actualStartDate && actualEndDate);
        const hasMetricFilter = minViews > 0 || minLikes > 0 || minComments > 0;

        const config = {
            board,
            limit,
            language: currentLanguage,
            start: start,
            end: end,
            sort: document.getElementById('sortMethod').value,
            min_views: minViews,
            min_likes: minLikes,
            min_comments: minComments,
            time_filter: actualTimeFilter,
            crawl_id: currentCrawlId
        };

        if (hasDateFilter || hasMetricFilter) {
            config.full_crawl_mode = true;
            console.log(`전체 크롤링 모드 활성화`);
        }

        if (hasDateFilter) {
            config.start_date = actualStartDate;
            config.end_date = actualEndDate;
            console.log(`사용자 지정 날짜: ${actualStartDate} ~ ${actualEndDate}`);
        } else {
            delete config.start_date;
            delete config.end_date;
            console.log(`시간 필터: ${actualTimeFilter}`);
        }

        console.log('크롤링 설정:', {
            site: currentSite,
            board: config.board,
            time_filter: config.time_filter,
            start_date: config.start_date,
            end_date: config.end_date,
            sort: config.sort,
            range: `${config.start}-${config.end}`,
            crawl_id: currentCrawlId
        });

        updateCrawlButton();
        showProgress();
        clearResults();

        document.getElementById('progressFill').style.width = '0%';

        try {
            let endpoint;
            if (currentSite === 'lemmy') {
                endpoint = 'lemmy-crawl';
            } else if (currentSite === 'universal') {
                endpoint = 'auto-crawl';
            } else {
                endpoint = `${currentSite}-crawl`;
            }
            
            console.log(`WebSocket 연결 시도: ${WS_BASE_URL}/ws/${endpoint}`);
            
            // Origin 헤더 로깅
            console.log('Client Origin:', window.location.origin);
            console.log('Target WebSocket URL:', `${WS_BASE_URL}/ws/${endpoint}`);
            
            currentSocket = await createWebSocketWithRetry(endpoint, config);
            
            if (currentSocket.readyState === 1) {
                // 이미 연결된 상태면 바로 전송
                console.log('즉시 전송:', config);
                currentSocket.send(JSON.stringify(config));
                showCancelButton();
            } else {
                // 연결 대기 중이면 이벤트 등록
                currentSocket.onopen = () => {
                    console.log('onopen 이벤트로 전송:', config);
                    currentSocket.send(JSON.stringify(config));
                    showCancelButton();
                };
            }
            
            currentSocket.onerror = (error) => {
                console.error('WebSocket 오류:', error);
                console.error('시도한 URL:', `${WS_BASE_URL}/ws/${endpoint}`);
                console.error('Origin:', window.location.origin);
                showTemporaryMessage('connection_failed', 'error');
                hideProgress();
                isLoading = false;
                updateCrawlButton();
                currentSocket = null;
                hideCancelButton();
            };

            currentSocket.onmessage = (event) => {
                const data = JSON.parse(event.data);
                
                console.log('WebSocket 메시지 수신:', data);
                
                if (data.cancelled) {
                    console.log('크롤링 취소됨:', data.message);
                    showTemporaryMessage(data.message || '크롤링이 취소되었습니다.', 'info');
                    hideProgress();
                    isLoading = false;
                    updateCrawlButton();
                    currentSocket.close();
                    currentSocket = null;
                    currentCrawlId = null;
                    hideCancelButton();
                    return;
                }

                if (data.progress !== undefined) {
                    let translatedStatus = data.status; // 기본값
                    
                    // 🔥 새로운 방식: status_key가 있으면 번역 처리
                    if (data.status_key) {
                        translatedStatus = getTranslatedStatus(data.status_key, data.status_data);
                    }
                    // 🔥 기존 방식: 하드코딩된 메시지들도 처리 (하위 호환)
                    else if (data.status) {
                        translatedStatus = translateLegacyStatus(data.status);
                    }
                    
                    updateProgress(
                        data.progress, 
                        translatedStatus, 
                        data.found_posts || data.total_found || 0,
                        data.current_page || data.page || 1
                    );
                }
                
                // 에러 메시지도 같은 방식으로 처리
                if (data.error_key) {
                    const translatedError = getTranslatedStatus(data.error_key, data.error_data);
                    showTemporaryMessage(translatedError, 'error');
                    return;
                }
                
                // 기존 에러 처리 (하위 호환)
                if (data.error) {
                    showTemporaryMessage(data.error, 'error');
                    return;
                }
                if (data.done) {
                    console.log('크롤링 완료, 데이터 확인:', data);
                    
                    if (data.data && Array.isArray(data.data) && data.data.length > 0) {
                        crawlResults = data.data;
                        console.log('결과 저장 완료:', crawlResults.length, '개 항목');
                        
                        updateProgress(100, 'complete', data.data.length, 1);
                        
                        // 🔥 displayResults 호출 시 성공 메시지 비활성화 (WebSocket에서 처리)
                        displayResults(data.data, start, false);
                        
                        setTimeout(() => {
                            hideProgress();
                            isLoading = false;
                            updateCrawlButton();
                            hideCancelButton();
                            showDownloadButton();
                            ensureSearchInterfaceVisible();
                        }, 500);
                        
                    } else {
                        console.warn('빈 결과 또는 잘못된 데이터 형식:', data.data);
                        updateProgress(100, 'No results found', 0, 1);
                        showTemporaryMessage('검색 결과가 없습니다.', 'info');
                        
                        setTimeout(() => {
                            hideProgress();
                            isLoading = false;
                            updateCrawlButton();
                            hideCancelButton();
                        }, 1000);
                    }
                    
                    if (currentSocket) {
                        currentSocket.close();
                        currentSocket = null;
                    }
                    
                    // 🔥 summary 메시지 처리 (백엔드에서 오는 완료 메시지만 표시)
                    if (data.summary) {
                        setTimeout(() => {
                            let message;
                            if (typeof data.summary === 'object' && data.summary.message_key) {
                                // 백엔드에서 구조화된 메시지가 온 경우
                                message = formatCrawlMessage(data.summary.message_key, data.summary.message_data,lang);
                            } else {
                                // 백엔드에서 직접 문자열이 온 경우
                                message = data.summary;
                            }
                            showTemporaryMessage(message, 'success');
                        }, 800);
                    } else if (data.data && data.data.length > 0) {
                        // 🔥 백엔드에서 summary가 없으면 프론트엔드에서 기본 메시지 생성
                        setTimeout(() => {
                            const messageData = {
                                site: currentSite?.toUpperCase() || 'SITE',
                                count: data.data.length,
                                start: start || 1,
                                end: (start || 1) + data.data.length - 1
                            };
                            
                            const message = formatCrawlMessage('complete', messageData);
                            showTemporaryMessage(message, 'success');
                        }, 800);
                    }
                }
            };

            currentSocket.onclose = () => {
                console.log('WebSocket 연결 종료');
                
                // 연결 종료 시 상태 정리
                if (isLoading && crawlResults.length > 0) {
                    // 결과가 있는데 로딩 중이면 완료 처리
                    isLoading = false;
                    hideProgress();
                    showDownloadButton();
                    hideCancelButton();
                    updateCrawlButton();
                }
                
                currentSocket = null;
            };

        } catch (error) {
            console.error('WebSocket 연결 완전 실패:', error);
            
            // 상세한 오류 정보 표시
            showEnhancedError(
                '서버 연결에 실패했습니다.',
                `오류: ${error.message}\n현재 환경: ${window.location.hostname}\n대상 서버: ${WS_BASE_URL}`
            );
            
            hideProgress();
            isLoading = false;
            updateCrawlButton();
            currentSocket = null;
            hideCancelButton();
        }
    }

    // 임시 메시지를 표시하는 함수
    function showTemporaryMessage(message, type = 'info', variables = {}) {
        const messageDiv = document.createElement('div');
        let translatedMessage = message;
        
        // 메시지가 언어 키인 경우 번역
        const lang = window.languages[currentLanguage];
        if (lang && lang.notifications && lang.notifications[message]) {
            translatedMessage = lang.notifications[message];
            
            // 템플릿 변수 치환
            Object.keys(variables).forEach(key => {
                translatedMessage = translatedMessage.replace(`{${key}}`, variables[key]);
            });
        }
        
        // CSS 클래스 적용
        messageDiv.className = `temporary-message ${type}`;
        messageDiv.textContent = translatedMessage;
        
        document.body.appendChild(messageDiv);
        
        // 표시 애니메이션
        setTimeout(() => {
            messageDiv.classList.add('show');
        }, 100);
        
        // 숨김 애니메이션 후 제거
        setTimeout(() => {
            messageDiv.classList.remove('show');
            messageDiv.classList.add('hide');
            
            setTimeout(() => {
                if (document.body.contains(messageDiv)) {
                    document.body.removeChild(messageDiv);
                }
            }, 300);
        }, 3000);
    }
    //백엔드에서 처리한 임시 메세지 표시
    function formatCrawlMessage(messageKey, messageData) {
        const lang = window.languages[currentLanguage];
        
        // 언어팩에서 템플릿 가져오기
        let template = lang.messages?.crawl?.[messageKey];
        
        if (!template) {
            console.warn(`메시지 템플릿을 찾을 수 없음: ${messageKey} (언어: ${currentLanguage})`);
            return `Message template not found: ${messageKey}`;
        }
        
        // 템플릿 변수 치환
        if (messageData && typeof template === 'string') {
            Object.keys(messageData).forEach(key => {
                template = template.replace(new RegExp(`\\{${key}\\}`, 'g'), messageData[key]);
            });
        }
        
        return template;
    }

    // 백엔드에서 처리하는 progress-message 메시지 템플릿을 실제 텍스트로 변환하는 함수
    function formatMessage(template, data = {}) {
        if (!template) return '';
        
        let message = template;
        Object.keys(data).forEach(key => {
            const placeholder = `{${key}}`;
            message = message.replace(new RegExp(placeholder, 'g'), data[key]);
        });
        
        return message;
    }

    // WebSocket 메시지에서 번역된 상태 메시지 생성
    function getTranslatedStatus(status_Key, status_Data = {}) {
        const lang = window.languages[currentLanguage];
        const template = lang.crawlingStatus?.[status_Key];
        const data_templete = lang.crawlingStatus?.[status_Data]

        if (!template) {
            console.warn(`Missing translation for status key: ${status_Key}`);
            return statusKey; // 키가 없으면 키 자체를 반환
        }
        
        return formatMessage(template, data_templete);
    }

    // 기존 하드코딩된 메시지들을 번역하는 함수 (하위 호환용)
    // 현재 translateLegacyStatus 함수에 패턴 추가
    function translateLegacyStatus(status) {
        const lang = window.languages[currentLanguage];
        
        // 🔥 패턴 매칭 규칙 확장
        const statusPatterns = [
            { pattern: /메타데이터 보강/, key: 'metadata_processing' },
            { pattern: /게시물 수집/, key: 'collecting_posts' },
            { pattern: /데이터 분석/, key: 'analyzing_content' },
            { pattern: /결과 필터링/, key: 'filtering_results' },
            { pattern: /번역 준비/, key: 'preparing_translation' },
            { pattern: /Reddit.*정렬로 수집/, key: 'reddit_analyzing' },
            { pattern: /DCInside.*파싱/, key: 'dcinside_parsing' },
            { pattern: /Blind.*처리/, key: 'blind_processing' },
            { pattern: /BBC.*가져오는/, key: 'bbc_fetching' },
            { pattern: /Lemmy.*연결/, key: 'lemmy_connecting' },
            { pattern: /웹페이지 분석/, key: 'universal_parsing' }
        ];
        
        for (const {pattern, key} of statusPatterns) {
            if (pattern.test(status)) {
                return lang.crawlingStatus?.[key] || status;
            }
        }
        
        return status;
    }

    // 검색 인터페이스가 보이도록 보장하는 함수
    function ensureSearchInterfaceVisible() {
        const boardSearchContainer = document.getElementById('boardSearchContainer');
        const optionsContainer = document.getElementById('optionsContainer');
        const buttonContainer = document.getElementById('buttonContainer');
        
        boardSearchContainer.classList.add('show');
        optionsContainer.classList.add('show');
        buttonContainer.classList.add('show');
    }

    // 취소 버튼을 표시하는 함수
    function showCancelButton() {
        const cancelBtn = document.getElementById('cancelBtn');
        cancelBtn.style.display = 'inline-flex';
    }

    // 취소 버튼을 숨기는 함수
    function hideCancelButton() {
        const cancelBtn = document.getElementById('cancelBtn');
        cancelBtn.style.display = 'none';
    }

    // 다운로드 버튼을 표시하는 함수
    function showDownloadButton() {
        const downloadBtn = document.getElementById('downloadBtn');
        downloadBtn.style.display = 'inline-flex';
    }

    // 다운로드 버튼을 숨기는 함수
    function hideDownloadButton() {
        const downloadBtn = document.getElementById('downloadBtn');
        downloadBtn.style.display = 'none';
    }

    // 크롤링을 취소하는 함수
    function cancelCrawling() {
        console.log(`크롤링 취소 요청: ${currentCrawlId}`);
        
        if (currentSocket) {
            currentSocket.close();
            currentSocket = null;
        }
        
        if (currentCrawlId) {
            sendCancelRequest(currentCrawlId);
        }
        
        isLoading = false;
        updateCrawlButton();
        hideProgress();
        hideCancelButton();
        
        updateProgress(0);
        
        const lang = window.languages[currentLanguage];
        showTemporaryMessage(lang.crawlingStatus?.cancelled || '크롤링이 취소되었습니다.', 'info');
        
        currentCrawlId = null;
    }

    // 백엔드에 취소 요청을 보내는 함수
    async function sendCancelRequest(crawlId) {
        try {
            console.log(`백엔드 취소 요청 전송: ${crawlId}`);
            
            const response = await fetch('http://localhost:8000/api/cancel-crawl', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    crawl_id: crawlId,
                    action: 'cancel'
                })
            });
            
            if (response.ok) {
                const result = await response.json();
                console.log('취소 요청 성공:', result);
            } else {
                console.warn('취소 요청 실패:', response.status);
            }
        } catch (error) {
            console.error('취소 요청 오류:', error);
        }
    }

    // 페이지 벗어날 때 크롤링 정리하는 이벤트 리스너
    window.addEventListener('beforeunload', function() {
        if (currentCrawlId) {
            console.log('페이지 종료시 크롤링 정리');
            sendCancelRequest(currentCrawlId);
        }
    });

    // Excel 파일을 다운로드하는 함수
    function downloadExcel() {
        if (crawlResults.length === 0) {
            showTemporaryMessage('no_data', 'error');
            return;
        }

        const headers = ['번호', '원제목', '번역제목', '링크', '본문', '조회수', '추천수', '댓글수', '작성일'];
        const csvContent = [
            headers.join(','),
            ...crawlResults.map(item => [
                item.번호 || '',
                `"${(item.원제목 || '').replace(/"/g, '""')}"`,
                `"${(item.번역제목 || '').replace(/"/g, '""')}"`,
                item.링크 || '',
                `"${(item.본문 || '').replace(/"/g, '""')}"`.replace(/\n/g, ' '),
                item.조회수 || 0,
                item.추천수 || 0,
                item.댓글수 || 0,
                `"${(item.작성일 || '').replace(/"/g, '""')}"`
            ].join(','))
        ].join('\n');

        const BOM = '\uFEFF';
        const blob = new Blob([BOM + csvContent], { type: 'text/csv;charset=utf-8;' });
        
        const now = new Date();
        const dateStr = now.getFullYear() + 
                    String(now.getMonth() + 1).padStart(2, '0') + 
                    String(now.getDate()).padStart(2, '0') + '_' +
                    String(now.getHours()).padStart(2, '0') +
                    String(now.getMinutes()).padStart(2, '0');
        
        const filename = `${currentSite}_crawl_${dateStr}.csv`;
        
        const link = document.createElement('a');
        if (link.download !== undefined) {
            const url = URL.createObjectURL(blob);
            link.setAttribute('href', url);
            link.setAttribute('download', filename);
            link.style.visibility = 'hidden';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            URL.revokeObjectURL(url);
            
            showTemporaryMessage('download_success', 'success', { filename: filename });
        }
    }

    // ==================== 진행 상황 및 결과 표시 ====================
    // 진행 상황을 표시하는 함수
    function showProgress() {
        const progressContainer = document.getElementById('progressContainer');
        progressContainer.classList.add('show');
        document.getElementById('progressDetails').style.display = 'flex';
        updateProgress(0);
    }

    // 진행 상황을 숨기는 함수
    function hideProgress() {
        const progressContainer = document.getElementById('progressContainer');
        progressContainer.classList.remove('show');
        document.getElementById('progressDetails').style.display = 'none';
    }

    // 진행 상황을 업데이트하는 함수
    function updateProgress(percent, status = null, foundPosts = 0, currentPage = 1) {
        const lang = window.languages[currentLanguage];

        document.getElementById('progressFill').style.width = percent + '%';
        
        if (status) {
            const statusMap = {
                'connecting': lang.crawlingStatus?.connecting || '서버에 연결 중...',
                'initializing': lang.crawlingStatus?.initializing || '크롤링 준비 중...',
                'crawling': lang.crawlingStatus?.crawling || '게시글 수집 중...',
                'processing': lang.crawlingStatus?.processing || '데이터 처리 중...',
                'filtering': lang.crawlingStatus?.filtering || '조건에 맞는 게시글 필터링 중...',
                'translating': lang.crawlingStatus?.translating || '제목 번역 중...',
                'finalizing': lang.crawlingStatus?.finalizing || '결과 정리 중...',
                'complete': lang.crawlingStatus?.complete || '수집 완료!'
            };
            
            document.getElementById('progressText').textContent = statusMap[status] || status;
        } else {
            document.getElementById('progressText').textContent = percent + '%';
        }
        
        // 라벨들도 번역 적용
        const postsLabel = document.getElementById('postsLabel');
        const pageLabel = document.getElementById('pageLabel');
        
        if (postsLabel) postsLabel.textContent = lang.crawlingStatus?.found || '개 수집';
        if (pageLabel) pageLabel.textContent = lang.crawlingStatus?.page || '페이지';
        
        // 발견된 게시글 수 표시
        if (foundPosts > 0) {
            document.getElementById('foundPosts').textContent = foundPosts;
        }
        
        // 현재 페이지 표시
        if (currentPage > 0) {
            document.getElementById('currentPage').textContent = currentPage;
        }
        
        // 예상 시간 계산 및 표시
        if (crawlStartTime && percent > 10) {
            const elapsed = Date.now() - crawlStartTime;
            const estimated = (elapsed / percent) * (100 - percent);
            const minutes = Math.floor(estimated / 60000);
            const seconds = Math.floor((estimated % 60000) / 1000);
            
            let timeText = (lang.crawlingStatus?.timeRemaining || '예상 시간') + ': ';
            if (minutes > 0) {
                timeText += `${minutes}${lang.resultTexts?.minutes || '분'} ${seconds}${lang.resultTexts?.seconds || '초'}`;
            } else {
                timeText += `${seconds}${lang.resultTexts?.seconds || '초'}`;
            }
            
            document.getElementById('progressEta').textContent = timeText;
        } else {
            document.getElementById('progressEta').textContent = (lang.crawlingStatus?.timeRemaining || '예상 시간') + ': ' + (lang.resultTexts?.calculating || '계산 중...');
        }
    }

    // 결과를 초기화하는 함수
    function clearResults() {
        const container = document.getElementById('resultsContainer');
        const downloadBtn = document.getElementById('downloadBtn');
        
        container.innerHTML = '';
        downloadBtn.style.display = 'none';
        crawlResults = [];
        
        container.style.opacity = '0';
        container.style.transform = 'translateY(-8px)';
        
        setTimeout(() => {
            container.style.opacity = '1';
            container.style.transform = 'translateY(0)';
        }, 300);
    }

    // 크롤링 결과를 표시하는 함수
    function displayResults(results, startIndex = 1) {
        const container = document.getElementById('resultsContainer');
        const lang = window.languages[currentLanguage];
        
        if (results.length === 0) {
            container.innerHTML = `<p style="text-align: center; color: #5f6368; font-size: 16px; padding: 40px;">${lang.resultTexts.noResults}</p>`;
            return;
        }
        
        // 완료 알림
        setTimeout(() => {
            const successMsg = (lang.crawlingStatus?.complete || '수집 완료') + `! ${results.length}${lang.crawlingStatus?.found || '개 게시글을 찾았습니다'}`;
            showTemporaryMessage(successMsg, 'success');
        }, 500);
        
        const elapsedTime = crawlStartTime ? Math.round((Date.now() - crawlStartTime) / 1000) : 0;
        
        const isAdvanced = document.getElementById('advancedSearch').checked;
        const start = isAdvanced ? parseInt(document.getElementById('startRankAdv').value) || 1 : parseInt(document.getElementById('startRank').value) || 1;
        const end = isAdvanced ? parseInt(document.getElementById('endRankAdv').value) || 20 : parseInt(document.getElementById('endRank').value) || 20;
        const estimatedPages = Math.ceil(end / 25);
        
        const summaryHtml = `
            <div style="
                background: #f8f9fa; 
                border-radius: 12px; 
                padding: 16px; 
                margin-bottom: 16px; 
                box-shadow: 0 2px 8px rgba(32,33,36,.1);">

                <div style="
                    display: flex; 
                    align-items: center; 
                    gap: 12px; 
                    margin-bottom: 16px;">

                    <div style="
                        width: 40px; 
                        height: 40px; 
                        background: white; 
                        border-radius: 50%;
                        display: flex; 
                        align-items: center; 
                        justify-content: center;">
                        
                        <img src="logo.png" alt="통계" style="width: 24px; height: 24px;">
                    </div>
                    <div>
                        <h3 style="color: #ff8000; margin: 0; font-size: 16px; font-weight: 550;">
                            ${lang.resultTexts.crawlComplete}
                        </h3>
                        <p style="color: #5f6368; margin: 0px 0 0 0; font-size: 11.5px;">
                            ${new Date().toLocaleString(currentLanguage === 'ko' ? 'ko-KR' : currentLanguage === 'ja' ? 'ja-JP' : 'en-US')} ${lang.resultTexts.completedAt}
                        </p>
                    </div>
                </div>
                
                <div style="display: grid; 
                    grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); 
                    gap: 16px; 
                    margin-bottom: 16px;">

                    <div style="
                        text-align: center; 
                        background: white; 
                        padding: 4px 6px; 
                        border-radius: 8px; 
                        border: 1px solid #e8eaed;">

                        <div style="
                            font-size: 16px; 
                            font-weight: 550; 
                            color: #ff8000; 
                            margin-top: 4px;">
                            ${results.length}
                        </div>

                        <div style="
                            font-size: 12px;
                            color: #5f6368;">
                            ${lang.resultTexts.totalPosts}
                        </div>
                    </div>

                    <div style="
                        text-align: center; 
                        background: white; 
                        padding: 4px 6px; 
                        border-radius: 8px; 
                        border: 1px solid #e8eaed;">

                        <div style="
                            font-size: 16px; 
                            font-weight: 550; 
                            color: #ff8000; 
                            margin-top: 4px;">
                            ${start}-${end}
                        </div>
                        <div style="
                            font-size: 12px; 
                            color: #5f6368;">
                            ${lang.resultTexts.rankRange || '순위 범위'}
                        </div>
                    </div>

                    <div style="
                        text-align: center; 
                        background: white; 
                        padding: 4px 6px; 
                        border-radius: 8px; 
                        border: 1px solid #e8eaed;">
                        
                        <div style="
                        font-size: 16px; 
                        font-weight: 550; 
                        color: #ff8000; 
                        margin-top: 4px;">
                        ~${estimatedPages}
                    </div>
                        <div style="
                        font-size: 12px;
                        color: #5f6368;">
                        ${lang.resultTexts.estimatedPages || '예상 페이지'}
                    </div>
                    </div>

                    <div style="
                        text-align: center; 
                        background: white; 
                        padding: 4px 6px; 
                        border-radius: 8px; 
                        border: 1px solid #e8eaed;">
                        
                        <div style="
                            font-size: 16px; 
                            font-weight: 550; 
                            color: #ff8000; 
                            margin-top: 4px;">
                            ${currentSite.toUpperCase()}
                        </div>

                        <div style="
                            font-size: 12px; 
                            color: #5f6368;">
                            ${lang.resultTexts.sourceSite}
                        </div>
                    </div>
                </div>
                
                <div style="
                    display: flex; 
                    justify-content: space-between; 
                    align-items: center; 
                    padding-top: 16px; 
                    border-top: 1px solid #e8eaed;">
                    
                    <div style="
                        display: flex; 
                        align-items: center; 
                        gap: 8px;">
                        
                        <span style="
                            font-size: 14px; 
                            color: #5f6368;">
                            ${lang.resultTexts.crawlMode || '크롤링 모드'}:
                        </span>

                        <span style="
                            font-size: 14px; 
                            font-weight: 500; 
                            color: #ff8000;">
                            ${isAdvanced ? (lang.resultTexts.advancedMode || '고급 검색색') : (lang.resultTexts.basicMode || '기본')}
                        </span>

                    </div>
                    <div style="
                        display: flex; 
                            align-items: center; 
                            gap: 8px;">

                        <span style="
                            font-size: 14px; 
                            color: #5f6368;">
                            ⏱️ ${lang.resultTexts.elapsedTime}:
                        </span>

                        <span style="
                            font-size: 14px;
                            font-weight: 500; 
                            color: #137333;">
                            ${elapsedTime}${lang.resultTexts.seconds}
                        </span>
                    </div>
                </div>
            </div>
        `;

        const resultsHtml = results.map((item, index) => {
            const itemNumber = startIndex + index;
            
            const title = item.원제목 || item.title || item.제목 || '';
            const translatedTitle = item.번역제목 || item.translated_title || '';
            const link = item.링크 || item.link || item.url || '#';
            const content = item.본문 || item.content || item.내용 || '';
            const views = item.조회수 || item.views || 0;
            const likes = item.추천수 || item.likes || item.score || 0;
            const comments = item.댓글수 || item.comments || 0;
            const date = item.작성일 || item.date || item.created_at || '';
            
            return `
                <div class="result-item" style="opacity: 0; transform: translateY(8px);">
                    <div class="result-header">
                        <div style="display: flex; align-items: flex-start; flex: 1;">
                            <div class="result-number">${itemNumber}</div>
                            <div style="flex: 1;">
                                <a href="${link}" target="_blank" class="result-title" rel="noopener noreferrer">
                                    ${title}
                                </a>
                                ${translatedTitle ? `<div class="result-translation">${translatedTitle}</div>` : ''}
                            </div>
                        </div>
                    </div>
                    
                    <div class="result-meta-row">
                        <div class="result-date">
                            📅 ${date}
                        </div>
                        <div class="result-stats">
                            ${views > 0 ? `<div class="stat-item">👁️ ${views.toLocaleString()}</div>` : ''}
                            ${likes > 0 ? `<div class="stat-item">👍 ${likes.toLocaleString()}</div>` : ''}
                            ${comments > 0 ? `<div class="stat-item">💬 ${comments.toLocaleString()}</div>` : ''}
                        </div>
                    </div>
                    
                    ${content ? `
                        <div class="result-content">
                            ${content.length > 200 ? content.substring(0, 200) + '...' : content}
                        </div>
                    ` : ''}
                    
                    <div class="result-links">
                        <a href="${link}" target="_blank" rel="noopener noreferrer">
                            ${lang.original || '원문 보기'}
                        </a>
                    </div>
                </div>
            `;
        }).join('');

        container.innerHTML = summaryHtml + resultsHtml;
        
        const resultItems = container.querySelectorAll('.result-item');
        resultItems.forEach((item, index) => {
            setTimeout(() => {
                item.style.opacity = '1';
                item.style.transform = 'translateY(0)';
            }, index * 100);
        });

        setTimeout(() => {
            showDownloadButton();  // 다운로드 버튼 강제 표시
            hideCancelButton();    // 취소 버튼 숨김
            
            // 크롤링 버튼 텍스트도 원래대로 복원
            const lang = window.languages[currentLanguage];
            document.getElementById('crawlBtn').textContent = lang.start || '크롤링 시작';
        }, 100);

        console.log(`${results.length}개 결과 표시 완료`);
    }

    // ==================== 유틸리티 함수 ====================
    // DOM 요소를 안전하게 쿼리하는 함수
    function safeQuerySelector(selector) {
        try {
            return document.querySelector(selector) || document.getElementById(selector);
        } catch (e) {
            console.warn(`Selector not found: ${selector}`);
            return null;
        }
    }

    // DOM 요소를 안전하게 업데이트하는 함수
    function safeUpdateElement(selector, property, value) {
        const element = safeQuerySelector(selector);
        if (element && value !== undefined) {
            element[property] = value;
        }
    }

    // URL에서 사이트명을 추출하는 함수
    function extractSiteName(url) {
        try {
            const urlObj = new URL(url.startsWith('http') ? url : 'https://' + url);
            const hostname = urlObj.hostname.toLowerCase();
            
            const siteMap = {
                'reddit.com': 'Reddit',
                'www.reddit.com': 'Reddit',
                'dcinside.com': 'DCInside',
                'gall.dcinside.com': 'DCInside',
                'teamblind.com': 'Blind',
                'blind.com': 'Blind',
                'lemmy.world': 'Lemmy',
                'lemmy.ml': 'Lemmy',
                'beehaw.org': 'Lemmy'
            };
            
            if (siteMap[hostname]) {
                return siteMap[hostname];
            }
            
            let siteName = hostname.replace(/^(www\.|m\.|mobile\.)/, '');
            
            siteName = siteName.split('.')[0];
            siteName = siteName.charAt(0).toUpperCase() + siteName.slice(1);
            
            return siteName;
            
        } catch (error) {
            return url;
        }
    }

    // 강화된 에러 메시지를 표시하는 함수
    function showEnhancedError(message, details = null) {
        const errorDiv = document.createElement('div');
        errorDiv.style.cssText = `
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: white;
            border: 2px solid #d93025;
            border-radius: 8px;
            padding: 20px;
            max-width: 400px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.3);
            z-index: 10002;
            font-family: arial, sans-serif;
        `;
        
        errorDiv.innerHTML = `
            <div style="color: #d93025; font-weight: bold; margin-bottom: 10px;">
                ❌ 오류 발생
            </div>
            <div style="color: #202124; margin-bottom: 15px;">
                ${message}
            </div>
            ${details ? `<div style="color: #5f6368; font-size: 12px; margin-bottom: 15px;">${details}</div>` : ''}
            <button onclick="this.parentElement.remove()" style="
                background: #1a73e8;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                cursor: pointer;
                float: right;
            ">확인</button>
            <div style="clear: both;"></div>
        `;
        
        document.body.appendChild(errorDiv);
        
        setTimeout(() => {
            if (document.body.contains(errorDiv)) {
                errorDiv.remove();
            }
        }, 5000);
    }

    // 사이트를 자동으로 감지하는 함수
    function enhancedSiteDetection(input) {
        const patterns = [
            { pattern: /reddit\.com/i, site: 'reddit', name: 'Reddit' },
            { pattern: /(dcinside\.com|gall\.dcinside)/i, site: 'dcinside', name: 'DCInside' },
            { pattern: /(teamblind\.com|blind\.com)/i, site: 'blind', name: 'Blind' },
            { pattern: /(bbc\.com|bbc\.co\.uk)/i, site: 'bbc', name: 'BBC' },
            { pattern: /lemmy\./i, site: 'lemmy', name: 'Lemmy' },
            { pattern: /beehaw\.org/i, site: 'lemmy', name: 'Lemmy' },
            { pattern: /sh\.itjust\.works/i, site: 'lemmy', name: 'Lemmy' }
        ];
        
        for (const {pattern, site, name} of patterns) {
            if (pattern.test(input)) {
                return { site, name };
            }
        }
        
        return null;
    }

    // 입력 유효성을 검사하는 함수
    function validateInput(site, boardInput) {
        const errors = [];
        
        if (!site) {
            errors.push('사이트를 선택해주세요');
            return errors;
        }
        
        if (!boardInput.trim()) {
            if (site === 'universal') {
                errors.push('크롤링할 웹사이트 URL을 입력해주세요');
            } else {
                errors.push('게시판 이름을 입력해주세요');
            }
            return errors;
        }
        
        switch (site) {
            case 'universal':
                if (!boardInput.startsWith('http')) {
                    errors.push('범용 크롤러는 http:// 또는 https://로 시작하는 완전한 URL이 필요합니다');
                }
                break;
                
            case 'reddit':
                if (boardInput.includes('reddit.com') && !boardInput.includes('/r/')) {
                    errors.push('Reddit 게시판은 "/r/게시판명" 형태여야 합니다');
                }
                break;
                
            case 'lemmy':
                if (!boardInput.includes('@') && !boardInput.includes('lemmy')) {
                    errors.push('Lemmy 커뮤니티는 "커뮤니티명@인스턴스" 형태여야 합니다 (예: technology@lemmy.world)');
                }
                break;
        }
        
        return errors;
    }

    // 디버깅을 위한 콘솔 명령어
    window.debugCrawl = {
        getCurrentId: () => currentCrawlId,
        forceCancel: () => cancelCrawling(),
        getStatus: () => ({
            isLoading,
            currentSite,
            currentCrawlId,
            socketStatus: currentSocket ? 'connected' : 'disconnected'
        })
    };

    console.log('디버깅 명령어: window.debugCrawl.getStatus(), window.debugCrawl.forceCancel()');


    // 보드 입력창을 클리어하는 함수
    function clearBoardInput() {
        const boardInput = document.getElementById('boardInput');
        boardInput.value = '';
        document.getElementById('clearBoardBtn').style.display = 'none';
        
        hideAutocomplete();
        updateCrawlButton();
        
        // 포커스를 보드 입력창에 다시 설정
        boardInput.focus();
    }

    // ========================================
    // HTML onclick 함수들을 전역으로 노출
    // ========================================

    // 사이트 관련
    window.handleSiteSearch = handleSiteSearch;
    window.clearSiteInput = clearSiteInput;
    window.clearBoardInput = clearBoardInput;

    // 크롤링 관련
    window.startCrawling = startCrawling;
    window.cancelCrawling = cancelCrawling;
    window.downloadExcel = downloadExcel;
    window.goBack = goBack;
    window.toggleAdvancedSearch = toggleAdvancedSearch;

    // 모달 관련
    window.openBugReportModal = openBugReportModal;
    window.closeBugReportModal = closeBugReportModal;
    window.openTermsModal = openTermsModal;
    window.closeTermsModal = closeTermsModal;
    window.openPrivacyModal = openPrivacyModal;
    window.closePrivacyModal = closePrivacyModal;
    window.openBusinessModal = openBusinessModal;
    window.closeBusinessModal = closeBusinessModal;

    // 피드백 관련
    window.updateCharacterCount = updateCharacterCount;
    window.updateBugReportButton = updateBugReportButton;
    window.handleFileUpload = handleFileUpload;
    window.removeFile = removeFile;
    window.submitBugReport = submitBugReport;

    // 바로가기 관련
    window.openShortcutModal = openShortcutModal;
    window.closeShortcutModal = closeShortcutModal;
    window.saveShortcut = saveShortcut;
    window.useShortcut = useShortcut;

    // 언어 관련
    window.toggleLanguageDropdown = toggleLanguageDropdown;
    window.selectLanguage = selectLanguage;

    // 자동완성 관련
    window.selectBBCSection = selectBBCSection;
    window.setLemmyCommunity = setLemmyCommunity;
    window.selectAutocompleteItem = selectAutocompleteItem;
    window.selectSiteAutocompleteItem = selectSiteAutocompleteItem;

    // ========================================
    // 전역 변수들을 다른 파일에서 접근 가능하게 노출
    // ========================================
    window.PickPostGlobals = {
        // 변수 getter/setter
        getCurrentSite: () => currentSite,
        setCurrentSite: (site) => currentSite = site,
        getCurrentLanguage: () => currentLanguage,
        setCurrentLanguage: (lang) => currentLanguage = lang,
        getIsLoading: () => isLoading,
        setIsLoading: (loading) => isLoading = loading,
        
        // API 설정
        API_BASE_URL,
        WS_BASE_URL,
        
        // 유틸리티 함수
        showTemporaryMessage,
        extractSiteName,
        updateLabels
    };