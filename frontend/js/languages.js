// languages.js 파일 상단에 추가 (기존 내용 유지하면서)

// 전역 언어 객체 확인
if (typeof window.languages === 'undefined') {
   window.languages = {};
}

// PickPost 언어팩 - 정리된 완전한 버전
const languages = {
   ko: {
       // ==================== 기본 UI 요소 ====================
       start: "크롤링 시작",
       clear: "결과 지우기", 
       ok: "확인",
       cancel: "취소",
       download: "Excel 다운로드",
       title: "PickPost",
       
       // ==================== 사이트 관련 ====================
       siteSelect: "사이트를 선택하세요",
       
       // ==================== 사이트 이름 번역 ====================
       siteNames: {
           reddit: "레딧",
           dcinside: "디시인사이드", 
           blind: "블라인드",
           bbc: "BBC",
           lemmy: "레미",
           universal: "범용"
       },
       
       // ==================== 폼 라벨 ====================
       labels: {
           minViews: "최소 조회수",
           minRecommend: "최소 추천수", 
           minComments: "최소 댓글수",
           startRank: "시작 순위",
           endRank: "끝 순위",
           sortMethod: "정렬 방식",
           timePeriod: "기간",
           advancedSearch: "고급 검색",
           startDate: "시작일",
           endDate: "종료일"
       },
       
       // ==================== 입력 필드 ====================
       sitePlaceholder: "사이트 이름 또는 주소를 입력하세요...",
       boardPlaceholder: "게시판 이름을 입력하세요...",
       boardPlaceholders: {
           default: "게시판 이름을 입력하세요...",
           reddit: "서브레딧 이름 (예: askreddit)",
           dcinside: "갤러리 이름 (예: programming)",
           blind: "게시판 이름 (예: 개발자)",
           lemmy: "커뮤니티@인스턴스 (예: technology@lemmy.world)",
           bbc: "BBC 섹션 URL",
           universal: "크롤링할 웹사이트 URL을 입력하세요..."
       },
       
       // ==================== 시간 필터 옵션 ====================
       timeFilterLabels: {
           hour: "1시간",
           day: "하루",
           week: "일주일", 
           month: "한 달",
           year: "일 년",
           all: "전체",
           custom: "사용자 지정"
       },
       
       // ==================== 정렬 옵션 ====================
       sortOptions: {
           latest: "최신순",
           popular: "인기순",
           views: "조회수순",
           comments: "댓글순",
           
           // Reddit 전용
           reddit: {
               new: "새 글",
               top: "인기글",
               hot: "핫한 글",
               best: "베스트",
               rising: "떠오르는 글"
           },
           
           // 기타 사이트용
           other: {
               popular: "인기순",
               recommend: "추천순", 
               recent: "최신순",
               comments: "댓글순"
           }
       },
       
       // ==================== 결과 표시 ====================
        views: "조회수",
        likes: "추천수", 
        comments: "댓글수",
        date: "작성일",
        original: "원문 링크",
        translation: "번역",
        fail: "(번역 실패)",

        resultTexts: {
        noResults: "검색 결과가 없습니다",
        resultsCount: "{count}개의 결과를 찾았습니다",
        showing: "{start}-{end} / {total}",
        loadMore: "더 보기"
        },

        results: {
            crawlingComplete: "크롤링 완료",
            completedAt: "완료",
            totalPosts: "총 게시물", 
            rankRange: "순위 범위",
            estimatedPages: "예상 페이지",
            sourcesite: "소스 사이트",
            crawlingMode: "크롤링 모드",
            basic: "기본",
            advanced: "고급 검색", 
            duration: "소요 시간",
            viewOriginal: "원문 보기",
            seconds: "초",
            posts: "개",
            page: "페이지",
            found: "개 수집",
            noResults: "결과가 없습니다"
        },

       // ==================== 크롤링 진행 상태 ====================
       crawlingProgress: {
           // 기본 진행 단계
           site_detecting: "사이트 분석 중...",
           site_connecting: "{site}에 연결 중...",
           posts_collecting: "{site}에서 게시물 수집 중...",
           posts_filtering: "조건에 맞는 게시물 필터링 중... ({matched}/{total})",
           posts_processing: "데이터 처리 중...",
           translation_preparing: "번역 준비 중... ({count}개 게시물)",
           translation_progress: "번역 진행 중... ({current}/{total})",
           finalizing: "결과 정리 중...",
           
           // 사이트별 특화 메시지
           reddit_analyzing: "Reddit 데이터 분석 중...",
           dcinside_parsing: "디시인사이드 파싱 중...",
           blind_processing: "블라인드 처리 중...",
           bbc_fetching: "BBC 뉴스 가져오는 중...",
           lemmy_connecting: "Lemmy 서버 연결 중...",
           universal_parsing: "웹페이지 구조 분석 중...",
           
           // 상세 상태
           board_analyzing: "{board} 게시판 분석 중...",
           page_collecting: "페이지 {page} 수집 중...",
           content_parsing: "컨텐츠 파싱 중...",
           metadata_processing: "메타데이터 처리 중...",
           filtering_by_criteria: "설정 조건으로 필터링 중...",
           preparing_results: "결과 준비 중..."
       },

       // ==================== 완료 메시지 ====================
        completionMessages: {
            success: "크롤링 완료: {count}개 게시물",
            noData: "결과가 없습니다",
            error: "오류가 발생했습니다",
            unified_complete: "{input}에서 {count}개 게시물 발견 (사이트: {site})",
            legacy_complete: "크롤링 완료: {count}개 게시물",
            crawl_complete: "{site} {board}에서 {count}개 게시물 수집 완료 ({start}-{end}위)",
            translation_complete: "번역 완료: {count}개 게시물을 처리했습니다",
            reddit_complete: "Reddit {board}에서 {count}개 게시물 수집 완료",
            dcinside_complete: "디시인사이드 {board} 갤러리에서 {count}개 게시물 수집 완료",
            blind_complete: "블라인드 {board}에서 {count}개 게시물 수집 완료",
            bbc_complete: "BBC {section}에서 {count}개 뉴스 수집 완료",
            lemmy_complete: "Lemmy {board}에서 {count}개 게시물 수집 완료",
            universal_complete: "{input}에서 {count}개 게시물 수집 완료",
            analysis_complete: "사이트 분석 완료: {site} 감지됨"
       },
       
       // ==================== 에러 메시지 ====================
       errorMessages: {
           empty_input: "크롤링할 사이트나 게시판을 입력해주세요",
           site_detection_failed: "사이트를 감지할 수 없습니다: {input}",
           unsupported_site: "지원하지 않는 사이트입니다: {site}",
           connection_failed: "{site} 연결에 실패했습니다",
           no_posts_found: "{site} {board}에서 조건에 맞는 게시물을 찾을 수 없습니다",
           crawling_timeout: "크롤링 시간이 초과되었습니다 ({site})",
           invalid_board: "올바르지 않은 게시판입니다: {board}",
           crawling_error: "크롤링 중 오류가 발생했습니다: {error}",
           translation_failed: "번역 중 오류가 발생했습니다",
           analysis_failed: "사이트 분석에 실패했습니다: {error}",
           rate_limited: "요청 제한에 걸렸습니다. 잠시 후 시도해주세요",
           network_error: "네트워크 연결에 문제가 있습니다",
           server_error: "서버 오류가 발생했습니다",
           permission_denied: "접근 권한이 없습니다",
           invalid_credentials: "인증 정보가 올바르지 않습니다",
           quota_exceeded: "일일 사용량을 초과했습니다",
           general: "크롤링 중 오류가 발생했습니다",
           unknown: "알 수 없는 오류가 발생했습니다",
           invalid_url: "올바르지 않은 URL입니다",
           site_not_found: "사이트를 찾을 수 없습니다",
           timeout: "요청 시간이 초과되었습니다",
           invalid_bbc_url: "올바른 BBC 뉴스 URL을 입력해주세요"
       },
       
       // ==================== 버튼 메시지 ====================
       crawlButtonMessages: {
           siteNotSelected: "사이트를 선택하세요",
           boardEmpty: "게시판을 입력하세요", 
           universalEmpty: "URL을 입력하세요",
           universalUrlError: "올바른 URL을 입력하세요",
           lemmyEmpty: "커뮤니티를 입력하세요",
           lemmyFormatError: "올바른 Lemmy 형식을 입력하세요",
           redditFormatError: "올바른 Reddit 형식을 입력하세요",
           crawling: "크롤링 중...",
           connecting: "연결 중...",
           analyzing: "분석 중..."
       },
       
       // ==================== 취소 메시지 ====================
       cancellationMessages: {
           crawl_cancelled: "크롤링이 취소되었습니다",
           cancelling: "크롤링을 취소하는 중...",
           cancel_requested: "취소 요청이 전송되었습니다"
       },
       
       // ==================== 크롤링 상태 표시 (UI용) ====================
        crawlingStatus: {
            found: "개 발견",
            page: "페이지",
            timeRemaining: "예상 시간",
            inProgress: "크롤링 중...",
            cancelled: "크롤링이 취소되었습니다.",
            processing: "처리 중...",
            connecting: "연결 중...",
            analyzing: "분석 중...",
            collecting: "수집 중...",
            completed: "크롤링 완료",
            cancelled: "크롤링이 취소되었습니다",
            noResults: "결과가 없습니다"
       },
       
       // ==================== 알림 메시지 ====================
       notifications: {
           file_too_large: "파일 크기는 5MB 이하로 제한됩니다",
           invalid_file_type: "이미지 파일만 업로드할 수 있습니다",
           no_data: "다운로드할 데이터가 없습니다",
           download_success: "파일이 다운로드되었습니다: {filename}"
       },
       
       // ==================== 피드백 시스템 ====================
       feedbackTitle: "PickPost에 의견 보내기",
       feedbackDescLabel: "의견을 설명해 주세요. (필수)",
       warningTitle: "민감한 정보는 포함하지 마세요", 
       warningDetail: "개인정보, 비밀번호, 금융정보 등은 포함하지 마세요.",
       submit: "보내기",
       fileAttach: "사진 첨부",
       fileAttached: "파일 첨부됨",
       
       messages: {
           feedback: {
               success: "피드백이 전송되었습니다. 감사합니다!",
               required: "피드백 내용을 입력해주세요",
               sending: "전송 중..."
           }
       },
       
       // ==================== 공지사항 ====================
       announcementTitle: "공지사항",
       announcementBtnText: "공지사항", 
       newBadge: "New",
       categories: {
           update: "업데이트",
           maintenance: "점검",
           feature: "기능",
           notice: "공지",
           security: "보안"
       },
       priorities: {
           high: "중요",
           normal: "일반",
           low: "참고"
       },
       
       // ==================== 기타 ====================
        shortcuts: "바로가기",
        addShortcut: "추가",
        shortcutName: "바로가기 이름",
        shortcutUrl: "게시판 URL 또는 이름",
        save: "저장",
        backBtn: "뒤로가기",
        privacy: "개인정보처리방침",
        terms: "약관",
        feedback: "피드백",
        business: "비즈니스",
        shortcutModalTitle: "사이트 추가",
        fillAllFields: "이름과 URL을 모두 입력해주세요.",
        maxShortcuts: "바로가기는 최대 5개까지만 추가할 수 있습니다.",
       
       // ==================== 도움말 텍스트 ====================
       lemmyHelpTitle: "Lemmy 커뮤니티 형식",
       lemmyHelpDescription: "커뮤니티명@인스턴스 형식으로 입력하세요\n예시: technology@lemmy.world",
       universalHelpTitle: "범용 크롤러 사용법",
       universalHelpDescription: "크롤링할 웹사이트의 완전한 URL을 입력하세요\n예시: https://example.com/forum",
       
       helpTexts: {
           lemmyHelp: {
               title: "Lemmy 커뮤니티 형식",
               description: "커뮤니티명@인스턴스 형식으로 입력하세요\n예시: technology@lemmy.world",
               examples: {
                   technology: "기술 관련 토론",
                   asklemmy: "Lemmy 커뮤니티에 질문하기"
               }
           },
           universalHelp: {
               title: "범용 크롤러 사용법",
               description: "크롤링할 웹사이트의 완전한 URL을 입력하세요\n예시: https://example.com/forum"
           }
       }
   },

   // ==================== 영어 ====================
   en: {
       // ==================== 기본 UI 요소 ====================
       start: "Start Crawling",
       clear: "Clear Results", 
       ok: "OK",
       cancel: "Cancel",
       download: "Download Excel",
       title: "PickPost",
       
       // ==================== 사이트 관련 ====================
       siteSelect: "Please select a site",

       // ==================== 사이트 이름 번역 ====================
       siteNames: {
           reddit: "Reddit",
           dcinside: "DCInside", 
           blind: "Blind",
           bbc: "BBC",
           lemmy: "Lemmy",
           universal: "Universal"
       },
       
       // ==================== 폼 라벨 ====================
       labels: {
           minViews: "Min Views",
           minRecommend: "Min Likes", 
           minComments: "Min Comments",
           startRank: "Start Rank",
           endRank: "End Rank",
           sortMethod: "Sort Method",
           timePeriod: "Time Period",
           advancedSearch: "Advanced Search",
           startDate: "Start Date",
           endDate: "End Date"
       },
       
       // ==================== 입력 필드 ====================
       sitePlaceholder: "Enter site name or address...",
       boardPlaceholder: "Enter board name...",
       boardPlaceholders: {
           default: "Enter board name...",
           reddit: "Subreddit name (e.g., askreddit)",
           dcinside: "Gallery name (e.g., programming)",
           blind: "Board name (e.g., developers)",
           lemmy: "community@instance (e.g., technology@lemmy.world)",
           bbc: "BBC section URL",
           universal: "Enter website URL to crawl..."
       },
       
       // ==================== 시간 필터 옵션 ====================
       timeFilterLabels: {
           hour: "1 Hour",
           day: "1 Day",
           week: "1 Week",
           month: "1 Month",
           year: "1 Year",
           all: "All Time",
           custom: "Custom Range"
       },
       
       // ==================== 정렬 옵션 ====================
       sortOptions: {
           latest: "Latest",
           popular: "Popular",
           views: "Most Viewed",
           comments: "Most Comments",
           
           // Reddit 전용
           reddit: {
               new: "New",
               top: "Top",
               hot: "Hot",
               best: "Best",
               rising: "Rising"
           },
           
           // 기타 사이트용
           other: {
               popular: "Popular",
               recommend: "Recommended", 
               recent: "Recent",
               comments: "Most Comments"
           }
       },
       
       // ==================== 결과 표시 ====================
        views: "Views",
        likes: "Likes",
        comments: "Comments",
        date: "Date",
        original: "Original Link",
        translation: "Translation",
        fail: "(Translation Failed)",
        
        resultTexts: {
            noResults: "No search results found",
            resultsCount: "Found {count} results",
            showing: "{start}-{end} / {total}",
            loadMore: "Load More"
        },

        results: {
            crawlingComplete: "Crawling Complete",
            completedAt: "Completed",
            totalPosts: "Total Posts",
            rankRange: "Rank Range", 
            estimatedPages: "Est. Pages",
            sourcesite: "Source Site",
            crawlingMode: "Crawling Mode",
            basic: "Basic",
            advanced: "Advanced Search",
            duration: "Duration", 
            viewOriginal: "View Original",
            seconds: "s",
            posts: "posts",
            page: "page", 
            found: "collected",
            noResults: "No results found"
        },

       
       // ==================== 크롤링 진행 상태 ====================
       crawlingProgress: {
           site_detecting: "Analyzing site...",
           site_connecting: "Connecting to {site}...",
           posts_collecting: "Collecting posts from {site}...",
           posts_filtering: "Filtering posts by criteria... ({matched}/{total})",
           posts_processing: "Processing data...",
           translation_preparing: "Preparing translation... ({count} posts)",
           translation_progress: "Translating... ({current}/{total})",
           finalizing: "Finalizing results...",
           
           reddit_analyzing: "Analyzing Reddit data...",
           dcinside_parsing: "Parsing DCInside...",
           blind_processing: "Processing Blind...",
           bbc_fetching: "Fetching BBC news...",
           lemmy_connecting: "Connecting to Lemmy server...",
           universal_parsing: "Analyzing webpage structure...",
           
           board_analyzing: "Analyzing {board} board...",
           page_collecting: "Collecting page {page}...",
           content_parsing: "Parsing content...",
           metadata_processing: "Processing metadata...",
           filtering_by_criteria: "Filtering by set criteria...",
           preparing_results: "Preparing results..."
       },
       
       // ==================== 완료 메시지 ====================
        completionMessages: {
            success: "Crawling complete: {count} posts",
            noData: "No results found", 
            error: "An error occurred",
            unified_complete: "Found {count} posts from {input} (Site: {site})",
            legacy_complete: "Crawling complete: {count} posts",
            crawl_complete: "Collected {count} posts from {site} {board} (Rank {start}-{end})",
            translation_complete: "Translation complete: processed {count} posts",
            reddit_complete: "Collected {count} posts from Reddit {board}",
            dcinside_complete: "Collected {count} posts from DCInside {board} gallery",
            blind_complete: "Collected {count} posts from Blind {board}",
            bbc_complete: "Collected {count} news from BBC {section}",
            lemmy_complete: "Collected {count} posts from Lemmy {board}",
            universal_complete: "Collected {count} posts from {input}",
            analysis_complete: "Site analysis complete: detected {site}"
       },
       
       // ==================== 에러 메시지 ====================
       errorMessages: {
           empty_input: "Please enter a site or board to crawl",
           site_detection_failed: "Cannot detect site: {input}",
           unsupported_site: "Unsupported site: {site}",
           connection_failed: "Failed to connect to {site}",
           no_posts_found: "No posts found matching criteria in {site} {board}",
           crawling_timeout: "Crawling timeout ({site})",
           invalid_board: "Invalid board: {board}",
           crawling_error: "Error occurred during crawling: {error}",
           translation_failed: "Error occurred during translation",
           analysis_failed: "Site analysis failed: {error}",
           rate_limited: "Rate limited. Please try again later",
           network_error: "Network connection problem",
           server_error: "Server error occurred",
           permission_denied: "Access permission denied",
           invalid_credentials: "Invalid authentication credentials",
           quota_exceeded: "Daily usage quota exceeded",
           general: "An error occurred during crawling",
           unknown: "Unknown error occurred",
           invalid_url: "Invalid URL",
           site_not_found: "Site not found",
           timeout: "Request timeout",
           invalid_bbc_url: "Please enter a valid BBC news URL"
       },
       
       // ==================== 버튼 메시지 ====================
       crawlButtonMessages: {
           siteNotSelected: "Select a site",
           boardEmpty: "Enter board name",
           universalEmpty: "Enter URL", 
           universalUrlError: "Enter valid URL",
           lemmyEmpty: "Enter community",
           lemmyFormatError: "Enter valid Lemmy format",
           redditFormatError: "Enter valid Reddit format",
           crawling: "Crawling...",
           connecting: "Connecting...",
           analyzing: "Analyzing..."
       },
       
       // ==================== 취소 메시지 ====================
       cancellationMessages: {
           crawl_cancelled: "Crawling has been cancelled",
           cancelling: "Cancelling crawl...",
           cancel_requested: "Cancel request sent"
       },
       
       // ==================== 크롤링 상태 표시 (UI용) ====================
        crawlingStatus: {
            found: "found",
            page: "page",
            timeRemaining: "estimated time",
            inProgress: "Crawling...",
            cancelled: "Crawling has been cancelled.",
            processing: "Processing...",
            connecting: "Connecting...", 
            analyzing: "Analyzing...",
            collecting: "Collecting...",
            completed: "Crawling Complete",
            cancelled: "Crawling has been cancelled",
            noResults: "No results found"
        },
       
       // ==================== 알림 메시지 ====================
       notifications: {
           file_too_large: "File size is limited to 5MB or less",
           invalid_file_type: "Only image files can be uploaded",
           no_data: "No data to download",
           download_success: "File downloaded: {filename}"
       },
       
       // ==================== 피드백 시스템 ====================
       feedbackTitle: "Send Feedback to PickPost",
       feedbackDescLabel: "Please describe your feedback. (Required)",
       warningTitle: "Do not include sensitive information",
       warningDetail: "Do not include personal information, passwords, financial information, etc.",
       submit: "Submit",
       fileAttach: "Attach Photo",
       fileAttached: "File Attached",
       
       messages: {
           feedback: {
               success: "Feedback sent successfully. Thank you!",
               required: "Please enter feedback content",
               sending: "Sending..."
           }
       },
       
       // ==================== 공지사항 ====================
       announcementTitle: "Announcements",
       announcementBtnText: "Announcements",
       newBadge: "New",
       categories: {
           update: "Update",
           maintenance: "Maintenance",
           feature: "Feature",
           notice: "Notice",
           security: "Security"
       },
       priorities: {
           high: "Important",
           normal: "Normal",
           low: "Reference"
       },
       
       // ==================== 기타 ====================
        shortcuts: "Shortcuts",
        addShortcut: "Add",
        shortcutName: "Shortcut Name",
        shortcutUrl: "Board URL or Name",
        save: "Save",
        backBtn: "Back",
        privacy: "Privacy Policy",
        terms: "Terms of Service",
        feedback: "Feedback",
        business: "Business",
        shortcutModalTitle: "Add Site",
        fillAllFields: "Please fill in both name and URL.",
        maxShortcuts: "You can add up to 5 shortcuts.",

       // ==================== 도움말 텍스트 ====================
       lemmyHelpTitle: "Lemmy Community Format",
       lemmyHelpDescription: "Enter community name in format: community@instance\nExample: technology@lemmy.world",
       universalHelpTitle: "Universal Crawler Usage",
       universalHelpDescription: "Enter the complete URL of the website to crawl\nExample: https://example.com/forum",
       
       helpTexts: {
           lemmyHelp: {
               title: "Lemmy Community Format",
               description: "Enter community name in format: community@instance\nExample: technology@lemmy.world",
               examples: {
                   technology: "Technology discussions",
                   asklemmy: "Ask the Lemmy community"
               }
           },
           universalHelp: {
               title: "Universal Crawler Usage",
               description: "Enter the complete URL of the website to crawl\nExample: https://example.com/forum"
           }
       }
   },
   
   // ==================== 일본어 ====================
   ja: {
       // ==================== 기본 UI 요소 ====================
       start: "クロール開始",
       clear: "結果をクリア",
       ok: "確認",
       cancel: "キャンセル",
       download: "Excelダウンロード",
       title: "PickPost",
       
       // ==================== 사이트 관련 ====================
       siteSelect: "サイトを選択してください",

       // ==================== 사이트 이름 번역 ====================
       siteNames: {
           reddit: "Reddit",
           dcinside: "DCインサイド", 
           blind: "Blind",
           bbc: "BBC",
           lemmy: "Lemmy",
           universal: "汎用"
       },
       
       // ==================== 폼 라벨 ====================
       labels: {
           minViews: "最小閲覧数",
           minRecommend: "最小推奨数", 
           minComments: "最小コメント数",
           startRank: "開始順位",
           endRank: "終了順位",
           sortMethod: "並び順",
           timePeriod: "期間",
           advancedSearch: "詳細検索",
           startDate: "開始日",
           endDate: "終了日"
       },
       
       // ==================== 입력 필드 ====================
       sitePlaceholder: "サイト名またはアドレスを入力してください...",
       boardPlaceholder: "掲示板名を入力してください...",
       boardPlaceholders: {
           default: "掲示板名を入力してください...",
           reddit: "サブレディット名 (例: askreddit)",
           dcinside: "ギャラリー名 (例: programming)",
           blind: "掲示板名 (例: 開発者)",
           lemmy: "コミュニティ@インスタンス (例: technology@lemmy.world)",
           bbc: "BBC セクション URL",
           universal: "クロールするウェブサイトのURLを入力してください..."
       },
       
       // ==================== 시간 필터 옵션 ====================
       timeFilterLabels: {
           hour: "1時間",
           day: "1日",
           week: "1週間",
           month: "1ヶ月",
           year: "1年",
           all: "全期間",
           custom: "カスタム範囲"
       },
       
       // ==================== 정렬 옵션 ====================
       sortOptions: {
           latest: "最新順",
           popular: "人気順",
           views: "閲覧数順",
           comments: "コメント順",
           
           // Reddit 전용
           reddit: {
               new: "新着",
               top: "人気投稿",
               hot: "ホット",
               best: "ベスト",
               rising: "急上昇"
           },
           
           // 기타 사이트용
           other: {
               popular: "人気順",
               recommend: "推奨順", 
               recent: "最新順",
               comments: "コメント順"
           }
       },
       
       // ==================== 결과 표시 ====================
        views: "閲覧数",
        likes: "推奨数",
        comments: "コメント数",
        date: "作成日",
        original: "原文リンク",
        translation: "翻訳",
        fail: "(翻訳失敗)",
        
        resultTexts: {
            noResults: "検索結果がありません",
            resultsCount: "{count}件の結果が見つかりました",
            showing: "{start}-{end} / {total}",
            loadMore: "もっと見る"
        },
        results: {
            crawlingComplete: "クロール完了",
            completedAt: "完了", 
            totalPosts: "総投稿数",
            rankRange: "順位範囲",
            estimatedPages: "推定ページ",
            sourcesite: "ソースサイト", 
            crawlingMode: "クロールモード",
            basic: "基本",
            advanced: "高度な検索",
            duration: "所要時間",
            viewOriginal: "原文を見る", 
            seconds: "秒",
            posts: "件",
            page: "ページ",
            found: "件収集", 
            noResults: "結果がありません"
        },
       
       // ==================== 크롤링 진행 상태 ====================
       crawlingProgress: {
           site_detecting: "サイト分析中...",
           site_connecting: "{site}に接続中...",
           posts_collecting: "{site}から投稿を収集中...",
           posts_filtering: "条件に合う投稿をフィルタリング中... ({matched}/{total})",
           posts_processing: "データ処理中...",
           translation_preparing: "翻訳準備中... ({count}個の投稿)",
           translation_progress: "翻訳進行中... ({current}/{total})",
           finalizing: "結果整理中...",
           
           reddit_analyzing: "Redditデータ分析中...",
           dcinside_parsing: "DCインサイド解析中...",
           blind_processing: "Blind処理中...",
           bbc_fetching: "BBCニュース取得中...",
           lemmy_connecting: "Lemmyサーバー接続中...",
           universal_parsing: "ウェブページ構造分析中...",
           
           board_analyzing: "{board}掲示板分析中...",
           page_collecting: "ページ{page}収集中...",
           content_parsing: "コンテンツ解析中...",
           metadata_processing: "メタデータ処理中...",
           filtering_by_criteria: "設定条件でフィルタリング中...",
           preparing_results: "結果準備中..."
       },
       
       // ==================== 완료 메시지 ====================
        completionMessages: {
            success: "クロール完了: {count}個の投稿",
            noData: "結果がありません",
            error: "エラーが発生しました",
            unified_complete: "{input}から{count}個の投稿を発見 (サイト: {site})",
            legacy_complete: "クロール完了: {count}個の投稿",
            crawl_complete: "{site} {board}から{count}個の投稿を収集完了 ({start}-{end}位)",
            translation_complete: "翻訳完了: {count}個の投稿を処理しました",
            reddit_complete: "Reddit {board}から{count}個の投稿を収集完了",
            dcinside_complete: "DCインサイド {board}ギャラリーから{count}個の投稿を収集完了",
            blind_complete: "Blind {board}から{count}個の投稿を収集完了",
            bbc_complete: "BBC {section}から{count}個のニュースを収集完了",
            lemmy_complete: "Lemmy {board}から{count}個の投稿を収集完了",
            universal_complete: "{input}から{count}個の投稿を収集完了",
            analysis_complete: "サイト分析完了: {site}を検出しました"
       },
       
       // ==================== 에러 메시지 ====================
       errorMessages: {
           empty_input: "クロールするサイトや掲示板を入力してください",
           site_detection_failed: "サイトを検出できません: {input}",
           unsupported_site: "サポートしていないサイトです: {site}",
           connection_failed: "{site}への接続に失敗しました",
           no_posts_found: "{site} {board}で条件に合う投稿が見つかりません",
           crawling_timeout: "クロールがタイムアウトしました ({site})",
           invalid_board: "正しくない掲示板です: {board}",
           crawling_error: "クロール中にエラーが発生しました: {error}",
           translation_failed: "翻訳中にエラーが発生しました",
           analysis_failed: "サイト分析に失敗しました: {error}",
           rate_limited: "リクエスト制限にかかりました。しばらく後に試してください",
           network_error: "ネットワーク接続に問題があります",
           server_error: "サーバーエラーが発生しました",
           permission_denied: "アクセス権限がありません",
           invalid_credentials: "認証情報が正しくありません",
           quota_exceeded: "日次使用量を超過しました",
           general: "クロール中にエラーが発生しました",
           unknown: "不明なエラーが発生しました",
           invalid_url: "正しくないURLです",
           site_not_found: "サイトが見つかりません",
           timeout: "リクエストタイムアウトです",
           invalid_bbc_url: "正しいBBC ニュースURLを入力してください"
       },
       
       // ==================== 버튼 메시지 ====================
       crawlButtonMessages: {
           siteNotSelected: "サイトを選択してください",
           boardEmpty: "掲示板を入力してください",
           universalEmpty: "URLを入力してください",
           universalUrlError: "正しいURLを入力してください", 
           lemmyEmpty: "コミュニティを入力してください",
           lemmyFormatError: "正しいLemmy形式を入力してください",
           redditFormatError: "正しいReddit形式を入力してください",
           crawling: "クロール中...",
           connecting: "接続中...",
           analyzing: "分析中..."
       },
       
       // ==================== 취소 메시지 ====================
       cancellationMessages: {
           crawl_cancelled: "クロールがキャンセルされました",
           cancelling: "クロールをキャンセル中...",
           cancel_requested: "キャンセルリクエストが送信されました"
       },
       
       // ==================== 크롤링 상태 표시 (UI용) ====================
        crawlingStatus: {
            found: "件発見",
            page: "ページ",
            timeRemaining: "予想時間",
            inProgress: "クロール中...",
            cancelled: "クロールがキャンセルされました。",
            processing: "処理中...",
            connecting: "接続中...",
            analyzing: "分析中...", 
            collecting: "収集中...",
            completed: "クロール完了",
            cancelled: "クロールがキャンセルされました",
            noResults: "結果がありません"
       },
       
       // ==================== 알림 메시지 ====================
       notifications: {
           file_too_large: "ファイルサイズは5MB以下に制限されています",
           invalid_file_type: "画像ファイルのみアップロードできます",
           no_data: "ダウンロードするデータがありません",
           download_success: "ファイルがダウンロードされました: {filename}"
       },
       
       // ==================== 피드백 시스템 ====================
       feedbackTitle: "PickPostに意見を送る",
       feedbackDescLabel: "意見を説明してください。（必須）",
       warningTitle: "機密情報は含めないでください",
       warningDetail: "個人情報、パスワード、金融情報などは含めないでください。",
       submit: "送信",
       fileAttach: "写真添付",
       fileAttached: "ファイル添付済み",
       
       messages: {
           feedback: {
               success: "フィードバックが送信されました。ありがとうございます！",
               required: "フィードバック内容を入力してください",
               sending: "送信中..."
           }
       },
       
       // ==================== 공지사항 ====================
       announcementTitle: "お知らせ",
       announcementBtnText: "お知らせ",
       newBadge: "New",
       categories: {
           update: "アップデート",
           maintenance: "メンテナンス",
           feature: "機能",
           notice: "お知らせ",
           security: "セキュリティ"
       },
       priorities: {
           high: "重要",
           normal: "通常",
           low: "参考"
       },
       
       // ==================== 기타 ====================
        shortcuts: "ショートカット",
        addShortcut: "追加",
        shortcutName: "ショートカット名",
        shortcutUrl: "掲示板URLまたは名前",
        save: "保存",
        backBtn: "戻る",
        privacy: "プライバシーポリシー",
        terms: "利用規約",
        feedback: "フィードバック",
        business: "ビジネス",
        shortcutModalTitle: "サイト追加",
        fillAllFields: "名前とURLを両方入力してください。", 
        maxShortcuts: "ショートカットは最大5つまで追加できます。",
       
       // ==================== 도움말 텍스트 ====================
       lemmyHelpTitle: "Lemmyコミュニティ形式",
       lemmyHelpDescription: "コミュニティ名@インスタンス形式で入力してください\n例: technology@lemmy.world",
       universalHelpTitle: "汎用クローラー使用方法",
       universalHelpDescription: "クロールするウェブサイトの完全なURLを入力してください\n例: https://example.com/forum",
       
       helpTexts: {
           lemmyHelp: {
               title: "Lemmyコミュニティ形式",
               description: "コミュニティ名@インスタンス形式で入力してください\n例: technology@lemmy.world",
               examples: {
                   technology: "技術関連ディスカッション",
                   asklemmy: "Lemmyコミュニティに質問"
               }
           },
           universalHelp: {
               title: "汎用クローラー使用方法",
               description: "クロールするウェブサイトの完全なURLを入力してください\n例: https://example.com/forum"
           }
       }
   }
};

