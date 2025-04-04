# Marathi Meme Generator

A Streamlit application that generates memes with Marathi text. The app detects emotions from Marathi text (both Devanagari and transliterated) and fetches relevant memes from Giphy.

## Features

- Supports both Devanagari and transliterated Marathi text
- Emotion detection for Marathi text
- Automatic font selection (Devanagari for Marathi, Impact for English)
- Dynamic text sizing and wrapping
- Meme generation based on detected emotions

## Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/marathi-meme-generator.git
cd marathi-meme-generator
```

2. Create a virtual environment and activate it:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies using uv:
```bash
uv add streamlit Pillow requests python-dotenv
```

4. Create a `.env` file with your Giphy API key:
```
GIPHY_API_KEY=your_api_key_here
```

5. Run the application:
```bash
streamlit run streamlit_app.py
```

## Requirements

- Python 3.9+
- uv (Python package installer)
- Streamlit
- Pillow
- Requests
- python-dotenv

## Usage

1. Enter Marathi text (in Devanagari or transliterated form)
2. Click "Generate Meme"
3. The app will detect the emotion and generate a relevant meme

## Examples

- "jevlas ka" → Flirt emotion
- "खूप छान" → Happy emotion
- "gadhav" → Roast emotion

