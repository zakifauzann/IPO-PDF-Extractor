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
    prompt = f"""
        You are an expert in financial analysis and IPO prospectuses. Your ABSOLUTE TOP PRIORITY is to extract specific information from the provided text and output the response in a STRICTLY VALID JSON format. If information is not found, leave the corresponding field empty or null. You will extract information ONLY from the "Financial Information," "Key Financial Data," "Corporate Information," or similar sections of the IPO prospectus.

        EXTRACT THE FOLLOWING INFORMATION:
        
        Strictly only extract data focusing specifically on the latest Financial Year Ended (FYE) results. Exclude any Financial Period Ended (FPE) data.

        1.  **Profit After Tax (PAT) ['000]**:
            * TYou MUST take values of latest FYE.
            * Ensure all figures are in RM'000 (Ringgit Malaysia thousands).

        2.  **PAT (FYE) List ['000, comma-separated]**:
            * Extract all available PAT values for Financial Year End (FYE).
            * Ensure values are formatted as a comma-separated list.
            * Figures must be in RM'000.

        3.  **PAT (FPE) List ['000, comma-separated]**:
            * Extract all available PAT values for Financial Period End (FPE).
            * Ensure values are formatted as a comma-separated list.
            * Figures must be in RM'000.

        4.  **FPE Period**:
            * Extract the financial period duration.
            * 1 - 12
            * Example: 9

        5.  **PE (Price-to-Earnings Ratio, reported)**:
            * Extract the officially reported PE ratio.
            * Ensure it is represented as a numerical value.

        6.  **PAT Margin [%]**:
            * Extract the PAT margin percentage.
            * Represent as a decimal (e.g., 0.25 for 25%).

        7.  **Total Assets (Pro Forma) ['000]**:
            * Extract total assets under pro forma adjustments.
            * Figures must be in RM'000.

        8.  **Total Liabilities (Pro Forma) ['000]**:
            * Extract total liabilities under pro forma adjustments.
            * Figures must be in RM'000.

        9.  **Total Cash ['000]**:
            * Extract the latest total cash available.
            * Figures must be in RM'000.

        10. **Total Interest-Bearing Borrowings ['000]**:
            * Extract total borrowings that bear interest.
            * Figures must be in RM'000.

        11. **Use of Proceeds**:
            * Extract detailed breakdown of IPO proceeds.
            * For category choose between these: Business Expansion, Debt Repayment, Working Capital, Listing Expenses and Others. 
            * Each entry must include:
                - **Category** (e.g., Expansion, Debt Repayment)
                - **Purpose**
                - **Amount (RM'000)**
                - **Percentage (%)**
                - **Time Frame in numbers (1-100)**

        12. **Executive Directors**:
            * Extract only directors with "Executive" in their title.
            * Each entry must include:
                - **Title**
                - **Name**
                - **Total Remuneration** (sum up salary, bonuses, others if applicable)
                - **Age** (only if explicitly stated, or try to find in text if not available in table; do not estimate)

        13. **Geographical Segments**:
            * Extract total revenue per geographical segment.
            * You MUST take values of latest FYE (search values under the latest FYE year).
            * You MUST use the values of the TOTAL revenues.
            * You MUST calculate the percentage based on the total revenue.
            * If the segment data is not found, return null.
            * Figures must be in RM'000.

        14. **Business Segments**:
            * Extract total revenue per business segment.
            * You MUST take values of latest FYE (search values under the latest FYE year).
            * You MUST use the values of the TOTAL revenues.
            * You MUST calculate the percentage based on the total revenue.
            * If the segment data is not found, return null.
            * Figures must be in RM'000.

        15. **Major Customers**:
        * Extract major customers and their total revenue contribution.
        * Take values of latest FYE.
        * Each entry must include:
            - **Name/Segment**
            - **Total Revenue (RM'000)**
            - **Percentage (%)**
        * If a table states "-" for revenue, consider it null.

        16. **Corporate Structure**:
            * Extract details on subsidiaries and associates.
            * Each entry must include:
                - **Name**
                - **Principal Activities**
                - **Ownership Percentage**
            * Classify ownership as:
                - **Subsidiaries** (own >= 50%)
                - **Associates** (own < 50%)
                
        17. **Sector:**
            * Determine and specify the company's sector and sub sector.
            * Refer to this link for categorization: https://www.bursamalaysia.com/sites/5bb54be15f36ca0af339077a/content_entry5ce3b50239fba2627b2864be/5ce3b5d35b711a163beae1c3/files/BURSA_MALAYSIA_SECTOR_CLASSIFICATION_OF_APPLICANTS_OR_LISTED_ISSUERS_Nov2024.pdf?1736733279
            * Only refer to this link, do not assume anything.

        OUTPUT REQUIREMENTS (MUST BE FOLLOWED EXACTLY):

        *   THE OUTPUT MUST BE A VALID JSON OBJECT. THIS IS YOUR TOP PRIORITY.
        *   Use clear and descriptive keys for each extracted field.
        *   IF A SPECIFIC PIECE OF INFORMATION IS NOT FOUND IN THE TEXT, SET THE CORRESPONDING VALUE TO `null`. DO NOT MAKE UP INFORMATION.
        *   Ensure that numerical values are represented as NUMBERS (e.g., 1234567.89), NOT STRINGS ("1234567.89").
        *   Percentages should be represented as decimals (e.g., 0.25 for 25%).
        *   Arrays should be used to represent lists of items (e.g., a list of Executive Directors).
        *   Include ALL the fields from the example, even if the value is `null`.
    """

    try:
        # Generate content using Gemini AI
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            config=types.GenerateContentConfig(
                temperature=0.3  # Low temperature for consistent outputs, low randomness
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
    pdf_path = os.path.join('msbpdf_abridged.pdf')  # Replace with the actual path to your PDF file

    if not os.path.exists(pdf_path):
        print(f"Error: PDF file '{pdf_path}' not found.")
        sys.exit(1)

    print(f"Processing PDF: {pdf_path}")

    structured_data = analyze_text_with_gemini(pdf_path)

    # Change output file name to match the PDF file name
    pdf_file_name = os.path.splitext(os.path.basename(pdf_path))[0]  # Get PDF file name without extension
    output_file = f"{pdf_file_name}_extracted.json"

    try:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(structured_data, f, indent=4, ensure_ascii=False)  # Ensure UTF-8 encoding
        print(f"Extraction complete! Data saved to {output_file}")
    except Exception as e:
        print(f"ERROR: Error writing to file: {e}")