// ==================== 정책 및 약관 ====================
const policies = {
   ko: {
       privacy: {
           title: "개인정보처리방침",
           content: `
               <h3>1. 개인정보의 처리목적</h3>
               <p>PickPost는 다음의 목적을 위하여 개인정보를 처리합니다:</p>
               <ul>
                   <li>서비스 제공 및 운영</li>
                   <li>사용자 문의사항 처리</li>
                   <li>서비스 개선을 위한 통계 분석</li>
               </ul>
               
               <h3>2. 개인정보의 처리 및 보유기간</h3>
               <p>PickPost는 법령에 따른 개인정보 보유·이용기간 또는 정보주체로부터 개인정보를 수집시에 동의받은 개인정보 보유·이용기간 내에서 개인정보를 처리·보유합니다.</p>
               
               <h3>3. 개인정보의 제3자 제공</h3>
               <p>PickPost는 정보주체의 개인정보를 개인정보의 처리목적에서 명시한 범위 내에서만 처리하며, 정보주체의 동의, 법률의 특별한 규정 등 개인정보보호법 제17조에 해당하는 경우에만 개인정보를 제3자에게 제공합니다.</p>
               
               <h3>4. 정보주체의 권리·의무 및 그 행사방법</h3>
               <p>정보주체는 PickPost에 대해 언제든지 다음 각 호의 개인정보 보호 관련 권리를 행사할 수 있습니다:</p>
               <ul>
                   <li>개인정보 처리정지 요구</li>
                   <li>개인정보 열람요구</li>
                   <li>개인정보 정정·삭제요구</li>
                   <li>개인정보 처리정지 요구</li>
               </ul>
           `
       },
       terms: {
           title: "서비스 이용약관",
           content: `
               <h3>제1조 (목적)</h3>
               <p>이 약관은 PickPost 서비스의 이용조건 및 절차에 관한 사항을 규정함을 목적으로 합니다.</p>
               
               <h3>제2조 (정의)</h3>
               <p>이 약관에서 사용하는 용어의 정의는 다음과 같습니다:</p>
               <ul>
                   <li>"서비스"라 함은 PickPost가 제공하는 모든 서비스를 의미합니다.</li>
                   <li>"이용자"라 함은 이 약관에 따라 회사가 제공하는 서비스를 받는 자를 의미합니다.</li>
               </ul>
               
               <h3>제3조 (약관의 효력 및 변경)</h3>
               <p>이 약관은 서비스 화면에 게시하거나 기타의 방법으로 이용자에게 공지함으로써 효력을 발생합니다.</p>
               
               <h3>제4조 (서비스의 제공 및 변경)</h3>
               <p>회사는 다음과 같은 업무를 수행합니다:</p>
               <ul>
                   <li>온라인 게시물 수집 및 정리 서비스</li>
                   <li>기타 회사가 정하는 업무</li>
               </ul>
           `
       }
   },
   ja: {
       privacy: {
           title: "プライバシーポリシー",
           content: `
               <h3>1. 個人情報の処理目的</h3>
               <p>PickPostは以下の目的のために個人情報を処理します：</p>
               <ul>
                   <li>サービス提供および運営</li>
                   <li>ユーザーお問い合わせ処理</li>
                   <li>サービス改善のための統計分析</li>
               </ul>
               
               <h3>2. 個人情報の処理および保有期間</h3>
               <p>PickPostは法令に基づく個人情報保有・利用期間または情報主体から個人情報を収集する際に同意を得た個人情報保有・利用期間内で個人情報を処理・保有します。</p>
               
               <h3>3. 個人情報の第三者提供</h3>
               <p>PickPostは情報主体の個人情報を個人情報の処理目的で明示した範囲内でのみ処理し、情報主体の同意、法律の特別な規定など個人情報保護法第17条に該当する場合にのみ個人情報を第三者に提供します。</p>
               
               <h3>4. 情報主体の権利・義務およびその行使方法</h3>
               <p>情報主体はPickPostに対していつでも以下の各号の個人情報保護関連権利を行使することができます：</p>
               <ul>
                   <li>個人情報処理停止要求</li>
                   <li>個人情報閲覧要求</li>
                   <li>個人情報訂正・削除要求</li>
                   <li>個人情報処理停止要求</li>
               </ul>
           `
       },
       terms: {
           title: "サービス利用規約",
           content: `
               <h3>第1条（目的）</h3>
               <p>この規約は、PickPostサービスの利用条件および手続きに関する事項を規定することを目的とします。</p>
               
               <h3>第2条（定義）</h3>
               <p>この規約で使用する用語の定義は以下の通りです：</p>
               <ul>
                   <li>「サービス」とは、PickPostが提供するすべてのサービスを意味します。</li>
                   <li>「利用者」とは、この規約に従って会社が提供するサービスを受ける者を意味します。</li>
               </ul>
               
               <h3>第3条（規約の効力および変更）</h3>
               <p>この規約は、サービス画面に掲示またはその他の方法で利用者に告知することにより効力を発生します。</p>
               
               <h3>第4条（サービスの提供および変更）</h3>
               <p>会社は以下の業務を行います：</p>
               <ul>
                   <li>オンライン投稿収集および整理サービス</li>
                   <li>その他会社が定める業務</li>
               </ul>
           `
       }
   },
   en: {
       privacy: {
           title: "Privacy Policy",
           content: `
               <h3>1. Purpose of Personal Information Processing</h3>
               <p>PickPost processes personal information for the following purposes:</p>
               <ul>
                   <li>Service provision and operation</li>
                   <li>User inquiry processing</li>
                   <li>Statistical analysis for service improvement</li>
               </ul>
               
               <h3>2. Personal Information Processing and Retention Period</h3>
               <p>PickPost processes and retains personal information within the personal information retention and use period according to laws or the personal information retention and use period agreed upon when collecting personal information from data subjects.</p>
               
               <h3>3. Third Party Provision of Personal Information</h3>
               <p>PickPost processes personal information of data subjects only within the scope specified in the purpose of personal information processing, and provides personal information to third parties only when it corresponds to Article 17 of the Personal Information Protection Act, such as consent of the data subject or special provisions of the law.</p>
               
               <h3>4. Rights and Obligations of Data Subjects and Methods of Exercise</h3>
               <p>Data subjects can exercise the following personal information protection-related rights against PickPost at any time:</p>
               <ul>
                   <li>Request to stop personal information processing</li>
                   <li>Request to view personal information</li>
                   <li>Request to correct or delete personal information</li>
                   <li>Request to stop personal information processing</li>
               </ul>
           `
       },
       terms: {
           title: "Terms of Service",
           content: `
               <h3>Article 1 (Purpose)</h3>
               <p>These terms aim to define the conditions and procedures for using PickPost services.</p>
               
               <h3>Article 2 (Definitions)</h3>
               <p>The definitions of terms used in these terms are as follows:</p>
               <ul>
                   <li>"Service" means all services provided by PickPost.</li>
                   <li>"User" means a person who receives services provided by the company in accordance with these terms.</li>
               </ul>
               
               <h3>Article 3 (Effect and Amendment of Terms)</h3>
               <p>These terms take effect by posting them on the service screen or notifying users by other means.</p>
               
               <h3>Article 4 (Provision and Change of Services)</h3>
               <p>The company performs the following tasks:</p>
               <ul>
                   <li>Online post collection and organization service</li>
                   <li>Other tasks determined by the company</li>
               </ul>
           `
       }
   }
};

