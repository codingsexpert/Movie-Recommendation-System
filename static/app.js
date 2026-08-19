// ═══════════════════════════════════════════════════════════════════════
// MovieGraph AI — Netflix-Style Cinematic Platform Engine v3.0
// ═══════════════════════════════════════════════════════════════════════

window.handleImageLoadError = function(img, title) {
  const wrap = img.parentNode;
  if (!wrap) return;
  img.remove();
  
  // Create beautiful fallback element
  const placeholder = document.createElement('div');
  placeholder.className = 'placeholder-poster-gradient';
  placeholder.style.width = '100%';
  placeholder.style.height = '100%';
  placeholder.style.background = 'linear-gradient(135deg, #1e293b, #0b0f1a)';
  placeholder.style.display = 'flex';
  placeholder.style.flexDirection = 'column';
  placeholder.style.alignItems = 'center';
  placeholder.style.justifyContent = 'center';
  placeholder.style.padding = '1.5rem';
  placeholder.style.textAlign = 'center';
  placeholder.style.border = '1px solid var(--border)';
  placeholder.innerHTML = `
    <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-bottom: 12px; filter: drop-shadow(0 2px 8px var(--accent-glow));"><rect x="2" y="2" width="20" height="20" rx="2.18" ry="2.18"></rect><path d="M7 2v20M17 2v20M2 12h20M2 7h5M2 17h5M17 17h5M17 7h5"></path></svg>
    <span style="font-family:'Outfit', sans-serif; font-size:1.05rem; font-weight:800; color:#ffffff; line-height:1.3; display:-webkit-box; -webkit-line-clamp:4; -webkit-box-orient:vertical; overflow:hidden; text-shadow:0 2px 4px rgba(0,0,0,0.5);">${title}</span>
  `;
  wrap.insertBefore(placeholder, wrap.firstChild);
};

