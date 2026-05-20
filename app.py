import streamlit as st
import csv
import io
import time
from scraper_utils import (
    scrape_team_contact_urls,
    scrape_page_contacts,
    google_dorking_for_profiles,
    enrich_profil_with_scraping
)
from hunter_client import HunterClient
from rapidapi_client import RapidAPIClient

st.set_page_config(page_title="Lead Scraper Finance", layout="wide")
st.title("🔍 Générateur de leads pour investisseurs")
st.markdown("Quatre moteurs : scraping web, Google Dorking, Domain Search, Email Finder (Hunter)")

if "leads" not in st.session_state:
    st.session_state.leads = []
if "processing" not in st.session_state:
    st.session_state.processing = False

hunter = HunterClient()
rapid = RapidAPIClient()

mode = st.sidebar.radio(
    "Mode de recherche",
    [
        "Scraping site web",
        "Google Dorking (profils sociaux)",
        "Domain Search (Hunter/RapidAPI)",
        "Email Finder (Hunter)"
    ]
)

with st.form(key="search_form"):
    if mode == "Scraping site web":
        target = st.text_input("URL du site cible (ex: https://www.exemple.fr)", placeholder="https://...")
        max_pages = st.slider("Nombre max de pages à explorer", 1, 10, 3)
        use_api = st.checkbox("Utiliser les API (Hunter/RapidAPI) si scraping local échoue", value=True)
        submitted = st.form_submit_button("Lancer la recherche")

    elif mode == "Google Dorking (profils sociaux)":
        target = st.text_input("Requête Google Dorking (ex: 'CEO startup finance Paris')", 
                               placeholder="Nom + secteur + ville")
        num_results = st.slider("Nombre de résultats par réseau", 5, 30, 15)
        submitted = st.form_submit_button("Lancer la recherche")

    elif mode == "Domain Search (Hunter/RapidAPI)":
        target = st.text_input("Nom de domaine de l'entreprise (ex: stripe.com)", placeholder="exemple.com")
        st.info("💡 Récupère tous les emails publics du domaine via Hunter (Domain Search) et RapidAPI.")
        submitted = st.form_submit_button("Récupérer les emails")

    else:  # Email Finder (Hunter)
        domain = st.text_input("Domaine de l'entreprise (ex: reddit.com)", placeholder="exemple.com")
        col1, col2 = st.columns(2)
        with col1:
            first_name = st.text_input("Prénom du dirigeant", placeholder="Alexis")
        with col2:
            last_name = st.text_input("Nom du dirigeant", placeholder="Ohanian")
        st.info("🔎 Hunter Email Finder : tente de trouver l'email exact du dirigeant à partir de son prénom, nom et domaine.")
        submitted = st.form_submit_button("Chercher l'email")
        target = None  # Pour éviter NameError

