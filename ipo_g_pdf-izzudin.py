import os
import json
import sys
import re  # Import the regular expression module
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pathlib import Path

# Load environment variables
load_dotenv(os.path.join(os.path.expanduser("~") , ".passkey" , ".env"))
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



def analyze_pdf_with_gemini(pdf_path):
    """Send pdf to Gemini AI and get structured JSON data, with improved error handling."""
    prompt = """
   You are an expert in financial analysis and annual reports. Your ABSOLUTE TOP PRIORITY is to extract specific information from the provided text and output the response in a STRICTLY VALID JSON format. If information is not found, leave the corresponding field empty or null.
 You are an expert in financial analysis and annual reports. Your ABSOLUTE TOP PRIORITY is to extract specific information from the provided text and output the response in a STRICTLY VALID JSON format. If information is not found, leave the corresponding field empty or null.

EXTRACT THE FOLLOWING INFORMATION: 

    1. Use of proceeds 
        - might be stated as "utilisation of proceeds" or similar.

    2. **Executive Directors**: (title, name, age, and total remuneration (salary, bonuses, other compensation, if available)).
        *   If age is not explicitly stated, do not include it.
        *   For salary, if there are multiple sources of remuneration (e.g., from the company and a group entity), sum all applicable amounts and report the total remuneration. Specify the currency.
        *   If total remuneration is not available or cannot be reliably calculated, set the `total_remuneration` to `null`.
        *   Include Chairman, Managing Director, CEO,COO, CFO and Exceutive Directors. Ignore Non-Executive Directors

    3. **Geographical Segments/Geographical Information**: (name, total revenue, and percentage of total revenue).   Strictly only extract data for the latest FYE (Ignore FPE)
    *   Strictly only extract data focusing specifically on the latest Financial Year Ended (FYE) results. Exclude any Financial Period Ended (FPE) data.
        *   Extract data ONLY from the "Geographical Segments" or "Geographical Information" section within the "Notes To The Financial Statements."
        *   Extract the revenue by geographical location from the annual report. This information is typically located in the notes to the financial statements, often under a section titled "Segment Reporting," "Operating Segments," or "Geographical Segments."
        *   The revenue should be broken down by geographical regions, and the values are expected to be in RM'000
        *   Extract directly from table rows if the data is presented in a table format.
        *   **CRITICAL:** If a table with geographical segments information is absent in the "Notes To The Financial Statements", set the entire "Geographical Segments" value to `null`. Do NOT use information from other sections of the report.
        *   Ignore rows or segments marked with "-". If a segment is ignored, do not include the corresponding key-value pair.

    4. **Business Segments**: (name, external revenue, total revenue, and percentage of total revenue).   Strictly only extract data for the latest FYE (Ignore FPE)
    *   Strictly only extract data focusing specifically on the latest Financial Year Ended (FYE) results. Exclude any Financial Period Ended (FPE) data.
        *   From the "Segment Information" table in the "Notes to the Financial Statements" section, extract the total revenue for each business segment. List each business segment along with its corresponding total revenue per segment. 
        *   Get the total revenue per business segment as well, total revenue is usually situated below the external revenue
        *   The values are expected to be in RM'000 , note the currency used in the currency_unit
        *   **CRITICAL:** You MUST find a section titled "Business Segments," "Business Information," or "Segment Information" in the "Notes To The Financial Statements" section of the annual report.
        *   **AVOID**: Do NOT use numbers from *Review of Performance* or *Review of Financial Performance*.
        *   Treat "-" as 0 (zero). If a business segment has zero revenue, represent the revenue as `0` (a number) and the percentage as `0.0` (a number).

    5.  **Major Customers**: (name, total revenue, year and percentage). "-" in the table means no revenue available for that year. Count as null. If the revenue for the current year is not available or not present in the table, also count as null.
    *   Strictly only extract data focusing specifically on the latest Financial Year Ended (FYE) results. Exclude any Financial Period Ended (FPE) data.
        *   get the latest FYE numbers. Ignore FPE 

    6. **Corporate Structure**: (information from *INVESTMENT IN SUBSIDIARIES*, *SUBSIDIARIES, ASSOCIATES AND JOINT VENTURES*, *SUBSIDIARIES*, or related sections)
        *   **Subsidiaries (ownership >= 50%)**: Extract name, principal activities, and ownership percentage (as a number from 1 to 100).
        *   **Associates (ownership < 50%)**: Extract name, principal activities, and ownership percentage (as a number from 1 to 100).
        *   **Subsidiaries/Associates (Unknown ownership)**: Extract name and principal activities.
   
OUTPUT REQUIREMENTS (MUST BE FOLLOWED EXACTLY):

*   THE OUTPUT MUST BE A VALID JSON OBJECT.  THIS IS YOUR TOP PRIORITY.
*   Use clear and descriptive keys for each extracted field.
*   IF A SPECIFIC PIECE OF INFORMATION IS NOT FOUND IN THE TEXT, SET THE CORRESPONDING VALUE TO `null`. DO NOT MAKE UP INFORMATION.
*   Ensure that numerical values are represented as NUMBERS (e.g., 1234567.89), NOT STRINGS ("1234567.89"). Percentages should be numbers (e.g., 25.0 for 25%).
*   Arrays should be used to represent lists of items (e.g., a list of Executive Directors).
*   Include ALL the fields/keys from the example structure (provided below, or in previous turns), even if the value is `null`. This maintains a consistent JSON structure.
        {
        "executive_directors": [
            {
            "title": "Chief Executive Officer",
            "name": "Alice Johnson",
            "age": 55,
            "remuneration": {
                "salary": 1200000,
                "directorFees": 30000,
                "meetingAllowance": 2500,
                "otherEmoluments": 230623
                },
            "total remuneration" : 1463123
            "remuneration_currency_unit":"RM"
            },
    
        ],
        "geographical_segments": [
            {
            "segment": "Malaysia",
            "total_revenue": 500000000.00,
            "percentage": 0.60
            },
            {
            "segment": "Thailand",
            "total_revenue": 250000000.00,
            "percentage": 0.30
            },
            {
            "segment": "China",
            "total_revenue": 83333333.33,
            "percentage": 0.10
            }
        ],
        "business_segments": [
            {
            "segment": "Software",
            "total_revenue" : 4500000.00,
            "currency_unit" : "RM'000",
            "percentage": 0.48
            },
            {
            "segment": "Manufacturing",
            "total_revenue": 350000000.00,
            "currency_unit" : "RM'000",
            "percentage": 0.42
            }
        ],
        "major_customers": [
            {
            "customer name": "Customer 2",
            "segment" : "construction"
            "total_revenue": 0,
            "currency_unit" : "RM'000"
            "percentage": 0,
            },
            {
            "customer name": "Customer C",
            "segment" : "construction"
            "total_revenue": 75000000.00,
            "currency_unit" : "RM'000"
            "percentage": 0.09,
            }
        ],
        "corporate_structure": {
            "subsidiaries": [
            {
                "name": "Alpha Ltd",
                "principal_activities": "Software Development",
                "ownership_percentage": 0.80
            },
            {
                "name": "Gamma Corp",
                "principal_activities": "Hardware Manufacturing",
                "ownership_percentage": 1.00
            }
            ],
            "associates": [
            {
                "name": "Delta Inc",
                "principal_activities": "Research and Development",
                "ownership_percentage": 0.30
            }
            ],
            "unknown_ownership": [
            {
                "name": "Epsilon Group",
                "principal_activities": "Marketing and Sales"
            }
            ]
        },
         
        "use_of_proceeds": [
            {
            "purpose" : "reconstruction_of_a_new_factory_cum_warehouse"
            "amount": 4974000,
            "percentage": 18.7
            },
            {
            "purpose" : "purchase_of_new_machinery_and_equipment"
            "amount": 6005000,
            "percentage": 22.58 
            }        
        ]
  
    }
    """

    try:
        # Generate content using Gemini AI
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            config=types.GenerateContentConfig(
                temperature=0.6 # Low temperature for consistent outputs, low randomness
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


def save_json(structured_data, pdf_path, calc_flag = False):
    # Change output file name to match the PDF file name
    pdf_file_name = os.path.splitext(os.path.basename(pdf_path))[0]  # Get PDF file name without extension
    output_file = os.path.join("json" , f"{pdf_file_name}.json")

    try:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(structured_data, f, indent=4, ensure_ascii=False)  # Ensure UTF-8 encoding
        print(f"Extraction complete! Data saved to {output_file}")
    except Exception as e:
        print(f"ERROR: Error writing to file: {e}")
    

if __name__ == "__main__":
    # Specify the PDF path here:
    pdf_path = os.path.join("pdf", "msbpdf.pdf")  # Replace with the actual path to your PDF file

    if not os.path.exists(pdf_path):
        print(f"Error: PDF file '{pdf_path}' not found.")
        sys.exit(1)

    print(f"Processing PDF: {pdf_path}")

    # save data from AI
    structured_data = analyze_pdf_with_gemini(pdf_path)
    save_json(structured_data , pdf_path)

