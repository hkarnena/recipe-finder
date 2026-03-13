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

console.log('Recipe Finder loaded!');