if submitted:
    # Validation
    if mode == "Email Finder (Hunter)":
        if not domain or not first_name or not last_name:
            st.warning("Veuillez remplir le domaine, le prénom et le nom.")
            st.stop()
    elif mode == "Domain Search (Hunter/RapidAPI)" and not target:
        st.warning("Veuillez entrer un nom de domaine.")
        st.stop()
    elif mode != "Email Finder (Hunter)" and not target:
        st.warning("Veuillez remplir le champ requis.")
        st.stop()

    st.session_state.processing = True
    st.session_state.leads = []
    msg_placeholder = st.empty()

    # ---------- Mode Scraping site web ----------
    if mode == "Scraping site web":
        with st.spinner(f"Analyse de {target}..."):
            urls = scrape_team_contact_urls(target, max_pages)
        all_contacts = []
        total_urls = len(urls)
        for i, url in enumerate(urls):
            msg_placeholder.info(f"Scraping ({i+1}/{total_urls}) : {url}")
            data = scrape_page_contacts(url)
            if not data["error"]:
                for email in data["emails"]:
                    all_contacts.append({
                        "source": "scraping local",
                        "url": url,
                        "type": "email",
                        "valeur": email,
                        "nom_extra": ""
                    })
                for phone in data["phones"]:
                    all_contacts.append({
                        "source": "scraping local",
                        "url": url,
                        "type": "téléphone",
                        "valeur": phone,
                        "nom_extra": ""
                    })
            time.sleep(0.5)
        
        if use_api and len([c for c in all_contacts if c["type"] == "email"]) == 0:
            msg_placeholder.info("🔁 Aucun email trouvé localement, appel des API...")
            domain_name = target.replace("https://", "").replace("http://", "").split("/")[0]
            hunter_result = hunter.domain_search(domain_name)
            if hunter_result and hunter_result.get("emails"):
                for email_obj in hunter_result["emails"]:
                    all_contacts.append({
                        "source": "Hunter.io",
                        "url": domain_name,
                        "type": "email",
                        "valeur": email_obj["value"],
                        "nom_extra": f"{email_obj.get('first_name', '')} {email_obj.get('last_name', '')}".strip()
                    })
            rapid_result = rapid.get_contacts(domain_name)
            if rapid_result and isinstance(rapid_result, list):
                for contact in rapid_result:
                    if "email" in contact and contact["email"]:
                        all_contacts.append({
                            "source": "RapidAPI",
                            "url": domain_name,
                            "type": "email",
                            "valeur": contact["email"],
                            "nom_extra": contact.get("name", "")
                        })
        st.session_state.leads = all_contacts
        msg_placeholder.success(f"✅ {len(all_contacts)} coordonnées extraites.")

    # ---------- Mode Google Dorking ----------
    elif mode == "Google Dorking (profils sociaux)":
        with st.spinner(f"Recherche de profils pour : {target}..."):
            profiles = google_dorking_for_profiles(target, num_results)
        enriched = []
        total_profiles = len(profiles)
        for idx, prof in enumerate(profiles):
            msg_placeholder.info(f"Extraction ({idx+1}/{total_profiles}) : {prof.get('platform', '')}")
            if "error" in prof:
                continue
            contact = enrich_profil_with_scraping(prof["url"])
            for email in contact["emails"]:
                enriched.append({
                    "source": prof["platform"],
                    "url": prof["url"],
                    "type": "email",
                    "valeur": email,
                    "nom_extra": prof.get("title", "")
                })
            for phone in contact["phones"]:
                enriched.append({
                    "source": prof["platform"],
                    "url": prof["url"],
                    "type": "téléphone",
                    "valeur": phone,
                    "nom_extra": prof.get("title", "")
                })
            if not contact["emails"] and not contact["phones"]:
                enriched.append({
                    "source": prof["platform"],
                    "url": prof["url"],
                    "type": "profil",
                    "valeur": prof["url"],
                    "nom_extra": prof.get("title", "")
                })
        st.session_state.leads = enriched
        msg_placeholder.success(f"📌 {len(enriched)} éléments extraits.")

    # ---------- Mode Domain Search (Hunter/RapidAPI) ----------
    elif mode == "Domain Search (Hunter/RapidAPI)":
        domain = target.lower().strip()
        all_contacts = []
        msg_placeholder.info("📡 Appel de Hunter.io (Domain Search)...")
        hunter_result = hunter.domain_search(domain)
        if hunter_result and hunter_result.get("emails"):
            for email_obj in hunter_result["emails"]:
                all_contacts.append({
                    "source": "Hunter.io (Domain Search)",
                    "url": domain,
                    "type": "email",
                    "valeur": email_obj["value"],
                    "nom_extra": f"{email_obj.get('first_name', '')} {email_obj.get('last_name', '')}".strip()
                })
        else:
            msg_placeholder.info("   Aucun email trouvé par Hunter.")
        
        msg_placeholder.info("📡 Appel de RapidAPI (Website Contacts)...")
        rapid_result = rapid.get_contacts(domain)
        if rapid_result and isinstance(rapid_result, list):
            for contact in rapid_result:
                if "email" in contact and contact["email"]:
                    all_contacts.append({
                        "source": "RapidAPI",
                        "url": domain,
                        "type": "email",
                        "valeur": contact["email"],
                        "nom_extra": contact.get("name", "")
                    })
        else:
            msg_placeholder.info("   Aucun contact trouvé par RapidAPI.")
        
        st.session_state.leads = all_contacts
        if not all_contacts:
            msg_placeholder.warning(f"Aucun email trouvé pour {domain} via les API.")
        else:
            msg_placeholder.success(f"✅ {len(all_contacts)} emails récupérés.")

    # ---------- Mode Email Finder (Hunter) ----------
    else:  # mode == "Email Finder (Hunter)"
        with st.spinner(f"Recherche de l'email de {first_name} {last_name} sur {domain}..."):
            finder_result = hunter.email_finder(domain, first_name, last_name)
        if finder_result and finder_result.get("email"):
            email = finder_result["email"]
            confidence = finder_result.get("confidence", 0)
            all_contacts = [{
                "source": "Hunter Email Finder",
                "url": domain,
                "type": "email",
                "valeur": email,
                "nom_extra": f"{first_name} {last_name} (confiance {confidence}%)"
            }]
            st.session_state.leads = all_contacts
            msg_placeholder.success(f"✅ Email trouvé : {email}")
        else:
            st.session_state.leads = []
            msg_placeholder.warning("❌ Aucun email trouvé. Vérifiez le domaine, le prénom et le nom, ou votre quota Hunter.")

    st.session_state.processing = False

# ----------------- Affichage des résultats -----------------
if st.session_state.leads:
    st.subheader("📋 Leads collectés")
    def dicts_to_csv(data):
        if not data:
            return ""
        output = io.StringIO()
        fieldnames = data[0].keys()
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)
        return output.getvalue()
    csv_data = dicts_to_csv(st.session_state.leads)
    col1, _ = st.columns(2)
    col1.download_button("📥 Télécharger CSV", data=csv_data, file_name="leads.csv", mime="text/csv")
    st.dataframe(st.session_state.leads, use_container_width=True)
else:
    if not st.session_state.processing:
        st.info("Aucun lead pour le moment. Lancez une recherche.")

st.markdown("---")
st.caption("⚠️ Les API ont des quotas gratuits (50/mois pour Hunter). Utilisez avec parcimonie.")