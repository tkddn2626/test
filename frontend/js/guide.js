// ==================== 사용법 가이드 알림창 관리 (guide-notification.js) ====================
// PickPost 사용법 가이드를 사이드 알림창으로 표시하는 독립 모듈
// "하루 동안 안 보기" 기능 포함, 검색창을 가리지 않는 비침습적 디자인
// Version: 3.0 - 사이드 알림창으로 변경

class GuideNotificationManager {
    constructor() {
        this.notification = null;
        this.checkbox = null;
        this.storageKey = 'pickpost_guide_hidden_until';
        this.currentLanguage = 'en'; // 기본 언어
        this.content = this.getContent();
        // DOM 준비 후 초기화
    }

    // 다국어 컨텐츠 정의
    getContent() {
        return {
            en: {
                title: '📢 PickPost User Guide',
                subtitle: 'Follow the step-by-step guide below to start data crawling quickly and easily.',
                featureTitle: 'Feature Overview',
                features: [
                    '🤖 Supported Platforms: Reddit, BBC, Lemmy, and general website URLs',
                    '⚙️ Sort & Filter: Hot, Top, time period, views/upvotes criteria',
                    '📊 Real-time Progress: Live status display during crawling',
                    '📥 Excel Download: Includes titles, links, dates, statistics',
                    '🌐 Multi-language support with translation options'
                ],
                steps: [
                    {
                        title: '1. Platform & Site Input',
                        description: 'Enter the website address or name in the search box.'
                    },
                    {
                        title: '2. Board/Community Input',
                        description: 'Enter the specific community identifier such as Reddit subreddits, Lemmy instances, etc. in the detailed search field.'
                    },
                    {
                        title: '3. Filter & Options Setup',
                        description: 'Configure sort method, time period, minimum views/upvotes, date range to collect the data you want.'
                    },
                    {
                        title: '4. Execute & Monitor Crawling',
                        description: 'Click the start button to see real-time progress, and use the cancel button to stop anytime.'
                    },
                    {
                        title: '5. Download Results',
                        description: 'After crawling is complete, click the Excel download button to save your collected results.'
                    }
                ],
                checkboxText: "Don't show for 24 hours",
                confirmButton: 'Got it!'
            },
            ko: {
                title: '📢 PickPost 사용법 가이드',
                subtitle: '아래 단계별 안내를 따라 쉽고 빠르게 데이터 크롤링을 시작해 보세요.',
                featureTitle: '기능 요약',
                features: [
                    '🤖 지원 플랫폼: Reddit, BBC, Lemmy 및 게시판 URL',
                    '⚙️ 정렬·필터: Hot, Top, 기간, 조회수/추천수 기준 설정',
                    '📊 실시간 진행: 실시간 현황 표시',
                    '📥 엑셀 다운로드: 제목, 링크, 작성일, 통계 등 포함',
                    '🌐 다국어 지원 및 번역 옵션 제공'
                ],
                steps: [
                    {
                        title: '1. 플랫폼 및 게시판 입력',
                        description: '검색창에 사이트 주소 또는 이름을 입력하세요.'
                    },
                    {
                        title: '2. 게시판 입력',
                        description: 'Reddit 서브레딧, Lemmy의 인스턴스 등 각각의 커뮤니티 식별자를 세부 검색창에 입력합니다.'
                    },
                    {
                        title: '3. 필터 & 옵션 설정',
                        description: '정렬 방식, 기간, 최소 조회수/추천수, 날짜 범위 등을 설정하여 원하는 데이터를 수집할 수 있습니다.'
                    },
                    {
                        title: '4. 크롤링 실행 및 확인',
                        description: '시작 버튼 클릭 시 실시간 진행률이 표시되며, 취소 버튼으로 언제든 중단 가능합니다.'
                    },
                    {
                        title: '5. 결과 다운로드',
                        description: '수집 완료 후 엑셀 다운로드 버튼을 눌러, 수집된 결과를 저장하세요.'
                    }
                ],
                checkboxText: '하루 동안 안 보기',
                confirmButton: '알겠습니다!'
            },
            ja: {
                title: '📢 PickPost 使用ガイド',
                subtitle: '以下のステップバイステップガイドに従って、データクローリングを簡単かつ迅速に開始してください。',
                featureTitle: '機能概要',
                features: [
                    '🤖 対応プラットフォーム: Reddit、BBC、Lemmy、および一般的なウェブサイトURL',
                    '⚙️ ソート・フィルター: Hot、Top、期間、ビュー数/アップボート基準',
                    '📊 リアルタイム進行: クローリング中のライブステータス表示',
                    '📥 Excelダウンロード: タイトル、リンク、日付、統計を含む',
                    '🌐 多言語サポートと翻訳オプション'
                ],
                steps: [
                    {
                        title: '1. プラットフォーム・サイト入力',
                        description: '検索ボックスにウェブサイトのアドレスまたは名前を入力してください。'
                    },
                    {
                        title: '2. ボード・コミュニティ入力',
                        description: 'Redditサブレディット、Lemmyインスタンスなどの特定のコミュニティ識別子を詳細検索フィールドに入力します。'
                    },
                    {
                        title: '3. フィルター・オプション設定',
                        description: 'ソート方法、期間、最小ビュー数/アップボート、日付範囲を設定して、必要なデータを収集します。'
                    },
                    {
                        title: '4. クローリング実行・監視',
                        description: 'スタートボタンをクリックしてリアルタイム進行状況を確認し、キャンセルボタンでいつでも停止できます。'
                    },
                    {
                        title: '5. 結果ダウンロード',
                        description: 'クローリング完了後、Excelダウンロードボタンをクリックして収集した結果を保存してください。'
                    }
                ],
                checkboxText: '24時間表示しない',
                confirmButton: '了解しました！'
            }
        };
    }

