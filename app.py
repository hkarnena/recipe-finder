from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import requests
import re
import os
import json
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

SPOONACULAR_KEY = os.environ.get("SPOONACULAR_KEY", "c5baffb0f2ea46e68121aa602f8f7d27")

def parse_instructions(text):
    if not text:
        return []
    lines = [l.strip() for l in text.splitlines()]
    lines = [l for l in lines if l]
    steps = []
    for line in lines:
        if re.fullmatch(r"(step\s*)?\d+", line.strip(), re.IGNORECASE):
            continue
        if len(line) < 200:
            cleaned = re.sub(r"^(step\s*)?\d+[\.\):\-]\s*", "", line, flags=re.IGNORECASE).strip()
            if cleaned and len(cleaned) > 4:
                steps.append(cleaned)
        else:
            for s in re.split(r"(?<=[.!?])\s+", line):
                s = re.sub(r"^(step\s*)?\d+[\.\):\-]\s*", "", s.strip(), flags=re.IGNORECASE).strip()
                if s and len(s) > 10:
                    steps.append(s)
    seen, unique = set(), []
    for s in steps:
        if s not in seen:
            seen.add(s)
            unique.append(s)
    return unique

templates.env.filters["parse_instructions"] = parse_instructions

def get_fallback_image(title):
    words = [w for w in re.sub(r"[^a-z ]", "", title.lower()).split() if len(w) > 3][:2]
    query = "+".join(words) if words else "food"
    return f"https://source.unsplash.com/400x300/?{query},food"

def check_image_ok(url):
    if not url:
        return False
    try:
        r = requests.head(url, timeout=4, allow_redirects=True)
        return r.status_code == 200 and "image" in r.headers.get("content-type", "")
    except Exception:
        return False

def scrape_instructions(url):
    if not url:
        return ""
    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; RecipeFinder/1.0)"}
        r = requests.get(url, timeout=8, headers=headers)
        if r.status_code != 200:
            return ""
        ld_blocks = re.findall(r"<script[^>]+type=[\"']application/ld\+json[\"'][^>]*>(.*?)</script>", r.text, re.DOTALL)
        for block in ld_blocks:
            try:
                data = json.loads(block.strip())
                if isinstance(data, dict) and "@graph" in data:
                    data = next((x for x in data["@graph"] if "recipeInstructions" in x), {})
                inst = data.get("recipeInstructions", [])
                if isinstance(inst, list):
                    steps = [(item.get("text", "") if isinstance(item, dict) else str(item)).strip() for item in inst]
                    result = "\n".join(s for s in steps if s)
                    if result:
                        return result
                elif isinstance(inst, str) and len(inst) > 20:
                    return inst
            except Exception:
                continue
    except Exception:
        pass
    return ""

def spoonacular_search(query, number=20, cuisine=""):
    if not SPOONACULAR_KEY:
        return []
    try:
        params = {"query": query, "number": number, "apiKey": SPOONACULAR_KEY}
        if cuisine:
            params["cuisine"] = cuisine
        r = requests.get("https://api.spoonacular.com/recipes/complexSearch", params=params, timeout=10)
        return [{"idMeal": f"sp_{item['id']}", "strMeal": item["title"], "strMealThumb": item.get("image", "").replace("http://", "https://")} for item in r.json().get("results", [])]
    except Exception:
        return []

def spoonacular_by_ingredient(ingredient, number=20):
    if not SPOONACULAR_KEY:
        return []
    try:
        r = requests.get("https://api.spoonacular.com/recipes/findByIngredients", params={"ingredients": ingredient, "number": number, "apiKey": SPOONACULAR_KEY}, timeout=10)
        return [{"idMeal": f"sp_{item['id']}", "strMeal": item["title"], "strMealThumb": item.get("image", "").replace("http://", "https://")} for item in (r.json() or [])]
    except Exception:
        return []

