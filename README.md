# Chat Saúde - Flask & OpenAI Medical Data Assistant

## 1. Overview

**Chat Saúde** is a web-based application built with Flask that serves as an intelligent medical data assistant. It provides a chat interface for healthcare professionals to query a patient's clinical journey using natural language.

The application leverages the OpenAI API to undesrtand user questions, analyze patient data retrieved from a PostgreSQL database, and provide answers. One nice feature is it's able to generate Python code for data visualizations on the fly and render the resulting plots directly within the chat interface.

## 2. Features

* **User Authentication**: Access is restricted to registered users with a session-based login system. For now to 'register' a user, just add his credentials at the .env file, but im planning to create a 'create account' system. 
* **Intuitive Chat Interface**: A clean and simple UI for asking questions about a specific patient.
* **OpenAI Integration**: Utilizes GPT-4o to understand complex queries and analyze clinical notes.
* **Dynamic Data Visualization**: Generates Python code (`matplotlib`) in response to requests for graphs and charts.
* **In-App Code Execution**:  Executes the generated Python code on the backend to render and display plots without requiring the user to leave the browser.
* **Database Connectivity**: Connects to a PostgreSQL database to fetch real-time patient journey data.

## 3. Project Structure

```
.
|-- static/
|   |- styles.css        # Frontend styling
|   |-- images/
|       |-- logo1.jpeg    # Application logo
|-- templates/
|   |-- index.html        # Main chat page
|   |-- login.html        # Login page
|-- db/
|   |-- models.py                # Main Flask application, routes, and logic
|-- app.py             # Database connection and query logic
|-- .env                  # File for environment variables (credentials)
|-- requirements.txt      # Python dependencies
```

## 4. Setup and Installation

Follow these steps to set up and run the project locally.

### 4.1. Prerequisites

* Python 3.8 or higher
* `pip` (Python package installer)
* Access to a PostgreSQL database

### 4.2. Clone the Repository

```bash
git clone <your-repository-url>
cd <repository-folder>
```

### 4.3. Create and Activate a Virtual Environment

It is highly recommended to use a virtual environment to manage project dependencies.

* **On macOS/Linux:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

* **On Windows:**
    ```bash
    python -m venv .venv
    .venv\Scripts\activate
    ```

### 4.4. Create a `requirements.txt` File

Create a file named `requirements.txt` in the root of your project and add the following dependencies:

```
Flask==2.3.2
openai==1.14.3
python-dotenv==1.0.0
SQLAlchemy==2.0.25
psycopg2-binary==2.9.9
matplotlib==3.7.1
```

### 4.5. Install Dependencies

Install all the required packages using pip:

```bash
pip install -r requirements.txt
```

### 4.6. Set Up Environment Variables

The application requires a `.env` file in the project root to store sensitive credentials securely.

1.  Create a file named `.env`:
    ```bash
    touch .env
    ```
2.  Copy and paste the following template into the file, replacing the placeholder values with your actual credentials.

```env
# OpenAI API Key
OPENAI_API_KEY="sk-YourOpenAISecretKey"

# Flask Secret Key (for session management)
# Generate a random key. You can use: python -c 'import os; print(os.urandom(24).hex())'
SECRET_KEY="your_super_secret_flask_key"

# Database Connection Details
DB_HOST="localhost"
DB_PORT="5432"
DB_NAME="your_database_name"
DB_USER="your_database_user"
DB_PASSWORD="your_database_password"

# Application User Credentials
ADMIN_CRED="admin_username"
ADMIN_SENHA="admin_password"
NEWUSER1_CRED="another_user"
NEWUSER1_SENHA="another_user_password"
```

## 5. Usage

Once the setup is complete, you can run the application.

1.  Make sure your virtual environment is activated.
2.  Run the Flask application from the root directory:
    ```bash
    flask run
    # or
    python app.py
    ```
3.  Open your web browser and navigate to `http://127.0.0.1:5000`.
4.  You will be redirected to the login page. Use one of the credentials you defined in the `.env` file to log in.
5.  On the main chat page, enter a valid "Patient ID" and type your question in the message box to start the conversation.

**Example Prompts:**
* "Summarize the patient's last 5 appointments."
* "Are there any mentions of allergies?"
* "Generate a bar chart showing the number of consultations per responsible physician."
