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

To run the interactive Knowledge Graph RAG chatbot:

```bash
python src/graph_rag_chatbot.py
```

The application will automatically:
1. Set up the vector index in Neo4j
2. Generate embeddings for all nodes in your graph (first run only)
3. Start the interactive chatbot interface

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

## Project Structure

- `src/graph_rag_chatbot.py` - Main RAG chatbot application
- `src/config/settings.py` - Configuration settings
- `src/db/neo4j_client.py` - Neo4j database client
- `requirements.txt` - Python dependencies
- `.env` - Environment variables (create this file)
