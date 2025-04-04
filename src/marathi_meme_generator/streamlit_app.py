import os
import random
import requests
from PIL import Image, ImageDraw, ImageFont
import io
from dotenv import load_dotenv
import streamlit as st
import re
import logging
import giphy_client
from giphy_client.rest import ApiException
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer

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
    "https://media.giphy.com/media/W3QKEujo8vztC/giphy.gif",
    "https://media.giphy.com/media/xT0GqimU9dTwmE5lra/giphy.gif",  # Shrug
    "https://media.giphy.com/media/3o7TKwmnDgQb5jemjK/giphy.gif",  # Whatever
    "https://media.giphy.com/media/3o6Zt4HU9uwXmXSAuI/giphy.gif",  # Meh
    "https://media.giphy.com/media/3o6UB2MSoh7z6Gw3fO/giphy.gif",  # Neutral face
    "https://media.giphy.com/media/3oAt2dA6LxMkRrGc0g/giphy.gif"   # OK
]

# Marathi words categorized by emotions/sentiments
MARATHI_EMOTIONS = {
    'happy': {
        'bara', 'bari', 'changla', 'changali', 'chhan', 'mast', 'khush', 'anandi',
        'majja', 'majet', 'waah', 'hushar', 'hushaar', 'hushshar', 'hushyar',
        'shaana', 'shahana', 'chalak'
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
        'prem',  'jaanu', 'babu', 'sona', 'maza', 'majha', 'tujha', 
        'tujhi', 'jiv','qt','cute', 'tu khup qt ahe', 'qt ahes', 'cute ahes',
        'khup cute ahe'
    },
    'roast': {
        'veda', 'vedi', 'pagal', 'gadha', 'gadhav', 'mahamurkh', 'mhais', 'reda', 'redya',
        'popat', 'buddhu', 'nalayak', 'gadhava', 'murkha', 'murkhya', 'murkh', 'makad', 
        'bavlat', 'chapri', 'baila', 'kavlya', 'taklya', 'chakram', 'dhakkan',
        'bewakoof', 'bewkuf', 'bewda', 'randukkar', 'tapori'
    },
    'sarcasm': {
        'ho_na', 'hona', 'barach', 'khari', 'khupach', 'kharch', 'obviously',
        'jarur', 'nakkich', 'avjun', 'avashya', 'shahanapana', 'shahane',
        'great', 'wah_wah', 'wahwa', 'khup_chhan_ha', 'kiti_changla_re_tu', 'kiti_hushaar',
        'vaah_re', 'vah_re', 'vah_va', 'asa_ka', 'asa_kaa', 'hoy_na', 'hoyna'
    }
}

# Flatten emotions dict for word detection
MARATHI_COMMON_WORDS = set().union(*MARATHI_EMOTIONS.values())

# Download NLTK data
try:
    nltk.data.find('sentiment/vader_lexicon.zip')
except LookupError:
    nltk.download('vader_lexicon')

# Initialize sentiment analyzer
sia = SentimentIntensityAnalyzer()

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
    """check the emotion from Marathi text."""
    # Convert text to lowercase for case-insensitive matching
    text_lower = text.lower()
    words = text_lower.split()
    
    # First check for roast words (highest priority) with partial matching
    for roast_word in MARATHI_EMOTIONS['roast']:
        if any(roast_word in word for word in words):
            return 'roast'
    
    # Then check for flirt-specific patterns with partial matching
    if any('qt' in word or 'cute' in word for word in words):
        return 'flirt'
        
    # Check for specific phrases
    flirt_phrases = [
        'jevlas ka', 'jevlis ka', 'khup cute ahe', 'tu khup qt ahe', 
        'qt ahes', 'cute ahes', 'khup qt', 'you are qt', 'you are cute',
        'tu qt', 'tu cute'
    ]
    if any(phrase in text_lower for phrase in flirt_phrases):
        return 'flirt'
        
    if 'ghari ja' in text_lower:
        return 'roast'
        
    if any(phrase in text_lower for phrase in ['ho na', 'hoy na', 'kiti chan']):
        return 'sarcasm'
    
    # Then check for word combinations that indicate flirting
    if ('khup' in words or 'khoop' in words) and ('cute' in words or 'qt' in words):
        return 'flirt'
    
    # Then check individual words in dictionary with partial matching
    emotion_counts = {}
    for emotion, word_set in MARATHI_EMOTIONS.items():
        # Count both exact and partial matches
        count = 0
        for word in words:
            # Check if any emotion word is part of the current word
            matches = sum(1 for emotion_word in word_set if emotion_word in word)
            count += matches
        if count > 0:
            emotion_counts[emotion] = count
    
    # Return emotion with most matches, or neutral if none found
    return max(emotion_counts.items(), key=lambda x: x[1])[0] if emotion_counts else 'neutral'

