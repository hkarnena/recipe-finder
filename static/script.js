// ── Page transition ───────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    document.body.classList.add('page-loaded');
});
document.addEventListener('click', e => {
    const a = e.target.closest('a');
    if (a && a.href && !a.href.startsWith('#') && !a.target && a.origin === location.origin) {
        e.preventDefault();
        document.body.classList.remove('page-loaded');
        setTimeout(() => { location.href = a.href; }, 220);
    }
});

// ── Cuisine filter ────────────────────────────────────────────────────────────
function filterCuisines(query) {
    const q = query.toLowerCase();
    document.querySelectorAll('#cuisineGrid .cuisine-card').forEach(card => {
        const name = card.querySelector('.cuisine-name').textContent.toLowerCase();
        card.style.display = name.includes(q) ? '' : 'none';
    });
}

// ── Loading spinner ───────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('searchForm');
    const spinner = document.getElementById('loadingSpinner');
    if (form && spinner) {
        form.addEventListener('submit', () => { spinner.style.display = 'flex'; });
    }
    updateFavoriteButtons();
    updateFavoriteCount();
});

// ── Search helpers ────────────────────────────────────────────────────────────
function searchIngredient(ingredient) {
    const input = document.getElementById('ingredientInput');
    if (input) {
        input.value = ingredient;
        document.getElementById('searchForm').submit();
    } else {
        window.location.href = '/?search=' + encodeURIComponent(ingredient);
    }
}

function setFridge(ingredients) {
    const input = document.getElementById('fridgeInput');
    if (input) input.value = ingredients;
}

// ── Favorites ─────────────────────────────────────────────────────────────────
function getFavorites() {
    return JSON.parse(localStorage.getItem('favorites') || '{}');
}
function saveFavorites(f) {
    localStorage.setItem('favorites', JSON.stringify(f));
}

function toggleFavorite(recipeId, recipeName, recipeImage) {
    const favs = getFavorites();
    if (favs[recipeId]) {
        delete favs[recipeId];
        showNotification('Removed from favorites!', 'remove');
    } else {
        favs[recipeId] = { name: recipeName, image: recipeImage };
        showNotification('Added to favorites!', 'add');
    }
    saveFavorites(favs);
    updateFavoriteButtons();
    updateFavoriteCount();
}

function updateFavoriteButtons() {
    const favs = getFavorites();
    document.querySelectorAll('.heart').forEach(heart => {
        const id = heart.id.replace('heart-', '');
        heart.textContent = favs[id] ? '❤' : '♡';
        heart.classList.toggle('favorited', !!favs[id]);
    });
}

function updateFavoriteCount() {
    const count = Object.keys(getFavorites()).length;
    document.querySelectorAll('#favCount').forEach(el => el.textContent = count);
}

function showFavorites() {
    const favs = getFavorites();
    const list = document.getElementById('favoritesList');
    if (Object.keys(favs).length === 0) {
        list.innerHTML = '<p class="no-favorites">No favorites yet! Start adding recipes you love.</p>';
    } else {
        list.innerHTML = Object.entries(favs).map(([id, r]) => `
            <div class="recipe-card">
                <button class="favorite-btn" onclick="toggleFavorite('${id}','${r.name}','${r.image}')" aria-label="Remove">
                    <span class="heart favorited" id="heart-${id}">❤</span>
                </button>
                <img src="${r.image}" alt="${r.name}" loading="lazy">
                <div class="recipe-content">
                    <h3 class="recipe-title">${r.name}</h3>
                    <a href="/recipe/${id}" class="recipe-btn">View Recipe →</a>
                </div>
            </div>
        `).join('');
    }
    document.getElementById('favoritesModal').style.display = 'block';
}

function closeFavorites() {
    document.getElementById('favoritesModal').style.display = 'none';
}

window.onclick = e => {
    const m = document.getElementById('favoritesModal');
    if (e.target === m) m.style.display = 'none';
};

// ── Rating & Notes ────────────────────────────────────────────────────────────
function getRatings() {
    return JSON.parse(localStorage.getItem('recipeRatings') || '{}');
}

function setRating(recipeId, value) {
    const ratings = getRatings();
    ratings[recipeId] = { ...ratings[recipeId], stars: value };
    localStorage.setItem('recipeRatings', JSON.stringify(ratings));
    renderStars(recipeId, value);
    showNotification(`Rated ${value} star${value > 1 ? 's' : ''}!`, 'add');
}

function saveNote(recipeId, text) {
    const ratings = getRatings();
    ratings[recipeId] = { ...ratings[recipeId], note: text };
    localStorage.setItem('recipeRatings', JSON.stringify(ratings));
}

function renderStars(recipeId, value) {
    const stars = document.querySelectorAll('#starRating .star');
    stars.forEach((s, i) => {
        s.classList.toggle('active', i < value);
    });
    const label = document.getElementById('ratingLabel');
    if (label) label.textContent = value ? `${value} / 5` : 'Tap to rate';
}