    // 초기화 메서드 - DOM 준비 후에만 호출
    init() {
        this.createNotificationElement();
        this.detectCurrentLanguage();
        this.generateNotificationContent();
        this.setupEventListeners();
        this.checkShouldShowNotification();
        console.log('✅ GuideNotificationManager initialized');
        return true;
    }

    // 알림창 엘리먼트 동적 생성
    createNotificationElement() {
        // 기존 알림창이 있다면 제거
        const existing = document.getElementById('guideNotification');
        if (existing) {
            existing.remove();
        }

        // 새 알림창 생성
        this.notification = document.createElement('div');
        this.notification.id = 'guideNotification';
        this.notification.className = 'guide-notification';
        
        this.notification.innerHTML = `
            <div class="guide-notification-content">
                <div class="guide-notification-header">
                    <h3 class="guide-notification-title" id="guideNotificationTitle"></h3>
                    <button class="guide-notification-close" onclick="closeGuideNotification()" aria-label="Close notification">✕</button>
                </div>
                
                <div class="guide-notification-body">
                    <div id="guideNotificationContent">
                        <!-- 내용이 JavaScript에서 동적으로 생성됩니다 -->
                    </div>
                </div>
                
                <div class="guide-notification-footer">
                    <div class="guide-notification-footer-left">
                        <label class="guide-checkbox-container">
                            <input type="checkbox" id="dontShowToday" class="guide-checkbox">
                            <span class="guide-checkbox-checkmark"></span>
                            <span class="guide-checkbox-text" id="guideCheckboxText"></span>
                        </label>
                    </div>
                    <div class="guide-notification-footer-right">
                        <button class="guide-btn guide-btn-primary" id="guideNotificationConfirm" onclick="closeGuideNotification()"></button>
                    </div>
                </div>
            </div>
        `;

        // 스타일 추가
        this.addNotificationStyles();
        
        // body에 추가
        document.body.appendChild(this.notification);
        
        console.log('✅ Guide notification element created');
    }

