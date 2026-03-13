// Show loading spinner on form submit
document.addEventListener('DOMContentLoaded', function() {
    const searchForm = document.getElementById('searchForm');
    const loadingSpinner = document.getElementById('loadingSpinner');
    
    if (searchForm && loadingSpinner) {
        searchForm.addEventListener('submit', function() {
            loadingSpinner.style.display = 'flex';
        });
    }
    
    // Initialize favorites
    updateFavoriteButtons();
    updateFavoriteCount();
});

// Quick search function for tags
function searchIngredient(ingredient) {
    const input = document.getElementById('ingredientInput');
    if (input) {
        input.value = ingredient;
        document.getElementById('searchForm').submit();
    } else {
        // If on results page, redirect to home with search
        window.location.href = '/?search=' + encodeURIComponent(ingredient);
    }
}

// Favorites System using localStorage
function getFavorites() {
    const favorites = localStorage.getItem('favorites');
    return favorites ? JSON.parse(favorites) : {};
}

function saveFavorites(favorites) {
    localStorage.setItem('favorites', JSON.stringify(favorites));
}

function toggleFavorite(recipeId, recipeName, recipeImage) {
    const favorites = getFavorites();
    
    if (favorites[recipeId]) {
        // Remove from favorites
        delete favorites[recipeId];
        showNotification('Removed from favorites!', 'remove');
    } else {
        // Add to favorites
        favorites[recipeId] = {
            name: recipeName,
            image: recipeImage
        };
        showNotification('Added to favorites!', 'add');
    }
    
    saveFavorites(favorites);
    updateFavoriteButtons();
    updateFavoriteCount();
}

function updateFavoriteButtons() {
    const favorites = getFavorites();
    
    // Update all heart buttons
    document.querySelectorAll('.heart').forEach(heart => {
        const recipeId = heart.id.replace('heart-', '');
        if (favorites[recipeId]) {
            heart.textContent = '❤';
            heart.classList.add('favorited');
        } else {
            heart.textContent = '♡';
            heart.classList.remove('favorited');
        }
    });
}

function updateFavoriteCount() {
    const favorites = getFavorites();
    const count = Object.keys(favorites).length;
    const countElements = document.querySelectorAll('#favCount');
    countElements.forEach(el => {
        el.textContent = count;
    });
}

function showFavorites() {
    const favorites = getFavorites();
    const modal = document.getElementById('favoritesModal');
    const favoritesList = document.getElementById('favoritesList');
    
    if (Object.keys(favorites).length === 0) {
        favoritesList.innerHTML = '<p class="no-favorites">No favorites yet! Start adding recipes you love.</p>';
    } else {
        let html = '';
        for (const [id, recipe] of Object.entries(favorites)) {
            html += `
                <div class="recipe-card">
                    <button class="favorite-btn" onclick="toggleFavorite('${id}', '${recipe.name}', '${recipe.image}')" aria-label="Remove from favorites">
                        <span class="heart favorited" id="heart-${id}">❤</span>
                    </button>
                    <img src="${recipe.image}" alt="${recipe.name}" loading="lazy">
                    <h3>${recipe.name}</h3>
                    <a href="/recipe/${id}" class="btn-view">View Recipe</a>
                </div>
            `;
        }
        favoritesList.innerHTML = html;
    }
    
    modal.style.display = 'block';
}

function closeFavorites() {
    const modal = document.getElementById('favoritesModal');
    modal.style.display = 'none';
}

// Close modal when clicking outside
window.onclick = function(event) {
    const modal = document.getElementById('favoritesModal');
    if (event.target == modal) {
        modal.style.display = 'none';
    }
}

// Notification system
function showNotification(message, type) {
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.classList.add('show');
    }, 10);
    
    setTimeout(() => {
        notification.classList.remove('show');
        setTimeout(() => {
            notification.remove();
        }, 300);
    }, 2000);
}

// Dark Mode Toggle
function toggleTheme() {
    const body = document.body;
    const themeIcon = document.querySelector('.theme-icon');
    
    body.classList.toggle('dark-mode');
    
    if (body.classList.contains('dark-mode')) {
        themeIcon.textContent = '☀️';
        localStorage.setItem('theme', 'dark');
    } else {
        themeIcon.textContent = '🌙';
        localStorage.setItem('theme', 'light');
    }
}

// Load saved theme on page load
function loadTheme() {
    const savedTheme = localStorage.getItem('theme');
    const themeIcon = document.querySelector('.theme-icon');
    
    if (savedTheme === 'dark') {
        document.body.classList.add('dark-mode');
        if (themeIcon) themeIcon.textContent = '☀️';
    }
}

// Print Recipe
function printRecipe() {
    window.print();
}

// Share Recipe
function shareRecipe(recipeName, recipeId) {
    const url = window.location.origin + '/recipe/' + recipeId;
    const text = `Check out this amazing recipe: ${recipeName}`;
    
    // Check if Web Share API is available
    if (navigator.share) {
        navigator.share({
            title: recipeName,
            text: text,
            url: url
        }).catch(err => console.log('Error sharing:', err));
    } else {
        // Fallback: Show custom share modal
        showShareModal(recipeName, url, text);
    }
}

function showShareModal(recipeName, url, text) {
    // Create modal if it doesn't exist
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
                       target="_blank" class="share-btn share-btn-twitter">
                        <span class="share-btn-icon">🐦</span>
                        Share on Twitter
                    </a>
                    <a href="https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(url)}" 
                       target="_blank" class="share-btn share-btn-facebook">
                        <span class="share-btn-icon">📘</span>
                        Share on Facebook
                    </a>
                    <a href="https://wa.me/?text=${encodeURIComponent(text + ' ' + url)}" 
                       target="_blank" class="share-btn share-btn-whatsapp">
                        <span class="share-btn-icon">💬</span>
                        Share on WhatsApp
                    </a>
                    <button onclick="copyToClipboard('${url}')" class="share-btn share-btn-copy">
                        <span class="share-btn-icon">📋</span>
                        Copy Link
                    </button>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
    }
    modal.style.display = 'block';
}

function closeShareModal() {
    const modal = document.getElementById('shareModal');
    if (modal) modal.style.display = 'none';
}

function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        showNotification('Link copied to clipboard!', 'add');
        closeShareModal();
    }).catch(err => {
        console.error('Failed to copy:', err);
    });
}

// Close share modal when clicking outside
window.addEventListener('click', function(event) {
    const modal = document.getElementById('shareModal');
    if (event.target == modal) {
        closeShareModal();
    }
});

// Initialize theme on page load
document.addEventListener('DOMContentLoaded', function() {
    loadTheme();
});

console.log('Recipe Finder loaded!');
