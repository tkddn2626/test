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

let community_name = '';
let lemmy_instance = '';

// 전역 오류 처리기
window.addEventListener('error', function(e) {
    console.error('🚨 전역 JavaScript 오류:', {
        message: e.message,
        filename: e.filename,
        lineno: e.lineno,
        timestamp: new Date().toISOString()
    });
    
    if (e.message.includes('community_name')) {
        window.community_name = '';
        window.lemmy_instance = '';
        showMessage('Input validation error fixed. Please try again.', 'info');
    } else if (e.message.includes('Cannot read properties of undefined')) {
        showMessage('pageRefreshNeeded', 'warning', { translate: true });
    } else {
        showMessage('errorMessages.general', 'warning', { translate: true });
    }
});

//언어 감지 함수
function get_user_language(config) {  // async 제거
    return config.get ? config.get("language", "en") : (config.language || "en");
}

function handleSpecificErrors(e) {
    if (e.message.includes('community_name is not defined')) {
        console.warn('🔧 community_name 변수 오류 - 자동 복구 시도');
        window.community_name = '';
        window.lemmy_instance = '';
        showMessage('Input validation error fixed. Please try again.', 'info');
        
    } else if (e.message.includes('Cannot read properties of undefined')) {
        console.warn('🔧 undefined 속성 접근 오류 - DOM 요소 체크');
        setTimeout(checkAndRepairDOMElements, 200);
        
    } else {
        showMessage('A temporary error occurred. Please try again.', 'warning');
    }
}

// 필수 DOM 요소들 존재 확인
function checkRequiredElements() {
    const requiredElements = [
        'boardInput', 'crawlBtn', 'siteInput', 
        'minViews', 'minRecommend', 'minComments',
        'sortMethod', 'timePeriod', 'autocomplete'
    ];
    
    return requiredElements.filter(id => !document.getElementById(id));
}

// ==================== API 및 환경 설정 ====================
// 환경별 API 설정을 반환하는 함수
function getApiConfig() {
    const hostname = window.location.hostname;
    
    if (hostname === 'localhost' || hostname === '127.0.0.1') {
        return {
            API_BASE_URL: 'http://localhost:8000',
            WS_BASE_URL: 'ws://localhost:8000'
        };
    }
    
    // 🔥 현재 배포된 정확한 도메인 사용
    const RENDER_DOMAIN = 'test-1-zm0k.onrender.com';
    
    return {
        API_BASE_URL: `https://${RENDER_DOMAIN}`,
        WS_BASE_URL: `wss://${RENDER_DOMAIN}`
    };
}

// WebSocket 연결을 재시도 로직과 함께 생성하는 함수
async function createWebSocketWithRetry(endpoint, config, maxRetries = 2) {
    const { WS_BASE_URL } = getApiConfig();
    
    for (let retry = 0; retry < maxRetries; retry++) {
        try {
            console.log(`WebSocket 연결 시도 ${retry + 1}/${maxRetries}: ${endpoint}`);
            
            const wsUrl = `${WS_BASE_URL}/ws/${endpoint}`;
            const ws = new WebSocket(wsUrl);
            
            // 간단한 타임아웃
            const timeout = setTimeout(() => {
                if (ws.readyState === WebSocket.CONNECTING) {
                    ws.close();
                }
            }, 10000);
            
            return new Promise((resolve, reject) => {
                ws.onopen = () => {
                    clearTimeout(timeout);
                    console.log(`✅ WebSocket 연결 성공: ${endpoint}`);
                    
                    // 설정 전송
                    ws.send(JSON.stringify(config));
                    console.log('📤 크롤링 설정 전송:', config);
                    
                    // ✅ 메시지 핸들러 설정
                    setupWebSocketMessageHandlers(ws, endpoint);
                    
                    resolve(ws);
                };

                ws.onerror = (error) => {
                    clearTimeout(timeout);
                    console.error(`❌ WebSocket 연결 오류 (${endpoint}):`, error);
                    reject(new Error(`연결 실패: ${endpoint}`));
                };

                ws.onclose = (event) => {
                    clearTimeout(timeout);
                    if (event.code !== 1000) {
                        reject(new Error(`연결 종료: ${event.code}`));
                    }
                };
            });

        } catch (error) {
            console.warn(`연결 실패 ${retry + 1}/${maxRetries}:`, error.message);
            
            if (retry === maxRetries - 1) {
                throw error;
            }
            
            await new Promise(resolve => setTimeout(resolve, 1000));
        }
    }
}

// API 설정을 전역 변수로 저장
const { API_BASE_URL, WS_BASE_URL } = getApiConfig();
console.log('API 설정:', { API_BASE_URL, WS_BASE_URL });

// ==================== 언어 및 라벨 관리 ====================
// 현재 언어에 맞는 라벨을 반환하는 함수
function getLabels() {
    return window.languages[currentLanguage] || window.languages.ko;
}

// 정렬 방법 라벨 업데이트
function updateSortMethodLabels() {
    const sortSelect = document.getElementById('sortMethod');
    const lang = window.languages[currentLanguage] || window.languages.en;
    
    if (!sortSelect || !lang) return;
    
    const currentValue = sortSelect.value;
    
    Array.from(sortSelect.options).forEach(option => {
        const value = option.value;
        let newText = '';
        
        if (currentSite === 'reddit' && lang.sortOptions?.reddit?.[value]) {
            newText = lang.sortOptions.reddit[value];
        } else if (lang.sortOptions?.other?.[value]) {
            newText = lang.sortOptions.other[value];
        }
        
        if (newText) {
            option.textContent = newText;
            console.log(`✅ 정렬 옵션 업데이트: ${value} = ${newText}`);
        }
    });
    
    sortSelect.value = currentValue;
}


// 시간 필터 라벨 업데이트
function updateTimeFilterLabels() {
    const timePeriodSelect = document.getElementById('timePeriod');
    const lang = window.languages[currentLanguage] || window.languages.en;
    
    if (!timePeriodSelect || !lang.timeFilterLabels) return;
    
    const currentValue = timePeriodSelect.value;
    
    // 모든 옵션 업데이트
    Array.from(timePeriodSelect.options).forEach(option => {
        const value = option.value;
        if (lang.timeFilterLabels[value]) {
            option.textContent = lang.timeFilterLabels[value];
            console.log(`✅ 시간 필터 업데이트: ${value} = ${lang.timeFilterLabels[value]}`);
        }
    });
    
    timePeriodSelect.value = currentValue;
}


function updateLabels() {
    const lang = window.languages?.[currentLanguage] || window.languages?.en || {};
    
    console.log(`🔄 언어 업데이트: ${currentLanguage}`, lang);
    
    // ✅ 기본 UI 요소들
    const elements = [
        { id: 'crawlBtn', prop: 'textContent', value: lang.start },
        { id: 'cancelBtn', prop: 'textContent', value: lang.cancel },
        { id: 'downloadBtn', prop: 'textContent', value: lang.download },
        { id: 'siteInput', prop: 'placeholder', value: lang.sitePlaceholder },
        { id: 'boardInput', prop: 'placeholder', value: lang.boardPlaceholder }
    ];
    
    // ✅ 라벨 요소들 - ID 기반으로 직접 업데이트
    const labelElements = [
        { id: 'sortMethodLabel', value: lang.labels?.sortMethod },
        { id: 'timePeriodLabel', value: lang.labels?.timePeriod },
        { id: 'advancedSearchLabel', value: lang.labels?.advancedSearch },
        { id: 'startRankLabel', value: lang.labels?.startRank },
        { id: 'endRankLabel', value: lang.labels?.endRank },
        { id: 'startRankAdvLabel', value: lang.labels?.startRank },
        { id: 'endRankAdvLabel', value: lang.labels?.endRank },
        { id: 'minViewsLabel', value: lang.labels?.minViews },
        { id: 'minRecommendLabel', value: lang.labels?.minRecommend },
        { id: 'minCommentsLabel', value: lang.labels?.minComments }
    ];
    
    const modalCloseButtons = [
        'closePrivacyBtn',
        'closeTermsBtn', 
        'closeBusinessBtn'
    ];
    
    modalCloseButtons.forEach(buttonId => {
        const button = document.getElementById(buttonId);
        if (button) {
            button.textContent = lang.ok || 'OK';
        }
    });
    

    // 날짜 라벨들 (콜론 포함)
    const dateLabels = [
        { id: 'startDateLabel', value: (lang.labels?.startDate || 'Start Date') + ':' },
        { id: 'endDateLabel', value: (lang.labels?.endDate || 'End Date') + ':' }
    ];

    // 기본 요소들 업데이트
    elements.forEach(({ id, prop, value }) => {
        const element = document.getElementById(id);
        if (element && value) {
            element[prop] = value;
            console.log(`✅ 업데이트: ${id} = ${value}`);
        }
    });
    
    // 라벨 요소들 업데이트
    labelElements.forEach(({ id, value }) => {
        const element = document.getElementById(id);
        if (element && value) {
            element.textContent = value;
            console.log(`✅ 라벨 업데이트: ${id} = ${value}`);
        }
    });
    
    // 날짜 라벨들 업데이트
    dateLabels.forEach(({ id, value }) => {
        const element = document.getElementById(id);
        if (element && value) {
            element.textContent = value;
            console.log(`✅ 날짜 라벨 업데이트: ${id} = ${value}`);
        }
    });
    
    // ✅ 드롭다운 옵션들 업데이트
    updateSortMethodLabels();
    updateTimeFilterLabels();
    
    // ✅ Footer 업데이트
    updateFooterLabels();
    
    // ✅ 공지사항 버튼 업데이트
    const announcementBtnText = document.getElementById('announcementBtnText');
    if (announcementBtnText) {
        announcementBtnText.textContent = lang.announcementBtnText || 'Announcements';
    }
    
    // ✅ 현재 사이트의 보드 placeholder 업데이트
    if (currentSite) {
        updateBoardPlaceholder(currentSite);
    }
}


