// PickPost 언어팩 - 완성된 버전
const languages = {
    ko: {
        // ==================== 기본 UI 요소 ====================
        start: "크롤링 시작",
        clear: "결과 지우기", 
        ok: "확인",
        cancel: "취소",
        download: "엑셀 다운로드",
        title: "PickPost",
        
        // ==================== 사이트 관련 ====================
        siteSelect: "사이트를 선택하세요",
        reddit: "레딧",
        dcinside: "디시인사이드",
        blind: "블라인드",
        lemmy: "레미",
        bbc: "BBC",
        universal: "범용",
        
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
        
        // ==================== 검색 옵션 ====================
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
        
        // ==================== 시간 필터 ====================
        timeFilterLabels: {
            hour: "1시간",
            day: "하루",
            week: "일주일", 
            month: "한 달",
            year: "일 년",
            all: "전체",
            custom: "사용자 지정"
        },
        
        // ==================== 결과 표시 ====================
        views: "조회수",
        likes: "추천수", 
        comments: "댓글수",
        date: "작성일",
        original: "원문 링크",
        translation: "번역",
        fail: "(번역 실패)",
        
        // ==================== 크롤링 진행 상태 ====================
        crawlingSteps: {
            initializing: "크롤링 준비 중...",
            detecting_site: "사이트 분석 중...",
            connecting: "{site} 연결 중...",
            collecting: "{site}에서 게시물 수집 중... ({page}페이지)",
            filtering: "조건에 맞는 게시물 필터링 중... ({matched}/{total})",
            processing: "데이터 처리 중...",
            translating: "번역 진행 중... ({current}/{total})",
            finalizing: "결과 정리 중...",
            complete: "완료"
        },
        
        crawlingStatus: {
            metadata_processing: "메타데이터 처리 중...",
            collecting_posts: "게시물 수집 중...",
            analyzing_content: "컨텐츠 분석 중...",
            filtering_results: "결과 필터링 중...",
            preparing_translation: "번역 준비 중...",
            reddit_analyzing: "Reddit 데이터 분석 중...",
            dcinside_parsing: "디시인사이드 파싱 중...",
            blind_processing: "블라인드 처리 중...",
            bbc_fetching: "BBC 뉴스 가져오는 중...",
            lemmy_connecting: "Lemmy 서버 연결 중...",
            universal_parsing: "웹페이지 구조 분석 중...",
            
            found: "개 발견",
            page: "페이지",
            timeRemaining: "예상 시간"
        },
        
        // ==================== 완료 메시지 ====================
        crawling: {
            complete: "{site} {board}에서 {count}개 게시물 수집 완료 ({start}-{end}위)"
        },
        
        // ==================== 버튼 메시지 ====================
        crawlButtonMessages: {
            siteNotSelected: "사이트를 선택하세요",
            boardEmpty: "게시판을 입력하세요", 
            universalEmpty: "URL을 입력하세요",
            universalUrlError: "올바른 URL을 입력하세요",
            lemmyEmpty: "커뮤니티를 입력하세요",
            lemmyFormatError: "올바른 Lemmy 형식을 입력하세요",
            redditFormatError: "올바른 Reddit 형식을 입력하세요"
        },
        
        // ==================== 에러 메시지 ====================
        errors: {
            general: "크롤링 중 오류가 발생했습니다",
            unknown: "알 수 없는 오류가 발생했습니다",
            connection_failed: "서버 연결에 실패했습니다",
            invalid_url: "올바르지 않은 URL입니다",
            site_not_found: "사이트를 찾을 수 없습니다",
            no_posts_found: "조건에 맞는 게시물이 없습니다",
            timeout: "요청 시간이 초과되었습니다",
            rate_limited: "요청 제한에 걸렸습니다. 잠시 후 시도하세요",
            invalid_bbc_url: "올바른 BBC 뉴스 URL을 입력해주세요",
            crawling_error: "크롤링 처리 중 오류가 발생했습니다"
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
        
        // ==================== 일반 알림 ====================
        notifications: {
            connection_failed: "서버 연결에 실패했습니다. 잠시 후 다시 시도해주세요",
            file_too_large: "파일 크기는 5MB 이하로 제한됩니다",
            invalid_file_type: "이미지 파일만 업로드할 수 있습니다",
            no_data: "다운로드할 데이터가 없습니다",
            download_success: "파일이 다운로드되었습니다: {filename}"
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
        business: "비즈니스"
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
        reddit: "Reddit",
        dcinside: "DCインサイド",
        blind: "Blind",
        lemmy: "Lemmy",
        bbc: "BBC",
        universal: "汎用",
        
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
        
        // ==================== 검색 옵션 ====================
        minViews: "最小閲覧数",
        minRecommend: "最小推奨数",
        minComments: "最小コメント数",
        startRank: "開始順位",
        endRank: "終了順位",
        sortMethod: "ソート方法",
        timePeriod: "期間",
        startDate: "開始日",
        endDate: "終了日",
        advancedSearch: "高度な検索",
        
        // ==================== 시간 필터 ====================
        timeFilterLabels: {
            hour: "1時間",
            day: "1日",
            week: "1週間",
            month: "1ヶ月",
            year: "1年",
            all: "全期間",
            custom: "カスタム範囲"
        },
        
        // ==================== 결과 표시 ====================
        views: "閲覧数",
        likes: "推奨数",
        comments: "コメント数",
        date: "作成日",
        original: "原文リンク",
        translation: "翻訳",
        fail: "(翻訳失敗)",
        
        // ==================== 크롤링 진행 상태 ====================
        crawlingSteps: {
            initializing: "クロール準備中...",
            detecting_site: "サイト分析中...",
            connecting: "{site}に接続中...",
            collecting: "{site}から投稿を収集中... ({page}ページ)",
            filtering: "条件に合う投稿をフィルタリング中... ({matched}/{total})",
            processing: "データ処理中...",
            translating: "翻訳進行中... ({current}/{total})",
            finalizing: "結果整理中...",
            complete: "完了"
        },
        
        crawlingStatus: {
            metadata_processing: "メタデータ処理中...",
            collecting_posts: "投稿収集中...",
            analyzing_content: "コンテンツ分析中...",
            filtering_results: "結果フィルタリング中...",
            preparing_translation: "翻訳準備中...",
            reddit_analyzing: "Redditデータ分析中...",
            dcinside_parsing: "DCインサイド解析中...",
            blind_processing: "Blind処理中...",
            bbc_fetching: "BBCニュース取得中...",
            lemmy_connecting: "Lemmyサーバー接続中...",
            universal_parsing: "ウェブページ構造分析中...",
            
            found: "件発見",
            page: "ページ",
            timeRemaining: "予想時間"
        },
        
        // ==================== 완료 메시지 ====================
        crawling: {
            complete: "{site} {board}から{count}個の投稿を収集完了 ({start}-{end}位)"
        },
        
        // ==================== 버튼 메시지 ====================
        crawlButtonMessages: {
            siteNotSelected: "サイトを選択してください",
            boardEmpty: "掲示板を入力してください",
            universalEmpty: "URLを入力してください",
            universalUrlError: "正しいURLを入力してください", 
            lemmyEmpty: "コミュニティを入力してください",
            lemmyFormatError: "正しいLemmy形式を入力してください",
            redditFormatError: "正しいReddit形式を入力してください"
        },
        
        // ==================== 에러 메시지 ====================
        errors: {
            general: "クロール中にエラーが発生しました",
            unknown: "不明なエラーが発生しました",
            connection_failed: "サーバー接続に失敗しました",
            invalid_url: "正しくないURLです",
            site_not_found: "サイトが見つかりません",
            no_posts_found: "条件に合う投稿がありません",
            timeout: "リクエストタイムアウトです",
            rate_limited: "リクエスト制限にかかりました。しばらく後に試してください",
            invalid_bbc_url: "正しいBBC ニュースURLを入力してください",
            crawling_error: "クロール処理中にエラーが発生しました"
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
        
        // ==================== 일반 알림 ====================
        notifications: {
            connection_failed: "サーバーへの接続に失敗しました。しばらくしてから再試行してください",
            file_too_large: "ファイルサイズは5MB以下に制限されています",
            invalid_file_type: "画像ファイルのみアップロードできます",
            no_data: "ダウンロードするデータがありません",
            download_success: "ファイルがダウンロードされました: {filename}"
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
        business: "ビジネス"
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
        reddit: "Reddit",
        dcinside: "DCInside",
        blind: "Blind",
        lemmy: "Lemmy",
        bbc: "BBC",
        universal: "Universal",
        
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
        
        // ==================== 검색 옵션 ====================
        minViews: "Minimum Views",
        minRecommend: "Minimum Likes",
        minComments: "Minimum Comments", 
        startRank: "Start Rank",
        endRank: "End Rank",
        sortMethod: "Sort Method",
        timePeriod: "Time Period",
        startDate: "Start Date",
        endDate: "End Date",
        advancedSearch: "Advanced Search",
        
        // ==================== 시간 필터 ====================
        timeFilterLabels: {
            hour: "1 Hour",
            day: "1 Day",
            week: "1 Week",
            month: "1 Month",
            year: "1 Year",
            all: "All Time",
            custom: "Custom Range"
        },
        
        // ==================== 결과 표시 ====================
        views: "Views",
        likes: "Likes",
        comments: "Comments",
        date: "Date",
        original: "Original Link",
        translation: "Translation",
        fail: "(Translation Failed)",
        
        // ==================== 크롤링 진행 상태 ====================
        crawlingSteps: {
            initializing: "Preparing crawl...",
            detecting_site: "Analyzing site...",
            connecting: "Connecting to {site}...",
            collecting: "Collecting posts from {site}... (Page {page})",
            filtering: "Filtering posts by criteria... ({matched}/{total})",
            processing: "Processing data...",
            translating: "Translating... ({current}/{total})",
            finalizing: "Finalizing results...",
            complete: "Complete"
        },
        
        crawlingStatus: {
            metadata_processing: "Processing metadata...",
            collecting_posts: "Collecting posts...",
            analyzing_content: "Analyzing content...",
            filtering_results: "Filtering results...",
            preparing_translation: "Preparing translation...",
            reddit_analyzing: "Analyzing Reddit data...",
            dcinside_parsing: "Parsing DCInside...",
            blind_processing: "Processing Blind...",
            bbc_fetching: "Fetching BBC news...",
            lemmy_connecting: "Connecting to Lemmy...",
            universal_parsing: "Analyzing webpage structure...",
            
            found: "found",
            page: "page",
            timeRemaining: "estimated time"
        },
        
        // ==================== 완료 메시지 ====================
        crawling: {
            complete: "Collected {count} posts from {site} {board} (Rank {start}-{end})"
        },
        
        // ==================== 버튼 메시지 ====================
        crawlButtonMessages: {
            siteNotSelected: "Select a site",
            boardEmpty: "Enter board name",
            universalEmpty: "Enter URL", 
            universalUrlError: "Enter valid URL",
            lemmyEmpty: "Enter community",
            lemmyFormatError: "Enter valid Lemmy format",
            redditFormatError: "Enter valid Reddit format"
        },
        
        // ==================== 에러 메시지 ====================
        errors: {
            general: "An error occurred during crawling",
            unknown: "Unknown error occurred",
            connection_failed: "Failed to connect to server",
            invalid_url: "Invalid URL",
            site_not_found: "Site not found",
            no_posts_found: "No posts found matching criteria",
            timeout: "Request timeout",
            rate_limited: "Rate limited. Please try again later",
            invalid_bbc_url: "Please enter a valid BBC news URL",
            crawling_error: "An error occurred during crawling process"
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
        
        // ==================== 일반 알림 ====================
        notifications: {
            connection_failed: "Failed to connect to server. Please try again later",
            file_too_large: "File size is limited to 5MB or less",
            invalid_file_type: "Only image files can be uploaded",
            no_data: "No data to download",
            download_success: "File downloaded: {filename}"
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
        business: "Business"
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
                <p>PickPostは情報主体の個人情報を個人情報の処理目的で明示した範囲内でのみ処理し、情報主体の同意、法律の特別な規定など個人情報保護法第17条に該당する場合にのみ個人情報を第三者に提供します。</p>
                
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

// ==================== 전역 변수 설정 ====================
window.languages = languages;
window.policies = policies;