document.addEventListener('DOMContentLoaded', () => {

  // ─── User Profile & Tracking ───
  let userId = localStorage.getItem('userId');
  if (!userId) {
    userId = 'user_' + Math.random().toString(36).substring(2, 15);
    localStorage.setItem('userId', userId);
  }
  
  window.trackEvent = async function(eventType, targetId, targetName) {
    try {
      await fetch('/api/track', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ userId, eventType, targetId, targetName })
      });
    } catch (e) {
      console.warn('Tracking failed:', e);
    }
  };

  // ─── DOM References ───
  const searchForm          = document.getElementById('searchForm');
  const queryInput          = document.getElementById('queryInput');
  const searchBtn           = document.getElementById('searchBtn');
  const micBtn              = document.getElementById('micBtn');
  const promptChips         = document.querySelectorAll('.prompt-chip');
  const suggestionsDropdown = document.getElementById('suggestionsDropdown');

  const loadingIndicator = document.getElementById('loadingIndicator');
  const resultsSection   = document.getElementById('resultsSection');
  const answerContent    = document.getElementById('answerContent');
  const graphSection     = document.getElementById('graphSection');
  const copyBtn          = document.getElementById('copyBtn');

  const zoomInBtn        = document.getElementById('zoomInBtn');
  const zoomOutBtn       = document.getElementById('zoomOutBtn');
  const resetFitBtn      = document.getElementById('resetFitBtn');

  const themeToggleBtn   = document.getElementById('themeToggleBtn');
  const movieGrid        = document.getElementById('movieGrid');
  const filterTabs       = document.querySelectorAll('.tab-btn');

  const spotlightRecommendBtn = document.getElementById('spotlightRecommendBtn');
  const spotlightGraphBtn     = document.getElementById('spotlightGraphBtn');
  const spotlightTrailerBtn   = document.getElementById('spotlightTrailerBtn');

  // Hero elements
  const spotlightBg       = document.getElementById('spotlightBg');
  const spotlightTitle    = document.getElementById('spotlightTitle');
  const spotlightYear     = document.getElementById('spotlightYear');
  const spotlightDirector = document.getElementById('spotlightDirector');
  const spotlightDesc     = document.getElementById('spotlightDesc');
  const spotlightRating   = document.getElementById('spotlightRating');

  // ─── Autocomplete suggestions logic ───
  let searchTimeout = null;
  queryInput.addEventListener('input', () => {
    if (searchTimeout) clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
      const val = queryInput.value;
    if (!val || val.length < 2) {
      suggestionsDropdown.classList.add('hidden');
      return;
    }

    const searchTerm = getAutocompleteSearchTerm(val);
    if (!searchTerm || searchTerm.length < 2) {
      suggestionsDropdown.classList.add('hidden');
      return;
    }

    // Filter movie titles in allCatalogMovies containing the search term
    const matches = allCatalogMovies.filter(m => 
      m.title.toLowerCase().includes(searchTerm.toLowerCase())
    );

    if (matches.length === 0) {
      suggestionsDropdown.classList.add('hidden');
      return;
    }

    // Render matches
    suggestionsDropdown.innerHTML = '';
    suggestionsDropdown.classList.remove('hidden');

    matches.slice(0, 6).forEach(movie => {
      const div = document.createElement('div');
      div.className = 'suggestion-item';
      div.innerHTML = `
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>
        <span>${movie.title}</span>
      `;
      div.addEventListener('click', () => {
        // Replace matching search term with the selected movie title
        const originalVal = queryInput.value;
        const lastIdx = originalVal.toLowerCase().lastIndexOf(searchTerm.toLowerCase());
        
        if (lastIdx !== -1) {
          queryInput.value = originalVal.substring(0, lastIdx) + movie.title + originalVal.substring(lastIdx + searchTerm.length);
        } else {
          queryInput.value = movie.title;
        }
        
        suggestionsDropdown.classList.add('hidden');
        queryInput.focus();
      });
      suggestionsDropdown.appendChild(div);
    });
    }, 200); // 200ms debounce
  });

  // Hide dropdown on click outside
  document.addEventListener('click', (e) => {
    if (!queryInput.contains(e.target) && !suggestionsDropdown.contains(e.target)) {
      suggestionsDropdown.classList.add('hidden');
    }
  });

  function getAutocompleteSearchTerm(inputText) {
    const text = inputText.toLowerCase();
    const keywords = ["similar to", "like", "about", "by", "explore", "jaisi", "jaisa"];
    for (const kw of keywords) {
      const idx = text.lastIndexOf(kw);
      if (idx !== -1) {
        return inputText.substring(idx + kw.length).trim();
      }
    }
    return inputText.trim();
  }

  let allCatalogMovies    = [];
  let visNetworkInstance  = null;
  let currentSpotlight    = null;
  let spotlightInterval   = null;

  // ─── Theme Toggle ───
  let currentTheme = localStorage.getItem('mg-theme') || 'light';
  applyTheme(currentTheme);

  themeToggleBtn.addEventListener('click', () => {
    currentTheme = currentTheme === 'dark' ? 'light' : 'dark';
    localStorage.setItem('mg-theme', currentTheme);
    applyTheme(currentTheme);
  });

  function applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    const label = themeToggleBtn.querySelector('span');
    if (label) label.textContent = theme === 'dark' ? 'Light' : 'Dark';
  }

  // ─── Load Stats ───
  loadStats();

  async function loadStats() {
    try {
      const res = await fetch('/api/stats');
      if (!res.ok) return;
      const stats = await res.json();
      const neo4jEl = document.getElementById('neo4jStatus');
      const pineEl  = document.getElementById('pineconeStatus');
      if (stats.neo4j) {
        const n = stats.neo4j.total_nodes || 0;
        neo4jEl.textContent = n > 0 ? `Neo4j · ${n}` : 'Neo4j';
        if (stats.neo4j.status && stats.neo4j.status.startsWith('error')) {
          const dot = neo4jEl.previousElementSibling;
          dot.style.background = '#ef4444';
          dot.style.boxShadow = '0 0 6px rgba(239,68,68,0.5)';
        }
      }
      if (stats.pinecone) {
        const v = stats.pinecone.total_vectors || 0;
        pineEl.textContent = v > 0 ? `Pinecone · ${v}` : 'Pinecone';
      }
    } catch(e) {}
  }

  // ─── Load Catalog ───
  loadMovieCatalog();

  async function loadMovieCatalog() {
    try {
      const res = await fetch('/api/catalog');
      if (!res.ok) return;
      allCatalogMovies = await res.json();
      renderMovieGrid(allCatalogMovies);
      setupSpotlightRotation(allCatalogMovies);
    } catch(err) {
      console.warn('Catalog load failed:', err);
    }
  }

  // ─── Spotlight Rotation ───
  function setupSpotlightRotation(movies) {
    if (!movies || movies.length === 0) return;
    let idx = 0;
    setSpotlight(movies[idx]);
    spotlightInterval = setInterval(() => {
      idx = (idx + 1) % movies.length;
      setSpotlight(movies[idx]);
    }, 7000);
  }

  const DEFAULT_CINEMA_BG = 'https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?auto=format&fit=crop&w=1600&q=80';

  function setSpotlight(movie) {
    if (window.trackEvent && movie.title) trackEvent('movie_click', 'movie', movie.title);
    currentSpotlight = movie;
    const info = document.getElementById('spotlightInfo');
    const posterImg = document.getElementById('spotlightPosterImg');
    const posterCard = document.getElementById('spotlightPosterCard');

    if (info) { info.style.opacity = '0'; info.style.transform = 'translateY(12px)'; }
    if (posterCard) { posterCard.style.opacity = '0'; posterCard.style.transform = 'translateY(12px)'; }

    setTimeout(() => {
      // 1. Update Floating Poster Card
      if (posterImg && movie.poster) {
        posterImg.src = movie.poster;
      }

      // 2. Preload & Set Hero Backdrop with multi-tier fallback
      const primaryBg = movie.backdrop || movie.poster || DEFAULT_CINEMA_BG;
      const bgTester = new Image();
      bgTester.onload = () => {
        if (spotlightBg) spotlightBg.style.backgroundImage = `url('${primaryBg}')`;
      };
      bgTester.onerror = () => {
        // Fallback to poster or Unsplash cinema backdrop if 404
        const fallbackBg = movie.poster || DEFAULT_CINEMA_BG;
        if (spotlightBg) spotlightBg.style.backgroundImage = `url('${fallbackBg}')`;
      };
      bgTester.src = primaryBg;

      if (spotlightTitle)    spotlightTitle.textContent    = movie.title || '';
      if (spotlightYear)     spotlightYear.textContent     = movie.year || '';
      if (spotlightDirector) spotlightDirector.textContent = movie.directors ? movie.directors[0] : '';
      if (spotlightRating) {
        if (movie.rating) {
          spotlightRating.innerHTML = `<svg class="icon-star" width="13" height="13" viewBox="0 0 24 24" fill="currentColor" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align: -2px; margin-right: 4px;"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon></svg>${movie.rating}`;
        } else {
          spotlightRating.innerHTML = '';
        }
      }
      if (spotlightDesc) {
        const actors = (movie.actors || []).slice(0, 3).join(', ');
        const genres = (movie.genres || []).join(' · ');
        spotlightDesc.textContent = `${genres} — Starring ${actors}`;
      }
      if (info) {
        setTimeout(() => {
          info.style.transition = 'opacity 0.45s ease, transform 0.45s ease';
          info.style.opacity = '1';
          info.style.transform = 'translateY(0)';
          if (posterCard) {
            posterCard.style.transition = 'opacity 0.45s ease, transform 0.45s ease';
            posterCard.style.opacity = '1';
            posterCard.style.transform = 'translateY(0)';
          }
        }, 50);
      }
    }, 250);
  }

  // ─── Trailer Modal ───
  const trailerModal      = document.getElementById('trailerModal');
  const trailerIframe     = document.getElementById('trailerIframe');
  const trailerModalTitle = document.getElementById('trailerModalTitle');
  const closeTrailerBtn   = document.getElementById('closeTrailerBtn');
  const trailerBackdrop   = document.getElementById('trailerBackdrop');

  function openTrailer(title, url) {
    if (!url) url = `https://www.youtube.com/embed?listType=search&list=${encodeURIComponent(title + ' official trailer')}`;
    trailerModalTitle.textContent = `${title} — Official Trailer`;
    trailerIframe.src = url.includes('autoplay') ? url : `${url}?autoplay=1`;
    trailerModal.classList.remove('hidden');
    document.body.style.overflow = 'hidden';
  }

  function closeTrailer() {
    trailerIframe.src = '';
    trailerModal.classList.add('hidden');
    document.body.style.overflow = '';
  }

  if (closeTrailerBtn) closeTrailerBtn.addEventListener('click', closeTrailer);
  if (trailerBackdrop) trailerBackdrop.addEventListener('click', closeTrailer);
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && !trailerModal.classList.contains('hidden')) closeTrailer(); });

  // ═══════════════════════════════════════════════════
  // Netflix-Style Pure Poster Card Renderer
  // ═══════════════════════════════════════════════════
  function renderMovieGrid(movies) {
    movieGrid.innerHTML = '';

    if (!movies || movies.length === 0) {
      movieGrid.innerHTML = '<p style="color:var(--text-tertiary); grid-column:1/-1; text-align:center; padding:3rem 0;">No movies found.</p>';
      return;
    }

    movies.forEach((movie) => {
      const card = document.createElement('div');
      card.className = 'movie-card';

      const posterUrl = movie.poster || 'https://image.tmdb.org/t/p/w500/d5iIlFn5s0ImszYzBPb8JPIfbXD.jpg';
      const ratingText = movie.rating ? `<svg class="icon-star" width="11" height="11" viewBox="0 0 24 24" fill="currentColor" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align: -1px; margin-right: 3px;"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon></svg>${movie.rating}` : '';
      const hasOscar = movie.awards && movie.awards.some(a => a.toLowerCase().includes('oscar'));
      const genresText = (movie.genres || []).slice(0, 3).join(' · ');
      const yearText = movie.year || '';

      card.innerHTML = `
        <div class="poster-wrap">
          <img src="${posterUrl}" alt="${movie.title}" loading="lazy" onload="this.classList.add('poster-loaded');" onerror="handleImageLoadError(this, '${movie.title.replace(/'/g, "\\'")}')" />
          <div class="poster-gradient"></div>

          ${ratingText ? `<div class="poster-rating">${ratingText}</div>` : ''}
          ${hasOscar ? `<div class="poster-oscar" title="Oscar Winner"><svg class="icon-trophy" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#d97706" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6"></path><path d="M18 9h1.5a2.5 2.5 0 0 0 0-5H18"></path><path d="M4 22h16"></path><path d="M10 14.66V17c0 .55-.45 1-1 1H4v2h16v-2h-5c-.55 0-1-.45-1-1v-2.34"></path><path d="M12 2a6 6 0 0 0-6 6v3.5c0 1.66 1.34 3 3 3h6c1.66 0 3-1.34 3-3V8a6 6 0 0 0-6-6z"></path></svg></div>` : ''}

          <div class="poster-info">
            <h3 class="poster-movie-title">${movie.title}</h3>
            <div class="poster-meta">${yearText}${genresText ? ' · ' + genresText : ''}</div>
            <div class="poster-actions">
              <button class="poster-btn poster-btn-primary poster-btn-cta" data-action="recommend" data-title="${movie.title}" title="Find Similar">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
                Similar
              </button>
              <button class="poster-btn poster-btn-red poster-btn-icon" data-action="trailer" data-title="${movie.title}" title="Watch Trailer">
                <svg viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>
              </button>
              <button class="poster-btn poster-btn-ghost poster-btn-icon" data-action="graph" data-title="${movie.title}" title="View Graph">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><circle cx="4" cy="6" r="2"/><circle cx="20" cy="6" r="2"/><circle cx="4" cy="18" r="2"/><circle cx="20" cy="18" r="2"/><line x1="6" y1="7" x2="10" y2="10"/><line x1="18" y1="7" x2="14" y2="10"/><line x1="6" y1="17" x2="10" y2="14"/><line x1="18" y1="17" x2="14" y2="14"/></svg>
              </button>
            </div>
          </div>
        </div>
      `;

      // Event delegation
      card.querySelector('[data-action="recommend"]').addEventListener('click', (e) => {
        e.stopPropagation();
        const q = `Recommend movies similar to ${movie.title}`;
        queryInput.value = q;
        executeSearch(q);
      });

      card.querySelector('[data-action="trailer"]').addEventListener('click', (e) => {
        e.stopPropagation();
        openTrailer(movie.title, movie.trailer);
      });

      card.querySelector('[data-action="graph"]').addEventListener('click', (e) => {
        e.stopPropagation();
        renderGraphCanvas(movie.title);
        graphSection.scrollIntoView({ behavior: 'smooth' });
      });

      movieGrid.appendChild(card);
    });
  }

  // ─── Filter Tabs ───
  filterTabs.forEach(tab => {
    tab.addEventListener('click', () => {
      filterTabs.forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      const filter = tab.getAttribute('data-filter');
      if (filter === 'all') {
        renderMovieGrid(allCatalogMovies);
      } else if (filter === 'Oscar') {
        renderMovieGrid(allCatalogMovies.filter(m => m.awards && m.awards.some(a => a.toLowerCase().includes('oscar'))));
      } else {
        renderMovieGrid(allCatalogMovies.filter(m => m.genres && m.genres.some(g => g.toLowerCase() === filter.toLowerCase())));
      }
    });
  });

  // ─── Spotlight Buttons ───
  if (spotlightRecommendBtn) {
    spotlightRecommendBtn.addEventListener('click', () => {
      const t = currentSpotlight ? currentSpotlight.title : 'Inception';
      if (window.trackEvent) trackEvent('similar_click', 'movie', t);
      queryInput.value = `Recommend movies similar to ${t}`;
      executeSearch(queryInput.value);
    });
  }
  if (spotlightTrailerBtn) {
    spotlightTrailerBtn.addEventListener('click', () => {
      if (currentSpotlight) openTrailer(currentSpotlight.title, currentSpotlight.trailer);
      else openTrailer('Inception', 'https://www.youtube.com/embed/YoHD9XEInc0');
    });
  }
  if (spotlightGraphBtn) {
    spotlightGraphBtn.addEventListener('click', () => {
      const t = currentSpotlight ? currentSpotlight.title : 'Inception';
      renderGraphCanvas(t);
      graphSection.scrollIntoView({ behavior: 'smooth' });
    });
  }

  // ─── Voice Search ───
  if ('SpeechRecognition' in window || 'webkitSpeechRecognition' in window) {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    const recognition = new SR();
    micBtn.addEventListener('click', () => { micBtn.style.color = 'var(--red)'; recognition.start(); });
    recognition.onresult = (e) => { const t = e.results[0][0].transcript; queryInput.value = t; micBtn.style.color = ''; executeSearch(t); };
    recognition.onend = () => { micBtn.style.color = ''; };
    recognition.onerror = () => { micBtn.style.color = ''; };
  } else { micBtn.style.display = 'none'; }

  // ─── Prompt Chips ───
  promptChips.forEach(c => { c.addEventListener('click', () => { queryInput.value = c.dataset.query; executeSearch(c.dataset.query); }); });

  // ─── Search Submit ───
  searchForm.addEventListener('submit', (e) => { e.preventDefault(); const q = queryInput.value.trim(); if (q) executeSearch(q); });

  // ─── Copy ───
  copyBtn.addEventListener('click', () => { navigator.clipboard.writeText(answerContent.innerText).then(() => { copyBtn.textContent = 'Copied ✓'; setTimeout(() => { copyBtn.textContent = 'Copy'; }, 2000); }); });

  // ─── Graph Zoom ───
  if (zoomInBtn)   zoomInBtn.addEventListener('click',  () => { if (visNetworkInstance) visNetworkInstance.moveTo({ scale: visNetworkInstance.getScale() * 1.3 }); });
  if (zoomOutBtn)  zoomOutBtn.addEventListener('click', () => { if (visNetworkInstance) visNetworkInstance.moveTo({ scale: visNetworkInstance.getScale() * 0.75 }); });
  if (resetFitBtn) resetFitBtn.addEventListener('click', () => { if (visNetworkInstance) visNetworkInstance.fit({ animation: { duration: 500, easingFunction: 'easeInOutQuad' } }); });

  // ─── Core Search ───
  async function executeSearch(query) {
    resultsSection.classList.add('hidden');
    graphSection.classList.add('hidden');
    const recGrid = document.getElementById('recommendedMoviesGrid');
    if (recGrid) recGrid.style.display = 'none';
    loadingIndicator.classList.remove('hidden');
    searchBtn.disabled = true;
    const s = searchBtn.querySelector('span');
    if (s) s.textContent = 'Searching...';
    loadingIndicator.scrollIntoView({ behavior: 'smooth', block: 'center' });

    try {
      if (window.trackEvent) trackEvent('search', 'query', query);
      const payload = { query: query };
      if (typeof userId !== 'undefined') payload.userId = userId;
      
      const response = await fetch('/api/query', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
      if (!response.ok) throw new Error('API failed');
      const data = await response.json();
      loadingIndicator.classList.add('hidden');
      resultsSection.classList.remove('hidden');
      const htmlContent = window.marked ? marked.parse(data.answer) : data.answer;
      const extractedTitles = extractMovieTitles(data.answer);
      
      if (extractedTitles.length > 0) {
        answerContent.style.display = 'none';
        const header = resultsSection.querySelector('.card-header');
        if (header) header.style.display = 'none';
        renderRecommendedMovies(extractedTitles);
      } else {
        answerContent.style.display = 'block';
        const header = resultsSection.querySelector('.card-header');
        if (header) header.style.display = 'flex';
        answerContent.innerHTML = htmlContent;
        renderRecommendedMovies(extractedTitles);
      }

      const entities = data.resolved ? data.resolved.entities || [] : [];
      if (entities.length > 0) renderGraphCanvas(entities[0].nodeName);
      resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
    } catch(err) {
      loadingIndicator.classList.add('hidden');
      resultsSection.classList.remove('hidden');
      answerContent.innerHTML = `<p style="color:var(--red);">Error: ${err.message}</p>`;
    } finally {
      searchBtn.disabled = false;
      const s = searchBtn.querySelector('span');
      if (s) s.textContent = 'Ask AI';
    }
  }

  // ─── HTML Typewriter Streamer (YouTube/ChatGPT Style) ───
  function typeHtml(element, html, speed = 8, callback = null) {
    // Write HTML instantly instead of slow typing effect to improve UX speed
    element.innerHTML = html;
    
    // Add simple fade-in effect
    element.style.opacity = '0';
    element.style.transform = 'translateY(10px)';
    element.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
    
    requestAnimationFrame(() => {
      element.style.opacity = '1';
      element.style.transform = 'translateY(0)';
    });
    
    if (callback) {
      setTimeout(callback, 50); // slight delay to allow DOM to paint
    }
  }

  // ─── Recommendation Cards Grid ───
  function extractMovieTitles(markdownText) {
    const titles = [];
    if (!markdownText) return titles;
    // Match patterns like "1. **Inception**" or "1. **The Matrix**:" or "- **RRR**"
    const regex = /(?:\d+\.|\*|-)\s+\*\*([^*]+)\*\*/g;
    let match;
    while ((match = regex.exec(markdownText)) !== null) {
      titles.push(match[1].trim());
    }
    return titles;
  }

  function renderRecommendedMovies(titles) {
    const recGrid = document.getElementById('recommendedMoviesGrid');
    if (!recGrid) return;
    recGrid.innerHTML = '';
    
    if (!titles || titles.length === 0) {
      recGrid.style.display = 'none';
      return;
    }
    
    recGrid.style.display = 'grid';
    
    // Find matching movies in allCatalogMovies (case-insensitive lookup)
    const matchedMovies = [];
    titles.forEach(title => {
      const movie = allCatalogMovies.find(m => m.title.toLowerCase().trim() === title.toLowerCase().trim());
      if (movie) {
        matchedMovies.push(movie);
      } else {
        // Fallback placeholder card if the movie is not in allCatalogMovies
        matchedMovies.push({
          title: title,
          year: '',
          rating: '',
          isPlaceholder: true,
          genres: ['Recommendation'],
          trailer: null
        });
      }
    });

    matchedMovies.forEach((movie) => {
      const card = document.createElement('div');
      card.className = 'movie-card';

      const ratingText = movie.rating ? `<svg class="icon-star" width="11" height="11" viewBox="0 0 24 24" fill="currentColor" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align: -1px; margin-right: 3px;"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon></svg>${movie.rating}` : '';
      const hasOscar = movie.awards && movie.awards.some(a => a.toLowerCase().includes('oscar'));
      const genresText = (movie.genres || []).slice(0, 3).join(' · ');
      const yearText = movie.year || '';

      let posterHtml = '';
      if (movie.isPlaceholder) {
        posterHtml = `
          <div class="placeholder-poster-gradient" style="width:100%; height:100%; background: linear-gradient(135deg, #1e293b, #0b0f1a); display:flex; flex-direction:column; align-items:center; justify-content:center; padding:1.5rem; text-align:center; border: 1px solid var(--border);">
            <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-bottom: 12px; filter: drop-shadow(0 2px 8px var(--accent-glow));"><rect x="2" y="2" width="20" height="20" rx="2.18" ry="2.18"></rect><path d="M7 2v20M17 2v20M2 12h20M2 7h5M2 17h5M17 17h5M17 7h5"></path></svg>
            <span style="font-family:'Outfit', sans-serif; font-size:1.05rem; font-weight:800; color:#ffffff; line-height:1.3; display:-webkit-box; -webkit-line-clamp:4; -webkit-box-orient:vertical; overflow:hidden; text-shadow:0 2px 4px rgba(0,0,0,0.5);">${movie.title}</span>
          </div>
        `;
      } else {
        const posterUrl = movie.poster || 'https://image.tmdb.org/t/p/w500/d5iIlFn5s0ImszYzBPb8JPIfbXD.jpg';
        const escapedTitle = movie.title.replace(/'/g, "\\'");
        posterHtml = `<img src="${posterUrl}" alt="${movie.title}" loading="lazy" onload="this.classList.add('poster-loaded');" onerror="handleImageLoadError(this, '${escapedTitle}')" />`;
      }

      card.innerHTML = `
        <div class="poster-wrap">
          ${posterHtml}
          <div class="poster-gradient"></div>

          ${ratingText ? `<div class="poster-rating">${ratingText}</div>` : ''}
          ${hasOscar ? `<div class="poster-oscar" title="Oscar Winner"><svg class="icon-trophy" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#d97706" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6"></path><path d="M18 9h1.5a2.5 2.5 0 0 0 0-5H18"></path><path d="M4 22h16"></path><path d="M10 14.66V17c0 .55-.45 1-1 1H4v2h16v-2h-5c-.55 0-1-.45-1-1v-2.34"></path><path d="M12 2a6 6 0 0 0-6 6v3.5c0 1.66 1.34 3 3 3h6c1.66 0 3-1.34 3-3V8a6 6 0 0 0-6-6z"></path></svg></div>` : ''}

          <div class="poster-info">
            <h3 class="poster-movie-title">${movie.title}</h3>
            <div class="poster-meta">${yearText}${yearText && genresText ? ' · ' : ''}${genresText}</div>
            <div class="poster-actions">
              <button class="poster-btn poster-btn-primary poster-btn-cta" data-action="recommend" data-title="${movie.title}" title="Find Similar">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
                Similar
              </button>
              ${movie.trailer ? `
              <button class="poster-btn poster-btn-red poster-btn-icon" data-action="trailer" data-title="${movie.title}" title="Watch Trailer">
                <svg viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>
              </button>
              ` : ''}
              <button class="poster-btn poster-btn-ghost poster-btn-icon" data-action="graph" data-title="${movie.title}" title="View Graph">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><circle cx="4" cy="6" r="2"/><circle cx="20" cy="6" r="2"/><circle cx="4" cy="18" r="2"/><circle cx="20" cy="18" r="2"/><line x1="6" y1="7" x2="10" y2="10"/><line x1="18" y1="7" x2="14" y2="10"/><line x1="6" y1="17" x2="10" y2="14"/><line x1="18" y1="17" x2="14" y2="14"/></svg>
              </button>
            </div>
          </div>
        </div>
      `;

      // Click Event Handlers
      card.querySelector('[data-action="recommend"]').addEventListener('click', (e) => {
        e.stopPropagation();
        const q = `Recommend movies similar to ${movie.title}`;
        queryInput.value = q;
        executeSearch(q);
      });

      if (movie.trailer) {
        card.querySelector('[data-action="trailer"]').addEventListener('click', (e) => {
          e.stopPropagation();
          openTrailer(movie.title, movie.trailer);
        });
      }

      card.querySelector('[data-action="graph"]').addEventListener('click', (e) => {
        e.stopPropagation();
        renderGraphCanvas(movie.title);
        graphSection.scrollIntoView({ behavior: 'smooth' });
      });

      recGrid.appendChild(card);
    });
  }

  // ─── Graph Renderer ───
  async function renderGraphCanvas(entityName) {
    try {
      const res = await fetch(`/api/graph_subnetwork/${encodeURIComponent(entityName)}`);
      if (!res.ok) return;
      const gd = await res.json();
      if (!gd.nodes || gd.nodes.length === 0) return;
      graphSection.classList.remove('hidden');
      const cm = { Movie: {background:'#2563eb',border:'#1d4ed8'}, Director: {background:'#7c3aed',border:'#5b21b6'}, Actor: {background:'#db2777',border:'#be185d'}, Genre: {background:'#059669',border:'#047857'}, Theme: {background:'#0891b2',border:'#0e7490'}, Award: {background:'#d97706',border:'#b45309'} };
      const dk = currentTheme === 'dark';
      const nodes = new vis.DataSet(gd.nodes.map(n => ({ id:n.id, label:n.label, group:n.group||'Movie', shape:'dot', size:n.group==='Movie'?26:17, borderWidth:2, color:cm[n.group]||cm.Movie, font:{color:dk?'#f1f5f9':'#0f172a',size:12,face:'Poppins',bold:true,strokeWidth:3,strokeColor:dk?'#0b0f1a':'#ffffff'}, shadow:{enabled:true,color:'rgba(0,0,0,0.15)',size:6,x:0,y:3} })));
      const edges = new vis.DataSet(gd.edges.map(e => ({ from:e.from, to:e.to, label:e.label, color:{color:dk?'rgba(148,163,184,0.2)':'rgba(100,116,139,0.2)',highlight:'#2563eb'}, width:1.5, smooth:{type:'continuous',roundness:0.2}, font:{size:9,align:'middle',color:dk?'rgba(203,213,225,0.6)':'#475569',strokeWidth:2,strokeColor:dk?'#0b0f1a':'#ffffff'}, arrows:{to:{enabled:true,scaleFactor:0.5}} })));
      visNetworkInstance = new vis.Network(document.getElementById('graphCanvas'), {nodes,edges}, { physics:{solver:'forceAtlas2Based',forceAtlas2Based:{gravitationalConstant:-45,centralGravity:0.008,springLength:130,springConstant:0.07,damping:0.4},stabilization:{iterations:180}}, interaction:{hover:true,zoomView:true,dragNodes:true} });
    } catch(e) { console.warn('Graph error:', e); }
  }

  // ─── Nav Links ───
  document.querySelectorAll('.nav-link').forEach(l => { l.addEventListener('click', () => { document.querySelectorAll('.nav-link').forEach(x => x.classList.remove('active')); l.classList.add('active'); }); });

  // Sync TMDB Button
  const syncTmdbBtn = document.getElementById('syncTmdbBtn');
  if (syncTmdbBtn) {
    syncTmdbBtn.addEventListener('click', async () => {
      syncTmdbBtn.innerHTML = '<span class="loading-spinner"></span> Syncing...';
      syncTmdbBtn.disabled = true;
      try {
        const res = await fetch('/api/sync_tmdb', { method: 'POST' });
        const data = await res.json();
        if (data.status === 'success') {
          alert('TMDB Sync started in the background! Trending movies are being added.');
        } else {
          alert('Failed to sync TMDB.');
        }
      } catch (err) {
        alert('Error triggering sync.');
      } finally {
        syncTmdbBtn.innerHTML = '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="vertical-align: -2px; margin-right: 4px;"><path d="M21.5 2v6h-6M2.13 15.57a9 9 0 1 0 3.32-8.3L2 9M2.5 22v-6h6M21.87 8.43a9 9 0 1 0-3.32 8.3L22 15"></path></svg> Sync Trending';
        syncTmdbBtn.disabled = false;
      }
    });
  }
});
