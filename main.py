import pandas as pd
from pymongo import MongoClient
from llama_cpp import Llama  # Changed from LangChain's LlamaCpp
import os
from dotenv import load_dotenv
import re

# Load environment variables
load_dotenv()

class MongoDBLoader:
    def __init__(self, mongodb_uri, db_name):
        self.client = MongoClient(mongodb_uri)
        self.db = self.client[db_name]
    
    def load_csv_to_collection(self, csv_path, collection_name):
        try:
            df = pd.read_csv(csv_path)
            data = df.to_dict('records')
            collection = self.db[collection_name]
            collection.insert_many(data)
            return True, f"Successfully loaded {len(data)} documents into {collection_name}"
        except Exception as e:
            return False, f"Error loading CSV: {str(e)}"

class MistralQueryGenerator:
    def __init__(self, model_path):
        self.llm = Llama(
            model_path=model_path,
            n_ctx=2048,
            n_threads=4,
            n_gpu_layers=20,
            verbose=False
        )
    
    def generate_query(self, columns, user_input):
        # Clean and preprocess the user input
        user_input = user_input.lower().strip()
        
        # Create a more structured prompt
        prompt = f"""<s>[INST] Convert this natural language query to a MongoDB JSON query:
        
        USER REQUEST: {user_input}
        AVAILABLE COLUMNS: {', '.join(columns)}
        
        RULES:
        1. Only return the query in format: {{"field": {{"$operator": value}}}}
        2. Use only these operators: $gt, $lt, $eq, $ne, $gte, $lte
        3. For numbers use numeric values (without quotes)
        4. For text use exact matches with quotes
        
        EXAMPLE INPUT: "price greater than 100"
        EXAMPLE OUTPUT: {{"Price": {{"$gt": 100}}}}
        
        YOUR RESPONSE MUST BE ONLY THE JSON QUERY:
        {{
        [/INST]
        {{"""  # Starts the JSON response

        try:
            response = self.llm(
                prompt,
                max_tokens=100,
                temperature=0.1,
                stop=["}", "\n"]
            )
            
            # Process the response
            full_response = "{" + response['choices'][0]['text'].strip()
            
            # Ensure proper JSON formatting
            if not full_response.endswith("}"):
                full_response += "}"
                
            # Basic validation
            if full_response.count("{") != full_response.count("}"):
                raise ValueError("Unbalanced braces in response")
                
            # Convert to dict
            import json
            query = json.loads(full_response)
            
            # Verify at least one column is used
            if not any(col in query for col in columns):
                # Try to find closest column match
                for col in columns:
                    if col.lower() in user_input:
                        # Reconstruct with found column
                        value = 100 if "100" in user_input else 50  # Default value
                        return {col: {"$gt": value}}
                raise ValueError("No matching columns found")
                
            return query
            
        except json.JSONDecodeError:
            # Fallback to simple query generation
            for col in columns:
                if col.lower() in user_input:
                    if "greater" in user_input or ">" in user_input:
                        value = self._extract_number(user_input) or 100
                        return {col: {"$gt": value}}
                    elif "less" in user_input or "<" in user_input:
                        value = self._extract_number(user_input) or 50
                        return {col: {"$lt": value}}
                    elif "equal" in user_input or "=" in user_input:
                        value = self._extract_number(user_input) or self._extract_text(user_input)
                        return {col: {"$eq": value}}
            raise ValueError("Could not generate query from input")
            
        except Exception as e:
            raise ValueError(f"Query generation error: {str(e)}")
    
    def _extract_number(self, text):
        import re
        match = re.search(r'\d+', text)
        return int(match.group()) if match else None
        
    def _extract_text(self, text):
        import re
        match = re.search(r'is (\w+)', text)
        return match.group(1) if match else None

class DataQuerySystem:
    def __init__(self):
        self.loader = MongoDBLoader(os.getenv("MONGODB_URI"), os.getenv("DB_NAME"))
        self.query_gen = MistralQueryGenerator(os.getenv("MODEL_PATH"))
        self.current_collection = None
    
    def load_csv(self):
        csv_path = input("Enter CSV path (e.g., data/products.csv): ")
        collection_name = input("Enter collection name (default: CSV filename): ")
        
        if not collection_name:
            collection_name = os.path.splitext(os.path.basename(csv_path))[0]
        
        success, msg = self.loader.load_csv_to_collection(csv_path, collection_name)
        print(msg)
        if success:
            self.current_collection = collection_name
            df = pd.read_csv(csv_path)
            self.columns = df.columns.tolist()
    
    def query_data(self):
        if not self.current_collection:
            print("Load a CSV first!")
            return
        
        print(f"Available columns: {', '.join(self.columns)}")
        
        while True:
            user_input = input("\nEnter query (e.g., 'Price > 50' or 'Brand is Apple'): ").strip()
            if not user_input:
                continue
                
            try:
                print("\nGenerating query...")
                query = self.query_gen.generate_query(self.columns, user_input)
                print(f"Generated MongoDB query: {query}")
                
                results = list(self.loader.db[self.current_collection].find(query))
                
                if not results:
                    print("\nNo matching documents found.")
                else:
                    df = pd.DataFrame(results).drop('_id', axis=1)
                    print("\nResults:")
                    print(df.to_string(index=False))
                    
                    if input("\nSave to CSV? (y/n): ").lower() == 'y':
                        filename = input("Enter filename (e.g., results.csv): ")
                        df.to_csv(filename, index=False)
                        print(f"Saved to {filename}")
                
                break
                
            except ValueError as e:
                print(f"\nError: {str(e)}")
                print("Suggested query formats:")
                print("- [ColumnName] [operator] [value]")
                print("- [ColumnName] greater/less than [value]")
                print("- [ColumnName] equals [value]")
                
                if input("Try again? (y/n): ").lower() != 'y':
                    break

    def run(self):
        while True:
            print("\n=== Data Query System ===")
            print("1. Load CSV")
            print("2. Query Data")
            print("3. Exit")
            choice = input("Choose option: ").strip()
            
            if choice == "1":
                self.load_csv()
            elif choice == "2":
                self.query_data()
            elif choice == "3":
                print("Exiting system...")
                break
            else:
                print("Invalid choice. Please try again.")

if __name__ == "__main__":
    system = DataQuerySystem()
    system.run()