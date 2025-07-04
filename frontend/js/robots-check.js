
class RobotsTxtChecker {
    constructor() {
        this.cache = new Map();
        this.cacheTimeout = 5 * 60 * 1000; // 5분 캐시
    }

    /**
     * robots.txt 확인 및 결과 표시
     */
    async checkRobotsTxt(targetUrl) {
        try {
            const baseUrl = this.getBaseUrl(targetUrl);
            const robotsUrl = `${baseUrl}/robots.txt`;
            
            // 캐시 확인
            const cached = this.getCached(robotsUrl);
            if (cached) return cached;

            // robots.txt 다운로드 시도
            const robotsContent = await this.fetchRobotsTxt(robotsUrl);
            const result = this.parseRobotsTxt(robotsContent, targetUrl);
            
            // 캐시 저장
            this.setCached(robotsUrl, result);
            return result;
            
        } catch (error) {
            console.error('robots.txt 확인 오류:', error);
            return {
                status: 'error',
                message: 'robots.txt를 확인할 수 없습니다',
                error: error.message
            };
        }
    }

    /**
     * robots.txt 다운로드
     */
    async fetchRobotsTxt(robotsUrl) {
        const response = await fetch(robotsUrl, {
            method: 'GET',
            headers: {
                'User-Agent': 'PickPost-Bot/1.0'
            }
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        return await response.text();
    }

    /**
     * robots.txt 파싱 및 분석
     */
    parseRobotsTxt(content, targetUrl) {
        const rules = this.parseRules(content);
        const userAgent = 'PickPost-Bot';
        const path = new URL(targetUrl).pathname;
        
        const applicableRules = this.getApplicableRules(rules, userAgent);
        const isAllowed = this.checkPathAllowed(applicableRules, path);
        const crawlDelay = this.getCrawlDelay(applicableRules);
        
        return {
            status: 'success',
            robotsUrl: `${this.getBaseUrl(targetUrl)}/robots.txt`,
            isAllowed,
            crawlDelay,
            recommendation: this.getRecommendation(isAllowed, crawlDelay),
            details: {
                targetPath: path,
                userAgent,
                matchedRules: this.getMatchedRules(applicableRules, path)
            }
        };
    }

    /**
     * robots.txt 규칙 파싱
     */
    parseRules(content) {
        const rules = [];
        const lines = content.split('\n');
        let currentUserAgent = null;
        
        for (let line of lines) {
            line = line.trim();
            if (!line || line.startsWith('#')) continue;
            
            const colonIndex = line.indexOf(':');
            if (colonIndex === -1) continue;
            
            const directive = line.substring(0, colonIndex).trim().toLowerCase();
            const value = line.substring(colonIndex + 1).trim();
            
            switch (directive) {
                case 'user-agent':
                    currentUserAgent = value;
                    break;
                case 'disallow':
                case 'allow':
                    if (currentUserAgent) {
                        rules.push({
                            userAgent: currentUserAgent,
                            directive,
                            path: value
                        });
                    }
                    break;
                case 'crawl-delay':
                    if (currentUserAgent) {
                        rules.push({
                            userAgent: currentUserAgent,
                            directive,
                            delay: parseInt(value) || 0
                        });
                    }
                    break;
            }
        }
        
        return rules;
    }

    /**
     * 해당 User-Agent에 적용되는 규칙 추출
     */
    getApplicableRules(rules, userAgent) {
        const applicable = [];
        applicable.push(...rules.filter(rule => rule.userAgent === userAgent));
        applicable.push(...rules.filter(rule => rule.userAgent === '*'));
        return applicable;
    }

    /**
     * 특정 경로의 크롤링 허용 여부 확인
     */
    checkPathAllowed(rules, path) {
        let allowed = true;
        
        for (const rule of rules) {
            if (rule.directive === 'disallow' || rule.directive === 'allow') {
                if (this.pathMatches(path, rule.path)) {
                    allowed = rule.directive === 'allow';
                }
            }
        }
        
        return allowed;
    }

    /**
     * 경로 패턴 매칭
     */
    pathMatches(path, pattern) {
        if (!pattern) return true;
        if (pattern === '/') return true;
        
        const regexPattern = pattern
            .replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
            .replace(/\\\*/g, '.*');
        
        const regex = new RegExp(`^${regexPattern}`);
        return regex.test(path);
    }

    /**
     * Crawl-delay 값 추출
     */
    getCrawlDelay(rules) {
        for (const rule of rules) {
            if (rule.directive === 'crawl-delay') {
                return rule.delay;
            }
        }
        return 0;
    }

    /**
     * 매칭된 규칙 반환
     */
    getMatchedRules(rules, path) {
        return rules.filter(rule => 
            (rule.directive === 'allow' || rule.directive === 'disallow') &&
            this.pathMatches(path, rule.path)
        );
    }

    /**
     * 권장사항 생성
     */
    getRecommendation(isAllowed, crawlDelay) {
        if (!isAllowed) {
            return {
                type: 'warning',
                message: '크롤링이 금지되어 있습니다',
                action: '다른 방법을 고려하거나 사이트 관리자에게 문의하세요'
            };
        } else if (crawlDelay > 0) {
            return {
                type: 'caution',
                message: `크롤링 지연시간 ${crawlDelay}초가 권장됩니다`,
                action: '요청 간격을 조정하여 사이트 부하를 줄이세요'
            };
        } else {
            return {
                type: 'success',
                message: '크롤링이 허용됩니다',
                action: '적절한 요청 간격을 유지하며 진행하세요'
            };
        }
    }

    /**
     * 기본 URL 추출
     */
    getBaseUrl(url) {
        try {
            const parsed = new URL(url);
            return `${parsed.protocol}//${parsed.host}`;
        } catch {
            return url.split('/').slice(0, 3).join('/');
        }
    }

    /**
     * 캐시 관리
     */
    getCached(key) {
        const cached = this.cache.get(key);
        if (cached && Date.now() - cached.timestamp < this.cacheTimeout) {
            return cached.data;
        }
        return null;
    }

    setCached(key, data) {
        this.cache.set(key, {
            data,
            timestamp: Date.now()
        });
    }

    /**
     * 결과를 간단한 알림으로 표시
     */
    async showQuickCheck(targetUrl) {
        const result = await this.checkRobotsTxt(targetUrl);
        const lang = window.languages?.[window.currentLanguage] || window.languages?.en || {};
        
        let message = '';
        let type = 'info';
        
        if (result.status === 'error') {
            message = `❌ robots.txt 확인 실패: ${result.error}`;
            type = 'warning';
        } else if (result.isAllowed) {
            message = `✅ 크롤링 허용됨${result.crawlDelay > 0 ? ` (${result.crawlDelay}초 지연 권장)` : ''}`;
            type = 'success';
        } else {
            message = `⚠️ ${result.recommendation.message}`;
            type = 'warning';
        }
        
        // PickPost의 showMessage 함수 사용
        if (window.PickPostGlobals?.showMessage) {
            window.PickPostGlobals.showMessage(message, type);
        } else {
            alert(message);
        }
        
        return result;
    }
}

// ==================== CSS 스타일 ====================

function addRobotsCheckStyles() {
    const style = document.createElement('style');
    style.textContent = `
        .robots-quick-btn {
            background: #17a2b8;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 6px;
            font-size: 12px;
            cursor: pointer;
            margin-left: 8px;
            transition: all 0.2s;
        }

        .robots-quick-btn:hover {
            background: #138496;
            transform: translateY(-1px);
        }

        .robots-check-result {
            margin: 8px 0;
            padding: 8px 12px;
            border-radius: 6px;
            font-size: 13px;
            line-height: 1.4;
        }

        .robots-check-result.success {
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }

        .robots-check-result.warning {
            background: #fff3cd;
            color: #856404;
            border: 1px solid #ffeaa7;
        }

        .robots-check-result.error {
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
    `;
    document.head.appendChild(style);
}

// ==================== 전역 인스턴스 생성 ====================

// DOM 로드 완료 시 초기화
document.addEventListener('DOMContentLoaded', () => {
    addRobotsCheckStyles();
    
    if (!window.robotsTxtChecker) {
        window.robotsTxtChecker = new RobotsTxtChecker();
        console.log('✅ RobotsTxtChecker initialized');
    }
});

// ==================== 간단한 사용 함수 ====================

// 현재 입력된 사이트의 robots.txt 간단 확인
window.checkCurrentSiteRobots = async function() {
    if (!window.robotsTxtChecker) {
        console.error('RobotsTxtChecker not initialized');
        return;
    }

    try {
        // 현재 입력된 URL 가져오기
        const siteInput = document.getElementById('siteInput')?.value?.trim();
        const boardInput = document.getElementById('boardInput')?.value?.trim();
        
        if (!siteInput) {
            window.PickPostGlobals?.showMessage('먼저 크롤링할 사이트를 입력해주세요.', 'warning');
            return;
        }

        let targetUrl = siteInput;
        
        // URL이 아닌 경우 기본 URL 구성
        if (!siteInput.startsWith('http')) {
            const currentSite = window.PickPostGlobals?.getCurrentSite();
            
            switch (currentSite) {
                case 'reddit':
                    targetUrl = `https://www.reddit.com/r/${boardInput || 'popular'}`;
                    break;
                case 'lemmy':
                    if (boardInput && boardInput.includes('@')) {
                        const [community, instance] = boardInput.split('@');
                        targetUrl = `https://${instance}/c/${community}`;
                    } else {
                        targetUrl = `https://lemmy.world/c/${boardInput || 'all'}`;
                    }
                    break;
                default:
                    targetUrl = `https://${siteInput}`;
            }
        }

        await window.robotsTxtChecker.showQuickCheck(targetUrl);
        
    } catch (error) {
        console.error('robots.txt 확인 오류:', error);
        window.PickPostGlobals?.showMessage('robots.txt 확인 중 오류가 발생했습니다.', 'error');
    }
};

console.log('✅ robots.txt 확인 기능 로드 완료');
