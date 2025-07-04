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

let autocompleteTimer = null;

// ==================== 모달 기능 호환성 래퍼 ====================
// modal.js와의 호환성을 위한 래퍼 함수들

function ensureModalManagerLoaded() {
    if (!window.modalManager) {
        console.error('❌ Modal 모듈이 로드되지 않았습니다');
        if (window.PickPostGlobals && window.PickPostGlobals.showMessage) {
            window.PickPostGlobals.showMessage(
                '모달 기능을 사용할 수 없습니다. 페이지를 새로고침해주세요.', 
                'error'
            );
        }
        return false;
    }
    return true;
}

// 피드백 모달 호환성 함수들
function openBugReportModal() {
    if (ensureModalManagerLoaded()) {
        window.modalManager.openModal('bugReport');
    }
}

function closeBugReportModal() {
    if (ensureModalManagerLoaded()) {
        window.modalManager.closeModal('bugReport');
    }
}

function updateCharacterCount() {
    if (ensureModalManagerLoaded()) {
        const bugReportModal = window.modalManager.modals.get('bugReport');
        if (bugReportModal && bugReportModal.updateCharacterCount) {
            bugReportModal.updateCharacterCount();
        }
    }
}

function updateBugReportButton() {
    if (ensureModalManagerLoaded()) {
        const bugReportModal = window.modalManager.modals.get('bugReport');
        if (bugReportModal && bugReportModal.updateSubmitButton) {
            bugReportModal.updateSubmitButton();
        }
    }
}

function handleFileUpload(event) {
    if (ensureModalManagerLoaded()) {
        const bugReportModal = window.modalManager.modals.get('bugReport');
        if (bugReportModal && bugReportModal.handleFileUpload) {
            bugReportModal.handleFileUpload(event);
        }
    }
}

function removeFile() {
    if (ensureModalManagerLoaded()) {
        const bugReportModal = window.modalManager.modals.get('bugReport');
        if (bugReportModal && bugReportModal.removeFile) {
            bugReportModal.removeFile();
        }
    }
}

// 약관 모달 호환성 함수들
function openTermsModal() {
    if (ensureModalManagerLoaded()) {
        window.modalManager.openModal('terms');
    }
}

function closeTermsModal() {
    if (ensureModalManagerLoaded()) {
        window.modalManager.closeModal('terms');
    }
}

// 개인정보처리방침 모달 호환성 함수들
function openPrivacyModal() {
    if (ensureModalManagerLoaded()) {
        window.modalManager.openModal('privacy');
    }
}

function closePrivacyModal() {
    if (ensureModalManagerLoaded()) {
        window.modalManager.closeModal('privacy');
    }
}

// 비즈니스 모달 호환성 함수들
function openBusinessModal() {
    if (ensureModalManagerLoaded()) {
        window.modalManager.openModal('business');
    }
}

function closeBusinessModal() {
    if (ensureModalManagerLoaded()) {
        window.modalManager.closeModal('business');
    }
}

// 바로가기 모달 호환성 함수들
function openShortcutModal() {
    if (ensureModalManagerLoaded()) {
        window.modalManager.openModal('shortcut');
    }
}

function closeShortcutModal() {
    if (ensureModalManagerLoaded()) {
        window.modalManager.closeModal('shortcut');
    }
}

function saveShortcut() {
    if (ensureModalManagerLoaded()) {
        const shortcutModal = window.modalManager.modals.get('shortcut');
        if (shortcutModal && shortcutModal.saveShortcut) {
            shortcutModal.saveShortcut();
        }
    }
}

// ==================== 전역 오류 처리기 ====================
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

// ==================== API 및 환경 설정 ====================
function getApiConfig() {
    const hostname = window.location.hostname;
    
    if (hostname === 'localhost' || hostname === '127.0.0.1') {
        return {
            API_BASE_URL: 'http://localhost:8000',
            WS_BASE_URL: 'ws://localhost:8000'
        };
    }
    
    return {
        API_BASE_URL: 'https://api.pick-post.com',
        WS_BASE_URL: 'wss://api.pick-post.com'
    };
}
// API 설정을 전역 변수로 저장
const { API_BASE_URL, WS_BASE_URL } = getApiConfig();
console.log('API 설정:', { API_BASE_URL, WS_BASE_URL });

// ==================== 언어 및 라벨 관리 ====================
function getLabels() {
    return window.languages[currentLanguage] || window.languages.ko;
}

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

function updateTimeFilterLabels() {
    const timePeriodSelect = document.getElementById('timePeriod');
    const lang = window.languages[currentLanguage] || window.languages.en;
    
    if (!timePeriodSelect || !lang.timeFilterLabels) return;
    
    const currentValue = timePeriodSelect.value;
    
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
    
    // 기본 UI 요소들
    const elements = [
        { id: 'crawlBtn', prop: 'textContent', value: lang.start },
        { id: 'cancelBtn', prop: 'textContent', value: lang.cancel },
        { id: 'downloadBtn', prop: 'textContent', value: lang.download },
        { id: 'siteInput', prop: 'placeholder', value: lang.sitePlaceholder },
        { id: 'boardInput', prop: 'placeholder', value: lang.boardPlaceholder }
    ];
    
    // 라벨 요소들
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
    
    // 날짜 라벨들
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
    
    // 드롭다운 옵션들 업데이트
    updateSortMethodLabels();
    updateTimeFilterLabels();
    
    // Footer 업데이트
    updateFooterLabels();
    
    // 공지사항 버튼 업데이트
    const announcementBtnText = document.getElementById('announcementBtnText');
    if (announcementBtnText) {
        announcementBtnText.textContent = lang.announcementBtnText || 'Announcements';
    }
    
    // 현재 사이트의 보드 placeholder 업데이트
    if (currentSite) {
        updateBoardPlaceholder(currentSite);
    }
}

