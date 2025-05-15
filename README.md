# 🧠 MongoDB AI Query Tool

A Streamlit application that allows users to query MongoDB collections using natural language, powered by Google's Gemini AI model.
Try this : https://llm-query-system.streamlit.app/

## Features

- **Natural Language Queries**: Convert plain English questions into MongoDB queries automatically
- **CSV Upload**: Easily upload and insert CSV data into your MongoDB collection
- **Interactive Results**: View query results directly in the app or download as CSV
- **AI-Powered**: Leverages AI to interpret user questions and generate accurate MongoDB queries

## Prerequisites

- Python 3.8+
- MongoDB instance (local or remote)
- Google Gemini API key

## Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/mongodb-ai-query-tool.git
   cd mongodb-ai-query-tool
   ```

2. Install the required packages:
   ```bash
   pip install streamlit pandas pymongo python-dotenv google-generativeai
   ```

3. Create a `.env` file in the project directory with the following variables:
   ```
   MONGO_URI=your_mongodb_connection_string
   DB_NAME=your_database_name
   COLLECTION_NAME=your_collection_name
   GEMINI_API_KEY=your_gemini_api_key
   ```

## Usage

1. Start the Streamlit app:
   ```bash
   streamlit run app.py
   ```

2. Open your browser and navigate to `http://localhost:8501`

3. The app workflow:
   - **Upload data**: Use the CSV uploader to add data to your MongoDB collection or use sample csv file for testing.
   - **Choose columns**: Select which fields should be available for querying
   - **Ask questions**: Enter natural language questions about your data.  For Ex. What are the products with a price greater than $50?
   - **View results**: See the generated MongoDB query and the matching data
   - **Export results**: Download query results as CSV files

## Example Queries

- "Show me all products priced over $100"
- "Find all products with a rating below 4.5 that have more than 200 reviews and
 are offered by the brand 'Nike' or 'Sony'"
- "List customers from New York with more than 5 orders"
- "Which products in the Electronics category have a rating of 4.5 or higher and are
 in stock?"

## How It Works

1. **Query Generation**: Your natural language input is sent to Gemini AI, which generates a MongoDB query
2. **MongoDB Execution**: The generated query is executed against your MongoDB collection
3. **Result Display**: Matching documents are displayed in a table and can be exported

## Troubleshooting

- **Connection Issues**: Verify your MongoDB connection string and ensure your IP is whitelisted
- **API Key Errors**: Check that your Gemini API key is valid and has appropriate permissions
- **Query Problems**: If queries fail, try being more specific or ensure the fields mentioned exist in your data

## Dependencies

- `streamlit`: Web application framework
- `pandas`: Data manipulation and analysis
- `pymongo`: MongoDB driver for Python
- `google-generativeai`: Google Gemini AI client
- `python-dotenv`: Environment variable management
