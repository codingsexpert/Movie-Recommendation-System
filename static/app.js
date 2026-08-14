// ═══════════════════════════════════════════════════════════════════════
// MovieGraph AI — Netflix-Style Cinematic Platform Engine v3.0
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
  const spotlightBg       = document.getElementById('spotlightBg');
  const spotlightTitle    = document.getElementById('spotlightTitle');
  const spotlightYear     = document.getElementById('spotlightYear');
  const spotlightDirector = document.getElementById('spotlightDirector');
  const spotlightDesc     = document.getElementById('spotlightDesc');
  const spotlightRating   = document.getElementById('spotlightRating');

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

  function setSpotlight(movie) {
    currentSpotlight = movie;
    const content = document.querySelector('.spotlight-content');
    if (content) { content.style.opacity = '0'; content.style.transform = 'translateY(12px)'; }

    setTimeout(() => {
      if (spotlightBg && movie.backdrop)  spotlightBg.style.backgroundImage = `url('${movie.backdrop}')`;
      if (spotlightTitle)    spotlightTitle.textContent    = movie.title || '';
      if (spotlightYear)     spotlightYear.textContent     = movie.year || '';
      if (spotlightDirector) spotlightDirector.textContent = movie.directors ? movie.directors[0] : '';
      if (spotlightRating)   spotlightRating.textContent   = movie.rating ? `⭐ ${movie.rating}` : '';
      if (spotlightDesc) {
        const actors = (movie.actors || []).slice(0, 3).join(', ');
        const genres = (movie.genres || []).join(' · ');
        spotlightDesc.textContent = `${genres} — Starring ${actors}`;
      }
      if (content) {
        setTimeout(() => {
          content.style.transition = 'opacity 0.45s ease, transform 0.45s ease';
          content.style.opacity = '1';
          content.style.transform = 'translateY(0)';
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
      const ratingText = movie.rating ? `⭐ ${movie.rating}` : '';
      const hasOscar = movie.awards && movie.awards.some(a => a.toLowerCase().includes('oscar'));
      const genresText = (movie.genres || []).slice(0, 3).join(' · ');
      const yearText = movie.year || '';

      card.innerHTML = `
        <div class="poster-wrap">
          <img src="${posterUrl}" alt="${movie.title}" loading="lazy" />
          <div class="poster-gradient"></div>

          ${ratingText ? `<div class="poster-rating">${ratingText}</div>` : ''}
          ${hasOscar ? '<div class="poster-oscar">🏆</div>' : ''}

          <div class="poster-info">
            <h3 class="poster-movie-title">${movie.title}</h3>
            <div class="poster-meta">${yearText}${genresText ? ' · ' + genresText : ''}</div>
            <div class="poster-actions">
              <button class="poster-btn poster-btn-primary" data-action="recommend" data-title="${movie.title}">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
                Similar
              </button>
              <button class="poster-btn poster-btn-red" data-action="trailer" data-title="${movie.title}">
                ▶ Trailer
              </button>
              <button class="poster-btn poster-btn-ghost" data-action="graph" data-title="${movie.title}">
                Graph
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
    loadingIndicator.classList.remove('hidden');
    searchBtn.disabled = true;
    const s = searchBtn.querySelector('span');
    if (s) s.textContent = 'Searching...';
    loadingIndicator.scrollIntoView({ behavior: 'smooth', block: 'center' });

    try {
      const response = await fetch('/api/query', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ query }) });
      if (!response.ok) throw new Error('API failed');
      const data = await response.json();
      loadingIndicator.classList.add('hidden');
      resultsSection.classList.remove('hidden');
      answerContent.innerHTML = window.marked ? marked.parse(data.answer) : data.answer;
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
      const nodes = new vis.DataSet(gd.nodes.map(n => ({ id:n.id, label:n.label, group:n.group||'Movie', shape:'dot', size:n.group==='Movie'?26:17, borderWidth:2, color:cm[n.group]||cm.Movie, font:{color:dk?'#f1f5f9':'#0f172a',size:12,face:'Inter',bold:true,strokeWidth:3,strokeColor:dk?'#0b0f1a':'#ffffff'}, shadow:{enabled:true,color:'rgba(0,0,0,0.15)',size:6,x:0,y:3} })));
      const edges = new vis.DataSet(gd.edges.map(e => ({ from:e.from, to:e.to, label:e.label, color:{color:dk?'rgba(148,163,184,0.2)':'rgba(100,116,139,0.2)',highlight:'#2563eb'}, width:1.5, smooth:{type:'continuous',roundness:0.2}, font:{size:9,align:'middle',color:dk?'rgba(203,213,225,0.6)':'#475569',strokeWidth:2,strokeColor:dk?'#0b0f1a':'#ffffff'}, arrows:{to:{enabled:true,scaleFactor:0.5}} })));
      visNetworkInstance = new vis.Network(document.getElementById('graphCanvas'), {nodes,edges}, { physics:{solver:'forceAtlas2Based',forceAtlas2Based:{gravitationalConstant:-45,centralGravity:0.008,springLength:130,springConstant:0.07,damping:0.4},stabilization:{iterations:180}}, interaction:{hover:true,zoomView:true,dragNodes:true} });
    } catch(e) { console.warn('Graph error:', e); }
  }

  // ─── Nav Links ───
  document.querySelectorAll('.nav-link').forEach(l => { l.addEventListener('click', () => { document.querySelectorAll('.nav-link').forEach(x => x.classList.remove('active')); l.classList.add('active'); }); });

});
