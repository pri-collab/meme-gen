import os
import random
import requests
from PIL import Image, ImageDraw, ImageFont
import io
from dotenv import load_dotenv
import streamlit as st
import re
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('meme_generator.log'),
        logging.StreamHandler()
    ]
)

# Disable unnecessary logging
logging.getLogger('PIL').setLevel(logging.WARNING)
logging.getLogger('dotenv').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)

# Load environment variables
load_dotenv()

# Default neutral memes for fallback
NEUTRAL_MEMES = [
    "https://media.giphy.com/media/ICOgUNjpvO0PC/giphy.gif",     
    "https://media.giphy.com/media/3oKIPnAiaMCws8nOsE/giphy.gif", 
    "https://media.giphy.com/media/W3QKEujo8vztC/giphy.gif"      
]

# Marathi words categorized by emotions/sentiments
MARATHI_EMOTIONS = {
    'happy': {
        'bara', 'bari', 'changla', 'changali', 'chhan', 'mast', 'khush', 'anandi',
        'majja', 'majet', 'waah'
    },
    'sad': {
        'dukh', 'rad', 'radto', 'radtoy', 'raag', 'ragavto', 'ragavtoy', 'waeet',
        'vait', 'kharab', 'tras'
    },
    'angry': {
        'rag', 'raag', 'ragavla', 'ragavli', 'chid', 'chidla', 'chidli',
        'gadhav', 'kavlya', 'taklya'
    },
    'surprise': {
        'are', 'arre', 'arrey', 'kay', 'kaay', 'khara',
        'kharach','bapre','kahihi'
    },
    'question': {
        'kay', 'kaay', 'kasa', 'kashi', 'ka', 'kaa', 'kashala', 'kuthe',
        'kadhi', 'kenvha','kashasathi'
    },
    'neutral': {
        'aahe', 'ahe', 'hota', 'hoti', 'hot', 'nahi', 'naahi',
        'mi', 'tu', 'tumhi', 'aapan', 'ghari', 'ja'
    },
    'excited': {
        'khup', 'khoop', 'jast', 'jaast', 'ekdum', 'bhari', 'jabardast',
        'jhakas', 'aha', 'mast', 'anand'
    },
    'flirt': {
        'sundar', 'sundara', 'goad', 'jevlis', 'jevlas', 'janu', 'babe', 'baby',
        'prem', 'pritam', 'jaanu', 'babu', 'sona', 'maza', 'majha', 'tujha', 
        'tujhi', 'jiv'
    },
    'roast': {
        'veda', 'vedi', 'pagal', 'gadha', 'gadhav', 'mahamurkh', 'mhais', 'reda', 'redya',
        'popat', 'buddhu', 'nalayak', 'gadhava', 'murkha', 'makad', 'shahana',
        'bavlat', 'chapri', 'baila', 'kavlya', 'taklya', 'chakram'
    }
}

# Flatten emotions dict for word detection
MARATHI_COMMON_WORDS = set().union(*MARATHI_EMOTIONS.values())

def is_marathi(text):
    """Check if text contains Marathi Unicode characters."""
    marathi_pattern = re.compile(r'[\u0900-\u097F]')
    return bool(marathi_pattern.search(text))

def is_marathi_transcript(text):
    """Check if text might be Marathi written in English."""
    words = set(text.lower().split())
    marathi_word_count = len(words.intersection(MARATHI_COMMON_WORDS))
    return marathi_word_count / len(words) > 0.2 if words else False

def detect_emotion(text):
    """Detect emotion from Marathi text."""
    # Convert text to lowercase and split into words
    words = text.lower().split()
    
    # First check for exact phrases
    text_lower = text.lower()
    if 'jevlas ka' in text_lower or 'jevlis ka' in text_lower:
        return 'flirt'
    if 'ghari ja' in text_lower or 'ghari ja' in text_lower:
        return 'roast'
    
    # Then check individual words in dictionary
    emotion_counts = {}
    for emotion, word_set in MARATHI_EMOTIONS.items():
        count = len(set(words).intersection(word_set))
        if count > 0:
            emotion_counts[emotion] = count
    
    # Return emotion with most matches, or neutral if none found
    return max(emotion_counts.items(), key=lambda x: x[1])[0] if emotion_counts else 'neutral'

