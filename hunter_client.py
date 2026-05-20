import requests
import streamlit as st

class HunterClient:
    def __init__(self):
        self.api_key = st.secrets.get("HUNTER_API_KEY")
        self.base_url = "https://api.hunter.io/v2"

    def domain_search(self, domain: str):
        """Récupère tous les emails d’un domaine (Domain Search)"""
        if not self.api_key:
            st.warning("Clé Hunter manquante")
            return None
        url = f"{self.base_url}/domain-search"
        params = {"domain": domain, "api_key": self.api_key}
        try:
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                return response.json().get("data", {})
            else:
                st.error(f"Hunter Domain Search error {response.status_code}")
                return None
        except Exception as e:
            st.error(f"Hunter exception: {e}")
            return None

    def email_finder(self, domain: str, first_name: str, last_name: str):
        """Trouve l’email d’une personne précise (Email Finder)"""
        if not self.api_key:
            return None
        url = f"{self.base_url}/email-finder"
        params = {
            "domain": domain,
            "first_name": first_name,
            "last_name": last_name,
            "api_key": self.api_key
        }
        try:
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                return response.json().get("data", {})
            return None
        except:
            return None

    def email_verifier(self, email: str):
        """Vérifie la validité d’un email (Email Verifier)"""
        if not self.api_key:
            return None
        url = f"{self.base_url}/email-verifier"
        params = {"email": email, "api_key": self.api_key}
        try:
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                return response.json().get("data", {})
            return None
        except:
            return None