def analyze_sentiment(text):
    """Analyze sentiment of the text using NLTK's VADER and custom Marathi word lists."""
    # First check for Marathi emotion using detect_emotion
    emotion = detect_emotion(text.lower())
    if emotion != 'neutral':
        return emotion
            
    # If no Marathi emotion detected, use NLTK for English
    try:
        scores = sia.polarity_scores(text)
        compound_score = scores['compound']
        
        if compound_score >= 0.05:
            return 'happy'
        elif compound_score <= -0.05:
            return 'sad'
        else:
            return 'neutral'
    except Exception as e:
        st.error(f"Error in sentiment analysis: {str(e)}")
        return 'neutral'

def get_giphy_meme(text):
    """Get a meme from Giphy based on text sentiment."""
    try:
        # Get API key
        api_key = os.getenv("GIPHY_API_KEY")
        if not api_key:
            logging.warning("No GIPHY API key found, using neutral memes")
            return random.choice(NEUTRAL_MEMES)

        # Configure API key
        api_instance = giphy_client.DefaultApi()
        
        # Analyze sentiment
        emotion = analyze_sentiment(text)
        st.info(f"Detected sentiment: {emotion.upper()}")
        
        # Define search terms based on sentiment with more variety
        search_terms = {
            'happy': ['happy meme', 'joy reaction', 'excited gif', 'celebration gif', 'dance happy'],
            'sad': ['sad meme', 'depressed reaction', 'crying gif', 'disappointed gif', 'upset reaction'],
            'positive': ['positive vibes', 'good mood', 'optimistic', 'thumbs up gif', 'awesome reaction'],
            'negative': ['angry meme', 'frustrated reaction', 'annoyed gif', 'mad gif', 'rage quit'],
            'neutral': ['neutral reaction', 'meh meme', 'whatever gif', 'ok gif', 'shrug gif'],
            'flirt': ['cute flirt', 'romantic cute', 'sweet couple', 'wink gif', 'flirting reaction'],
            'roast': ['roast meme', 'savage reaction', 'burn gif', 'destruction gif', 'owned gif'],
            'sarcasm': [
                'sarcastic reaction', 'eye roll', 'yeah right meme', 
                'sure sure gif', 'obviously meme', 'skill issue meme',
                'git gud reaction', 'cope seethe meme', 'sarcastic face',
                'eyeroll gif', 'whatever reaction', 'sarcastic clap',
                'slow clap', 'sarcastic applause'
            ]
        }
        
        # Get search terms for the detected emotion
        terms = search_terms.get(emotion, ['meme', 'reaction'])
        
        # Randomly select a search term and get multiple results
        term = random.choice(terms)
        try:
            api_response = api_instance.gifs_search_get(
                api_key,
                term,
                limit=5,  # Get 5 results instead of 1
                rating='g'
            )
            if api_response.data:
                # Randomly select one of the results
                return random.choice(api_response.data).images.original.url
        except ApiException as e:
            if e.status == 429:  # Rate limit exceeded
                st.warning("GIPHY API rate limit reached. Using fallback memes.")
            else:
                st.warning(f"Failed to search with term '{term}': {str(e)}")
        
        # If we hit rate limit or no memes found, use fallback memes
        fallback_memes = {
            'happy': [
                "https://media.giphy.com/media/ICOgUNjpvO0PC/giphy.gif",  # Happy dance
                "https://media.giphy.com/media/l41lUjUgLLwWrz20w/giphy.gif",  # Celebration
                "https://media.giphy.com/media/26u4lOMA8JKSnL9Uk/giphy.gif"  # Joy
            ],
            'sad': [
                "https://media.giphy.com/media/3oKIPnAiaMCws8nOsE/giphy.gif",  # Sad face
                "https://media.giphy.com/media/d2lcHJTG5Tscg/giphy.gif",  # Crying
                "https://media.giphy.com/media/OPU6wzx8JrHna/giphy.gif"  # Disappointed
            ],
            'sarcasm': [
                "https://media.giphy.com/media/3oKIPnAiaMCws8nOsE/giphy.gif",  # Eye roll
                "https://media.giphy.com/media/wzxK9cmYgIPDy/giphy.gif",  # Whatever
                "https://media.giphy.com/media/l0HlvtIPzPzsNYbXW/giphy.gif"  # Sure sure
            ],
            'roast': [
                "https://media.giphy.com/media/W3QKEujo8vztC/giphy.gif",  # Burn
                "https://media.giphy.com/media/Aff4ryYiacUO4/giphy.gif",  # Destroyed
                "https://media.giphy.com/media/RdKjAkFTNZkWUGyRXF/giphy.gif"  # Roasted
            ],
            'flirt': [
                "https://media.giphy.com/media/3oKIPnAiaMCws8nOsE/giphy.gif",  # Wink
                "https://media.giphy.com/media/l41Yh1jQhxNQHQXL2/giphy.gif",  # Cute
                "https://media.giphy.com/media/l0HlDJhyI8qoh7Wfu/giphy.gif"  # Sweet
            ],
            'positive': [
                "https://media.giphy.com/media/3oKIPnAiaMCws8nOsE/giphy.gif",  # Thumbs up
                "https://media.giphy.com/media/ICOgUNjpvO0PC/giphy.gif",  # Happy dance
                "https://media.giphy.com/media/W3QKEujo8vztC/giphy.gif",  # Celebration
                "https://media.giphy.com/media/l41YdDNnasCzZXWX6/giphy.gif"  # Awesome
            ],
            'negative': [
                "https://media.giphy.com/media/W3QKEujo8vztC/giphy.gif",  # Angry
                "https://media.giphy.com/media/l41YfykEffZ7QM55m/giphy.gif",  # Mad
                "https://media.giphy.com/media/l0HlDHQEiIdY3kxlm/giphy.gif"  # Rage
            ],
            'neutral': NEUTRAL_MEMES
        }
        
        # Return a random fallback meme based on emotion, or a neutral one if no specific fallback
        return random.choice(fallback_memes.get(emotion, NEUTRAL_MEMES))
        
    except Exception as e:
        st.error(f"Error getting meme: {str(e)}")
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
        max_size = min(60, border_height // 3)  # Reduced from 70 to 60
    elif word_count <= 6 and char_count <= 30:
        max_size = min(45, border_height // 3)  # Reduced from 55 to 45
    else:
        max_size = min(35, border_height // 3)  # Reduced from 45 to 35
    
    min_size = 20  # Reduced from 25 to 20
    current_size = max_size
    
    while current_size >= min_size:
        try:
            font = get_font(text, current_size)
            wrapped_text = wrap_text(text, image_width * 0.85, font, draw)
            num_lines = wrapped_text.count('\n') + 1
            line_spacing = current_size // 4  # Reduced from 6 to 4 for tighter spacing
            total_text_height = (current_size * num_lines) + (line_spacing * (num_lines - 1))
            
            bbox = draw.multiline_textbbox((0, 0), wrapped_text, font=font, align='center', spacing=line_spacing)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            if (text_width <= image_width * 0.85 and 
                text_height <= border_height * 0.85 and
                total_text_height <= border_height * 0.85):
                return font, text_width, text_height, wrapped_text, line_spacing
            
            current_size -= 2  # Reduced step size from 3 to 2 for finer control
        except:
            current_size -= 2
            continue
    
    # If no size worked, use minimum size
    font = get_font(text, min_size)
    wrapped_text = wrap_text(text, image_width * 0.85, font, draw)
    bbox = draw.multiline_textbbox((0, 0), wrapped_text, font=font, align='center')
    line_spacing = min_size // 4  # Reduced from 6 to 4
    return font, bbox[2] - bbox[0], bbox[3] - bbox[1], wrapped_text, line_spacing

def add_text_to_image(image_url, text):
    """Download image and add text to it."""
    try:
        response = requests.get(image_url)
        response.raise_for_status()
        image = Image.open(io.BytesIO(response.content))
        
        # Check if image is animated GIF
        if getattr(image, "is_animated", False):
            # Get all frames
            frames = []
            for frame in range(image.n_frames):
                image.seek(frame)
                frame_image = image.convert('RGBA')
                
                # Create a copy of the frame to draw on
                frame_with_text = frame_image.copy()
                draw = ImageDraw.Draw(frame_with_text)
                
                # Use exactly 20% of image height for text area
                border_height = int(frame_with_text.height * 0.20)
                draw.rectangle(
                    [(0, frame_with_text.height - border_height), 
                     (frame_with_text.width, frame_with_text.height)],
                    fill=(0, 0, 0, 255)
                )
                
                font, text_width, text_height, wrapped_text, line_spacing = calculate_optimal_font_size(
                    draw, text, frame_with_text.width, frame_with_text.height, border_height
                )
                
                # Center text in the border area with more padding at the bottom
                x = (frame_with_text.width - text_width) / 2
                y = (frame_with_text.height - border_height) + ((border_height - text_height) / 2) - 5  # Added -5 for better bottom padding
                
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
                
                frames.append(frame_with_text)
            
            # Save as animated GIF
            img_byte_arr = io.BytesIO()
            frames[0].save(
                img_byte_arr,
                format='GIF',
                save_all=True,
                append_images=frames[1:],
                duration=image.info.get('duration', 100),
                loop=0
            )
            img_byte_arr.seek(0)
            return img_byte_arr
        else:
            # Handle static images as before
            image = image.convert('RGBA')
            draw = ImageDraw.Draw(image)
            
            border_height = int(image.height * 0.20)
            draw.rectangle(
                [(0, image.height - border_height), (image.width, image.height)],
                fill=(0, 0, 0, 255)
            )
            
            font, text_width, text_height, wrapped_text, line_spacing = calculate_optimal_font_size(
                draw, text, image.width, image.height, border_height
            )
            
            x = (image.width - text_width) / 2
            y = (image.height - border_height) + ((border_height - text_height) / 2) - 5  # Added -5 for better bottom padding
            
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