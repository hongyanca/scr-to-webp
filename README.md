# Screenshot to WebP Converter

A Python script that automatically finds the newest screenshot, generates meaningful filenames using AI, and converts PNG screenshots to WebP format with compression.

## Features

- 🔍 **Auto-detection**: Finds the newest screenshot starting with "SCR-" in your Downloads folder
- 🤖 **AI-powered naming**: Uses LLM to generate meaningful, SEO-friendly filenames
- 🗂️ **Interactive selection**: Choose from multiple filename suggestions
- 📦 **WebP conversion**: Converts PNG to WebP format with 80% quality for optimal compression
- 📊 **Compression stats**: Shows file sizes and compression ratio

## Requirements

- Python 3.10+
- `cwebp` CLI tool (part of WebP tools)
- OpenRouter API key for LLM access

### Installing WebP Tools

**macOS (using Homebrew):**
```bash
brew install webp
```

**Ubuntu/Debian:**
```bash
sudo apt-get install webp
```

**Windows:**
Download from [Google's WebP page](https://developers.google.com/speed/webp/download)

## Setup

1. Clone or download this script
2. Install required Python packages:
   ```bash
   pip install requests
   ```
3. Set your OpenRouter API key as an environment variable:
   ```bash
   export OPENROUTER_API_KEY="your_api_key_here"
   ```

## Usage

1. Take a screenshot (it should be saved as "SCR-*.png" in your Downloads folder)
2. Run the script:
   ```bash
   python main.py
   ```
3. Choose from the AI-generated filename suggestions
4. The script will convert your screenshot to WebP format

## Configuration

You can modify these constants in the script:

- `SCR_PATH`: Directory to search for screenshots (default: "~/Downloads/")
- `MODEL_NAME`: LLM model to use for filename generation
- `CWEBP_CLI_TEMPLATE`: WebP conversion command template

## Example Output

```
Filename suggestions:
1. login-page-design
2. user-authentication
3. web-login-form

Select a number (press Enter for 1): 2
Selected filename: user-authentication
Successfully converted to: /Users/username/Downloads/user-authentication.webp
Input size: 1,245,680 bytes
Output size: 156,432 bytes
Compression ratio: 87.4%
```

## API Key

This script uses OpenRouter API for AI-powered filename generation. You can get a free API key at [openrouter.ai](https://openrouter.ai/).