def get_giphy_meme(text):
    """Fetch a relevant meme from Giphy based on the input text and emotion."""
    api_key = os.getenv("GIPHY_API_KEY")
    if not api_key:
        logging.warning("No GIPHY API key found, using neutral memes")
        return random.choice(NEUTRAL_MEMES)
    
    url = "https://api.giphy.com/v1/gifs/search"
    
    # Different handling for Marathi and English text
    is_marathi_text = is_marathi(text) or is_marathi_transcript(text)
    
    if is_marathi_text:
        # Detect emotion from Marathi text
        emotion = detect_emotion(text)
        logging.info(f"Detected emotion for '{text}': {emotion.upper()}")
        
        # Special handling for flirt emotion with more variety
        if emotion == 'flirt':
            flirt_searches = [
                'cute couple reaction',
                'flirting anime',
                'love cute cartoon',
                'romantic reaction',
                'sweet love',
                'cute love',
                'anime blush',
                'shy cute',
                'cute flirt',
                'blushing reaction'
            ]
            logging.info(f"Using flirt search terms for: {text}")
            # Try each search term with higher limit for more variety
            for search_term in random.sample(flirt_searches, len(flirt_searches)):
                logging.info(f"Trying search term: {search_term}")
                try:
                    params = {
                        "api_key": api_key,
                        "q": search_term,
                        "limit": 10,
                        "rating": "g",
                        "offset": random.randint(0, 10)
                    }
                    
                    response = requests.get(url, params=params)
                    response.raise_for_status()
                    data = response.json()
                    
                    if data["data"]:
                        logging.info(f"Found meme for search term: {search_term}")
                        return random.choice(data["data"])["images"]["original"]["url"]
                except Exception as e:
                    logging.error(f"Error with search term '{search_term}': {str(e)}")
                    continue
        
        # For other emotions
        search_terms = {
            'roast': ['roast meme', 'savage reaction', 'insult funny'],
            'happy': ['happy dance', 'celebration', 'joy reaction'],
            'sad': ['sad crying', 'disappointed', 'upset reaction'],
            'angry': ['angry reaction', 'rage meme', 'mad funny'],
            'surprise': ['shocked reaction', 'surprised meme', 'wow face'],
            'question': ['confused meme', 'thinking reaction', 'doubt face'],
            'excited': ['excited reaction', 'awesome', 'celebration'],
            'neutral': ['neutral reaction', 'okay meme', 'normal face']
        }
        
        emotion_terms = search_terms.get(emotion, ['reaction'])
        search_attempts = [
            f"meme {emotion_terms[0]}",
            emotion_terms[0],
            emotion_terms[1] if len(emotion_terms) > 1 else 'funny reaction',
            emotion_terms[2] if len(emotion_terms) > 2 else 'reaction',
            'funny reaction'
        ]
        
        # Add random offset for more variety
        for search_term in search_attempts:
            try:
                params = {
                    "api_key": api_key,
                    "q": search_term,
                    "limit": 5,
                    "rating": "g",
                    "offset": random.randint(0, 10)
                }
                
                response = requests.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                
                if data["data"]:
                    return random.choice(data["data"])["images"]["original"]["url"]
            except:
                continue
    else:
        # For English text, use the text directly with random offset
        search_attempts = [
            text,
            ' '.join(text.split()[:2]),
            text.split()[0],
            'reaction',
            'funny'
        ]
        
        for search_term in search_attempts:
            try:
                params = {
                    "api_key": api_key,
                    "q": search_term,
                    "limit": 5,
                    "rating": "g",
                    "offset": random.randint(0, 10)
                }
                
                response = requests.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                
                if data["data"]:
                    return random.choice(data["data"])["images"]["original"]["url"]
            except:
                continue
    
    return random.choice(NEUTRAL_MEMES)

def get_font(text, size):
    """Get the font for text rendering."""
    try:
        # Only use Devanagari font for actual Devanagari script
        if is_marathi(text):
            # Common paths for Noto Sans Devanagari font
            marathi_font_paths = [
                "/System/Library/Fonts/Supplemental/Noto Sans Devanagari.ttf",  # macOS
                "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf",  # Linux
                "C:\\Windows\\Fonts\\NotoSansDevanagari-Regular.ttf",  # Windows
                "static/fonts/NotoSansDevanagari-Regular.ttf"  # Local project directory
            ]
            
            for path in marathi_font_paths:
                if os.path.exists(path):
                    return ImageFont.truetype(path, size)
            
            # If font not found locally, download it from google fonts
            font_url = "https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSansDevanagari/NotoSansDevanagari-Regular.ttf"
            response = requests.get(font_url)
            if response.status_code == 200:
                font_bytes = io.BytesIO(response.content)
                return ImageFont.truetype(font_bytes, size)
        
        # For English text and transliterated Marathi, use Impact font
        impact_paths = [
            "/Library/Fonts/Impact.ttf",  # macOS
            "/usr/share/fonts/truetype/msttcorefonts/Impact.ttf",  # Linux
            "C:\\Windows\\Fonts\\Impact.ttf",  # Windows
            "static/fonts/Impact.ttf"  # Local project directory
        ]
        
        for path in impact_paths:
            if os.path.exists(path):
                return ImageFont.truetype(path, size)
        
        # If Impact not found, download DejaVuSans as fallback
        impact_url = "https://github.com/python-pillow/Pillow/blob/main/Tests/fonts/DejaVuSans.ttf?raw=true"
        response = requests.get(impact_url)
        font_bytes = io.BytesIO(response.content)
        return ImageFont.truetype(font_bytes, size)
    except:
        # Fallback to default font if everything else fails
        return ImageFont.load_default()

