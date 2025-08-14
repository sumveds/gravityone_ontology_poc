# gravityone_ontology_poc

## Prerequisites

- Python 3.8+
- Neo4j database instance
- OpenAI API key

## Setup

1. **Clone the repository and navigate to the project directory**

2. **Create and activate a virtual environment** (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**:
```bash
pip install -r requirements.txt
```

4. **Configure environment variables**:
   - Copy `.env.example` to `.env` (if available) or create a `.env` file
   - Update the following variables in `.env`:
     ```
     NEO4J_URI=your_neo4j_connection_string
     NEO4J_USER=your_neo4j_username
     NEO4J_PASSWORD=your_neo4j_password
     OPENAI_API_KEY=your_openai_api_key
     ```

## Running the Knowledge Graph RAG Chat

You can run the chatbot in two modes: **CLI mode** or **Web interface (Streamlit)**.

### 🖥️ CLI Mode (Original)

To run the interactive command-line chatbot:

```bash
python src/graph_rag_chatbot.py
```

### 🌐 Streamlit Web Interface (Recommended)

For a modern web-based chat interface:

**Method 1: Using the launcher script**
```bash
python run_streamlit.py
```

**Method 2: Direct streamlit command**
```bash
streamlit run src/graph_rag_chatbot.py
```

The Streamlit interface provides:
- 💬 Modern chat UI with message history
- 📋 Clickable example questions in the sidebar
- 🎯 Better user experience with loading indicators
- 🔄 Session state management
- 🗑️ Clear chat history functionality

The web app will launch at `http://localhost:8501` and open in your default browser.

### System Initialization

Both modes will automatically:
1. Set up the vector index in Neo4j
2. Generate embeddings for all nodes in your graph (first run only)
3. Start the chatbot interface

### First Run vs Subsequent Runs

- **First Run**: The application will generate embeddings for all nodes in your Neo4j graph. This process may take several minutes depending on the number of nodes and OpenAI API response times.

- **Subsequent Runs**: The application will skip nodes that already have embeddings, making startup much faster.

### Resetting Embeddings

If you need to regenerate all embeddings (e.g., after significant data changes):

```bash
python src/graph_rag_chatbot.py --reset
```

This will:
1. Remove all existing embeddings from nodes
2. Regenerate embeddings for all nodes
3. Start the chatbot

### Using the Chatbot

Once running, you can ask business questions about your organization such as:
- "What are the strategic objectives?"
- "Show me projects related to data capabilities"
- "What risks threaten our customer service objectives?"
- "Which business units own the most projects?"

Type `exit` or `quit` to stop the chatbot.

## 🚀 Deploying to Streamlit Cloud

To deploy your chatbot to Streamlit Cloud for public access:

### Prerequisites
- GitHub repository with your code
- Streamlit Cloud account (free at [share.streamlit.io](https://share.streamlit.io))

### Step-by-Step Deployment

1. **Push your code to GitHub**:
   ```bash
   git add .
   git commit -m "Add Streamlit interface for Graph RAG chatbot"
   git push origin main
   ```

2. **Create a Streamlit secrets file**:
   Create `.streamlit/secrets.toml` in your repository:
   ```toml
   [secrets]
   NEO4J_URI = "your_neo4j_connection_string"
   NEO4J_USER = "your_neo4j_username" 
   NEO4J_PASSWORD = "your_neo4j_password"
   OPENAI_API_KEY = "your_openai_api_key"
   ```
   
   ⚠️ **Important**: Add `.streamlit/secrets.toml` to your `.gitignore` file to keep secrets secure.

3. **Update settings.py for Streamlit Cloud**:
   Modify `src/config/settings.py` to read from Streamlit secrets:
   ```python
   import streamlit as st
   
   # Check if running in Streamlit Cloud
   if hasattr(st, 'secrets'):
       NEO4J_URI = st.secrets["NEO4J_URI"]
       NEO4J_USER = st.secrets["NEO4J_USER"] 
       NEO4J_PASSWORD = st.secrets["NEO4J_PASSWORD"]
       OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
   else:
       # Fallback to environment variables for local development
       from dotenv import load_dotenv
       load_dotenv()
       # ... rest of your existing settings
   ```

4. **Deploy to Streamlit Cloud**:
   - Go to [share.streamlit.io](https://share.streamlit.io)
   - Click "New app"
   - Connect your GitHub repository
   - Set main file path: `src/graph_rag_chatbot.py`
   - Configure secrets in the Streamlit Cloud dashboard
   - Click "Deploy"

### Updating Your Deployed App

When you make changes to your code:

1. **Push changes to GitHub**:
   ```bash
   git add .
   git commit -m "Update chatbot features"
   git push origin main
   ```

2. **Streamlit Cloud auto-deployment**:
   - Streamlit Cloud automatically detects changes and redeploys
   - You can also manually trigger redeployment from the dashboard
   - Monitor logs in the Streamlit Cloud interface for any issues

### Managing Secrets in Streamlit Cloud

1. Go to your app's settings in Streamlit Cloud
2. Navigate to the "Secrets" section
3. Add your environment variables in TOML format:
   ```toml
   NEO4J_URI = "your_connection_string"
   NEO4J_USER = "your_username"
   NEO4J_PASSWORD = "your_password" 
   OPENAI_API_KEY = "your_api_key"
   ```
4. Save the secrets - the app will automatically restart

## Project Structure

- `src/graph_rag_chatbot.py` - Main RAG chatbot application
- `src/config/settings.py` - Configuration settings
- `src/db/neo4j_client.py` - Neo4j database client
- `run_streamlit.py` - Streamlit launcher script
- `requirements.txt` - Python dependencies
- `.env` - Environment variables (create this file)
- `.streamlit/secrets.toml` - Streamlit Cloud secrets (for deployment)
