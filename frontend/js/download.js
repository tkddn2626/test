// ==================== 통합 다운로드 모듈 (Excel + Media) ====================
// Excel 다운로드와 미디어 다운로드를 통합한 모듈

// ==================== 전역 변수 및 상태 관리 ====================
let isDownloadingMedia = false;
let downloadProgress = 0;

// ==================== Excel 다운로드 기능 ====================

/**
 * Load SheetJS library dynamically
 */
async function loadSheetJS() {
    if (typeof XLSX !== 'undefined') {
        return true;
    }

    return new Promise((resolve) => {
        const script = document.createElement('script');
        script.src = 'https://cdnjs.cloudflare.com/ajax/libs/xlsx/0.18.5/xlsx.full.min.js';
        script.onload = () => {
            console.log('✅ SheetJS library loaded successfully');
            resolve(true);
        };
        script.onerror = () => {
            console.warn('❌ Failed to load SheetJS library');
            resolve(false);
        };
        document.head.appendChild(script);
    });
}

/**
 * Main Excel download function
 */
async function downloadExcel() {
    if (crawlResults.length === 0) {
        showMessage('No data available for download', 'error');
        return;
    }

    showMessage('Creating Excel file...', 'info');

    const sheetJSLoaded = await loadSheetJS();
    
    if (!sheetJSLoaded) {
        console.warn('⚠️ SheetJS failed to load, falling back to CSV');
        downloadAsCSV();
        return;
    }

    try {
        await createStyledExcelFile();
    } catch (error) {
        console.error('Excel creation error:', error);
        downloadAsCSV();
    }
}

/**
 * Create Excel file with professional styling
 */
async function createStyledExcelFile() {
    const wb = XLSX.utils.book_new();
    
    // Prepare data
    const worksheetData = prepareExcelData();
    
    // Create worksheet
    const ws = XLSX.utils.aoa_to_sheet(worksheetData);
    
    // Apply professional styling
    applyProfessionalStyles(ws, worksheetData.length);
    
    // Add worksheet to workbook
    XLSX.utils.book_append_sheet(wb, ws, "Crawling Results");
    
    // Generate filename
    const filename = generateExcelFilename();
    
    // Download Excel file
    XLSX.writeFile(wb, filename);
    
    showMessage(`Excel file downloaded: ${filename}`, 'success');
    console.log(`✅ Excel download completed: ${filename}`);
}

/**
 * Prepare data for Excel (keeping original structure)
 */
function prepareExcelData() {
    // Original headers
    const headers = [
        'Rank', 
        'Original Title', 
        'Translated Title', 
        'Source Link', 
        'Content Preview', 
        'Views', 
        'Likes', 
        'Comments', 
        'Published Date'
    ];
    
    // Process data with original structure
    const dataRows = crawlResults.map((item, index) => [
        index + 1, // Rank
        cleanText(item.원제목 || item.title || item.제목 || 'Untitled'),
        cleanText(item.번역제목 || item.translated_title || ''),
        item.링크 || item.link || item.url || '',
        cleanContent(item.본문 || item.content || item.내용 || ''),
        formatNumber(item.조회수 || item.views || 0),
        formatNumber(item.추천수 || item.likes || item.score || 0),
        formatNumber(item.댓글수 || item.comments || 0),
        formatDate(item.작성일 || item.date || item.created_at || '')
    ]);
    
    return [headers, ...dataRows];
}

/**
 * Apply professional styling (inspired by business dashboard)
 */
