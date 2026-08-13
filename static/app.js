// ═══════════════════════════════════════════════════════════════════════
// MovieGraph AI — Premium Cinematic Platform Engine v2.0
// ═══════════════════════════════════════════════════════════════════════

document.addEventListener('DOMContentLoaded', () => {

  // ─── DOM References ───
  const searchForm       = document.getElementById('searchForm');
  const queryInput       = document.getElementById('queryInput');
  const searchBtn        = document.getElementById('searchBtn');
  const micBtn           = document.getElementById('micBtn');
  const promptChips      = document.querySelectorAll('.prompt-chip');

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
  const spotlightBg      = document.getElementById('spotlightBg');
  const spotlightTitle   = document.getElementById('spotlightTitle');
  const spotlightYear    = document.getElementById('spotlightYear');
  const spotlightDirector = document.getElementById('spotlightDirector');
  const spotlightDesc    = document.getElementById('spotlightDesc');
  const spotlightRating  = document.getElementById('spotlightRating');

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

  // ─── Load Database Stats (navbar badges) ───
  loadStats();

  async function loadStats() {
    try {
      const res = await fetch('/api/stats');
      if (!res.ok) return;
      const stats = await res.json();

      const neo4jEl = document.getElementById('neo4jStatus');
      const pineEl  = document.getElementById('pineconeStatus');

      if (stats.neo4j) {
        const nodeCount = stats.neo4j.total_nodes || 0;
        neo4jEl.textContent = nodeCount > 0 ? `Neo4j · ${nodeCount} nodes` : 'Neo4j';
        // Color the dot based on status
        const dot = neo4jEl.previousElementSibling;
        if (stats.neo4j.status && stats.neo4j.status.startsWith('error')) {
          dot.style.background = '#ef4444';
          dot.style.boxShadow = '0 0 6px rgba(239,68,68,0.5)';
        }
      }

      if (stats.pinecone) {
        const vecCount = stats.pinecone.total_vectors || 0;
        pineEl.textContent = vecCount > 0 ? `Pinecone · ${vecCount} vectors` : 'Pinecone';
      }
    } catch (e) {
      // Silently fail — badges stay with defaults
    }
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
    } catch (err) {
      console.warn('Catalog load failed:', err);
    }
  }

  // ─── Spotlight Rotation (auto-rotate hero every 8s) ───
  function setupSpotlightRotation(movies) {
    if (!movies || movies.length === 0) return;

    let idx = 0;
    setSpotlight(movies[idx]);

    spotlightInterval = setInterval(() => {
      idx = (idx + 1) % movies.length;
      setSpotlight(movies[idx]);
    }, 8000);
  }

  function setSpotlight(movie) {
    currentSpotlight = movie;

    // Fade transition
    const content = document.querySelector('.spotlight-content');
    if (content) {
      content.style.opacity = '0';
      content.style.transform = 'translateY(15px)';
    }

    setTimeout(() => {
      if (spotlightBg && movie.backdrop) {
        spotlightBg.style.backgroundImage = `url('${movie.backdrop}')`;
      }
      if (spotlightTitle)    spotlightTitle.textContent    = movie.title || 'Untitled';
      if (spotlightYear)     spotlightYear.textContent     = movie.year || '';
      if (spotlightDirector) spotlightDirector.textContent = movie.directors ? movie.directors[0] : '';
      if (spotlightRating)   spotlightRating.textContent   = movie.rating ? `⭐ ${movie.rating}` : '';

      if (spotlightDesc) {
        const themes = (movie.themes || []).join(', ');
        const actors = (movie.actors || []).slice(0, 3).join(', ');
        spotlightDesc.textContent = `Starring ${actors}. Themes: ${themes}.`;
      }

      // Animate back in
      if (content) {
        setTimeout(() => {
          content.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
          content.style.opacity = '1';
          content.style.transform = 'translateY(0)';
        }, 50);
      }
    }, 300);
  }

  // ─── Trailer Modal ───
  const trailerModal     = document.getElementById('trailerModal');
  const trailerIframe    = document.getElementById('trailerIframe');
  const trailerModalTitle = document.getElementById('trailerModalTitle');
  const closeTrailerBtn  = document.getElementById('closeTrailerBtn');
  const trailerBackdrop  = document.getElementById('trailerBackdrop');

  function openTrailer(title, url) {
    if (!url) {
      url = `https://www.youtube.com/embed?listType=search&list=${encodeURIComponent(title + ' official trailer')}`;
    }
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

  // ESC key closes trailer
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && !trailerModal.classList.contains('hidden')) {
      closeTrailer();
    }
  });

  // ─── Render Movie Grid ───
  function renderMovieGrid(movies) {
    movieGrid.innerHTML = '';

    if (!movies || movies.length === 0) {
      movieGrid.innerHTML = '<p style="color: var(--text-tertiary); font-size: 0.9rem; grid-column: 1 / -1; text-align: center; padding: 3rem 0;">No movies found in this category.</p>';
      return;
    }

    movies.forEach((movie, index) => {
      const card = document.createElement('div');
      card.className = 'movie-card';
      card.style.animationDelay = `${index * 0.06}s`;

      const hasOscar = movie.awards && movie.awards.some(a => a.toLowerCase().includes('oscar'));
      const awardLabel = hasOscar ? 'Oscar Winner' : (movie.awards && movie.awards[0] ? movie.awards[0] : '');

      const genresHtml = (movie.genres || []).map(g => `<span class="genre-pill">${g}</span>`).join('');
      const directorsText = movie.directors && movie.directors.length > 0 ? movie.directors.join(', ') : 'N/A';
      const actorsText = movie.actors && movie.actors.length > 0 ? movie.actors.slice(0, 3).join(', ') : 'N/A';
      const posterUrl = movie.poster || 'https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?auto=format&fit=crop&w=500&q=80';
      const ratingText = movie.rating ? `⭐ ${movie.rating}` : '';

      card.innerHTML = `
        <div class="card-poster">
          <img src="${posterUrl}" alt="${movie.title} poster" loading="lazy" />
          <div class="poster-overlay"></div>
          <div class="poster-play-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="#ffffff"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>
          </div>
          <div class="poster-badge-row">
            <span class="year-badge">${movie.year || ''}</span>
            <span class="rating-pill">${ratingText}</span>
            ${awardLabel ? `<span class="award-pill">🏆 ${awardLabel}</span>` : ''}
          </div>
          <div class="poster-content">
            <h3 class="poster-title">${movie.title}</h3>
          </div>
        </div>
        <div class="card-body">
          <div class="card-meta-line"><strong>Dir</strong> ${directorsText}</div>
          <div class="card-meta-line"><strong>Cast</strong> ${actorsText}</div>
          <div class="card-genres">${genresHtml}</div>
          <div class="card-actions">
            <button class="btn-card-recommend" data-title="${movie.title}">More Like This</button>
            <button class="btn-card-trailer" data-title="${movie.title}">▶ Trailer</button>
            <button class="btn-card-graph" data-title="${movie.title}">Graph</button>
          </div>
        </div>
      `;

      // Event listeners
      card.querySelector('.btn-card-recommend').addEventListener('click', () => {
        const q = `Recommend movies similar to ${movie.title}`;
        queryInput.value = q;
        executeSearch(q);
      });

      card.querySelector('.btn-card-trailer').addEventListener('click', () => {
        openTrailer(movie.title, movie.trailer);
      });

      card.querySelector('.btn-card-graph').addEventListener('click', () => {
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
      const title = currentSpotlight ? currentSpotlight.title : 'Inception';
      const q = `Recommend movies similar to ${title}`;
      queryInput.value = q;
      executeSearch(q);
    });
  }

  if (spotlightTrailerBtn) {
    spotlightTrailerBtn.addEventListener('click', () => {
      if (currentSpotlight) {
        openTrailer(currentSpotlight.title, currentSpotlight.trailer);
      } else {
        openTrailer('Inception', 'https://www.youtube.com/embed/YoHD9XEInc0');
      }
    });
  }

  if (spotlightGraphBtn) {
    spotlightGraphBtn.addEventListener('click', () => {
      const title = currentSpotlight ? currentSpotlight.title : 'Inception';
      renderGraphCanvas(title);
      graphSection.scrollIntoView({ behavior: 'smooth' });
    });
  }

  // ─── Voice Search ───
  if ('SpeechRecognition' in window || 'webkitSpeechRecognition' in window) {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const recognition = new SpeechRecognition();

    micBtn.addEventListener('click', () => {
      micBtn.style.color = 'var(--red)';
      recognition.start();
    });

    recognition.onresult = (e) => {
      const text = e.results[0][0].transcript;
      queryInput.value = text;
      micBtn.style.color = '';
      executeSearch(text);
    };

    recognition.onend = () => { micBtn.style.color = ''; };
    recognition.onerror = () => { micBtn.style.color = ''; };
  } else {
    micBtn.style.display = 'none';
  }

  // ─── Quick Prompt Chips ───
  promptChips.forEach(chip => {
    chip.addEventListener('click', () => {
      const q = chip.getAttribute('data-query');
      queryInput.value = q;
      executeSearch(q);
    });
  });

  // ─── Search Form Submit ───
  searchForm.addEventListener('submit', (e) => {
    e.preventDefault();
    const queryText = queryInput.value.trim();
    if (queryText) executeSearch(queryText);
  });

  // ─── Copy Button ───
  copyBtn.addEventListener('click', () => {
    navigator.clipboard.writeText(answerContent.innerText).then(() => {
      copyBtn.textContent = 'Copied ✓';
      setTimeout(() => { copyBtn.textContent = 'Copy'; }, 2000);
    });
  });

  // ─── Graph Zoom Controls ───
  if (zoomInBtn) {
    zoomInBtn.addEventListener('click', () => {
      if (visNetworkInstance) {
        visNetworkInstance.moveTo({ scale: visNetworkInstance.getScale() * 1.3 });
      }
    });
  }

  if (zoomOutBtn) {
    zoomOutBtn.addEventListener('click', () => {
      if (visNetworkInstance) {
        visNetworkInstance.moveTo({ scale: visNetworkInstance.getScale() * 0.75 });
      }
    });
  }

  if (resetFitBtn) {
    resetFitBtn.addEventListener('click', () => {
      if (visNetworkInstance) {
        visNetworkInstance.fit({ animation: { duration: 500, easingFunction: 'easeInOutQuad' } });
      }
    });
  }

  // ─── Core Search Execution ───
  async function executeSearch(query) {
    resultsSection.classList.add('hidden');
    graphSection.classList.add('hidden');
    loadingIndicator.classList.remove('hidden');

    searchBtn.disabled = true;
    const btnSpan = searchBtn.querySelector('span');
    if (btnSpan) btnSpan.textContent = 'Searching...';

    // Scroll to search area
    loadingIndicator.scrollIntoView({ behavior: 'smooth', block: 'center' });

    try {
      const response = await fetch('/api/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query })
      });

      if (!response.ok) throw new Error('API Query failed');

      const data = await response.json();

      loadingIndicator.classList.add('hidden');
      resultsSection.classList.remove('hidden');

      if (window.marked) {
        answerContent.innerHTML = marked.parse(data.answer);
      } else {
        answerContent.innerText = data.answer;
      }

      // Render Subgraph for resolved entity
      const entities = data.resolved ? data.resolved.entities || [] : [];
      if (entities.length > 0) {
        renderGraphCanvas(entities[0].nodeName);
      }

      resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
    } catch (err) {
      loadingIndicator.classList.add('hidden');
      resultsSection.classList.remove('hidden');
      answerContent.innerHTML = `<p style="color: var(--red);">Error: ${err.message}</p>`;
    } finally {
      searchBtn.disabled = false;
      const btnSpan = searchBtn.querySelector('span');
      if (btnSpan) btnSpan.textContent = 'Ask AI';
    }
  }

  // ─── Render 2D Vis.js Knowledge Subgraph ───
  async function renderGraphCanvas(entityName) {
    try {
      const res = await fetch(`/api/graph_subnetwork/${encodeURIComponent(entityName)}`);
      if (!res.ok) return;
      const graphData = await res.json();

      if (!graphData.nodes || graphData.nodes.length === 0) return;

      graphSection.classList.remove('hidden');

      const colorMap = {
        Movie:    { background: '#7c3aed', border: '#5b21b6' },
        Director: { background: '#a855f7', border: '#7e22ce' },
        Actor:    { background: '#ec4899', border: '#be185d' },
        Genre:    { background: '#10b981', border: '#047857' },
        Theme:    { background: '#06b6d4', border: '#0e7490' },
        Award:    { background: '#f59e0b', border: '#b45309' }
      };

      const isDark = currentTheme === 'dark';

      const nodes = new vis.DataSet(graphData.nodes.map(n => {
        const group = n.group || 'Movie';
        return {
          id: n.id,
          label: n.label,
          group: group,
          shape: 'dot',
          size: group === 'Movie' ? 26 : 18,
          borderWidth: 2,
          color: colorMap[group] || colorMap.Movie,
          font: {
            color: isDark ? '#f1f5f9' : '#0f172a',
            size: 12,
            face: 'Inter',
            bold: true,
            strokeWidth: 3,
            strokeColor: isDark ? '#06080f' : '#ffffff'
          },
          shadow: {
            enabled: true,
            color: 'rgba(0,0,0,0.2)',
            size: 8,
            x: 0,
            y: 4
          }
        };
      }));

      const edges = new vis.DataSet(graphData.edges.map(e => ({
        from: e.from,
        to: e.to,
        label: e.label,
        color: {
          color: isDark ? 'rgba(148,163,184,0.25)' : 'rgba(100,116,139,0.3)',
          highlight: '#7c3aed'
        },
        width: 1.5,
        smooth: { type: 'continuous', roundness: 0.2 },
        font: {
          size: 9,
          align: 'middle',
          color: isDark ? 'rgba(203,213,225,0.7)' : '#475569',
          strokeWidth: 2,
          strokeColor: isDark ? '#06080f' : '#ffffff'
        },
        arrows: { to: { enabled: true, scaleFactor: 0.55 } }
      })));

      const container = document.getElementById('graphCanvas');
      const data = { nodes, edges };
      const options = {
        physics: {
          solver: 'forceAtlas2Based',
          forceAtlas2Based: {
            gravitationalConstant: -45,
            centralGravity: 0.008,
            springLength: 130,
            springConstant: 0.07,
            damping: 0.4
          },
          stabilization: { iterations: 180 }
        },
        interaction: {
          hover: true,
          zoomView: true,
          dragNodes: true,
          tooltipDelay: 200
        }
      };

      visNetworkInstance = new vis.Network(container, data, options);
    } catch (err) {
      console.warn('Graph rendering error:', err);
    }
  }

  // ─── Smooth Nav Links (active state) ───
  const navLinks = document.querySelectorAll('.nav-link');
  navLinks.forEach(link => {
    link.addEventListener('click', () => {
      navLinks.forEach(l => l.classList.remove('active'));
      link.classList.add('active');
    });
  });

});
