import os
import json
import sys
import re
import httpx
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Load environment variables
load_dotenv(os.path.join(os.path.expanduser("~"), ".passkey", ".env"))
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if not GOOGLE_API_KEY:
    print("Error: Missing GOOGLE_API_KEY in .env file")
    sys.exit(1)

# Configure Gemini API
try:
    client = genai.Client(api_key=GOOGLE_API_KEY)
except Exception as e:
    print(f"Error configuring Gemini API: {e}")
    sys.exit(1)


def read_prompt():
    try:
        with open("ipo_financials.txt", "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        print(f"ERROR: Failed to read prompt file: {e}")
        sys.exit(1)


def analyze_pdf_with_gemini(pdf_url):
    """Download and analyze PDF from URL with Gemini AI."""
    try:
        # Read prompt
        prompt = read_prompt()

        # Download the PDF from the URL
        pdf_data = httpx.get(pdf_url).content

        # Generate content using Gemini AI
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            config=types.GenerateContentConfig(temperature=0.5),
            contents=[
                types.Part.from_bytes(data=pdf_data, mime_type='application/pdf'),
                prompt
            ]
        )

        print(response.usage_metadata)

        match = re.search(r"\{.*}", response.text, re.DOTALL)
        if match:
            json_text = match.group(0)
        else:
            print("ERROR: Could not extract JSON from Gemini response.")
            json_text = "{}"

        try:
            return json.loads(json_text)
        except json.JSONDecodeError as e:
            print(f"ERROR: JSON decoding error: {e}")
            return {}

    except Exception as e:
        print(f"ERROR: Gemini processing failed: {e}")
        return {}


def save_json(data, pdf_url):
    filename = os.path.splitext(os.path.basename(pdf_url))[0]
    output_path = os.path.join("json", f"{filename}_financial.json")

    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        print(f"✅ Extraction complete! Data saved to {output_path}")
    except Exception as e:
        print(f"ERROR: Failed to write JSON: {e}")


def extract_pdf_financial(pdf_url):
    print(f"Processing PDF: {pdf_url}")
    extracted_data = analyze_pdf_with_gemini(pdf_url)
    save_json(extracted_data, pdf_url)


if __name__ == "__main__":
    # Example test URL
    test_url = "https://anns.sgp1.cdn.digitaloceanspaces.com/3443412.pdf"
    extract_pdf_financial(test_url)