    // 알림창 스타일 추가
    addNotificationStyles() {
        // 기존 스타일이 있다면 제거
        const existing = document.getElementById('guideNotificationStyles');
        if (existing) {
            existing.remove();
        }

        const style = document.createElement('style');
        style.id = 'guideNotificationStyles';
        style.textContent = `
            /* 가이드 알림창 스타일 */
            .guide-notification {
                position: fixed;
                top: 80px;
                left: 20px;
                width: 320px;
                max-width: calc(50vw - 40px);
                height: 400px;
                max-height: calc(100vh - 100px);
                background: white;
                border-radius: 12px;
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.15);
                z-index: 999;
                opacity: 0;
                transform: translateX(-100%);
                transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
                border: 1px solid #e8eaed;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                overflow: hidden;
                display: flex;
                flex-direction: column;
            }

            .guide-notification.show {
                opacity: 1;
                transform: translateX(0);
            }

            .guide-notification-content {
                display: flex;
                flex-direction: column;
                height: 100%;
            }

            .guide-notification-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 16px 20px 12px;
                border-bottom: 1px solid #f1f3f4;
                flex-shrink: 0;
            }

            .guide-notification-title {
                font-size: 18px;
                font-weight: 500;
                color: #202124;
                margin: 0;
                display: flex;
                align-items: center;
                gap: 8px;
            }

            .guide-notification-close {
                background: none;
                border: none;
                font-size: 16px;
                color: #5f6368;
                cursor: pointer;
                padding: 6px;
                border-radius: 50%;
                transition: all 0.2s ease;
                width: 28px;
                height: 28px;
                display: flex;
                align-items: center;
                justify-content: center;
                flex-shrink: 0;
            }

            .guide-notification-close:hover {
                background: #f1f3f4;
                color: #202124;
            }

            .guide-notification-body {
                padding: 16px 20px;
                overflow-y: scroll;
                flex: 1;
                line-height: 1.5;
                overscroll-behavior: contain;
                min-height: 0;
            }

            .guide-notification-body::-webkit-scrollbar {
                width: 6px;
            }

            .guide-notification-body::-webkit-scrollbar-track {
                background: #f1f3f4;
                border-radius: 3px;
            }

            .guide-notification-body::-webkit-scrollbar-thumb {
                background: #dadce0;
                border-radius: 3px;
            }

            .guide-notification-body::-webkit-scrollbar-thumb:hover {
                background: #bdc1c6;
            }

            .guide-notification-footer {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 12px 20px 16px;
                border-top: 1px solid #f1f3f4;
                background: #fafafa;
                flex-shrink: 0;
            }

            .guide-checkbox-container {
                display: flex;
                align-items: center;
                cursor: pointer;
                font-size: 13px;
                color: #5f6368;
                gap: 8px;
            }

            .guide-checkbox {
                position: absolute;
                opacity: 0;
                cursor: pointer;
                height: 0;
                width: 0;
            }

            .guide-checkbox-checkmark {
                height: 16px;
                width: 16px;
                background-color: white;
                border: 2px solid #dadce0;
                border-radius: 3px;
                transition: all 0.2s ease;
                position: relative;
                flex-shrink: 0;
            }

            .guide-checkbox:checked ~ .guide-checkbox-checkmark {
                background-color: #1a73e8;
                border-color: #1a73e8;
            }

            .guide-checkbox:checked ~ .guide-checkbox-checkmark:after {
                content: "";
                position: absolute;
                display: block;
                left: 4px;
                top: 1px;
                width: 4px;
                height: 8px;
                border: solid white;
                border-width: 0 2px 2px 0;
                transform: rotate(45deg);
            }

            .guide-checkbox-text {
                user-select: none;
                line-height: 1.3;
            }

            .guide-btn {
                padding: 8px 16px;
                border-radius: 6px;
                font-size: 13px;
                font-weight: 500;
                cursor: pointer;
                transition: all 0.2s ease;
                border: none;
                min-width: 70px;
            }

            .guide-btn-primary {
                background: #1a73e8;
                color: white;
            }

            .guide-btn-primary:hover {
                background: #1557b0;
                transform: translateY(-1px);
                box-shadow: 0 2px 8px rgba(26, 115, 232, 0.3);
            }

            .guide-feature-summary {
                background: #f8f9fa;
                padding: 12px;
                border-radius: 6px;
                margin-bottom: 16px;
                border-left: 3px solid #1a73e8;
            }

            .guide-feature-title {
                font-weight: 600;
                margin-bottom: 8px;
                color: #202124;
                font-size: 14px;
            }

            .guide-feature-list {
                list-style: none;
                padding: 0;
                margin: 0;
                font-size: 12px;
                color: #5f6368;
                line-height: 1.4;
            }

            .guide-feature-list li {
                margin-bottom: 4px;
                padding-left: 16px;
                position: relative;
            }

            .guide-step {
                margin-bottom: 14px;
                padding-bottom: 14px;
                border-bottom: 1px solid #f1f3f4;
            }

            .guide-step:last-child {
                margin-bottom: 0;
                padding-bottom: 0;
                border-bottom: none;
            }

            .guide-step-title {
                font-weight: 500;
                font-size: 14px;
                color: #202124;
                margin-bottom: 6px;
            }

            .guide-step-description {
                font-size: 13px;
                color: #5f6368;
                line-height: 1.4;
            }

            .guide-subtitle {
                color: #5f6368;
                margin-bottom: 16px;
                font-size: 13px;
                line-height: 1.4;
            }

            /* 마우스 오버 시 z-index 상승 */
            .guide-notification:hover {
                z-index: 10000;
            }

            /* 모바일 대응 */
            @media (max-width: 768px) {
                .guide-notification {
                    top: 70px;
                    left: 10px;
                    width: 280px;
                    height: 350px;
                    max-width: calc(100vw - 20px);
                    max-height: calc(100vh - 80px);
                }
                
                .guide-notification-title {
                    font-size: 16px;
                }
            }

            /* 화면이 작을 때 더 작게 */
            @media (max-width: 480px) {
                .guide-notification {
                    width: 260px;
                    height: 300px;
                    max-width: calc(100vw - 20px);
                }
            }

            .guide-steps {
                min-height: 300px;
            }

            /* 애니메이션 성능 최적화 */
            .guide-notification {
                will-change: opacity, transform;
            }
        `;
        
        document.head.appendChild(style);
    }

