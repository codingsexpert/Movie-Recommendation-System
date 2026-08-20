// MovieGraph AI - JioHotstar Clone JS v2.0
// Features: Skeleton loaders, Search history, Error states, Keyboard shortcuts, Enhanced detail panel

window.handleImageLoadError = function(img, title) {
  img.src = 'https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?auto=format&fit=crop&w=500&q=80';
};

document.addEventListener('DOMContentLoaded', () => {

  // ─── DOM References ───
  const searchForm          = document.getElementById('searchForm');
  const queryInput          = document.getElementById('queryInput');
  const searchBtn           = document.getElementById('searchBtn');
  const searchOverlay       = document.getElementById('searchOverlay');
  const navSearch           = document.getElementById('navSearch');
  
  const loadingIndicator    = document.getElementById('loadingIndicator');
  const aiSearchResults     = document.getElementById('aiSearchResults');
  const aiSearchGrid        = document.getElementById('aiSearchGrid');
  const aiSearchTitle       = document.getElementById('aiSearchTitle');

  const heroCarousel        = document.getElementById('heroCarousel');
  
  const rowAction           = document.getElementById('rowAction');
  const rowSciFi            = document.getElementById('rowSciFi');
  const rowDrama            = document.getElementById('rowDrama');
  const rowAll              = document.getElementById('rowAll');

  const trailerModal        = document.getElementById('trailerModal');
  const trailerIframe       = document.getElementById('trailerIframe');
  const closeTrailerBtn     = document.getElementById('closeTrailerBtn');
  const trailerBackdrop     = document.getElementById('trailerBackdrop');

  let allCatalogMovies = [];

  // ═══════════════════════════════════════════
  // Search History (localStorage)
  // ═══════════════════════════════════════════
  const MAX_HISTORY = 8;
  
  function getSearchHistory() {
    try {
      return JSON.parse(localStorage.getItem('mg-search-history') || '[]');
    } catch { return []; }
  }
  
  function addToSearchHistory(query) {
    let history = getSearchHistory();
    history = history.filter(h => h.toLowerCase() !== query.toLowerCase());
    history.unshift(query);
    history = history.slice(0, MAX_HISTORY);
    localStorage.setItem('mg-search-history', JSON.stringify(history));
    renderSearchHistory();
  }
  
  function removeFromHistory(query) {
    let history = getSearchHistory().filter(h => h !== query);
    localStorage.setItem('mg-search-history', JSON.stringify(history));
    renderSearchHistory();
  }
  
  function renderSearchHistory() {
    let container = document.getElementById('searchHistoryChips');
    if (!container) {
      container = document.createElement('div');
      container.id = 'searchHistoryChips';
      container.className = 'search-history';
      const searchContainer = document.querySelector('.search-container');
      if (searchContainer) searchContainer.appendChild(container);
    }
    
    const history = getSearchHistory();
    if (history.length === 0) {
      container.innerHTML = '';
      return;
    }
    
    container.innerHTML = `
      <span class="search-history-label">Recent:</span>
      ${history.map(h => `
        <span class="history-chip" data-query="${h}">
          ${h.length > 30 ? h.substring(0, 30) + '…' : h}
          <span class="remove-chip" data-remove="${h}">×</span>
        </span>
      `).join('')}
    `;
    
    container.querySelectorAll('.history-chip').forEach(chip => {
      chip.addEventListener('click', (e) => {
        if (e.target.classList.contains('remove-chip')) {
          e.stopPropagation();
          removeFromHistory(e.target.dataset.remove);
          return;
        }
        queryInput.value = chip.dataset.query;
        searchForm.dispatchEvent(new Event('submit'));
      });
    });
  }

  // ═══════════════════════════════════════════
  // Skeleton Loader
  // ═══════════════════════════════════════════
  function renderSkeletons(container, count = 6) {
    if (!container) return;
    container.innerHTML = '';
    for (let i = 0; i < count; i++) {
      const skeleton = document.createElement('div');
      skeleton.className = 'skeleton-card';
      container.appendChild(skeleton);
    }
  }

  // ═══════════════════════════════════════════
  // Error State
  // ═══════════════════════════════════════════
  function renderError(container, message, retryFn) {
    if (!container) return;
    container.innerHTML = `
      <div class="error-card">
        <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="10"></circle>
          <line x1="15" y1="9" x2="9" y2="15"></line>
          <line x1="9" y1="9" x2="15" y2="15"></line>
        </svg>
        <h4>Something went wrong</h4>
        <p>${message}</p>
        ${retryFn ? '<button onclick="location.reload()">Retry</button>' : ''}
      </div>
    `;
  }

  // ═══════════════════════════════════════════
  // Keyboard Shortcuts
  // ═══════════════════════════════════════════
  document.addEventListener('keydown', (e) => {
    // "/" to focus search
    if (e.key === '/' && !e.ctrlKey && !e.metaKey && document.activeElement !== queryInput) {
      e.preventDefault();
      searchOverlay.classList.remove('hidden');
      queryInput.focus();
    }
    // Escape to close overlays
    if (e.key === 'Escape') {
      if (!trailerModal.classList.contains('hidden')) {
        closeTrailer();
      } else if (!searchOverlay.classList.contains('hidden')) {
        searchOverlay.classList.add('hidden');
      } else if (currentActivePanel) {
        currentActivePanel.remove();
        currentActivePanel = null;
      }
    }
  });

  // Add keyboard hint
  const hint = document.createElement('div');
  hint.className = 'keyboard-hint';
  hint.innerHTML = 'Press <kbd>/</kbd> to search · <kbd>Esc</kbd> to close';
  document.body.appendChild(hint);
  setTimeout(() => { hint.style.opacity = '0'; setTimeout(() => hint.remove(), 500); }, 6000);

  // ═══════════════════════════════════════════
  // Toggle Search Overlay
  // ═══════════════════════════════════════════
  navSearch.addEventListener('click', () => {
    searchOverlay.classList.toggle('hidden');
    if (!searchOverlay.classList.contains('hidden')) {
      queryInput.focus();
      renderSearchHistory();
    }
  });

  // ═══════════════════════════════════════════
  // Load Catalog with Skeletons
  // ═══════════════════════════════════════════
  // Show skeletons immediately
  renderSkeletons(rowAction, 6);
  renderSkeletons(rowSciFi, 6);
  renderSkeletons(rowDrama, 6);
  renderSkeletons(rowAll, 8);

  loadMovieCatalog();

  async function loadMovieCatalog() {
    try {
      const res = await fetch('/api/catalog');
      if (!res.ok) throw new Error(`API returned ${res.status}`);
      allCatalogMovies = await res.json();
      renderCatalogRows(allCatalogMovies);
      setupHeroCarousel(allCatalogMovies);
    } catch(err) {
      console.warn('Catalog load failed:', err);
      renderError(rowAll, 'Failed to load movie catalog. Please check your connection.');
    }
  }

  function renderCatalogRows(movies) {
    if(!movies) return;
    
    const actionMovies = movies.filter(m => m.genres && m.genres.includes('Action'));
    const sciFiMovies = movies.filter(m => m.genres && m.genres.includes('Sci-Fi'));
    const dramaMovies = movies.filter(m => m.genres && m.genres.includes('Drama'));

    renderRow(rowAction, actionMovies);
    renderRow(rowSciFi, sciFiMovies);
    renderRow(rowDrama, dramaMovies);
    renderRow(rowAll, movies);
  }

  function renderRow(container, movies) {
    if(!container) return;
    container.innerHTML = '';
    if (!movies || movies.length === 0) {
      container.innerHTML = '<p style="color:var(--text-muted); padding: 1rem;">No movies found in this category.</p>';
      return;
    }
    movies.slice(0, 15).forEach(movie => {
      const card = document.createElement('div');
      card.className = 'movie-card';
      card.innerHTML = `<img src="${movie.poster || ''}" alt="${movie.title}" onerror="handleImageLoadError(this, '${movie.title.replace(/'/g, "\\'")}')" />`;
      card.addEventListener('click', () => handleHotstarPanelClick(movie, container.parentElement));
      container.appendChild(card);
    });
  }

  // ═══════════════════════════════════════════
  // Hero Carousel
  // ═══════════════════════════════════════════
  let heroInterval;
  function setupHeroCarousel(movies) {
    if(!movies || movies.length === 0) return;
    const heroMovies = movies.filter(m => parseFloat(m.rating || 0) >= 8.0).slice(0, 5);
    if(heroMovies.length === 0) return;
    
    let idx = 0;
    renderHero(heroMovies[idx]);
    
    heroInterval = setInterval(() => {
      idx = (idx + 1) % heroMovies.length;
      renderHero(heroMovies[idx]);
    }, 7000);
  }

  function renderHero(movie) {
    const bgUrl = movie.backdrop || movie.poster || 'https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?auto=format&fit=crop&w=1600&q=80';
    const genresText = (movie.genres || ['Action', 'Drama']).join(' • ');
    const castText = (movie.actors || []).slice(0, 3).join(', ');
    
    heroCarousel.innerHTML = `
      <div class="hotstar-hero carousel-slide" style="background-image: url('${bgUrl}');">
        <div class="hotstar-content">
          <h1 class="hotstar-title">${movie.title}</h1>
          <div class="hotstar-meta">
            <span class="imdb">IMDb ${movie.rating || '8.5'}</span>
            <span>•</span>
            <span>${movie.year || '2023'}</span>
            <span>•</span>
            <span>${genresText}</span>
          </div>
          <p class="hotstar-overview">${movie.overview || (castText ? `Starring ${castText}` : 'A captivating cinematic experience.')}</p>
          <div class="hotstar-genres">${genresText}</div>
          <div class="hotstar-actions">
            <button class="hotstar-btn-play" onclick="openTrailer('${movie.trailer || ''}')">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>
              Watch Trailer
            </button>
            <button class="hotstar-btn-add">+</button>
          </div>
        </div>
      </div>
    `;
  }

  // ═══════════════════════════════════════════
  // Trailer Modal
  // ═══════════════════════════════════════════
  window.openTrailer = function(url) {
    if (!url) { alert("Trailer not available"); return; }
    if (url.includes('youtube.com/results')) {
       window.open(url, '_blank');
       return;
    }
    let embedUrl = url;
    if (url.includes('youtube.com/watch?v=')) {
      embedUrl = url.replace('watch?v=', 'embed/');
    }
    trailerIframe.src = embedUrl;
    trailerModal.classList.remove('hidden');
  }

  closeTrailerBtn.addEventListener('click', closeTrailer);
  trailerBackdrop.addEventListener('click', closeTrailer);
  
  function closeTrailer() {
    trailerModal.classList.add('hidden');
    trailerIframe.src = "";
  }

  // ═══════════════════════════════════════════
  // Enhanced Detail Panel with Director/Cast/Awards
  // ═══════════════════════════════════════════
  let currentActivePanel = null;

  async function handleHotstarPanelClick(movie, parentContainer) {
    if (currentActivePanel) {
      currentActivePanel.remove();
      currentActivePanel = null;
    }

    const panel = document.createElement('div');
    panel.className = 'hotstar-panel';
    currentActivePanel = panel;

    const bgUrl = movie.backdrop || movie.poster || 'https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?auto=format&fit=crop&w=1600&q=80';
    const directorsText = (movie.directors || []).join(', ') || 'Unknown';
    const actorsText = (movie.actors || []).slice(0, 4).join(', ') || 'Unknown';
    const themesText = (movie.themes || []).join(', ') || 'N/A';
    const awardsHtml = (movie.awards || []).map(a => `<span class="panel-award-badge">🏆 ${a}</span>`).join('');

    panel.innerHTML = `
      <div class="hotstar-hero" style="background-image: url('${bgUrl}'); min-height: 400px;">
        <button class="hotstar-close" id="panelCloseBtn">&times;</button>
        <div class="hotstar-content" style="width: 70%; padding: 2rem;">
          <h2 class="hotstar-title" style="font-size: 2.5rem;">${movie.title}</h2>
          <div class="hotstar-meta">
            <span class="imdb">IMDb ${movie.rating || 'N/A'}</span>
            <span>•</span>
            <span>${movie.year || 'Unknown'}</span>
            <span>•</span>
            <span>${(movie.genres || []).join(' • ')}</span>
          </div>
          <p class="hotstar-overview" style="-webkit-line-clamp: 3;">${movie.overview || `Directed by ${directorsText}. Starring ${actorsText}.`}</p>
          <div class="hotstar-actions">
            <button class="hotstar-btn-play" onclick="openTrailer('${movie.trailer || ''}')">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>
              Play Trailer
            </button>
          </div>
        </div>
      </div>
      <div class="panel-details-grid">
        <div class="panel-detail-item">
          <label>Director</label>
          <p>${directorsText}</p>
        </div>
        <div class="panel-detail-item">
          <label>Cast</label>
          <p>${actorsText}</p>
        </div>
        <div class="panel-detail-item">
          <label>Themes</label>
          <p>${themesText}</p>
        </div>
        <div class="panel-detail-item">
          <label>Rating</label>
          <p>⭐ ${movie.rating || 'N/A'} / 10</p>
        </div>
      </div>
      ${awardsHtml ? `<div class="panel-awards">${awardsHtml}</div>` : ''}
      <div class="hotstar-related-section">
        <h3 class="hotstar-related-heading">More Like This</h3>
        <div class="mini-grid" id="panelMiniGrid_${movie.id || Date.now()}">
          <div class="skeleton-card"></div>
          <div class="skeleton-card"></div>
          <div class="skeleton-card"></div>
          <div class="skeleton-card"></div>
        </div>
      </div>
    `;

    parentContainer.insertAdjacentElement('afterend', panel);
    
    setTimeout(() => {
      panel.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }, 100);

    panel.querySelector('#panelCloseBtn').addEventListener('click', () => {
      panel.remove();
      currentActivePanel = null;
    });

    // Fetch related movies
    const gridId = panel.querySelector('.mini-grid').id;
    try {
      const res = await fetch(`/api/related/${encodeURIComponent(movie.title)}`);
      if (res.ok) {
        const data = await res.json();
        const miniGrid = document.getElementById(gridId);
        if (miniGrid) {
          if (data.movies && data.movies.length > 0) {
            miniGrid.innerHTML = data.movies.map(m => `
              <div class="mini-card" onclick="alert('Navigating to ${m.title ? m.title.replace(/'/g, "\\'") : "movie"}')" >
                <img src="${m.poster || `/api/poster?title=${encodeURIComponent(m.title || m)}`}" alt="${m.title || m}" onerror="handleImageLoadError(this, '')" />
                <div class="mini-card-title">${m.title || m}</div>
              </div>
            `).join('');
          } else {
            miniGrid.innerHTML = '<p style="color:var(--text-muted);">No similar movies found.</p>';
          }
        }
      }
    } catch(e) {
      const miniGrid = document.getElementById(gridId);
      if (miniGrid) miniGrid.innerHTML = '<p style="color:var(--text-muted);">Could not load recommendations.</p>';
    }
  }


  // ═══════════════════════════════════════════
  // AI Search with Error Handling & History
  // ═══════════════════════════════════════════
  searchForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const query = queryInput.value.trim();
    if(!query) return;

    // Add to search history
    addToSearchHistory(query);

    loadingIndicator.classList.remove('hidden');
    aiSearchResults.classList.add('hidden');
    
    try {
      const res = await fetch('/api/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: query })
      });
      
      if (!res.ok) throw new Error(`Server error: ${res.status}`);
      
      const data = await res.json();
      loadingIndicator.classList.add('hidden');
      
      // Check for error in response
      if (data.answer && (data.answer.includes('[Error]') || data.answer.includes('[Warning]'))) {
        aiSearchTitle.textContent = `Results for: "${query}"`;
        aiSearchResults.classList.remove('hidden');
        aiSearchGrid.innerHTML = `<div class="error-card">
          <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path>
            <line x1="12" y1="9" x2="12" y2="13"></line>
            <line x1="12" y1="17" x2="12.01" y2="17"></line>
          </svg>
          <h4>Rate Limit or API Error</h4>
          <p>${data.answer.replace(/\*\*/g, '')}</p>
        </div>`;
        return;
      }
      
      aiSearchTitle.textContent = `AI Recommendations for: "${query}"`;
      aiSearchResults.classList.remove('hidden');

      let moviesToRender = data.movies || [];
      
      if (moviesToRender.length === 0 && data.answer) {
         const regex = /\*\*([^*]+)\*\*|\*([^*]+)\*/g;
         let match;
         const extracted = new Set();
         while ((match = regex.exec(data.answer)) !== null) {
            let mTitle = match[1] || match[2];
            mTitle = mTitle.trim();
            if (mTitle.length > 1 && mTitle.length < 50 && !mTitle.toLowerCase().includes('genre') && !mTitle.toLowerCase().includes('director')) {
               extracted.add(mTitle);
            }
         }
         
         moviesToRender = Array.from(extracted).map(title => ({
            title: title,
            poster: `/api/poster?title=${encodeURIComponent(title)}`,
            backdrop: `/api/poster?title=${encodeURIComponent(title)}`,
            year: "TMDB",
            rating: "AI",
            overview: data.answer.substring(0, 200) + "...",
            trailer: `https://www.youtube.com/results?search_query=${encodeURIComponent(title + " movie trailer")}`,
            genres: ['AI Recommendation']
         }));
      }

      if (moviesToRender.length > 0) {
        renderRow(aiSearchGrid, moviesToRender);
      } else {
        aiSearchGrid.innerHTML = `<div style="padding: 1.5rem; color: var(--text-muted); line-height: 1.6;">
           ${data.answer ? data.answer.replace(/\n/g, '<br>') : 'No specific movies found for this query.'}
        </div>`;
      }

    } catch (error) {
      console.error(error);
      loadingIndicator.classList.add('hidden');
      aiSearchTitle.textContent = 'Search Error';
      aiSearchResults.classList.remove('hidden');
      aiSearchGrid.innerHTML = '';
      renderError(aiSearchGrid, `Failed to search: ${error.message}. Please try again.`, true);
    }
  });

  // Initialize search history display
  renderSearchHistory();

});
