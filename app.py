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
    api_url = f"https://www.themealdb.com/api/json/v1/1/filter.php?i={ingredient}"
    try:
        response = requests.get(api_url, timeout=10)
        response.raise_for_status()
        recipes = response.json().get("meals", [])
    except Exception as e:
        recipes = []
    return templates.TemplateResponse("results.html", {"request": request, "recipes": recipes, "ingredient": ingredient})

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