function updateFooterLabels() {
    const lang = window.languages?.[currentLanguage] || window.languages?.en || {};
    
    console.log(`🔄 Footer 언어 업데이트: ${currentLanguage}`);
    
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

function toggleLanguageDropdown() {
    const dropdown = document.getElementById('languageDropdown');
    dropdown.classList.toggle('show');
}

function hideLanguageDropdown() {
    document.getElementById('languageDropdown').classList.remove('show');
}

function selectLanguage(langCode, langName = null) {
    console.log(`🌐 언어 변경 요청: ${langCode}`);
    
    currentLanguage = langCode;
    window.currentLanguage = langCode;

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
    
    // 즉시 모든 라벨 업데이트 (Footer 포함)
    setTimeout(() => {
        updateLabels();
        
        // 현재 선택된 사이트가 있으면 관련 옵션들도 다시 로드
        if (currentSite) {
            loadSiteSortOptions(currentSite);
            updateBoardPlaceholder(currentSite);
        }
        
        console.log(`✅ 언어 변경 완료: ${langCode}`);
    }, 50);
    
    hideLanguageDropdown();
}

// ==================== 페이지 초기화 및 이벤트 설정 ====================
function refreshPage() {
    location.reload();
}

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

    boardInput.addEventListener('input', function() {
    if (isProgrammaticInput) {
        isProgrammaticInput = false;
        return;
    }
    
    const value = this.value.trim();
    
    if (value.length === 0 && currentSite === 'lemmy') {
        showLemmyHelp();
    } else if (value.length >= 2) {
        // 디바운스 적용 - 이전 타이머 취소하고 150ms 후 실행
        clearTimeout(autocompleteTimer);
        autocompleteTimer = setTimeout(() => fetchAutocomplete(value), 150);
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
        // 모달 관련 이벤트 리스너는 modal.js에서 처리
    });

    siteInput.addEventListener('paste', function(e) {
    setTimeout(() => {
        const pastedValue = this.value.trim();
        if (pastedValue && (pastedValue.startsWith('http://') || 
                           pastedValue.startsWith('https://') ||
                           (pastedValue.includes('.') && pastedValue.includes('/')))) {
            handleSiteSearch();
        }
    }, 100);
});
}

document.addEventListener('DOMContentLoaded', function() {
    console.log('📄 DOM 로딩 완료');
    
    // 기본 언어 설정 개선
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
    
    // 언어팩 확인 후 모든 UI 업데이트
    if (window.languages && window.languages.en) {
        updateLabels();
    } else {
        console.warn('언어팩이 로드되지 않았습니다');
        setTimeout(() => {
            if (window.languages && window.languages.en) {
                updateLabels();
            }
        }, 100);
    }
    
    // 모달 매니저 로드 대기
    function waitForModalManager() {
        if (window.modalManager) {
            console.log('✅ Modal 매니저 로드 완료');
            return;
        }
        
        console.log('⏳ Modal 매니저 로드 대기 중...');
        setTimeout(waitForModalManager, 100);
    }
    
    waitForModalManager();
    
    // 나머지 초기화
    initializeLemmyVariables();
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
    
    if (window.initializeFeedbackSystem) {
        window.initializeFeedbackSystem();
    }
    
    window.dispatchEvent(new Event('PickPostReady'));
});

// ==================== 바로가기 관리 시스템 ====================
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

function loadShortcuts() {
    const container = document.getElementById('siteSelection');
    const lang = window.languages[currentLanguage] || window.languages.en;

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
            ➕ ${lang.addShortcut || 'Add'}
        </button>
    ` : '';
    
    container.innerHTML = shortcutButtons + addButton;
}

function removeShortcut(index) {
    shortcuts.splice(index, 1);
    localStorage.setItem('pickpost_shortcuts', JSON.stringify(shortcuts));
    loadShortcuts();
}

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

// ==================== 사이트 검색 및 자동완성 ====================
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

function showSiteAutocomplete(keyword) {
    if (!keyword || keyword.length < 1) {
        hideSiteAutocomplete();
        return;
    }
    
    const keywordLower = keyword.toLowerCase();
    
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
            (keywordLower.includes('범용') && item.site === 'universal');
    });

    if (suggestions.length > 0) {
        siteAutocompleteData = suggestions;
        showSiteSuggestions(suggestions, keyword);
    } else {
        hideSiteAutocomplete();
    }
}

function showSiteSuggestions(suggestions, keyword) {
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

function selectSiteAutocompleteItem(index) {
    if (index >= 0 && index < siteAutocompleteData.length) {
        const selectedSite = siteAutocompleteData[index];
        
        // 선택된 사이트 이름을 입력창에 표시
        document.getElementById('siteInput').value = selectedSite.name;
        hideSiteAutocomplete();
        
        // 선택된 사이트 타입으로 설정
        selectSite(selectedSite.site);
    }
}

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

function isElementVisible(element) {
    return element.offsetParent !== null && !element.disabled;
}

function handleSiteSearch() {
    const siteInputValue = document.getElementById('siteInput').value.trim();
    
    if (siteInputValue) {
        // URL 감지
        const isURL = siteInputValue.startsWith('http://') || 
                     siteInputValue.startsWith('https://') ||
                     (siteInputValue.includes('.') && siteInputValue.includes('/'));
        
        if (isURL) {
            // 사이트 이름 추출
            const siteName = extractSiteName(siteInputValue);
            
            // 사이트 검색창에 사이트 이름 설정
            document.getElementById('siteInput').value = siteName;
            document.getElementById('clearSiteBtn').style.display = 'flex';
            
            // 사이트 타입 감지 및 설정
            const detectedSite = extractSiteName(siteInputValue);
            selectSite(detectedSite);
            
            // 세부검색창에 원본 URL 복사
            setTimeout(() => {
                const boardInput = document.getElementById('boardInput');
                if (boardInput) {
                    safeSetBoardInput(siteInputValue);
                }
            }, 500);
        } else {
            // 기존 로직
            const detectedSite = extractSiteName(siteInputValue);
            selectSite(detectedSite);
            document.getElementById('siteInput').value = siteInputValue;
        }
    }
}


// ==================== 사이트 선택 및 설정 ====================
function selectSite(site) {
    // 안전한 초기화
    autocompleteData = [];
    highlightIndex = -1;
    
    const container = document.getElementById('autocomplete');
    if (container) {
        container.innerHTML = '';
    }
    
    const boardInput = document.getElementById('boardInput');
    if (boardInput && site !== 'universal' && !boardInput.value.trim()) {
        // 값이 없을 때만 초기화
        boardInput.value = '';
    }
    
    if (searchInitiated && currentSite === site) return;
    
    // 현재 사이트 설정
    currentSite = site;
    searchInitiated = true;
    
    if (site === 'lemmy') {
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

    loadSiteSortOptions(site);
    animateToSearchMode();
    
    setTimeout(() => {
        showBoardSearch();
        showOptions(site);
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

function updateBoardPlaceholder(site) {
    const boardInput = document.getElementById('boardInput');
    const lang = window.languages[currentLanguage];
    
    if (boardInput && lang.boardPlaceholders) {
        const placeholder = lang.boardPlaceholders[site] || lang.boardPlaceholders.default;
        boardInput.placeholder = placeholder;
    }
}

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
            sortSelect.innerHTML = `
                <option value="recent">${lang.sortOptions?.other?.recent || 'Recent'}</option>
                <option value="popular">${lang.sortOptions?.other?.popular || 'Popular'}</option>
                <option value="recommend">${lang.sortOptions?.other?.recommend || 'Recommend'}</option>
                <option value="comments">${lang.sortOptions?.other?.comments || 'Comments'}</option>
            `;
        }
        sortSelect.dispatchEvent(new Event('change'));
    } catch (error) {
        console.error('정렬 옵션 로드 오류:', error);
    }
}

function animateToSearchMode() {
    const searchText = document.getElementById('siteInput').value.trim();
    if (!searchText) return;

    const logoContainer = document.getElementById('logoContainer');
    const mainContainer = document.getElementById('mainContainer');
    
    logoContainer.classList.add('compact');
    mainContainer.classList.add('compact');
}

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

function showOptions(site) {
    const optionsContainer = document.getElementById('optionsContainer');
    const buttonContainer = document.getElementById('buttonContainer');
    
    setTimeout(() => {
        optionsContainer.classList.add('show');
        buttonContainer.classList.add('show');
    }, 200);

    updateCrawlButton();
}

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

function selectBBCSection(index) {
    if (index >= 0 && index < autocompleteData.length) {
        safeSetBoardInput(autocompleteData[index]);
    }
}

async function fetchAutocomplete(keyword) {
    console.log(`🔍 자동완성 요청: site=${currentSite}, keyword="${keyword}"`);
    
    if (!keyword || keyword.trim().length < 2) {
        console.log('⚠️ 키워드 너무 짧음 또는 비어있음');
        if (currentSite === 'lemmy' && (!keyword || keyword.trim().length === 0)) {
            showLemmyHelp();
            return;
        }
        hideAutocomplete();
        return;
    }
    
    if (!currentSite) {
        console.log('⚠️ 사이트가 선택되지 않음');
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
        console.log(`📡 API 호출: ${API_BASE_URL}/autocomplete/${currentSite}?keyword=${encodeURIComponent(keyword)}`);
        
        const response = await fetch(`${API_BASE_URL}/autocomplete/${currentSite}?keyword=${encodeURIComponent(keyword)}`);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        console.log(`📨 API 응답:`, data);
        
        if (data.matches && data.matches.length > 0) {
            autocompleteData = data.matches;
            showAutocomplete(keyword);
            console.log(`✅ 자동완성 표시: ${data.matches.length}개 항목`);
        } else {
            console.log('📭 API에서 결과 없음, 오프라인 자동완성 시도');
            useOfflineAutocomplete(keyword);
        }
    } catch (error) {
        console.error('❌ 자동완성 API 오류:', error);
        console.log('🔄 오프라인 자동완성으로 폴백');
        useOfflineAutocomplete(keyword);
    }
}

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

function showLemmyHelpContent() {
    const container = document.getElementById('autocomplete');
    const boardSearchContainer = document.getElementById('boardSearchContainer');
    
    if (!container || !boardSearchContainer) return;
    
    boardSearchContainer.classList.add('dropdown-active');
    
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

function showLemmyHelp() {
    const boardInput = document.getElementById('boardInput');
    if (boardInput.value.trim()) {
        return;
    }
    
    showLemmyHelpContent();
}

function setLemmyCommunity(community) {
    safeSetBoardInput(community);
}

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
        if (currentSite === 'universal') {
            buttonText = lang.crawlButtonMessages?.universalEmpty || 'Enter website URL';
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
    
    if (isLoading) {
        buttonText = lang.crawlingStatus?.processing || '크롤링 중...';
    }
    
    crawlBtn.textContent = buttonText;
}

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

function showAutocomplete(keyword) {
    console.log(`🎨 자동완성 UI 표시: ${autocompleteData.length}개 항목`);
    
    const container = document.getElementById('autocomplete');
    const boardSearchContainer = document.getElementById('boardSearchContainer');
    
    if (autocompleteData.length === 0) {
        console.log('⚠️ 자동완성 데이터 없음');
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
            <div class="autocomplete-item" 
                data-index="${index}" 
                onclick="selectAutocompleteItem(${index})"
                onmouseenter="highlightIndex = ${index}; updateHighlight();"
                style="cursor: pointer;">
                <div style="flex: 1;">${highlighted}</div>
            </div>
        `;
    }).join('');

    container.classList.add('show');
    highlightIndex = -1;

    // 마우스 이벤트 처리
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
    
    console.log('✅ 자동완성 UI 표시 완료');
}

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

