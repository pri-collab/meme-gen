# Marathi Meme Generator

A Streamlit application that generates memes with Marathi text and sentiment analysis. The app can detect emotions in both English and Marathi text, and generates appropriate memes with text overlay.

## Features

- Sentiment analysis for both English and Marathi text
- Emotion detection (happy, sad, positive, negative, neutral)
- Special handling for Marathi emotions (flirt, roast, sarcasm)
- Text overlay on memes (supports both static images and animated GIFs)
- Fallback memes when API rate limits are reached
- UI with Streamlit



## Setup

1. Clone the repository:
```bash
git clone https://github.com/pri-collab/meme-gen.git
cd meme-gen
```

2. Create and activate a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies using uv:
```bash
uv pip install -e .
```

4. Create a `.env` file with your GIPHY API key:
```
GIPHY_API_KEY=your_api_key_here
```

## Usage

1. Run the Streamlit app:
```bash
.venv/bin/python -m streamlit run src/marathi_meme_generator/main.py
```

2. Open your browser and go to http://localhost:8501

3. Enter text in the input box to generate memes. Examples:
   - English: "I'm so happy!", "This is terrible", "The sky is blue"
   - Marathi: "खूप छान", "jevlas ka", "gadhav"
   - Sarcastic: "skill issue", "git gud", "cope and seethe"

## Features in Detail

### Sentiment Analysis
- Uses NLTK's VADER for English sentiment analysis
- Custom Marathi emotion detection
- Supports multiple emotions: happy, sad, positive, negative, neutral
- Special handling for Marathi-specific emotions (flirt, roast, sarcasm)

### Meme Generation
- Fetches memes from GIPHY API
- Prioritizes animated GIFs
- Adds text overlay with proper formatting
- Includes fallback memes for when API rate limits are reached
- Supports both static images and animated GIFs

### Text Overlay
- Automatically sizes text to fit the image
- Adds black background for better readability
- White text with black outline for visibility

## Dependencies

- streamlit>=1.32.0
- Pillow>=10.2.0
- requests>=2.31.0
- python-dotenv>=1.0.0
- giphy_client>=1.0.0
- nltk>=3.8.1

=======
# meme-gen
searches memes based on text ( supports Marathi)

