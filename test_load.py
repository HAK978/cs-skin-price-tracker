# test_load.py
import json
import psycopg2
from datetime import datetime
from pathlib import Path

def test_database_load():
    conn = psycopg2.connect(
        dbname="cs_skins",
        user="postgres",
        password="1234",  # Your password
        host="localhost",
        port="5432"
    )
    cur = conn.cursor()
    
    json_file = "C:\\Users\\harsh\\GitHub\\cs-skin-price-tracker\\MP9 - Music Box (Factory New).json"
    
    try:
        print(f"Reading file: {json_file}")
        with open(json_file, 'r') as f:
            data = json.load(f)
        print(f"Found {len(data['prices'])} price entries")
        
        market_hash_name = "MP9 | Music Box (Factory New)"
        
        # Insert skin
        cur.execute("""
            INSERT INTO skins (market_hash_name)
            VALUES (%s)
            ON CONFLICT (market_hash_name) DO NOTHING
            RETURNING skin_id
        """, (market_hash_name,))
        conn.commit()
        
        result = cur.fetchone()
        if result:
            skin_id = result[0]
            print(f"Created new skin with ID: {skin_id}")
        else:
            cur.execute("SELECT skin_id FROM skins WHERE market_hash_name = %s", 
                       (market_hash_name,))
            skin_id = cur.fetchone()[0]
            print(f"Found existing skin with ID: {skin_id}")
        
        # Process price history
        processed = 0
        for date_str, price, volume in data['prices']:
            try:
                date_str = date_str.replace(": +0", ":00 +0000")
                timestamp = datetime.strptime(date_str, '%b %d %Y %H:%M %z')
                price_usd = float(price) * 0.012  # Convert to USD
                
                cur.execute("""
                    INSERT INTO price_history 
                        (time, skin_id, price_usd, price_original, currency, volume)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (time, skin_id) DO UPDATE SET
                        price_usd = EXCLUDED.price_usd,
                        price_original = EXCLUDED.price_original,
                        volume = EXCLUDED.volume
                """, (
                    timestamp,
                    skin_id,
                    price_usd,
                    float(price),
                    data['price_prefix'],
                    int(volume)
                ))
                processed += 1
                if processed % 50 == 0:
                    conn.commit()
                    print(f"Processed {processed} entries")
                
            except Exception as e:
                print(f"Error processing entry: {date_str}, {price}, {volume}")
                print(f"Error details: {e}")
                conn.rollback()
        
        # Final commit
        conn.commit()
        print(f"Finished processing {processed} entries")
        
        # Verify data
        cur.execute("""
            SELECT COUNT(*) FROM price_history 
            WHERE skin_id = %s
        """, (skin_id,))
        count = cur.fetchone()[0]
        print(f"Total entries in database for this skin: {count}")
        
    except Exception as e:
        conn.rollback()
        print(f"Error: {e}")
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    test_database_load()