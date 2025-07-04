// announcements/announcement-1.js
// 다국어 공지사항 파일

announcementData = {
    id: 1,
    date: '2025-06-11',
    isNew: true,
    category: 'notice',
    priority: 'high',
    translations: {
        ko: {
            title: 'PickPost 서비스 오픈!',
            content: 'Reddit, BBC, Lemmy, 4chan 등 다양한 플랫폼의 콘텐츠를 크롤링할 수 있는 PickPost가 오픈했습니다.'
        },
        en: {
            title: 'PickPost Service Launch!',
            content: 'PickPost is now open, allowing you to crawl content from various platforms like Reddit, BBC, Lemmy, 4chan.'
        },
        ja: {
            title: 'PickPostサービス開始！',
            content: 'Reddit、BBC、Lemmy、4chanなど様々なプラットフォームのコンテンツをクロールできるPickPostがオープンしました。'
        }
    }
};