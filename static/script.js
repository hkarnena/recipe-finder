// Show loading spinner on form submit
document.addEventListener('DOMContentLoaded', function() {
    const searchForm = document.getElementById('searchForm');
    const loadingSpinner = document.getElementById('loadingSpinner');
    
    if (searchForm && loadingSpinner) {
        searchForm.addEventListener('submit', function() {
            loadingSpinner.style.display = 'flex';
        });
    }
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

console.log('Recipe Finder loaded!');
