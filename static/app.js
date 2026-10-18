/* ==========================================================================
   MarkItDown Studio - Client Application Logic
   ========================================================================== */

document.addEventListener('DOMContentLoaded', () => {
  // Elements
  const themeToggleBtn = document.getElementById('themeToggleBtn');
  const dropZone = document.getElementById('dropZone');
  const fileInput = document.getElementById('fileInput');
  const selectedFilesContainer = document.getElementById('selectedFilesContainer');
  const fileList = document.getElementById('fileList');
  const fileCountBadge = document.getElementById('fileCountBadge');
  const clearFilesBtn = document.getElementById('clearFilesBtn');
  const convertBtn = document.getElementById('convertBtn');
  const autoDownloadCheck = document.getElementById('autoDownloadCheck');
  
  // Tabs
  const tabUploadBtn = document.getElementById('tabUploadBtn');
  const tabPathBtn = document.getElementById('tabPathBtn');
  const uploadTab = document.getElementById('uploadTab');
  const pathTab = document.getElementById('pathTab');
  const localPathInput = document.getElementById('localPathInput');

  // Loading
  const loadingCard = document.getElementById('loadingCard');
  const loadingStatusText = document.getElementById('loadingStatusText');
  const loadingDetailText = document.getElementById('loadingDetailText');
  const elapsedTimer = document.getElementById('elapsedTimer');

  // Result
  const resultCard = document.getElementById('resultCard');
  const resultFileName = document.getElementById('resultFileName');
  const statWords = document.getElementById('statWords');
  const statChars = document.getElementById('statChars');
  const statSize = document.getElementById('statSize');
  const statTime = document.getElementById('statTime');

  // View modes
  const viewPreviewBtn = document.getElementById('viewPreviewBtn');
  const viewRawBtn = document.getElementById('viewRawBtn');
  const renderedMarkdownView = document.getElementById('renderedMarkdownView');
  const rawMarkdownView = document.getElementById('rawMarkdownView');
  const rawMarkdownTextarea = document.getElementById('rawMarkdownTextarea');

  // Actions
  const copyMarkdownBtn = document.getElementById('copyMarkdownBtn');
  const downloadMarkdownBtn = document.getElementById('downloadMarkdownBtn');

  // History
  const historyCard = document.getElementById('historyCard');
  const historyList = document.getElementById('historyList');
  const clearHistoryBtn = document.getElementById('clearHistoryBtn');

  // Toast
  const toast = document.getElementById('toast');
  const toastMessage = document.getElementById('toastMessage');

  // State
  let selectedFiles = [];
  let currentMarkdown = '';
  let currentOutputName = 'document.md';
  let timerInterval = null;
  let startTime = 0;
  let history = [];

  // Theme Persistence
  const savedTheme = localStorage.getItem('markitdown_theme') || 'dark-theme';
  document.body.className = savedTheme;

  themeToggleBtn.addEventListener('click', () => {
    if (document.body.classList.contains('dark-theme')) {
      document.body.classList.replace('dark-theme', 'light-theme');
      localStorage.setItem('markitdown_theme', 'light-theme');
    } else {
      document.body.classList.replace('light-theme', 'dark-theme');
      localStorage.setItem('markitdown_theme', 'dark-theme');
    }
  });

  // Tab Switching
  tabUploadBtn.addEventListener('click', () => {
    tabUploadBtn.classList.add('active');
    tabPathBtn.classList.remove('active');
    uploadTab.classList.add('active');
    pathTab.classList.remove('active');
    updateConvertButtonState();
  });

  tabPathBtn.addEventListener('click', () => {
    tabPathBtn.classList.add('active');
    tabUploadBtn.classList.remove('active');
    pathTab.classList.add('active');
    uploadTab.classList.remove('active');
    updateConvertButtonState();
  });

  localPathInput.addEventListener('input', () => {
    updateConvertButtonState();
  });

  // Dropzone Events
  dropZone.addEventListener('click', () => fileInput.click());

  ['dragenter', 'dragover'].forEach(eventName => {
    dropZone.addEventListener(eventName, (e) => {
      e.preventDefault();
      e.stopPropagation();
      dropZone.classList.add('dragover');
    });
  });

  ['dragleave', 'drop'].forEach(eventName => {
    dropZone.addEventListener(eventName, (e) => {
      e.preventDefault();
      e.stopPropagation();
      dropZone.classList.remove('dragover');
    });
  });

  dropZone.addEventListener('drop', (e) => {
    const droppedFiles = Array.from(e.dataTransfer.files);
    if (droppedFiles.length > 0) {
      addFiles(droppedFiles);
    }
  });

  fileInput.addEventListener('change', () => {
    const files = Array.from(fileInput.files);
    if (files.length > 0) {
      addFiles(files);
    }
    fileInput.value = ''; // Reset for re-selection
  });

  function addFiles(newFiles) {
    selectedFiles = [...selectedFiles, ...newFiles];
    renderFileList();
    updateConvertButtonState();
  }

  function formatBytes(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  }

  function renderFileList() {
    if (selectedFiles.length === 0) {
      selectedFilesContainer.style.display = 'none';
      return;
    }

    selectedFilesContainer.style.display = 'block';
    fileCountBadge.textContent = selectedFiles.length;
    fileList.innerHTML = '';

    selectedFiles.forEach((file, index) => {
      const ext = file.name.split('.').pop() || 'FILE';
      const item = document.createElement('div');
      item.className = 'file-item';
      item.innerHTML = `
        <div class="file-item-info">
          <span class="file-type-badge">${ext}</span>
          <div>
            <div class="file-name-text" title="${file.name}">${file.name}</div>
            <div class="file-size-text">${formatBytes(file.size)}</div>
          </div>
        </div>
        <button class="file-remove-btn" title="Gỡ tệp" data-index="${index}">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </button>
      `;
      fileList.appendChild(item);
    });

    fileList.querySelectorAll('.file-remove-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const idx = parseInt(e.currentTarget.getAttribute('data-index'), 10);
        selectedFiles.splice(idx, 1);
        renderFileList();
        updateConvertButtonState();
      });
    });
  }

  clearFilesBtn.addEventListener('click', () => {
    selectedFiles = [];
    renderFileList();
    updateConvertButtonState();
  });

  function updateConvertButtonState() {
    const isUploadTab = uploadTab.classList.contains('active');
    if (isUploadTab) {
      convertBtn.disabled = selectedFiles.length === 0;
    } else {
      const pathVal = localPathInput.value.trim();
      convertBtn.disabled = pathVal.length === 0;
    }
  }

  // Toast Functionality
  function showToast(message, type = 'success') {
    toastMessage.textContent = message;
    toast.className = `toast toast-${type} show`;
    setTimeout(() => {
      toast.classList.remove('show');
    }, 3200);
  }

  // View Mode Switching
  viewPreviewBtn.addEventListener('click', () => {
    viewPreviewBtn.classList.add('active');
    viewRawBtn.classList.remove('active');
    renderedMarkdownView.style.display = 'block';
    rawMarkdownView.style.display = 'none';
  });

  viewRawBtn.addEventListener('click', () => {
    viewRawBtn.classList.add('active');
    viewPreviewBtn.classList.remove('active');
    renderedMarkdownView.style.display = 'none';
    rawMarkdownView.style.display = 'block';
  });

  // Copy Markdown
  copyMarkdownBtn.addEventListener('click', async () => {
    if (!currentMarkdown) return;
    try {
      await navigator.clipboard.writeText(currentMarkdown);
      const originalText = copyMarkdownBtn.innerHTML;
      copyMarkdownBtn.innerHTML = `
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="20 6 9 17 4 12"></polyline>
        </svg>
        <span>Đã sao chép!</span>
      `;
      showToast('Đã sao chép toàn bộ Markdown vào bộ nhớ tạm!');
      setTimeout(() => {
        copyMarkdownBtn.innerHTML = originalText;
      }, 2000);
    } catch (err) {
      showToast('Không thể sao chép vào bộ nhớ tạm: ' + err.message, 'error');
    }
  });

  // Download Markdown
  downloadMarkdownBtn.addEventListener('click', () => {
    if (!currentMarkdown) return;
    downloadMarkdownFile(currentOutputName, currentMarkdown);
  });

  function downloadMarkdownFile(filename, content) {
    const blob = new Blob([content], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    showToast(`Đã tải về tệp ${filename}!`);
  }

  // Timer helpers
  function startTimer() {
    startTime = Date.now();
    elapsedTimer.textContent = '0.0s';
    timerInterval = setInterval(() => {
      const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
      elapsedTimer.textContent = `${elapsed}s`;
    }, 100);
  }

  function stopTimer() {
    clearInterval(timerInterval);
    const elapsed = ((Date.now() - startTime) / 1000).toFixed(2);
    return elapsed;
  }

  // Convert Process
  convertBtn.addEventListener('click', async () => {
    const isUploadTab = uploadTab.classList.contains('active');

    // UI Loading state
    resultCard.style.display = 'none';
    loadingCard.style.display = 'block';
    convertBtn.disabled = true;
    startTimer();

    try {
      if (isUploadTab) {
        // Upload flow: loop through files or process the primary file
        const file = selectedFiles[0];
        loadingStatusText.textContent = `Đang chuyển đổi: ${file.name}...`;
        loadingDetailText.textContent = `Tải lên và xử lý tệp dung lượng ${formatBytes(file.size)}`;

        const doReflow = document.getElementById('reflowCheck') ? document.getElementById('reflowCheck').checked : true;
        const formData = new FormData();
        formData.append('file', file);
        formData.append('reflow', doReflow);

        const response = await fetch('/api/convert', {
          method: 'POST',
          body: formData,
        });

        const data = await response.json();
        if (!response.ok || !data.success) {
          throw new Error(data.error || 'Có lỗi xảy ra khi chuyển đổi tệp.');
        }

        handleConversionSuccess(data);

      } else {
        // Local path flow
        let pathVal = localPathInput.value.trim();
        // Remove quotes if present (e.g. from "Copy as path")
        pathVal = pathVal.replace(/^["']|["']$/g, '');

        loadingStatusText.textContent = `Đang đọc từ đường dẫn ổ đĩa...`;
        loadingDetailText.textContent = pathVal;

        const doReflow = document.getElementById('reflowCheck') ? document.getElementById('reflowCheck').checked : true;
        const response = await fetch('/api/convert-path', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ path: pathVal, reflow: doReflow }),
        });

        const data = await response.json();
        if (!response.ok || !data.success) {
          throw new Error(data.error || 'Có lỗi xảy ra khi đọc tệp từ ổ đĩa.');
        }

        handleConversionSuccess(data);
      }
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      loadingCard.style.display = 'none';
      convertBtn.disabled = false;
      stopTimer();
    }
  });

  function handleConversionSuccess(data) {
    const duration = stopTimer();
    currentMarkdown = data.markdown || '';
    const baseName = data.filename.replace(/\.[^/.]+$/, "");
    currentOutputName = `${baseName}.md`;

    // Render Stats
    resultFileName.textContent = currentOutputName;
    const wordsCount = currentMarkdown.trim().split(/\s+/).filter(Boolean).length;
    const charsCount = currentMarkdown.length;
    const sizeFormatted = formatBytes(new Blob([currentMarkdown]).size);

    statWords.textContent = `${wordsCount.toLocaleString()} từ`;
    statChars.textContent = `${charsCount.toLocaleString()} ký tự`;
    statSize.textContent = sizeFormatted;
    statTime.textContent = `${duration}s`;

    // Render Views
    rawMarkdownTextarea.value = currentMarkdown;
    if (typeof marked !== 'undefined') {
      renderedMarkdownView.innerHTML = marked.parse(currentMarkdown);
    } else {
      renderedMarkdownView.textContent = currentMarkdown;
    }

    resultCard.style.display = 'block';
    resultCard.scrollIntoView({ behavior: 'smooth' });

    // Auto-download check
    if (autoDownloadCheck.checked) {
      downloadMarkdownFile(currentOutputName, currentMarkdown);
    }

    // Add to history
    addToHistory({
      name: currentOutputName,
      originalName: data.filename,
      size: sizeFormatted,
      time: duration,
      words: wordsCount,
      markdown: currentMarkdown
    });

    showToast(`Chuyển đổi thành công ${currentOutputName}!`);
  }

  function addToHistory(item) {
    history.unshift(item);
    renderHistory();
  }

  function renderHistory() {
    if (history.length === 0) {
      historyCard.style.display = 'none';
      return;
    }

    historyCard.style.display = 'block';
    historyList.innerHTML = '';

    history.forEach((histItem, idx) => {
      const el = document.createElement('div');
      el.className = 'history-item';
      el.innerHTML = `
        <div class="history-item-left">
          <span class="file-type-badge">MD</span>
          <div>
            <strong>${histItem.name}</strong>
            <div class="file-size-text">${histItem.size} • ${histItem.words.toLocaleString()} từ • ${histItem.time}s</div>
          </div>
        </div>
        <button class="btn btn-secondary" style="padding: 0.4rem 0.85rem; font-size: 0.8rem;">
          Mở lại
        </button>
      `;

      el.addEventListener('click', () => {
        currentMarkdown = histItem.markdown;
        currentOutputName = histItem.name;
        resultFileName.textContent = currentOutputName;
        rawMarkdownTextarea.value = currentMarkdown;
        if (typeof marked !== 'undefined') {
          renderedMarkdownView.innerHTML = marked.parse(currentMarkdown);
        }
        resultCard.style.display = 'block';
        resultCard.scrollIntoView({ behavior: 'smooth' });
        showToast(`Đã mở lại tệp: ${histItem.name}`);
      });

      historyList.appendChild(el);
    });
  }

  clearHistoryBtn.addEventListener('click', () => {
    history = [];
    renderHistory();
  });

});
