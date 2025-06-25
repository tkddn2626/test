// 피드백 전송 함수
async function sendBugReportToServer(bugReport) {
    try {
        console.log('📡 피드백 전송 시작:', {
            description: bugReport.description?.substring(0, 50) + '...',
            hasFile: bugReport.hasFile,
            language: bugReport.currentLanguage
        });
        
        // 🔥 수정: API URL 동적 가져오기
        const API_BASE_URL = window.PickPostGlobals?.API_BASE_URL || 'http://localhost:8000';
        
        const response = await fetch(`${API_BASE_URL}/api/feedback`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(bugReport)
        });
        
        const result = await response.json();
        
        if (response.ok) {
            console.log('✅ 피드백 전송 성공:', result);
            
            // 🔥 수정: 메시지 번역 사용
            const lang = window.languages[window.PickPostGlobals?.getCurrentLanguage() || 'ko'];
            const successMsg = lang.messages?.feedback?.success || 
                             `피드백이 전송되었습니다! (ID: ${result.feedback_id})`;
            
            window.PickPostGlobals?.showTemporaryMessage(successMsg, 'success');
        } else {
            console.warn('⚠️ 피드백 전송 실패:', response.status, result);
            
            const errorMsg = result.error || `서버 오류 (${response.status})`;
            window.PickPostGlobals?.showTemporaryMessage(`피드백 전송 실패: ${errorMsg}`, 'error');
            
            saveBugReportLocally(bugReport);
        }
        
    } catch (error) {
        console.error('❌ 피드백 전송 오류:', error);
        
        const lang = window.languages[window.PickPostGlobals?.getCurrentLanguage() || 'ko'];
        
        if (error.name === 'TypeError' && error.message.includes('fetch')) {
            const msg = lang.messages?.feedback?.network_error || 
                       '네트워크 연결을 확인해주세요. 피드백이 로컬에 저장되었습니다.';
            window.PickPostGlobals?.showTemporaryMessage(msg, 'error');
        } else {
            const msg = lang.messages?.feedback?.send_error || 
                       `전송 오류: ${error.message}. 피드백이 로컬에 저장되었습니다.`;
            window.PickPostGlobals?.showTemporaryMessage(msg, 'error');
        }
        
        saveBugReportLocally(bugReport);
    }
}

// 피드백 제출 함수
function submitBugReport() {
    const description = document.getElementById('bugReportDescription').value.trim();
    const fileInput = document.getElementById('fileInput');
    const hasFile = fileInput.files.length > 0;
    
    // 🔥 수정: 언어 객체 올바른 참조
    const lang = window.languages[window.PickPostGlobals?.getCurrentLanguage() || 'ko'];
    
    // 입력 검증
    if (!description) {
        const msg = lang.messages?.feedback?.required || '피드백 내용을 입력해주세요.';
        window.PickPostGlobals?.showTemporaryMessage(msg, 'error');
        document.getElementById('bugReportDescription').focus();
        return;
    }
    
    if (description.length < 10) {
        window.PickPostGlobals?.showTemporaryMessage('피드백은 최소 10자 이상 입력해주세요.', 'error');
        document.getElementById('bugReportDescription').focus();
        return;
    }
    
    if (description.length > 1000) {
        window.PickPostGlobals?.showTemporaryMessage('피드백은 최대 1000자까지 입력 가능합니다.', 'error');
        return;
    }
    
    // 로딩 상태
    const submitBtn = document.getElementById('bugReportSubmitBtn');
    const originalText = submitBtn.textContent;
    submitBtn.disabled = true;
    
    const sendingText = lang.messages?.feedback?.sending || '전송 중...';
    submitBtn.textContent = sendingText;
    
    // 🔥 수정: 시스템 정보 수집
    const systemInfo = {
        userAgent: navigator.userAgent,
        language: navigator.language,
        languages: navigator.languages,
        platform: navigator.platform,
        cookieEnabled: navigator.cookieEnabled,
        onLine: navigator.onLine,
        screenResolution: `${screen.width}x${screen.height}`,
        viewportSize: `${window.innerWidth}x${window.innerHeight}`,
        colorDepth: screen.colorDepth,
        pixelDepth: screen.pixelDepth,
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
        timestamp: new Date().toISOString()
    };
    
    // 🔥 수정: 전역 변수 안전하게 참조
    const bugReport = {
        description: description,
        hasFile: hasFile,
        fileName: hasFile ? fileInput.files[0].name : null,
        fileSize: hasFile ? fileInput.files[0].size : null,
        systemInfo: systemInfo,
        currentLanguage: window.PickPostGlobals?.getCurrentLanguage() || 'ko',
        currentSite: window.PickPostGlobals?.getCurrentSite() || null,
        url: window.location.href,
        timestamp: new Date().toISOString(),
        
        // 추가 컨텍스트
        pageContext: {
            isLoading: window.PickPostGlobals?.getIsLoading() || false
        }
    };
    
    // 성공 처리
    setTimeout(() => {
        const successMsg = lang.messages?.feedback?.success || 
                          '피드백이 전송되었습니다. 소중한 의견 감사합니다! 🙏';
        
        // 모달 닫기 (전역 함수 사용)
        if (window.closeBugReportModal) {
            window.closeBugReportModal();
        }
        
        // 버튼 상태 복구
        submitBtn.disabled = false;
        submitBtn.textContent = originalText;
        
    }, 1000);
    
    // 실제 전송
    sendBugReportToServer(bugReport);
}

