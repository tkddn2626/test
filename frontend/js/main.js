
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
    console.error('🚨 전역 JavaScript 오류:', {
        message: e.message,
        filename: e.filename,
        lineno: e.lineno,
        timestamp: new Date().toISOString()
    });
    
    // 간단한 복구 로직만 유지
    if (e.message.includes('community_name')) {
        window.community_name = '';
        window.lemmy_instance = '';
        showMessage('Input validation error fixed. Please try again.', 'info');
    } else if (e.message.includes('Cannot read properties of undefined')) {
        showMessage('페이지를 새로고침해주세요.', 'warning');
    } else {
        showMessage('일시적인 오류가 발생했습니다.', 'warning');
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
    const RENDER_DOMAIN = 'test-1-zm0k.onrender.com';
    
    return {
        API_BASE_URL: `https://${RENDER_DOMAIN}`,
        WS_BASE_URL: `wss://${RENDER_DOMAIN}`  // WSS 사용
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
                    
                    // 메시지 핸들러 설정
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

// 모든 UI 라벨을 현재 언어에 맞게 업데이트하는 함수
function updateLabels(lang) {
    if (!lang) {
        console.warn('언어 팩이 없습니다. 영어로 폴백합니다.');
        lang = window.languages?.en || {};
    }
    
    // ✅ safeSetText 대신 직접 안전하게 설정
    const crawlBtn = safeGetElement('crawlBtn');
    if (crawlBtn) crawlBtn.textContent = lang.start || 'Start Crawling';
    
    const cancelBtn = safeGetElement('cancelBtn');
    if (cancelBtn) cancelBtn.textContent = lang.cancel || 'Cancel';
    
    const downloadBtn = safeGetElement('downloadBtn');
    if (downloadBtn) downloadBtn.textContent = lang.download || 'Download';
    // 플레이스홀더 안전하게 설정
    function safePlaceholder(elementId, placeholder) {
        const element = document.getElementById(elementId);
        if (element && placeholder !== undefined) {
            element.placeholder = placeholder;
        }
    }
    
    safePlaceholder('siteInput', lang.sitePlaceholder || 'Search for a site...');
    
    if (currentSite) {
        updateBoardPlaceholder(currentSite);
    } else {
        safePlaceholder('boardInput', lang.boardPlaceholders?.default || 'Enter board name...');
    }
    
    safePlaceholder('shortcutNameInput', lang.shortcutNamePlaceholder || 'Site name');
    safePlaceholder('shortcutUrlInput', lang.shortcutUrlPlaceholder || 'Site URL');
    
    // 라벨들 안전하게 업데이트
    safeSetText('minViewsLabel', lang.minViews || 'Min Views');
    safeSetText('minRecommendLabel', lang.minRecommend || 'Min Likes');
    safeSetText('minCommentsLabel', lang.minComments || 'Min Comments');
    safeSetText('startRankLabel', lang.startRank || 'Start Rank');
    safeSetText('endRankLabel', lang.endRank || 'End Rank');
    safeSetText('sortMethodLabel', lang.sortMethod || 'Sort Method');
    safeSetText('timePeriodLabel', lang.timePeriod || 'Time Period');
    safeSetText('advancedSearchLabel', lang.advancedSearch || 'Advanced Search');
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
    currentLanguage = langCode;
    
    // langName이 제공되지 않은 경우 기본값 설정
    if (!langName) {
        const languageNames = {
            'ko': '한국어',
            'en': 'English', 
            'ja': '日本語'
        };
        langName = languageNames[langCode] || langCode;
    }
    
    // 안전한 DOM 요소 접근
    const currentLangElement = document.getElementById('currentLang');
    if (currentLangElement) {
        currentLangElement.textContent = langName;
    }
    
    // 언어 옵션 활성화 상태 업데이트
    document.querySelectorAll('.language-option').forEach(option => {
        option.classList.remove('active');
        // onclick 속성에서 언어 코드를 찾아서 매칭
        if (option.getAttribute('onclick') && option.getAttribute('onclick').includes(langCode)) {
            option.classList.add('active');
        }
    });
    
    updateLabels(window.languages[currentLanguage]);
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
    
    if (window.languages && window.languages.en) {
        updateLabels(window.languages.en);
    }

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
    
    // ❌ 삭제: 존재하지 않는 함수들
    // testApiConnection().then(apiConnected => {
    //     console.log('API 연결 상태:', apiConnected);
    // });
    // testWebSocketConnection().then(wsConnected => {
    //     console.log('WebSocket 연결 상태:', wsConnected);
    // });

    if (window.initializeFeedbackSystem) {
        window.initializeFeedbackSystem();
    }
    
    setTimeout(() => {
        if (!initializeApp()) {
            console.error('❌ 앱 초기화 실패');
        }
    }, 100);

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
    try {
        // ✅ 수정: 안전한 초기화
        autocompleteData = [];
        highlightIndex = -1;
        
        const container = safeGetElement('autocomplete');
        if (container) {
            container.innerHTML = '';
        }
        
        const boardInput = safeGetElement('boardInput');
        if (boardInput) {
            boardInput.value = '';
        }
        
        // 중복 실행 방지
        if (searchInitiated && currentSite === site && !extractedURL) {
            return;
        }
        
        // ✅ 수정: 사이트별 전역 변수 안전하게 초기화
        currentSite = site;
        searchInitiated = true;
        
        // Lemmy 전용 변수들 초기화 (에러 방지)
        if (site === 'lemmy') {
            window.community_name = '';
            window.lemmy_instance = '';
        }
        
        // UI 업데이트
        updateBoardPlaceholder(site);
        updateSiteButtonStates(site);
        loadSiteSortOptions(site, extractedURL);
        animateToSearchMode();
        
        // 지연된 UI 표시
        setTimeout(() => {
            showBoardSearch();
            showOptions(site);
            
            if (extractedURL && site === 'universal' && boardInput) {
                boardInput.value = extractedURL;
                const clearBtn = safeGetElement('clearBoardBtn');
                if (clearBtn) {
                    clearBtn.style.display = 'flex';
                }
                updateCrawlButton();
            }
        }, 300);
        
    } catch (error) {
        console.error('❌ selectSite 실행 중 오류:', error);
        showMessage('사이트 선택 중 오류가 발생했습니다. 페이지를 새로고침해주세요.', 'error');
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
    const sortSelect = safeGetElement('sortMethod');
    const lang = getSafeLanguagePack();
    
    if (!sortSelect) {
        console.warn('sortMethod 요소를 찾을 수 없습니다');
        return;
    }
    
    try {
        if (site === 'reddit') {
            sortSelect.innerHTML = `
                <option value="new">${lang.sortOptions?.reddit?.new || 'New'}</option>
                <option value="top">${lang.sortOptions?.reddit?.top || 'Top'}</option>
                <option value="hot">${lang.sortOptions?.reddit?.hot || 'Hot'}</option>
                <option value="best">${lang.sortOptions?.reddit?.best || 'Best'}</option>
                <option value="rising">${lang.sortOptions?.reddit?.rising || 'Rising'}</option>
            `;
            sortSelect.value = "new";
        } else if (site === 'universal' && url) {
            const detectedOptions = await detectSiteSortOptions(url);
            if (detectedOptions?.length > 0) {
                sortSelect.innerHTML = detectedOptions.map(option => 
                    `<option value="${option.value}">${option.label}</option>`
                ).join('');
                sortSelect.value = detectedOptions[0].value;
            } else {
                useDefaultSortOptions(sortSelect, lang);
            }
        } else {
            useDefaultSortOptions(sortSelect, lang);
        }
        
        sortSelect.dispatchEvent(new Event('change'));
    } catch (error) {
        console.error('정렬 옵션 로드 오류:', error);
        useDefaultSortOptions(sortSelect, lang);
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
    try {
        const boardInput = safeGetElement('boardInput');
        const crawlBtn = safeGetElement('crawlBtn');
        
        if (!boardInput || !crawlBtn) {
            console.warn('필수 DOM 요소를 찾을 수 없어 크롤링 버튼 업데이트를 건너뜁니다');
            return;
        }
        
        const boardValue = boardInput.value?.trim() || '';
        const lang = getSafeLanguagePack();
        
        let isValid = false;
        let buttonText = lang.start || 'Start Crawling';
        
        if (!currentSite) {
            buttonText = lang.crawlButtonMessages?.siteNotSelected || 'Select a site';
            isValid = false;
        } else if (!boardValue) {
            buttonText = getSiteSpecificEmptyMessage(currentSite, lang);
            isValid = false;
        } else {
            const validation = validateSiteInput(currentSite, boardValue, lang);
            isValid = validation.isValid;
            if (!isValid) {
                buttonText = validation.message;
            }
        }
        
        crawlBtn.disabled = !isValid || isLoading;
        
        if (!isLoading) {
            crawlBtn.textContent = buttonText;
        }
        
    } catch (error) {
        console.error('❌ updateCrawlButton 실행 중 오류:', error);
        
        // 폴백: 기본 상태로 설정
        const crawlBtn = safeGetElement('crawlBtn');
        if (crawlBtn && !isLoading) {
            crawlBtn.textContent = 'Start Crawling';
            crawlBtn.disabled = false;
        }
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
    if (isLoading) {
        console.log('이미 크롤링이 진행 중입니다.');
        return;
    }

    const boardInput = safeGetValue('boardInput');
    if (!boardInput) {
        showMessage('게시판 URL 또는 키워드를 입력해주세요.', 'error');
        return;
    }

    try {
        isLoading = true;
        searchInitiated = true;
        crawlStartTime = Date.now();
        
        updateUIForCrawlStart();
        
        // 🔥 단순화된 크롤링 시작
        await startUnifiedCrawling(boardInput);
        
    } catch (error) {
        console.error('크롤링 시작 오류:', error);
        showMessage(`크롤링 중 오류: ${error.message}`, 'error');
        resetCrawlingState();
    }
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
    
    return {
        // 통합 엔드포인트용
        input: boardInput,
        site: currentSite || 'auto',
        
        // 호환성을 위한 필드들
        board: boardInput,  // 레거시 호환
        
        // 크롤링 옵션
        sort: sort,
        start: range.start,
        end: range.end,
        start_index: range.start,  // 백엔드 호환
        end_index: range.end,      // 백엔드 호환
        min_views: parseInt(safeGetValue('minViews', '0')),
        min_likes: parseInt(safeGetValue('minRecommend', '0')),
        min_comments: parseInt(safeGetValue('minComments', '0')),
        time_filter: timeFilter,
        start_date: safeGetValue('startDate') || null,
        end_date: safeGetValue('endDate') || null,
        
        // 번역 옵션
        translate: selectedLangs.length > 0,
        target_languages: selectedLangs,
        
        // 언어 설정
        language: currentLanguage || 'en'
    };
}
// 레거시 auto-crawl용 설정 생성 
function buildLegacyCrawlConfig(boardInput) {
    const selectedLangs = getSelectedLanguages();
    const sort = document.getElementById('sortMethod')?.value || 'recent';
    const timeFilter = document.getElementById('timePeriod')?.value || 'day';
    const range = getSelectedRange();
    
    return {
        // 레거시 필드명
        board: boardInput,
        
        // ✅ 필터 옵션들 (정확한 필드명)
        sort: sort,
        start: range.start,
        end: range.end,
        min_views: parseInt(document.getElementById('minViews')?.value || '0'),
        min_likes: parseInt(document.getElementById('minRecommend')?.value || '0'),
        min_comments: parseInt(document.getElementById('minComments')?.value || '0'),
        time_filter: timeFilter,
        start_date: document.getElementById('startDate')?.value || null,
        end_date: document.getElementById('endDate')?.value || null,
        
        translate: selectedLangs.length > 0,
        target_languages: selectedLangs,
        
        debug: {
            frontend_version: '2.0.0',
            endpoint_type: 'legacy_auto',
            fallback: true
        }
    };
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
function getTranslatedStatus(statusKey, statusData = {}) {
    const lang = window.languages[currentLanguage];
    const template = lang.crawlingStatus?.[statusKey];

    if (!template) {
        console.warn(`Missing translation for status key: ${statusKey}`);
        return statusKey; // 키가 없으면 키 자체를 반환
    }
    
    return formatMessage(template, statusData);
}

// 레거시 상태 메시지 번역 (패턴 매칭)
function translateLegacyStatus(status) {
    const lang = window.languages[currentLanguage];
    
    // 패턴 매칭 규칙
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
    
// 🔥 통합 WebSocket 메시지 핸들러
function setupWebSocketMessageHandlers(ws, endpoint) {
    ws.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            console.log(`📨 메시지 수신 (${endpoint}):`, data);

            // 중단 처리 (최우선)
            if (data.cancelled) {
                showMessage('크롤링이 취소되었습니다.', 'info');
                resetCrawlingState();
                return;
            }

            // 신규 메시지 시스템 처리
            if (data.message_type) {
                handleNewMessageSystem(data);
                return;
            }

            // 레거시 시스템 처리 (하위 호환성)
            handleLegacyMessageSystem(data, endpoint);

        } catch (error) {
            console.error('메시지 파싱 오류:', error, event.data);
            showMessage('메시지 처리 중 오류가 발생했습니다.', 'error');
        }
    };

    ws.onerror = (error) => {
        console.error(`❌ WebSocket 오류 (${endpoint}):`, error);
        showMessage('연결 오류가 발생했습니다', 'error');
    };

    ws.onclose = (event) => {
        console.log(`🔌 WebSocket 연결 종료 (${endpoint}):`, event.code, event.reason);
        
        if (isLoading && event.code !== 1000) {
            showMessage('연결이 예기치 않게 종료되었습니다', 'error');
            resetCrawlingState();
        }
    };
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

// 레거시 진행률 메시지 처리 
function handleLegacyProgress(data, endpoint) {
    const progress = Math.min(Math.max(data.progress || 0, 0), 100);
    let status = data.status || data.message || '처리 중...';
    
    // 레거시 상태 메시지 번역
    status = translateLegacyStatus(status);
    
    console.log(`📊 레거시 진행률 (${endpoint}): ${progress}% - ${status}`);
    
    updateProgress(progress, status);
    
    // 부분 결과 실시간 표시
    if (data.partial_results && data.partial_results.length > 0) {
        displayPartialResults(data.partial_results);
    }
}
// 레거시 메시지 처리 (하위 호환성)
function handleLegacyMessage(data, endpoint) {
    // 중단 메시지 처리
    if (data.cancelled) {
        showMessage('크롤링이 취소되었습니다.', 'info');
        resetCrawlingState();
        return;
    }

    // 에러 처리
    if (data.error) {
        handleLegacyError(data.error, endpoint);
        return;
    }

    // 완료 처리
    if (data.done) {
        handleLegacyComplete(data, endpoint);
        return;
    }

    // 진행률 처리
    if (data.progress !== undefined) {
        handleLegacyProgress(data, endpoint);
        return;
    }

    // 상태 처리
    if (data.status) {
        handleLegacyStatus(data, endpoint);
        return;
    }

    // 부분 결과 처리
    if (data.data) {
        handlePartialResults(data, endpoint);
        return;
    }

    console.log(`ℹ️ 기타 메시지 (${endpoint}):`, data);
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
        const lang = window.languages[currentLanguage];
        crawlBtn.textContent = lang?.crawlingStatus?.inProgress || '크롤링 중...';
    }
    
    // 🔥 진행률 표시 시작
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

function startUniversalCrawling() {
    currentSite = 'universal';
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
    // 진행률 컨테이너 표시
    const progressContainer = document.getElementById('progressContainer');
    if (progressContainer) {
        progressContainer.classList.add('show');
    }
    
    // 진행률 바 업데이트
    const progressBar = document.getElementById('progress-bar') || 
                        document.querySelector('.progress-bar') ||
                        document.querySelector('[id*="progress"]');
    
    if (progressBar) {
        progressBar.style.width = `${Math.max(0, Math.min(100, progress))}%`;
        progressBar.setAttribute('aria-valuenow', progress);
    }
    
    // 진행률 텍스트 업데이트
    const progressText = document.getElementById('progress-text') || 
                        document.getElementById('progressText') ||
                        document.querySelector('.progress-text');
                        
    if (progressText) {
        progressText.textContent = message || `${progress}%`;
    }
    
    // 상세 정보 표시
    const progressDetails = document.getElementById('progress-details') || 
                        document.getElementById('progressDetails');
                        
    if (progressDetails && Object.keys(details).length > 0) {
        const detailsText = Object.entries(details)
            .map(([key, value]) => `${key}: ${value}`)
            .join(' | ');
        progressDetails.textContent = detailsText;
        progressDetails.style.display = 'block';
    } else if (progressDetails) {
        progressDetails.style.display = 'none';
    }
    
    console.log(`🎯 진행률 UI 업데이트: ${progress}% - ${message}`);
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
    // ✅ 수정: 영어 우선 폴백
    const lang = window.languages && window.languages[currentLanguage] ? 
                window.languages[currentLanguage] : 
                (window.languages && window.languages.en ? 
                 window.languages.en : 
                 window.languages.ko);
    
    if (results.length === 0) {
        const noResultsText = lang.resultTexts?.noResults || 'No results found';
        container.innerHTML = `<p style="text-align: center; color: #5f6368; font-size: 16px; padding: 40px;">${noResultsText}</p>`;
        return;
    }
    
    // 완료 알림
    setTimeout(() => {
        const completeText = lang.crawlingStatus?.complete || 'Collection complete';
        const foundText = lang.crawlingStatus?.found || ' posts found';
        const successMsg = `${completeText}! ${results.length}${foundText}`;
        showMessage(successMsg, 'success');
    }, 500);
    
    // 나머지 displayResults 로직은 동일...
    // (기존 코드 유지)
}

// ✅ 메시지 표시 함수들을 하나로 통합
function showMessage(message, type = 'info', options = {}) {
    try {
        const messageDiv = document.createElement('div');
        let displayMessage = message;
        
        // 언어 키인 경우 번역
        if (options.translate && window.languages) {
            const lang = window.languages[currentLanguage] || window.languages.en || window.languages.ko;
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
        
        document.body.appendChild(messageDiv);
        
        setTimeout(() => messageDiv.classList.add('show'), 100);
        
        setTimeout(() => {
            messageDiv.classList.remove('show');
            messageDiv.classList.add('hide');
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
            console.log(`📨 메시지 수신 (${endpoint}):`, data);

            // 취소 처리
            if (data.cancelled) {
                showMessage('크롤링이 취소되었습니다.', 'info');
                resetCrawlingState();
                return;
            }

            // 에러 처리
            if (data.error || data.error_key) {
                const errorMsg = data.error_detail || data.error || '크롤링 중 오류가 발생했습니다.';
                showMessage(errorMsg, 'error');
                resetCrawlingState();
                return;
            }

            // 완료 처리
            if (data.done) {
                const results = data.data || data.results || [];
                if (results.length > 0) {
                    crawlResults = results;
                    displayResults(results);
                    enableDownloadButtons();
                    showMessage(`크롤링 완료: ${results.length}개 게시물`, 'success');
                } else {
                    showMessage('결과가 없습니다.', 'warning');
                }
                resetCrawlingState();
                return;
            }

            // 진행률 처리
            if (data.progress !== undefined) {
                const progress = Math.max(0, Math.min(100, data.progress));
                const status = data.status || data.message || '처리 중...';
                updateProgress(progress, status);
                return;
            }

        } catch (error) {
            console.error('메시지 파싱 오류:', error);
            showMessage('메시지 처리 중 오류가 발생했습니다.', 'error');
        }
    };

    ws.onerror = (error) => {
        console.error(`❌ WebSocket 오류 (${endpoint}):`, error);
        showMessage('연결 오류가 발생했습니다', 'error');
        resetCrawlingState();
    };

    ws.onclose = (event) => {
        console.log(`🔌 WebSocket 연결 종료 (${endpoint}):`, event.code);
        if (isLoading && event.code !== 1000) {
            showMessage('연결이 예기치 않게 종료되었습니다', 'error');
            resetCrawlingState();
        }
    };
}

// ❌ 삭제: handleWebSocketMessage, handleNewMessageSystem, handleLegacyMessageSystem 등

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

function enableDownloadButtons() {
const downloadButtons = document.querySelectorAll('.download-button');
downloadButtons.forEach(button => {
    button.disabled = false;
    button.style.opacity = '1';
});
}

function showProgressBar(show) {
    const progressContainer = document.querySelector('.progress-container');
    if (progressContainer) {
        progressContainer.style.display = show ? 'block' : 'none';
    }
}

// 선택된 언어 가져오기
function getSelectedLanguages() {
    // 언어 선택 체크박스가 있는지 확인
    const languageCheckboxes = document.querySelectorAll('input[name="target_languages"]:checked');
    if (languageCheckboxes.length > 0) {
        return Array.from(languageCheckboxes).map(cb => cb.value);
    }
    
    // 기본값: 현재 선택된 언어로 번역
    if (currentLanguage !== 'ko') {
        return [currentLanguage];
    }
    
    return []; // 번역 안함
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

// ✅ 안전한 언어팩 접근
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
        'universal': lang.crawlButtonMessages?.universalEmpty || 'Enter website URL',
        'lemmy': lang.crawlButtonMessages?.lemmyEmpty || 'Enter Lemmy community',
        'default': lang.crawlButtonMessages?.boardEmpty || 'Enter board name'
    };
    
    return messages[site] || messages.default;
}

// 사이트별 입력 유효성 검사
function validateSiteInput(site, boardValue, lang) {
    switch (site) {
        case 'universal':
            const isValidUrl = boardValue.startsWith('http://') || 
                             boardValue.startsWith('https://') ||
                             (boardValue.includes('.') && boardValue.includes('/'));
            
            return {
                isValid: isValidUrl,
                message: isValidUrl ? '' : (lang.crawlButtonMessages?.universalUrlError || 'Enter a valid URL')
            };
            
        case 'lemmy':
            // ✅ 수정: community_name 변수 사용하지 않고 직접 검증
            if (boardValue.includes('@') && boardValue.split('@').length === 2) {
                const [community, instance] = boardValue.split('@');
                return {
                    isValid: community.length > 0 && instance.length > 0,
                    message: ''
                };
            } else if (boardValue.startsWith('https://') && boardValue.includes('/c/')) {
                return { isValid: true, message: '' };
            } else if (boardValue.length > 2) {
                return {
                    isValid: true,
                    message: `Try ${boardValue}@lemmy.world`
                };
            } else {
                return {
                    isValid: false,
                    message: lang.crawlButtonMessages?.lemmyFormatError || 'Format: community@lemmy.world'
                };
            }
            
        case 'reddit':
            const hasRedditError = boardValue.includes('reddit.com') && !boardValue.includes('/r/');
            return {
                isValid: !hasRedditError,
                message: hasRedditError ? (lang.crawlButtonMessages?.redditFormatError || 'Reddit format error') : ''
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
window.debugCrawlConfig = debugCrawlConfig;
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
    showMessage,
    extractSiteName,
    updateLabels
};
