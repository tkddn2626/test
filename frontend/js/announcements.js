// ==================== 공지사항 관리 시스템 ====================
// 공지사항 데이터와 관련 기능을 전담하는 모듈

// 공지사항 데이터 동적 로드
let announcements = [];

/**
 * announcements 폴더에서 파일들을 동적으로 로드하는 함수
 */
async function loadAnnouncementFiles() {
    try {
        const currentLanguage = window.PickPostGlobals?.getCurrentLanguage() || 'en';
        const loadedAnnouncements = [];
        let consecutiveNotFound = 0; // 연속으로 찾지 못한 파일 개수
        const MAX_CONSECUTIVE_NOT_FOUND = 3; // 연속으로 3개 파일이 없으면 중단
        
        // 1부터 순차적으로 시도하되, 연속으로 파일이 없으면 조기 중단
        for (let i = 1; i <= 50; i++) {
            const filePath = `js/announcements/announcement-${i}.js`;
            
            try {
                const response = await fetch(filePath);
                if (response.ok) {
                    // 파일을 찾았으므로 카운터 리셋
                    consecutiveNotFound = 0;
                    
                    const text = await response.text();
                    
                    // JavaScript 파일을 eval로 실행하여 데이터 추출
                    let announcementData;
                    eval(text); // 파일에서 announcementData 변수를 설정
                    
                    if (announcementData) {
                        // 현재 언어에 맞는 데이터 추출
                        const translation = announcementData.translations[currentLanguage] || 
                                          announcementData.translations['ko'] || 
                                          announcementData.translations['en'];
                        
                        if (translation) {
                            loadedAnnouncements.push({
                                id: announcementData.id,
                                date: announcementData.date,
                                title: translation.title,
                                content: translation.content,
                                isNew: announcementData.isNew,
                                category: announcementData.category,
                                priority: announcementData.priority
                            });
                        }
                    }
                } else if (response.status === 404) {
                    // 404면 연속 카운터 증가
                    consecutiveNotFound++;
                    
                    // 연속으로 MAX_CONSECUTIVE_NOT_FOUND개 파일이 없으면 중단
                    if (consecutiveNotFound >= MAX_CONSECUTIVE_NOT_FOUND) {
                        console.log(`공지사항 로드 중단: 연속으로 ${MAX_CONSECUTIVE_NOT_FOUND}개 파일이 없음 (${i-MAX_CONSECUTIVE_NOT_FOUND}번부터 ${i-1}번까지)`);
                        break;
                    }
                } else {
                    // 다른 HTTP 오류 (403, 500 등)도 연속 카운터 증가
                    consecutiveNotFound++;
                    
                    if (consecutiveNotFound >= MAX_CONSECUTIVE_NOT_FOUND) {
                        console.log(`공지사항 로드 중단: 연속으로 ${MAX_CONSECUTIVE_NOT_FOUND}개 파일에 오류 발생`);
                        break;
                    }
                }
            } catch (error) {
                // 네트워크 오류나 기타 오류
                consecutiveNotFound++;
                
                // 네트워크 오류가 연속으로 발생해도 중단
                if (consecutiveNotFound >= MAX_CONSECUTIVE_NOT_FOUND) {
                    console.log(`공지사항 로드 중단: 연속으로 ${MAX_CONSECUTIVE_NOT_FOUND}개 파일에서 네트워크 오류`);
                    break;
                }
            }
        }
        
        announcements = loadedAnnouncements;
        
        console.log(`공지사항 로드 완료 (${currentLanguage}): ${announcements.length}개`);
        
    } catch (error) {
        console.error('공지사항 파일 로드 중 오류:', error);
        
        // 파일이 없으면 빈 배열 사용
        announcements = [];
    }
}

// 공지사항 상태 관리
let readAnnouncements = JSON.parse(localStorage.getItem('pickpost_read_announcements') || '[]');
let lastAnnouncementCheck = localStorage.getItem('pickpost_last_announcement_check') || '2025-06-01';

// ==================== 공지사항 모달 관리 ====================

/**
 * 공지사항 모달을 여는 함수
 */
