# Recipe Finder 🍳

A simple web application to search for recipes by ingredient using TheMealDB API.

## Features

- Search recipes by ingredient
- View recipe details with ingredients and instructions
- Responsive design
- Clean and modern UI

## Installation

1. Clone the repository:
```bash
git clone <your-repo-url>
cd recipe_finder
```

2. Create a virtual environment:
```bash
python -m venv venv
```

3. Activate the virtual environment:
- Windows: `venv\Scripts\activate`
- Linux/Mac: `source venv/bin/activate`

4. Install dependencies:
```bash
pip install -r requirements.txt
```

## Running the Application

```bash
uvicorn app:app --reload
```

Then open your browser and go to: `http://localhost:8000`

## Technologies Used

- FastAPI - Web framework
- Jinja2 - Template engine
- TheMealDB API - Recipe data
- HTML/CSS - Frontend

## API Used

This project uses [TheMealDB](https://www.themealdb.com/api.php) - a free recipe API.
