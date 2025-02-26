# load_prices.py
from pathlib import Path
from database_handler import DatabaseHandler

def load_all_price_histories():
    # Directory where JSON files are saved
    json_dir = "C:\\Users\\harsh\\GitHub\\cs-skin-price-tracker"
    
    # Initialize database connection
    db = DatabaseHandler()
    
    try:
        # Process all JSON files in directory
        json_files = list(Path(json_dir).glob("*.json"))
        print(f"Found {len(json_files)} JSON files to process")
        
        for json_file in json_files:
            print(f"\nProcessing {json_file.name}")
            db.load_json_to_db(str(json_file))
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    load_all_price_histories()