    // PickPost 언어팩 - 모든 다국어 데이터 관리
    const languages = {
                ko: {
                    start: "크롤링 시작",
                    clear: "결과 지우기",
                    ok: "확인",
                    cancel: "취소",
                    download: "엑셀 다운로드",
                    siteSelect: "사이트를 선택하세요",
                    reddit: "레딧",
                    dcinside: "디시인사이드", 
                    blind: "블라인드",
                    lemmy: "레미",
                    original: "원문 링크",
                    redditLink: "레딧 링크",
                    translation: "번역",
                    fail: "(번역 실패)",
                    title: "PickPost",
                    sitePlaceholder: "사이트 이름 또는 주소를 입력하세요...",
                    boardPlaceholder: "게시판 이름을 입력하세요...",
                    minViews: "최소 조회수",
                    minRecommend: "최소 추천수",
                    minComments: "최소 댓글수",
                    startRank: "시작 순위",
                    endRank: "끝 순위",
                    sortMethod: "정렬 방식",
                    timePeriod: "기간",
                    startDate: "시작일",
                    endDate: "종료일",
                    advancedSearch: "고급 검색",
                    privacy: "개인정보처리방침",
                    terms: "약관",
                    feedback: "피드백",
                    ad: "광고",
                    terms: "서비스 약관",
                    business: "비즈니스",
                    backBtn: "뒤로가기",
                    hour: "시간",
                    day: "하루",
                    week: "일주일",
                    month: "한 달",
                    year: "일 년",
                    all: "전체",
                    custom: "사용자지정",
                    views: "조회수",
                    likes: "추천수",
                    comments: "댓글수",
                    date: "작성일",
                    shortcuts: "바로가기",
                    addShortcut: "추가",
                    shortcutName: "바로가기 이름",
                    shortcutUrl: "게시판 URL 또는 이름",
                    save: "저장",
                    original: "원문 링크",
                    fileAttach: "사진 첨부",
                    fileAttached: "파일 첨부됨",
                    fileAttachTitle: "사진을 첨부해 PickPost에서 의견을 더 잘 이해하는 데 도움이 됩니다.",
                    shortcutModalTitle: "사이트 추가",
                    shortcutNamePlaceholder: "사이트 이름",
                    shortcutUrlPlaceholder: "사이트 URL",
                    feedbackTitle: "PickPost에 의견 보내기",
                    feedbackDescLabel: "의견을 설명해 주세요. (필수)",
                    warningTitle: "민감한 정보는 포함하지 마세요",
                    warningDetail: "개인정보, 비밀번호, 금융정보 등은 포함하지 마세요. 제출된 피드백은 서비스 개선 목적으로만 사용됩니다.",
                    submit: "보내기",
                    announcementTitle: "공지사항",
                    announcementBtnText: "공지사항",
                    newBadge: "New",

                    // 정렬 방식 다국어
                    sortOptions: {
                        reddit: {
                            top: "인기순",
                            hot: "핫",
                            new: "최신순",
                            best: "베스트",
                            rising: "떠오름"
                        },
                        lemmy: {
                            Hot: "Hot",
                            Active: "Active", 
                            New: "최신순",
                            Old: "Old",
                            TopDay: "오늘 인기",
                            TopWeek: "주간 인기",
                            TopMonth: "월간 인기",
                            TopYear: "연간 인기",
                            TopAll: "역대 인기",
                            MostComments: "댓글 많은 순",
                            NewComments: "새 댓글순"
                        },
                        other: {
                            popular: "인기순",
                            recommend: "추천순",
                            recent: "최신순",
                            comments: "댓글순"
                        }
                    },
                    resultTexts: {
                        crawlComplete: "크롤링 완료",
                        totalPosts: "총 게시물",
                        rankRange: "순위 범위",
                        estimatedPages: "예상 페이지",
                        sourceSite: "수집 사이트",
                        crawlMode: "크롤링 모드",
                        elapsedTime: "소요 시간",
                        basicMode: "기본",
                        advancedMode: "고급 검색",
                        seconds: "초",
                        completedAt: "수집 완료",
                        noResults: "검색 결과가 없습니다.",
                        calculating: "계산 중",
                        estimatedTime: "예상 시간",
                        minutes: "분",
                        postsCollected: "개 수집",
                        page: "페이지"
                    },
                    // 사이트별 placeholder
                    boardPlaceholders: {
                        reddit: "서브레딧 이름을 입력하세요... (예: programming)",
                        lemmy: "커뮤니티@인스턴스 형태로 입력하세요... (예: technology@lemmy.world)",
                        dcinside: "갤러리 이름을 입력하세요... (예: programming)",
                        blind: "토픽 이름을 입력하세요... (예: 개발자)",
                        bbc: "BBC 섹션을 선택하세요...",
                        universal: "완전한 URL을 입력하세요... (예: https://example.com/board)",
                        default: "게시판 이름을 입력하세요..."
                    },
                    // 크롤링 버튼 상세 메시지
                    crawlButtonMessages: {
                        siteNotSelected: "사이트를 선택하세요",
                        boardEmpty: "게시판을 입력하세요",
                        lemmyFormatError: "형식: community@lemmy.world",
                        lemmyEmpty: "Lemmy 커뮤니티를 입력하세요",
                        universalUrlError: "올바른 URL을 입력하세요",
                        universalEmpty: "크롤링할 웹사이트 URL을 입력하세요",
                        redditFormatError: 'Reddit 게시판은 "/r/게시판명" 형태여야 합니다',
                        invalidInput: "올바른 형식으로 입력하세요"
                    },
                    //사용법 메세지
                    helpTexts: {
                        universalTitle: "사용법",
                        universalDesc: "• 완전한 URL: https://example.com/board\n• 간단한 도메인: example.com/board\n• www 포함: www.example.com/board",
                        lemmyTitle: "Lemmy 커뮤니티 입력 가이드",
                        lemmyDesc: "올바른 형식:\n• 커뮤니티명@인스턴스\n• 예: technology@lemmy.world\n• 예: asklemmy@lemmy.ml\n\n인기 인스턴스:\n• lemmy.world, lemmy.ml, beehaw.org\n• programming.dev, lemm.ee"
                        },
                    lemmyHelp: {
                        title: "Lemmy 커뮤니티 입력 가이드",
                        description: "올바른 형식:\n• 커뮤니티명@인스턴스\n• 예: technology@lemmy.world\n• 예: asklemmy@lemmy.ml\n\n인기 인스턴스:\n• lemmy.world, lemmy.ml, beehaw.org\n• programming.dev, lemm.ee",
                        examples: {
                            technology: "기술 관련 토론",
                            asklemmy: "질문과 답변"
                        },
                    },crawlingStatus: {
                        connecting: "서버에 연결 중...",
                        initializing: "크롤링 준비 중...",
                        crawling: "게시글 수집 중...",
                        processing: "데이터 처리 중...",
                        filtering: "조건에 맞는 게시글 필터링 중...",
                        translating: "제목 번역 중...",
                        finalizing: "결과 정리 중...",
                        complete: "수집 완료!",
                        found: "개 게시글 발견",
                        page: "페이지 탐색 중",
                        timeRemaining: "예상 남은 시간",
                        cancelled: "크롤링이 취소되었습니다",
                    },
                    // 진행 단계별 메시지
                    progressSteps: {
                        step1_timeFilter: "1단계. 사이트 시간 필터 적용",
                        step2_boardAccess: "2단계. 게시판 접근 중",
                        step3_dataCollection: "3단계. 데이터 수집 중",
                        step4_filtering: "4단계. 조건별 필터링",
                        step5_translation: "5단계. 제목 번역 중",
                        step6_finalization: "6단계. 결과 정리 중"
                    },
                    
                    // 진행 상황 상세 정보
                    progressDetails: {
                        timeFilterApplied: "시간 필터 적용됨",
                        boardConnected: "게시판 연결됨",
                        dataProcessing: "데이터 처리 중",
                        filteringPosts: "게시글 필터링 중",
                        translatingTitles: "제목 번역 중",
                        preparingResults: "결과 준비 중"
                    },
                    // 성공 메시지 템플릿들
                    successMessages: {
                        // 기본 수집 완료 메시지
                        collectionComplete: "✅ {site}에서 {count}개 게시물 수집 완료 (순위 {start}-{end})",
                        
                        // 다양한 상황별 메시지들
                        singlePost: "✅ {site}에서 1개 게시물 수집 완료",
                        noRankRange: "✅ {site}에서 {count}개 게시물 수집 완료",
                        withTimeFilter: "✅ {site}에서 {count}개 게시물 수집 완료 ({timeFilter}, 순위 {start}-{end})",
                        filteredResults: "✅ {site}에서 {total}개 중 조건에 맞는 {filtered}개 게시물 수집 완료",
                        
                        // 사이트별 특화 메시지
                        reddit: "✅ Reddit 서브레딧 '{board}'에서 {count}개 게시물 수집 완료",
                        lemmy: "✅ Lemmy 커뮤니티 '{board}'에서 {count}개 게시물 수집 완료",
                        dcinside: "✅ DC인사이드 '{board}' 갤러리에서 {count}개 게시물 수집 완료",
                        blind: "✅ 블라인드 '{board}' 토픽에서 {count}개 게시물 수집 완료",
                        bbc: "✅ BBC {board} 섹션에서 {count}개 뉴스 수집 완료",
                        universal: "✅ {board}에서 {count}개 게시물 수집 완료",
                        
                    },
                    messages: {
                        // 크롤링 관련
                        crawl: {
                            complete: "{site}에서 {count}개 게시물 수집 완료 (순위 {start}-{end})",
                            complete_filtered: "{site}에서 {count}개 게시물 수집 완료 (순위 {start}-{end}, 필터 적용)",
                            complete_date: "{site}에서 {count}개 게시물 수집 완료 ({start_date}~{end_date} 기간, 순위 {start}-{end})",
                            no_posts_found: "{site}에서 게시물을 찾을 수 없습니다",
                            no_matching_posts: "{site}에서 설정한 조건에 맞는 게시물을 찾을 수 없습니다",
                            loading: "크롤링 중..."
                        },
                        
                        // 피드백 관련  
                        feedback: {
                            success: "피드백이 전송되었습니다. 소중한 의견 감사합니다! 🙏",
                            success_simple: "피드백이 전송되었습니다. 감사합니다!",
                            required: "피드백 내용을 입력해주세요",
                            sending: "전송 중..."
                        },
                        
                        // 일반 알림
                        notifications: {
                            connection_failed: "서버 연결에 실패했습니다. 잠시 후 다시 시도해주세요",
                            file_too_large: "파일 크기는 5MB 이하로 제한됩니다",
                            download_success: "파일이 다운로드되었습니다: {filename}"
                        }
                    },
                    
                    // 시간 필터 표시용
                    timeFilterLabels: {
                        hour: "1시간",
                        day: "하루", 
                        week: "일주일",
                        month: "한 달",
                        year: "일 년",
                        all: "전체",
                        custom: "사용자 지정"
                    },
                    // 공지사항 카테고리별 이름
                    categories: {
                        update: "업데이트",
                        maintenance: "점검",
                        feature: "기능",
                        notice: "공지",
                        security: "보안"
                    },
                    
                    // 우선순위 텍스트
                    priorities: {
                        high: "중요",
                        normal: "일반",
                        low: "참고"
                    },
                    
                    // 공지사항 상태
                    newAnnouncement: "새 공지",
                    readAnnouncement: "확인됨",
                    
                    //알림
                    notifications: {
                        'feedback_required': '피드백 내용을 입력해주세요.',
                        'file_too_large': '파일 크기는 5MB 이하로 제한됩니다.',
                        'invalid_file_type': '이미지 파일만 업로드할 수 있습니다.',
                        'connection_failed': '서버 연결에 실패했습니다. 잠시 후 다시 시도해주세요.',
                        'no_data': '다운로드할 데이터가 없습니다.',
                        'download_success': '파일이 다운로드되었습니다 : {filename}'
                    },
                    
                    errorMessages: {
                        no_posts_found: "게시물을 찾을 수 없습니다",
                        no_matching_posts: "설정한 조건에 맞는 게시물을 찾을 수 없습니다"
                    }

                },
                en: {
                    start: "Start Crawling",
                    clear: "Clear Results",
                    cancel: "Cancel",
                    ok: "OK",
                    download: "Download Excel",
                    siteSelect: "Select a site",
                    reddit: "Reddit",
                    dcinside: "DCInside",
                    blind: "Blind",
                    lemmy: "Lemmy",
                    original: "Original Link",
                    redditLink: "Reddit Link",
                    translation: "Translation",
                    fail: "(Translation Failed)",
                    title: "PickPost",
                    sitePlaceholder: "Enter site name or URL...",
                    boardPlaceholder: "Enter board name...",
                    minViews: "Min Views",
                    minRecommend: "Min Likes",
                    minComments: "Min Comments",
                    startRank: "Start Rank",
                    endRank: "End Rank",
                    sortMethod: "Sort Method",
                    timePeriod: "Time Period",
                    startDate: "Start Date",
                    endDate: "End Date",
                    advancedSearch: "Advanced Search",
                    privacy: "Privacy Policy",
                    terms: "Terms",
                    feedback: "feedback",
                    terms: "Terms of Service",
                    ad: "Advertising",
                    business: "Business",
                    backBtn: "Back",
                    hour: "Hour",
                    day: "Day",
                    week: "Week",
                    month: "Month",
                    year: "Year",
                    all: "All Time",
                    custom: "Custom",
                    views: "Views",
                    likes: "Likes",
                    comments: "Comments",
                    date: "Date",
                    shortcuts: "Shortcuts",
                    addShortcut: "Add",
                    shortcutName: "Shortcut Name",
                    shortcutUrl: "Board URL or Name",
                    save: "Save",
                    original: "Original Link",
                    fileAttach: "Attach photo",
                    fileAttached: "File attached", 
                    fileAttachTitle: "Adding a photo helps PickPost better understand your feedback.",
                    shortcutModalTitle: "Add Site",
                    shortcutNamePlaceholder: "Site name",
                    shortcutUrlPlaceholder: "Site URL",
                    feedbackTitle: "Send feedback to PickPost",
                    feedbackDescLabel: "Please describe your feedback. (Required)",
                    warningTitle: "Do not include sensitive information",
                    warningDetail: "Do not include personal information, passwords, financial information, etc. Submitted feedback is used only for service improvement purposes.",
                    submit: "Send",
                    announcementTitle: "Announcements",
                    announcementBtnText: "Announcements", 
                    newBadge: "New",

                    // 정렬 방식 다국어
                    sortOptions: {
                        reddit: {
                            top: "Top",
                            hot: "Hot",
                            new: "New",
                            best: "Best",
                            rising: "Rising"
                        },
                        lemmy: {
                            Hot: "Hot",
                            Active: "Active",
                            New: "New",
                            Old: "Old",
                            TopDay: "Top Day",
                            TopWeek: "Top Week",
                            TopMonth: "Top Month",
                            TopYear: "Top Year",
                            TopAll: "Top All Time",
                            MostComments: "Most Comments",
                            NewComments: "New Comments"
                        },
                        other: {
                            popular: "Popular",
                            recommend: "Most Liked",
                            recent: "Recent",
                            comments: "Most Comments"
                        }
                    },
                    resultTexts: {
                        crawlComplete: "Crawling Complete",
                        totalPosts: "Total Posts",
                        rankRange: "Rank Range",
                        estimatedPages: "Est. Pages",
                        sourceSite: "Source Site",
                        crawlMode: "Crawl Mode",
                        elapsedTime: "Elapsed Time",
                        basicMode: "Basic",
                        advancedMode: "Advanced Filter",
                        seconds: "sec",
                        completedAt: "Completed",
                        noResults: "No search results found.",
                        calculating: "Calculating",
                        estimatedTime: "Est. Time",
                        minutes: "min",
                        postsCollected: " collected",
                        page: "page"
                    },

                    // 사이트별 placeholder
                    boardPlaceholders: {
                        reddit: "Enter subreddit name... (e.g., programming)",
                        lemmy: "Enter community@instance format... (e.g., technology@lemmy.world)",
                        dcinside: "Enter gallery name... (e.g., programming)",
                        blind: "Enter topic name... (e.g., developers)",
                        bbc: "Select BBC section...",
                        universal: "Enter complete URL... (e.g., https://example.com/board)",
                        default: "Enter board name..."
                    },
                    // 크롤링 버튼 상세 메시지
                    crawlButtonMessages: {
                        siteNotSelected: "Select a site",
                        boardEmpty: "Enter board name",
                        lemmyFormatError: "Format: community@lemmy.world",
                        lemmyEmpty: "Enter Lemmy community",
                        universalUrlError: "Enter a valid URL",
                        universalEmpty: "Enter website URL to crawl",
                        redditFormatError: 'Reddit board should be in "/r/boardname" format',
                        invalidInput: "Enter correct format"
                    },
                    //사용법 메세지
                    helpTexts: {
                        universalTitle: "Usage Guide",
                        universalDesc: "• Complete URL: https://example.com/board\n• Simple domain: example.com/board\n• With www: www.example.com/board",
                        lemmyTitle: "Lemmy Community Input Guide", 
                        lemmyDesc: "Correct format:\n• community@instance\n• Example: technology@lemmy.world\n• Example: asklemmy@lemmy.ml\n\nPopular instances:\n• lemmy.world, lemmy.ml, beehaw.org\n• programming.dev, lemm.ee"
                    },
                    lemmyHelp: {
                        title: "Lemmy Community Input Guide",
                        description: "Correct format:\n• community@instance\n• Example: technology@lemmy.world\n• Example: asklemmy@lemmy.ml\n\nPopular instances:\n• lemmy.world, lemmy.ml, beehaw.org\n• programming.dev, lemm.ee",
                        examples: {
                            technology: "Technology discussions",
                            asklemmy: "Questions and answers"
                        }
                    },
                    crawlingStatus: {
                        connecting: "Connecting to server...",
                        initializing: "Preparing crawl...",
                        crawling: "Collecting posts...",
                        processing: "Processing data...",
                        filtering: "Filtering posts by criteria...",
                        translating: "Translating titles...",
                        finalizing: "Finalizing results...",
                        complete: "Collection complete!",
                        found: " posts found",
                        page: "Exploring page",
                        timeRemaining: "Est. time remaining",
                        cancelled: "Crawling cancelled",
                    },
                    // 진행 단계별 메시지
                    progressSteps: {
                        step1_timeFilter: "Step 1. Applying site time filter",
                        step2_boardAccess: "Step 2. Accessing board",
                        step3_dataCollection: "Step 3. Collecting data",
                        step4_filtering: "Step 4. Filtering by criteria",
                        step5_translation: "Step 5. Translating titles",
                        step6_finalization: "Step 6. Finalizing results"
                    },
                    
                    // 진행 상황 상세 정보
                    progressDetails: {
                        timeFilterApplied: "Time filter applied",
                        boardConnected: "Board connected",
                        dataProcessing: "Processing data",
                        filteringPosts: "Filtering posts",
                        translatingTitles: "Translating titles",
                        preparingResults: "Preparing results"
                    },
                    // 성공 메시지 템플릿들
                    successMessages: {
                        // 기본 수집 완료 메시지
                        collectionComplete: "✅ Successfully collected {count} posts from {site} (ranks {start}-{end})",
                        
                        // 다양한 상황별 메시지들
                        singlePost: "✅ Successfully collected 1 post from {site}",
                        noRankRange: "✅ Successfully collected {count} posts from {site}",
                        withTimeFilter: "✅ Successfully collected {count} posts from {site} ({timeFilter}, ranks {start}-{end})",
                        filteredResults: "✅ Successfully collected {filtered} posts matching criteria out of {total} from {site}",
                        
                        // 사이트별 특화 메시지
                        reddit: "✅ Successfully collected {count} posts from Reddit subreddit '{board}'",
                        lemmy: "✅ Successfully collected {count} posts from Lemmy community '{board}'",
                        dcinside: "✅ Successfully collected {count} posts from DCInside '{board}' gallery",
                        blind: "✅ Successfully collected {count} posts from Blind '{board}' topic",
                        bbc: "✅ Successfully collected {count} news from BBC {board} section",
                        universal: "✅ Successfully collected {count} posts from {board}"
                    },
                    messages: {
                        // 크롤링 관련
                        crawl: {
                            complete: "Successfully collected {count} posts from {site} (ranks {start}-{end})",
                            complete_filtered: "Successfully collected {count} posts from {site} (ranks {start}-{end}, filtered)",
                            complete_date: "Successfully collected {count} posts from {site} ({start_date}~{end_date} period, ranks {start}-{end})",
                            no_posts_found: "No posts found on {site}",
                            no_matching_posts: "No posts matching your criteria found on {site}",
                            loading: "Crawling..."
                        },
                        
                        // 피드백 관련  
                        feedback: {
                            success: "Your feedback has been sent. Thank you for your valuable input! 🙏",
                            success_simple: "Your feedback has been sent. Thank you!",
                            required: "Please enter feedback content",
                            sending: "Sending..."
                        },
                        
                        // 일반 알림
                        notifications: {
                            connection_failed: "Failed to connect to server. Please try again later",
                            file_too_large: "File size must be 5MB or less",
                            download_success: "File has been downloaded: {filename}"
                        }
                    },
                    
                    // 시간 필터 표시용
                    timeFilterLabels: {
                        hour: "1 hour",
                        day: "1 day",
                        week: "1 week", 
                        month: "1 month",
                        year: "1 year",
                        all: "all time",
                        custom: "custom range"
                    },
                    // 공지사항 카테고리별 이름
                    categories: {
                        update: "Update",
                        maintenance: "Maintenance",
                        feature: "Feature",
                        notice: "Notice", 
                        security: "Security"
                    },
                    
                    // 우선순위 텍스트
                    priorities: {
                        high: "Important",
                        normal: "Normal",
                        low: "Info"
                    },
                    
                    // 공지사항 상태
                    newAnnouncement: "New",
                    readAnnouncement: "Read",

                    notifications: {
                        'feedback_required': 'Please enter feedback content.',
                        'file_too_large': 'File size must be 5MB or less.',
                        'invalid_file_type': 'Only image files can be uploaded.',
                        'connection_failed': 'Failed to connect to server. Please try again later.',
                        'no_data': 'No data to download.',
                        'download_success': 'File has been downloaded : {filename}'
                    },
                },
                ja: {
                    start: "クロール開始",
                    clear: "結果をクリア",
                    cancel: "キャンセル",
                    ok: "OK",
                    download: "Excelダウンロード",
                    siteSelect: "サイトを選択してください",
                    reddit: "レディット",
                    dcinside: "ディシインサイド",
                    blind: "ブラインド",
                    lemmy: "レミー",
                    original: "元のリンク", 
                    redditLink: "レディットリンク",
                    translation: "翻訳",
                    fail: "（翻訳失敗）",
                    title: "PickPost",
                    sitePlaceholder: "サイト名またはURLを入力してください...",
                    boardPlaceholder: "掲示板名を入力してください...",
                    minViews: "最小閲覧数",
                    minRecommend: "最小推薦数",
                    minComments: "最小コメント数",
                    startRank: "開始順位",
                    endRank: "終了順位",
                    sortMethod: "ソート方法",
                    timePeriod: "期間",
                    startDate: "開始日",
                    endDate: "終了日",
                    advancedSearch: "詳細検索",
                    privacy: "プライバシーポリシー",
                    terms: "利用規約",
                    feedback: "フィードバック",
                    terms: "利用規約",
                    ad: "広告",
                    business: "ビジネス",
                    backBtn: "戻る",
                    hour: "時間",
                    day: "日",
                    week: "週",
                    month: "月",
                    year: "年",
                    all: "全期間",
                    custom: "カスタム",
                    views: "閲覧数",
                    likes: "推薦数",
                    comments: "コメント数",
                    date: "作成日",
                    shortcuts: "ショートカット",
                    addShortcut: "ショートカット追加",
                    shortcutName: "ショートカット名",
                    shortcutUrl: "掲示板URLまたは名前",
                    save: "保存",
                    original: "元のリンク",
                    fileAttach: "写真を添付",
                    fileAttached: "ファイル添付済み",
                    fileAttachTitle: "写真を追加すると、PickPostがフィードバックをより良く理解するのに役立ちます。",
                    shortcutModalTitle: "サイト追加", 
                    shortcutNamePlaceholder: "サイト名",
                    shortcutUrlPlaceholder: "サイトURL",
                    loadingTexts: 'クロール中...',
                    feedbackTitle: "PickPostにフィードバックを送信",
                    feedbackDescLabel: "フィードバックの内容を説明してください。（必須）",
                    warningTitle: "機密情報は含めないでください",
                    warningDetail: "個人情報、パスワード、金融情報などは含めないでください。送信されたフィードバックはサービス改善目的でのみ使用されます。",
                    submit: "送信",
                    announcementTitle: "お知らせ",
                    announcementBtnText: "お知らせ",
                    newBadge: "New",

                    // 정렬 방식 다국어
                    sortOptions: {
                        reddit: {
                            top: "人気順",
                            hot: "ホット",
                            new: "最新順",
                            best: "ベスト",
                            rising: "急上昇"
                        },
                        lemmy: {
                            Hot: "ホット",
                            Active: "アクティブ",
                            New: "最新順",
                            Old: "古い順",
                            TopDay: "今日の人気",
                            TopWeek: "週間人気",
                            TopMonth: "月間人気",
                            TopYear: "年間人気",
                            TopAll: "全期間人気",
                            MostComments: "コメント多い順",
                            NewComments: "新着コメント順"
                        },
                        other: {
                            popular: "人気順",
                            recommend: "推薦順",
                            recent: "最新順",
                            comments: "コメント順"
                        }
                    },
                    resultTexts: {
                        crawlComplete: "クロール完了",
                        totalPosts: "総投稿数",
                        rankRange: "順位範囲",
                        estimatedPages: "推定ページ",
                        sourceSite: "収集サイト",
                        crawlMode: "クロールモード",
                        elapsedTime: "所要時間",
                        basicMode: "基本",
                        advancedMode: "高度フィルター",
                        seconds: "秒",
                        completedAt: "収集完了",
                        noResults: "検索結果が見つかりません。",
                        calculating: "計算中",
                        estimatedTime: "推定時間",
                        minutes: "分",
                        postsCollected: "件収集",
                        page: "ページ"
                    },
                    //사이트별 placeholder
                    boardPlaceholders: {
                        reddit: "サブレディット名を入力... (例: programming)",
                        lemmy: "コミュニティ@インスタンス形式で入力... (例: technology@lemmy.world)",
                        dcinside: "ギャラリー名を入力... (例: programming)",
                        blind: "トピック名を入力... (例: 開発者)",
                        bbc: "BBCセクションを選択...",
                        universal: "完全なURLを入力... (例: https://example.com/board)",
                        default: "掲示板名を入力..."
                    },
                    //크롤링 버튼 상세 메시지
                    crawlButtonMessages: {
                        siteNotSelected: "サイトを選択してください",
                        boardEmpty: "掲示板を入力してください",
                        lemmyFormatError: "形式: community@lemmy.world",
                        lemmyEmpty: "Lemmyコミュニティを入力してください",
                        universalUrlError: "正しいURLを入力してください",
                        universalEmpty: "クロールするウェブサイトURLを入力してください",
                        redditFormatError: 'Reddit掲示板は"/r/掲示板名"形式である必要があります',
                        invalidInput: "正しい形式で入力してください"
                    },
                    //사용법 메세지
                    helpTexts: {
                        universalTitle: "使用ガイド",
                        universalDesc: "• 完全なURL: https://example.com/board\n• シンプルなドメイン: example.com/board\n• wwwを含む: www.example.com/board",
                        lemmyTitle: "Lemmyコミュニティ入力ガイド",
                        lemmyDesc: "正しい形式:\n• コミュニティ@インスタンス\n• 例: technology@lemmy.world\n• 例: asklemmy@lemmy.ml\n\n人気インスタンス:\n• lemmy.world, lemmy.ml, beehaw.org\n• programming.dev, lemm.ee"
                    },
                    lemmyHelp: {
                        title: "Lemmyコミュニティ入力ガイド",
                        description: "正しい形式:\n• コミュニティ@インスタンス\n• 例: technology@lemmy.world\n• 例: asklemmy@lemmy.ml\n\n人気インスタンス:\n• lemmy.world, lemmy.ml, beehaw.org\n• programming.dev, lemm.ee",
                        examples: {
                            technology: "技術関連の議論",
                            asklemmy: "質問と回答"
                        }
                    },
                    crawlingStatus: {
                        connecting: "サーバーに接続中...",
                        initializing: "クロールの準備中...",
                        crawling: "投稿を収集中...",
                        processing: "データを処理中...",
                        filtering: "条件に合う投稿をフィルタリング中...",
                        translating: "タイトルを翻訳中...",
                        finalizing: "結果をまとめ中...",
                        complete: "収集完了！",
                        found: "件の投稿を発見",
                        page: "ページを探索中",
                        timeRemaining: "推定残り時間",
                        cancelled: "クロールがキャンセルされました",
                    },
                    // 진행 단계별 메시지
                    progressSteps: {
                        step1_timeFilter: "ステップ1. サイト時間フィルタ適用",
                        step2_boardAccess: "ステップ2. 掲示板アクセス中",
                        step3_dataCollection: "ステップ3. データ収集中", 
                        step4_filtering: "ステップ4. 条件別フィルタリング",
                        step5_translation: "ステップ5. タイトル翻訳中",
                        step6_finalization: "ステップ6. 結果整理中"
                    },
                    
                    // 진행 상황 상세 정보
                    progressDetails: {
                        timeFilterApplied: "時間フィルタが適用されました",
                        boardConnected: "掲示板に接続されました",
                        dataProcessing: "データ処理中",
                        filteringPosts: "投稿をフィルタリング中",
                        translatingTitles: "タイトルを翻訳中",
                        preparingResults: "結果を準備中"
                    },
                    // 성공 메시지 템플릿들
                    successMessages: {
                        // 기본 수집 완료 메시지
                        collectionComplete: "✅ {site}から{count}件の投稿を収集完了 (順位 {start}-{end})",
                        
                        // 다양한 상황별 메시지들
                        singlePost: "✅ {site}から1件の投稿を収集完了",
                        noRankRange: "✅ {site}から{count}件の投稿を収集完了",
                        withTimeFilter: "✅ {site}から{count}件の投稿を収集完了 ({timeFilter}、順位 {start}-{end})",
                        filteredResults: "✅ {site}から{total}件中条件に合う{filtered}件の投稿を収集完了",
                        
                        // 사이트별 특화 메시지
                        reddit: "✅ Redditサブレディット'{board}'から{count}件の投稿を収集完了",
                        lemmy: "✅ Lemmyコミュニティ'{board}'から{count}件の投稿を収集完了",
                        dcinside: "✅ DCインサイド'{board}'ギャラリーから{count}件の投稿を収集完了",
                        blind: "✅ ブラインド'{board}'トピックから{count}件の投稿を収集完了",
                        bbc: "✅ BBC {board}セクションから{count}件のニュースを収集完了",
                        universal: "✅ {board}から{count}件の投稿を収集完了"
                    },
                    messages: {
                        // 크롤링 관련
                        crawl: {
                            complete: "{site}から{count}件の投稿を収集完了 (順位 {start}-{end})",
                            complete_filtered: "{site}から{count}件の投稿を収集完了 (順位 {start}-{end}、フィルター適用)",
                            complete_date: "{site}から{count}件の投稿を収集完了 ({start_date}~{end_date} 期間、順位 {start}-{end})",
                            no_posts_found: "{site}で投稿が見つかりませんでした",
                            no_matching_posts: "{site}で設定した条件に合う投稿が見つかりませんでした",
                            loading: "クロール中..."
                        },
                        
                        // 피드백 관련  
                        feedback: {
                            success: "フィードバックが送信されました。貴重なご意見をありがとうございます！🙏",
                            success_simple: "フィードバックが送信されました。ありがとうございます！",
                            required: "フィードバック内容を入力してください",
                            sending: "送信中..."
                        },
                        
                        // 일반 알림
                        notifications: {
                            connection_failed: "サーバーへの接続に失敗しました。しばらくしてから再試行してください",
                            file_too_large: "ファイルサイズは5MB以下に制限されています",
                            download_success: "ファイルがダウンロードされました: {filename}"
                        }
                    },

                    // 시간 필터 표시용
                    timeFilterLabels: {
                        hour: "1時間",
                        day: "1日",
                        week: "1週間",
                        month: "1ヶ月", 
                        year: "1年",
                        all: "全期間",
                        custom: "カスタム範囲"
                    },
                    // 공지사항 카테고리별 이름
                    categories: {
                        update: "アップデート",
                        maintenance: "メンテナンス",
                        feature: "機能",
                        notice: "お知らせ",
                        security: "セキュリティ"
                    },
                    
                    // 우선순위 텍스트
                    priorities: {
                        high: "重要",
                        normal: "通常",
                        low: "参考"
                    },
                    
                    // 공지사항 상태
                    newAnnouncement: "新着",
                    readAnnouncement: "確認済み",

                    notifications: {
                        'feedback_required': 'フィードバック内容を入力してください。',
                        'file_too_large': 'ファイルサイズは5MB以下に制限されています。',
                        'invalid_file_type': '画像ファイルのみアップロードできます。',
                        'connection_failed': 'サーバーへの接続に失敗しました。しばらくしてから再試行してください。',
                        'no_data': 'ダウンロードするデータがありません。',
                        'download_success': 'ファイルがダウンロードされました : {filename}'
                    },
                }
            };


    // 약관 및 정책 내용
    const policies = {
        ko: {
            privacy: {
                title: "🔒 개인정보처리방침",
                content: `
                    <h3 style="color: #1a73e8; margin-bottom: 12px;">📌 수집하는 정보</h3>
                    <ul style="margin-bottom: 16px; line-height: 1.6;">
                        <li>사용자가 피드백을 제출할 때 작성한 내용</li>
                        <li>사용자의 시스템 정보 (브라우저 종류, 운영체제, 언어 설정 등)</li>
                        <li>화면 해상도, 시간대, 현재 페이지 URL</li>
                        <li>제출 시각</li>
                    </ul>

                    <h3 style="color: #1a73e8; margin-bottom: 12px;">📌 정보 수집 목적</h3>
                    <ul style="margin-bottom: 16px; line-height: 1.6;">
                        <li>오류 및 버그 개선</li>
                        <li>사용자 경험 품질 향상</li>
                        <li>통계적 분석 및 향후 기능 개선 참고</li>
                    </ul>

                    <h3 style="color: #1a73e8; margin-bottom: 12px;">📌 보관 및 삭제</h3>
                    <ul style="margin-bottom: 16px; line-height: 1.6;">
                        <li>수집된 피드백은 최대 6개월간 보관 후 자동 삭제됩니다.</li>
                        <li>사용자는 언제든지 자신의 피드백 삭제를 요청할 수 있습니다.</li>
                    </ul>

                    <h3 style="color: #1a73e8; margin-bottom: 12px;">📌 제3자 제공</h3>
                    <p style="line-height: 1.6;">수집된 정보는 외부에 제공되지 않으며, 마케팅 목적으로 사용되지 않습니다.</p>
                `
            },

            terms: {
                title: "📋 서비스 약관",
                content: `
                    <h3 style="color: #1a73e8; margin-bottom: 12px;">1. 서비스 개요</h3>
                    <p style="margin-bottom: 16px; line-height: 1.6;">PickPost는 사용자가 입력한 키워드 또는 URL을 기반으로 다양한 커뮤니티에서 게시글을 수집, 필터링, 정렬하여 보여주는 웹 기반 서비스입니다.</p>

                    <h3 style="color: #1a73e8; margin-bottom: 12px;">2. 책임 한계</h3>
                    <p style="margin-bottom: 16px; line-height: 1.6;">본 서비스는 단순한 검색/분석 도구로, 크롤링된 콘텐츠의 정확성, 최신성, 신뢰성에 대해 보증하지 않습니다.<br>외부 사이트 콘텐츠에 대한 저작권 및 책임은 해당 사이트에 있으며, PickPost는 이를 임의로 수정하거나 재배포하지 않습니다.</p>

                    <h3 style="color: #1a73e8; margin-bottom: 12px;">3. 사용자의 의무</h3>
                    <p style="margin-bottom: 16px; line-height: 1.6;">사용자는 본 서비스를 불법 목적, 자동화 도구 학습, 무단 수집 등에 사용해서는 안 됩니다.<br>비정상적인 접근 시도, 과도한 요청 발생 시 서비스 접속이 제한될 수 있습니다.</p>

                    <h3 style="color: #1a73e8; margin-bottom: 12px;">4. 데이터 처리</h3>
                    <p style="margin-bottom: 16px; line-height: 1.6;">검색 결과는 일시적으로 처리되며 서버에 저장되지 않습니다.<br>피드백 제출 시 제공된 시스템 정보는 오류 개선을 위한 용도로만 사용되며, 제3자에게 제공되지 않습니다.</p>

                    <h3 style="color: #1a73e8; margin-bottom: 12px;">5. 변경 및 종료</h3>
                    <p style="margin-bottom: 16px; line-height: 1.6;">PickPost는 서비스의 기능, UI, 정책 등을 사전 고지 없이 변경하거나 종료할 수 있습니다.<br>이용약관 및 개인정보처리방침은 변경 시 사이트를 통해 고지됩니다.</p>

                    <h3 style="color: #1a73e8; margin-bottom: 12px;">6. 기타</h3>
                    <p style="line-height: 1.6;">본 약관에 명시되지 않은 사항은 관계 법령 및 일반적인 인터넷 서비스 관행에 따릅니다.</p>
                `
            },

            business: {
                title: "💼 비즈니스 안내",
                content: `
                    <div style="background: #e8f0fe; padding: 16px; border-radius: 8px; margin-bottom: 16px;">
                        <p style="margin: 0; line-height: 1.6; font-weight: 500;">📢 PickPost는 다양한 커뮤니티 게시글을 수집·정리하여 사용자에게 보여주는 웹 기반 검색 도우미입니다.</p>
                    </div>

                    <p style="margin-bottom: 16px; line-height: 1.6;">현재 모든 콘텐츠는 사용자가 직접 입력한 키워드 또는 URL을 기반으로 수집되며, 광고나 협찬 콘텐츠는 포함되어 있지 않습니다.</p>

                    <h3 style="color: #1a73e8; margin-bottom: 12px;">📌 향후 광고 및 제휴 운영 방침</h3>
                    <ul style="margin-bottom: 16px; line-height: 1.6;">
                        <li>향후 일부 검색 결과에 <strong>스폰서 콘텐츠</strong>, <strong>제휴 링크</strong>, 또는 <strong>브랜드 큐레이션 콘텐츠</strong>가 포함될 수 있습니다.</li>
                        <li>광고 또는 제휴 콘텐츠는 <strong>[광고]</strong>, <strong>[제휴]</strong>, <strong>Sponsored</strong> 등의 명확한 표시와 함께 사용자에게 구분되어 제공됩니다.</li>
                        <li>광고 데이터는 크롤링 데이터와 별도로 처리되며, 피드백이나 검색 내용과 연결되지 않습니다.</li>
                    </ul>

                    <h3 style="color: #1a73e8; margin-bottom: 12px;">📌 비즈니스 협업/제휴 안내</h3>
                    <p style="margin-bottom: 16px; line-height: 1.6;">기업 또는 커뮤니티 운영자와의 협업을 통해 콘텐츠 제공, 크롤링 데이터 API 연동, 통계 리포트 자동화 등 다양한 B2B 연계를 고려하고 있습니다.<br>오픈 API, 대시보드 제공, 사용자 맞춤형 커스터마이징 기능도 협의 가능합니다.</p>

                    <h3 style="color: #1a73e8; margin-bottom: 12px;">📮 문의 방법</h3>
                    <ul style="line-height: 1.6;">
                        <li>📧 contact@pickpost.ai (예시 메일)</li>
                        <li>또는 피드백 창에 간단히 연락처를 남겨주시면 확인 후 연락드리겠습니다.</li>
                    </ul>
                `
            }
        },

        en: {
            privacy: {
                title: "🔒 Privacy Policy",
                content: `
                    <h3 style="color: #1a73e8; margin-bottom: 12px;">📌 Information We Collect</h3>
                    <ul style="margin-bottom: 16px; line-height: 1.6;">
                        <li>Content submitted when users provide feedback</li>
                        <li>User system information (browser type, operating system, language settings, etc.)</li>
                        <li>Screen resolution, timezone, current page URL</li>
                        <li>Submission time</li>
                    </ul>

                    <h3 style="color: #1a73e8; margin-bottom: 12px;">📌 Purpose of Collection</h3>
                    <ul style="margin-bottom: 16px; line-height: 1.6;">
                        <li>Bug fixes and error improvements</li>
                        <li>User experience quality enhancement</li>
                        <li>Statistical analysis and future feature improvement reference</li>
                    </ul>

                    <h3 style="color: #1a73e8; margin-bottom: 12px;">📌 Storage and Deletion</h3>
                    <ul style="margin-bottom: 16px; line-height: 1.6;">
                        <li>Collected feedback is stored for a maximum of 6 months and then automatically deleted.</li>
                        <li>Users can request deletion of their feedback at any time.</li>
                    </ul>

                    <h3 style="color: #1a73e8; margin-bottom: 12px;">📌 Third Party Sharing</h3>
                    <p style="line-height: 1.6;">Collected information is not shared with external parties and is not used for marketing purposes.</p>
                `
            },

            terms: {
                title: "📋 Terms of Service",
                content: `
                    <h3 style="color: #1a73e8; margin-bottom: 12px;">1. Service Overview</h3>
                    <p style="margin-bottom: 16px; line-height: 1.6;">PickPost is a web-based service that collects, filters, and sorts posts from various communities based on keywords or URLs entered by users.</p>

                    <h3 style="color: #1a73e8; margin-bottom: 12px;">2. Limitation of Liability</h3>
                    <p style="margin-bottom: 16px; line-height: 1.6;">This service is a simple search/analysis tool and does not guarantee the accuracy, currency, or reliability of crawled content.<br>Copyright and responsibility for external site content belongs to the respective sites, and PickPost does not arbitrarily modify or redistribute such content.</p>

                    <h3 style="color: #1a73e8; margin-bottom: 12px;">3. User Obligations</h3>
                    <p style="margin-bottom: 16px; line-height: 1.6;">Users must not use this service for illegal purposes, automated tool training, unauthorized collection, etc.<br>Service access may be restricted in case of abnormal access attempts or excessive requests.</p>

                    <h3 style="color: #1a73e8; margin-bottom: 12px;">4. Data Processing</h3>
                    <p style="margin-bottom: 16px; line-height: 1.6;">Search results are processed temporarily and are not stored on servers.<br>System information provided when submitting feedback is used only for error improvement purposes and is not provided to third parties.</p>

                    <h3 style="color: #1a73e8; margin-bottom: 12px;">5. Changes and Termination</h3>
                    <p style="margin-bottom: 16px; line-height: 1.6;">PickPost may change or terminate service functions, UI, policies, etc. without prior notice.<br>Terms of service and privacy policy changes will be announced through the site.</p>

                    <h3 style="color: #1a73e8; margin-bottom: 12px;">6. Other Matters</h3>
                    <p style="line-height: 1.6;">Matters not specified in these terms follow relevant laws and general internet service practices.</p>
                `
            },

            business: {
                title: "💼 Business Information",
                content: `
                    <div style="background: #e8f0fe; padding: 16px; border-radius: 8px; margin-bottom: 16px;">
                        <p style="margin: 0; line-height: 1.6; font-weight: 500;">📢 PickPost is a web-based search assistant that collects and organizes posts from various communities for users.</p>
                    </div>

                    <p style="margin-bottom: 16px; line-height: 1.6;">Currently, all content is collected based on keywords or URLs directly entered by users, and does not include advertisements or sponsored content.</p>

                    <h3 style="color: #1a73e8; margin-bottom: 12px;">📌 Future Advertising and Partnership Policy</h3>
                    <ul style="margin-bottom: 16px; line-height: 1.6;">
                        <li>In the future, some search results may include <strong>sponsored content</strong>, <strong>affiliate links</strong>, or <strong>brand curation content</strong>.</li>
                        <li>Advertising or partnership content will be clearly marked with <strong>[Ad]</strong>, <strong>[Partnership]</strong>, <strong>Sponsored</strong>, etc.</li>
                        <li>Advertising data is processed separately from crawling data and is not linked to feedback or search content.</li>
                    </ul>

                    <h3 style="color: #1a73e8; margin-bottom: 12px;">📌 Business Collaboration/Partnership Information</h3>
                    <p style="margin-bottom: 16px; line-height: 1.6;">We are considering various B2B connections such as content provision, crawling data API integration, and statistical report automation through collaboration with companies or community operators.<br>Open API, dashboard provision, and user-customized features are also negotiable.</p>

                    <h3 style="color: #1a73e8; margin-bottom: 12px;">📮 Contact Information</h3>
                    <ul style="line-height: 1.6;">
                        <li>📧 contact@pickpost.ai (example email)</li>
                        <li>Or simply leave your contact information in the feedback form and we will contact you after review.</li>
                    </ul>
                `
            }
        },

        ja: {
            privacy: {
                title: "🔒 プライバシーポリシー",
                content: `
                    <h3 style="color: #1a73e8; margin-bottom: 12px;">📌 収集する情報</h3>
                    <ul style="margin-bottom: 16px; line-height: 1.6;">
                        <li>ユーザーがフィードバックを提出する際に作成したコンテンツ</li>
                        <li>ユーザーのシステム情報（ブラウザの種類、OS、言語設定など）</li>
                        <li>画面解像度、タイムゾーン、現在のページURL</li>
                        <li>提出時刻</li>
                    </ul>

                    <h3 style="color: #1a73e8; margin-bottom: 12px;">📌 情報収集の目的</h3>
                    <ul style="margin-bottom: 16px; line-height: 1.6;">
                        <li>エラーやバグの改善</li>
                        <li>ユーザーエクスペリエンスの品質向上</li>
                        <li>統計的分析および今後の機能改善の参考</li>
                    </ul>

                    <h3 style="color: #1a73e8; margin-bottom: 12px;">📌 保管と削除</h3>
                    <ul style="margin-bottom: 16px; line-height: 1.6;">
                        <li>収集されたフィードバックは最大6ヶ月間保管後、自動削除されます。</li>
                        <li>ユーザーはいつでも自分のフィードバックの削除を要求できます。</li>
                    </ul>

                    <h3 style="color: #1a73e8; margin-bottom: 12px;">📌 第三者への提供</h3>
                    <p style="line-height: 1.6;">収集された情報は外部に提供されず、マーケティング目的で使用されません。</p>
                `
            },

            terms: {
                title: "📋 利用規約",
                content: `
                    <h3 style="color: #1a73e8; margin-bottom: 12px;">1. サービス概要</h3>
                    <p style="margin-bottom: 16px; line-height: 1.6;">PickPostは、ユーザーが入力したキーワードまたはURLに基づいて、様々なコミュニティから投稿を収集、フィルタリング、ソートして表示するウェブベースのサービスです。</p>

                    <h3 style="color: #1a73e8; margin-bottom: 12px;">2. 責任の制限</h3>
                    <p style="margin-bottom: 16px; line-height: 1.6;">このサービスは単純な検索/分析ツールであり、クロールされたコンテンツの正確性、最新性、信頼性を保証しません。<br>外部サイトのコンテンツに対する著作権と責任は該当サイトにあり、PickPostはこれを任意に修正または再配布しません。</p>

                    <h3 style="color: #1a73e8; margin-bottom: 12px;">3. ユーザーの義務</h3>
                    <p style="margin-bottom: 16px; line-height: 1.6;">ユーザーは本サービスを違法な目的、自動化ツールの学習、無断収集などに使用してはいけません。<br>異常なアクセス試行、過度なリクエストが発生した場合、サービスアクセスが制限される可能性があります。</p>

                    <h3 style="color: #1a73e8; margin-bottom: 12px;">4. データ処理</h3>
                    <p style="margin-bottom: 16px; line-height: 1.6;">検索結果は一時的に処理され、サーバーに保存されません。<br>フィードバック提出時に提供されたシステム情報はエラー改善目的のみに使用され、第三者に提供されません。</p>

                    <h3 style="color: #1a73e8; margin-bottom: 12px;">5. 変更と終了</h3>
                    <p style="margin-bottom: 16px; line-height: 1.6;">PickPostは、サービスの機能、UI、ポリシーなどを事前通知なしに変更または終了することができます。<br>利用規約およびプライバシーポリシーは変更時にサイトを通じて告知されます。</p>

                    <h3 style="color: #1a73e8; margin-bottom: 12px;">6. その他</h3>
                    <p style="line-height: 1.6;">本規約に明記されていない事項は、関係法令および一般的なインターネットサービス慣行に従います。</p>
                `
            },

            business: {
                title: "💼 ビジネス案内",
                content: `
                    <div style="background: #e8f0fe; padding: 16px; border-radius: 8px; margin-bottom: 16px;">
                        <p style="margin: 0; line-height: 1.6; font-weight: 500;">📢 PickPostは様々なコミュニティの投稿を収集・整理してユーザーに表示するウェブベースの検索アシスタントです。</p>
                    </div>

                    <p style="margin-bottom: 16px; line-height: 1.6;">現在、すべてのコンテンツはユーザーが直接入力したキーワードまたはURLに基づいて収集されており、広告やスポンサーコンテンツは含まれていません。</p>

                    <h3 style="color: #1a73e8; margin-bottom: 12px;">📌 今後の広告および提携運営方針</h3>
                    <ul style="margin-bottom: 16px; line-height: 1.6;">
                        <li>今後、一部の検索結果に<strong>スポンサーコンテンツ</strong>、<strong>提携リンク</strong>、または<strong>ブランドキュレーションコンテンツ</strong>が含まれる可能性があります。</li>
                        <li>広告または提携コンテンツは<strong>[広告]</strong>、<strong>[提携]</strong>、<strong>Sponsored</strong>などの明確な表示とともにユーザーに区別して提供されます。</li>
                        <li>広告データはクロールデータと別途処理され、フィードバックや検索内容と連結されません。</li>
                    </ul>

                    <h3 style="color: #1a73e8; margin-bottom: 12px;">📌 ビジネス協業/提携案内</h3>
                    <p style="margin-bottom: 16px; line-height: 1.6;">企業またはコミュニティ運営者との協業を通じて、コンテンツ提供、クロールデータAPI連動、統計レポート自動化など様々なB2B連携を検討しています。<br>オープンAPI、ダッシュボード提供、ユーザーカスタマイズ機能も協議可能です。</p>

                    <h3 style="color: #1a73e8; margin-bottom: 12px;">📮 お問い合わせ方法</h3>
                    <ul style="line-height: 1.6;">
                        <li>📧 contact@pickpost.ai（例示メール）</li>
                        <li>またはフィードバック欄に簡単に連絡先を残していただければ、確認後ご連絡いたします。</li>
                    </ul>
                `
            }
        }
    };

    // 언어팩 내보내기
    window.languages = languages;
    window.policies = policies;