// ==================== 공지사항 관리 시스템 ====================
// 공지사항 데이터와 관련 기능을 전담하는 모듈

// 공지사항 데이터 (실제로는 API에서 가져올 수 있음)
const announcements = [
    {
        id: 1,
        date: '2025-06-11',
        title: 'PickPost 서비스 오픈!',
        content: 'Reddit, BBC, Lemmy 등 다양한 플랫폼의 콘텐츠를 크롤링할 수 있는 PickPost가 오픈했습니다.',
        isNew: true,
        category: 'notice',
        priority: 'high'
    },

];

// 공지사항 상태 관리
let readAnnouncements = JSON.parse(localStorage.getItem('pickpost_read_announcements') || '[]');
let lastAnnouncementCheck = localStorage.getItem('pickpost_last_announcement_check') || '2025-06-01';

// ==================== 공지사항 모달 관리 ====================

/**
 * 공지사항 모달을 여는 함수
 */
function openAnnouncementModal() {
    const modal = document.getElementById('announcementModal');
    const lang = window.languages[window.PickPostGlobals?.getCurrentLanguage() || 'ko'];
    
    // 제목 번역
    const titleElement = document.getElementById('announcementTitle');
    if (titleElement) {
        titleElement.textContent = lang.announcementTitle || '📢 공지사항';
    }
    
    // 닫기 버튼 번역
    const closeBtn = document.getElementById('announcementCloseBtn');
    if (closeBtn) {
        closeBtn.textContent = lang.ok || '확인';
    }
    
    // 공지사항 목록 생성
    loadAnnouncements();
    
    modal.classList.add('show');
    
    // 새 공지 뱃지 숨기기 및 읽음 상태 업데이트
    markAllAnnouncementsAsRead();
    
    // 키보드 트랩 설정 (접근성)
    setupAnnouncementModalKeyboardTrap(modal);
}

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
    
    // 공지사항을 날짜순으로 정렬 (최신순)
    const sortedAnnouncements = [...announcements].sort((a, b) => new Date(b.date) - new Date(a.date));
    
    container.innerHTML = sortedAnnouncements.map(announcement => {
        const date = new Date(announcement.date).toLocaleDateString(
            currentLanguage === 'ko' ? 'ko-KR' : 
            currentLanguage === 'ja' ? 'ja-JP' : 'en-US'
        );
        
        // 카테고리 및 우선순위 번역
        const categoryText = lang.categories?.[announcement.category] || announcement.category;
        const priorityText = lang.priorities?.[announcement.priority] || announcement.priority;
        
        // 우선순위에 따른 스타일
        const priorityClass = announcement.priority === 'high' ? 'priority-high' : 
                            announcement.priority === 'low' ? 'priority-low' : 'priority-normal';
        
        // 카테고리에 따른 아이콘
        const categoryIcon = getCategoryIcon(announcement.category);
        
        return `
            <div class="announcement-item ${announcement.isNew ? 'new' : ''} ${priorityClass}">
                <div class="announcement-header">
                    <div class="announcement-meta">
                        <span class="announcement-date">${date}</span>
                        <div class="announcement-badges">
                            <span class="category-badge category-${announcement.category}">
                                ${categoryIcon} ${categoryText}
                            </span>
                            ${announcement.priority === 'high' ? `<span class="priority-badge">${priorityText}</span>` : ''}
                            ${announcement.isNew ? `<span class="new-badge">${lang.newAnnouncement || '새 공지'}</span>` : ''}
                        </div>
                    </div>
                </div>
                <div class="announcement-content">
                    <h3 class="announcement-title">${announcement.title}</h3>
                    <p class="announcement-text">${announcement.content}</p>
                </div>
            </div>
        `;
    }).join('');
    
    // 애니메이션 효과
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

// ==================== 초기화 ====================

/**
 * 공지사항 시스템을 초기화하는 함수
 */
function initializeAnnouncementSystem() {
    // 페이지 로드 시 새 공지사항 확인
    checkNewAnnouncements();
    
    // 주기적으로 새 공지사항 확인 (옵션)
    setInterval(checkNewAnnouncements, 5 * 60 * 1000); // 5분마다
    
    console.log('공지사항 시스템이 초기화되었습니다.');
}

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

// ===================================
// 관리자용 공지사항 추가 예시
// ===================================

/*
// 콘솔에서 새 공지사항 추가하는 방법:
window.announcementManager.addAnnouncement({
    priority: 'high', // 'high', 'normal', 'low'
    category: 'maintenance', // 'update', 'maintenance', 'feature', 'notice', 'security'
    translations: {
        ko: {
            title: '⚠️ 긴급 점검 안내',
            content: `
                <p>서버 점검으로 인해 일시적으로 서비스가 중단됩니다.</p>
                <ul>
                    <li><strong>점검 시간</strong>: 2025-06-13 02:00 ~ 04:00 (2시간)</li>
                    <li><strong>영향 범위</strong>: 모든 크롤링 기능</li>
                </ul>
                <p>이용에 불편을 드려 죄송합니다.</p>
            `
        },
        en: {
            title: '⚠️ Emergency Maintenance Notice',
            content: `
                <p>Service will be temporarily unavailable due to server maintenance.</p>
                <ul>
                    <li><strong>Maintenance Time</strong>: 2025-06-13 02:00 ~ 04:00 (2 hours)</li>
                    <li><strong>Affected Services</strong>: All crawling functions</li>
                </ul>
                <p>We apologize for any inconvenience.</p>
            `
        },
        ja: {
            title: '⚠️ 緊急メンテナンス案内',
            content: `
                <p>サーバーメンテナンスにより一時的にサービスが中断されます。</p>
                <ul>
                    <li><strong>メンテナンス時間</strong>: 2025-06-13 02:00 ~ 04:00 (2時間)</li>
                    <li><strong>影響範囲</strong>: すべてのクロール機能</li>
                </ul>
                <p>ご不便をおかけして申し訳ございません。</p>
            `
        }
    }
});
*/