    // 현재 언어 감지
    detectCurrentLanguage() {
        if (window.currentLanguage) {
            this.currentLanguage = window.currentLanguage;
        } else if (window.languages) {
            this.currentLanguage = 'en';
        }
        console.log(`🌐 Detected language: ${this.currentLanguage}`);
    }

    // 알림창 컨텐츠 동적 생성
    generateNotificationContent() {
        const lang = this.content[this.currentLanguage] || this.content.en;
        
        // 제목 설정
        const title = this.notification.querySelector('#guideNotificationTitle');
        if (title) {
            title.textContent = lang.title;
        }

        // 본문 내용 생성
        const contentDiv = this.notification.querySelector('#guideNotificationContent');
        if (contentDiv) {
            contentDiv.innerHTML = this.createContentHTML(lang);
        }

        // 체크박스 텍스트
        const checkboxText = this.notification.querySelector('#guideCheckboxText');
        if (checkboxText) {
            checkboxText.textContent = lang.checkboxText;
        }

        // 확인 버튼
        const confirmBtn = this.notification.querySelector('#guideNotificationConfirm');
        if (confirmBtn) {
            confirmBtn.textContent = lang.confirmButton;
        }

        // 체크박스 참조 업데이트
        this.checkbox = this.notification.querySelector('#dontShowToday');

        console.log('✅ Notification content generated for language:', this.currentLanguage);
    }

    // 본문 HTML 생성
    createContentHTML(lang) {
        const featuresHTML = lang.features.map(feature => 
            `<li>${feature}</li>`
        ).join('');

        const stepsHTML = lang.steps.map(step => 
            `<div class="guide-step">
                <div class="guide-step-title">${step.title}</div>
                <div class="guide-step-description">${step.description}</div>
            </div>`
        ).join('');

        return `
            <div class="guide-subtitle">${lang.subtitle}</div>
            
            <div class="guide-feature-summary">
                <div class="guide-feature-title">${lang.featureTitle}</div>
                <ul class="guide-feature-list">
                    ${featuresHTML}
                </ul>
            </div>

            <div class="guide-steps">
                ${stepsHTML}
            </div>
        `;
    }

