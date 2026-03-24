import os
import msal
import requests
from dotenv import load_dotenv
from config import config
from flask_sqlalchemy import SQLAlchemy
from models.ModelUser import ModelUser
from models.entities.User import User
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import secrets
from itsdangerous import URLSafeTimedSerializer



MS_GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"
TOKEN_SALT = "cliente-access"


def build_client_access_token(username, nonce):
    serializer = URLSafeTimedSerializer(config["development"].SECRET_KEY)
    return serializer.dumps(
        {"username": username, "nonce": nonce},
        salt=TOKEN_SALT
    )

def get_access_token(application_id, client_secret, tenant_id):
    """
    Get an app-only token using client credentials flow.
    """
    authority = f"https://login.microsoftonline.com/{tenant_id}/"

    # Create a confidential client
    client = msal.ConfidentialClientApplication(
        client_id=application_id,
        client_credential=client_secret,
        authority=authority
    )

    # IMPORTANT: for app-only, you always use .default scope
    result = client.acquire_token_for_client(
        scopes=["https://graph.microsoft.com/.default"]
    )

    if "access_token" in result:
        return result["access_token"]
    else:
        raise Exception(f"Failed to get token: {result.get('error_description')}")

def send_email(access_token, from_email, to_email, subject, body):
    """
    Send mail as a specific user (robot@empresa.es) using app-only token.
    """
    url = f"{MS_GRAPH_BASE_URL}/users/{from_email}/sendMail"
    
    message = {
        "message": {
            "subject": subject,
            "body": {
                "contentType": "HTML",   # ← IMPORTANTE
                "content": body
            },
            "toRecipients": [
                {
                    "emailAddress": {
                        "address": to_email
                    }
                }
            ]
        },
        "saveToSentItems": "true"
    }

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    response = requests.post(url, headers=headers, json=message)
    
    if response.status_code == 202:
        print(f"Email sent successfully from {from_email} to {to_email}")
    else:
        print(f"Failed to send email. Status: {response.status_code}")
        print("Details:", response.text)

def main():
    
    load_dotenv("variables.env")

    app_id = os.getenv("APP_ID")
    tenant_id = os.getenv("TENANT_ID")
    client_secret = os.getenv("CLIENT_SECRET")
    
    print(app_id)
    print(tenant_id)
    print(client_secret)

    if not app_id or not tenant_id or not client_secret:
        raise Exception("Missing required environment variables.")

    access_token = get_access_token(
        application_id=app_id,
        client_secret=client_secret,
        tenant_id=tenant_id
    )
    
    engine = create_engine("postgresql://usuario:minueva123@localhost/datosweb_utf8")  # cambia según tu BD
    Session = sessionmaker(bind=engine)
    session = Session()
    
    mails_cliente = session.query(User).all()
    
    for i in mails_cliente :

        # to_email = "robot@dinagram.es"  # Replace with actual email
        to_email = i.email
        usuario = i.username
        nonce = secrets.token_urlsafe(32)
        token = build_client_access_token(usuario, nonce)
        i.reset_token = nonce
        subject = "Prueba"
        body = f"""
        <html>
        <body>
            <p>Rellena el trabajo en este <a href="http://127.0.0.1:5000/completartrabajo/{usuario}?token={token}">link</a></p>
        </body>
        </html>
        """

        
        from_email = "robot@dinagram.es"
        print("Hola")
        send_email(access_token, from_email, to_email, subject, body)
    session.commit() 

if __name__ == "__main__":
    main()