def spoonacular_detail(spoon_id):
    if not SPOONACULAR_KEY:
        return None
    try:
        r = requests.get(f"https://api.spoonacular.com/recipes/{spoon_id}/information", params={"apiKey": SPOONACULAR_KEY, "includeNutrition": "false"}, timeout=10)
        d = r.json()
        image = d.get("image", "")
        if image:
            image = image.replace("http://", "https://")
            image = re.sub(r"-\d+x\d+\.", "-312x231.", image)
        if not check_image_ok(image):
            image = get_fallback_image(d.get("title", "food"))
        instructions = ""
        source_link = ""
        analyzed = d.get("analyzedInstructions", [])
        if analyzed:
            steps = []
            for section in analyzed:
                for step in section.get("steps", []):
                    steps.append(step.get("step", "").strip())
            instructions = "\n".join(s for s in steps if s)
        source_url = d.get("sourceUrl", "")
        if not instructions and source_url:
            instructions = scrape_instructions(source_url)
        if not instructions:
            raw = d.get("instructions") or ""
            href_match = re.search(r"href=[\"']([^\"']+)[\"']", raw)
            if href_match:
                source_link = href_match.group(1).replace("http://", "https://")
            else:
                clean = re.sub(r"<[^>]+>", " ", raw).strip()
                if len(clean) > 30 and not re.match(r"^(find|see|view|get|click|instructions?\s)", clean, re.IGNORECASE):
                    instructions = clean
        if not source_link and not instructions:
            source_link = source_url
        dish_types = d.get("dishTypes", [])
        category = dish_types[0].title() if dish_types else "Recipe"
        cuisines = d.get("cuisines", [])
        area = cuisines[0] if cuisines else "International"
        recipe = {"idMeal": f"sp_{d['id']}", "strMeal": d.get("title", "").title(), "strMealThumb": image, "strCategory": category, "strArea": area, "strInstructions": instructions, "strYoutube": "", "strSource": source_link or source_url, "_external_instructions": source_link}
        ingredients = d.get("extendedIngredients", [])
        for i, ing in enumerate(ingredients[:20], start=1):
            name = ing.get("name", "").strip()
            original = ing.get("original", "")
            measure = original.replace(name, "").strip(" ,")
            recipe[f"strIngredient{i}"] = name
            recipe[f"strMeasure{i}"] = measure
        for i in range(len(ingredients) + 1, 21):
            recipe[f"strIngredient{i}"] = ""
            recipe[f"strMeasure{i}"] = ""
        return recipe
    except Exception:
        return None

def spoonacular_nutrition(spoon_id):
    if not SPOONACULAR_KEY:
        return None
    try:
        r = requests.get(f"https://api.spoonacular.com/recipes/{spoon_id}/nutritionWidget.json", params={"apiKey": SPOONACULAR_KEY}, timeout=10)
        d = r.json()
        def val(name):
            for n in d.get("nutrients", []):
                if n.get("name", "").lower() == name.lower():
                    return f"{round(n.get('amount', 0))}{n.get('unit','')}"
            return "N/A"
        return {"calories": val("Calories"), "protein": val("Protein"), "carbs": val("Carbohydrates"), "fat": val("Fat"), "fiber": val("Fiber")}
    except Exception:
        return None

def spoonacular_similar(spoon_id, number=4):
    if not SPOONACULAR_KEY:
        return []
    try:
        r = requests.get(f"https://api.spoonacular.com/recipes/{spoon_id}/similar", params={"apiKey": SPOONACULAR_KEY, "number": number}, timeout=10)
        return [{"idMeal": f"sp_{item['id']}", "strMeal": item["title"], "strMealThumb": f"https://img.spoonacular.com/recipes/{item['id']}-312x231.jpg"} for item in (r.json() or [])]
    except Exception:
        return []

def merge_unique(base, extra):
    seen = {r["idMeal"] for r in base}
    for r in extra:
        if r["idMeal"] not in seen:
            base.append(r)
            seen.add(r["idMeal"])
    return base

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/search", response_class=HTMLResponse)
def search(request: Request, ingredient: str = Form(...)):
    recipes = []
    seen_ids = set()
    def add(meals):
        for m in (meals or []):
            if m["idMeal"] not in seen_ids:
                recipes.append(m)
                seen_ids.add(m["idMeal"])
    try:
        add(requests.get(f"https://www.themealdb.com/api/json/v1/1/filter.php?i={ingredient}", timeout=10).json().get("meals"))
    except Exception:
        pass
    try:
        add(requests.get(f"https://www.themealdb.com/api/json/v1/1/search.php?s={ingredient}", timeout=10).json().get("meals"))
    except Exception:
        pass
    if not recipes and " " in ingredient:
        try:
            add(requests.get(f"https://www.themealdb.com/api/json/v1/1/filter.php?i={ingredient.split()[0]}", timeout=10).json().get("meals"))
        except Exception:
            pass
    add(spoonacular_by_ingredient(ingredient, number=20))
    add(spoonacular_search(ingredient, number=20))
    return templates.TemplateResponse("results.html", {"request": request, "recipes": recipes, "ingredient": ingredient})

@app.post("/fridge", response_class=HTMLResponse)
def fridge_search(request: Request, ingredients: str = Form(...)):
    recipes = []
    seen_ids = set()
    def add(meals):
        for m in (meals or []):
            if m["idMeal"] not in seen_ids:
                recipes.append(m)
                seen_ids.add(m["idMeal"])
    add(spoonacular_by_ingredient(ingredients, number=24))
    for ing in [i.strip() for i in ingredients.split(",")][:3]:
        try:
            add(requests.get(f"https://www.themealdb.com/api/json/v1/1/filter.php?i={ing}", timeout=10).json().get("meals"))
        except Exception:
            pass
    return templates.TemplateResponse("results.html", {"request": request, "recipes": recipes, "ingredient": ingredients, "is_fridge": True})

