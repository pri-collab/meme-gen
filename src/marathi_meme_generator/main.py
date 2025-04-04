import os
import random
import requests
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import Request
from PIL import Image, ImageDraw, ImageFont
import io
from dotenv import load_dotenv
from pydantic import BaseModel

# Load environment variables
load_dotenv()

app = FastAPI()

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
templates = Jinja2Templates(directory="templates")

# Default memes 
# TODO - Add more memes
DEFAULT_MEMES = [
    "https://api.memegen.link/images/doge/such_meme/very_app.png",
    "https://api.memegen.link/images/grumpycat/no/like_this.png",
    "https://api.memegen.link/images/rollsafe/cant_have_problems/if_you_dont_think.png",
]

class SearchQuery(BaseModel):
    text: str
    language: str = "en"  # Default to English

def get_giphy_meme(text):
    """Fetch a random meme from Giphy based on the input text."""
    api_key = os.getenv("GIPHY_API_KEY")
    if not api_key:
        return random.choice(DEFAULT_MEMES)
    
    url = f"https://api.giphy.com/v1/gifs/search"
    params = {
        "api_key": api_key,
        "q": text,
        "limit": 1,
        "rating": "g"
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        if data["data"]:
            return data["data"][0]["images"]["original"]["url"]
        return random.choice(DEFAULT_MEMES)
    except Exception:
        return random.choice(DEFAULT_MEMES)

def get_font(language):
    """Get the appropriate font based on language."""
    try:
        if language == "mr":  # Marathi
            return ImageFont.truetype("static/fonts/NotoSansMarathi-Regular.ttf", 40)
        else:  # English
            return ImageFont.truetype("arial.ttf", 40)
    except:
        return ImageFont.load_default()

def add_text_to_image(image_url, text, language="en"):
    """Download image and add text to it."""
    try:
        # Download image
        response = requests.get(image_url)
        response.raise_for_status()
        image = Image.open(io.BytesIO(response.content))
        
        # Create drawing object
        draw = ImageDraw.Draw(image)
        
        # Get appropriate font
        font = get_font(language)
        
        # Add text to image
        text_width, text_height = draw.textsize(text, font=font)
        x = (image.width - text_width) / 2
        y = image.height - text_height - 20
        
        # Add text with outline for better visibility
        outline_color = "black"
        text_color = "white"
        
        # Draw outline
        for offset in [(1,1), (-1,1), (1,-1), (-1,-1)]:
            draw.text((x + offset[0], y + offset[1]), text, font=font, fill=outline_color)
        
        # Draw main text
        draw.text((x, y), text, font=font, fill=text_color)
        
        # Save to bytes
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='PNG')
        img_byte_arr.seek(0)
        
        return img_byte_arr
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/search")
async def search_meme(query: SearchQuery):
    """
    Search for a meme based on the input text and return the generated meme.
    """
    if not query.text:
        raise HTTPException(status_code=400, detail="Text cannot be empty")
    
    # Get meme image URL
    meme_url = get_giphy_meme(query.text)
    
    # Add text to image
    image_bytes = add_text_to_image(meme_url, query.text, query.language)
    
    return Response(content=image_bytes.getvalue(), media_type="image/png") 