// Footer 요소들을 번역하는 함수
function updateFooterLabels() {
    const lang = window.languages?.[currentLanguage] || window.languages?.en || {};
    
    console.log(`🔄 Footer 언어 업데이트: ${currentLanguage}`);
    
    // Footer 링크들 업데이트
    const footerElements = [
        { id: 'privacyLink', key: 'privacy' },
        { id: 'termsLink', key: 'terms' },
        { id: 'bugReportLink', key: 'feedback' },
        { id: 'businessLink', key: 'business' }
    ];
    
    footerElements.forEach(({ id, key }) => {
        const element = document.getElementById(id);
        if (element && lang[key]) {
            element.textContent = lang[key];
            console.log(`✅ Footer 업데이트: ${id} = ${lang[key]}`);
        }
    });
    
    // 언어 선택 버튼의 현재 언어 표시도 업데이트
    const currentLangElement = document.getElementById('currentLang');
    if (currentLangElement) {
        const languageNames = {
            'ko': '한국어',
            'en': 'English', 
            'ja': '日本語'
        };
        currentLangElement.textContent = languageNames[currentLanguage] || currentLanguage;
    }
}
// 모든 UI 라벨을 현재 언어에 맞게 업데이트하는 함수
function updateFooterLabels() {
    const lang = window.languages?.[currentLanguage] || window.languages?.en || {};
    
    console.log(`🔄 Footer 언어 업데이트: ${currentLanguage}`);
    
    // Footer 링크들 업데이트
    const footerElements = [
        { id: 'privacyLink', key: 'privacy' },
        { id: 'termsLink', key: 'terms' },
        { id: 'bugReportLink', key: 'feedback' },
        { id: 'businessLink', key: 'business' }
    ];
    
    footerElements.forEach(({ id, key }) => {
        const element = document.getElementById(id);
        if (element && lang[key]) {
            element.textContent = lang[key];
            console.log(`✅ Footer 업데이트: ${id} = ${lang[key]}`);
        }
    });
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
function selectLanguage(langCode, langName = null) {
    console.log(`🌐 언어 변경 요청: ${langCode}`);
    
    currentLanguage = langCode;
    
    if (!langName) {
        const languageNames = {
            'ko': '한국어',
            'en': 'English', 
            'ja': '日本語'
        };
        langName = languageNames[langCode] || langCode;
    }
    
    const currentLangElement = document.getElementById('currentLang');
    if (currentLangElement) {
        currentLangElement.textContent = langName;
    }
    
    document.querySelectorAll('.language-option').forEach(option => {
        option.classList.remove('active');
        if (option.getAttribute('onclick') && option.getAttribute('onclick').includes(langCode)) {
            option.classList.add('active');
        }
    });
    
    // ✅ 즉시 모든 라벨 업데이트 (Footer 포함)
    setTimeout(() => {
        updateLabels();
        
        // ✅ 현재 선택된 사이트가 있으면 관련 옵션들도 다시 로드
        if (currentSite) {
            loadSiteSortOptions(currentSite);
            updateBoardPlaceholder(currentSite);
        }
        
        console.log(`✅ 언어 변경 완료: ${langCode}`);
    }, 50);
    
    hideLanguageDropdown();
}

// ==================== 피드백 및 모달 관리 ====================
// 피드백 모달을 여는 함수
function openBugReportModal() {
    const modal = document.getElementById('bugReportModal');
    const textarea = document.getElementById('bugReportDescription');
    const lang = window.languages[currentLanguage];
    
    // 모달 내 모든 텍스트 번역
    document.getElementById('bugReportTitleText').textContent = lang.feedbackTitle || 'Send Feedback to PickPost';
    document.getElementById('bugReportDescLabel').textContent = lang.feedbackDescLabel || 'Please describe your feedback. (Required)';
    document.getElementById('screenshotTitle').textContent = lang.fileAttachTitle || 'Attach a photo to help PickPost better understand your feedback.';
    document.getElementById('bugReportWarningText').textContent = lang.warningTitle || 'Do not include sensitive information';
    document.getElementById('bugReportWarningDetail').textContent = lang.warningDetail || 'Do not include personal information, passwords, financial information, etc.';
    document.getElementById('bugReportCancelBtn').textContent = lang.cancel || 'Cancel';
    document.getElementById('bugReportSubmitBtn').textContent = lang.submit || 'Submit';
    
    // 플레이스홀더 및 기타 텍스트
    if (textarea) {
        textarea.placeholder = lang.feedbackPlaceholder || 'Please tell us why you are providing this feedback. Specific descriptions are very helpful for improvement.';
    }
    
    const screenshotBtn = document.getElementById('screenshotBtn');
    const screenshotBtnText = document.getElementById('screenshotBtnText');
    if (screenshotBtnText) {
        screenshotBtnText.textContent = lang.fileAttach || 'Attach Photo';
    }
    
    modal.classList.add('show');
    setTimeout(() => textarea?.focus(), 300);
    setupModalKeyboardTrap(modal);
}

// 피드백 모달을 닫는 함수
function closeBugReportModal() {
    const modal = document.getElementById('bugReportModal');
    
    const description = document.getElementById('bugReportDescription').value.trim();
    if (description.length > 0) {
        if (!confirm(getLocalizedMessage('confirmClose'))) {
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
    const terms = window.policies[currentLanguage]?.terms || window.policies.en?.terms || {};
    const lang = window.languages[currentLanguage] || window.languages.en;
    
    document.getElementById('termsModalTitle').textContent = terms.title || 'Terms of Service';
    document.getElementById('termsModalContent').innerHTML = terms.content || '<p>Terms of service content not available.</p>';
    
    // ✅ 확인 버튼 번역 추가
    const closeBtn = document.getElementById('closeTermsBtn');
    if (closeBtn) {
        closeBtn.textContent = lang.ok || 'OK';
    }
    
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
    const policy = window.policies[currentLanguage]?.privacy || window.policies.en?.privacy || {};
    const lang = window.languages[currentLanguage] || window.languages.en;
    
    document.getElementById('privacyModalTitle').textContent = policy.title || 'Privacy Policy';
    document.getElementById('privacyModalContent').innerHTML = policy.content || '<p>Privacy policy content not available.</p>';
    
    // ✅ 확인 버튼 번역 추가
    const closeBtn = document.getElementById('closePrivacyBtn');
    if (closeBtn) {
        closeBtn.textContent = lang.ok || 'OK';
    }
    
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
    const policy = window.policies[currentLanguage]?.business || window.policies.en?.business || {};
    const lang = window.languages[currentLanguage] || window.languages.en;
    
    document.getElementById('businessModalTitle').textContent = policy.title || '💼 Business Information';
    document.getElementById('businessModalContent').innerHTML = policy.content || '<p>Business information not available.</p>';
    
    // ✅ 확인 버튼 번역 추가
    const closeBtn = document.getElementById('closeBusinessBtn');
    if (closeBtn) {
        closeBtn.textContent = lang.ok || 'OK';
    }
    
    modal.classList.add('show');
    setupModalKeyboardTrap(modal);
}
// 비즈니스 모달을 닫는 함수
function closeBusinessModal() {
    document.getElementById('businessModal').classList.remove('show');
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
        showMessage('feedback_required', 'error');
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
        showMessage(lang.messages.feedback.success || '피드백이 전송되었습니다. 감사합니다!', 'success');
        
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
            const lang = window.languages[currentLanguage];
            showMessage('file_too_large', 'error', { translate: true });
            
            event.target.value = '';
            return;
        }

        if (!file.type.startsWith('image/')) {
            showMessage('invalid_file_type', 'error');
            
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

    function showSiteHelp(site) {
        if (site === 'lemmy') {
            showLemmyHelp();
        } else if (site === 'auto_crawl') {
            showauto_crawlHelp();
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
            // ✅ 수정: originalBoardValue 대신 빈 문자열
            this.value = '';
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
   console.log('📄 DOM 로딩 완료');
   
   // 🔥 기본 언어 설정 개선
   currentLanguage = 'en';

   const currentLangElement = document.getElementById('currentLang');
   if (currentLangElement) {
       currentLangElement.textContent = 'English';
   }
   
   document.querySelectorAll('.language-option').forEach(option => {
       option.classList.remove('active');
   });
   
   const enOption = document.querySelector('[onclick*="en"]');
   if (enOption) {
       enOption.classList.add('active');
   }
   
   // 🔥 언어팩 확인 후 모든 UI 업데이트
   if (window.languages && window.languages.en) {
       updateLabels(); // 이제 모든 번역이 포함됨
   } else {
       console.warn('언어팩이 로드되지 않았습니다');
       setTimeout(() => {
           if (window.languages && window.languages.en) {
               updateLabels();
           }
       }, 100);
   }
   
   // 나머지 초기화...
   initializeLemmyVariables();
   initializeDefaultShortcuts();
   setupEventListeners();
   initializeDateInputs();
   loadShortcuts(); // 번역이 적용된 바로가기 로드

   const logoImage = document.querySelector('.logo-image');
   if (logoImage) {
       logoImage.addEventListener('click', function() {
           location.reload();
       });
   }
   
   console.log('PickPost 시작, API 설정:', { API_BASE_URL, WS_BASE_URL });
   
   if (window.initializeFeedbackSystem) {
       window.initializeFeedbackSystem();
   }
   
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
    const lang = window.languages[currentLanguage] || window.languages.en;

    const siteColors = {
        reddit: '#ff4500',
        dcinside: '#00a8ff', 
        blind: '#00d2d3',
        bbc: '#bb1919',
        lemmy: '#00af54',
        auto_crawl: '#28a745'
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
            ➕ ${lang.addShortcut || 'Add'}
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

    const lang = window.languages[currentLanguage] || window.languages.en;

    // 🔥 모달 제목 번역
    const header = modal.querySelector('.shortcut-modal-header');
    if (header) {
        header.textContent = lang.shortcutModalTitle || 'Add Site';
    }
    
    // 🔥 입력 필드 플레이스홀더 번역
    const nameInput = document.getElementById('shortcutNameInput');
    const urlInput = document.getElementById('shortcutUrlInput');
    
    if (nameInput) {
        nameInput.placeholder = lang.shortcutName || 'Shortcut Name';
    }
    if (urlInput) {
        urlInput.placeholder = lang.shortcutUrl || 'Site URL';
    }
    
    // 🔥 버튼 텍스트 번역
    const buttons = modal.querySelectorAll('.shortcut-modal-buttons .btn');
    if (buttons.length >= 2) {
        buttons[0].textContent = lang.cancel || 'Cancel';
        buttons[1].textContent = lang.save || 'Save';
    }

    modal.classList.add('show');
    setTimeout(() => nameInput?.focus(), 100);
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
    const lang = window.languages[currentLanguage] || window.languages.en;
    
    if (!name || !url) {
        showMessage(lang.fillAllFields || 'Please fill in both name and URL.', 'error');
        return;
    }
    
    if (shortcuts.length >= 5) {
        showMessage(lang.maxShortcuts || 'You can add up to 5 shortcuts.', 'error');
        return;
    }
    
    const shortcut = { name, url, site: 'auto_crawl' };
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
        auto_crawl: 'auto_crawl'
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

function safeSetText(elementId, text) {
    try {
        const element = safeGetElement(elementId);
        if (element && text !== undefined && text !== null) {
            element.textContent = String(text);
            return true;
        }
        return false;
    } catch (error) {
        console.warn(`텍스트 설정 실패 (${elementId}):`, error);
        return false;
    }
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
    { name: 'Auto Crawler', site: 'auto_crawl', icon: '#28a745', desc: 'All websites (Direct URL input)' }
    
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
            (keywordLower.includes('범용') && item.site === 'auto_crawl') ||
            extractedURL;
    });

    if (extractedURL) {
        const auto_crawlIndex = suggestions.findIndex(s => s.site === 'auto_crawl');
        if (auto_crawlIndex > -1) {
            const auto_crawl = suggestions.splice(auto_crawlIndex, 1)[0];
            auto_crawl.desc = `URL 감지됨: ${extractedURL}`;
            suggestions.unshift(auto_crawl);
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
        
        let descHighlighted = item.desc;
        
        if (extractedURL && item.site === 'auto_crawl') {
            const urlDetectedText = getLocalizedMessage('urlDetected');
            descHighlighted = `${urlDetectedText}: ${extractedURL}`;
        } else {
            descHighlighted = item.desc.replace(
                new RegExp(`(${keyword})`, 'gi'),
                '<mark style="background: #ffeb3b;">$1</mark>'
            );
        }
        
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
        
        if (selectedSite.site === 'auto_crawl' && extractedURL) {
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
        selectSite('auto_crawl', extractedURL);
        
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
            selectSite('auto_crawl');
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
    // ✅ 안전한 초기화
    autocompleteData = [];
    highlightIndex = -1;
    
    const container = document.getElementById('autocomplete');
    if (container) {
        container.innerHTML = '';
    }
    
    const boardInput = document.getElementById('boardInput');
    if (boardInput) {
        boardInput.value = '';
    }
    
    if (searchInitiated && currentSite === site && !extractedURL) return;
    
    // ✅ Lemmy 전용 변수들 안전하게 초기화
    currentSite = site;
    searchInitiated = true;
    
    if (site === 'lemmy') {
        // ✅ 전역 변수를 안전하게 초기화
        if (typeof window.community_name === 'undefined') {
            window.community_name = '';
        }
        if (typeof window.lemmy_instance === 'undefined') {
            window.lemmy_instance = '';
        }
    }
    
    updateBoardPlaceholder(site);
    
    document.querySelectorAll('.site-btn').forEach(btn => {
        if (btn && btn.classList) {
            btn.classList.remove('active');
            if (btn.dataset?.site === site) {
                btn.classList.add('active');
            }
        }
    });

    loadSiteSortOptions(site, extractedURL);
    animateToSearchMode();
    
    setTimeout(() => {
        showBoardSearch();
        showOptions(site);
        
        if (extractedURL && site === 'auto_crawl' && boardInput) {
            boardInput.value = extractedURL;
            const clearBtn = document.getElementById('clearBoardBtn');
            if (clearBtn) {
                clearBtn.style.display = 'flex';
            }
            updateCrawlButton();
        }
    }, 300);
}

function initializeLemmyVariables() {
    if (typeof window.community_name === 'undefined') {
        window.community_name = '';
    }
    if (typeof window.lemmy_instance === 'undefined') {
        window.lemmy_instance = '';
    }
}

// 사이트 버튼 상태 업데이트 (분리된 함수)
function updateSiteButtonStates(selectedSite) {
    try {
        document.querySelectorAll('.site-btn').forEach(btn => {
            if (btn && btn.classList) {
                btn.classList.remove('active');
                if (btn.dataset?.site === selectedSite) {
                    btn.classList.add('active');
                }
            }
        });
    } catch (error) {
        console.warn('사이트 버튼 상태 업데이트 실패:', error);
    }
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
    const lang = window.languages?.[currentLanguage] || window.languages?.en || {};
    
    if (!sortSelect) return;
    
    try {
        if (site === 'reddit') {
            sortSelect.innerHTML = `
                <option value="new">${lang.sortOptions?.reddit?.new || 'New'}</option>
                <option value="top">${lang.sortOptions?.reddit?.top || 'Top'}</option>
                <option value="hot">${lang.sortOptions?.reddit?.hot || 'Hot'}</option>
                <option value="best">${lang.sortOptions?.reddit?.best || 'Best'}</option>
                <option value="rising">${lang.sortOptions?.reddit?.rising || 'Rising'}</option>
            `;
        } else {
            // ✅ 안전한 접근으로 수정
            sortSelect.innerHTML = `
                <option value="popular">${lang.sortOptions?.other?.popular || 'Popular'}</option>
                <option value="recommend">${lang.sortOptions?.other?.recommend || 'Recommend'}</option>
                <option value="recent">${lang.sortOptions?.other?.recent || 'Recent'}</option>
                <option value="comments">${lang.sortOptions?.other?.comments || 'Comments'}</option>
            `;
        }
        sortSelect.dispatchEvent(new Event('change'));
    } catch (error) {
        console.error('정렬 옵션 로드 오류:', error);
    }
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
    if (currentSite === 'auto_crawl') {
        if (keyword.startsWith('http://') || keyword.startsWith('https://')) {
            hideAutocomplete();
            updateCrawlButton();
        } else {
            showauto_crawlHelp();
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
    
    if (!container || !boardSearchContainer) return;
    
    boardSearchContainer.classList.add('dropdown-active');
    
    // 기존 키 활용
    const title = getLocalizedMessage('lemmyHelpTitle');
    const description = getLocalizedMessage('lemmyHelpDescription');
    
    container.innerHTML = `
        <div class="autocomplete-item" style="cursor: default; background: #f8f9fa;">
            <div style="flex: 1;">
                <div style="font-weight: 500; color: #1a73e8;">${title}</div>
                <div style="font-size: 12px; color: #70757a; margin-top: 4px;">
                    ${description.replace(/\n/g, '<br>')}
                </div>
            </div>
        </div>
        <div class="autocomplete-item" onclick="setLemmyCommunity('technology@lemmy.world');">
            <div style="flex: 1;">
                <div style="color: #1a73e8;">🔧 technology@lemmy.world</div>
                <div style="font-size: 11px; color: #70757a;">${getLocalizedMessage('helpTexts.lemmyHelp.examples.technology')}</div>
            </div>
        </div>
        <div class="autocomplete-item" onclick="setLemmyCommunity('asklemmy@lemmy.ml');">
            <div style="flex: 1;">
                <div style="color: #1a73e8;">❓ asklemmy@lemmy.ml</div>
                <div style="font-size: 11px; color: #70757a;">${getLocalizedMessage('helpTexts.lemmyHelp.examples.asklemmy')}</div>
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
    const boardValue = document.getElementById('boardInput')?.value?.trim() || '';
    const crawlBtn = document.getElementById('crawlBtn');
    const lang = window.languages?.[currentLanguage] || window.languages?.en || {};
    
    if (!crawlBtn) return;
    
    let isValid = false;
    let buttonText = lang.start || 'Start Crawling';
    
    if (!currentSite) {
        buttonText = lang.crawlButtonMessages?.siteNotSelected || 'Select a site';
        isValid = false;
    } else if (!boardValue) {
        // 🔥 사이트별 메시지도 번역
        if (currentSite === 'auto_crawl') {
            buttonText = lang.crawlButtonMessages?.auto_crawlEmpty || 'Enter website URL';
        } else if (currentSite === 'lemmy') {
            buttonText = lang.crawlButtonMessages?.lemmyEmpty || 'Enter Lemmy community';
        } else {
            buttonText = lang.crawlButtonMessages?.boardEmpty || 'Enter board name';
        }
        isValid = false;
    } else {
        const validation = validateSiteInput(currentSite, boardValue, lang);
        isValid = validation.isValid;
        if (!isValid && validation.message) {
            buttonText = validation.message;
        }
    }
    
    crawlBtn.disabled = !isValid || isLoading;
    
    // 🔥 크롤링 중일 때도 번역
    if (isLoading) {
        buttonText = lang.crawlingStatus?.processing || '크롤링 중...';
    }
    
    crawlBtn.textContent = buttonText;
}

// 범용 크롤러 도움말을 표시하는 함수
function showauto_crawlHelp() {
    const container = document.getElementById('autocomplete');
    const boardSearchContainer = document.getElementById('boardSearchContainer');
    const lang = window.languages[currentLanguage];
    
    boardSearchContainer.classList.add('dropdown-active');
    
    container.innerHTML = `
        <div class="autocomplete-item" style="cursor: default; background: #f8f9fa;">
            <div style="flex: 1;">
                <div style="font-weight: 500; color: #1a73e8;">${lang.helpTexts.auto_crawlTitle}</div>
                <div style="font-size: 12px; color: #70757a; margin-top: 4px;">
                    ${lang.helpTexts.auto_crawlDesc.replace(/\n/g, '<br>')}
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
    if (isLoading) {
        console.log('이미 크롤링이 진행 중입니다.');
        return;
    }

    const boardInput = document.getElementById('boardInput')?.value?.trim();
    if (!boardInput) {
        showMessage('crawlButtonMessages.boardEmpty', 'error', { translate: true });
        return;
    }

    try {
        isLoading = true;
        searchInitiated = true;
        crawlStartTime = Date.now();
        
        updateUIForCrawlStart();
        updateProgress(0, getLocalizedMessage('preparingCrawl'));
        
        // 기존 설정 코드...
        const config = {
            input: boardInput,
            site: currentSite || 'auto',
            sort: safeGetValue('sortMethod', 'recent'),
            start: parseInt(safeGetValue('startRank', '1')),
            end: parseInt(safeGetValue('endRank', '20')),
            min_views: parseInt(safeGetValue('minViews', '0')),
            min_likes: parseInt(safeGetValue('minRecommend', '0')),
            min_comments: parseInt(safeGetValue('minComments', '0')),
            time_filter: safeGetValue('timePeriod', 'day'),
            start_date: safeGetValue('startDate') || null,
            end_date: safeGetValue('endDate') || null,
            language: currentLanguage || 'en'
        };
        
        currentSocket = await createWebSocketWithRetry('crawl', config);
        console.log('✅ 크롤링 시작');
        
    } catch (error) {
        console.error('❌ 크롤링 실패:', error);
        showMessage('errorMessages.connection_failed', 'error', { translate: true });
        resetCrawlingState();
    }
}
// 레거시 엔드포인트 결정 함수
function determineLegacyEndpoint(site) {
    const endpointMap = {
        'reddit': 'reddit-crawl',
        'dcinside': 'dcinside-crawl',
        'blind': 'blind-crawl', 
        'bbc': 'bbc-crawl',
        'lemmy': 'lemmy-crawl',
        'auto_crawl': 'auto_crawl-crawl'
    };
    
    return endpointMap[site] || 'auto-crawl';
}


async function startUnifiedCrawling(boardInput) {
    try {
        // 1. 통합 엔드포인트 시도 (우선순위)
        console.log('🔥 통합 엔드포인트 시도...');
        const config = buildCrawlConfig(boardInput);
        currentSocket = await createWebSocketWithRetry('crawl', config);
        
        console.log('✅ 통합 엔드포인트 연결 성공');
        
    } catch (unifiedError) {
        console.warn('⚠️ 통합 엔드포인트 실패, 레거시 방식으로 폴백:', unifiedError);
        
        // 2. 레거시 자동 크롤링으로 폴백
        try {
            const config = buildLegacyCrawlConfig(boardInput);
            currentSocket = await createWebSocketWithRetry('auto-crawl', config);
            console.log('✅ 레거시 auto-crawl 연결 성공');
            
        } catch (legacyError) {
            console.error('❌ 모든 크롤링 방식 실패');
            throw new Error(`통합 크롤링과 레거시 크롤링 모두 실패: ${legacyError.message}`);
        }
    }
}

// 🔥 통합 엔드포인트용 설정 생성
function buildCrawlConfig(boardInput) {
    const selectedLangs = getSelectedLanguages();
    const sort = safeGetValue('sortMethod', 'recent');
    const timeFilter = safeGetValue('timePeriod', 'day');
    const range = getSelectedRange();
    
    // 기본 설정
    const baseConfig = {
        input: boardInput,
        site: currentSite || 'auto',
        board: boardInput,
        sort: sort,
        start: range.start,
        end: range.end,
        start_index: range.start,
        end_index: range.end,
        min_views: parseInt(safeGetValue('minViews', '0')),
        min_likes: parseInt(safeGetValue('minRecommend', '0')),
        time_filter: timeFilter,
        start_date: safeGetValue('startDate') || null,
        end_date: safeGetValue('endDate') || null,
        translate: selectedLangs.length > 0,  
        target_languages: selectedLangs,      
        skip_translation: selectedLangs.length === 0,
        language: currentLanguage || 'en'
    };
    
    // 🔥 사이트별로 지원하지 않는 매개변수 제거
    const siteSpecificConfigs = {
        'lemmy': {
            excludeParams: ['min_comments']
        },
        'reddit': {
            excludeParams: []
        },
        'dcinside': {
            excludeParams: ['min_comments']
        },
        'blind': {
            excludeParams: ['min_comments']
        },
        'bbc': {
            excludeParams: []
        },
        'auto_crawl': {
            excludeParams: []
        }
    };
    
    // min_comments는 조건부로만 추가
    const siteConfig = siteSpecificConfigs[currentSite] || { excludeParams: [] };
    
    if (!siteConfig.excludeParams.includes('min_comments')) {
        baseConfig.min_comments = parseInt(safeGetValue('minComments', '0'));
    }
    
    console.log(`🔧 번역 설정: translate=${baseConfig.translate}, target_languages=[${baseConfig.target_languages.join(', ')}]`);
    console.log(`🔧 사이트별 설정 적용 (${currentSite}):`, baseConfig);
    
    return baseConfig;
}

// 레거시 auto-crawl용 설정 생성 
function buildLegacyCrawlConfig(boardInput) {
    const config = buildCrawlConfig(boardInput);
    
    // 레거시 전용 필드 추가
    config.debug = {
        frontend_version: '2.0.0',
        endpoint_type: 'legacy_auto',
        fallback: true
    };
    
    return config;
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

// 크롤링 완료 처리 (통합)
function handleCrawlComplete(data, endpoint) {
    console.log(`✅ 크롤링 완료 (${endpoint}):`, data);
    
    // 결과 데이터 추출 (엔드포인트별 호환성)
    let results = data.data || data.results || [];
    let summary = data.summary || `크롤링 완료: ${results.length}개 게시물`;
    
    // 🔥 통합 엔드포인트에서 사이트 감지 정보 확인
    if (data.detected_site) {
        console.log(`🎯 자동 감지된 사이트: ${data.detected_site}`);
        summary += ` (감지된 사이트: ${data.detected_site})`;
    }
    
    // 결과 표시
    if (results.length > 0) {
        crawlResults = results;
        displayResults(results);
        
        const elapsed = crawlStartTime ? ((Date.now() - crawlStartTime) / 1000).toFixed(1) : '?';
        showMessage(`${summary} (${elapsed}초)`, 'success');
        
        // 다운로드 버튼 활성화
        enableDownloadButtons();
        
    } else {
        showMessage('크롤링이 완료되었지만 결과가 없습니다.', 'warning');
    }
    
    resetCrawlingState();
}

// 크롤링 에러 처리 (통합)
function handleCrawlError(error, endpoint) {
    console.error(`❌ 크롤링 오류 (${endpoint}):`, error);
    
    let errorMessage;
    const lang = window.languages[currentLanguage];
    
    // 에러 타입별 메시지 처리
    if (error.error_code) {
        errorMessage = getLocalizedMessage(`errors.${error.error_code}`, error);
    } else if (typeof error === 'string') {
        errorMessage = `${lang?.errors?.general || '크롤링 중 오류가 발생했습니다'}: ${error}`;
    } else if (error.message) {
        errorMessage = `${lang?.errors?.general || '크롤링 중 오류가 발생했습니다'}: ${error.message}`;
    } else {
        errorMessage = lang?.errors?.unknown || '알 수 없는 오류가 발생했습니다';
    }
    
    showMessage(errorMessage, 'error');
    resetCrawlingState();
}

function handleErrorMessage(data) {
    const errorCode = data.error_code || 'unknown_error';
    const errorDetail = data.error_detail || '';
    const site = (data.site || '').toUpperCase();
    
    console.error(`❌ 오류: ${errorCode}`);
    
    const messageKey = `errors.${errorCode}`;
    const translatedMessage = getLocalizedMessage(messageKey, {
        site: site,
        detail: errorDetail
    });
    
    showMessage(translatedMessage, 'error');
    resetCrawlingState();
}

// UI 업데이트 함수들...

function updateProgressBar(progress, status) {
    const progressBar = document.querySelector('.progress-bar');
    const progressText = document.querySelector('.progress-text');
    
    if (progressBar) {
        progressBar.style.width = `${Math.min(progress, 100)}%`;
    }
    
    if (progressText) {
        progressText.textContent = `${Math.round(progress)}% - ${status}`;
    }
}

function updateStatusDisplay(status) {
    const statusElement = document.querySelector('.crawl-status');
    if (statusElement) {
        statusElement.textContent = status;
        statusElement.style.display = 'block';
    }
}

function updateUIForCrawlStart() {
    // 기존 결과 클리어
    crawlResults = [];
    const resultsContainer = document.getElementById('resultsContainer') || 
                            document.getElementById('results');
    if (resultsContainer) {
        resultsContainer.innerHTML = '';
    }
    
    // 크롤링 버튼 상태 변경
    const crawlBtn = document.getElementById('crawlBtn');
    if (crawlBtn) {
        crawlBtn.disabled = true;
        // 기존 키 재사용
        crawlBtn.textContent = getLocalizedMessage('crawlingStatus.processing');
    }
    
    // 진행률 표시 시작
    showProgress();
    
    // 취소 버튼 활성화
    showCancelButton();
    
    console.log('🚀 크롤링 UI 준비 완료');
}


function resetCrawlingState() {
    try {
        hideProgress();
        isLoading = false;
        updateCrawlButton();
        hideCancelButton();
        
        if (currentSocket) {
            try {
                currentSocket.close();
            } catch (e) {
                console.warn('WebSocket 종료 중 오류:', e);
            }
            currentSocket = null;
        }
        
        currentCrawlId = null;
        crawlStartTime = null;
        
        console.log('🧹 크롤링 상태 정리 완료');
        
    } catch (error) {
        console.error('❌ 크롤링 상태 정리 중 오류:', error);
    }
}

// 🔥 사이트별 엔드포인트 지원 (레거시 호환성)
// 필요시 기존 사이트별 함수들도 통합 엔드포인트를 우선 사용하도록 업데이트

function startRedditCrawling() {
    // 통합 엔드포인트 우선, 실패시 기존 방식
    currentSite = 'reddit';
    return startCrawling();
}

function startDCInsideCrawling() {
    currentSite = 'dcinside';
    return startCrawling();
}

function startBlindCrawling() {
    currentSite = 'blind';
    return startCrawling();
}

function startBBCCrawling() {
    currentSite = 'bbc';
    return startCrawling();
}

function startLemmyCrawling() {
    currentSite = 'lemmy';
    return startCrawling();
}

function startauto_crawlCrawling() {
    currentSite = 'auto_crawl';
    return startCrawling();
}

// 진행률 메시지 처리
function handleProgressMessage(data) {
    const progress = Math.min(Math.max(data.progress || 0, 0), 100);
    const step = data.step || 'unknown';
    const site = (data.site || '').toUpperCase();
    const board = data.board || '';
    const details = data.details || {};
    
    console.log(`📊 진행률: ${progress}% - ${step}`);
    
    // 언어팩에서 메시지 가져오기
    const messageKey = `crawlingSteps.${step}`;
    const translatedMessage = getLocalizedMessage(messageKey, {
        site: site,
        board: board,
        page: details.page || details.current_page || '',
        matched: details.matched_posts || details.matched || '',
        total: details.total_posts || details.total_checked || '',
        current: details.current_post || details.current || '',
        ...details
    });
    
    updateProgress(progress, translatedMessage);
}
// 상태 메시지 처리
function handleStatusMessage(data) {
    const step = data.step || 'unknown';
    const site = (data.site || '').toUpperCase();
    const details = data.details || {};
    
    console.log(`ℹ️ 상태: ${step}`);
    
    const messageKey = `crawlingStatus.${step}`;
    const translatedMessage = getLocalizedMessage(messageKey, {
        site: site,
        ...details
    });
    
    showMessage(translatedMessage, 'info');
}

// 완료 메시지 처리
function handleCompleteMessage(data) {
    const totalCount = data.total_count || 0;
    const site = (data.site || '').toUpperCase();
    const board = data.board || '';
    const startRank = data.start_rank || 1;
    const endRank = data.end_rank || totalCount;
    
    console.log(`✅ 완료: ${totalCount}개 게시물`);
    
    // 결과 데이터 저장 및 표시
    if (data.data && data.data.length > 0) {
        crawlResults = data.data;
        displayResults(data.data);
        enableDownloadButtons();
    }
    
    const messageKey = 'crawling.complete';
    const translatedMessage = getLocalizedMessage(messageKey, {
        site: site,
        board: board,
        count: totalCount,
        start: startRank,
        end: endRank
    });
    
    const elapsed = crawlStartTime ? 
        ((Date.now() - crawlStartTime) / 1000).toFixed(1) : '?';
    
    showMessage(`${translatedMessage} (${elapsed}초)`, 'success');
    resetCrawlingState();
}



function handleCrawlingEnd() {
    hideProgress();
    isLoading = false;
    updateCrawlButton();
    hideCancelButton();
    
    if (currentSocket) {
        currentSocket.close();
        currentSocket = null;
    }
}

function handleCrawlingSuccess(data) {
    // 결과 데이터 저장
    if (data.data && data.data.length > 0) {
        crawlResults = data.data;
        showDownloadButton();
    }
    
    handleCrawlingEnd();
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
    showMessage(lang.crawlingStatus?.cancelled || '크롤링이 취소되었습니다.', 'info');
    
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
        showMessage('no_data', 'error');
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
        
        showMessage('download_success', 'success', { filename: filename });
    }
}

// ==================== 진행 상황 및 결과 표시 ====================
// 진행 상황을 표시하는 함수
function showProgress() {
    const progressContainer = document.getElementById('progressContainer');
    if (progressContainer) {
        progressContainer.classList.add('show');
        progressContainer.style.display = 'block';
    }
    
    const progressDetails = document.getElementById('progressDetails');
    if (progressDetails) {
        progressDetails.style.display = 'flex';
    }
    
    updateProgress(0, '크롤링 준비 중...');
}

// 진행 상황을 숨기는 함수
function hideProgress() {
    const progressContainer = document.getElementById('progressContainer');
    if (progressContainer) {
        progressContainer.classList.remove('show');
        progressContainer.style.display = 'none';
    }
    
    const progressDetails = document.getElementById('progressDetails');
    if (progressDetails) {
        progressDetails.style.display = 'none';
    }
}

// 진행 상황을 업데이트하는 함수
function updateProgress(progress, message, details = {}) {
    const progressContainer = document.getElementById('progressContainer');
    if (progressContainer) {
        progressContainer.classList.add('show');
        progressContainer.style.display = 'block';
    }
    
    // 진행률 바 업데이트
    const progressBarSelectors = [
        '#progressFill',
        '.progress-fill', 
        '#progress-bar',
        '.progress-bar'
    ];
    
    let progressBar = null;
    for (const selector of progressBarSelectors) {
        progressBar = document.querySelector(selector);
        if (progressBar) break;
    }
    
    if (progressBar) {
        const validProgress = Math.max(0, Math.min(100, progress));
        progressBar.style.width = `${validProgress}%`;
    }
    
    // 진행률 텍스트 업데이트 (번역된 메시지 사용)
    const progressTextSelectors = [
        '#progressText',
        '.progress-text',
        '.progress-message'
    ];
    
    let progressText = null;
    for (const selector of progressTextSelectors) {
        progressText = document.querySelector(selector);
        if (progressText) break;
    }
    
    if (progressText) {
        // 메시지가 번역 키인지 확인하고 번역
        let displayMessage = message;
        if (typeof message === 'string' && !message.includes(' ') && window.languages) {
            const translatedMessage = getLocalizedMessage(message);
            if (translatedMessage !== message) {
                displayMessage = translatedMessage;
            }
        }
        progressText.textContent = displayMessage || `${progress}%`;
    }
    
    // ✅ 예상시간 번역 추가
    const progressEta = document.getElementById('progressEta');
    if (progressEta && crawlStartTime && progress > 10) {
        const lang = window.languages[currentLanguage] || window.languages.en;
        const elapsed = Date.now() - crawlStartTime;
        const estimated = (elapsed / progress) * (100 - progress);
        const minutes = Math.floor(estimated / 60000);
        const seconds = Math.floor((estimated % 60000) / 1000);
        
        let timeText = (lang.crawlingStatus?.timeRemaining || 'Estimated time') + ': ';
        if (minutes > 0) {
            const minutesLabel = lang.resultTexts?.minutes || 'min';
            const secondsLabel = lang.resultTexts?.seconds || 's';
            timeText += `${minutes}${minutesLabel} ${seconds}${secondsLabel}`;
        } else {
            const secondsLabel = lang.resultTexts?.seconds || 's';
            timeText += `${seconds}${secondsLabel}`;
        }
        
        progressEta.textContent = timeText;
    } else if (progressEta) {
        const lang = window.languages[currentLanguage] || window.languages.en;
        const timeRemaining = lang.crawlingStatus?.timeRemaining || 'Estimated time';
        const calculating = lang.resultTexts?.calculating || 'Calculating...';
        progressEta.textContent = `${timeRemaining}: ${calculating}`;
    }
    
    console.log(`🎯 진행률 UI 업데이트: ${progress}% - ${message}`);
}

// 크롤링 결과를 표시하는 함수

// 크롤링 결과를 표시하는 함수
function displayResults(results, startIndex = 1) {
    // 안전한 DOM 요소 접근
    const container = safeGetElement('resultsContainer');
    if (!container) {
        console.error('resultsContainer 요소를 찾을 수 없습니다.');
        // 간단한 폴백 표시
        showSimpleResults(results);
        return;
    }
    
    if (!results || results.length === 0) {
        const lang = window.languages[currentLanguage] || window.languages.en;
        container.innerHTML = `
            <div style="text-align: center; color: #5f6368; font-size: 16px; padding: 40px;">
                ${lang.results?.noResults || 'No results found'}
            </div>
        `;
        return;
    }
    
    // 언어팩 가져오기
    const lang = window.languages[currentLanguage] || window.languages.en;
    
    // 완료 메시지 표시
    setTimeout(() => {
        const message = lang.completionMessages?.success || 'Crawling complete: {count} posts';
        const translatedMessage = message.replace('{count}', results.length);
        showMessage(translatedMessage, 'success');
    }, 500);
    
    // 설정값 가져오기
    const elapsedTime = crawlStartTime ? Math.round((Date.now() - crawlStartTime) / 1000) : 0;
    const isAdvanced = safeGetElement('advancedSearch')?.checked || false;
    const start = parseInt(safeGetValue(isAdvanced ? 'startRankAdv' : 'startRank', '1'));
    const end = parseInt(safeGetValue(isAdvanced ? 'endRankAdv' : 'endRank', '20'));
    const estimatedPages = Math.ceil(end / 25);
    
    // 번역된 텍스트들
    const texts = {
        crawlingComplete: lang.results?.crawlingComplete || 'Crawling Complete',
        completedAt: lang.results?.completedAt || 'Completed',
        totalPosts: lang.results?.totalPosts || 'Total Posts',
        rankRange: lang.results?.rankRange || 'Rank Range',
        estimatedPages: lang.results?.estimatedPages || 'Est. Pages',
        sourcesite: lang.results?.sourcesite || 'Source Site',
        crawlingMode: lang.results?.crawlingMode || 'Crawling Mode',
        basic: lang.results?.basic || 'Basic',
        advanced: lang.results?.advanced || 'Advanced Search',
        duration: lang.results?.duration || 'Duration',
        viewOriginal: lang.results?.viewOriginal || 'View Original',
        seconds: lang.results?.seconds || 's',
        posts: lang.results?.posts || 'posts',
        page: lang.results?.page || 'page'
    };
    
    // HTML 생성
    const summaryHtml = `
        <div style="background: #f8f9fa; border-radius: 12px; padding: 16px; margin-bottom: 16px; box-shadow: 0 2px 8px rgba(32,33,36,.1);">
            <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 16px;">
                <div style="width: 40px; height: 40px; background: white; border-radius: 50%; display: flex; align-items: center; justify-content: center;">
                    <img src="logo.png" alt="PickPost" style="width: 24px; height: 24px;">
                </div>
                <div>
                    <h3 style="color: #ff8000; margin: 0; font-size: 16px; font-weight: 550;">
                        ${texts.crawlingComplete}
                    </h3>
                    <p style="color: #5f6368; margin: 0; font-size: 11.5px;">
                        ${new Date().toLocaleString('en-US')} ${texts.completedAt}
                    </p>
                </div>
            </div>
            
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 16px; margin-bottom: 16px;">
                <div style="text-align: center; background: white; padding: 8px; border-radius: 8px; border: 1px solid #e8eaed;">
                    <div style="font-size: 16px; font-weight: 550; color: #ff8000;">${results.length}</div>
                    <div style="font-size: 12px; color: #5f6368;">${texts.totalPosts}</div>
                </div>
                
                <div style="text-align: center; background: white; padding: 8px; border-radius: 8px; border: 1px solid #e8eaed;">
                    <div style="font-size: 16px; font-weight: 550; color: #ff8000;">${start}-${end}</div>
                    <div style="font-size: 12px; color: #5f6368;">${texts.rankRange}</div>
                </div>
                
                <div style="text-align: center; background: white; padding: 8px; border-radius: 8px; border: 1px solid #e8eaed;">
                    <div style="font-size: 16px; font-weight: 550; color: #ff8000;">~${estimatedPages}</div>
                    <div style="font-size: 12px; color: #5f6368;">${texts.estimatedPages}</div>
                </div>
                
                <div style="text-align: center; background: white; padding: 8px; border-radius: 8px; border: 1px solid #e8eaed;">
                    <div style="font-size: 16px; font-weight: 550; color: #ff8000;">${(currentSite || 'UNKNOWN').toUpperCase()}</div>
                    <div style="font-size: 12px; color: #5f6368;">${texts.sourcesite}</div>
                </div>
            </div>
            
            <div style="display: flex; justify-content: space-between; align-items: center; padding-top: 16px; border-top: 1px solid #e8eaed;">
                <div style="display: flex; align-items: center; gap: 8px;">
                    <span style="font-size: 14px; color: #5f6368;">${texts.crawlingMode}:</span>
                    <span style="font-size: 14px; font-weight: 500; color: #ff8000;">
                        ${isAdvanced ? texts.advanced : texts.basic}
                    </span>
                </div>
                <div style="display: flex; align-items: center; gap: 8px;">
                    <span style="font-size: 14px; color: #5f6368;">⏱️ ${texts.duration}:</span>
                    <span style="font-size: 14px; font-weight: 500; color: #137333;">${elapsedTime}${texts.seconds}</span>
                </div>
            </div>
        </div>
    `;
    
    // 개별 결과 HTML 생성
    const resultsHtml = results.map((item, index) => {
        const itemNumber = startIndex + index;
        
        // 안전한 필드 접근
        const title = item.원제목 || item.title || item.제목 || 'No Title';
        const translatedTitle = item.번역제목 || item.translated_title || '';
        const link = item.링크 || item.link || item.url || '#';
        const content = item.본문 || item.content || item.내용 || '';
        const views = item.조회수 || item.views || 0;
        const likes = item.추천수 || item.likes || item.score || 0;
        const comments = item.댓글수 || item.comments || 0;
        const date = item.작성일 || item.date || item.created_at || '';
        
        // 번역된 라벨들
        const viewsLabel = lang.views || 'Views';
        const likesLabel = lang.likes || 'Likes'; 
        const commentsLabel = lang.comments || 'Comments';
        
        //번역 제목이 원제목과 같거나 의미없는 경우 표시하지 않음
        const shouldShowTranslation = translatedTitle && 
                                translatedTitle !== title && 
                                translatedTitle.trim() !== '' &&
                                !translatedTitle.includes('Translation not needed');
        
        return `
            <div class="result-item" style="opacity: 0; transform: translateY(8px);">
                <div class="result-header">
                    <div style="display: flex; align-items: flex-start; flex: 1;">
                        <div class="result-number">${itemNumber}</div>
                        <div style="flex: 1;">
                            <a href="${link}" target="_blank" class="result-title" rel="noopener noreferrer">
                                ${title}
                            </a>
                            ${shouldShowTranslation ? `<div class="result-translation">${translatedTitle}</div>` : ''}
                        </div>
                    </div>
                </div>
                
                <div class="result-meta-row">
                    <div class="result-date">📅 ${date}</div>
                    <div class="result-stats">
                        ${views > 0 ? `<div class="stat-item" title="${viewsLabel}">👁️ ${views.toLocaleString()}</div>` : ''}
                        ${likes > 0 ? `<div class="stat-item" title="${likesLabel}">👍 ${likes.toLocaleString()}</div>` : ''}
                        ${comments > 0 ? `<div class="stat-item" title="${commentsLabel}">💬 ${comments.toLocaleString()}</div>` : ''}
                    </div>
                </div>
                
                ${content ? `<div class="result-content">${content.length > 200 ? content.substring(0, 200) + '...' : content}</div>` : ''}
                
                <div class="result-links">
                    <a href="${link}" target="_blank" rel="noopener noreferrer">
                        ${texts.viewOriginal} →
                    </a>
                </div>
            </div>
        `;
    }).join('');
    
    // 컨테이너에 HTML 삽입
    try {
        container.innerHTML = summaryHtml + resultsHtml;
        
        // 결과 아이템들 순차적 애니메이션
        const resultItems = container.querySelectorAll('.result-item');
        resultItems.forEach((item, index) => {
            setTimeout(() => {
                item.style.opacity = '1';
                item.style.transform = 'translateY(0)';
            }, index * 100);
        });
        
        // UI 상태 업데이트
        setTimeout(() => {
            enableDownloadButtons();
            
            const cancelBtn = safeGetElement('cancelBtn');
            if (cancelBtn) {
                cancelBtn.style.display = 'none';
            }
            
            const crawlBtn = safeGetElement('crawlBtn');
            if (crawlBtn) {
                crawlBtn.textContent = lang.start || 'Start Crawling';
                crawlBtn.disabled = false;
            }
        }, 100);
        
        console.log(`${results.length}개 결과 표시 완료`);
        
    } catch (error) {
        console.error('결과 표시 중 오류:', error);
        showSimpleResults(results);
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
function showMessage(message, type = 'info', options = {}) {
    try {
        const messageDiv = document.createElement('div');
        let displayMessage = message;
                
        //언어팩인지 확인하고 번역
        if (typeof message === 'string' && !message.includes(' ') && window.languages) {
                    const translatedMessage = getLocalizedMessage(message, options.variables);
                    if (translatedMessage !== message) {
                        displayMessage = translatedMessage;
                    }
                }

        // 언어 키인 경우 번역
        if (options.translate && window.languages) {
            const lang = window.languages[currentLanguage] || window.languages.en;
            if (lang.notifications && lang.notifications[message]) {
                displayMessage = lang.notifications[message];
                
                // 변수 치환
                if (options.variables) {
                    Object.keys(options.variables).forEach(key => {
                        displayMessage = displayMessage.replace(`{${key}}`, options.variables[key]);
                    });
                }
            }
        }
        
        messageDiv.className = `temporary-message ${type}`;
        messageDiv.textContent = displayMessage;
        
        // 🔥 스타일 추가 (마이그레이션 전 디자인 유지)
        messageDiv.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 12px 20px;
            border-radius: 8px;
            color: white;
            font-weight: 500;
            font-size: 14px;
            z-index: 10000;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            transform: translateX(400px);
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        `;
        
        // 타입별 색상 설정
        const colors = {
            success: '#137333',
            error: '#d93025', 
            warning: '#f57c00',
            info: '#1a73e8'
        };
        messageDiv.style.backgroundColor = colors[type] || colors.info;
        
        document.body.appendChild(messageDiv);
        
        setTimeout(() => {
            messageDiv.style.transform = 'translateX(0)';
        }, 100);
        
        setTimeout(() => {
            messageDiv.style.transform = 'translateX(400px)';
            setTimeout(() => {
                if (document.body.contains(messageDiv)) {
                    document.body.removeChild(messageDiv);
                }
            }, 300);
        }, options.duration || 3000);
        
    } catch (error) {
        console.error('메시지 표시 중 오류:', error);
        alert(message); // 폴백
    }
}

// ✅ 메시지 표시 함수들을 하나로 통합
function showMessage(message, type = 'info', options = {}) {
    try {
        const messageDiv = document.createElement('div');
        let displayMessage = message;
        
        // 언어 키인 경우 번역
        if (options.translate && window.languages) {
            const lang = window.languages[currentLanguage] || window.languages.en;
            if (lang.notifications && lang.notifications[message]) {
                displayMessage = lang.notifications[message];
                
                // 변수 치환
                if (options.variables) {
                    Object.keys(options.variables).forEach(key => {
                        displayMessage = displayMessage.replace(`{${key}}`, options.variables[key]);
                    });
                }
            }
        }
        
        messageDiv.className = `temporary-message ${type}`;
        messageDiv.textContent = displayMessage;
        
        // 🔥 스타일 추가 (마이그레이션 전 디자인 유지)
        messageDiv.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 12px 20px;
            border-radius: 8px;
            color: white;
            font-weight: 500;
            font-size: 14px;
            z-index: 10000;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            transform: translateX(400px);
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        `;
        
        // 타입별 색상 설정
        const colors = {
            success: '#137333',
            error: '#d93025', 
            warning: '#f57c00',
            info: '#1a73e8'
        };
        messageDiv.style.backgroundColor = colors[type] || colors.info;
        
        document.body.appendChild(messageDiv);
        
        setTimeout(() => {
            messageDiv.style.transform = 'translateX(0)';
        }, 100);
        
        setTimeout(() => {
            messageDiv.style.transform = 'translateX(400px)';
            setTimeout(() => {
                if (document.body.contains(messageDiv)) {
                    document.body.removeChild(messageDiv);
                }
            }, 300);
        }, options.duration || 3000);
        
    } catch (error) {
        console.error('메시지 표시 중 오류:', error);
        alert(message); // 폴백
    }
}


// ✅ 하나의 통합된 WebSocket 메시지 핸들러만 유지
function setupWebSocketMessageHandlers(ws, endpoint) {
    ws.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            console.log(`📨 메시지 수신:`, data);

            if (data.cancelled) {
                showMessage('crawlingStatus.cancelled', 'info', { translate: true });
                resetCrawlingState();
                return;
            }

            if (data.error) {
                showMessage('errorMessages.general', 'error', { translate: true });
                resetCrawlingState();
                return;
            }

            if (data.done) {
                const results = data.data || [];
                if (results.length > 0) {
                    crawlResults = results;
                    displayResults(results);
                    enableDownloadButtons();
                    
                    const message = getLocalizedMessage('completionMessages.success').replace('{count}', results.length);
                    showMessage(message, 'success');
                } else {
                    showMessage('completedNoResults', 'warning', { translate: true });
                }
                resetCrawlingState();
                return;
            }

            if (data.progress !== undefined) {
                const progress = Math.max(0, Math.min(100, data.progress));
                
                let statusKey = 'crawlingStatus.processing';
                if (data.status) {
                    const statusMap = {
                        'connecting': 'crawlingStatus.connecting',
                        'analyzing': 'crawlingStatus.analyzing', 
                        'collecting': 'crawlingStatus.collecting',
                        'processing': 'crawlingStatus.processing'
                    };
                    statusKey = statusMap[data.status.toLowerCase()] || statusKey;
                }
                
                updateProgress(progress, getLocalizedMessage(statusKey));
                return;
            }

        } catch (error) {
            console.error('메시지 파싱 오류:', error);
            showMessage('errorMessages.general', 'error', { translate: true });
        }
    };

    ws.onerror = (error) => {
        console.error(`❌ WebSocket 오류:`, error);
        showMessage('errorMessages.network_error', 'error', { translate: true });
        resetCrawlingState();
    };

    ws.onclose = (event) => {
        console.log(`🔌 WebSocket 연결 종료:`, event.code);
        if (isLoading && event.code !== 1000) {
            showMessage('connectionDropped', 'error', { translate: true });
            resetCrawlingState();
        }
    };
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

// DOM 요소 존재 확인 후 이벤트 리스너 추가
function safeAddEventListener(elementId, event, handler) {
    try {
        const element = document.getElementById(elementId);
        if (element) {
            element.addEventListener(event, handler);
            return true;
        } else {
            console.warn(`요소를 찾을 수 없음: ${elementId}`);
        }
    } catch (error) {
        console.error(`이벤트 리스너 추가 실패 (${elementId}):`, error);
    }
    return false;
}


// 보드 입력 키 이벤트 핸들러
function handleBoardInputKeyup(e) {
    // 이미 있는 keydown 이벤트와 별도로 keyup에서 추가 처리
    if (e.key === 'Enter' && !e.isComposing) {
        // 한글 입력 완료 후 엔터 처리
        const value = e.target.value.trim();
        if (value && currentSite) {
            updateCrawlButton();
        }
    }
}

// 초기화 함수에서 DOM 요소 존재 확인
function initializeApp() {
    console.log('🚀 앱 초기화 시작');
    
    try {
        // 1. 전역 변수 초기화
        initializeGlobalVariables();
        
        // 2. 필수 DOM 요소들 존재 확인
        const requiredElements = [
            'boardInput', 'crawlBtn', 'siteInput', 
            'minViews', 'minRecommend', 'minComments',
            'sortMethod', 'timePeriod'
        ];
        
        const missingElements = requiredElements.filter(id => !safeGetElement(id));
        
        if (missingElements.length > 0) {
            console.error('❌ 필수 DOM 요소들이 누락됨:', missingElements);
            showMessage('페이지 로딩이 완전하지 않습니다. 페이지를 새로고침해주세요.', 'error');
            return false;
        }
        
        // 3. 이벤트 리스너들 안전하게 추가
        setupSafeEventListeners();
        
        // 4. 언어 설정 (기본값: 영어)
        selectLanguage('en', 'English');
        
        console.log('✅ 앱 초기화 완료');
        return true;
        
    } catch (error) {
        console.error('❌ 앱 초기화 중 오류:', error);
        showMessage('앱 초기화 중 오류가 발생했습니다. 페이지를 새로고침해주세요.', 'error');
        return false;
    }
}

function setupSafeEventListeners() {
    // 기존 이벤트 리스너들을 안전하게 추가
    safeAddEventListener('boardInput', 'input', updateCrawlButton);
    safeAddEventListener('boardInput', 'keyup', handleBoardInputKeyup);
    
    // 입력 요소들에 대한 이벤트 리스너
    const inputElements = [
        'minViews', 'minRecommend', 'startRank', 'endRank', 
        'startRankAdv', 'endRankAdv', 'minComments',
        'sortMethod', 'startDate', 'endDate'
    ];
    
    inputElements.forEach(elementId => {
        safeAddEventListener(elementId, 'input', updateCrawlButton);
        safeAddEventListener(elementId, 'change', updateCrawlButton);
    });
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
function validateSiteInput(site, boardValue, lang) {
    switch (site) {
        case 'auto_crawl':
            const isValidUrl = boardValue.startsWith('http://') || 
                             boardValue.startsWith('https://') ||
                             (boardValue.includes('.') && boardValue.includes('/'));
            
            return {
                isValid: isValidUrl,
                message: isValidUrl ? '' : getLocalizedMessage('crawlButtonMessages.auto_crawlUrlError')
            };
            
        case 'lemmy':
            if (boardValue.includes('@') && boardValue.split('@').length === 2) {
                const [community, instance] = boardValue.split('@');
                return {
                    isValid: community.length > 0 && instance.length > 0,
                    message: ''
                };
            } else if (boardValue.startsWith('https://') && boardValue.includes('/c/')) {
                return { isValid: true, message: '' };
            } else if (boardValue.length > 2) {
                const suggestion = getLocalizedMessage('formatSuggestion');
                return {
                    isValid: true,
                    message: `${suggestion}: ${boardValue}@lemmy.world`
                };
            } else {
                return {
                    isValid: false,
                    message: getLocalizedMessage('crawlButtonMessages.lemmyFormatError')
                };
            }
            
        case 'reddit':
            const hasRedditError = boardValue.includes('reddit.com') && !boardValue.includes('/r/');
            return {
                isValid: !hasRedditError,
                message: hasRedditError ? getLocalizedMessage('crawlButtonMessages.redditFormatError') : ''
            };
            
        default:
            return {
                isValid: boardValue.length > 0,
                message: ''
            };
    }
}

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

function enableDownloadButtons() {
    const downloadBtn = document.getElementById('downloadBtn');
    if (downloadBtn) {
        downloadBtn.style.display = 'inline-flex';
        downloadBtn.disabled = false;
    }
}

function showProgressBar(show) {
    const progressContainer = document.querySelector('.progress-container');
    if (progressContainer) {
        progressContainer.style.display = show ? 'block' : 'none';
    }
}

// 게시물 언어를 감지하는 함수
function detectContentLanguage() {
    console.log(`🔍 detectContentLanguage 호출됨, currentSite: ${currentSite}`);
    
    // 사이트별 기본 언어 매핑 (더 정확하게)
    const siteLanguageMap = {
        'reddit': 'en',
        'lemmy': 'en', 
        'bbc': 'en',
        'dcinside': 'ko',
        'blind': 'ko'
    };
    
    // auto_crawl 크롤러의 경우 URL에서 언어 추정 (더 정교하게)
    if (currentSite === 'auto_crawl') {
        const boardInput = document.getElementById('boardInput')?.value || '';
        
        // 한국어 사이트 패턴
        if (boardInput.includes('.kr') || 
            boardInput.includes('korean') || 
            boardInput.includes('한국') ||
            boardInput.includes('naver.com') ||
            boardInput.includes('daum.net')) {
            return 'ko';
        }
        
        // 일본어 사이트 패턴  
        if (boardInput.includes('.jp') || 
            boardInput.includes('japanese') || 
            boardInput.includes('日本')) {
            return 'ja';
        }
        
        return 'en'; // 기본값
    }
    
    const result = siteLanguageMap[currentSite] || 'en';
    console.log(`🎯 ${currentSite} → ${result}`);
    return result;
}
// 선택된 언어 가져오기
function getSelectedLanguages() {
    console.log('🔍 getSelectedLanguages 호출됨');
    
    // 언어 선택 체크박스가 있는지 확인 (수동 선택)
    const languageCheckboxes = document.querySelectorAll('input[name="target_languages"]:checked');
    if (languageCheckboxes.length > 0) {
        return Array.from(languageCheckboxes).map(cb => cb.value);
    }
    
    // 게시물 언어 감지
    const detectedLanguage = detectContentLanguage();
    console.log(`🎯 감지된 언어: ${detectedLanguage}, 현재 UI 언어: ${currentLanguage}`);
    
    // ✅ 핵심: 언어가 같으면 빈 배열 반환 (번역 안함)
    if (detectedLanguage === currentLanguage) {
        console.log(`🚫 번역 안함: 언어가 동일함 (${detectedLanguage} === ${currentLanguage})`);
        return []; 
    }
    
    console.log(`✅ 번역 진행: ${detectedLanguage} → ${currentLanguage}`);
    return [currentLanguage];
}

// 게시물 언어를 감지하는 함수 (getSelectedLanguages 함수 위에 추가)
function detectContentLanguage() {
    // 사이트별 기본 언어 매핑
    const siteLanguageMap = {
        'reddit': 'en',
        'lemmy': 'en', 
        'bbc': 'en',
        'dcinside': 'ko',
        'blind': 'ko'
    };
    
    // auto_crawl 크롤러의 경우 URL에서 언어 추정
    if (currentSite === 'auto_crawl') {
        const boardInput = document.getElementById('boardInput')?.value || '';
        if (boardInput.includes('.kr') || boardInput.includes('korean') || boardInput.includes('한국')) {
            return 'ko';
        }
        if (boardInput.includes('.jp') || boardInput.includes('japanese') || boardInput.includes('日본')) {
            return 'ja';
        }
        return 'en'; // 기본값
    }
    
    return siteLanguageMap[currentSite] || 'en';
}

// 선택된 범위 가져오기
function getSelectedRange() {
    const isAdvanced = document.getElementById('advancedSearch')?.checked;
    return {
        start: parseInt(document.getElementById(isAdvanced ? 'startRankAdv' : 'startRank')?.value || '1'),
        end: parseInt(document.getElementById(isAdvanced ? 'endRankAdv' : 'endRank')?.value || '20')
    };
}

console.log('✅ 통합 엔드포인트 지원 main.js 로드 완료');

// ✅ 안전한 전역 변수 초기화
function initializeGlobalVariables() {
    // Lemmy 전용 변수들 안전하게 초기화
    if (typeof window.community_name === 'undefined') {
        window.community_name = '';
    }
    if (typeof window.lemmy_instance === 'undefined') {
        window.lemmy_instance = '';
    }
    
    // 기타 필요한 전역 변수들
    if (typeof window.languages === 'undefined') {
        console.error('언어팩이 로드되지 않았습니다');
        window.languages = { en: { start: 'Start Crawling' } }; // 폴백
    }
}

// 언어팩 접근 함수 
function getSafeLanguagePack() {
    try {
        return window.languages?.[currentLanguage] || 
               window.languages?.en || 
               window.languages?.ko || 
               { start: 'Start Crawling' }; // 최종 폴백
    } catch (error) {
        console.warn('언어팩 접근 오류:', error);
        return { start: 'Start Crawling' };
    }
}
// 사이트별 빈 입력 메시지 가져오기
function getSiteSpecificEmptyMessage(site, lang) {
    const messages = {
        'auto_crawl': lang.crawlButtonMessages?.auto_crawlEmpty || 'Enter website URL',
        'lemmy': lang.crawlButtonMessages?.lemmyEmpty || 'Enter Lemmy community',
        'default': lang.crawlButtonMessages?.boardEmpty || 'Enter board name'
    };
    
    return messages[site] || messages.default;
}

// 사이트별 입력 유효성 검사
function validateSiteInput(site, boardValue, lang) {
    switch (site) {
        case 'auto_crawl':
            const isValidUrl = boardValue.startsWith('http://') || 
                             boardValue.startsWith('https://') ||
                             (boardValue.includes('.') && boardValue.includes('/'));
            
            return {
                isValid: isValidUrl,
                message: isValidUrl ? '' : getLocalizedMessage('crawlButtonMessages.auto_crawlUrlError')
            };
            
        case 'lemmy':
            if (boardValue.includes('@') && boardValue.split('@').length === 2) {
                const [community, instance] = boardValue.split('@');
                return {
                    isValid: community.length > 0 && instance.length > 0,
                    message: ''
                };
            } else if (boardValue.startsWith('https://') && boardValue.includes('/c/')) {
                return { isValid: true, message: '' };
            } else if (boardValue.length > 2) {
                // 신규 키 사용하여 제안 제공
                const suggestion = getLocalizedMessage('formatSuggestion');
                return {
                    isValid: true,
                    message: `${suggestion}: ${boardValue}@lemmy.world`
                };
            } else {
                return {
                    isValid: false,
                    message: getLocalizedMessage('crawlButtonMessages.lemmyFormatError')
                };
            }
            
        case 'reddit':
            const hasRedditError = boardValue.includes('reddit.com') && !boardValue.includes('/r/');
            return {
                isValid: !hasRedditError,
                message: hasRedditError ? getLocalizedMessage('crawlButtonMessages.redditFormatError') : ''
            };
            
        default:
            return {
                isValid: boardValue.length > 0,
                message: ''
            };
    }
}

// ============================================================================
//  안전한 DOM 요소 접근을 위한 헬퍼 함수
// ============================================================================


// 안전한 값 가져오기 함수
function safeGetElement(elementId) {
    try {
        const element = document.getElementById(elementId);
        if (!element) {
            console.warn(`❌ 요소를 찾을 수 없음: ${elementId}`);
            return null;
        }
        return element;
    } catch (error) {
        console.error(`❌ 요소 접근 오류 (${elementId}):`, error);
        return null;
    }
}

// 안전한 값 가져오기 (수정된 버전)
function safeGetValue(elementId, defaultValue = '') {
    const element = safeGetElement(elementId);
    return element?.value?.trim() || defaultValue;
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
window.debugProgress = (progress, message) => updateProgress(progress, message);

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
window.validateSiteInput = validateSiteInput;
window.showSiteSuggestions = showSiteSuggestions;
window.showLemmyHelpContent = showLemmyHelpContent;
window.updateTimeFilterLabels = updateTimeFilterLabels;
window.updateSortMethodLabels = updateSortMethodLabels;
window.updateFooterLabels = updateFooterLabels;

// 자동완성 관련
window.selectBBCSection = selectBBCSection;
window.setLemmyCommunity = setLemmyCommunity;
window.selectAutocompleteItem = selectAutocompleteItem;
window.selectSiteAutocompleteItem = selectSiteAutocompleteItem;

//  selectSite 함수 전역 노출
window.selectSite = selectSite;
window.removeShortcut = removeShortcut;
window.displayResults = displayResults;
window.enableDownloadButtons = enableDownloadButtons;
window.showMessage = showMessage;

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
    showMessage,
    extractSiteName,
    updateLabels
};