    // 이벤트 리스너 설정
    setupEventListeners() {
        // ESC 키로 알림창 닫기
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.isNotificationOpen()) {
                this.closeNotification();
            }
        });
    }

    // 알림창이 열려있는지 확인
    isNotificationOpen() {
        return this.notification && this.notification.classList.contains('show');
    }

    // 알림창 표시 여부 확인
    checkShouldShowNotification() {
        const hiddenUntil = localStorage.getItem(this.storageKey);
        
        if (hiddenUntil) {
            const hiddenUntilDate = new Date(hiddenUntil);
            const now = new Date();
            
            if (now < hiddenUntilDate) {
                console.log('📅 Guide notification: Hidden for 24 hours, not showing');
                return;
            } else {
                localStorage.removeItem(this.storageKey);
                console.log('📅 Guide notification: 24-hour period expired, showing notification');
            }
        }

        // 1초 후 알림창 표시
        setTimeout(() => {
            this.openNotification();
        }, 1000);
    }

    // 알림창 열기
    openNotification() {
        if (!this.notification) {
            console.error('❌ Guide notification element not found');
            return;
        }

        try {
            this.notification.classList.add('show');
            console.log('✅ Guide notification opened');
        } catch (error) {
            console.error('❌ Guide notification open error:', error);
        }
    }

    // 알림창 닫기
    closeNotification() {
        if (!this.notification) {
            console.error('❌ Guide notification element not found');
            return;
        }

        try {
            // 체크박스 상태 확인 및 처리
            if (this.checkbox && this.checkbox.checked) {
                this.setHiddenFor24Hours();
            }

            // 알림창 닫기 애니메이션
            this.notification.classList.remove('show');
            
            // 애니메이션 완료 후 제거
            setTimeout(() => {
                if (this.notification && this.notification.parentNode) {
                    this.notification.remove();
                }
            }, 400);

            console.log('✅ Guide notification closed');
        } catch (error) {
            console.error('❌ Guide notification close error:', error);
        }
    }

    // 24시간 동안 숨김 설정
    setHiddenFor24Hours() {
        const now = new Date();
        const hiddenUntil = new Date(now.getTime() + 24 * 60 * 60 * 1000);
        
        localStorage.setItem(this.storageKey, hiddenUntil.toISOString());
        
        console.log('📅 Guide notification: Hidden for 24 hours');
        console.log(`   Next display scheduled: ${hiddenUntil.toLocaleString()}`);
    }

    // 언어 변경 시 컨텐츠 업데이트
    updateLanguage(lang) {
        if (this.content[lang]) {
            this.currentLanguage = lang;
            this.generateNotificationContent();
            console.log(`🌐 Guide notification language updated: ${lang}`);
        } else {
            console.warn(`⚠️ Language not supported: ${lang}`);
        }
    }

    // 수동으로 알림창 열기 (디버깅용)
    forceOpen() {
        console.log('🔧 Guide notification force open');
        this.createNotificationElement();
        this.generateNotificationContent();
        this.openNotification();
    }

    // 숨김 설정 초기화 (디버깅용)
    resetHiddenSettings() {
        localStorage.removeItem(this.storageKey);
        console.log('🔧 Guide notification hidden settings reset');
    }

    // 상태 정보 출력 (디버깅용)
    getStatus() {
        const hiddenUntil = localStorage.getItem(this.storageKey);
        const isHidden = hiddenUntil && new Date() < new Date(hiddenUntil);
        
        return {
            isNotificationOpen: this.isNotificationOpen(),
            isHiddenFor24Hours: isHidden,
            hiddenUntil: hiddenUntil ? new Date(hiddenUntil).toLocaleString() : null,
            currentLanguage: this.currentLanguage,
            storageKey: this.storageKey,
            notificationElement: !!this.notification
        };
    }
}

// ==================== 법적 동의 기능 ====================

class LegalConsentManager {
    constructor() {
        this.storageKey = 'pickpost_legal_consent';
        this.consentDuration = 24 * 60 * 60 * 1000; // 24시간
    }

    hasValidConsent() {
        try {
            const stored = localStorage.getItem(this.storageKey);
            if (!stored) return false;

            const consent = JSON.parse(stored);
            const now = Date.now();
            
            if (now - consent.timestamp > this.consentDuration) {
                localStorage.removeItem(this.storageKey);
                return false;
            }

            return consent.agreed === true;
        } catch (error) {
            console.error('동의 상태 확인 오류:', error);
            return false;
        }
    }

