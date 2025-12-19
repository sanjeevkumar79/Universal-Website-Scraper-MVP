let currentResponse = null;

async function scrapeWebsite() {
    const urlInput = document.getElementById('url-input');
    const scrapeBtn = document.getElementById('scrape-btn');
    const btnText = document.getElementById('btn-text');
    const btnLoading = document.getElementById('btn-loading');
    const errorContainer = document.getElementById('error-container');
    const resultsContainer = document.getElementById('results-container');

    const url = urlInput.value.trim();

    // Validate URL
    if (!url) {
        alert('Please enter a URL');
        return;
    }

    if (!url.startsWith('http://') && !url.startsWith('https://')) {
        alert('URL must start with http:// or https://');
        return;
    }

    // Reset UI
    errorContainer.style.display = 'none';
    resultsContainer.style.display = 'none';

    // Show loading state
    scrapeBtn.disabled = true;
    btnText.style.display = 'none';
    btnLoading.style.display = 'inline-block';

    try {
        const response = await fetch('/scrape', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ url })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        currentResponse = data;

        // Display results
        displayResults(data.result);

    } catch (error) {
        showError(`Failed to scrape: ${error.message}`);
    } finally {
        // Reset button
        scrapeBtn.disabled = false;
        btnText.style.display = 'inline';
        btnLoading.style.display = 'none';
    }
}

function displayResults(result) {
    const resultsContainer = document.getElementById('results-container');
    const errorContainer = document.getElementById('error-container');
    const errorList = document.getElementById('error-list');

    // Show errors if any
    if (result.errors && result.errors.length > 0) {
        errorList.innerHTML = '';
        result.errors.forEach(error => {
            const li = document.createElement('li');
            li.textContent = `[${error.phase}] ${error.message}`;
            errorList.appendChild(li);
        });
        errorContainer.style.display = 'block';
    }

    // Display meta information
    displayMeta(result.meta, result.url, result.scrapedAt);

    // Display interactions
    displayInteractions(result.interactions);

    // Display sections
    displaySections(result.sections);

    // Show results container
    resultsContainer.style.display = 'block';
}

function displayMeta(meta, url, scrapedAt) {
    const metaInfo = document.getElementById('meta-info');
    metaInfo.innerHTML = `
        <h3>📋 Metadata</h3>
        <p><strong>URL:</strong> ${escapeHtml(url)}</p>
        <p><strong>Scraped At:</strong> ${scrapedAt}</p>
        <p><strong>Title:</strong> ${escapeHtml(meta.title || 'N/A')}</p>
        <p><strong>Description:</strong> ${escapeHtml(meta.description || 'N/A')}</p>
        <p><strong>Language:</strong> ${escapeHtml(meta.language || 'N/A')}</p>
        ${meta.canonical ? `<p><strong>Canonical:</strong> ${escapeHtml(meta.canonical)}</p>` : ''}
    `;
}

function displayInteractions(interactions) {
    const interactionsInfo = document.getElementById('interactions-info');

    const hasInteractions =
        interactions.clicks.length > 0 ||
        interactions.scrolls > 0 ||
        interactions.pages.length > 1;

    if (!hasInteractions) {
        interactionsInfo.style.display = 'none';
        return;
    }

    interactionsInfo.style.display = 'block';

    let html = '<h3>🎯 Interactions</h3>';

    if (interactions.clicks.length > 0) {
        html += `<p><strong>Clicks:</strong> ${interactions.clicks.length}</p>`;
        html += '<ul>';
        interactions.clicks.forEach(click => {
            html += `<li>${escapeHtml(click)}</li>`;
        });
        html += '</ul>';
    }

    if (interactions.scrolls > 0) {
        html += `<p><strong>Scrolls:</strong> ${interactions.scrolls}</p>`;
    }

    if (interactions.pages.length > 1) {
        html += `<p><strong>Pages Visited:</strong> ${interactions.pages.length}</p>`;
        html += '<ul>';
        interactions.pages.forEach(page => {
            html += `<li>${escapeHtml(page)}</li>`;
        });
        html += '</ul>';
    }

    interactionsInfo.innerHTML = html;
}

function displaySections(sections) {
    const sectionCount = document.getElementById('section-count');
    const sectionsList = document.getElementById('sections-list');

    sectionCount.textContent = sections.length;
    sectionsList.innerHTML = '';

    sections.forEach((section, index) => {
        const sectionDiv = document.createElement('div');
        sectionDiv.className = 'section-item';

        const preview = section.content.text.substring(0, 100);
        const stats = {
            headings: section.content.headings.length,
            links: section.content.links.length,
            images: section.content.images.length,
            lists: section.content.lists.length,
            tables: section.content.tables.length
        };

        sectionDiv.innerHTML = `
            <div class="section-header" onclick="toggleSection(${index})">
                <div>
                    <div class="section-title">
                        ${escapeHtml(section.label)}
                        <span class="section-type">${section.type}</span>
                    </div>
                    <div class="section-preview">${escapeHtml(preview)}${section.content.text.length > 100 ? '...' : ''}</div>
                </div>
                <div class="section-toggle" id="toggle-${index}">▼</div>
            </div>
            <div class="section-content" id="content-${index}">
                <div class="content-stats">
                    <div class="stat-item">
                        <div class="stat-value">${stats.headings}</div>
                        <div class="stat-label">Headings</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value">${stats.links}</div>
                        <div class="stat-label">Links</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value">${stats.images}</div>
                        <div class="stat-label">Images</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value">${stats.lists}</div>
                        <div class="stat-label">Lists</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value">${stats.tables}</div>
                        <div class="stat-label">Tables</div>
                    </div>
                </div>
                <div class="json-viewer">
                    <pre>${escapeHtml(JSON.stringify(section, null, 2))}</pre>
                </div>
            </div>
        `;

        sectionsList.appendChild(sectionDiv);
    });
}

function toggleSection(index) {
    const content = document.getElementById(`content-${index}`);
    const toggle = document.getElementById(`toggle-${index}`);

    content.classList.toggle('active');
    toggle.classList.toggle('active');
}

function downloadJSON() {
    if (!currentResponse) {
        alert('No data to download');
        return;
    }

    const dataStr = JSON.stringify(currentResponse, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(dataBlob);

    const link = document.createElement('a');
    link.href = url;
    link.download = `scrape-${Date.now()}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
}

function showError(message) {
    const errorContainer = document.getElementById('error-container');
    const errorList = document.getElementById('error-list');

    errorList.innerHTML = `<li>${escapeHtml(message)}</li>`;
    errorContainer.style.display = 'block';
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Allow Enter key to submit
document.getElementById('url-input').addEventListener('keypress', function (e) {
    if (e.key === 'Enter') {
        scrapeWebsite();
    }
});
