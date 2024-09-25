import os
import requests
from fastapi import FastAPI, Form
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles  # Add this import
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
import openai
import wikipedia
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from .env file
load_dotenv()

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Mount the static files directory
app.mount("/static", StaticFiles(directory="static"), name="static")

# Set up OpenAI API key
openai.api_key = os.environ.get("OPENAI_API_KEY")

class CityInfo(BaseModel):
    landmarks: list[str]
    activities: list[str]
    restaurants: list[str]

@app.get("/")
async def index():
    file_path = Path("./templates/index.html")
    return FileResponse(file_path)

@app.post("/city-info")
async def get_city_info(city: str = Form(...)):
    city_info = await get_city_info_from_ai(city)
    gmap_api_key = os.getenv('GMAP_API_KEY')
    coordinates = get_gps_coordinates(city, gmap_api_key)
    return JSONResponse(content={
        "city": city,
        "landmarks": city_info.landmarks,
        "activities": city_info.activities,
        "restaurants": city_info.restaurants,
        "gmap_api_key": gmap_api_key,
        "coordinates": coordinates
    })


@app.get("/result", response_class=HTMLResponse)
async def result(request: Request):
    gmap_api_key = os.getenv('GMAP_API_KEY')
    return templates.TemplateResponse(
        "result.html",
        {"request": request, "gmap_api_key": gmap_api_key},
    )

async def get_city_info_from_ai(city: str) -> CityInfo:
    try:
        client = openai.AsyncOpenAI()
        completion = await client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Provide information about landmarks, activities, and restaurants in the given city."},
                {"role": "user", "content": f"Provide top 5 landmarks, 5 fun activities, and 5 top restaurants in {city}."},
            ],
            response_format=CityInfo,
        )
        
        city_info = completion.choices[0].message.parsed
        # Fetch Wikipedia images for landmarks
        landmarks_with_images = []
        for landmark in city_info.landmarks:
            landmark_info = {"name": landmark}
            try:
                page = wikipedia.page(landmark)
                landmark_info['image'] = page.images[0]  # Get the first image
            except Exception as e:
                print(f"Error fetching image for {landmark}: {e}")
                landmark_info['image'] = None
            landmarks_with_images.append(landmark_info)
        city_info.landmarks = landmarks_with_images
        return city_info
    except Exception as e:
        print(f"Error getting city info: {e}")
        return CityInfo(landmarks=[], activities=[], restaurants=[])

def get_gps_coordinates(city: str, api_key: str) -> dict:
    url = f"https://maps.googleapis.com/maps/api/geocode/json?address={city}&key={api_key}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        if data['results']:
            location = data['results'][0]['geometry']['location']
            return {"lat": location['lat'], "lng": location['lng']}
    return {"lat": None, "lng": None}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)