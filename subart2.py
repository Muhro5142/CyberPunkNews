import re

import requests

API_URL = "https://apifreellm.com/api/chat"
HEADERS = {"Content-Type": "application/json"}
SYSTEM_PROMPT = """<|begin_of_text|>
<|start_header_id|>system<|end_header_id|>
You are a strict Night City crime reporter AI.  
Before generating a report, follow these rules:

1. If the input is NOT related to crime, violence, gangs, police, cyberware incidents, Night City districts, or Cyberpunk 2077 setting:
   - Output ONLY this exact text: "Input not related to Night City crime report."
   - Do not generate anything else.

2. If the input IS relevant, then generate crime reports in EXACT format:

Location: [District name in Night City]
Time: [Approximate time]
Headline: [Under 8 words]
Summary: [1 sentence with casualty count]

Then translate the report to Russian after '---' in this EXACT format:
Локация: [Район в Найт-Сити]
Время: [Приблизительное время]
Заголовок: [До 8 слов]
Сводка: [1 предложение с числом жертв]

Night City districts: Watson, Westbrook, Heywood, Pacifica, Santo Domingo, City Center, Badlands.  
If a street name is mentioned, assign it to the correct district.  
If district is unclear, use the street name as a landmark within any of the specified districts above.

Important rules:
- Never include any commentary or additional text
- Use only allowed characters in Russian text
- Always maintain the exact format
- Replace any non-Russian characters in Russian part with equivalents<|eot_id|>

<|start_header_id|>user<|end_header_id|>
Event: {input}<|eot_id|>

<|start_header_id|>assistant<|end_header_id|>"""


def validate_english_format(text):
    """Validate the English part of the response has the correct format"""
    required_sections = ["Location", "Time", "Headline", "Summary"]
    return all(re.search(rf'{section}:', text) for section in required_sections)

def validate_russian_format(text):
    """Validate the Russian part of the response has the correct format"""
    required_sections = ["Локация", "Время", "Заголовок", "Сводка"]
    return all(re.search(rf'{section}:', text) for section in required_sections)

def clean_russian_text(text):
    """Clean and validate Russian text, replacing invalid characters"""
    # Expanded character mapping for replacements
    char_map = {
        'a': 'а', 'b': 'б', 'c': 'с', 'd': 'д', 'e': 'е', 
        'g': 'г', 'h': 'х', 'i': 'и', 'k': 'к', 'l': 'л', 
        'm': 'м', 'n': 'н', 'o': 'о', 'p': 'п', 'r': 'р', 
        's': 'с', 't': 'т', 'u': 'у', 'v': 'в', 'w': 'в', 
        'x': 'х', 'y': 'у', 'z': 'з',
        'A': 'А', 'B': 'В', 'C': 'С', 'D': 'Д', 'E': 'Е', 
        'F': 'Ф', 'G': 'Г', 'H': 'Н', 'I': 'И', 'K': 'К', 
        'L': 'Л', 'M': 'М', 'N': 'Н', 'O': 'О', 'P': 'Р', 
        'R': 'Р', 'S': 'С', 'T': 'Т', 'U': 'У', 'V': 'В', 
        'W': 'В', 'X': 'Х', 'Y': 'У', 'Z': 'З'
    }
    
    # Process each character
    cleaned_text = []
    for char in text:
        if char in char_map:
            cleaned_text.append(char_map[char])
        else:
            cleaned_text.append(char)
    
    return ''.join(cleaned_text)

def validate_russian_text(text):
    """Check and clean Russian text"""
    # First clean the text
    text = clean_russian_text(text)
    
    # Define allowed characters
    russian_alphabet = set('абвгдеёжзийклмнопрстуфхцчшщъыьэюяАБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ')
    allowed_punctuation = set(' .,!?;:-—–()[]{}«»"\'\n\t')
    allowed_digits = set('0123456789')
    allowed_in_russian = russian_alphabet | allowed_punctuation | allowed_digits
    
    # Remove section headers before checking
    for header in ["Локация:", "Время:", "Заголовок:", "Сводка:"]:
        text = text.replace(header, "")
    
    # Just check for any remaining non-Russian characters but don't fail validation
    for char in text:
        if char not in allowed_in_russian:
            print(f"Warning: Character '{char}' may not display correctly in Russian")
    
    return True  # We now clean text instead of rejecting

def extract_location_info(text):
    """Extract street and time information from input text"""
    # Look for street names
    street_match = re.search(r'(\w+)\s+[Ss]treet', text)
    street = street_match.group(1) if street_match else None
    
    # Look for time format HH:MM
    time_match = re.search(r'(\d{1,2}:\d{2})', text)
    time = time_match.group(1) if time_match else None
    
    return street, time

def query_model(news_input):
    """Query the FreeLLM API with strict validation"""
    try:
        # Short-circuit on empty/too long input to avoid abuse
        if not news_input or len(news_input) > 1000:
            print("Input rejected by length guard")
            return "", False
        # Extract location and time info
        street, time = extract_location_info(news_input)
        if street and "district" not in news_input.lower():
            if street.lower() == "heywood":
                news_input = f"{news_input} (Heywood District)"
        
        formatted_prompt = SYSTEM_PROMPT.format(input=news_input)

        # Send request to FreeLLM
        data = {"message": formatted_prompt}
        resp = requests.post(API_URL, headers=HEADERS, json=data, timeout=15)
        js = resp.json()

        if js.get("status") != "success":
            print("API Error:", js.get("error"))
            return "", False

        output = js["response"].strip()

        # Explicitly suppress known fallback response from being used anywhere
        fallback_phrase = "Input not related to Night City crime report."
        if fallback_phrase in output:
            print("Input not crime-related; suppressing output.")
            return "", False

        # Split and validate parts
        parts = output.split('---', 1)
        english = parts[0].strip()
        russian = parts[1].strip() if len(parts) > 1 else ""

        # Fix district unknown
        if "Location: District unknown" in english and street:
            english = english.replace("Location: District unknown", f"Location: Heywood")

        english_valid = validate_english_format(english)

        russian_valid = False
        if russian:
            if "Локация: неизвестный район" in russian and street:
                russian = russian.replace("Локация: неизвестный район", "Локация: Хейвуд")
            
            russian = clean_russian_text(russian)
            russian_valid = validate_russian_format(russian) and validate_russian_text(russian)

        if english_valid and russian_valid:
            print("Valid output generated!")
            return f"{english}\n---\n{russian}", True
        elif english_valid:
            print("Only English part is valid")
            return english, True
        else:
            print("Invalid output generated.")
            return output, False

    except Exception as e:
        print(f"Error running model query: {e}")
        return "", False

if __name__ == "__main__":
    print("🔹 Night City Crime Reporter 🔹")
    event = input("Crime details: ").strip()
    
    if event:
        output, is_valid = query_model(event)
        
        if is_valid and output:
            parts = output.split('---', 1)
            english = parts[0].strip()
            
            print("\n📰 Breaking News:")
            print(english)
            
            if len(parts) > 1:
                russian = parts[1].strip()
                print("\n🌍 Экстренные Новости:")
                print(russian)
        elif not is_valid:
            print("\n⚠ Note: The input was not suitable for a Night City crime report.")
