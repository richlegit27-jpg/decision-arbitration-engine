\# Nova



Nova is a local AI chat application designed to run entirely on your own machine.

It combines conversational AI with memory, file attachments, and workspace awareness to create a persistent AI assistant environment.



The goal of Nova is to provide a powerful AI interface that behaves more like a real operating system tool than a simple chatbot.



---



\# Features



â€¢ Persistent chat sessions  

â€¢ Memory system for contextual learning  

â€¢ File attachments and uploads  

â€¢ Workspace awareness of project files  

â€¢ Streaming AI responses  

â€¢ Sidebar chat navigation  

â€¢ Memory panel management  

â€¢ Local runtime storage



---



\# Project Structure



C:\\Users\\Owner\\nova



nova

â”‚

â”œâ”€â”€ backend

â”‚   â”œâ”€â”€ main.py

â”‚   â”œâ”€â”€ brain.py

â”‚   â”œâ”€â”€ routes\_chat.py

â”‚   â”œâ”€â”€ memory\_store.py

â”‚   â”œâ”€â”€ workspace\_state.py

â”‚   â””â”€â”€ other backend modules

â”‚

â”œâ”€â”€ static

â”‚   â”œâ”€â”€ css

â”‚   â”œâ”€â”€ js

â”‚   â””â”€â”€ assets

â”‚

â”œâ”€â”€ templates

â”‚   â””â”€â”€ index.html

â”‚

â”œâ”€â”€ runtime

â”‚   â”œâ”€â”€ uploads

â”‚   â”œâ”€â”€ runtime\_chats.json

â”‚   â””â”€â”€ runtime\_workspace\_state.json

â”‚

â”œâ”€â”€ requirements.txt

â””â”€â”€ README.md



---



\# Running Nova



Open PowerShell and run:



cd C:\\Users\\Owner\\nova

py -m uvicorn --app-dir C:\\Users\\Owner\\nova backend.main:app --host 127.0.0.1 --port 8000



Then open your browser:



http://127.0.0.1:8000



---



\# Requirements



Python 3.10+



Required packages are listed in:



requirements.txt



Install dependencies:



pip install -r requirements.txt



---



\# Runtime Files



Nova stores data locally in the runtime directory:



runtime\_chats.json

runtime\_workspace\_state.json

uploads/



These files contain chat history, memory state, and uploaded attachments.



---



\# Notes



Nova is designed to be modular.

Backend logic, UI rendering, memory management, and workspace analysis are separated into individual components to allow future expansion.



The system is intended to evolve into a full AI workspace platform.



---



\# Status



Current build: Local development version



Core functionality:

\- Chat

\- Memory

\- Attachments

\- Streaming responses

\- Workspace state



Further development may include improved UI polish, enhanced reasoning modules, and expanded tool integrations.



---



\# License



Private project.


