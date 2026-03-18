from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import requests
import re
import os
from dotenv import load_dotenv

load_dotenv()  # loads .env locally; on Render it reads from environment variables

app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Load Spoonacular API key — hardcoded fallback for local dev safety
SPOONACULAR_KEY = os.environ.get("SPOONACULAR_KEY", "c5baffb0f2ea46e68121aa602f8f7d27")

# ── Instruction parser ────────────────────────────────────────────────────────

def parse_instructions(text: str) -> list[str]:
    if not text:
        return []
    lines = [l.strip() for l in text.splitlines()]
    lines = [l for l in lines if l]
    steps = []
    for line in lines:
        if re.fullmatch(r'(step\s*)?\d+', line.strip(), re.IGNORECASE):
            continue
        if len(line) < 200:
            cleaned = re.sub(r'^(step\s*)?\d+[\.\):\-]\s*', '', line, flags=re.IGNORECASE).strip()
            if cleaned and len(cleaned) > 4:
                steps.append(cleaned)
        else:
            for s in re.split(r'(?<=[.!?])\s+', line):
                s = re.sub(r'^(step\s*)?\d+[\.\):\-]\s*', '', s.strip(), flags=re.IGNORECASE).strip()
                if s and len(s) > 10:
                    steps.append(s)
    seen, unique = set(), []
    for s in steps:
        if s not in seen:
            seen.add(s)
            unique.append(s)
    return unique

templates.env.filters["parse_instructions"] = parse_instructions

# ── Spoonacular helpers ───────────────────────────────────────────────────────

def spoonacular_search(query: str, number: int = 20, cuisine: str = "") -> list[dict]:
    """Search Spoonacular and return results normalised to MealDB card shape."""
    if not SPOONACULAR_KEY:
        return []
    try:
        params = {"query": query, "number": number, "apiKey": SPOONACULAR_KEY}
        if cuisine:
            params["cuisine"] = cuisine
        r = requests.get(
            "https://api.spoonacular.com/recipes/complexSearch",
            params=params,
            timeout=10
        )
        results = r.json().get("results", [])
        return [
            {
                "idMeal": f"sp_{item['id']}",
                "strMeal": item["title"],
                "strMealThumb": item.get("image", "").replace("http://", "https://"),
                "_source": "spoonacular",
            }
            for item in results
        ]
    except Exception:
        return []


def spoonacular_by_ingredient(ingredient: str, number: int = 20) -> list[dict]:
    """Find recipes by ingredient via Spoonacular."""
    if not SPOONACULAR_KEY:
        return []
    try:
        r = requests.get(
            "https://api.spoonacular.com/recipes/findByIngredients",
            params={"ingredients": ingredient, "number": number, "apiKey": SPOONACULAR_KEY},
            timeout=10
        )
        return [
            {
                "idMeal": f"sp_{item['id']}",
                "strMeal": item["title"],
                "strMealThumb": item.get("image", "").replace("http://", "https://"),
                "_source": "spoonacular",
                "_spoon_id": item["id"],
            }
            for item in (r.json() or [])
        ]
    except Exception:
        return []


def spoonacular_detail(spoon_id: int) -> dict | None:
    """Fetch full recipe detail from Spoonacular and normalise to MealDB shape."""
    if not SPOONACULAR_KEY:
        return None
    try:
        r = requests.get(
            f"https://api.spoonacular.com/recipes/{spoon_id}/information",
            params={"apiKey": SPOONACULAR_KEY, "includeNutrition": "false"},
            timeout=10
        )
        d = r.json()

        # Image — use 312x231 thumbnail (more reliable than 556x370)
        image = d.get("image", "")
        if image:
            # Normalise to https and use the smaller reliable size
            image = image.replace("http://", "https://")
            image = re.sub(r'-\d+x\d+\.', '-312x231.', image)

        # Instructions — prefer analyzed steps (clean text, no HTML)
        instructions = ""
        source_link = ""  # link to external site if no instructions
        analyzed = d.get("analyzedInstructions", [])
        if analyzed:
            steps = []
            for section in analyzed:
                for step in section.get("steps", []):
                    steps.append(step.get("step", "").strip())
            instructions = "\n".join(s for s in steps if s)

        # Fallback: extract URL from HTML instructions and use as source link
        if not instructions:
            raw = d.get("instructions") or ""
            # Try to pull href from anchor tag
            href_match = re.search(r'href=["\']([^"\']+)["\']', raw)
            if href_match:
                source_link = href_match.group(1).replace("http://", "https://")
            else:
                # Strip HTML and check if there's real text
                clean = re.sub(r'<[^>]+>', ' ', raw).strip()
                if len(clean) > 30 and not clean.lower().startswith("instruction"):
                    instructions = clean

        # Use sourceUrl as fallback link if we still have nothing
        if not source_link and not instructions:
            source_link = d.get("sourceUrl", "")

        # Category and cuisine
        dish_types = d.get("dishTypes", [])
        category = dish_types[0].title() if dish_types else "Recipe"
        cuisines = d.get("cuisines", [])
        area = cuisines[0] if cuisines else "International"

        recipe = {
            "idMeal": f"sp_{d['id']}",
            "strMeal": d.get("title", "").title(),
            "strMealThumb": image,
            "strCategory": category,
            "strArea": area,
            "strInstructions": instructions,
            "strYoutube": "",
            "strSource": source_link or d.get("sourceUrl", ""),
            "_external_instructions": source_link,  # signals template to show link button
        }

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


