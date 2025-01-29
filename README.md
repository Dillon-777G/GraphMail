# Graph Email Integration

This repository provides a framework for integrating Microsoft Graph API to fetch and manage emails from specified folders. It includes an asynchronous Python-based implementation utilizing FastAPI for the backend, Azure authentication, and Graph API integration.

- **Note:** Not production ready

## Features
- **Asynchronous API Calls**
- **FastAPI RESTful Endpoints**
- **Fetch Folder Contents by Folder Name**

## Folder Structure

```
.
├── app/
│   ├── controllers/
│   │   ├── auth_controller.py        # Handles authentication routes
│   │   ├── attachment_controller.py  # Handles email-attachment-related routes   
│   │   ├── email_controller.py       # Handles email-related routes
│   │   ├── folder_controller.py      # Main endpoint, contains the logic for navigation
│   ├── fAPI_dependencies/
│   │   ├── auth_dependency.py         # dependency for authenticating all endpoints 
│   ├── exception/
│   │   ├── exceptions.py            #Container class for defining all exceptions
│   │   ├── exception_handler.py     #Global exception handler for the micro-service
│   ├── logging/
│   │   ├── logging_config.py    # config loader for the yaml
│   │   ├── logging.yaml         # yaml config for logging instance
│   ├── models/
│   │   ├── email_attachment.py  # Data model for the outlook email attachments
│   │   ├── email_model.py       # Data models for outlook emails 
│   │   ├── folder.py            # Data model for the outlook folders
│   ├── responses/
│   │   ├── attachment_responsee.py       # Custom response class for downloading attachments
│   ├── service/
│   │   ├── attachment_service.py   # logic for attachment operations
│   │   ├── email_service.py        # logic for email operations
│   │   ├── folder_service.py       # logic for folder operations
│   │   ├── graph_service.py        # Handles Microsoft Graph API client setup and authentication
│   ├── utils/
│   │   ├── graph_utils.py          # Utility functions for the graph API
│   ├── app.py                   # Main app that includes all controllers
├── test/
│   ├── attachment_service.py/
│   │   ├── test_attachment_service.py          # Testing functionality of filtering attachments for emails
├── run_server.py                # Uvicorn server runner for the FastAPI app
├── .gitignore                   # Ignored files and directories for Git
├── README.md                    # Project documentation
├── requirements.in              # Python package dependencies
├── pylintrc                     # Linting configuration
```

## Security: Azure AD OAuth2 Authentication

### **Running with the Auth Code Flow:**
- Documentation available at: https://learn.microsoft.com/en-us/graph/sdks/choose-authentication-providers?tabs=python
- This flow depends on the `AuthorizationCodeCredential` being used to construct the `GraphServiceClient`.

## JSON RESPONSE FORMAT:
   - I am currently using pydantic in order to reduce boilerplate code. 
   - This library is subject to change and will need to be monitored for any breaking changes.

## GRAPH COLLECTION NOTE: 
   - Any response with a collection of objects will have the key 'value' which contains the collection. Any function that is expected to return a collection of objects should be designed to check for this key.
   - If the value key is not present, the function should raise an exception.
   - This is subject to change as the API evolves and should be monitored.
   - LINK: https://learn.microsoft.com/en-us/graph/traverse-the-graph?tabs=http

## Setup

### Prerequisites

- Python 3.9+
- Azure AD Application with appropriate Graph API permissions

### Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd <repository-directory>
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.in
   ```

3. Set environment variables:
   ```bash
   export AZURE_CLIENT_ID=<YOUR_CLIENT_ID>
   export AZURE_TENANT_ID=<YOUR_TENANT_ID>
   export AZURE_REDIRECT_URI=<YOUR_REDIRECT_URI>
   export AZURE_CLIENT_SECRET=<YOUR_CLIENT_SECRET>
   export AZURE_GRAPH_USER_SCOPES=<YOUR_SCOPES>
   ```

## Usage

### 1. FASTAPI Server

Start the FastAPI server:
```bash
python run_server.py
```
The server will be available at `http://localhost:5000`.

#### Available Endpoints

- **GET /auth**: Initiates the Azure OAuth2 flow and provides the authorization URL.
- **GET /callback**: Handles the OAuth2 callback and exchanges the authorization code for a token.
- **GET /graph/emails/folder**: Fetches emails from a specified folder (query parameter: `folder_name`).
- **GET /attachments/{folder_name}/{message_id}**: Fetches all attachments for a given message. (path vars: `folder_name`, `message_id`)
- **GET /attachments/{folder_name}/{message_id}/{attachment_id}/download**: Downloads and retrieves metadata for a given attachment. (path vars: `folder_name`, `message_id`, `attachment_id`)
