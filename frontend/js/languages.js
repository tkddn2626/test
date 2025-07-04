// 전역 언어 객체 확인
if (typeof window.languages === 'undefined') {
   window.languages = {};
}

// PickPost 언어팩 - 정리된 완전한 버전
const languages = {
   ko: {
       // ==================== 기본 UI 요소 ====================
       start: "시작",
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
           universal: "수집 할 웹사이트 URL을 입력하세요..."
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
        loadMore: "더 보기",
        minutes: "min",
        seconds: "s",           
        calculating: "Calculating..."
        },

        results: {
            crawlingComplete: "수집 완료",
            completedAt: "완료",
            totalPosts: "총 게시물", 
            rankRange: "순위 범위",
            estimatedPages: "예상 페이지",
            sourcesite: "소스 사이트",
            crawlingMode: "수집 모드",
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
            success: "수집 완료: {count}개 게시물",
            noData: "결과가 없습니다",
            error: "오류가 발생했습니다",
            unified_complete: "{input}에서 {count}개 게시물 발견 (사이트: {site})",
            legacy_complete: "수집 완료: {count}개 게시물",
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
           empty_input: "수집 할 사이트나 게시판을 입력해주세요",
           site_detection_failed: "사이트를 감지할 수 없습니다: {input}",
           unsupported_site: "지원하지 않는 사이트입니다: {site}",
           connection_failed: "{site} 연결에 실패했습니다",
           no_posts_found: "{site} {board}에서 조건에 맞는 게시물을 찾을 수 없습니다",
           crawling_timeout: "시간이 초과되었습니다 ({site})",
           invalid_board: "올바르지 않은 게시판입니다: {board}",
           crawling_error: "수집 중 오류가 발생했습니다: {error}",
           translation_failed: "번역 중 오류가 발생했습니다",
           analysis_failed: "사이트 분석에 실패했습니다: {error}",
           rate_limited: "요청 제한에 걸렸습니다. 잠시 후 시도해주세요",
           network_error: "네트워크 연결에 문제가 있습니다",
           server_error: "서버 오류가 발생했습니다",
           permission_denied: "접근 권한이 없습니다",
           invalid_credentials: "인증 정보가 올바르지 않습니다",
           quota_exceeded: "일일 사용량을 초과했습니다",
           general: "수집 중 오류가 발생했습니다",
           unknown: "알 수 없는 오류가 발생했습니다",
           invalid_url: "올바르지 않은 URL입니다",
           site_not_found: "사이트를 찾을 수 없습니다",
           timeout: "요청 시간이 초과되었습니다",
           invalid_bbc_url: "올바른 BBC 뉴스 URL을 입력해주세요",
           
       },

        media: {
            no_media_found: "다운로드할 미디어가 없습니다",
            already_in_progress: "이미 미디어 다운로드가 진행 중입니다",
            site_info_missing: "사이트 정보가 없습니다",
            checking: "🔍 확인 중...",
            checking_support: "미디어 지원 여부 확인 중...",
            collecting: "📦 미디어 수집 중...",
            collecting_files: "미디어 파일 수집 및 다운로드 중...",
            compressing: "📁 압축 중...",
            creating_zip: "ZIP 파일 생성 중...",
            download_ready: "다운로드 준비 완료!",
            download_success: "미디어 다운로드 완료!\n파일: {file_count}개 ({size_mb}MB)",
            files_failed: "{failed_count}개 파일 다운로드 실패",
            download_failed_general: "미디어 다운로드에 실패했습니다",
            download_failed_with_error: "미디어 다운로드 실패: {error}",
            service_unavailable: "미디어 다운로드 기능이 현재 사용할 수 없습니다",
            service_not_found: "미디어 다운로드 서비스를 찾을 수 없습니다",
            
            all_downloads_failed: "모든 파일 다운로드에 실패했습니다",
            processing_error: "다운로드 처리 중 오류: {error}",
            file_access_failed: "파일 접근 불가: {url} (상태: {status})",
            file_size_exceeded: "파일 크기 초과: {filename} ({size_mb}MB)",
            download_failed: "다운로드 실패: {url} (상태: {status})",
            download_timeout: "다운로드 타임아웃: {url}",
            zip_creation_error: "ZIP 생성 오류: {error}",
            unsupported_site: "{site_type} 사이트는 미디어 다운로드를 지원하지 않습니다",
            file_delete_error: "파일 삭제 실패: {file_path} - {error}",
            old_files_cleanup: "{removed_count}개의 오래된 파일을 정리했습니다",
            cleanup_error: "파일 정리 중 오류 발생: {error}",
            download_complete: "다운로드 완료: 성공 {success_count}개, 실패 {failed_count}개",
            zip_creation_complete: "ZIP 압축 완료: {zip_path} ({file_count}개 파일)",
            download_task_error: "다운로드 작업 오류: {error}",
            post_extraction_error: "{site_type}에서 게시물 미디어 추출 실패: {error}"
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
           crawling: "수집 중...",
           connecting: "연결 중...",
           analyzing: "분석 중..."
       },
       
       // ==================== 취소 메시지 ====================
       cancellationMessages: {
           crawl_cancelled: "수집이 취소되었습니다",
           cancelling: "취소하는 중...",
           cancel_requested: "취소 요청이 전송되었습니다"
       },
       
       // ==================== 크롤링 상태 표시 (UI용) ====================
        crawlingStatus: {
            found: "개 발견",
            page: "페이지",
            timeRemaining: "예상 시간",
            inProgress: "수집 중...",
            cancelled: "취소되었습니다.",
            processing: "처리 중...",
            connecting: "연결 중...",
            analyzing: "분석 중...",
            collecting: "수집 중...",
            completed: "수집 완료",
            noResults: "결과가 없습니다"
       },
       
       // ==================== 알림 메시지 ====================
        notifications: {
            file_too_large: "파일 크기는 5MB 이하로 제한됩니다",
            invalid_file_type: "이미지 파일만 업로드할 수 있습니다",
            no_data: "다운로드할 데이터가 없습니다",
            download_success: "파일이 다운로드: {filename}"
        },
          // 확인 다이얼로그 
        confirmClose: "작성 중인 내용이 있습니다. 정말 닫으시겠습니까?",
        
        // 에러 복구 
        pageRefreshNeeded: "페이지를 새로고침해주세요.",
        connectionDropped: "연결이 예기치 않게 종료되었습니다",
        
        // 진행 상황 세분화 
        preparingCrawl: "수집 준비 중...",
        completedNoResults: "게시물 수집이 완료되었지만 결과가 없습니다.",
        
        // 자동완성 도움말 
        urlDetected: "URL 감지됨",
        formatSuggestion: "형식 제안",
    
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
        shortcutName: "사이트 이름",
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
       start: "Start",
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
            loadMore: "Load More",
            minutes: "min",
            seconds: "s",           
            calculating: "Calculating..."
        },

        results: {
            crawlingComplete: "Complete",
            completedAt: "Completed",
            totalPosts: "Total Posts",
            rankRange: "Rank Range", 
            estimatedPages: "Est. Pages",
            sourcesite: "Source Site",
            crawlingMode: "Collecting Mode",
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
                success: "Complete: {count} posts",
                noData: "No results found", 
                error: "An error occurred",
                unified_complete: "Found {count} posts from {input} (Site: {site})",
                legacy_complete: "Complete: {count} posts",
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
            invalid_bbc_url: "Please enter a valid BBC news URL",
        },

        media: {
            no_media_found: "No media found for download",
            already_in_progress: "Media download already in progress",
            site_info_missing: "Site information is missing",
            checking: "🔍 Checking...",
            checking_support: "Checking media support...",
            collecting: "📦 Collecting media...",
            collecting_files: "Collecting and downloading media files...",
            compressing: "📁 Compressing...",
            creating_zip: "Creating ZIP file...",
            download_ready: "Download ready!",
            download_success: "Media download complete!\nFiles: {file_count} ({size_mb}MB)",
            files_failed: "{failed_count} files failed to download",
            download_failed_general: "Media download failed",
            download_failed_with_error: "Media download failed: {error}",
            service_unavailable: "Media download service is currently unavailable",
            service_not_found: "Media download service not found",
            
            all_downloads_failed: "All file downloads failed",
            processing_error: "Download processing error: {error}",
            file_access_failed: "File access failed: {url} (status: {status})",
            file_size_exceeded: "File size exceeded: {filename} ({size_mb}MB)",
            download_failed: "Download failed: {url} (status: {status})",
            download_timeout: "Download timeout: {url}",
            zip_creation_error: "ZIP creation error: {error}",
            unsupported_site: "{site_type} site does not support media download",
            file_delete_error: "File deletion failed: {file_path} - {error}",
            old_files_cleanup: "Cleaned up {removed_count} old files",
            cleanup_error: "Error during file cleanup: {error}",
            download_complete: "Download complete: {success_count} successful, {failed_count} failed",
            zip_creation_complete: "ZIP compression complete: {zip_path} ({file_count} files)",
            download_task_error: "Download task error: {error}",
            post_extraction_error: "Failed to extract media from {site_type} post: {error}"
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
           crawl_cancelled: "Collecting has been cancelled",
           cancelling: "Cancelling collect...",
           cancel_requested: "Cancel request sent"
       },
       
       // ==================== 크롤링 상태 표시 (UI용) ====================
        crawlingStatus: {
            found: "found",
            page: "page",
            timeRemaining: "estimated time",
            inProgress: "Crollecting...",
            cancelled: "Collecting has been cancelled.",
            processing: "Processing...",
            connecting: "Connecting...", 
            analyzing: "Analyzing...",
            collecting: "Collecting...",
            completed: "Complete",
            noResults: "No results found"
        },
       
       // ==================== 알림 메시지 ====================
       notifications: {
           file_too_large: "File size is limited to 5MB or less",
           invalid_file_type: "Only image files can be uploaded",
           no_data: "No data to download",
           download_success: "File downloaded: {filename}"
       },
        confirmClose: "There is content being written. Are you sure you want to close?",
        pageRefreshNeeded: "Please refresh the page.",
        connectionDropped: "Connection was unexpectedly closed",
        preparingCrawl: "Preparing to collect...",
        completedNoResults: "Collecting completed but no results found.",
        urlDetected: "URL detected",
        formatSuggestion: "Format suggestion",
           
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
        shortcutName: "Site Name",
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
            loadMore: "もっと見る",
            minutes: "min",
            seconds: "s",           
            calculating: "Calculating..."
        },
        results: {
            crawlingComplete: "収集完了",
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
            invalid_bbc_url: "正しいBBC ニュースURLを入力してください",

        },

        media: {
                    // 새로 추가된 메시지들
                    no_media_found: "ダウンロードするメディアが見つかりません",
                    already_in_progress: "メディアダウンロードが既に進行中です",
                    site_info_missing: "サイト情報がありません",
                    checking: "🔍 確認中...",
                    checking_support: "メディアサポートを確認中...",
                    collecting: "📦 メディア収集中...",
                    collecting_files: "メディアファイルの収集とダウンロード中...",
                    compressing: "📁 圧縮中...",
                    creating_zip: "ZIPファイル作成中...",
                    download_ready: "ダウンロード準備完了！",
                    download_success: "メディアダウンロード完了！\nファイル: {file_count}個 ({size_mb}MB)",
                    files_failed: "{failed_count}個のファイルダウンロードに失敗",
                    download_failed_general: "メディアダウンロードに失敗しました",
                    download_failed_with_error: "メディアダウンロード失敗: {error}",
                    service_unavailable: "メディアダウンロード機能は現在利用できません",
                    service_not_found: "メディアダウンロードサービスが見つかりません",
                    
                    // 基本メッセージ
                    all_downloads_failed: "すべてのファイルダウンロードに失敗しました",
                    processing_error: "ダウンロード処理エラー: {error}",
                    file_access_failed: "ファイルアクセス失敗: {url} (ステータス: {status})",
                    file_size_exceeded: "ファイルサイズ超過: {filename} ({size_mb}MB)",
                    download_failed: "ダウンロード失敗: {url} (ステータス: {status})",
                    download_timeout: "ダウンロードタイムアウト: {url}",
                    zip_creation_error: "ZIP作成エラー: {error}",
                    unsupported_site: "{site_type}サイトはメディアダウンロードをサポートしていません",
                    file_delete_error: "ファイル削除失敗: {file_path} - {error}",
                    old_files_cleanup: "{removed_count}個の古いファイルをクリーンアップしました",
                    cleanup_error: "ファイルクリーンアップ中にエラーが発生: {error}",
                    download_complete: "ダウンロード完了: 成功 {success_count}個、失敗 {failed_count}個",
                    zip_creation_complete: "ZIP圧縮完了: {zip_path} ({file_count}個のファイル)",
                    download_task_error: "ダウンロードタスクエラー: {error}",
                    post_extraction_error: "{site_type}の投稿からメディア抽出に失敗: {error}"
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
                completed: "収集完了",
                noResults: "結果がありません"
        },
        
        // ==================== 알림 메시지 ====================
        notifications: {
            file_too_large: "ファイルサイズは5MB以下に制限されています",
            invalid_file_type: "画像ファイルのみアップロードできます",
            no_data: "ダウンロードするデータがありません",
            download_success: "ファイルがダウンロードされました: {filename}"
        },

            confirmClose: "作成中の内容があります。本当に閉じますか？",
            pageRefreshNeeded: "ページを更新してください。",
            connectionDropped: "接続が予期せず終了しました",
            preparingCrawl: "クロール準備中...",
            completedNoResults: "クロールが完了しましたが、結果がありません。",
            urlDetected: "URL検出済み",
            formatSuggestion: "形式提案",

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
               <p>PickPost는 개인정보를 수집하지 않으며, 단기 세션 내에서만 데이터를 처리합니다. 모든 데이터는 Excel 다운로드 후 즉시 삭제됩니다.</p>
               
               <h3>3. 개인정보의 제3자 제공</h3>
               <p>PickPost는 개인정보를 수집하지 않으므로 제3자에게 제공하지 않습니다.</p>
               
               <h3>4. 개인정보보호 책임자</h3>
               <p>개인정보 관련 문의사항은 피드백 기능을 통해 연락해 주시기 바랍니다.</p>
           `
       },
       terms: {
           title: "서비스 이용약관",
           content: `
               <h3>제1조 (목적)</h3>
               <p>이 약관은 PickPost 웹 크롤링 서비스의 이용조건 및 절차에 관한 사항을 규정함을 목적으로 합니다.</p>
               
               <h3>제2조 (정의)</h3>
               <p>이 약관에서 사용하는 용어의 정의는 다음과 같습니다:</p>
               <ul>
                   <li>"서비스"라 함은 PickPost가 제공하는 공개 웹 콘텐츠 수집 및 정리 서비스를 의미합니다.</li>
                   <li>"이용자"라 함은 이 약관에 따라 서비스를 이용하는 자를 의미합니다.</li>
                   <li>"크롤링"이라 함은 공개된 웹사이트에서 HTML 파싱을 통해 정보를 수집하는 행위를 의미합니다.</li>
               </ul>
               
               <h3>제3조 (서비스의 범위와 제한)</h3>
               <p>PickPost는 다음과 같은 서비스를 제공합니다:</p>
               <ul>
                   <li>공개된 소셜미디어 콘텐츠 수집 (Reddit, Lemmy 등)</li>
                   <li>HTML 파싱 기반 데이터 수집 (API 우회 없음)</li>
                   <li>수집된 데이터의 Excel 형태 다운로드 지원</li>
               </ul>
               <p><strong>서비스 제한사항:</strong></p>
               <ul>
                   <li>로그인이 필요한 비공개 영역은 접근하지 않습니다</li>
                   <li>개인정보는 수집하지 않습니다</li>
                   <li>요청 속도 제한(Rate Limiting)이 적용됩니다</li>
               </ul>
               
               <h3>제4조 (이용자의 책임)</h3>
               <p><strong>⚠️ 중요: 크롤링 대상 사이트의 법적 책임은 이용자에게 있습니다</strong></p>
               <ul>
                   <li>이용자는 크롤링하려는 사이트의 이용약관(TOS) 및 robots.txt를 확인할 책임이 있습니다</li>
                   <li>크롤링으로 인한 모든 법적 책임은 이용자가 부담합니다</li>
                   <li>과도한 요청으로 대상 사이트에 부하를 주어서는 안 됩니다</li>
                   <li>수집된 데이터의 사용에 대한 책임은 이용자에게 있습니다</li>
                   <li>저작권, 개인정보보호법 등 관련 법령을 준수해야 합니다</li>
               </ul>
               
               <h3>제5조 (금지행위)</h3>
               <p>이용자는 다음 행위를 하여서는 안 됩니다:</p>
               <ul>
                   <li>대상 사이트의 이용약관을 위반하는 크롤링</li>
                   <li>개인정보가 포함된 비공개 정보에 대한 무단 접근</li>
                   <li>과도한 요청으로 서비스 방해를 야기하는 행위</li>
                   <li>불법적인 목적으로 수집된 데이터를 사용하는 행위</li>
               </ul>
               
               <h3>제6조 (서비스 제공자의 면책)</h3>
               <ul>
                   <li>PickPost는 이용자의 크롤링 행위로 인한 법적 분쟁에 대해 책임을 지지 않습니다</li>
                   <li>대상 사이트와의 법적 문제는 이용자가 직접 해결해야 합니다</li>
                   <li>PickPost는 도구를 제공할 뿐이며, 사용에 대한 책임은 이용자에게 있습니다</li>
                   <li>수집된 데이터의 정확성이나 완전성을 보장하지 않습니다</li>
               </ul>
               
               <h3>제7조 (권장사항)</h3>
               <p>안전한 서비스 이용을 위해 다음을 권장합니다:</p>
               <ul>
                   <li>크롤링 전 대상 사이트의 robots.txt 확인</li>
                   <li>적절한 요청 간격 유지</li>
                   <li>대상 사이트의 이용약관 숙지</li>
                   <li>개인정보보호법 등 관련 법령 준수</li>
               </ul>
               
               <h3>제8조 (약관의 효력 및 변경)</h3>
               <p>이 약관은 서비스 화면에 게시함으로써 효력을 발생하며, 관련 법령 변경시 사전 공지 후 수정될 수 있습니다.</p>
           `
       },
       business: {
            title: "💼 비즈니스 안내",
            content: `
                <div style="line-height: 1.8;">
                    <h3>🚀 PickPost 비즈니스 솔루션</h3>
                    <p>PickPost는 공개된 웹 데이터를 안전하고 효율적으로 수집·분석할 수 있는 법적 리스크가 낮은 도구입니다.</p>
                    
                    <h4>📊 핵심 안전 기능</h4>
                    <ul>
                        <li><strong>공개 데이터만 수집:</strong> 로그인 필요 영역 배제</li>
                        <li><strong>HTML 파싱 기반:</strong> API 제한 우회 없음</li>
                        <li><strong>개인정보 미수집:</strong> GDPR 등 개인정보보호법 준수</li>
                        <li><strong>요청 속도 제한:</strong> 대상 사이트 부하 최소화</li>
                        <li><strong>단기 세션:</strong> 데이터 즉시 삭제</li>
                    </ul>
                    
                    <h4>💼 비즈니스 활용 (합법적 용도)</h4>
                    <ul>
                        <li><strong>공개 브랜드 모니터링:</strong> 소셜미디어 언급 추적</li>
                        <li><strong>시장 동향 분석:</strong> 공개 포럼 트렌드 파악</li>
                        <li><strong>경쟁사 공개 정보 분석:</strong> 공개된 발표 내용 수집</li>
                        <li><strong>콘텐츠 연구:</strong> 공개 게시물 패턴 분석</li>
                    </ul>
                    
                    <h4>⚖️ 법적 준수사항</h4>
                    <p><strong>이용자는 반드시 확인해야 합니다:</strong></p>
                    <ul>
                        <li>대상 사이트의 이용약관 및 robots.txt</li>
                        <li>관련 개인정보보호법 및 저작권법</li>
                        <li>수집 데이터의 적법한 사용 범위</li>
                    </ul>
                    
                    <h4>📞 문의하기</h4>
                    <p>법적 준수사항이나 비즈니스 활용에 대한 문의는 피드백 기능을 통해 연락해 주세요.</p>
                </div>
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
               <p>PickPost does not collect personal information and only processes data within short-term sessions. All data is immediately deleted after Excel download.</p>
               
               <h3>3. Third Party Provision of Personal Information</h3>
               <p>PickPost does not collect personal information and therefore does not provide it to third parties.</p>
               
               <h3>4. Personal Information Protection Officer</h3>
               <p>For personal information inquiries, please contact us through the feedback feature.</p>
           `
       },
       terms: {
           title: "Terms of Service",
           content: `
               <h3>Article 1 (Purpose)</h3>
               <p>These terms aim to define the conditions and procedures for using PickPost web crawling services.</p>
               
               <h3>Article 2 (Definitions)</h3>
               <p>The definitions of terms used in these terms are as follows:</p>
               <ul>
                   <li>"Service" means the public web content collection and organization service provided by PickPost.</li>
                   <li>"User" means a person who uses the service in accordance with these terms.</li>
                   <li>"Crawling" means the act of collecting information from publicly available websites through HTML parsing.</li>
               </ul>
               
               <h3>Article 3 (Service Scope and Limitations)</h3>
               <p>PickPost provides the following services:</p>
               <ul>
                   <li>Collection of public social media content (Reddit, Lemmy, etc.)</li>
                   <li>HTML parsing-based data collection (no API circumvention)</li>
                   <li>Excel format download support for collected data</li>
               </ul>
               <p><strong>Service Limitations:</strong></p>
               <ul>
                   <li>No access to private areas requiring login</li>
                   <li>No collection of personal information</li>
                   <li>Rate limiting is applied</li>
               </ul>
               
               <h3>Article 4 (User Responsibilities)</h3>
               <p><strong>⚠️ Important: Users are legally responsible for crawling target sites</strong></p>
               <ul>
                   <li>Users are responsible for checking the Terms of Service (TOS) and robots.txt of sites they intend to crawl</li>
                   <li>Users bear all legal responsibility for crawling activities</li>
                   <li>Users must not burden target sites with excessive requests</li>
                   <li>Users are responsible for the use of collected data</li>
                   <li>Users must comply with relevant laws including copyright and privacy protection laws</li>
               </ul>
               
               <h3>Article 5 (Prohibited Activities)</h3>
               <p>Users must not engage in the following activities:</p>
               <ul>
                   <li>Crawling that violates target site terms of service</li>
                   <li>Unauthorized access to private information containing personal data</li>
                   <li>Activities that cause service disruption through excessive requests</li>
                   <li>Using collected data for illegal purposes</li>
               </ul>
               
               <h3>Article 6 (Service Provider Disclaimer)</h3>
               <ul>
                   <li>PickPost is not responsible for legal disputes arising from user crawling activities</li>
                   <li>Users must directly resolve legal issues with target sites</li>
                   <li>PickPost only provides tools; users are responsible for their use</li>
                   <li>PickPost does not guarantee the accuracy or completeness of collected data</li>
               </ul>
               
               <h3>Article 7 (Recommendations)</h3>
               <p>For safe service use, we recommend:</p>
               <ul>
                   <li>Checking target site robots.txt before crawling</li>
                   <li>Maintaining appropriate request intervals</li>
                   <li>Understanding target site terms of service</li>
                   <li>Complying with relevant laws including privacy protection laws</li>
               </ul>
               
               <h3>Article 8 (Terms Effectiveness and Amendment)</h3>
               <p>These terms take effect by posting on the service screen and may be modified after prior notice when relevant laws change.</p>
           `
       },
       business: {
            title: "💼 Business Information",
            content: `
                <div style="line-height: 1.8;">
                    <h3>🚀 PickPost Business Solutions</h3>
                    <p>PickPost is a low legal-risk tool for safely and efficiently collecting and analyzing public web data.</p>
                    
                    <h4>📊 Core Safety Features</h4>
                    <ul>
                        <li><strong>Public Data Only:</strong> Excludes login-required areas</li>
                        <li><strong>HTML Parsing Based:</strong> No API circumvention</li>
                        <li><strong>No Personal Data Collection:</strong> GDPR and privacy law compliant</li>
                        <li><strong>Rate Limiting:</strong> Minimizes target site load</li>
                        <li><strong>Short Sessions:</strong> Immediate data deletion</li>
                    </ul>
                    
                    <h4>💼 Business Applications (Legal Use)</h4>
                    <ul>
                        <li><strong>Public Brand Monitoring:</strong> Tracking social media mentions</li>
                        <li><strong>Market Trend Analysis:</strong> Understanding public forum trends</li>
                        <li><strong>Competitor Public Info Analysis:</strong> Collecting publicly available announcements</li>
                        <li><strong>Content Research:</strong> Analyzing public post patterns</li>
                    </ul>
                    
                    <h4>⚖️ Legal Compliance</h4>
                    <p><strong>Users must verify:</strong></p>
                    <ul>
                        <li>Target site terms of service and robots.txt</li>
                        <li>Relevant privacy protection and copyright laws</li>
                        <li>Legal scope of collected data usage</li>
                    </ul>
                    
                    <h4>📞 Contact Us</h4>
                    <p>For inquiries about legal compliance or business applications, please contact us through the feedback feature.</p>
                </div>
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
               <p>PickPostは個人情報を収集せず、短期セッション内でのみデータを処理します。すべてのデータはExcelダウンロード後に即座に削除されます。</p>
               
               <h3>3. 個人情報の第三者提供</h3>
               <p>PickPostは個人情報を収集しないため、第三者に提供することはありません。</p>
               
               <h3>4. 個人情報保護責任者</h3>
               <p>個人情報に関するお問い合わせは、フィードバック機能を通じてご連絡ください。</p>
           `
       },
       terms: {
           title: "サービス利用規約",
           content: `
               <h3>第1条（目的）</h3>
               <p>この規約は、PickPostウェブクローリングサービスの利用条件および手続きに関する事項を規定することを目的とします。</p>
               
               <h3>第2条（定義）</h3>
               <p>この規約で使用する用語の定義は以下の通りです：</p>
               <ul>
                   <li>「サービス」とは、PickPostが提供する公開ウェブコンテンツ収集・整理サービスを意味します。</li>
                   <li>「利用者」とは、この規約に従ってサービスを利用する者を意味します。</li>
                   <li>「クローリング」とは、公開されたウェブサイトからHTMLパースを通じて情報を収集する行為を意味します。</li>
               </ul>
               
               <h3>第3条（サービスの範囲と制限）</h3>
               <p>PickPostは以下のサービスを提供します：</p>
               <ul>
                   <li>公開ソーシャルメディアコンテンツ収集（Reddit、Lemmyなど）</li>
                   <li>HTMLパースベースのデータ収集（API回避なし）</li>
                   <li>収集データのExcel形式ダウンロード支援</li>
               </ul>
               <p><strong>サービス制限事項：</strong></p>
               <ul>
                   <li>ログインが必要な非公開エリアにはアクセスしません</li>
                   <li>個人情報は収集しません</li>
                   <li>リクエスト速度制限（Rate Limiting）が適用されます</li>
               </ul>
               
               <h3>第4条（利用者の責任）</h3>
               <p><strong>⚠️ 重要：クローリング対象サイトの法的責任は利用者にあります</strong></p>
               <ul>
                   <li>利用者はクローリング予定サイトの利用規約（TOS）およびrobots.txtを確認する責任があります</li>
                   <li>クローリングによるすべての法的責任は利用者が負担します</li>
                   <li>過度なリクエストで対象サイトに負荷をかけてはいけません</li>
                   <li>収集データの使用に対する責任は利用者にあります</li>
                   <li>著作権、個人情報保護法など関連法令を遵守する必要があります</li>
               </ul>
               
               <h3>第5条（禁止行為）</h3>
               <p>利用者は以下の行為をしてはいけません：</p>
               <ul>
                   <li>対象サイトの利用規約に違反するクローリング</li>
                   <li>個人情報が含まれる非公開情報への無断アクセス</li>
                   <li>過度なリクエストでサービス妨害を引き起こす行為</li>
                   <li>不法な目的で収集データを使用する行為</li>
               </ul>
               
               <h3>第6条（サービス提供者の免責）</h3>
               <ul>
                   <li>PickPostは利用者のクローリング行為による法的紛争について責任を負いません</li>
                   <li>対象サイトとの法的問題は利用者が直接解決する必要があります</li>
                   <li>PickPostはツールを提供するのみであり、使用に対する責任は利用者にあります</li>
                   <li>収集データの正確性や完全性を保証しません</li>
               </ul>
               
               <h3>第7条（推奨事項）</h3>
               <p>安全なサービス利用のため、以下を推奨します：</p>
               <ul>
                   <li>クローリング前の対象サイトrobots.txt確認</li>
                   <li>適切なリクエスト間隔の維持</li>
                   <li>対象サイト利用規約の理解</li>
                   <li>個人情報保護法など関連法令の遵守</li>
               </ul>
               
               <h3>第8条（規約の効力および変更）</h3>
               <p>この規約はサービス画面に掲示することにより効力を発生し、関連法令変更時は事前告知後に修正される場合があります。</p>
           `
       },
       business: {
            title: "💼 ビジネス案内",
            content: `
                <div style="line-height: 1.8;">
                    <h3>🚀 PickPost ビジネスソリューション</h3>
                    <p>PickPostは、公開ウェブデータを安全かつ効率的に収集・分析できる法的リスクが低いツールです。</p>
                    
                    <h4>📊 コア安全機能</h4>
                    <ul>
                        <li><strong>公開データのみ収集:</strong> ログイン必要エリア除外</li>
                        <li><strong>HTMLパースベース:</strong> API制限回避なし</li>
                        <li><strong>個人情報未収集:</strong> GDPRなど個人情報保護法準拠</li>
                        <li><strong>リクエスト速度制限:</strong> 対象サイト負荷最小化</li>
                        <li><strong>短期セッション:</strong> データ即座削除</li>
                    </ul>
                    
                    <h4>💼 ビジネス活用（合法的用途）</h4>
                    <ul>
                        <li><strong>公開ブランドモニタリング:</strong> ソーシャルメディア言及追跡</li>
                        <li><strong>市場動向分析:</strong> 公開フォーラムトレンド把握</li>
                        <li><strong>競合公開情報分析:</strong> 公開発表内容収集</li>
                        <li><strong>コンテンツ研究:</strong> 公開投稿パターン分析</li>
                    </ul>
                    
                    <h4>⚖️ 法的遵守事項</h4>
                    <p><strong>利用者は必ず確認が必要：</strong></p>
                    <ul>
                        <li>対象サイトの利用規約およびrobots.txt</li>
                        <li>関連個人情報保護法および著作権法</li>
                        <li>収集データの適法な使用範囲</li>
                    </ul>
                    
                    <h4>📞 お問い合わせ</h4>
                    <p>法的遵守事項やビジネス活用に関するお問い合わせは、フィードバック機能を通じてご連絡ください。</p>
                </div>
            `
        }
   }
};

// ==================== languages.js에 추가할 번역 구조 ====================

const additionalTranslations = {
    ko: {
        // 법적 동의 관련
        legalConsent: {
            title: "법적 책임 고지",
            warning: "⚠️ 중요 안내사항",
            description: "PickPost는 공개 데이터 수집 도구를 제공할 뿐이며, 크롤링으로 인한 모든 법적 책임은 사용자에게 있습니다.",
            checkboxText: "본인은 크롤링 대상 사이트의 이용약관 및 정책을 확인하였으며, 해당 데이터 수집에 대한 법적 책임이 본인에게 있음을 인지합니다.",
            confirmBtn: "동의하고 시작",
            cancelBtn: "취소",
            consentRequired: "크롤링을 시작하려면 동의가 필요합니다.",
            termsLink: "이용약관",
            privacyLink: "개인정보처리방침"
        },

        // robots.txt 확인 관련
        robotsCheck: {
            title: "robots.txt 확인 결과",
            checking: "robots.txt 확인 중...",
            allowed: "크롤링이 허용됩니다",
            disallowed: "크롤링이 금지되어 있습니다",
            error: "robots.txt를 확인할 수 없습니다",
            recommendation: "권장사항",
            delay: "권장 지연시간",
            quickBtn: "robots.txt 확인"
        }
    },

    en: {
        // 법적 동의 관련
        legalConsent: {
            title: "Legal Responsibility Notice",
            warning: "⚠️ Important Notice",
            description: "PickPost only provides public data collection tools. Users are fully responsible for any legal consequences arising from crawling activities.",
            checkboxText: "I have reviewed the terms of service and policies of the target crawling sites and acknowledge that I am legally responsible for data collection activities.",
            confirmBtn: "Agree and Start",
            cancelBtn: "Cancel",
            consentRequired: "Consent is required to start crawling.",
            termsLink: "Terms of Service",
            privacyLink: "Privacy Policy"
        },

        // robots.txt 확인 관련
        robotsCheck: {
            title: "robots.txt Check Result",
            checking: "Checking robots.txt...",
            allowed: "Crawling is allowed",
            disallowed: "Crawling is prohibited",
            error: "Cannot check robots.txt",
            recommendation: "Recommendation",
            delay: "Recommended Delay",
            quickBtn: "Check robots.txt"
        }
    },

    ja: {
        // 법적 동의 관련
        legalConsent: {
            title: "法的責任告知",
            warning: "⚠️ 重要なお知らせ",
            description: "PickPostは公開データ収集ツールを提供するのみであり、クローリングによるすべての法的責任は利用者にあります。",
            checkboxText: "クローリング対象サイトの利用規約およびポリシーを確認し、当該データ収集に対する法的責任が私にあることを認識しています。",
            confirmBtn: "同意して開始",
            cancelBtn: "キャンセル",
            consentRequired: "クローリングを開始するには法的同意が必要です。",
            termsLink: "利用規約",
            privacyLink: "プライバシーポリシー"
        },

        // robots.txt 확인 관련
        robotsCheck: {
            title: "robots.txt確認結果",
            checking: "robots.txt確認中...",
            allowed: "クローリングが許可されています",
            disallowed: "クローリングが禁止されています",
            error: "robots.txtを確認できません",
            recommendation: "推奨事項",
            delay: "推奨遅延時間",
            quickBtn: "robots.txt確認"
        }
    }
};

// ==================== 기존 languages.js에 병합하는 방법 ====================

// 방법 1: 각 언어 객체에 직접 추가
languages.ko.legalConsent = additionalTranslations.ko.legalConsent;
languages.ko.robotsCheck = additionalTranslations.ko.robotsCheck;

languages.en.legalConsent = additionalTranslations.en.legalConsent;
languages.en.robotsCheck = additionalTranslations.en.robotsCheck;

languages.ja.legalConsent = additionalTranslations.ja.legalConsent;
languages.ja.robotsCheck = additionalTranslations.ja.robotsCheck;

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