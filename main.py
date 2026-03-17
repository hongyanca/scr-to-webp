#!/usr/bin/env python3
import requests
import json
import base64
import os
import glob
import subprocess
import sys
# from pathlib import Path

# MODEL_NAME = "gemini-2.5-flash"
MODEL_NAME = "gemini-3.1-flash-lite-preview"
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
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent"


def display_path(path):
    """Render paths under the home directory using ~ for display."""
    home_dir = os.path.expanduser("~")
    abs_path = os.path.abspath(path)
    if abs_path == home_dir:
        return "~"
    if abs_path.startswith(home_dir + os.sep):
        return abs_path.replace(home_dir, "~", 1)
    return abs_path


def get_scr_img_path(search_path=None, explicit_path=None):
    """Return absolute path for an explicit file or the newest SCR-*.png from known locations."""
    if explicit_path:
        candidate = os.path.abspath(os.path.expanduser(explicit_path))
        if os.path.isfile(candidate):
            return candidate
        return None

    search_paths = []
    if search_path:
        search_paths.append(os.path.expanduser(search_path))
    search_paths.append(os.getcwd())

    files = []
    for base_path in search_paths:
        pattern = os.path.join(base_path, "SCR-*.png")
        files.extend(glob.glob(pattern))

    if not files:
        return None

    # Sort by modification time, newest first
    newest_file = max(files, key=os.path.getmtime)
    return os.path.abspath(newest_file)


def encode_image_to_base64(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def get_screenshot_inline_part(search_path=None, explicit_path=None):
    """Find screenshot and return a Gemini inline_data part, or None if not found."""
    image_path = get_scr_img_path(search_path=search_path, explicit_path=explicit_path)
    if image_path is not None:
        base64_image = encode_image_to_base64(image_path)
        return {"inline_data": {"mime_type": "image/png", "data": base64_image}}
    return None


def llm_gen_filename(search_path=None, explicit_path=None):
    """Generate filename suggestions using LLM for newest screenshot in search_path"""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("LLM request failed: GEMINI_API_KEY is not set")
        return None

    headers = {"x-goog-api-key": api_key, "Content-Type": "application/json"}

    image_part = get_screenshot_inline_part(search_path=search_path, explicit_path=explicit_path)

    if image_part is None:
        return None

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": PROMPT_GEN_FILENAME},
                    image_part,
                ]
            }
        ]
    }

    try:
        response = requests.post(GEMINI_API_URL, headers=headers, json=payload, timeout=30)
        if not response.ok:
            try:
                error_payload = response.json()
            except ValueError:
                error_payload = {"raw_body": response.text}

            print(f"LLM request failed: HTTP {response.status_code}")
            print(json.dumps(error_payload, indent=2))
            return None

        return response.json()
    except requests.RequestException as e:
        print(f"LLM request failed: {e}")
        return None


def extract_filenames(llm_response):
    """Extract filenames from LLM response content and return as dict"""
    if not llm_response or "candidates" not in llm_response:
        return None

    try:
        parts = llm_response["candidates"][0]["content"]["parts"]
        content = "".join(part.get("text", "") for part in parts)
        # Remove markdown code block markers if present
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        # Parse JSON content
        parsed_json = json.loads(content.strip())
        return parsed_json
    except (KeyError, IndexError, json.JSONDecodeError):
        return None


def select_filename(filenames_dict):
    """Display filename options and get user selection"""
    if not filenames_dict or "filenames" not in filenames_dict:
        return None

    filenames = filenames_dict["filenames"]
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
            custom_filename = user_input.lower().replace(" ", "-")
            print(f"Using custom filename: {custom_filename}")
            return custom_filename

    except (ValueError, KeyboardInterrupt):
        print("Using first option.")
        return filenames[0]


def default_filename_for_image(image_path):
    """Fallback filename when LLM suggestions are unavailable."""
    stem = os.path.splitext(os.path.basename(image_path))[0].lower()
    return stem.replace(" ", "-")


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
        _ = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)

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
    explicit_path = sys.argv[1] if len(sys.argv) > 1 else None
    print(f"LLM Model: {MODEL_NAME}")
    image_path = get_scr_img_path(search_path=SCR_PATH, explicit_path=explicit_path)
    if image_path is None:
        print("No input image found. Pass a file path or place an SCR-*.png in the current directory or ~/Downloads.")
        return

    print(f"Using image: {display_path(image_path)}")
    response = llm_gen_filename(search_path=SCR_PATH, explicit_path=explicit_path)
    filenames = extract_filenames(response)
    selected_filename = select_filename(filenames)
    if selected_filename is None:
        selected_filename = default_filename_for_image(image_path)
        print(f"Falling back to filename: {selected_filename}")
    print(f"Selected filename: {selected_filename}")
    if image_path and selected_filename:
        compress_image_webp(image_path, selected_filename)


if __name__ == "__main__":
    main()