async function openAnnouncementModal() {
    const modal = document.getElementById('announcementModal');
    const lang = window.languages[currentLanguage] || window.languages.en;
    
    // 모달 제목 번역
    const titleElement = document.getElementById('announcementTitle');
    if (titleElement) {
        titleElement.textContent = `📢 ${lang.announcementTitle || 'Announcements'}`;
    }
    
    // 버튼 텍스트 번역
    const closeBtn = document.getElementById('announcementCloseBtn');
    if (closeBtn) {
        closeBtn.textContent = lang.ok || 'OK';
    }
    
    // 공지사항 버튼 텍스트도 업데이트
    const announcementBtn = document.getElementById('announcementBtn');
    const announcementBtnText = document.getElementById('announcementBtnText');
    if (announcementBtnText) {
        announcementBtnText.textContent = lang.announcementBtnText || 'Announcements';
    }
    
    // 공지사항 파일들을 먼저 로드
    await loadAnnouncementFiles();
    
    // ✅ 추가: 공지사항 내용 로드
    loadAnnouncements();
    
    modal.classList.add('show');
    
    // ✅ 추가: 키보드 트랩 설정 (ESC 키 지원)
    setupAnnouncementModalKeyboardTrap(modal);
    
    // 모든 공지사항을 읽음 처리
    markAllAnnouncementsAsRead();
}

/**
 * 공지사항 시스템을 초기화하는 함수
 */
async function initializeAnnouncementSystem() {
    // 초기화 시 공지사항 파일들 로드
    await loadAnnouncementFiles();
    
    // 페이지 로드 시 새 공지사항 확인
    checkNewAnnouncements();
    
    // 주기적으로 새 공지사항 확인 (옵션)
    setInterval(checkNewAnnouncements, 5 * 60 * 1000); // 5분마다
    
    console.log('공지사항 시스템이 초기화되었습니다.');
}

// (기존 함수들은 그대로 유지)

/**
 * 공지사항 모달을 닫는 함수
 */
function closeAnnouncementModal() {
    const modal = document.getElementById('announcementModal');
    modal.classList.remove('show');
}

/**
 * 공지사항 목록을 로드하고 표시하는 함수
 */
function loadAnnouncements() {
    const container = document.getElementById('announcementList');
    const currentLanguage = window.PickPostGlobals?.getCurrentLanguage() || 'ko';
    const lang = window.languages[currentLanguage];
    
    if (!container) {
        console.error('announcementList 요소를 찾을 수 없습니다');
        return;
    }
    
    // 공지사항을 우선순위와 날짜 순으로 정렬
    // 중요 공지사항(priority: 'high')을 최상단에 고정
    const sortedAnnouncements = [...announcements].sort((a, b) => {
        // 중요 공지사항을 최상단에 고정
        if (a.priority === 'high' && b.priority !== 'high') return -1;
        if (b.priority === 'high' && a.priority !== 'high') return 1;
        // 그 다음은 날짜순 (최신순)
        return new Date(b.date) - new Date(a.date);
    });
    
    // 간단하고 깔끔한 HTML 구조로 변경
    container.innerHTML = sortedAnnouncements.map(announcement => {
        const date = new Date(announcement.date).toLocaleDateString(
            currentLanguage === 'ko' ? 'ko-KR' : 
            currentLanguage === 'ja' ? 'ja-JP' : 'en-US'
        );
        
        // 카테고리 번역
        const categoryText = lang?.categories?.[announcement.category] || announcement.category;
        
        // 중요 공지사항인지 확인
        const isImportant = announcement.priority === 'high';
        
        // 카테고리 아이콘
        const categoryIcon = getCategoryIcon(announcement.category);
        
        return `
            <div class="announcement-item ${announcement.isNew ? 'new' : ''} ${isImportant ? 'priority-high' : ''}">
                <div class="announcement-date">${date}</div>
                <div class="announcement-content">
                    <h3>${announcement.title}</h3>
                    <p>${announcement.content}</p>
                </div>
                ${announcement.category ? `
                    <div class="announcement-badges">
                        <span class="category-badge category-${announcement.category}">
                            ${categoryIcon} ${categoryText}
                        </span>
                    </div>
                ` : ''}
            </div>
        `;
    }).join('');
    
    // 애니메이션 효과 적용
    animateAnnouncementItems();
}


/**
 * 카테고리에 따른 아이콘을 반환하는 함수
 */