function applyProfessionalStyles(worksheet, dataLength) {
    const range = XLSX.utils.decode_range(worksheet['!ref']);
    
    // Column widths (optimized for readability)
    const columnWidths = [
        { wch: 8 },   // Rank
        { wch: 50 },  // Original Title
        { wch: 50 },  // Translated Title
        { wch: 35 },  // Source Link
        { wch: 40 },  // Content Preview
        { wch: 12 },  // Views
        { wch: 12 },  // Likes
        { wch: 12 },  // Comments
        { wch: 18 }   // Published Date
    ];
    worksheet['!cols'] = columnWidths;
    
    // Row heights
    const rowHeights = [];
    for (let i = 0; i <= dataLength; i++) {
        rowHeights[i] = { hpt: i === 0 ? 35 : 60 }; // Header: 35px, Data: 60px
    }
    worksheet['!rows'] = rowHeights;
    
    // Apply styling inspired by dashboard design
    for (let row = range.s.r; row <= range.e.r; row++) {
        for (let col = range.s.c; col <= range.e.c; col++) {
            const cellAddress = XLSX.utils.encode_cell({ r: row, c: col });
            const cell = worksheet[cellAddress];
            
            if (!cell) continue;
            
            // Base styling
            cell.s = {
                font: {
                    name: 'Segoe UI',
                    sz: row === 0 ? 12 : 11,
                    bold: row === 0,
                    color: row === 0 ? { rgb: 'FFFFFF' } : { rgb: '2C3E50' }
                },
                alignment: {
                    wrapText: true,
                    vertical: 'center',
                    horizontal: getAlignment(col, row === 0),
                    indent: col === 1 || col === 2 ? 1 : 0
                },
                border: {
                    top: { style: 'thin', color: { rgb: 'E8EAED' } },
                    bottom: { style: 'thin', color: { rgb: 'E8EAED' } },
                    left: { style: 'thin', color: { rgb: 'E8EAED' } },
                    right: { style: 'thin', color: { rgb: 'E8EAED' } }
                }
            };
            
            // Header styling - Dark blue background like dashboard
            if (row === 0) {
                cell.s.fill = { fgColor: { rgb: '4A5568' } }; // Dark blue-gray
                cell.s.border = {
                    top: { style: 'medium', color: { rgb: '2D3748' } },
                    bottom: { style: 'medium', color: { rgb: '2D3748' } },
                    left: { style: 'thin', color: { rgb: '2D3748' } },
                    right: { style: 'thin', color: { rgb: '2D3748' } }
                };
            }
            
            // Data row styling
            if (row > 0) {
                // Rank column - similar to Priority column in dashboard
                if (col === 0) {
                    cell.s.fill = { fgColor: { rgb: 'F7FAFC' } };
                    cell.s.font.bold = true;
                    cell.s.font.color = { rgb: '4A5568' };
                }
                
                // Link column - professional blue styling
                if (col === 3 && cell.v && cell.v.startsWith('http')) {
                    cell.l = { Target: cell.v, Tooltip: cell.v };
                    cell.s.font.color = { rgb: '0000FF' };
                    cell.s.font.underline = true;
                    // URL을 그대로 표시하되 하이퍼링크로 만들기
                }
                
                // Number columns - right aligned
                if (col >= 5 && col <= 7) {
                    cell.s.alignment.horizontal = 'right';
                    cell.s.font.color = { rgb: '2D3748' };
                }
                
                // Date column
                if (col === 8) {
                    cell.s.font.color = { rgb: '718096' };
                }
                
                // Alternating row colors for better readability
                if (row % 2 === 0) {
                    if (!cell.s.fill) {
                        cell.s.fill = { fgColor: { rgb: 'F9FAFB' } };
                    }
                }
            }
        }
    }
    
    // Add freeze panes and auto filter
    worksheet['!freeze'] = { xSplit: 0, ySplit: 1 };
    worksheet['!autofilter'] = { ref: XLSX.utils.encode_range(range) };
}

/**
 * Get alignment for columns
 */
function getAlignment(colIndex, isHeader) {
    if (isHeader) return 'center';
    
    switch (colIndex) {
        case 0: return 'center';     // Rank
        case 1: 
        case 2: 
        case 4: return 'left';       // Titles and content
        case 3: return 'center';     // Link
        case 5: 
        case 6: 
        case 7: return 'right';      // Numbers
        case 8: return 'center';     // Date
        default: return 'left';
    }
}

/**
 * Generate filename
 */
