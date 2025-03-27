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
        You are an expert in financial analysis and IPO prospectuses. 
        Your ABSOLUTE TOP PRIORITY is to extract specific information from the provided text and output the response in a STRICTLY VALID JSON format. 
        If information is not found, leave the corresponding field empty or null. Do not calculate or assume any values unless explicitly stated. 
        You will extract information ONLY from the "Business Overview", "Financial Information," "Key Financial Data," "Corporate Information," "Operating Segments", or similar sections of the IPO prospectus.

        EXTRACT THE FOLLOWING INFORMATION:
        
        Strictly only extract data focusing specifically on the latest Financial Year Ended (FYE) results. Exclude any Financial Period Ended (FPE) data. Be careful of unit used in the document, for example RM'000 or RM Million or just simply RM (round off to become RM'000).

        1.  **Geographical Segments**:
            * Extract total revenue per geographical segment.
            * You MUST take values of latest FYE or Financial Year Ended (extract values under the latest FYE year). Do not mistake for latest year of FPE.
            * You MUST use the values of the TOTAL revenues.
            * You MUST calculate the percentage based on the total revenue.
            * Ensure the percentage is presented in a standard format (e.g., 98.83% instead of 0.9883).
            * If the segment data is not found, return null.
            * Figures must be in RM'000.

        2.  **Business Segments**:
            * Extract total revenue per business segment.
            * You MUST take values of latest FYE or Financial Year Ended (extract values under the latest FYE year). Do not mistake for latest year of FPE.
            * You MUST use the values of the TOTAL revenues.
            * You MUST calculate the percentage based on the total revenue.
            * Ensure the percentage is presented in a standard format (e.g., 98.83% instead of 0.9883).
            * If the segment data is not found, return null.
            * Figures must be in RM'000.

        3.  **Major Customers**:
            * Extract major customers and their total revenue contribution.
            * Take values of latest FYE.
            * Each entry must include:
                - **Name/Segment**
                - **Total Revenue (RM'000)**
                - **Percentage (%)**.
            * If a table states "-" for revenue, consider it null.

        4.  **Corporate Structure**:
            * Extract details on subsidiaries and associates.
            * Each entry must include:
                - **Name**
                - **Principal Activities**
                - **Ownership Percentage**.
            * Classify ownership as:
                - **Subsidiaries** (own >= 50%)
                - **Associates** (own < 50%)
                
        5.  **Sector:**
            * Identify the company's sector and sub-sector based on Bursa Malaysia's classification (below). 
            * Locate the most relevant keywords in the document rr the most mentioned in the document to support your classification. 
            * Provide a brief explanation for your choice.
            * If no sub-sector is found, state it explicitly—do not assume.
            * Use the reference table below and avoid making assumptions.
            
            Sector              Sub Sector          Definition
            ------------------------------------------------------------------------------------------------------------
            1                   1.1                 Companies engaged in the construction of commercial and
            CONSTRUCTION        CONSTRUCTION        residential buildings, infrastructure such as railways, highways,
                                                    roads and providers of building construction-related services
                                                    such as architects, interior design
            
            2                   2.1                 Companies that raise livestock and operate fisheries. Includes
            CONSUMER            AGRICULTURAL        manufacturers of livestock feeds
            PRODUCTS &          PRODUCTS
            SERVICES
                                2.2                 Companies that produce and distribute passenger automobiles
                                AUTOMOTIVE
            
                                2.3                 Businesses not covered in the other prescribed sub sectors
                                CONSUMER            under Consumer Products & Services
                                SERVICES
            
                                2.4                 Food or beverages producers including packaged foods, dairy
                                FOOD/BEVERAGES      products, brewers, soft drinks
            
                                2.5                 Manufacturers and distributors of household products including
                                HOUSEHOLD GOODS     furniture, kitchenware, consumer electronics
            
                                2.6                 Manufacturers and distributers of personal products including
                                PERSONAL GOODS      textiles, apparel, footwear, jewellery, timepieces, accessories,
                                                    cosmetics, personal care, tobacco
            
                                2.7                 Owners and operators of retail stores including direct marketing
                                RETAILERS
            
                                2.8                 Companies providing travel and tourism related services
                                TRAVEL, LEISURE &   includes airlines, gambling, hotels, restaurants and recreational
                                HOSPITALITY         services
            
            3                   3.1                 Suppliers of equipment and services to oil and gas producers
            ENERGY              ENERGY              such as drilling, exploration, platform construction
                                INFRASTRUCTURE,
                                EQUIPMENT &
                                SERVICES
            
                                3.2                 Companies engaged in the exploration and production of oil and
                                OIL & GAS           gas
                                PRODUCERS
            
                                3.3                 Companies that produce alternative energy including alternative
                                OTHER ENERGY        fuels
                                RESOURCES
            
                                3.4                 Companies that provide equipment and services involved in
                                RENEWABLE ENERGY    producing renewable energy
            
            ------------------------------------------------------------------------------------------------------------
            
            Sector              Sub Sector          Definition
            ------------------------------------------------------------------------------------------------------------
            4                   4.1                 Banks providing a broad range of financial services, including
            FINANCIAL           ΒΑΝΚING             retail banking, loans and money transmissions
            SERVICES
        
                                4.2                 Insurance companies with products in life, health, property and
                                INSURANCE           casualty insurance, takaful
            
                                4.3                 Companies engaged in financial activities not specified
                                OTHER               elsewhere, include stock exchanges, securities, asset
                                FINANCIALS          management companies and other service providers to financial
                                                    institutions
            
            5                   5.1                 Manufacturers and distributors of health care equipment and
            HEALTH CARE         HEALTH CARE         providers of health care services includes lab testing services,
                                EQUIPMENT &         dialysis centers
                                SERVICES
            
                                5.2                 Owners and operators of health care facilities including
                                HEALTH CARE         hospitals, clinics, nursing homes, rehabilitation centres
                                PROVIDERS
            
                                5.3                 Companies engaged in the research, development, production
                                PHARMACEUTICALS     or distribution of pharmaceuticals
            
            6                   6.1                 Manufacturers and distributors of parts and accessories for
            INDUSTRIAL          AUTO PARTS          automobiles and motorcycles such as tires, batteries, engines
            PRODUCTS &
            SERVICES
            
                                6.2                 Manufacturers and wholesalers of building materials including
                                BUILDING            cement, concrete, tiles and paint
                                MATERIALS
            
                                6.3                 Companies that primarily produce and distribute chemicals for
                                CHEMICALS           industry use. Includes plastics and rubber in their raw form or
                                                    molded plastic products, polymers, adhesives, dyes, coatings
                                                    and other chemicals for specialised applications
            
                                6.4                 Diversified companies with business activities in three or more
                                DIVERSIFIED         sectors of which none contributes substantial revenue
                                INDUSTRIALS
            
                                6.5                 Manufacturers and distributors of heavy machinery and
                                INDUSTRIAL          engineering equipment
                                ENGINEERING
            
                                6.6                 Manufacturers and distributors of industrial machinery and
                                INDUSTRIAL          components which includes machine tools, castings and
                                MATERIALS,          moulding equipment, presses, compressors, elevators and
                                COMPONENTS &        escalators
                                EQUIPMENT
            
            ------------------------------------------------------------------------------------------------------------
            
            Sector              Sub Sector              Definition
            ------------------------------------------------------------------------------------------------------------
            7                   6.7                 Businesses not covered in the other prescribed sub sectors
            PLANTATION          INDUSTRIAL          under Industrial Products & Services
                                SERVICES
            
                                6.8                 Producers and traders of metals and metal products which
                                METALS              includes iron, aluminium and steel
            
                                6.9                 Manufacturers & distributors of paper, containers, cardboard,
                                PACKAGING           bags, boxes and cans used for packaging
                                MATERIALS
            
                                6.10                Manufacturers and distributors of timber and related wood
                                WOOD AND WOOD       products
                                PRODUCTS
            
            8                   7.1                 Companies engaged in the cultivation, planting and/or replanting
            PROPERTY            PLANTATION          of crops
            
                                8.1                 Companies that invest in real estate through development,
                                PROPERTY            investment and ownership including real estate service providers
                                                    such as real estate brokers, agencies, leasing companies,
                                                    management companies and advisory services
            
            9                   9.1                 Real estate investment trusts that focus investment in a portfolio
            REAL ESTATE         REAL ESTATE         of income-generating properties such as shopping malls, hotels,
            INVESTMENT          INVESTMENT          offices and service apartments
            TRUSTS              TRUSTS
            
            10                  10.1                Companies providing internet-related services such as Internet
            TECHNOLOGY          DIGITAL             access providers, search engines and providers of website
                                SERVICES            design, web hosting and e-mail services including companies
                                                    that provide solutions and platforms for e-commerce or
                                                    electronic payments
            
                                10.2                Companies engaged in the manufacturing and distribution of
                                SEMICONDUCTORS      semiconductors and semiconductor equipment
            
                                10.3                Companies engaged in developing and producing software
                                SOFTWARE            designed for specialised application such as systems software,
                                                    enterprise and technical software, mobile application
            
                                10.4                Manufacturers and distributors of technology hardware and
                                TECHNOLOGY          equipment such as computers, servers, mainframes,
                                EQUIPMENT           workstations and related peripherals such as mass-storage
                                                    drives, motherboards, monitors, keyboards, printers, smartcards
            
            -----------------------------------------------------------------------------------------------------
            
            Sector              Sub Sector          Definition
            -----------------------------------------------------------------------------------------------------
            11                  11.1                Companies providing advertising, public relations and marketing
            TELECOMMUNICATIONS  MEDIA               services includes producers, operators and broadcasters of
            & MEDIA                                 radio, television, music and filmed entertainment, publishers of
                                                    information via printed or electronic media
            
                                11.2                Producers and distributors of telecommunication equipment
                                TELECOMMUNICATIONS  such as satelites, LANs, WANs, routers, mobile telephones,
                                EQUIPMENT           fibers optics, teleconferencing equipment
            
                                11.3                Providers of mobile and fixed-line telecommunication networks
                                TELECOMMUNICATIONS  and providers of satelite and wireless data communication
                                SERVICE             solutions and related services
                                PROVIDERS
            
            12                  12.1                Companies providing transportation services including
            TRANSPORTATION      TRANSPORTATION      companies that manage airports, train depots, ports and
            & LOGISTICS         & LOGISTICS         providers of courier and logistic services
                                SERVICES
            
                                12.2                Manufacturers and distributors of transportation equipment
                                TRANSPORTATION      includes shipbuilding
                                EQUIPMENT
            
            13                  13.1                Companies that produce or distribute electricity
            UTILITIES           ELECTRICITY
            
                                13.2                Companies providing water or distribute gas to end-users or
                                GAS, WATER &        utility companies with significant presence in more than one
                                MULTI-UTILITIES     utility
            
                                13.3                Companies that produce or distribute electricity through a
                                RENEWABLE ENERGY    renewable energy source
                                ELECTRICITY
            
            14                  14.1                Close-ended investment entities
            CLOSED END FUND     CLOSED END FUND
            
            15                  15.1                Special purpose acquisition companies
            SPECIAL             SPECIAL
            PURPOSE             PURPOSE
            ACQUISITION         ACQUISITION
            COMPANY             COMPANY
            
            16                  16.1                Conventional fixed income securities that are listed and traded
            BOND                CONVENTIONAL-MGS    on the stock market
            CONVENTIONAL
            
                                16.2                Conventional fixed income securities that are listed and traded
                                CONVENTIONAL-GG     on the stock market
            
                                16.3                Conventional fixed income securities that are listed and traded
                                CONVENTIONAL-PDS    on the stock market
            
            ------------------------------------------------------------------------------------------------------------

            Sector              Sub Sector          Definition
            ------------------------------------------------------------------------------------------------------------
            17                  17.1                Shariah Compliant fixed income securities that are listed and
            BOND ISLAMIC        ISLAMIC-GII         traded on the stock market
            
                                17.2                Shariah Compliant fixed income securities that are listed and
                                ISLAMIC-GG          traded on the stock market
            
                                17.3                Shariah Compliant fixed income securities that are listed and
                                ISLAMIC-PDS         traded on the stock market
            
            18                  18.1                Open-ended investment entities
            EXCHANGE            COMMODITY FUND
            TRADED FUND-
            COMMODITY
            
            19                  19.1                Open-ended investment entities
            EXCHANGE            EQUITY FUND
            TRADED FUND-
            EQUITY
            
            20                  20.1                Open-ended investment entities
            EXCHANGE            BOND FUND
            TRADED FUND-
            BOND
            
            21                  21.1                Business enterprises that are set up as trust, instead of
            BUSINESS            BUSINESS TRUST      companies. They are hybrid structures with elements of both
            TRUST                                   companies and trusts and created by a trust deed

        6.  **Additional Sector**

            * The sectors below are not part of Bursa Malaysia’s classification.
            * Locate the most relevant keywords in the document rr the most mentioned in the document to support your classification. 
            * Identify and classify them as additional sectors.
            * Provide a brief explanation for each classification, including the reason for your choice.
            
            "Automotive", "Blue Chip", "Construction", "Consumer Products", "Food & Beverages", "Financial Services", "Healthcare",
            "Industrials Products", "Infrastructure (IPC)", "Media", "Oil & Gas", "Plantation", "Plastics", "Power Utilities",
            "REITs", "Retailers", "Rubber Gloves", "Shipping Ports", "Exports", "Steel", "Technology", "Telco",
            "Trading & Services", "Water Utilities", "Wooden Products", "Sarawak", "Internet of Things (IoT)", "Gold",
            "Poultry & Eggs", "Property", "Hotels", "Sugar & Flour", "GLCs", "Upstream Oil & Gas", "Midstream Oil & Gas",
            "Downstream Oil & Gas", "Big Brands F&B", "Courier Service", "Tan Sri Syed Mokhtar Al-Bukhary", "Mid Cap", "Small Cap",
            "Highway", "Micro Cap", "F4GBM", "Green Tech", "Stationery", "All Stocks", "Logistics",
            "Petrol Refiners and Distributors", "ETF", "Asset Management Service", "Copper Product", "Brewery",
            "Computer Peripheral", "Condom", "Building Materials", "Crane", "Drinking Water", "Engineering Service",
            "Fire Service", "Gaming", "Gas", "Office Products", "Jewellery", "Travel, Leisure & Hospitality", "M&E",
            "Marine Operation & Chartering", "Polymer", "Agricultural Products", "Aluminium", "Apparels", "Speaker Systems",
            "Auto Parts", "Automotive Battery", "Aviation", "Cements", "Education", "Electronic", "Furniture",
            "Medical Service & Equipment", "Chemicals", "Banking", "IT Solutions/ IT Product", "Metals", "Petrochemicals",
            "Palm Oil Machineries", "Packaging", "Papers", "Pharmaceuticals", "Plastic Product (Consumer)",
            "Plastic Product (Precision Manufacturing)", "Ports", "Manufacturing", "Publication & Printing", "Rubber Plantations",
            "Rubber Products", "Semiconductors", "Stone & Quarry", "Tins", "Transportations", "Penny Stocks", "Aerospace",
            "Coffee", "Malaysian Steel", "Small & Mid Cap*", "FBMKLCI", "MSCI", "F4GBM Shariah",
            "Newly Classified Shariah Non-Compliant Securities", "Newly Classified Shariah-Compliant Securities",
            "Payment Products", "PN17", "Automation", "LED", "E&E", "Integrated Facilities Management", "IPO", "Personal Goods",
            "Health Care Equipment & Services", "Coronavirus", "Industrial Materials, Components & Equipment",
            "Industrial Products & Services", "Electronic Manufacturing Services (EMS)", "Industrial Engineering", "Energy",
            "Energy Infrastructure, Equipment & Services", "Consumer Products & Services", "Packaging Materials",
            "Digital Services", "Software", "Transportation & Logistics", "Transportation Equipment",
            "Transportation & Logistics Services", "5G", "Stock Brokers", "Consumer Services", "Household Goods",
            "Diversified Industrials", "Industrial Services", "Cloud Managed Services", "Wood & Wood Products",
            "Technology Equipment", "Insurance", "Other Financials", "Oil & Gas Producers", "Other Energy Resources",
            "Health Care Providers", "Telecommunications & Media", "Telecommunications Equipment",
            "Telecommunications Service Providers", "Utilities", "Electricity", "Gas, Water & Multi-Utilities", "Dry Bulk Carrier",
            "Integrated Immigration System", "Solar", "Timbers", "Cocoa", "OSAT", "Donald Trump", "Joe Biden", "Budget 2021",
            "Work-from-Home (WFH)", "Conglomerates", "Vaccine", "Solar EPCC", "LRT3", "ATE", "Factory Automation",
            "Container Ship Owner", "Freight Forwarding", "Warehousing", "Prime Movers & Trailers", "Electric Vehicles",
            "EV Charger", "Precision Machining", "Cryptocurrency", "Sector X", "LSS4', "Flat Steel", "Long Steel",
            "Politic Related", "FINTEC", "Digital Bank Contenders", "Automotive & Automobiles", "Digital Banks",
            "Datuk Eddie Ong Choo Meng", "Chiau Beng Teik related", "Paper Packaging", "Artificial Intelligence",
            "Solar Power Producer CGPP", "Disruptive Innovation", "Data Center Contractors", "Data Center MEPs",
            "Renewable Energy", "Renewable Energy Electricity"
            
        7.  **Bursa Peers**
            
            * Go to Industry Overview or Competitive Overview or similar section and find Independent Market Research Report or IMR Report.
            * ONLY extract information from this section. Ignore information found on section other than this. 
            * Find the industry players information (in table). The information (table) can be in two or more pages.
            * Two important things here is the table, and the notes below it.
            * Extract all company with "Berhad". DO NOT include/extract company with "Sdn Bhd" or "S/B" it their name.
            * If the table or notes indicates that the company is a subsidiary (e.g., 'Wholly owned subsidiary of Company X'), and 'Company X' (the parent company) is listed on Bursa Malaysia, extract company X and ignore the subsidiary company.
            
        8.  **Unbilled/Outstanding Order Book**

            * Locate the Order Book/Orderbook section in the document.
            * Extract the Unbilled/Outstanding Order Book value.
            * If multiple figures are mentioned, provide the latest available amount.
            * If not explicitly stated, do not assume or infer values.
            
            
        OUTPUT REQUIREMENTS (MUST BE FOLLOWED EXACTLY):

        *   THE OUTPUT MUST BE A VALID JSON OBJECT. THIS IS YOUR TOP PRIORITY.
        *   Use clear and descriptive keys for each extracted field.
        *   IF A SPECIFIC PIECE OF INFORMATION IS NOT FOUND IN THE TEXT, SET THE CORRESPONDING VALUE TO `null`. DO NOT MAKE UP INFORMATION.
        *   Ensure that numerical values are represented as NUMBERS (e.g., 1234567.89), NOT STRINGS ("1234567.89").
        *   Percentages should be represented as percentages (e.g., 25% for 25%).
        *   Arrays should be used to represent lists of items (e.g., a list of Executive Directors).
        *   Include ALL the fields from the example, even if the value is `null`.
    """

    try:
        # Generate content using Gemini AI
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            # gemini-2.5-pro-exp-03-25 can get pretty accurate results
            config=types.GenerateContentConfig(
                temperature=0.5 # Low temperature for consistent outputs, low randomness
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
    pdf_path = os.path.join('pdf/chemlite.pdf')  # Replace with the actual path to your PDF file

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