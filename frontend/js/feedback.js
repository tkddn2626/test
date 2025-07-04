// 피드백 전송 함수
async function sendBugReportToServer(bugReport) {
    try {
        console.log('📡 피드백 전송 시작:', {
            description: bugReport.description?.substring(0, 50) + '...',
            hasFile: bugReport.hasFile,
            language: bugReport.currentLanguage
        });
        
        // API URL 동적 가져오기
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
        } else {
            console.warn('⚠️ 피드백 전송 실패:', response.status, result);
            
            const errorMsg = result.error || `서버 오류 (${response.status})`;
            window.PickPostGlobals?.showMessage(`피드백 전송 실패: ${errorMsg}`, 'error');
            
            saveBugReportLocally(bugReport);
        }
        
    } catch (error) {
        console.error('❌ 피드백 전송 오류:', error);
        
        const lang = window.languages[window.PickPostGlobals?.getCurrentLanguage() || 'ko'];
        
        if (error.name === 'TypeError' && error.message.includes('fetch')) {
            const msg = lang.messages?.feedback?.network_error || 
                       '네트워크 연결을 확인해주세요. 피드백이 로컬에 저장되었습니다.';
            window.PickPostGlobals?.showMessage(msg, 'error');
        } else {
            const msg = lang.messages?.feedback?.send_error || 
                       `전송 오류: ${error.message}. 피드백이 로컬에 저장되었습니다.`;
            window.PickPostGlobals?.showMessage(msg, 'error');
        }
        
        saveBugReportLocally(bugReport);
    }
}

// 피드백 제출 함수 - 개선된 검증 및 중복 전송 방지
function submitBugReport() {
    const description = document.getElementById('bugReportDescription').value.trim();
    const fileInput = document.getElementById('fileInput');
    const hasFile = fileInput.files.length > 0;
    
    // 언어 객체 올바른 참조
    const lang = window.languages[window.PickPostGlobals?.getCurrentLanguage() || 'ko'];
    
    // 개선된 입력 검증 - 텍스트 또는 파일 중 하나만 있으면 OK
    if (!description && !hasFile) {
        const msg = lang.messages?.feedback?.required || '피드백 내용을 입력하거나 파일을 첨부해주세요.';
        window.PickPostGlobals?.showMessage(msg, 'error');
        if (!hasFile) {
            document.getElementById('bugReportDescription').focus();
        }
        return;
    }
    
    // 최대 길이 검증은 유지
    if (description.length > 1000) {
        window.PickPostGlobals?.showMessage('피드백은 최대 1000자까지 입력 가능합니다.', 'error');
        return;
    }
    
    // 중복 전송 방지 - 버튼 상태 확인
    const submitBtn = document.getElementById('bugReportSubmitBtn');
    if (submitBtn.disabled) {
        console.log('⚠️ 이미 전송 중이므로 중복 요청 무시');
        return;
    }
    
    // 로딩 상태 설정
    const originalText = submitBtn.textContent;
    submitBtn.disabled = true;
    
    const sendingText = lang.messages?.feedback?.sending || '전송 중...';
    submitBtn.textContent = sendingText;
    
    // 시스템 정보 수집
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
    
    // 전역 변수 안전하게 참조
    const bugReport = {
        description: description || '(파일만 첨부됨)', // 텍스트가 없으면 기본 메시지
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
    
    // 실제 전송 (성공 후 모달 닫기 로직 개선)
    sendBugReportToServer(bugReport)
        .then(() => {
        // 성공 메시지 표시
            const successMsg = lang.messages?.feedback?.success || 
                            '피드백이 전송되었습니다. 소중한 의견 감사합니다! 🙏';
            window.PickPostGlobals?.showMessage(successMsg, 'success');
            
            // 🔥 모달 닫기 전에 입력창 비우기 (확인창 방지)
            document.getElementById('bugReportDescription').value = '';
            
            // 모달 닫기
            if (window.closeBugReportModal) {
                window.closeBugReportModal();
            }
        })
        .catch((error) => {
            console.error('❌ 피드백 전송 실패:', error);
            // 오류 메시지는 sendBugReportToServer에서 처리
        })
        .finally(() => {
            // 버튼 상태 복구
            submitBtn.disabled = false;
            submitBtn.textContent = originalText;
        });
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

// 페이지 로드 시 대기 중인 피드백 재전송 시도
function initializeFeedbackSystem() {
    retryPendingFeedback();
    console.log('📝 개선된 피드백 시스템 초기화 완료');
}

// 🔥 유지되는 함수들 (내부 사용 또는 호환성 용도):
window.initializeFeedbackSystem = initializeFeedbackSystem;

// 간단한 피드백 함수 (호환성 - API 직접 호출용)
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

console.log('📝 개선된 피드백 시스템 로드 완료 (modal.js 통합 버전)');