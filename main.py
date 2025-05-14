import os
import json
import time
from dotenv import load_dotenv
from pymongo import MongoClient
from google import generativeai as genai

# Load environment variables
load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME")
COLLECTION_NAME = os.getenv("COLLECTION_NAME")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Configuration
GEMINI_MODEL = "gemini-2.0-flash"  # Updated to latest model
MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds
MAX_RESULTS_TO_SHOW = 3

class MongoDBHandler:
    def __init__(self):
        try:
            self.client = MongoClient(MONGO_URI)
            self.db = self.client[DB_NAME]
            self.collection = self.db[COLLECTION_NAME]
            # Test connection
            self.collection.find_one()
            print("✅ MongoDB connection successful")
        except Exception as e:
            raise ConnectionError(f"❌ Failed to connect to MongoDB: {str(e)}")

    def get_collection_fields(self):
        try:
            sample = self.collection.find_one()
            if not sample:
                print("⚠️ Collection is empty")
                return []
            fields = list(sample.keys())
            print(f"📋 Available fields: {', '.join(fields)}")
            return fields
        except Exception as e:
            print(f"❌ Error fetching fields: {str(e)}")
            return []

    def run_query(self, query):
        try:
            result = list(self.collection.find(query))
            print(f"🔍 Found {len(result)} matching documents")
            return result
        except Exception as e:
            print(f"❌ Query Error: {e}")
            return []

class QueryGenerator:
    def __init__(self):
        if not GEMINI_API_KEY:
            raise ValueError("❌ Missing Gemini API key")
        
        try:
            genai.configure(api_key=GEMINI_API_KEY)
            self.model = genai.GenerativeModel(GEMINI_MODEL)
            print("✅ Gemini query generator initialized")
        except Exception as e:
            raise ValueError(f"❌ Failed to initialize Gemini: {str(e)}")

    def generate_query(self, columns, user_input):
        prompt = f"""
Convert this natural language query to a MongoDB query using ONLY these fields: {', '.join(columns)}

RULES:
1. Return ONLY valid JSON
2. No explanations or markdown
3. Use operators: $gt, $lt, $eq, $in
4. For dates, use ISODate format
5. Field names must match exactly

EXAMPLES:
Input: "price over 100" → {{"Price": {{"$gt": 100}}}}
Input: "Samsung phones" → {{"Brand": "Samsung", "Category": "Phone"}}

ACTUAL QUERY: {user_input}
"""
        
        for attempt in range(MAX_RETRIES):
            try:
                print(f"🔄 Attempt {attempt + 1}/{MAX_RETRIES}...")
                response = self.model.generate_content(prompt)
                
                if not response.text:
                    raise ValueError("Empty response from Gemini")
                
                # Clean the response
                clean_result = response.text.strip()
                clean_result = clean_result.replace("```json", "").replace("```", "").replace("json", "")
                
                print(f"⚙️ Raw response: {clean_result}")
                return json.loads(clean_result)
                
            except json.JSONDecodeError:
                print("⚠️ Invalid JSON response from Gemini")
                print(f"Raw response: {response.text if hasattr(response, 'text') else response}")
            except Exception as e:
                print(f"⚠️ API Error: {str(e)}")
            
            if attempt < MAX_RETRIES - 1:
                print(f"⏳ Waiting {RETRY_DELAY} seconds before retry...")
                time.sleep(RETRY_DELAY)
        
        print("❌ All attempts failed")
        return None

def display_results(results):
    if not results:
        print("No results found")
        return
    
    for idx, item in enumerate(results[:MAX_RESULTS_TO_SHOW], 1):
        print(f"\n📄 Result {idx}:")
        print(json.dumps(item, indent=2, default=str))
    
    if len(results) > MAX_RESULTS_TO_SHOW:
        print(f"\n... and {len(results) - MAX_RESULTS_TO_SHOW} more results")

def main():
    print("\n" + "="*50)
    print("MongoDB Natural Language Query Tool")
    print("="*50 + "\n")
    
    try:
        print("🔌 Initializing MongoDB connection...")
        mongo_handler = MongoDBHandler()
    except Exception as e:
        print(str(e))
        return

    print("\n📂 Fetching collection fields...")
    columns = mongo_handler.get_collection_fields()
    if not columns:
        print("❌ Cannot proceed without collection fields")
        return

    try:
        print("\n🤖 Initializing Gemini query generator...")
        query_generator = QueryGenerator()
    except Exception as e:
        print(str(e))
        return

    print("\n" + "="*50)
    print("Enter queries in natural language (e.g. 'products under $50')")
    print("Type 'exit' or 'quit' to end\n")

    while True:
        try:
            user_input = input("🔎 Query > ").strip()
            if user_input.lower() in ["exit", "quit"]:
                break
            if not user_input:
                continue

            print("\n⚙️ Processing query...")
            start_time = time.time()
            
            query = query_generator.generate_query(columns, user_input)
            if not query:
                print("⚠️ Could not generate valid query")
                continue

            print(f"\n🔧 Generated query:\n{json.dumps(query, indent=2)}")
            
            print("\n🔍 Searching database...")
            results = mongo_handler.run_query(query)
            
            print("\n" + "="*50)
            print(f"⏱️  Query took {time.time() - start_time:.2f} seconds")
            display_results(results)
            print("\n" + "="*50)

        except KeyboardInterrupt:
            print("\n🛑 Operation cancelled by user")
            break
        except Exception as e:
            print(f"\n❌ Unexpected error: {str(e)}")

    print("\n👋 Exiting application...")

if __name__ == "__main__":
    # Verify all required packages are installed
    try:
        import google.generativeai
        import pymongo
    except ImportError as e:
        print(f"❌ Missing required package: {str(e)}")
        print("Please install with: pip install google-generativeai pymongo python-dotenv")
        exit(1)
        
    main()