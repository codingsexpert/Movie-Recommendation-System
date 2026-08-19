// MovieGraph AI - JioHotstar Clone JS

window.handleImageLoadError = function(img, title) {
  // simple fallback
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

  // Toggle Search Overlay
  navSearch.addEventListener('click', () => {
    searchOverlay.classList.toggle('hidden');
    if (!searchOverlay.classList.contains('hidden')) {
      queryInput.focus();
    }
  });

  // Load Catalog
  loadMovieCatalog();

  async function loadMovieCatalog() {
    try {
      const res = await fetch('/api/catalog');
      if (!res.ok) return;
      allCatalogMovies = await res.json();
      renderCatalogRows(allCatalogMovies);
      setupHeroCarousel(allCatalogMovies);
    } catch(err) {
      console.warn('Catalog load failed:', err);
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
    movies.slice(0, 15).forEach(movie => {
      const card = document.createElement('div');
      card.className = 'movie-card';
      card.innerHTML = `<img src="${movie.poster || ''}" alt="${movie.title}" onerror="handleImageLoadError(this, '${movie.title.replace(/'/g, "\\'")}')" />`;
      
      // Pass the row container parent so we know where to inject the panel
      card.addEventListener('click', () => handleHotstarPanelClick(movie, container.parentElement));
      container.appendChild(card);
    });
  }

  // Hero Carousel
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
    
    heroCarousel.innerHTML = `
      <div class="hotstar-hero carousel-slide" style="background-image: url('${bgUrl}');">
        <div class="hotstar-content">
          <h1 class="hotstar-title">${movie.title}</h1>
          <div class="hotstar-meta">
            <span class="imdb">IMDb ${movie.rating || '8.5'}</span>
            <span>•</span>
            <span>${movie.year || '2023'}</span>
            <span>•</span>
            <span>U/A 16+</span>
          </div>
          <p class="hotstar-overview">${movie.overview || 'A captivating cinematic experience.'}</p>
          <div class="hotstar-genres">${(movie.genres || ['Action', 'Drama']).join(' • ')}</div>
          <div class="hotstar-actions">
            <button class="hotstar-btn-play" onclick="openTrailer('${movie.trailer || ''}')">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>
              Subscribe to Watch
            </button>
            <button class="hotstar-btn-add">+</button>
          </div>
        </div>
      </div>
    `;
  }

  window.openTrailer = function(url) {
    if (!url) { alert("Trailer not available"); return; }
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

  // Active Panel tracking
  let currentActivePanel = null;

  async function handleHotstarPanelClick(movie, parentContainer) {
    // If a panel is already open, remove it
    if (currentActivePanel) {
      currentActivePanel.remove();
      currentActivePanel = null;
    }

    const panel = document.createElement('div');
    panel.className = 'hotstar-panel';
    currentActivePanel = panel;

    const bgUrl = movie.backdrop || movie.poster || 'https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?auto=format&fit=crop&w=1600&q=80';

    panel.innerHTML = `
      <div class="hotstar-hero" style="background-image: url('${bgUrl}'); min-height: 400px;">
        <button class="hotstar-close" id="panelCloseBtn">&times;</button>
        <div class="hotstar-content" style="width: 70%; padding: 2rem;">
          <h2 class="hotstar-title" style="font-size: 2.5rem;">${movie.title}</h2>
          <div class="hotstar-meta">
            <span class="imdb">IMDb ${movie.rating || 'N/A'}</span>
            <span>•</span>
            <span>${movie.year || 'Unknown'}</span>
          </div>
          <p class="hotstar-overview" style="-webkit-line-clamp: 2;">${movie.overview || 'No description available.'}</p>
          <div class="hotstar-genres">${(movie.genres || []).join(' • ')}</div>
          <div class="hotstar-actions">
            <button class="hotstar-btn-play" onclick="openTrailer('${movie.trailer || ''}')">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>
              Play Trailer
            </button>
          </div>
        </div>
      </div>
      <div class="hotstar-related-section">
        <h3 class="hotstar-related-heading">More Like This</h3>
        <div class="mini-grid" id="panelMiniGrid_${movie.id || Date.now()}">
          <p style="color:var(--text-muted);">Loading related...</p>
        </div>
      </div>
    `;

    // Inject panel right after the row container
    parentContainer.insertAdjacentElement('afterend', panel);
    
    // Smooth scroll to panel
    setTimeout(() => {
      panel.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }, 100);

    // Setup close button
    panel.querySelector('#panelCloseBtn').addEventListener('click', () => {
      panel.remove();
      currentActivePanel = null;
    });

    // Fetch related
    const gridId = panel.querySelector('.mini-grid').id;
    try {
      const res = await fetch(\`/api/related/\${encodeURIComponent(movie.title)}\`);
      if (res.ok) {
        const data = await res.json();
        const miniGrid = document.getElementById(gridId);
        if (miniGrid) {
          if (data.movies && data.movies.length > 0) {
            miniGrid.innerHTML = data.movies.map(m => \`
              <div class="mini-card" onclick="alert('Navigating to \${m.title.replace(/'/g, "\\\\'")}')">
                <img src="\${m.poster || 'https://via.placeholder.com/150x225?text=No+Poster'}" alt="\${m.title}" />
                <div class="mini-card-title">\${m.title}</div>
              </div>
            \`).join('');
          } else {
            miniGrid.innerHTML = '<p style="color:var(--text-muted);">No similar movies found.</p>';
          }
        }
      }
    } catch(e) {
      console.error(e);
    }
  }


  // AI Search Logic
  searchForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const query = queryInput.value.trim();
    if(!query) return;

    loadingIndicator.classList.remove('hidden');
    aiSearchResults.classList.add('hidden');
    
    try {
      const res = await fetch('/api/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: query })
      });
      
      const data = await res.json();
      loadingIndicator.classList.add('hidden');
      
      aiSearchTitle.textContent = \`AI Recommendations for: "\${query}"\`;
      aiSearchResults.classList.remove('hidden');

      if (data.movies && data.movies.length > 0) {
        renderRow(aiSearchGrid, data.movies);
      } else {
        aiSearchGrid.innerHTML = \`<p style="color:var(--text-muted); padding: 1rem;">No specific movies found for this query.</p>\`;
      }

    } catch (error) {
      console.error(error);
      loadingIndicator.classList.add('hidden');
    }
  });

});
