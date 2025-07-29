Comprehensive Analysis of Conversational AI Pipelines
This project presents a detailed analysis and benchmarking of 45 different conversational AI pipelines. Each pipeline is a unique combination of various Speech-to-Text (STT), Text-to-Speech (TTS), and Large Language Model (LLM) services. The primary goal is to evaluate their performance across different use-cases and identify the most optimal combinations.

🚀 Tech Stack & Models Used
This project utilizes the following models and technologies:

Category	Models / Services
Text-to-Speech (TTS)	azure, deepgram, pyttsx3
Speech-to-Text (STT)	azure, deepgram, whisper, assembly, speech recognition
Large Language Model (LLM)	openai, gemini, grok, cohere
Core Language	Python

Export to Sheets
📁 Project Structure
This repository is organized into 45 distinct folders. Each folder represents a unique combination of the models listed above and contains the necessary code and configuration to run that specific pipeline.

⚙️ Setup and Installation
Follow the steps below to run this project on your local machine:

1. Clone the repository:

Bash

git clone https://github.com/your-username/your-repository-name.git
cd your-repository-name
2. Create a virtual environment (Recommended):

Bash

python -m venv venv
source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
3. Install dependencies:
(Ensure you have a requirements.txt file with all the necessary libraries.)

Bash

pip install -r requirements.txt
4. Set up environment variables:
You need to create a .env file to store your secret API keys. Create a file named .env in the project's root directory and add your API keys in the following format.

Code snippet

# OpenAI
OPENAI_API_KEY="your_openai_api_key"

# Azure
AZURE_TTS_KEY="your_azure_api_key"
AZURE_REGION="your_azure_region"

# Deepgram
DEEPGRAM_API_KEY="your_deepgram_api_key"

# AssemblyAI
ASSEMBLYAI_API_KEY="your_assemblyai_api_key"

# Cohere
COHERE_API_KEY="your_cohere_api_key"

# Gemini (Add keys as required)
GEMINI_API_KEY="your_gemini_api_key"
5. Run a specific combination:
To run any combination, navigate to its respective folder and execute the main Python script.

Bash

cd combo_01/
python main.py
📊 Results and Analysis
The table below provides a brief analysis of the findings from the 45 combinations. (You can fill this table based on your results.)

Combination ID	STT Model	TTS Model	LLM Model	Key Finding / Best Use-Case
Combo-01	azure	azure	openai	Fast response, good for general queries.
Combo-02	whisper	deepgram	gemini	High transcription accuracy, suitable for technical dictation.
Combo-03	assembly	pyttsx3	cohere	Fully offline TTS, good for privacy-focused apps.
...	...	...	...	...
