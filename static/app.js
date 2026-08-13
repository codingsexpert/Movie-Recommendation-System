// MovieGraph AI - Commercial Streaming Platform Engine

document.addEventListener('DOMContentLoaded', () => {
  const searchForm = document.getElementById('searchForm');
  const queryInput = document.getElementById('queryInput');
  const searchBtn = document.getElementById('searchBtn');
  const micBtn = document.getElementById('micBtn');
  const promptChips = document.querySelectorAll('.prompt-chip');
  
  const loadingIndicator = document.getElementById('loadingIndicator');
  const resultsSection = document.getElementById('resultsSection');
  const answerContent = document.getElementById('answerContent');
  const graphSection = document.getElementById('graphSection');
  const copyBtn = document.getElementById('copyBtn');
  
  const zoomInBtn = document.getElementById('zoomInBtn');
  const zoomOutBtn = document.getElementById('zoomOutBtn');
  const resetFitBtn = document.getElementById('resetFitBtn');
  
  const themeToggleBtn = document.getElementById('themeToggleBtn');
  const movieGrid = document.getElementById('movieGrid');
  const filterTabs = document.querySelectorAll('.tab-btn');
  
  const spotlightRecommendBtn = document.getElementById('spotlightRecommendBtn');
  const spotlightGraphBtn = document.getElementById('spotlightGraphBtn');

  let allCatalogMovies = [];
  let visNetworkInstance = null;

  // Theme Toggle Logic
  let currentTheme = localStorage.getItem('theme') || 'dark';
  applyTheme(currentTheme);

  themeToggleBtn.addEventListener('click', () => {
    currentTheme = currentTheme === 'dark' ? 'light' : 'dark';
    localStorage.setItem('theme', currentTheme);
    applyTheme(currentTheme);
  });

  function applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    themeToggleBtn.innerText = theme === 'dark' ? 'Light Mode' : 'Dark Mode';
  }

  // Load Catalog Movies Grid
  loadMovieCatalog();

  async function loadMovieCatalog() {
    try {
      const res = await fetch('/api/catalog');
      if (!res.ok) return;
      allCatalogMovies = await res.json();
      renderMovieGrid(allCatalogMovies);
    } catch (err) {
      console.warn('Failed loading catalog:', err);
    }
  }

  function renderMovieGrid(movies) {
    movieGrid.innerHTML = '';
    if (!movies || movies.length === 0) {
      movieGrid.innerHTML = '<p style="color: var(--text-muted); font-size: 0.9rem;">No movies found in category.</p>';
      return;
    }

    movies.forEach(movie => {
      const card = document.createElement('div');
      card.className = 'movie-card';

      const hasOscar = movie.awards && movie.awards.some(a => a.toLowerCase().includes('oscar'));
      const awardLabel = hasOscar ? 'Oscar Winner' : (movie.awards && movie.awards[0] ? movie.awards[0] : '');

      const genresHtml = (movie.genres || []).map(g => `<span class="genre-pill">${g}</span>`).join('');
      const directorsText = movie.directors && movie.directors.length > 0 ? movie.directors.join(', ') : 'N/A';
      const actorsText = movie.actors && movie.actors.length > 0 ? movie.actors.slice(0, 3).join(', ') : 'N/A';

      card.innerHTML = `
        <div class="card-poster">
          <div class="poster-badge-row">
            <span class="year-badge">${movie.year || 'N/A'}</span>
            ${awardLabel ? `<span class="award-pill">🏆 ${awardLabel}</span>` : ''}
          </div>
          <h3 class="poster-title">${movie.title}</h3>
        </div>
        <div class="card-body">
          <div class="card-meta-line"><strong>Dir:</strong> ${directorsText}</div>
          <div class="card-meta-line"><strong>Cast:</strong> ${actorsText}</div>
          <div class="card-genres">${genresHtml}</div>
          <div class="card-actions">
            <button class="btn-card-recommend" data-title="${movie.title}">More Like This</button>
            <button class="btn-card-graph" data-title="${movie.title}">View Graph</button>
          </div>
        </div>
      `;

      // Event listeners on card buttons
      const recBtn = card.querySelector('.btn-card-recommend');
      const grpBtn = card.querySelector('.btn-card-graph');

      recBtn.addEventListener('click', () => {
        const q = `Recommend movies similar to ${movie.title}`;
        queryInput.value = q;
        executeSearch(q);
      });

      grpBtn.addEventListener('click', () => {
        renderGraphCanvas(movie.title);
        graphSection.scrollIntoView({ behavior: 'smooth' });
      });

      movieGrid.appendChild(card);
    });
  }

  // Filter Tabs Handler
  filterTabs.forEach(tab => {
    tab.addEventListener('click', () => {
      filterTabs.forEach(t => t.classList.remove('active'));
      tab.classList.add('active');

      const filter = tab.getAttribute('data-filter');
      if (filter === 'all') {
        renderMovieGrid(allCatalogMovies);
      } else if (filter === 'Oscar') {
        const filtered = allCatalogMovies.filter(m => m.awards && m.awards.some(a => a.toLowerCase().includes('oscar')));
        renderMovieGrid(filtered);
      } else {
        const filtered = allCatalogMovies.filter(m => m.genres && m.genres.some(g => g.toLowerCase() === filter.toLowerCase()));
        renderMovieGrid(filtered);
      }
    });
  });

  // Spotlight Banner Buttons
  if (spotlightRecommendBtn) {
    spotlightRecommendBtn.addEventListener('click', () => {
      const q = 'Recommend movies similar to Inception';
      queryInput.value = q;
      executeSearch(q);
    });
  }

  if (spotlightGraphBtn) {
    spotlightGraphBtn.addEventListener('click', () => {
      renderGraphCanvas('Inception');
      graphSection.scrollIntoView({ behavior: 'smooth' });
    });
  }

  // Voice Search
  if ('SpeechRecognition' in window || 'webkitSpeechRecognition' in window) {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const recognition = new SpeechRecognition();
    
    micBtn.addEventListener('click', () => {
      recognition.start();
    });

    recognition.onresult = (e) => {
      const text = e.results[0][0].transcript;
      queryInput.value = text;
      executeSearch(text);
    };
  } else {
    micBtn.style.display = 'none';
  }

  // Quick Prompts Chips
  promptChips.forEach(chip => {
    chip.addEventListener('click', () => {
      const q = chip.getAttribute('data-query');
      queryInput.value = q;
      executeSearch(q);
    });
  });

  // Search Form Submit
  searchForm.addEventListener('submit', (e) => {
    e.preventDefault();
    const queryText = queryInput.value.trim();
    if (queryText) {
      executeSearch(queryText);
    }
  });

  // Copy Answer Button
  copyBtn.addEventListener('click', () => {
    navigator.clipboard.writeText(answerContent.innerText).then(() => {
      copyBtn.innerText = 'Copied!';
      setTimeout(() => { copyBtn.innerText = 'Copy Output'; }, 2000);
    });
  });

  // Graph Zoom Controls
  if (zoomInBtn) {
    zoomInBtn.addEventListener('click', () => {
      if (visNetworkInstance) {
        const scale = visNetworkInstance.getScale();
        visNetworkInstance.moveTo({ scale: scale * 1.25 });
      }
    });
  }

  if (zoomOutBtn) {
    zoomOutBtn.addEventListener('click', () => {
      if (visNetworkInstance) {
        const scale = visNetworkInstance.getScale();
        visNetworkInstance.moveTo({ scale: scale * 0.8 });
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

  // Core Search Execution Function
  async function executeSearch(query) {
    resultsSection.classList.add('hidden');
    graphSection.classList.add('hidden');
    loadingIndicator.classList.remove('hidden');

    searchBtn.disabled = true;
    searchBtn.innerText = 'Searching...';

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

      resultsSection.scrollIntoView({ behavior: 'smooth' });
    } catch (err) {
      loadingIndicator.classList.add('hidden');
      resultsSection.classList.remove('hidden');
      answerContent.innerHTML = `<p style="color: #ef4444;">Error processing search: ${err.message}</p>`;
    } finally {
      searchBtn.disabled = false;
      searchBtn.innerText = 'Ask AI Engine';
    }
  }

  // Render 2D Vis.js Knowledge Subgraph Canvas
  async function renderGraphCanvas(entityName) {
    try {
      const res = await fetch(`/api/graph_subnetwork/${encodeURIComponent(entityName)}`);
      if (!res.ok) return;
      const graphData = await res.json();

      if (!graphData.nodes || graphData.nodes.length === 0) return;

      graphSection.classList.remove('hidden');

      const nodes = new vis.DataSet(graphData.nodes.map(n => {
        const group = n.group || 'Movie';
        let colorObj = { background: '#6366f1', border: '#4338ca' };

        if (group === 'Director') colorObj = { background: '#a855f7', border: '#7e22ce' };
        else if (group === 'Actor') colorObj = { background: '#ec4899', border: '#be185d' };
        else if (group === 'Genre') colorObj = { background: '#10b981', border: '#047857' };
        else if (group === 'Theme') colorObj = { background: '#06b6d4', border: '#0e7490' };
        else if (group === 'Award') colorObj = { background: '#f59e0b', border: '#b45309' };

        return {
          id: n.id,
          label: n.label,
          group: group,
          shape: 'dot',
          size: group === 'Movie' ? 24 : 18,
          borderWidth: 2,
          color: colorObj,
          font: {
            color: currentTheme === 'dark' ? '#f8fafc' : '#0f172a',
            size: 12,
            face: 'Inter',
            bold: true,
            strokeWidth: 3,
            strokeColor: currentTheme === 'dark' ? '#0b0f19' : '#ffffff'
          }
        };
      }));

      const edges = new vis.DataSet(graphData.edges.map(e => ({
        from: e.from,
        to: e.to,
        label: e.label,
        color: { color: currentTheme === 'dark' ? 'rgba(148, 163, 184, 0.4)' : 'rgba(100, 116, 139, 0.4)' },
        width: 1.5,
        smooth: { type: 'continuous', roundness: 0.2 },
        font: {
          size: 9,
          align: 'middle',
          color: currentTheme === 'dark' ? '#cbd5e1' : '#475569',
          strokeWidth: 2,
          strokeColor: currentTheme === 'dark' ? '#0b0f19' : '#ffffff'
        },
        arrows: { to: { enabled: true, scaleFactor: 0.6 } }
      })));

      const container = document.getElementById('graphCanvas');
      const data = { nodes, edges };
      const options = {
        physics: {
          solver: 'forceAtlas2Based',
          forceAtlas2Based: {
            gravitationalConstant: -40,
            centralGravity: 0.01,
            springLength: 120,
            springConstant: 0.08
          },
          stabilization: { iterations: 150 }
        },
        interaction: { hover: true, zoomView: true, dragNodes: true }
      };

      visNetworkInstance = new vis.Network(container, data, options);
    } catch (err) {
      console.warn('Graph rendering warning:', err);
    }
  }
});
