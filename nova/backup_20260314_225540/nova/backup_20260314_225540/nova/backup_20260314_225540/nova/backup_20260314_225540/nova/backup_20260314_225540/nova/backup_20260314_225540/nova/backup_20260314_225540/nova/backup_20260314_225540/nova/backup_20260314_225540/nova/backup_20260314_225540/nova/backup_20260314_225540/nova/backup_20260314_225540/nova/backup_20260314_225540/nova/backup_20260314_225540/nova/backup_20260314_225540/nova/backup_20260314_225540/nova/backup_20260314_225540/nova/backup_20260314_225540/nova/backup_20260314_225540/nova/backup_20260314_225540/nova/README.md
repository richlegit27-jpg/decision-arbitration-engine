\# Nova



Nova is a local AI chat application designed to run entirely on your own machine.

It combines conversational AI with memory, file attachments, and workspace awareness to create a persistent AI assistant environment.



The goal of Nova is to provide a powerful AI interface that behaves more like a real operating system tool than a simple chatbot.



---



\# Features



• Persistent chat sessions  

• Memory system for contextual learning  

• File attachments and uploads  

• Workspace awareness of project files  

• Streaming AI responses  

• Sidebar chat navigation  

• Memory panel management  

• Local runtime storage



---



\# Project Structure



C:\\Users\\Owner\\nova



nova

│

├── backend

│   ├── main.py

│   ├── brain.py

│   ├── routes\_chat.py

│   ├── memory\_store.py

│   ├── workspace\_state.py

│   └── other backend modules

│

├── static

│   ├── css

│   ├── js

│   └── assets

│

├── templates

│   └── index.html

│

├── runtime

│   ├── uploads

│   ├── runtime\_chats.json

│   └── runtime\_workspace\_state.json

│

├── requirements.txt

└── README.md



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

