# =======================
# MongoDB AI Query Tool
# =======================
# This app lets users:
# - Upload a CSV file to MongoDB
# - Ask questions in natural language
# - Use Google Gemini AI to convert the question into a MongoDB query
# - View or download the results

import streamlit as st
import os
import json
import time
import pandas as pd
from dotenv import load_dotenv
from pymongo import MongoClient, errors
from google import generativeai as genai

# =======================
# Load environment variables from .env file
# Required keys: MONGO_URI, DB_NAME, COLLECTION_NAME, GEMINI_API_KEY
# =======================
load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME")
COLLECTION_NAME = os.getenv("COLLECTION_NAME")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Model and configuration
GEMINI_MODEL = "gemini-2.0-flash"
MAX_RETRIES = 3              # Try up to 3 times if Gemini fails
RETRY_DELAY = 5              # Wait 5 seconds before retrying
MAX_RESULTS_TO_SHOW = 3      # Limit results shown on screen

# =======================
# MongoDB Handler Class
# =======================
# Handles all database operations
class MongoDBHandler:
    def __init__(self):
        try:
            # Connect to MongoDB server
            self.client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
            self.client.server_info()  # Check if the connection is OK
            self.db = self.client[DB_NAME]
            self.collection = self.db[COLLECTION_NAME]
        except errors.ServerSelectionTimeoutError as e:
            raise ConnectionError("Could not connect to MongoDB") from e

    def get_fields(self):
        # Get field names from one sample document
        sample = self.collection.find_one()
        return list(sample.keys()) if sample else []

    def run_query(self, query):
        # Run a MongoDB query and return the results
        try:
            return list(self.collection.find(query))
        except Exception as e:
            raise RuntimeError(f"MongoDB query failed: {e}")

    def insert_csv(self, df):
        # Insert CSV data into the MongoDB collection
        try:
            self.collection.insert_many(df.to_dict(orient="records"))
        except Exception as e:
            raise RuntimeError(f"Failed to insert data: {e}")

# =======================
# Gemini Query Generator Class
# =======================
# Uses Gemini AI to convert natural language to MongoDB queries
class QueryGenerator:
    def __init__(self):
        genai.configure(api_key=GEMINI_API_KEY)
        self.model = genai.GenerativeModel(GEMINI_MODEL)

    def generate_query(self, columns, user_input):
        # Prompt Gemini with rules and the user's input
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
        for _ in range(MAX_RETRIES):
            try:
                response = self.model.generate_content(prompt)
                clean = response.text.strip().replace("```json", "").replace("```", "").replace("json", "")
                parsed = json.loads(clean)
                if not isinstance(parsed, dict):
                    raise ValueError("Generated query is not a valid JSON object")
                return parsed
            except Exception:
                time.sleep(RETRY_DELAY)
        return None  # Return None if all retries fail

# =======================
# Streamlit UI
# =======================
def main():
    st.title("🧠 MongoDB AI Query Tool")

    # Track number of queries for unique filenames
    if "query_count" not in st.session_state:
        st.session_state.query_count = 0

    # Initialize database and Gemini
    try:
        mongo = MongoDBHandler()
        query_gen = QueryGenerator()
    except Exception as e:
        st.error(f"Connection failed: {e}")
        return

    # === CSV Upload Section ===
    st.subheader("📤 Upload CSV to MongoDB")
    uploaded_file = st.file_uploader("Choose a CSV file", type="csv")

    if uploaded_file:
        try:
            df_csv = pd.read_csv(uploaded_file)
            st.write("Preview:")
            st.dataframe(df_csv.head())
            if st.button("Upload to MongoDB"):
                mongo.insert_csv(df_csv)
                st.success("CSV uploaded and inserted into MongoDB.")
        except Exception as e:
            st.error(f"CSV upload failed: {e}")

    # === Query Section ===
    all_fields = mongo.get_fields()
    if not all_fields:
        st.warning("No data found in MongoDB collection.")
        return

    # Step 1: Select which fields Gemini can use
    st.subheader("Step 1: Choose Columns")
    selected_columns = st.multiselect("Select columns to allow in your query", all_fields, default=all_fields)

    # Step 2: Enter your natural language question
    st.subheader("Step 2: Enter Your Question")
    user_input = st.text_input("Ask something about your data")

    # Step 3: Choose result output method
    st.subheader("Step 3: Choose Output")
    display = st.checkbox("Show results in table", value=True)
    save = st.checkbox("Save results to CSV")

    # Only run if user has typed a question and selected display/save
    if user_input and (display or save):
        if not selected_columns:
            st.error("Please select at least one column.")
            return

        st.session_state.query_count += 1
        file_name = f"test_case{st.session_state.query_count}.csv"

        with st.spinner("Thinking..."):
            start = time.time()
            query = query_gen.generate_query(selected_columns, user_input)

            if query is None:
                st.error("❌ Failed to generate a valid query.")
                return

            # Show the generated MongoDB query
            st.subheader("Generated MongoDB Query")
            st.code(json.dumps(query, indent=2))

            try:
                results = mongo.run_query(query)
            except Exception as e:
                st.error(f"❌ MongoDB query error: {e}")
                return

            if not results:
                st.warning("No results found.")
            else:
                # Convert to DataFrame and remove MongoDB "_id"
                df = pd.DataFrame(results).drop(columns=["_id"], errors="ignore")

                if display:
                    st.subheader("📊 Results")
                    st.dataframe(df.head(MAX_RESULTS_TO_SHOW))

                if save:
                    df.to_csv(file_name, index=False)
                    with open(file_name, "rb") as f:
                        st.download_button("📥 Download CSV", f, file_name, "text/csv")

                st.success(f"✅ Done in {time.time() - start:.2f} sec")

# Run the app
if __name__ == "__main__":
    main()