def merge_unique(base: list, extra: list) -> list:
    """Merge two recipe lists, deduplicating by idMeal."""
    seen = {r["idMeal"] for r in base}
    for r in extra:
        if r["idMeal"] not in seen:
            base.append(r)
            seen.add(r["idMeal"])
    return base

# ── Routes ────────────────────────────────────────────────────────────────────

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

    # MealDB: ingredient filter
    try:
        r1 = requests.get(f"https://www.themealdb.com/api/json/v1/1/filter.php?i={ingredient}", timeout=10)
        add(r1.json().get("meals"))
    except Exception:
        pass

    # MealDB: name search
    try:
        r2 = requests.get(f"https://www.themealdb.com/api/json/v1/1/search.php?s={ingredient}", timeout=10)
        add(r2.json().get("meals"))
    except Exception:
        pass

    # MealDB: first-word fallback
    if not recipes and " " in ingredient:
        try:
            r3 = requests.get(f"https://www.themealdb.com/api/json/v1/1/filter.php?i={ingredient.split()[0]}", timeout=10)
            add(r3.json().get("meals"))
        except Exception:
            pass

    # Spoonacular: by ingredient + by name search
    add(spoonacular_by_ingredient(ingredient, number=20))
    add(spoonacular_search(ingredient, number=20))

    return templates.TemplateResponse("results.html", {
        "request": request, "recipes": recipes, "ingredient": ingredient
    })


@app.get("/cuisine/{cuisine_name}", response_class=HTMLResponse)
def browse_cuisine(request: Request, cuisine_name: str):
    recipes = []
    try:
        r = requests.get(f"https://www.themealdb.com/api/json/v1/1/filter.php?a={cuisine_name}", timeout=10)
        recipes = r.json().get("meals", []) or []
    except Exception:
        pass

    if len(recipes) < 5:
        try:
            fb = requests.get(f"https://www.themealdb.com/api/json/v1/1/search.php?s={cuisine_name}", timeout=10).json().get("meals", []) or []
            recipes = merge_unique(recipes, fb)
        except Exception:
            pass

    # Boost with Spoonacular cuisine search
    # For known cuisines, also pass cuisine filter for better results
    cuisine_map = {
        "italian": "Italian", "japanese": "Japanese", "mexican": "Mexican",
        "indian": "Indian", "french": "French", "chinese": "Chinese",
        "greek": "Greek", "american": "American", "thai": "Thai",
        "british": "British", "moroccan": "African", "turkish": "Middle Eastern"
    }
    spoon_cuisine = cuisine_map.get(cuisine_name.lower(), "")
    recipes = merge_unique(recipes, spoonacular_search(cuisine_name, number=20, cuisine=spoon_cuisine))
    # Extra pass for Indian to get more dishes
    if spoon_cuisine == "Indian":
        for term in ["curry", "biryani", "masala", "dal", "paneer", "tandoori"]:
            recipes = merge_unique(recipes, spoonacular_search(term, number=10, cuisine="Indian"))

    return templates.TemplateResponse("results.html", {
        "request": request, "recipes": recipes,
        "ingredient": cuisine_name, "is_cuisine": True
    })


@app.get("/category/{category_name}", response_class=HTMLResponse)
def browse_category(request: Request, category_name: str):
    if category_name.lower() in ("non-veg", "nonveg", "non veg"):
        recipes = []
        seen_ids = set()
        for cat in ["Chicken", "Beef", "Seafood", "Lamb", "Pork"]:
            try:
                r = requests.get(f"https://www.themealdb.com/api/json/v1/1/filter.php?c={cat}", timeout=10)
                for m in (r.json().get("meals") or []):
                    if m["idMeal"] not in seen_ids:
                        recipes.append(m)
                        seen_ids.add(m["idMeal"])
            except Exception:
                pass
        recipes = merge_unique(recipes, spoonacular_search("meat chicken beef", number=20))
        return templates.TemplateResponse("results.html", {
            "request": request, "recipes": recipes, "ingredient": "Non-Veg"
        })

    recipes = []
    try:
        r = requests.get(f"https://www.themealdb.com/api/json/v1/1/filter.php?c={category_name}", timeout=10)
        recipes = r.json().get("meals", []) or []
    except Exception:
        pass

    # Boost with Spoonacular
    recipes = merge_unique(recipes, spoonacular_search(category_name, number=15))

    return templates.TemplateResponse("results.html", {
        "request": request, "recipes": recipes, "ingredient": category_name
    })


@app.get("/recipe/{recipe_id}", response_class=HTMLResponse)
def recipe_detail(request: Request, recipe_id: str):
    # Spoonacular recipe (id starts with "sp_")
    if recipe_id.startswith("sp_"):
        spoon_id = int(recipe_id[3:])
        recipe = spoonacular_detail(spoon_id)
        return templates.TemplateResponse("recipe.html", {"request": request, "recipe": recipe})

    # MealDB recipe
    try:
        r = requests.get(f"https://www.themealdb.com/api/json/v1/1/lookup.php?i={recipe_id}", timeout=10)
        recipe = r.json().get("meals", [None])[0]
    except Exception:
        recipe = None
    return templates.TemplateResponse("recipe.html", {"request": request, "recipe": recipe})


@app.get("/random", response_class=HTMLResponse)
def random_recipe(request: Request):
    try:
        r = requests.get("https://www.themealdb.com/api/json/v1/1/random.php", timeout=10)
        recipe = r.json().get("meals", [None])[0]
        if recipe:
            return templates.TemplateResponse("recipe.html", {"request": request, "recipe": recipe})
    except Exception:
        pass
    return templates.TemplateResponse("recipe.html", {"request": request, "recipe": None})
