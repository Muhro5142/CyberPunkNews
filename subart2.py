import subprocess
import re

SYSTEM_PROMPT = """<|begin_of_text|>
<|start_header_id|>system<|end_header_id|>
Generate crime reports for Night City in EXACT format:

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
If district is unclear, use the street name as a landmark within "Heywood" district.

Important rules:
1. Never include any commentary or additional text
2. Use only allowed characters in Russian text
3. Always maintain the exact format
4. Replace any non-Russian characters in Russian part with equivalents<|eot_id|>

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
    """Query the model with strict validation"""
    try:
        # Extract location and time info to help with prompt formatting
        street, time = extract_location_info(news_input)
        
        # Enhance input if needed
        if street and "district" not in news_input.lower():
            if street.lower() == "heywood":
                news_input = f"{news_input} (Heywood District)"
        
        formatted_prompt = SYSTEM_PROMPT.format(input=news_input)
        
        process = subprocess.Popen(
            ['ollama', 'run', 'llama3'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            bufsize=1
        )
        
        try:
            stdout, stderr = process.communicate(input=formatted_prompt, timeout=240)
        except subprocess.TimeoutExpired:
            process.kill()
            print("Model query timed out after 240 seconds")
            return "", False
            
        if process.returncode != 0:
            print(f"Model process failed with return code {process.returncode}")
            if stderr:
                print(f"Error: {stderr.strip()}")
            return "", False
            
        output = stdout.strip()
        
        # Split and validate parts
        parts = output.split('---', 1)
        english = parts[0].strip()
        russian = parts[1].strip() if len(parts) > 1 else ""
        
        # Check and fix "District unknown" if needed
        if "Location: District unknown" in english and street:
            # Default to Heywood if street is mentioned but district is unknown
            english = english.replace("Location: District unknown", f"Location: Heywood")
        
        english_valid = validate_english_format(english)
        
        # Process Russian part
        russian_valid = False
        if russian:
            # Check and fix unknown district in Russian text
            if "Локация: неизвестный район" in russian and street:
                russian = russian.replace("Локация: неизвестный район", "Локация: Хейвуд")
                
            russian = clean_russian_text(russian)  # Apply the replacement here
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
        
        if output:
            parts = output.split('---', 1)
            english = parts[0].strip()
            
            print("\n📰 Breaking News:")
            print(english)
            
            if len(parts) > 1:
                russian = parts[1].strip()
                print("\n🌍 Экстренные Новости:")
                print(russian)
        
        if not is_valid:
            print("\n⚠ Note: The report may have formatting issues but was still displayed.")