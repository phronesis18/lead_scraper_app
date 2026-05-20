import requests
import streamlit as st

class RapidAPIClient:
    def __init__(self):
        self.api_key = st.secrets.get("RAPIDAPI_KEY")
        self.host = "website-contacts-scraper.p.rapidapi.com"

    def get_contacts(self, domain: str):
        """Scrape les contacts publics d’un domaine via RapidAPI"""
        if not self.api_key:
            st.warning("Clé RapidAPI manquante")
            return None
        url = "https://website-contacts-scraper.p.rapidapi.com/scrape-contacts"
        headers = {
            "x-rapidapi-key": self.api_key,
            "x-rapidapi-host": self.host,
            "Content-Type": "application/json"
        }
        params = {"query": domain, "match_email_domain": "false", "external_matching": "false"}
        try:
            response = requests.get(url, headers=headers, params=params, timeout=15)
            if response.status_code == 200:
                return response.json()
            else:
                st.error(f"RapidAPI error {response.status_code}")
                return None
        except Exception as e:
            st.error(f"RapidAPI exception: {e}")
            return None