function generateExcelFilename() {
    const now = new Date();
    const dateStr = now.getFullYear().toString().slice(-2) + '.' +
                   String(now.getMonth() + 1).padStart(2, '0') + '.' +
                   String(now.getDate()).padStart(2, '0') + ' ' +
                   String(now.getHours()).padStart(2, '0') + '.' +
                   String(now.getMinutes()).padStart(2, '0');
    
    const siteMap = {
        reddit: 'Reddit',
        dcinside: 'DCInside',
        blind: 'Blind',
        bbc: 'BBC',
        lemmy: 'Lemmy',
        '4chan': '4chan',
        universal: 'Universal'
    };
    
    const siteName = siteMap[currentSite] || currentSite || 'Unknown';
    const resultCount = crawlResults.length;
    
    return `${dateStr} ${siteName} 1-${resultCount}위.xlsx`;
}

// ==================== CSV 다운로드 ====================

/**
 * Create CSV content
 */
function createCSVContent() {
    const headers = ['순위', '원제목', '번역제목', '링크', '내용 미리보기', '조회수', '추천수', '댓글수', '작성일'];
    const csvData = [headers];
    
    crawlResults.forEach((item, index) => {
        const row = [
            index + 1,
            cleanText(item.원제목 || item.title || item.제목 || 'Untitled'),
            cleanText(item.번역제목 || item.translated_title || ''),
            item.링크 || item.link || item.url || '',
            cleanContent(item.본문 || item.content || item.내용 || ''),
            formatNumber(item.조회수 || item.views || 0),
            formatNumber(item.추천수 || item.likes || item.score || 0),
            formatNumber(item.댓글수 || item.comments || 0),
            formatDate(item.작성일 || item.date || item.created_at || '')
        ];
        csvData.push(row);
    });
    
    return csvData.map(row => 
        row.map(cell => 
            typeof cell === 'string' && (cell.includes(',') || cell.includes('"') || cell.includes('\n'))
                ? `"${cell.replace(/"/g, '""')}"` 
                : cell
        ).join(',')
    ).join('\n');
}

/**
 * Generate CSV filename
 */
function generateCSVFilename() {
    const now = new Date();
    const dateStr = now.getFullYear().toString().slice(-2) + '.' +
                   String(now.getMonth() + 1).padStart(2, '0') + '.' +
                   String(now.getDate()).padStart(2, '0') + ' ' +
                   String(now.getHours()).padStart(2, '0') + '.' +
                   String(now.getMinutes()).padStart(2, '0');
    
    const siteMap = {
        reddit: 'Reddit',
        dcinside: 'DCInside',
        blind: 'Blind',
        bbc: 'BBC',
        lemmy: 'Lemmy',
        '4chan': '4chan',
        universal: 'Universal'
    };
    
    const siteName = siteMap[currentSite] || currentSite || 'Unknown';
    const resultCount = crawlResults.length;
    
    return `${dateStr} ${siteName} 1-${resultCount}위.csv`;
}

function downloadAsCSV() {
    if (crawlResults.length === 0) {
        showMessage(getLocalizedMessage('notifications.no_data'), 'error');
        return;
    }

    try {
        const csvContent = createCSVContent();
        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const filename = generateCSVFilename();
        
        const link = document.createElement('a');
        link.setAttribute('href', url);
        link.setAttribute('download', filename);
        link.style.visibility = 'hidden';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
        
        showMessage(getLocalizedMessage('notifications.download_success', { filename }), 'success');
    } catch (error) {
        showMessage(getLocalizedMessage('errorMessages.general'), 'error');
    }
}

// ==================== 미디어 다운로드 기능 ====================

/**
 * 미디어 다운로드 가능 여부 확인
 */
async function checkMediaDownloadSupport() {
    try {
        const { API_BASE_URL } = getApiConfig();
        const response = await fetch(`${API_BASE_URL}/api/media-info`);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        console.log('🔍 미디어 지원 정보:', data);
        
        // 사이트가 지원되는지 확인
        const isSupported = data.available && 
                           data.supported_sites && 
                           data.supported_sites.includes(currentSite);
        
        console.log(`📊 미디어 지원 여부: ${currentSite} = ${isSupported}`);
        
        return isSupported;
        
    } catch (error) {
        console.error('❌ 미디어 지원 확인 오류:', error);
        return false;
    }
}