    saveConsent() {
        const consent = {
            agreed: true,
            timestamp: Date.now(),
            version: '1.0'
        };
        localStorage.setItem(this.storageKey, JSON.stringify(consent));
    }

    showConsentModal() {
        return new Promise((resolve, reject) => {
            const lang = window.languages?.[window.currentLanguage] || window.languages?.en || {};
            
            const modalHtml = `
                <div class="legal-consent-modal" id="legalConsentModal" style="z-index: 15000;">
                    <div class="legal-consent-content">
                        <div class="legal-consent-header">
                            <h3>⚖️ ${lang.legalConsent?.title || '법적 책임 고지'}</h3>
                        </div>
                        
                        <div class="legal-consent-body">
                            <div class="legal-notice">
                                <p><strong>${lang.legalConsent?.warning || '⚠️ 중요 안내사항'}</strong></p>
                                <p>${lang.legalConsent?.description || 'PickPost는 공개 데이터 수집 도구를 제공할 뿐이며, 크롤링으로 인한 모든 법적 책임은 사용자에게 있습니다.'}</p>
                            </div>
                            
                            <div class="consent-checklist">
                                <label class="consent-checkbox-container">
                                    <input type="checkbox" id="legalConsentCheck" />
                                    <span class="consent-text">
                                        ${lang.legalConsent?.checkboxText || '본인은 크롤링 대상 사이트의 이용약관 및 정책을 확인하였으며, 해당 데이터 수집에 대한 법적 책임이 본인에게 있음을 인지합니다.'}
                                    </span>
                                </label>
                            </div>
                            
                            <div class="consent-links">
                                <a href="javascript:void(0)" onclick="legalConsentManager.openTermsFromConsent()">${lang.terms || '이용약관'}</a> | 
                                <a href="javascript:void(0)" onclick="legalConsentManager.openPrivacyFromConsent()">${lang.privacy || '개인정보처리방침'}</a>
                            </div>
                        </div>
                        
                        <div class="legal-consent-footer">
                            <button type="button" class="consent-btn consent-cancel" onclick="legalConsentManager.cancelConsent()">
                                ${lang.cancel || '취소'}
                            </button>
                            <button type="button" class="consent-btn consent-confirm" id="consentConfirmBtn" disabled onclick="legalConsentManager.confirmConsent()">
                                ${lang.legalConsent?.confirmBtn || '동의하고 시작'}
                            </button>
                        </div>
                    </div>
                </div>
            `;

            document.body.insertAdjacentHTML('beforeend', modalHtml);
            this.setupConsentEventListeners(resolve, reject);
            
            const modal = document.getElementById('legalConsentModal');
            modal.style.display = 'flex';
            document.body.style.overflow = 'hidden';
            
            setTimeout(() => {
                document.getElementById('legalConsentCheck')?.focus();
            }, 100);
        });
    }

    // 동의 모달에서 약관 열기 - z-index 높게
    openTermsFromConsent() {
        if (window.modalManager) {
            // 약관 모달의 z-index를 더 높게 설정
            const originalOpen = window.modalManager.openModal;
            window.modalManager.openModal = function(type, options) {
                const result = originalOpen.call(this, type, options);
                const termsModal = document.getElementById('termsModal');
                if (termsModal) {
                    termsModal.style.zIndex = '16000';
                }
                return result;
            };
            
            window.modalManager.openModal('terms');
            
            // 원래 함수로 복구
            window.modalManager.openModal = originalOpen;
        }
    }

    // 동의 모달에서 개인정보처리방침 열기 - z-index 높게  
    openPrivacyFromConsent() {
        if (window.modalManager) {
            const originalOpen = window.modalManager.openModal;
            window.modalManager.openModal = function(type, options) {
                const result = originalOpen.call(this, type, options);
                const privacyModal = document.getElementById('privacyModal');
                if (privacyModal) {
                    privacyModal.style.zIndex = '16000';
                }
                return result;
            };
            
            window.modalManager.openModal('privacy');
            window.modalManager.openModal = originalOpen;
        }
    }