@app.get("/cuisine/{cuisine_name}", response_class=HTMLResponse)
def browse_cuisine(request: Request, cuisine_name: str):
    recipes = []
    try:
        recipes = requests.get(f"https://www.themealdb.com/api/json/v1/1/filter.php?a={cuisine_name}", timeout=10).json().get("meals", []) or []
    except Exception:
        pass
    if len(recipes) < 5:
        try:
            fb = requests.get(f"https://www.themealdb.com/api/json/v1/1/search.php?s={cuisine_name}", timeout=10).json().get("meals", []) or []
            recipes = merge_unique(recipes, fb)
        except Exception:
            pass
    cuisine_map = {"italian": "Italian", "japanese": "Japanese", "mexican": "Mexican", "indian": "Indian", "french": "French", "chinese": "Chinese", "greek": "Greek", "american": "American", "thai": "Thai", "british": "British", "moroccan": "African", "turkish": "Middle Eastern"}
    spoon_cuisine = cuisine_map.get(cuisine_name.lower(), "")
    recipes = merge_unique(recipes, spoonacular_search(cuisine_name, number=20, cuisine=spoon_cuisine))
    if spoon_cuisine == "Indian":
        for term in ["curry", "biryani", "masala", "dal", "paneer", "tandoori"]:
            recipes = merge_unique(recipes, spoonacular_search(term, number=10, cuisine="Indian"))
    return templates.TemplateResponse("results.html", {"request": request, "recipes": recipes, "ingredient": cuisine_name, "is_cuisine": True})

@app.get("/category/{category_name}", response_class=HTMLResponse)
def browse_category(request: Request, category_name: str):
    if category_name.lower() in ("non-veg", "nonveg", "non veg"):
        recipes = []
        seen_ids = set()
        for cat in ["Chicken", "Beef", "Seafood", "Lamb", "Pork"]:
            try:
                for m in (requests.get(f"https://www.themealdb.com/api/json/v1/1/filter.php?c={cat}", timeout=10).json().get("meals") or []):
                    if m["idMeal"] not in seen_ids:
                        recipes.append(m)
                        seen_ids.add(m["idMeal"])
            except Exception:
                pass
        recipes = merge_unique(recipes, spoonacular_search("meat chicken beef", number=20))
        return templates.TemplateResponse("results.html", {"request": request, "recipes": recipes, "ingredient": "Non-Veg"})
    recipes = []
    try:
        recipes = requests.get(f"https://www.themealdb.com/api/json/v1/1/filter.php?c={category_name}", timeout=10).json().get("meals", []) or []
    except Exception:
        pass
    recipes = merge_unique(recipes, spoonacular_search(category_name, number=15))
    return templates.TemplateResponse("results.html", {"request": request, "recipes": recipes, "ingredient": category_name})

@app.get("/recipe/{recipe_id}", response_class=HTMLResponse)
def recipe_detail(request: Request, recipe_id: str):
    if recipe_id.startswith("sp_"):
        spoon_id = int(recipe_id[3:])
        recipe = spoonacular_detail(spoon_id)
        nutrition = spoonacular_nutrition(spoon_id)
        similar = spoonacular_similar(spoon_id)
        return templates.TemplateResponse("recipe.html", {"request": request, "recipe": recipe, "nutrition": nutrition, "similar": similar})
    try:
        recipe = requests.get(f"https://www.themealdb.com/api/json/v1/1/lookup.php?i={recipe_id}", timeout=10).json().get("meals", [None])[0]
    except Exception:
        recipe = None
    return templates.TemplateResponse("recipe.html", {"request": request, "recipe": recipe, "nutrition": None, "similar": []})

@app.get("/random", response_class=HTMLResponse)
def random_recipe(request: Request):
    try:
        recipe = requests.get("https://www.themealdb.com/api/json/v1/1/random.php", timeout=10).json().get("meals", [None])[0]
        if recipe:
            return templates.TemplateResponse("recipe.html", {"request": request, "recipe": recipe, "nutrition": None, "similar": []})
    except Exception:
        pass
    return templates.TemplateResponse("recipe.html", {"request": request, "recipe": None, "nutrition": None, "similar": []})

@app.get("/planner", response_class=HTMLResponse)
def meal_planner(request: Request):
    return templates.TemplateResponse("planner.html", {"request": request})