/**
 * 미디어 다운로드 진행률 표시
 */
function showMediaDownloadProgress(message, progress = null) {
    // 기존 진행률 표시 요소 재사용 또는 새로 생성
    let progressContainer = document.getElementById('mediaProgressContainer');
    
    if (!progressContainer) {
        progressContainer = document.createElement('div');
        progressContainer.id = 'mediaProgressContainer';
        progressContainer.style.cssText = `
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: white;
            padding: 24px;
            border-radius: 12px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.15);
            z-index: 10000;
            min-width: 300px;
            text-align: center;
        `;
        document.body.appendChild(progressContainer);
    }
    
    let content = `
        <div style="margin-bottom: 16px;">
            <div style="font-size: 18px; font-weight: 600; color: #1a73e8; margin-bottom: 8px;">
                Media Download
            </div>
            <div style="font-size: 14px; color: #5f6368;">
                ${message}
            </div>
        </div>
    `;
    
    if (progress !== null) {
        content += `
            <div style="background: #f1f3f4; height: 8px; border-radius: 4px; overflow: hidden; margin-bottom: 8px;">
                <div style="background: #1a73e8; height: 100%; width: ${progress}%; transition: width 0.3s ease;"></div>
            </div>
            <div style="font-size: 12px; color: #5f6368;">
                ${progress}%
            </div>
        `;
    }
    
    progressContainer.innerHTML = content;
}

/**
 * 미디어 다운로드 진행률 숨기기
 */
function hideMediaDownloadProgress() {
    const progressContainer = document.getElementById('mediaProgressContainer');
    if (progressContainer) {
        progressContainer.remove();
    }
}

// ==================== 미디어 다운로드 함수 ====================

