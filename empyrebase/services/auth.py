import datetime
import json
import jwt as jwt
from empyrebase.utils import raise_detailed_error
import requests
from urllib.parse import unquote
from Crypto.PublicKey import RSA
import webbrowser


class Auth:
    """ Authentication Service """

    def __init__(self, api_key, requests, credentials):
        self.api_key = api_key
        self.current_user = None
        self.requests = requests
        self.credentials = credentials

    def sign_in_with_email_and_password(self, email, password):
        request_ref = f"https://www.googleapis.com/identitytoolkit/v3/relyingparty/verifyPassword?key={self.api_key}"
        headers = {"content-type": "application/json; charset=UTF-8"}
        data = json.dumps(
            {"email": email, "password": password, "returnSecureToken": True})
        request_object = requests.post(request_ref, headers=headers, data=data)
        raise_detailed_error(request_object)
        self.current_user = request_object.json()
        return request_object.json()

    def get_google_oauth_token(self, client_id: str, client_secret: str, redirect_uri: str = "http://localhost", scope: str = "email%20profile%20openid") -> str:
        """
        Retrieves an OAuth token from Google using the Client Credentials Flow.

        This method opens a web browser to redirect the user to the Google authentication page,
        and then prompts them to paste the authorization code back in. The resulting access token
        is returned as a string.

        Args:
            client_id (str): The ID of your application on Google Cloud Console.
            client_secret (str): The secret key for your application on Google Cloud Console.
            redirect_uri (str, optional): The URL to which the user will be redirected after authorization. Defaults to "http://localhost".
            scope (str, optional): A space-separated list of scopes that you want to use with this token. Defaults to "email profile openid".

        Returns:
            str: The OAuth access token.
        """
        base = "https://accounts.google.com/o/oauth2/v2/auth"
        auth_url = (
            f"{base}?response_type=code"
            f"&client_id={client_id}"
            f"&redirect_uri={redirect_uri}"
            f"&scope={scope}"
            f"&access_type=offline"
            f"&prompt=consent"
        )

        print("Visit this URL to sign in:")
        print(auth_url)
        webbrowser.open(auth_url)
        code = input("Paste the code here: ")
        code = unquote(code)

        # Get actual token
        token_url = "https://oauth2.googleapis.com/token"
        data = {
            "code": (code),
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code"
        }
        request_object = requests.post(token_url, data=data)
        raise_detailed_error(request_object)
        request_json = request_object.json()
        # OAuth may use both access_token and id_token, there's no difference.
        # Since the postBody parameters use id_token as a param name, I'll use id_token as a first choice
        return request_json.get("id_token", request_json.get("access_token"))
        # Since the postBody parameters use id_token as a param name, I'll use id_token as a first choice
        return request_json.get("id_token", request_json.get("access_token"))

    def sign_in_with_oauth(self, oauth_token: str, provider_id: str = "google.com", request_uri: str = "http://localhost") -> dict:
        """
        Sign in using an OAuth token.

        Args:
            - oauth_token (str): The OAuth token to use for authentication.
            - provider_id (str, optional): The ID of the OAuth provider. Defaults to "google.com".
            - request_uri (str, optional): The URI that will be included in the authorization request. Defaults to "http://localhost".

        Returns:
            dict: A dictionary containing the user's data and authentication token.
        """
        request_ref = f'https://identitytoolkit.googleapis.com/v1/accounts:signInWithIdp?key={self.api_key}'
        data = {
            'postBody': f'id_token={oauth_token}&providerId={provider_id}',
            'requestUri': request_uri,
            'returnSecureToken': True,
        }
        request_object = requests.post(request_ref, json=data)
        raise_detailed_error(request_object)
        self.current_user = request_object.json()
        return request_object.json()

    def sign_in_anonymous(self):
        request_ref = f"https://www.googleapis.com/identitytoolkit/v3/relyingparty/signupNewUser?key={self.api_key}"
        headers = {"content-type": "application/json; charset=UTF-8"}
        data = json.dumps({"returnSecureToken": True})
        request_object = requests.post(request_ref, headers=headers, data=data)
        raise_detailed_error(request_object)
        self.current_user = request_object.json()
        return request_object.json()

    def create_custom_token(self, uid, additional_claims=None, expiry_minutes=60):
        service_account_email = self.credentials.service_account_email
        private_key = self.credentials._private_key_pkcs8_pem
        payload = {
            "iss": service_account_email,
            "sub": service_account_email,
            "aud": "https://identitytoolkit.googleapis.com/google.identity.identitytoolkit.v1.IdentityToolkit",
            "uid": uid,
            # issued at time
            "iat": datetime.datetime.now(datetime.timezone.utc),
            "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=expiry_minutes)
        }
        if additional_claims:
            payload.update(additional_claims)
        token = jwt.encode(payload, private_key,
                           algorithm="RS256")  # create token
        return token

    def sign_in_with_custom_token(self, token):
        request_ref = f"https://www.googleapis.com/identitytoolkit/v3/relyingparty/verifyCustomToken?key={self.api_key}"
        headers = {"content-type": "application/json; charset=UTF-8"}
        data = json.dumps({"returnSecureToken": True, "token": token})
        request_object = requests.post(request_ref, headers=headers, data=data)
        raise_detailed_error(request_object)
        return request_object.json()

    def refresh(self, refresh_token):
        request_ref = f"https://securetoken.googleapis.com/v1/token?key={self.api_key}"
        headers = {"content-type": "application/json; charset=UTF-8"}
        data = json.dumps({"grantType": "refresh_token",
                          "refreshToken": refresh_token})
        request_object = requests.post(request_ref, headers=headers, data=data)
        raise_detailed_error(request_object)
        request_object_json = request_object.json()
        # handle weirdly formatted response
        user = {
            "userId": request_object_json["user_id"],
            "idToken": request_object_json["id_token"],
            "refreshToken": request_object_json["refresh_token"]
        }
        return user

    def get_account_info(self, id_token):
        request_ref = f"https://www.googleapis.com/identitytoolkit/v3/relyingparty/getAccountInfo?key={self.api_key}"
        headers = {"content-type": "application/json; charset=UTF-8"}
        data = json.dumps({"idToken": id_token})
        request_object = requests.post(request_ref, headers=headers, data=data)
        raise_detailed_error(request_object)
        return request_object.json()

    def send_email_verification(self, id_token):
        request_ref = f"https://www.googleapis.com/identitytoolkit/v3/relyingparty/getOobConfirmationCode?key={self.api_key}"
        headers = {"content-type": "application/json; charset=UTF-8"}
        data = json.dumps({"requestType": "VERIFY_EMAIL", "idToken": id_token})
        request_object = requests.post(request_ref, headers=headers, data=data)
        raise_detailed_error(request_object)
        return request_object.json()

    def send_password_reset_email(self, email):
        request_ref = f"https://www.googleapis.com/identitytoolkit/v3/relyingparty/getOobConfirmationCode?key={self.api_key}"
        headers = {"content-type": "application/json; charset=UTF-8"}
        data = json.dumps({"requestType": "PASSWORD_RESET", "email": email})
        request_object = requests.post(request_ref, headers=headers, data=data)
        raise_detailed_error(request_object)
        return request_object.json()

    def change_password(self, id_token: str, password: str, return_secure_token: bool):
        """Change the password of a user

        Args:
            id_token (str): Auth token (idToken) for the user
            password (str): New password to change to
            return_secure_token (bool): Whether or not to return an ID and refresh token.

        Returns:
            dict: Response from firebase.
        """
        request_ref = f"https://identitytoolkit.googleapis.com/v1/accounts:update?key={self.api_key}"
        headers = {"content-type": "application/json; charset=UTF-8"}
        data = json.dumps({
            "idToken": id_token,
            "password": password,
            "returnSecureToken": return_secure_token,
        })
        request_object = requests.post(request_ref, headers=headers, data=data)
        raise_detailed_error(request_object)
        return request_object.json()

    def verify_password_reset_code(self, reset_code, new_password):
        request_ref = f"https://www.googleapis.com/identitytoolkit/v3/relyingparty/resetPassword?key={self.api_key}"
        headers = {"content-type": "application/json; charset=UTF-8"}
        data = json.dumps({"oobCode": reset_code, "newPassword": new_password})
        request_object = requests.post(request_ref, headers=headers, data=data)
        raise_detailed_error(request_object)
        return request_object.json()

    def create_user_with_email_and_password(self, email, password):
        request_ref = f"https://www.googleapis.com/identitytoolkit/v3/relyingparty/signupNewUser?key={self.api_key}"
        headers = {"content-type": "application/json; charset=UTF-8"}
        data = json.dumps(
            {"email": email, "password": password, "returnSecureToken": True})
        request_object = requests.post(request_ref, headers=headers, data=data)
        raise_detailed_error(request_object)
        return request_object.json()

    def delete_user_account(self, id_token):
        request_ref = f"https://www.googleapis.com/identitytoolkit/v3/relyingparty/deleteAccount?key={self.api_key}"
        headers = {"content-type": "application/json; charset=UTF-8"}
        data = json.dumps({"idToken": id_token})
        request_object = requests.post(request_ref, headers=headers, data=data)
        raise_detailed_error(request_object)
        return request_object.json()

    def update_profile(self, id_token, display_name=None, photo_url=None, delete_attribute=None):
        """
        https://firebase.google.com/docs/reference/rest/auth#section-update-profile
        """
        request_ref = f"https://identitytoolkit.googleapis.com/v1/accounts:update?key={self.api_key}"
        headers = {"content-type": "application/json; charset=UTF-8"}
        data = json.dumps({"idToken": id_token, "displayName": display_name, "photoURL": photo_url,
                          "deleteAttribute": delete_attribute, "returnSecureToken": True})
        request_object = requests.post(request_ref, headers=headers, data=data)
        raise_detailed_error(request_object)
        return request_object.json()