// ==================== 유틸리티 함수 ====================

// 메시지 템플릿 처리 함수
function getLocalizedMessage(messageKey, templateData = {}, language = null) {
   const lang = language || currentLanguage || 'en';
   const languagePack = window.languages[lang] || window.languages.en;
   
   let template = '';
   
   // 키 경로 탐색 (예: "crawlingProgress.site_detecting")
   const keyParts = messageKey.split('.');
   let current = languagePack;
   
   for (const part of keyParts) {
       if (current && current[part]) {
           current = current[part];
       } else {
           console.warn(`Missing translation key: ${messageKey} for language: ${lang}`);
           // 영어 폴백
           if (lang !== 'en') {
               return getLocalizedMessage(messageKey, templateData, 'en');
           }
           return messageKey; // 최종 폴백
       }
   }
   
   template = current;
   
   // 템플릿 변수 치환
   if (templateData && typeof templateData === 'object') {
       Object.keys(templateData).forEach(key => {
           const placeholder = new RegExp(`\\{${key}\\}`, 'g');
           template = template.replace(placeholder, templateData[key] || '');
       });
   }
   
   return template;
}

// 진행률 메시지 생성 함수
function createProgressMessage(statusKey, statusData = {}) {
   return getLocalizedMessage(`crawlingProgress.${statusKey}`, statusData);
}