function getCategoryIcon(category) {
    const icons = {
        update: '🔄',
        maintenance: '🔧',
        feature: '✨',
        notice: '📢',
        security: '🔒'
    };
    return icons[category] || '📋';
}

/**
 * 공지사항 아이템에 애니메이션 효과를 적용하는 함수
 */
function animateAnnouncementItems() {
    const items = document.querySelectorAll('.announcement-item');
    items.forEach((item, index) => {
        item.style.opacity = '0';
        item.style.transform = 'translateY(20px)';
        
        setTimeout(() => {
            item.style.transition = 'all 0.3s ease';
            item.style.opacity = '1';
            item.style.transform = 'translateY(0)';
        }, index * 100);
    });
}

// ==================== 새 공지사항 확인 및 알림 ====================

/**
 * 새 공지사항이 있는지 확인하는 함수
 */
function checkNewAnnouncements() {
    const badge = document.getElementById('announcementBadge');
    const currentLanguage = window.PickPostGlobals?.getCurrentLanguage() || 'en';
    const lang = window.languages?.[currentLanguage] || window.languages.en;

    if (!badge) {
        console.warn('announcementBadge 요소가 없습니다.');
        return;
    }

    const hasNewAnnouncements = announcements.some(announcement => 
        announcement.isNew && !readAnnouncements.includes(announcement.id)
    );

    const latestAnnouncementDate = Math.max(...announcements.map(a => new Date(a.date).getTime()));
    const lastCheckDate = new Date(lastAnnouncementCheck).getTime();
    const hasRecentAnnouncements = latestAnnouncementDate > lastCheckDate;

    if (hasNewAnnouncements || hasRecentAnnouncements) {
        // 강제로 모든 스타일 적용
        badge.style.cssText = `
            display: inline-block !important;
            background: #ff8c00 !important;
            color: white !important;
            font-size: 10px !important;
            padding: 2px 6px !important;
            border-radius: 10px !important;
            font-weight: 600 !important;
            margin-left: 6px !important;
        `;
        badge.textContent = lang.newBadge || 'New';
        badge.classList.add('pulse-animation');
        
        console.log('🟢 뱃지 표시됨:', badge.style.display, badge.textContent);
    } else {
        badge.style.display = 'none';
        badge.classList.remove('pulse-animation');
        console.log('🔴 뱃지 숨김');
    }
}

/**
 * 모든 공지사항을 읽음 처리하는 함수
 */
function markAllAnnouncementsAsRead() {
    const badge = document.getElementById('announcementBadge');
    
    // 모든 공지사항 ID를 읽음 목록에 추가
    const allAnnouncementIds = announcements.map(a => a.id);
    readAnnouncements = [...new Set([...readAnnouncements, ...allAnnouncementIds])];
    
    // 로컬 스토리지에 저장
    localStorage.setItem('pickpost_read_announcements', JSON.stringify(readAnnouncements));
    localStorage.setItem('pickpost_last_announcement_check', new Date().toISOString().split('T')[0]);
    
    // 뱃지 숨기기
    if (badge) {
        badge.style.display = 'none';
        badge.classList.remove('pulse-animation');
    }
}

/**
 * 특정 공지사항을 읽음 처리하는 함수
 */
function markAnnouncementAsRead(announcementId) {
    if (!readAnnouncements.includes(announcementId)) {
        readAnnouncements.push(announcementId);
        localStorage.setItem('pickpost_read_announcements', JSON.stringify(readAnnouncements));
    }
    
    // 읽지 않은 공지사항이 없으면 뱃지 숨기기
    checkNewAnnouncements();
}

// ==================== API 연동 기능 ====================

/**
 * 서버에서 공지사항을 가져오는 함수 (향후 구현)
 */
async function fetchAnnouncementsFromAPI() {
    try {
        const API_BASE_URL = window.PickPostGlobals?.API_BASE_URL;
        if (!API_BASE_URL) {
            console.warn('API_BASE_URL이 설정되지 않았습니다. 로컬 데이터를 사용합니다.');
            return announcements;
        }
        
        const response = await fetch(`${API_BASE_URL}/api/announcements`);
        if (response.ok) {
            const data = await response.json();
            return data.announcements || announcements;
        } else {
            console.warn('공지사항 API 호출 실패:', response.status);
            return announcements;
        }
    } catch (error) {
        console.error('공지사항 로드 중 오류:', error);
        return announcements;
    }
}

