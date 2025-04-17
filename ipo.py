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


def read_prompt_file(relative_path):
    try:
        base_dir = os.path.dirname(__file__)
        # Go up one level from extractor/
        full_path = os.path.join(base_dir, "..", relative_path)
        with open(full_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        print(f"ERROR: Failed to read prompt file {relative_path}: {e}")
        sys.exit(1)


def analyze_pdf_with_gemini(pdf_url):
    """Analyze PDF with Gemini AI using both prompts."""
    try:
        # Read both prompts
        financial_prompt = read_prompt_file("prompts/ipo_financials.txt")
        proceeds_prompt = read_prompt_file("prompts/ipo_proceeds.txt")

        # Download the PDF from the URL
        pdf_data = httpx.get(pdf_url).content

        # Combined prompt
        full_prompt = (
            "Please extract the following information from the IPO document. "
            "Respond with a single JSON object containing two main keys: "
            "`financials` and `proceeds`.\n\n"
            f"---\n\n[FINANCIALS PROMPT]\n{financial_prompt}\n\n"
            f"[PROCEEDS PROMPT]\n{proceeds_prompt}"
        )

        # Generate content
        response = client.models.generate_content(
            model="gemini-2.5-pro-exp-03-25",
            config=types.GenerateContentConfig(temperature=0.5),
            contents=[
                types.Part.from_bytes(data=pdf_data, mime_type='application/pdf'),
                full_prompt
            ]
        )

        print(response.usage_metadata)

        # Try to extract JSON
        match = re.search(r"\{.*}", response.text, re.DOTALL)
        if not match:
            print("ERROR: Could not extract JSON from Gemini response.")
            return {}

        json_text = match.group(0)
        return json.loads(json_text)

    except json.JSONDecodeError as e:
        print(f"ERROR: JSON decoding error: {e}")
        return {}
    except Exception as e:
        print(f"ERROR: Gemini processing failed: {e}")
        return {}



def save_combined_json(combined_data, pdf_url):
    filename = os.path.splitext(os.path.basename(pdf_url))[0]
    output_dir = os.path.join(os.path.dirname(__file__), "..", "json")  # one level up from extractor/
    os.makedirs(output_dir, exist_ok=True)  # ensure folder exists

    output_path = os.path.join(output_dir, f"{filename}_ipo.json")

    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(combined_data, f, indent=4, ensure_ascii=False)
        print(f"✅ Combined IPO data saved to {output_path}")
    except Exception as e:
        print(f"ERROR: Failed to write combined IPO JSON: {e}")



def extract_pdf_combined(pdf_url):
    print(f"Processing PDF from URL: {pdf_url}")
    combined_data = analyze_pdf_with_gemini(pdf_url)
    save_combined_json(combined_data, pdf_url)


if __name__ == "__main__":
    test_url = "https://anns.sgp1.cdn.digitaloceanspaces.com/3542085.pdf"
    extract_pdf_combined(test_url)