// 완료 메시지 생성 함수
function createCompletionMessage(completionKey, completionData = {}) {
   return getLocalizedMessage(`completionMessages.${completionKey}`, completionData);
}

// 에러 메시지 생성 함수
function createErrorMessage(errorKey, errorData = {}) {
   return getLocalizedMessage(`errorMessages.${errorKey}`, errorData);
}

// 취소 메시지 생성 함수
function createCancellationMessage(cancellationKey) {
   return getLocalizedMessage(`cancellationMessages.${cancellationKey}`);
}

// 전역 함수로 노출
window.getLocalizedMessage = getLocalizedMessage;
window.createProgressMessage = createProgressMessage;
window.createCompletionMessage = createCompletionMessage;
window.createErrorMessage = createErrorMessage;
window.createCancellationMessage = createCancellationMessage;

// ==================== 전역 변수 설정 ====================
window.languages = languages;
window.policies = policies;

// 언어팩 로드 완료 확인
console.log('✅ 언어팩 로드 완료:', Object.keys(window.languages));

// 기본 언어 설정 함수 (main.js에서 사용)
function getLocalizedMessage(messageKey, templateData = {}) {
   try {
       const lang = window.languages[window.currentLanguage || 'en'] || window.languages.en;
       
       const keyParts = messageKey.split('.');
       let current = lang;
       
       for (const part of keyParts) {
           if (current && current[part]) {
               current = current[part];
           } else {
               console.warn(`Missing translation key: ${messageKey}`);
               return messageKey;
           }
       }
       
       let message = current;
       
       // 템플릿 변수 치환
       if (templateData && typeof templateData === 'object') {
           Object.keys(templateData).forEach(key => {
               const placeholder = new RegExp(`\\{${key}\\}`, 'g');
               message = message.replace(placeholder, templateData[key] || '');
           });
       }
       
       return message;
   } catch (error) {
       console.error('언어 메시지 처리 오류:', error);
       return messageKey;
   }
}

// 전역으로 노출
window.getLocalizedMessage = getLocalizedMessage;
