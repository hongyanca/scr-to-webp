#!/usr/bin/env python3
import requests
import json
import base64
import os
import glob
import subprocess
from pathlib import Path

MODEL_NAME = "google/gemma-3-27b-it:free"
PROMPT_GEN_FILENAME = """
You are an AI tasked with generating a concise, meaningful filename for a screenshot. Analyze the content of the screenshot and create a filename that:
- Reflects the main subject or purpose of the screenshot.
- Uses all lowercase letters.
- Separates words with hyphens ("-").
- Is brief (aim for 3-5 words, max 30 characters).
- Avoids special characters unless essential.
- Output at least two options but no more then four options.
- Output format is json, nothing but json. Do NOT put reasonings in the output.
Example: For a screenshot of a login page, the filename might be "login-page" or "login-new-user". The output looks like:
{
    "filenames": ["login-page", "login-new-user"]
}
Based on the provided screenshot, generate a single filename that meets these criteria.
"""
SCR_PATH = "~/Downloads/"
CWEBP_CLI_TEMPLATE = "cwebp -q 80 {input} -o {output}"


def get_scr_img_path(search_path):
    """Return absolute path of the newest .png file starts with 'SCR-' in search_path"""
    expanded_path = os.path.expanduser(search_path)
    pattern = os.path.join(expanded_path, "SCR-*.png")
    files = glob.glob(pattern)
    
    if not files:
        return None
    
    # Sort by modification time, newest first
    newest_file = max(files, key=os.path.getmtime)
    return os.path.abspath(newest_file)


def encode_image_to_base64(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def get_screenshot_data_url(search_path):
    """Find newest SCR- screenshot and return as data URL, or None if not found"""
    image_path = get_scr_img_path(search_path)
    if image_path is not None:
        base64_image = encode_image_to_base64(image_path)
        return f"data:image/png;base64,{base64_image}"
    return None


def llm_gen_filename(search_path):
    """Generate filename suggestions using LLM for newest screenshot in search_path"""
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {"Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}", "Content-Type": "application/json"}
    
    # Get screenshot data URL
    data_url = get_screenshot_data_url(search_path)
    
    if data_url is None:
        return None
    
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": PROMPT_GEN_FILENAME},
                {"type": "image_url", "image_url": {"url": data_url}},
            ],
        }
    ]
    
    payload = {"model": MODEL_NAME, "messages": messages}
    
    response = requests.post(url, headers=headers, json=payload)
    return response.json()


def extract_filenames(llm_response):
    """Extract filenames from LLM response content and return as dict"""
    if not llm_response or 'choices' not in llm_response:
        return None
    
    try:
        content = llm_response['choices'][0]['message']['content']
        # Remove markdown code block markers if present
        if '```json' in content:
            content = content.split('```json')[1].split('```')[0]
        elif '```' in content:
            content = content.split('```')[1].split('```')[0]
        
        # Parse JSON content
        parsed_json = json.loads(content.strip())
        return parsed_json
    except (KeyError, IndexError, json.JSONDecodeError):
        return None


def select_filename(filenames_dict):
    """Display filename options and get user selection"""
    if not filenames_dict or 'filenames' not in filenames_dict:
        return None
    
    filenames = filenames_dict['filenames']
    if not filenames:
        return None
    
    print("\nAI-generated filename suggestions:")
    for i, filename in enumerate(filenames, 1):
        print(f"  {i}. {filename}")
    
    try:
        user_input = input(f"\nChoose an option (1-{len(filenames)}) or enter custom filename [default: 1]: ").strip()
        
        if not user_input:
            return filenames[0]
        
        # Try to parse as number first
        try:
            selection = int(user_input)
            if 1 <= selection <= len(filenames):
                return filenames[selection - 1]
            else:
                print(f"Invalid selection ({selection}), using first option.")
                return filenames[0]
        except ValueError:
            # If not a number, treat as custom filename
            custom_filename = user_input.lower().replace(' ', '-')
            print(f"Using custom filename: {custom_filename}")
            return custom_filename
            
    except (ValueError, KeyboardInterrupt):
        print("Using first option.")
        return filenames[0]


def compress_image_webp(image_path, selected_filename):
    """Convert PNG to WebP using cwebp CLI tool"""
    if not image_path or not selected_filename:
        return None
    
    # Get the directory of the input image
    input_dir = os.path.dirname(image_path)
    
    # Create output path with .webp extension
    output_path = os.path.join(input_dir, f"{selected_filename}.webp")
    
    # Get input file size
    input_size = os.path.getsize(image_path)
    
    # Format the CLI command
    command = CWEBP_CLI_TEMPLATE.format(input=image_path, output=output_path)
    
    try:
        # Run the command
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        
        # Get output file size
        output_size = os.path.getsize(output_path)
        
        # Calculate compression ratio
        compression_ratio = (1 - output_size / input_size) * 100
        
        print(f"Successfully converted to: {output_path}")
        print(f"Input size: {input_size:,} bytes")
        print(f"Output size: {output_size:,} bytes")
        print(f"Compression ratio: {compression_ratio:.1f}%")
        
        return output_path
    except subprocess.CalledProcessError as e:
        print(f"Error converting image: {e}")
        return None


def main():
    response = llm_gen_filename(SCR_PATH)
    filenames = extract_filenames(response)
    selected_filename = select_filename(filenames)
    print(f"Selected filename: {selected_filename}")
    image_path = get_scr_img_path(SCR_PATH)
    if image_path and selected_filename:
        compress_image_webp(image_path, selected_filename)
    
    
if __name__ == "__main__":
    main()
