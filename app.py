import streamlit as st
import os
import json
import time
import pandas as pd
from dotenv import load_dotenv
from pymongo import MongoClient
from google import generativeai as genai

# Load environment variables
load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME")
COLLECTION_NAME = os.getenv("COLLECTION_NAME")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

GEMINI_MODEL = "gemini-2.0-flash"
MAX_RETRIES = 3
RETRY_DELAY = 5
MAX_RESULTS_TO_SHOW = 3

# MongoDB Handler
class MongoDBHandler:
    def __init__(self):
        self.client = MongoClient(MONGO_URI)
        self.db = self.client[DB_NAME]
        self.collection = self.db[COLLECTION_NAME]
        self.collection.find_one()

    def get_fields(self):
        sample = self.collection.find_one()
        return list(sample.keys()) if sample else []

    def run_query(self, query):
        return list(self.collection.find(query))

# Gemini Query Generator
class QueryGenerator:
    def __init__(self):
        genai.configure(api_key=GEMINI_API_KEY)
        self.model = genai.GenerativeModel(GEMINI_MODEL)

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
        for _ in range(MAX_RETRIES):
            try:
                response = self.model.generate_content(prompt)
                clean = response.text.strip().replace("```json", "").replace("```", "").replace("json", "")
                return json.loads(clean)
            except Exception:
                time.sleep(RETRY_DELAY)
        return None

# Streamlit UI
def main():
    st.title("🧠 MongoDB AI Query Tool")

    if "query_count" not in st.session_state:
        st.session_state.query_count = 0

    try:
        mongo = MongoDBHandler()
        all_fields = mongo.get_fields()
        query_gen = QueryGenerator()
    except Exception as e:
        st.error(f"Connection failed: {e}")
        return

    st.subheader("Step 1: Choose Columns")
    selected_columns = st.multiselect("Select columns to allow in your query", all_fields, default=all_fields)

    st.subheader("Step 2: Enter Your Question")
    user_input = st.text_input("Ask something about your data")

    st.subheader("Step 3: Choose Output")
    display = st.checkbox("Show results in table", value=True)
    save = st.checkbox("Save results to CSV")

    if user_input and (display or save):
        st.session_state.query_count += 1
        file_name = f"test_case{st.session_state.query_count}.csv"

        with st.spinner("Thinking..."):
            start = time.time()
            query = query_gen.generate_query(selected_columns, user_input)

            if query:
                st.subheader("Generated MongoDB Query")
                st.code(json.dumps(query, indent=2))

                results = mongo.run_query(query)

                if not results:
                    st.warning("No results found.")
                else:
                    df = pd.DataFrame(results).drop(columns=["_id"], errors="ignore")

                    if display:
                        st.subheader("📊 Results")
                        st.dataframe(df.head(MAX_RESULTS_TO_SHOW))

                    if save:
                        df.to_csv(file_name, index=False)
                        with open(file_name, "rb") as f:
                            st.download_button("📥 Download CSV", f, file_name, "text/csv")

                    st.success(f"Done in {time.time() - start:.2f} sec")
            else:
                st.error("Failed to generate a valid query.")

if __name__ == "__main__":
    main()