async function downloadMedia() {
    // 기본 검증
    if (!crawlResults || crawlResults.length === 0) {
        showMessage(getLocalizedMessage('media.no_media_found'), 'error');
        return;
    }
    
    if (isDownloadingMedia) {
        showMessage(getLocalizedMessage('media.already_in_progress'), 'warning');
        return;
    }
    
    if (!currentSite) {
        showMessage(getLocalizedMessage('media.site_info_missing'), 'error');
        return;
    }
    
    try {
        isDownloadingMedia = true;
        
        // 버튼 상태 변경
        const mediaButton = document.getElementById('downloadMediaBtn');
        
        if (mediaButton) {
            mediaButton.textContent = getLocalizedMessage('media.checking');
            mediaButton.disabled = true;
        }
               
        // API 설정
        const { API_BASE_URL } = getApiConfig();
        
        if (mediaButton) {
            mediaButton.textContent = getLocalizedMessage('media.collecting');
        }
        
        showMediaDownloadProgress(getLocalizedMessage('media.collecting_files'), 0);
        
        // 🔥 모든 사이트에서 미디어 다운로드 시도
        const siteTypeForAPI = currentSite; // shouldCheckAPI ? currentSite : 'universal';
        
        const response = await fetch(`${API_BASE_URL}/api/download-media`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                posts: crawlResults,
                site_type: siteTypeForAPI,
                include_images: true,
                include_videos: true,
                include_audio: false,
                max_file_size_mb: 50
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        if (mediaButton) {
            mediaButton.textContent = getLocalizedMessage('media.compressing');
        }
        
        showMediaDownloadProgress(getLocalizedMessage('media.creating_zip'), 75);
        
        const result = await response.json();
        
        if (result.success) {
            showMediaDownloadProgress(getLocalizedMessage('media.download_ready'), 100);
            
            // ZIP 파일 다운로드
            const downloadUrl = `${API_BASE_URL}${result.download_url}`;
            const link = document.createElement('a');
            link.href = downloadUrl;
            link.download = result.zip_filename;
            link.style.display = 'none';
            
            document.body.appendChild(link);
            
            setTimeout(() => {
                link.click();
                document.body.removeChild(link);
                
                // 성공 메시지
                const successMessage = getLocalizedMessage('media.download_success', {
                    file_count: result.downloaded_files,
                    size_mb: result.zip_size_mb
                });
                
                showMessage(successMessage, 'success');
                
                if (result.failed_files > 0) {
                    setTimeout(() => {
                        const failMessage = getLocalizedMessage('media.files_failed', {
                            failed_count: result.failed_files
                        });
                        showMessage(failMessage, 'warning');
                    }, 2000);
                }
                
                hideMediaDownloadProgress();
            }, 500);
            
        } else {
            hideMediaDownloadProgress();
            const errorMessage = result.error || getLocalizedMessage('media.download_failed_general');
            showMessage(
                getLocalizedMessage('media.download_failed_with_error', { error: errorMessage }), 
                'error'
            );
        }
        
    } catch (error) {
        hideMediaDownloadProgress();
        
        let errorMessage;
        if (error.message.includes('503')) {
            errorMessage = getLocalizedMessage('media.service_unavailable');
        } else if (error.message.includes('404')) {
            errorMessage = getLocalizedMessage('media.service_not_found');
        } else if (error.message.includes('NetworkError') || error.message.includes('fetch')) {
            errorMessage = getLocalizedMessage('errorMessages.network_error');
        } else {
            errorMessage = getLocalizedMessage('media.processing_error', { error: error.message });
        }
        
        showMessage(errorMessage, 'error');
        
    } finally {
        isDownloadingMedia = false;
        
        const mediaButton = document.getElementById('downloadMediaBtn');
        if (mediaButton) {
            mediaButton.textContent = 'Media';
            mediaButton.disabled = false;
        }
        
        hideMediaDownloadProgress();
    }
}

/**
 * API 설정 가져오기 (main.js와 동일)
 */
function getApiConfig() {
    const hostname = window.location.hostname;
    
    if (hostname === 'localhost' || hostname === '127.0.0.1') {
        return {
            API_BASE_URL: 'http://localhost:8000',
            WS_BASE_URL: 'ws://localhost:8000'
        };
    }
    
    return {
        API_BASE_URL: 'https://api.pick-post.com',
        WS_BASE_URL: 'wss://api.pick-post.com'
    };
}

// ==================== 공통 유틸리티 함수 ====================

/**
 * Clean and format text
 */
function cleanText(text) {
    if (!text) return '';
    
    return text
        .replace(/\s+/g, ' ')
        .trim()
        .substring(0, 150);
}

/**
 * Clean and format content
 */
function cleanContent(text) {
    if (!text) return '';
    
    return text
        .replace(/\n/g, ' ')
        .replace(/\s+/g, ' ')
        .trim()
        .substring(0, 200) + (text.length > 200 ? '...' : '');
}

/**
 * Format numbers
 */
function formatNumber(num) {
    if (!num || num === 0) return 0;
    
    const number = parseInt(num);
    if (isNaN(number)) return 0;
    
    return number;
}

/**
 * Format date
 */
function formatDate(dateStr) {
    if (!dateStr) return '';
    
    try {
        const date = new Date(dateStr);
        if (isNaN(date.getTime())) return dateStr;
        
        return date.toLocaleDateString('en-US', { 
            year: 'numeric', 
            month: 'short', 
            day: 'numeric' 
        }) + ' ' + date.toLocaleTimeString('en-US', { 
            hour: '2-digit', 
            minute: '2-digit',
            hour12: false
        });
    } catch (error) {
        return dateStr;
    }
}

// ==================== 전역 함수 노출 ====================

// Excel 다운로드 관련
window.downloadExcel = downloadExcel;
window.downloadAsCSV = downloadAsCSV;

// 미디어 다운로드 관련
window.downloadMedia = downloadMedia;
window.checkMediaDownloadSupport = checkMediaDownloadSupport;

// 유틸리티 함수들
window.cleanText = cleanText;
window.cleanContent = cleanContent;
window.formatNumber = formatNumber;
window.formatDate = formatDate;

console.log('✅ 통합 다운로드 모듈 (Excel + Media) 로드 완료');