    setupConsentEventListeners(resolve, reject) {
        const checkbox = document.getElementById('legalConsentCheck');
        const confirmBtn = document.getElementById('consentConfirmBtn');
        
        checkbox.addEventListener('change', () => {
            confirmBtn.disabled = !checkbox.checked;
            confirmBtn.classList.toggle('active', checkbox.checked);
        });

        const escHandler = (e) => {
            if (e.key === 'Escape') {
                this.cancelConsent();
                document.removeEventListener('keydown', escHandler);
            } else if (e.key === 'Enter' && checkbox.checked) {
                // 👆 이 두 줄만 추가
                this.confirmConsent();
            }
        };
        document.addEventListener('keydown', escHandler);

        this.resolveConsent = resolve;
        this.rejectConsent = reject;
    }

    confirmConsent() {
        const checkbox = document.getElementById('legalConsentCheck');
        if (!checkbox.checked) return;

        this.saveConsent();
        this.closeConsentModal();
        
        if (this.resolveConsent) {
            this.resolveConsent(true);
        }
    }

    cancelConsent() {
        this.closeConsentModal();
        
        if (this.rejectConsent) {
            this.rejectConsent(new Error('사용자가 법적 동의를 거부했습니다'));
        }
    }

    closeConsentModal() {
        const modal = document.getElementById('legalConsentModal');
        if (modal) {
            modal.remove();
        }
        document.body.style.overflow = '';
    }
}

// ==================== CSS 수정 ====================

function addLegalConsentStyles() {
    const style = document.createElement('style');
    style.textContent = `
        .legal-consent-modal {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0, 0, 0, 0.7);
            display: flex;
            justify-content: center;
            align-items: center;
            z-index: 15000; /* 높은 z-index */
            backdrop-filter: blur(2px);
        }

        .legal-consent-content {
            background: white;
            border-radius: 12px;
            padding: 24px;
            max-width: 500px;
            width: 90%;
            max-height: 80vh;
            overflow-y: auto;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
            animation: modalSlideIn 0.3s ease-out;
        }

        @keyframes modalSlideIn {
            from {
                opacity: 0;
                transform: translateY(-30px) scale(0.95);
            }
            to {
                opacity: 1;
                transform: translateY(0) scale(1);
            }
        }

        .legal-consent-header h3 {
            margin: 0 0 20px 0;
            color: #333;
            font-size: 20px;
            text-align: center;
        }

        .legal-notice {
            background: #fff3cd;
            border: 1px solid #ffeaa7;
            border-radius: 8px;
            padding: 16px;
            margin-bottom: 20px;
        }

        .legal-notice p {
            margin: 0 0 8px 0;
            line-height: 1.5;
        }

        .legal-notice strong {
            color: #856404;
        }

        .consent-checklist {
            margin: 20px 0;
        }

        .consent-checkbox-container {
            display: flex;
            align-items: flex-start;
            cursor: pointer;
            line-height: 1.5;
            gap: 12px;
        }

        /* checkmark span 제거 - 기본 체크박스만 사용 */
        .consent-checkbox-container input[type="checkbox"] {
            width: 18px;
            height: 18px;
            margin: 0;
            cursor: pointer;
            flex-shrink: 0;
            margin-top: 2px;
        }

        .consent-text {
            flex: 1;
            font-size: 14px;
            color: #333;
        }

        .consent-links {
            text-align: center;
            margin: 16px 0;
            font-size: 13px;
        }

        .consent-links a {
            color: #007bff;
            text-decoration: none;
        }

        .consent-links a:hover {
            text-decoration: underline;
        }

        .legal-consent-footer {
            display: flex;
            gap: 12px;
            justify-content: flex-end;
            margin-top: 20px;
        }

        .consent-btn {
            padding: 10px 20px;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;
            transition: all 0.2s;
        }

        .consent-cancel {
            background: #6c757d;
            color: white;
        }

        .consent-cancel:hover {
            background: #5a6268;
        }

        .consent-confirm {
            background: #28a745;
            color: white;
        }

        .consent-confirm:disabled {
            background: #ccc;
            cursor: not-allowed;
        }

        .consent-confirm.active:hover {
            background: #218838;
        }

        @media (max-width: 480px) {
            .legal-consent-content {
                padding: 16px;
                width: 95%;
            }
            
            .legal-consent-footer {
                flex-direction: column;
            }
            
            .consent-btn {
                width: 100%;
            }
        }
    `;
    document.head.appendChild(style);
}

