from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import requests

app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Home page
@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# Search recipes
@app.post("/search", response_class=HTMLResponse)
def search(request: Request, ingredient: str = Form(...)):
    recipes = []
    seen_ids = set()

    # Try ingredient search first
    try:
        r1 = requests.get(f"https://www.themealdb.com/api/json/v1/1/filter.php?i={ingredient}", timeout=10)
        for m in (r1.json().get("meals") or []):
            if m["idMeal"] not in seen_ids:
                recipes.append(m)
                seen_ids.add(m["idMeal"])
    except Exception:
        pass

    # Also search by meal name
    try:
        r2 = requests.get(f"https://www.themealdb.com/api/json/v1/1/search.php?s={ingredient}", timeout=10)
        for m in (r2.json().get("meals") or []):
            if m["idMeal"] not in seen_ids:
                recipes.append(m)
                seen_ids.add(m["idMeal"])
    except Exception:
        pass

    # If still empty, try first word only
    if not recipes and " " in ingredient:
        first_word = ingredient.split()[0]
        try:
            r3 = requests.get(f"https://www.themealdb.com/api/json/v1/1/filter.php?i={first_word}", timeout=10)
            for m in (r3.json().get("meals") or []):
                if m["idMeal"] not in seen_ids:
                    recipes.append(m)
                    seen_ids.add(m["idMeal"])
        except Exception:
            pass

    return templates.TemplateResponse("results.html", {
        "request": request,
        "recipes": recipes,
        "ingredient": ingredient
    })

# Browse by cuisine
@app.get("/cuisine/{cuisine_name}", response_class=HTMLResponse)
def browse_cuisine(request: Request, cuisine_name: str):
    # Fetch by area (cuisine)
    area_url = f"https://www.themealdb.com/api/json/v1/1/filter.php?a={cuisine_name}"
    try:
        response = requests.get(area_url, timeout=10)
        response.raise_for_status()
        recipes = response.json().get("meals", []) or []
    except Exception:
        recipes = []

    # If fewer than 5 results, also search by ingredient name as fallback
    if len(recipes) < 5:
        try:
            fallback_url = f"https://www.themealdb.com/api/json/v1/1/search.php?s={cuisine_name}"
            fb = requests.get(fallback_url, timeout=10).json().get("meals", []) or []
            # Merge without duplicates
            existing_ids = {r["idMeal"] for r in recipes}
            for meal in fb:
                if meal["idMeal"] not in existing_ids:
                    recipes.append(meal)
        except Exception:
            pass

    return templates.TemplateResponse("results.html", {
        "request": request,
        "recipes": recipes,
        "ingredient": cuisine_name,
        "is_cuisine": True
    })

# Browse by category
@app.get("/category/{category_name}", response_class=HTMLResponse)
def browse_category(request: Request, category_name: str):
    api_url = f"https://www.themealdb.com/api/json/v1/1/filter.php?c={category_name}"
    try:
        response = requests.get(api_url, timeout=10)
        response.raise_for_status()
        recipes = response.json().get("meals", [])
    except Exception as e:
        recipes = []
    return templates.TemplateResponse("results.html", {"request": request, "recipes": recipes, "ingredient": category_name})

# Recipe details
@app.get("/recipe/{recipe_id}", response_class=HTMLResponse)
def recipe_detail(request: Request, recipe_id: str):
    api_url = f"https://www.themealdb.com/api/json/v1/1/lookup.php?i={recipe_id}"
    try:
        response = requests.get(api_url, timeout=10)
        response.raise_for_status()
        data = response.json()
        recipe = data.get("meals", [None])[0]
    except Exception as e:
        recipe = None
    return templates.TemplateResponse("recipe.html", {"request": request, "recipe": recipe})

# Random recipe
@app.get("/random", response_class=HTMLResponse)
def random_recipe(request: Request):
    api_url = "https://www.themealdb.com/api/json/v1/1/random.php"
    try:
        response = requests.get(api_url, timeout=10)
        response.raise_for_status()
        data = response.json()
        recipe = data.get("meals", [None])[0]
        if recipe:
            recipe_id = recipe.get("idMeal")
            return templates.TemplateResponse("recipe.html", {"request": request, "recipe": recipe})
    except Exception as e:
        pass
    return templates.TemplateResponse("recipe.html", {"request": request, "recipe": None})