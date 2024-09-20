import os
import requests
from fastapi import FastAPI, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import openai

from dotenv import load_dotenv  # Add this import

# Load environment variables from .env file
load_dotenv()  # Add this line


app = FastAPI()

# Set up templates and static files
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Set up OpenAI API key
openai.api_key = os.environ.get("OPENAI_API_KEY")

class CityInfo(BaseModel):
    landmarks: list[str]
    activities: list[str]
    restaurants: list[str]

@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/")
async def get_city_info(request: Request, city: str = Form(...)):
    city_info = await get_city_info_from_ai(city)
    gmap_api_key = os.getenv('GMAP_API_KEY')
    coordinates = get_gps_coordinates(city, gmap_api_key)  # Ensure this line is correct
    return templates.TemplateResponse("result.html", {
        "request": request,
        "city": city,
        "landmarks": city_info.landmarks,
        "activities": city_info.activities,
        "restaurants": city_info.restaurants,
        "gmap_api_key": gmap_api_key,
        "coordinates": coordinates  # Ensure this line is correct
    })

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

def parse_response(content: str) -> tuple[list[str], list[str]]:
    landmarks = []
    activities = []
    current_list = None

    for line in content.split('\n'):
        line = line.strip()
        if line.lower().startswith("landmarks:"):
            current_list = landmarks
        elif line.lower().startswith("activities:"):
            current_list = activities
        elif line.startswith(("1.", "2.", "3.", "4.", "5.")) and current_list is not None:
            current_list.append(line[3:].strip())

    return landmarks, activities

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)