// ==================== 전역 인스턴스 및 함수 ====================

// GuideNotificationManager 인스턴스
let guideNotificationManager;

// DOM 로드 완료 시 초기화 - 단일 인스턴스만 생성
document.addEventListener('DOMContentLoaded', () => {
    try {
        // 중복 생성 방지
        if (guideNotificationManager) {
            console.warn('⚠️ GuideNotificationManager already exists, skipping initialization');
            return;
        }
        
        guideNotificationManager = new GuideNotificationManager();
        
        // DOM 준비 후 초기화 실행
        const initSuccess = guideNotificationManager.init();
        
        if (initSuccess) {
            // 전역 함수로 노출 (기존 코드와의 호환성)
            window.guideNotificationManager = guideNotificationManager;
            console.log('✅ GuideNotificationManager global initialization complete');
        } else {
            console.error('❌ GuideNotificationManager initialization failed');
            guideNotificationManager = null;
        }
        addLegalConsentStyles();
        
        // 전역 인스턴스 생성 (기존 guide.js 로직 뒤에)
        if (!window.legalConsentManager) {
            window.legalConsentManager = new LegalConsentManager();
            console.log('✅ LegalConsentManager initialized in guide.js');
        }
    } catch (error) {
        console.error('❌ GuideNotificationManager initialization failed:', error);
        guideNotificationManager = null;
    }
});

// ==================== 전역 호환성 함수들 ====================
// index.html과의 호환성을 위한 함수들

// 알림창 닫기
function closeGuideNotification() {
    if (guideNotificationManager) {
        guideNotificationManager.closeNotification();
    } else {
        console.error('❌ GuideNotificationManager not initialized.');
    }
}

// 알림창 열기
function openGuideNotification() {
    if (guideNotificationManager) {
        guideNotificationManager.openNotification();
    } else {
        console.error('❌ GuideNotificationManager not initialized.');
    }
}

// 언어 변경 시 호출
function updateGuideNotificationLanguage(lang) {
    if (guideNotificationManager) {
        guideNotificationManager.updateLanguage(lang);
    }
}

// 기존 모달 함수들과의 호환성
function closeGuideModal() {
    closeGuideNotification();
}

function openGuideModal() {
    openGuideNotification();
}

function updateGuideModalLanguage(lang) {
    updateGuideNotificationLanguage(lang);
}

// ==================== 디버깅 전용 함수들 ====================

window.guideNotificationDebug = {
    // 강제로 알림창 열기
    forceOpen: () => guideNotificationManager?.forceOpen(),
    
    // 숨김 설정 초기화
    reset: () => guideNotificationManager?.resetHiddenSettings(),
    
    // 현재 상태 확인
    status: () => guideNotificationManager?.getStatus(),
    
    // 24시간 숨김 설정 (테스트용)
    hide24h: () => guideNotificationManager?.setHiddenFor24Hours(),
    
    // 언어 변경 테스트
    setLang: (lang) => guideNotificationManager?.updateLanguage(lang),
    
    // 인스턴스 확인
    instance: () => guideNotificationManager
};

// 기존 디버깅 함수와의 호환성
window.guideModalDebug = window.guideNotificationDebug;

// ==================== 다른 모듈과의 연동 ====================

// 언어 변경 이벤트 리스너
document.addEventListener('languageChanged', (event) => {
    if (event.detail && event.detail.language) {
        updateGuideNotificationLanguage(event.detail.language);
    }
});

// 전역 언어 변경 함수와 연동
if (typeof window !== 'undefined') {
    const originalSelectLanguage = window.selectLanguage;
    window.selectLanguage = function(lang, displayName) {
        if (originalSelectLanguage) {
            originalSelectLanguage(lang, displayName);
        }
        updateGuideNotificationLanguage(lang);
    };
}

console.log('📢 Guide Notification Manager v3.0 loaded - 사이드 알림창으로 변경');
console.log('   Usage: window.guideNotificationDebug.status() - Check status');
console.log('   Usage: window.guideNotificationDebug.forceOpen() - Force open');
console.log('   Usage: window.guideNotificationDebug.reset() - Reset settings');
