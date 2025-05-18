# Preference Elicitation Companion

A Streamlit-based application that helps elicit and manage user preferences through natural conversation.

## Features

- Interactive chat interface for preference elicitation
- Persistent storage of user preferences
- Integration with LLM services for natural conversation
- Simple JSON-based storage (with potential for vector embeddings)

## Setup

1. Clone the repository
2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Create a `.env` file in the root directory with your API keys:
   ```
   OPENAI_API_KEY=your_openai_api_key_here
   MODEL_NAME=gpt-3.5-turbo
   ```

## Usage

1. Start the Streamlit app:
   ```bash
   streamlit run app.py
   ```
2. Open your browser to the URL shown in the terminal (typically http://localhost:8501)
3. Start chatting with the preference elicitation companion

## Project Structure

```
├── app.py                     # Main Streamlit application
├── core/
│   ├── __init__.py
│   ├── llm_services.py        # Functions to interact with different LLMs
│   ├── preference_manager.py  # Logic for storing, retrieving, embedding preferences
│   └── elicitation_bot.py     # Logic for the preference elicitation companion
├── data/
│   └── preferences.json       # Simple JSON store for preferences (MVP)
│   └── (potentially) vector_store/ # For embedded preferences later
├── .env                       # To store API keys locally (add to .gitignore)
├── requirements.txt
└── README.md
```

## Contributing

Feel free to submit issues and enhancement requests!