function updateHighlight() {
    const boardInput = document.getElementById('boardInput');
    document.querySelectorAll('.autocomplete-item').forEach((item, index) => {
        item.classList.toggle('highlighted', index === highlightIndex);
    });

    if (highlightIndex >= 0 && highlightIndex < autocompleteData.length) {
        boardInput.value = autocompleteData[highlightIndex];
    }
}

function selectAutocompleteItem(index) {
    if (index >= 0 && index < autocompleteData.length) {
        safeSetBoardInput(autocompleteData[index]);
    }
}

function clearBoardInput() {
    const boardInput = document.getElementById('boardInput');
    boardInput.value = '';
    document.getElementById('clearBoardBtn').style.display = 'none';
    
    hideAutocomplete();
    updateCrawlButton();
    
    boardInput.focus();
}

// ==================== 크롤링 시스템 ====================
async function createWebSocketWithRetry(endpoint, config, maxRetries = 2) {
    const { WS_BASE_URL } = getApiConfig();
    
    for (let retry = 0; retry < maxRetries; retry++) {
        try {
            console.log(`WebSocket 연결 시도 ${retry + 1}/${maxRetries}: ${endpoint}`);
            
            const wsUrl = `${WS_BASE_URL}/ws/${endpoint}`;
            const ws = new WebSocket(wsUrl);
            
            const timeout = setTimeout(() => {
                if (ws.readyState === WebSocket.CONNECTING) {
                    ws.close();
                }
            }, 10000);
            
            return new Promise((resolve, reject) => {
                ws.onopen = () => {
                    clearTimeout(timeout);
                    console.log(`✅ WebSocket 연결 성공: ${endpoint}`);
                    
                    ws.send(JSON.stringify(config));
                    console.log('📤 크롤링 설정 전송:', config);
                    
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

async function startCrawling() {
    try {
        if (window.legalConsentManager && !window.legalConsentManager.hasValidConsent()) {
            await window.legalConsentManager.showConsentModal();
        }
    } catch (error) {
        // 👇 이 부분을 언어팩으로 변경
        showMessage('legalConsent.consentRequired', 'warning', { translate: true });
        return;
    }

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
        
        // 백엔드로 전달할 설정
        const config = {
            input: boardInput,  // 게시판 이름만 전달
            site: currentSite,  // 이미 선택된 사이트 타입 명시적 전달
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

function updateUIForCrawlStart() {
    crawlResults = [];
    const resultsContainer = document.getElementById('resultsContainer') || 
                            document.getElementById('results');
    if (resultsContainer) {
        resultsContainer.innerHTML = '';
    }
    
    const crawlBtn = document.getElementById('crawlBtn');
    if (crawlBtn) {
        crawlBtn.disabled = true;
        crawlBtn.textContent = getLocalizedMessage('crawlingStatus.processing');
    }
    
    showProgress();
    showCancelButton();
    
    console.log('🚀 크롤링 UI 준비 완료');
}

function resetCrawlingState() {
    try {
        hideProgress();
        isLoading = false;
        updateCrawlButton();
        hideCancelButton();
        // 미디어 다운로드 버튼 숨기기
        const downloadMediaBtn = document.getElementById('downloadMediaBtn');
        if (downloadMediaBtn) {
            downloadMediaBtn.style.display = 'none';
        }

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

function showCancelButton() {
    const cancelBtn = document.getElementById('cancelBtn');
    cancelBtn.style.display = 'inline-flex';
}

function hideCancelButton() {
    const cancelBtn = document.getElementById('cancelBtn');
    cancelBtn.style.display = 'none';
}

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

window.addEventListener('beforeunload', function() {
    if (currentCrawlId) {
        console.log('페이지 종료시 크롤링 정리');
        sendCancelRequest(currentCrawlId);
    }
});

// ==================== 진행 상황 및 결과 표시 ====================
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

function updateProgress(progress, message, details = {}) {
    const progressContainer = document.getElementById('progressContainer');
    if (progressContainer) {
        progressContainer.classList.add('show');
        progressContainer.style.display = 'block';
    }
    
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
        let displayMessage = message;
        if (typeof message === 'string' && !message.includes(' ') && window.languages) {
            const translatedMessage = getLocalizedMessage(message);
            if (translatedMessage !== message) {
                displayMessage = translatedMessage;
            }
        }
        progressText.textContent = displayMessage || `${progress}%`;
    }
    
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

// ==================== 광고 관련 함수 ====================
function createAdHtml(adIndex) {
    const lang = window.languages[currentLanguage] || window.languages.en;
    const adLabel = lang.ads?.advertisement || 'Advertisement';
    
    return `
        <div class="ad-container">
            <div class="ad-label">${adLabel}</div>
            <div class="ad-content">
                <ins class="adsbygoogle"
                     style="display:block; width:100%; min-width:300px; min-height:250px;"
                     data-ad-client="ca-pub-8742005050963144"
                     data-ad-slot="7984301720"
                     data-ad-format="rectangle"></ins>
            </div>
        </div>
    `;
}

function initializeAds() {
    try {
        // 잠시 대기 후 광고 초기화 (DOM이 완전히 렌더링된 후)
        setTimeout(() => {
            const adElements = document.querySelectorAll('.adsbygoogle:not([data-adsbygoogle-status])');
            
            if (adElements.length === 0) {
                console.log('ℹ️ 초기화할 광고가 없습니다.');
                return;
            }
            
            console.log(`🎯 광고 초기화 시작: ${adElements.length}개`);
            
            adElements.forEach((ad, index) => {
                try {
                    // 개별 광고마다 약간의 지연을 두고 초기화
                    setTimeout(() => {
                        if (!ad.hasAttribute('data-adsbygoogle-status')) {
                            // 광고 크기 검증
                            const rect = ad.getBoundingClientRect();
                            if (rect.width > 0 && rect.height > 0) {
                                (adsbygoogle = window.adsbygoogle || []).push({});
                                console.log(`✅ 광고 ${index + 1} 초기화 성공`);
                            } else {
                                console.warn(`⚠️ 광고 ${index + 1} 크기가 0입니다.`);
                            }
                        }
                    }, index * 200); // 각 광고마다 200ms 간격
                } catch (error) {
                    console.error(`❌ 광고 ${index + 1} 초기화 실패:`, error);
                }
            });
        }, 500); // 전체적으로 500ms 대기
        
    } catch (error) {
        console.warn('❌ 광고 초기화 실패:', error);
    }
}

// ==================== 결과 표시 함수 ====================
function displayResults(results, startIndex = 1) {
    const container = safeGetElement('resultsContainer');
    if (!container) {
        console.error('resultsContainer 요소를 찾을 수 없습니다.');
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
    
    const lang = window.languages[currentLanguage] || window.languages.en;
    
    setTimeout(() => {
        const message = lang.completionMessages?.success || 'Crawling complete: {count} posts';
        const translatedMessage = message.replace('{count}', results.length);
        showMessage(translatedMessage, 'success');
    }, 500);
    
    const elapsedTime = crawlStartTime ? Math.round((Date.now() - crawlStartTime) / 1000) : 0;
    const isAdvanced = safeGetElement('advancedSearch')?.checked || false;
    const start = parseInt(safeGetValue(isAdvanced ? 'startRankAdv' : 'startRank', '1'));
    const end = parseInt(safeGetValue(isAdvanced ? 'endRankAdv' : 'endRank', '20'));
    const estimatedPages = Math.ceil(end / 25);
    
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
    
    // 요약 정보 HTML 생성
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
    
    // 광고 삽입 간격 설정 (4~7개 사이 랜덤)
    const getRandomAdInterval = () => Math.floor(Math.random() * 3) + 4; // 4~7 랜덤
    let nextAdPosition = getRandomAdInterval(); // 첫 번째 광고 위치
    let adCount = 0;
    
    // 모든 HTML 요소를 배열로 준비
    const htmlElements = [];
    
    // 결과 아이템들 생성
    results.forEach((item, index) => {
        const itemNumber = startIndex + index;
        
        // 🔥 기본 결과 아이템 데이터 추출
        const title = item.원제목 || item.title || item.제목 || 'No Title';
        const translatedTitle = item.번역제목 || item.translated_title || '';
        const link = item.링크 || item.link || item.url || '#';
        const content = item.본문 || item.content || item.내용 || '';
        const views = item.조회수 || item.views || 0;
        const likes = item.추천수 || item.likes || item.score || 0;
        const comments = item.댓글수 || item.comments || 0;
        const date = item.작성일 || item.date || item.created_at || '';
        
        // 🔥 썸네일 관련 데이터 추출
        const thumbnailUrl = item['썸네일 URL'] || item.thumbnail_url || item.썸네일 || item['이미지 URL'] || '';
        const hasThumbnail = thumbnailUrl && thumbnailUrl.trim() !== '';
        
        // 🔥 미디어 타입 정보 추출
        const mediaType = item['미디어타입'] || item.media_type || item.mediaType || '';
        const mediaCount = item['미디어수'] || item.media_count || item.mediaCount || 0;
        const fileExtension = item['파일확장자'] || item.file_extension || '';
        
        // 라벨 텍스트
        const viewsLabel = lang.views || 'Views';
        const likesLabel = lang.likes || 'Likes'; 
        const commentsLabel = lang.comments || 'Comments';
        
        // 번역 제목 표시 여부
        const shouldShowTranslation = translatedTitle && 
                                translatedTitle !== title && 
                                translatedTitle.trim() !== '' &&
                                !translatedTitle.includes('Translation not needed');
        
        // 🔥 미디어 인디케이터 삭제 (2번째 사진에 없음)

        // 🔥 수정된 결과 아이템 HTML 생성 (썸네일이 있을 때 레이아웃 분리)
        const resultHtml = `
            <div class="result-item result-item-hidden" data-index="${index}">
                ${hasThumbnail ? `
                    <div style="display: flex; gap: 12px; height: 100%;">
                        <div style="flex: 1; display: flex; flex-direction: column;">
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
                            
                            <div class="result-meta-row" style="display: flex; align-items: center; gap: 0;">
                                <div style="display: flex; align-items: center; gap: 0;">
                                    <div class="result-date">📅 ${date}</div>
                                    ${views > 0 ? `<div class="stat-item" title="${viewsLabel}" style="margin-left: 4px;">👁️ ${views.toLocaleString()}</div>` : ''}
                                    ${likes > 0 ? `<div class="stat-item" title="${likesLabel}" style="margin-left: 4px;">👍 ${likes.toLocaleString()}</div>` : ''}
                                    ${comments > 0 ? `<div class="stat-item" title="${commentsLabel}" style="margin-left: 4px;">💬 ${comments.toLocaleString()}</div>` : ''}
                                </div>
                            </div>
                            
                            ${content ? `<div class="result-content">${content.length > 200 ? content.substring(0, 200) + '...' : content}</div>` : ''}
                            
                            <div class="result-links" style="margin-top: auto;">
                                <a href="${link}" target="_blank" rel="noopener noreferrer">
                                    ${texts.viewOriginal} →
                                </a>
                            </div>
                        </div>
                        
                        <div style="flex-shrink: 0;">
                            <img src="${thumbnailUrl}" 
                                 alt="썸네일" 
                                 class="result-thumbnail" 
                                 onerror="this.style.display='none'" 
                                 loading="lazy"
                                 onclick="window.open('${link}', '_blank')"
                                 title="클릭해서 원본 보기"
                                 style="width: 120px; height: 90px; object-fit: cover; border-radius: 6px; border: 1px solid #dadce0;">
                        </div>
                    </div>
                ` : `
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
                    
                    <div class="result-meta-row" style="display: flex; align-items: center; gap: 0;">
                        <div style="display: flex; align-items: center; gap: 0;">
                            <div class="result-date">📅 ${date}</div>
                            ${views > 0 ? `<div class="stat-item" title="${viewsLabel}" style="margin-left: 4px;">👁️ ${views.toLocaleString()}</div>` : ''}
                            ${likes > 0 ? `<div class="stat-item" title="${likesLabel}" style="margin-left: 4px;">👍 ${likes.toLocaleString()}</div>` : ''}
                            ${comments > 0 ? `<div class="stat-item" title="${commentsLabel}" style="margin-left: 4px;">💬 ${comments.toLocaleString()}</div>` : ''}
                        </div>
                    </div>
                    
                    ${content ? `<div class="result-content">${content.length > 200 ? content.substring(0, 200) + '...' : content}</div>` : ''}
                    
                    <div class="result-links">
                        <a href="${link}" target="_blank" rel="noopener noreferrer">
                            ${texts.viewOriginal} →
                        </a>
                    </div>
                `}
            </div>
        `;
        
        // 결과 아이템 추가
        htmlElements.push(resultHtml);
        
        // 광고 삽입 조건: 설정된 위치에 도달했고 마지막 아이템이 아닐 때
        if ((index + 1) === nextAdPosition && index < results.length - 1) {
            adCount++;
            htmlElements.push(createAdHtml(adCount));
            
            // 다음 광고 위치를 새로운 랜덤 간격으로 설정
            nextAdPosition += getRandomAdInterval();
        }
    });
    
    // 전체 결과 HTML 조합
    const resultsHtml = htmlElements.join('');
    
    try {
        // 전체 HTML을 컨테이너에 삽입
        container.innerHTML = summaryHtml + resultsHtml;
        
        // 🔥 썸네일 관련 애니메이션 및 이벤트 설정
        const resultItems = container.querySelectorAll('.result-item-hidden');
        resultItems.forEach((item, index) => {
            setTimeout(() => {
                item.classList.remove('result-item-hidden');
                item.classList.add('result-item-shown');
            }, index * 100);
        });
        
        // 🔥 썸네일 이미지 로드 오류 처리 개선
        const thumbnailImages = container.querySelectorAll('.result-thumbnail');
        thumbnailImages.forEach(img => {
            img.addEventListener('error', function() {
                console.log(`썸네일 로드 실패: ${this.src}`);
                this.style.display = 'none';
            });
            
            img.addEventListener('load', function() {
                console.log(`썸네일 로드 성공: ${this.src}`);
            });
        });
        
        // UI 업데이트 및 광고 초기화
        setTimeout(() => {
            enableDownloadButtons();
            
            // 광고 초기화
            initializeAds();
            
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
        
        console.log(`✅ ${results.length}개 결과 표시 완료 (광고 ${adCount}개, 썸네일 ${thumbnailImages.length}개 포함)`);
        
    } catch (error) {
        console.error('❌ 결과 표시 중 오류:', error);
        showSimpleResults(results);
    }
}

function showSimpleResults(results) {
    const container = safeGetElement('resultsContainer');
    if (container) {
        container.innerHTML = `
            <div style="text-align: center; padding: 20px;">
                <h3>크롤링 완료: ${results.length}개 결과</h3>
                <p>결과를 표시하는 중 오류가 발생했지만, 데이터는 정상적으로 수집되었습니다.</p>
            </div>
        `;
    }
}

function clearResults() {
    const container = document.getElementById('resultsContainer');
    const downloadBtn = document.getElementById('downloadBtn');
    const downloadMediaBtn = document.getElementById('downloadMediaBtn');
    
    container.innerHTML = '';
    downloadBtn.style.display = 'none';
    crawlResults = [];
    
    // 미디어 다운로드 버튼 숨기기 추가
    if (downloadMediaBtn) {
        downloadMediaBtn.style.display = 'none';
    }

    container.style.opacity = '0';
    container.style.transform = 'translateY(-8px)';
    
    setTimeout(() => {
        container.style.opacity = '1';
        container.style.transform = 'translateY(0)';
    }, 300);
}

function showMessage(message, type = 'info', options = {}) {
    try {
        const messageDiv = document.createElement('div');
        let displayMessage = message;
        
        if (typeof message === 'string' && !message.includes(' ') && window.languages) {
            const translatedMessage = getLocalizedMessage(message, options.variables);
            if (translatedMessage !== message) {
                displayMessage = translatedMessage;
            }
        }

        if (options.translate && window.languages) {
            const lang = window.languages[currentLanguage] || window.languages.en;
            if (lang.notifications && lang.notifications[message]) {
                displayMessage = lang.notifications[message];
                
                if (options.variables) {
                    Object.keys(options.variables).forEach(key => {
                        displayMessage = displayMessage.replace(`{${key}}`, options.variables[key]);
                    });
                }
            }
        }
        
        messageDiv.className = `temporary-message ${type}`;
        messageDiv.textContent = displayMessage;
        
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
        alert(message);
    }
}

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
                let status = "";
                
                // 언어팩 키가 있으면 활용
                if (data.status_key && data.status_data) {
                    status = getLocalizedMessage(data.status_key, data.status_data);
                } else if (data.status) {
                    status = data.status;  // 폴백
                }
                
                updateProgress(data.progress, status);
            }

        } catch (error) {
            console.error('메시지 파싱 오류:', error);
            showMessage('errorMessages.general', 'error', { translate: true });
        }
    };

    ws.onerror = (error) => {
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

function safeGetValue(elementId, defaultValue = '') {
    const element = safeGetElement(elementId);
    return element?.value?.trim() || defaultValue;
}

//사이트 이름 추출 함수
function extractSiteName(rawInput) {
    // 1) 전처리: 소문자화 + 앞뒤 공백 제거
    const inputLower = (rawInput || '').toLowerCase().trim();

    try {
        // 2) 빈 문자열 처리
        if (!inputLower) return 'Unknown';
        
        // 3) URL 아닌 경우(스킴도 없고, 최소한의 도메인 패턴(.)도 없으면)
        if (!inputLower.includes('://') && !inputLower.includes('.')) {
            return inputLower;
        }
        
        // 4) URL 객체 생성: 스킴이 없으면 https:// 자동 추가
        const normalizedUrl = inputLower.startsWith('http') 
            ? inputLower 
            : 'https://' + inputLower;
        const urlObj = new URL(normalizedUrl);
        
        // 5) 호스트네임 추출 (이미 소문자)
        let hostname = urlObj.hostname
            // www. or m. or mobile. 제거
            .replace(/^(www\.|m\.|mobile\.)/, '');
        
        // 6) 메인 도메인 추출 로직 개선
        const domainParts = hostname.split('.');
        let siteName = '';
        
        if (domainParts.length >= 2) {
            // 알려진 서브도메인 패턴 처리
            const knownSubdomains = [
                'boards', 'news', 'sport', 'sports', 'blog', 'shop', 'store', 
                'mail', 'maps', 'docs', 'drive', 'photos', 'translate',
                'play', 'music', 'video', 'tv', 'radio', 'podcast',
                'support', 'help', 'forum', 'community', 'wiki',
                'api', 'cdn', 'static', 'assets', 'img', 'images',
                'old', 'new', 'beta', 'test', 'dev', 'staging', 'kr'
            ];
            
            // 첫 번째 부분이 알려진 서브도메인이면서 전체 도메인이 3부분 이상인 경우
            if (domainParts.length >= 3 && knownSubdomains.includes(domainParts[0])) {
                // 두 번째 부분을 메인 도메인으로 사용
                siteName = domainParts[1];
            } else {
                // 그렇지 않으면 첫 번째 부분 사용
                siteName = domainParts[0];
            }
        } else {
            // 단일 도메인인 경우
            siteName = hostname;
        }
        
        // 7) 첫 글자만 대문자로 변환해서 반환
        return siteName.charAt(0).toUpperCase() + siteName.slice(1);
        
    } catch (error) {
        // URL 생성 실패 시 원본 전처리값 또는 Unknown
        return inputLower || 'Unknown';
    }
}

function validateSiteInput(site, boardValue, lang) {
    // 단순화된 검증 - 백엔드에서 상세 검증 처리
    switch (site) {
        case 'universal':
            return {
                isValid: boardValue.length > 0,
                message: ''
            };
            
        case 'lemmy':
            return {
                isValid: boardValue.length > 0,
                message: ''
            };
            
        case 'reddit':
            return {
                isValid: boardValue.length > 0,
                message: ''
            };
            
        default:
            return {
                isValid: boardValue.length > 0,
                message: ''
            };
    }
}

function enableDownloadButtons() {
    const downloadBtn = document.getElementById('downloadBtn');
    const downloadMediaBtn = document.getElementById('downloadMediaBtn');
    
    if (downloadBtn) {
        downloadBtn.style.display = 'inline-flex';
        downloadBtn.disabled = false;
    }
    // 크롤링 결과가 있으면 미디어 버튼 항상 표시
    if (downloadMediaBtn) {
        downloadMediaBtn.style.display = 'inline-flex';
        downloadMediaBtn.disabled = false;
        console.log(`🎯 미디어 다운로드 버튼 표시 (사이트: ${currentSite})`);
    }
}

function detectContentLanguage() {
    const siteLanguageMap = {
        'reddit': 'en',
        'lemmy': 'en', 
        'bbc': 'en',
        '4chan': 'en',
        'dcinside': 'ko',
        'blind': 'ko'
    };
    
    if (currentSite === 'universal') {
        const boardInput = document.getElementById('boardInput')?.value || '';
        if (boardInput.includes('.kr') || boardInput.includes('korean') || boardInput.includes('한국')) {
            return 'ko';
        }
        if (boardInput.includes('.jp') || boardInput.includes('japanese') || boardInput.includes('日本')) {
            return 'ja';
        }
        return 'en';
    }
    
    return siteLanguageMap[currentSite] || 'en';
}

function getSelectedLanguages() {
    const languageCheckboxes = document.querySelectorAll('input[name="target_languages"]:checked');
    if (languageCheckboxes.length > 0) {
        return Array.from(languageCheckboxes).map(cb => cb.value);
    }
    
    const detectedLanguage = detectContentLanguage();
    console.log(`🎯 감지된 언어: ${detectedLanguage}, 현재 UI 언어: ${currentLanguage}`);
    
    if (detectedLanguage === currentLanguage) {
        console.log(`🚫 번역 안함: 언어가 동일함 (${detectedLanguage} === ${currentLanguage})`);
        return []; 
    }
    
    console.log(`✅ 번역 진행: ${detectedLanguage} → ${currentLanguage}`);
    return [currentLanguage];
}

function getSelectedRange() {
    const isAdvanced = document.getElementById('advancedSearch')?.checked;
    return {
        start: parseInt(document.getElementById(isAdvanced ? 'startRankAdv' : 'startRank')?.value || '1'),
        end: parseInt(document.getElementById(isAdvanced ? 'endRankAdv' : 'endRank')?.value || '20')
    };
}

function initializeGlobalVariables() {
    if (typeof window.community_name === 'undefined') {
        window.community_name = '';
    }
    if (typeof window.lemmy_instance === 'undefined') {
        window.lemmy_instance = '';
    }
    
    if (typeof window.languages === 'undefined') {
        console.error('언어팩이 로드되지 않았습니다');
        window.languages = { en: { start: 'Start Crawling' } };
    }
}

// getLocalizedMessage 함수 추가
function getLocalizedMessage(key, variables = {}) {
    const lang = window.languages?.[currentLanguage] || window.languages?.en || {};
    
    // 키를 dot notation으로 처리
    const keys = key.split('.');
    let message = lang;
    
    for (const k of keys) {
        message = message?.[k];
        if (!message) break;
    }
    
    if (!message) {
        console.warn(`번역 키를 찾을 수 없음: ${key}`);
        return key;
    }
    
    // 변수 치환
    let result = message;
    Object.keys(variables).forEach(varKey => {
        result = result.replace(`{${varKey}}`, variables[varKey]);
    });
    
    return result;
}

// ==================== 전역 함수 노출 ====================
// HTML onclick 함수들을 전역으로 노출 (호환성 유지)

// 사이트 관련
window.handleSiteSearch = handleSiteSearch;
window.clearSiteInput = clearSiteInput;
window.clearBoardInput = clearBoardInput;

// 크롤링 관련
window.startCrawling = startCrawling;
window.cancelCrawling = cancelCrawling;
window.goBack = goBack;
window.toggleAdvancedSearch = toggleAdvancedSearch;

// 모달 관련 (호환성 래퍼)
window.openBugReportModal = openBugReportModal;
window.closeBugReportModal = closeBugReportModal;
window.openTermsModal = openTermsModal;
window.closeTermsModal = closeTermsModal;
window.openPrivacyModal = openPrivacyModal;
window.closePrivacyModal = closePrivacyModal;
window.openBusinessModal = openBusinessModal;
window.closeBusinessModal = closeBusinessModal;
window.openShortcutModal = openShortcutModal;
window.closeShortcutModal = closeShortcutModal;

// 피드백 관련 (호환성 래퍼)
window.updateCharacterCount = updateCharacterCount;
window.updateBugReportButton = updateBugReportButton;
window.handleFileUpload = handleFileUpload;
window.removeFile = removeFile;

// 바로가기 관련
window.useShortcut = useShortcut;
window.removeShortcut = removeShortcut;
window.saveShortcut = saveShortcut;

// 언어 관련
window.toggleLanguageDropdown = toggleLanguageDropdown;
window.selectLanguage = selectLanguage;

// 자동완성 관련
window.selectBBCSection = selectBBCSection;
window.setLemmyCommunity = setLemmyCommunity;
window.selectAutocompleteItem = selectAutocompleteItem;
window.selectSiteAutocompleteItem = selectSiteAutocompleteItem;

// 기타
window.selectSite = selectSite;
window.displayResults = displayResults;
window.enableDownloadButtons = enableDownloadButtons;
window.showMessage = showMessage;

// ==================== 전역 변수들을 다른 파일에서 접근 가능하게 노출 ====================
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
    updateLabels,
    
    // 바로가기 배열 (modal.js에서 접근)
    getShortcuts: () => shortcuts,
    setShortcuts: (newShortcuts) => shortcuts = newShortcuts
};

console.log('✅ Universal → AutoCrawler 수정 완료된 main.js 로드 완료');