function loadRatingAndNote(recipeId) {
    if (!recipeId) return;
    const data = getRatings()[recipeId];
    if (!data) return;
    if (data.stars) renderStars(recipeId, data.stars);
    if (data.note) {
        const ta = document.getElementById('recipeNote');
        if (ta) ta.value = data.note;
    }
}

// ── Meal Planner ──────────────────────────────────────────────────────────────
function addToMealPlan(id, name, image) {
    // Show a quick day/meal picker modal
    let modal = document.getElementById('plannerPickModal');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'plannerPickModal';
        modal.className = 'share-modal';
        document.body.appendChild(modal);
    }
    const days = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday'];
    const meals = ['Breakfast','Lunch','Dinner'];
    modal.innerHTML = `
        <div class="share-modal-content">
            <span class="close" onclick="document.getElementById('plannerPickModal').style.display='none'">&times;</span>
            <h3>📅 Add to Meal Plan</h3>
            <p style="color:var(--text-muted);font-size:0.9rem;margin-bottom:1rem;">Choose a day and meal slot</p>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:0.5rem;">
                ${days.map(d => meals.map(m => `
                    <button class="diet-btn" style="text-align:left;border-radius:8px;"
                        onclick="confirmAddToPlan('${id}','${name.replace(/'/g,"\\'")}','${image}','${d}','${m}')">
                        <strong>${d}</strong> · ${m}
                    </button>
                `).join('')).join('')}
            </div>
        </div>
    `;
    modal.style.display = 'block';
}

function confirmAddToPlan(id, name, image, day, meal) {
    const plan = JSON.parse(localStorage.getItem('mealPlan') || '{}');
    plan[`${day}_${meal}`] = { id, name, image };
    localStorage.setItem('mealPlan', JSON.stringify(plan));
    document.getElementById('plannerPickModal').style.display = 'none';
    showNotification(`Added to ${day} ${meal}!`, 'add');
}

// ── Notification ──────────────────────────────────────────────────────────────
function showNotification(message, type) {
    const n = document.createElement('div');
    n.className = `notification ${type}`;
    n.textContent = message;
    document.body.appendChild(n);
    setTimeout(() => n.classList.add('show'), 10);
    setTimeout(() => {
        n.classList.remove('show');
        setTimeout(() => n.remove(), 300);
    }, 2200);
}

// ── Dark Mode ─────────────────────────────────────────────────────────────────
function toggleTheme() {
    document.body.classList.toggle('dark-mode');
    const icon = document.querySelector('.theme-icon');
    const isDark = document.body.classList.contains('dark-mode');
    if (icon) icon.textContent = isDark ? '☀️' : '🌙';
    localStorage.setItem('theme', isDark ? 'dark' : 'light');
}

function loadTheme() {
    if (localStorage.getItem('theme') === 'dark') {
        document.body.classList.add('dark-mode');
        const icon = document.querySelector('.theme-icon');
        if (icon) icon.textContent = '☀️';
    }
}

// ── Print ─────────────────────────────────────────────────────────────────────
function printRecipe() { window.print(); }

// ── Share ─────────────────────────────────────────────────────────────────────
function shareRecipe(recipeName, recipeId) {
    const url = `${location.origin}/recipe/${recipeId}`;
    const text = `Check out this recipe: ${recipeName}`;
    if (navigator.share) {
        navigator.share({ title: recipeName, text, url }).catch(() => {});
    } else {
        showShareModal(recipeName, url, text);
    }
}

function showShareModal(recipeName, url, text) {
    let modal = document.getElementById('shareModal');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'shareModal';
        modal.className = 'share-modal';
        modal.innerHTML = `
            <div class="share-modal-content">
                <span class="close" onclick="closeShareModal()">&times;</span>
                <h3>Share Recipe</h3>
                <div class="share-buttons">
                    <a href="https://twitter.com/intent/tweet?text=${encodeURIComponent(text)}&url=${encodeURIComponent(url)}"
                       target="_blank" class="share-btn share-btn-twitter">🐦 Share on Twitter</a>
                    <a href="https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(url)}"
                       target="_blank" class="share-btn share-btn-facebook">📘 Share on Facebook</a>
                    <a href="https://wa.me/?text=${encodeURIComponent(text+' '+url)}"
                       target="_blank" class="share-btn share-btn-whatsapp">💬 Share on WhatsApp</a>
                    <button onclick="copyToClipboard('${url}')" class="share-btn share-btn-copy">📋 Copy Link</button>
                </div>
            </div>`;
        document.body.appendChild(modal);
    }
    modal.style.display = 'block';
}

function closeShareModal() {
    const m = document.getElementById('shareModal');
    if (m) m.style.display = 'none';
}

function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        showNotification('Link copied!', 'add');
        closeShareModal();
    });
}

window.addEventListener('click', e => {
    const sm = document.getElementById('shareModal');
    if (e.target === sm) closeShareModal();
    const pm = document.getElementById('plannerPickModal');
    if (e.target === pm) pm.style.display = 'none';
});

document.addEventListener('DOMContentLoaded', () => { loadTheme(); });
