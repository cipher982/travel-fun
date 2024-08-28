import os
from fastapi import FastAPI, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import openai

app = FastAPI()

# Set up templates and static files
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Set up OpenAI API key
openai.api_key = os.environ.get("OPENAI_API_KEY")

class CityInfo(BaseModel):
    landmarks: list[str]
    activities: list[str]


@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/")
async def get_city_info(request: Request, city: str = Form(...)):
    city_info = await get_city_info_from_ai(city)
    return templates.TemplateResponse("result.html", {
        "request": request,
        "city": city,
        "landmarks": city_info.landmarks,
        "activities": city_info.activities
    })

async def get_city_info_from_ai(city: str) -> CityInfo:
    try:
        client = openai.AsyncOpenAI()
        completion = await client.beta.chat.completions.parse(
            model="gpt-4o-2024-08-06",
            messages=[
                {"role": "system", "content": "Provide information about landmarks and activities in the given city."},
                {"role": "user", "content": f"Provide top 5 landmarks and 5 fun activities in {city}."},
            ],
            response_format=CityInfo,
        )
        
        city_info = completion.choices[0].message.parsed
        return city_info
    except Exception as e:
        print(f"Error getting city info: {e}")
        return CityInfo(landmarks=[], activities=[])

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