// 로컬 저장 함수
function saveBugReportLocally(bugReport) {
    try {
        const localData = {
            ...bugReport,
            localSavedAt: new Date().toISOString(),
            status: 'pending_upload'
        };
        
        console.log('💾 로컬 저장:', localData);
        
        try {
            const saved = JSON.parse(localStorage.getItem('pending_feedback') || '[]');
            saved.push(localData);
            
            if (saved.length > 10) {
                saved.splice(0, saved.length - 10);
            }
            
            localStorage.setItem('pending_feedback', JSON.stringify(saved));
            console.log('💾 localStorage에 백업 저장됨');
            
        } catch (storageError) {
            console.warn('localStorage 저장 실패:', storageError);
        }
        
    } catch (error) {
        console.error('로컬 저장 실패:', error);
    }
}

// main.js에서 호출하도록 수정

// 대기 중인 피드백 재전송 함수
async function retryPendingFeedback() {
    try {
        const pending = JSON.parse(localStorage.getItem('pending_feedback') || '[]');
        
        if (pending.length > 0) {
            console.log(`📤 대기 중인 피드백 ${pending.length}개 발견, 재전송 시도 중...`);
            
            const API_BASE_URL = window.PickPostGlobals?.API_BASE_URL || 'http://localhost:8000';
            
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
                    }
                    
                } catch (error) {
                    console.log('❌ 대기 피드백 재전송 실패:', error.message);
                    break;
                }
            }
            
            localStorage.setItem('pending_feedback', JSON.stringify(pending));
            
            if (pending.length === 0) {
                console.log('✅ 모든 대기 피드백 전송 완료');
            }
        }
        
    } catch (error) {
        console.warn('대기 피드백 처리 오류:', error);
    }
}

//페이지 로드 시 대기 중인 피드백 재전송 시도
function initializeFeedbackSystem() {
    retryPendingFeedback();
    console.log('📝 개선된 피드백 시스템 초기화 완료');
}

console.log('📝 개선된 피드백 시스템 초기화 완료');

window.submitFeedback = async function(message) {
    const response = await fetch("/api/feedback", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message })
    });

    return response.json();
}

// 🔥 전역 함수로 노출
window.submitBugReport = submitBugReport;
window.sendBugReportToServer = sendBugReportToServer;
window.initializeFeedbackSystem = initializeFeedbackSystem;

// 🔥 간단한 피드백 함수 (호환성)
window.submitFeedback = async function(message) {
    const API_BASE_URL = window.PickPostGlobals?.API_BASE_URL || 'http://localhost:8000';
    
    const response = await fetch(`${API_BASE_URL}/api/feedback`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message })
    });

    return response.json();
};

// main.js에서 호출할 수 있도록
window.addEventListener('PickPostReady', initializeFeedbackSystem);