def wrap_text(text, width, font, draw):
    """Wrap text to fit within a given width."""
    words = text.split()
    lines = []
    current_line = []
    
    for word in words:
        current_line.append(word)
        test_line = ' '.join(current_line)
        bbox = draw.textbbox((0, 0), test_line, font=font)
        text_width = bbox[2] - bbox[0]
        
        if text_width > width:
            if len(current_line) > 1:
                current_line.pop()
                lines.append(' '.join(current_line))
                current_line = [word]
            else:
                lines.append(word)
                current_line = []
    
    if current_line:
        lines.append(' '.join(current_line))
    
    return '\n'.join(lines)

def calculate_optimal_font_size(draw, text, image_width, image_height, border_height):
    """Calculate the optimal font size that fits the text within the image width."""
    # Calculate font sizes based on text length and 20% of image height
    word_count = len(text.split())
    char_count = len(text)
    
    # Base maximum size on border height (which is 20% of image height)
    if word_count <= 3 and char_count <= 15:
        max_size = min(70, border_height // 2)
    elif word_count <= 6 and char_count <= 30:
        max_size = min(55, border_height // 2)
    else:
        max_size = min(45, border_height // 2)
    
    min_size = 25
    current_size = max_size
    
    while current_size >= min_size:
        try:
            font = get_font(text, current_size)
            wrapped_text = wrap_text(text, image_width * 0.85, font, draw)
            num_lines = wrapped_text.count('\n') + 1
            line_spacing = current_size // 6
            total_text_height = (current_size * num_lines) + (line_spacing * (num_lines - 1))
            
            bbox = draw.multiline_textbbox((0, 0), wrapped_text, font=font, align='center', spacing=line_spacing)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            if (text_width <= image_width * 0.85 and 
                text_height <= border_height * 0.85 and
                total_text_height <= border_height * 0.85):
                return font, text_width, text_height, wrapped_text, line_spacing
            
            current_size -= 3
        except:
            current_size -= 3
            continue
    
    # If no size worked, use minimum size
    font = get_font(text, min_size)
    wrapped_text = wrap_text(text, image_width * 0.85, font, draw)
    bbox = draw.multiline_textbbox((0, 0), wrapped_text, font=font, align='center')
    line_spacing = min_size // 6
    return font, bbox[2] - bbox[0], bbox[3] - bbox[1], wrapped_text, line_spacing

def add_text_to_image(image_url, text):
    """Download image and add text to it."""
    try:
        response = requests.get(image_url)
        response.raise_for_status()
        image = Image.open(io.BytesIO(response.content)).convert('RGBA')
        draw = ImageDraw.Draw(image)
        
        # Use exactly 20% of image height for text area
        border_height = int(image.height * 0.20)
        draw.rectangle(
            [(0, image.height - border_height), (image.width, image.height)],
            fill=(0, 0, 0, 255)
        )
        
        font, text_width, text_height, wrapped_text, line_spacing = calculate_optimal_font_size(
            draw, text, image.width, image.height, border_height
        )
        
        # Center text in the border area
        x = (image.width - text_width) / 2
        y = (image.height - border_height) + ((border_height - text_height) / 2)
        
        # Draw outline
        outline_width = 2
        for adj in range(-outline_width, outline_width+1):
            for adj2 in range(-outline_width, outline_width+1):
                if adj != 0 or adj2 != 0:
                    draw.multiline_text(
                        (x+adj, y+adj2),
                        wrapped_text,
                        font=font,
                        fill=(0, 0, 0, 255),
                        align='center',
                        spacing=line_spacing
                    )
        
        # Draw main text
        draw.multiline_text(
            (x, y),
            wrapped_text,
            font=font,
            fill=(255, 255, 255, 255),
            align='center',
            spacing=line_spacing
        )
        
        img_byte_arr = io.BytesIO()
        image.convert('RGB').save(img_byte_arr, format='PNG', quality=100)
        img_byte_arr.seek(0)
        return img_byte_arr
        
    except Exception as e:
        st.error(f"Error creating meme: {str(e)}")
        return None

def main():
    st.title("Meme Generator")

    text = st.text_input("Enter your text:", "")
    
    if st.button("Generate Meme"):
        if not text:
            st.warning("Please enter some text!")
        else:
            with st.spinner("Generating your meme..."):
                # Check if text is Marathi
                is_marathi_text = is_marathi(text) or is_marathi_transcript(text)
                if is_marathi_text:
                    emotion = detect_emotion(text)
                    st.info(f"Detected emotion: {emotion.upper()}")
                
                meme_url = get_giphy_meme(text)
                image_bytes = add_text_to_image(meme_url, text)
                if image_bytes:
                    st.image(image_bytes, use_container_width=True)

# Create fonts directory if it doesn't exist
os.makedirs("static/fonts", exist_ok=True)

if __name__ == "__main__":
    main() 