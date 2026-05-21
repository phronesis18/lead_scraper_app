from scraper_utils import find_emails_by_domain

domaine = "microsoft.com"   # ou un autre domaine
emails = find_emails_by_domain(domaine)
print("Emails trouvés :", emails)