/**
 * 공지사항 조회 통계를 서버에 전송하는 함수 (향후 구현)
 */
async function sendAnnouncementView(announcementId) {
    try {
        const API_BASE_URL = window.PickPostGlobals?.API_BASE_URL;
        if (!API_BASE_URL) return;
        
        await fetch(`${API_BASE_URL}/api/announcements/${announcementId}/view`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                timestamp: new Date().toISOString(),
                userAgent: navigator.userAgent
            })
        });
    } catch (error) {
        console.error('공지사항 조회 통계 전송 실패:', error);
    }
}

// ==================== 접근성 및 키보드 지원 ====================

/**
 * 공지사항 모달에서 키보드 트랩을 설정하는 함수 (접근성)
 */
function setupAnnouncementModalKeyboardTrap(modal) {
    const focusableElements = modal.querySelectorAll(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );
    const firstFocusableElement = focusableElements[0];
    const lastFocusableElement = focusableElements[focusableElements.length - 1];

    // 기존 이벤트 리스너 제거
    modal.removeEventListener('keydown', handleAnnouncementModalKeydown);
    
    // 새 이벤트 리스너 추가
    modal.addEventListener('keydown', handleAnnouncementModalKeydown);

    function handleAnnouncementModalKeydown(e) {
        if (e.key === 'Escape') {
            closeAnnouncementModal();
            return;
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
    }
}

// ==================== 유틸리티 함수 ====================

/**
 * 공지사항 데이터를 날짜별로 그룹화하는 함수
 */
function groupAnnouncementsByDate() {
    const grouped = {};
    announcements.forEach(announcement => {
        const date = announcement.date;
        if (!grouped[date]) {
            grouped[date] = [];
        }
        grouped[date].push(announcement);
    });
    return grouped;
}

/**
 * 특정 카테고리의 공지사항만 필터링하는 함수
 */
function filterAnnouncementsByCategory(category) {
    return announcements.filter(announcement => announcement.category === category);
}

/**
 * 읽지 않은 공지사항만 반환하는 함수
 */
function getUnreadAnnouncements() {
    return announcements.filter(announcement => 
        !readAnnouncements.includes(announcement.id)
    );
}

/**
 * 공지사항 검색 함수
 */
function searchAnnouncements(query) {
    const lowercaseQuery = query.toLowerCase();
    return announcements.filter(announcement =>
        announcement.title.toLowerCase().includes(lowercaseQuery) ||
        announcement.content.toLowerCase().includes(lowercaseQuery)
    );
}

// announcements.js에 추가
function resetAnnouncementReadStatusImmediate() {
    localStorage.removeItem('pickpost_read_announcements');
    localStorage.removeItem('pickpost_last_announcement_check');
    
    // 전역 변수 즉시 초기화
    readAnnouncements = [];
    lastAnnouncementCheck = '2025-06-01';
    
    // 뱃지 상태 즉시 업데이트
    checkNewAnnouncements();
}

// 전역으로 노출
window.resetAnnouncementReadStatusImmediate = resetAnnouncementReadStatusImmediate;

// ==================== 전역 함수 노출 ====================

// HTML에서 직접 호출할 수 있도록 전역으로 노출
window.openAnnouncementModal = openAnnouncementModal;
window.closeAnnouncementModal = closeAnnouncementModal;
window.checkNewAnnouncements = checkNewAnnouncements;
window.markAnnouncementAsRead = markAnnouncementAsRead;

// 다른 모듈에서 사용할 수 있도록 전역 객체에 추가
window.AnnouncementSystem = {
    openModal: openAnnouncementModal,
    closeModal: closeAnnouncementModal,
    checkNew: checkNewAnnouncements,
    markAsRead: markAnnouncementAsRead,
    markAllAsRead: markAllAnnouncementsAsRead,
    getUnread: getUnreadAnnouncements,
    search: searchAnnouncements,
    init: initializeAnnouncementSystem,
    announcements: announcements
};

// 페이지 로드 시 자동 초기화
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeAnnouncementSystem);
} else {
    initializeAnnouncementSystem();
}