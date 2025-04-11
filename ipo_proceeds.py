import os
import json
import sys
import re
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pathlib import Path

# Load environment variables
load_dotenv(os.path.join(os.path.expanduser("~"), ".passkey", ".env"))
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")  # Using GOOGLE_API_KEY

if not GOOGLE_API_KEY:
    print("Error: Missing GOOGLE_API_KEY in .env file")
    sys.exit(1)

# Configure Gemini API
try:
    client = genai.Client(api_key=GOOGLE_API_KEY)
except Exception as e:
    print(f"Error configuring Gemini API: {e}")
    sys.exit(1)


def analyze_text_with_gemini(pdf_path):
    """Send extracted text to Gemini AI and get structured JSON data, with improved error handling."""


    try:
        # Generate content using Gemini AI
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            # gemini-2.5-pro-exp-03-25 can get pretty accurate results
            # 0.3 temperature
            config=types.GenerateContentConfig(
                temperature=0.3 # Low temperature for consistent outputs, low randomness
            ),
            contents=[
                types.Part.from_bytes(
                    data=Path(pdf_path).read_bytes(),
                    mime_type='application/pdf',
                ),
                prompt
            ]
        )

        print(response.usage_metadata)
        # Extract JSON using regex to handle extra text
        match = re.search(r"\{.*}", response.text, re.DOTALL)
        if match:
            json_text = match.group(0)
        else:
            print("ERROR: Could not extract JSON from Gemini response.")
            json_text = "{}"

        # Parse JSON
        try:
            json_data = json.loads(json_text)
            return json_data

        except json.JSONDecodeError as e:
            print(f"ERROR: JSON decoding error: {e}")
            return {}

    except Exception as e:
        print(f"ERROR: Gemini processing failed: {e}")
        return {}


if __name__ == "__main__":
    # Specify the PDF path here:
    pdf_path = os.path.join('pdf/cuckoo.pdf')  # Replace with the actual path to your PDF file

    if not os.path.exists(pdf_path):
        print(f"Error: PDF file '{pdf_path}' not found.")
        sys.exit(1)

    print(f"Processing PDF: {pdf_path}")

    structured_data = analyze_text_with_gemini(pdf_path)

    # Change output file name to match the PDF file name
    pdf_file_name = os.path.splitext(os.path.basename(pdf_path))[0]  # Get PDF file name without extension
    output_file = f"json/{pdf_file_name}_extracted.json"

    try:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(structured_data, f, indent=4, ensure_ascii=False)  # Ensure UTF-8 encoding
        print(f"Extraction complete! Data saved to {output_file}")
    except Exception as e:
        print(f"ERROR: Error writing to file: {e}")