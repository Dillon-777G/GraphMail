# GraphMail Integration

This repository provides a framework for integrating Microsoft Graph API to fetch and manage emails from specified folders. It includes an asynchronous Python-based implementation utilizing FastAPI for the backend, Azure authentication, and Graph API integration.

- **Note:** Not production ready, README is pending a rewrite.

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
