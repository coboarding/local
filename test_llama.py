import asyncio
import json
from coboarding.ai.llm_client import LLMClient

async def test_llama():
    # Initialize the LLM client with a smaller model for testing
    # This will download the model on first run
    print("Initializing LLM client...")
    llm_client = LLMClient(model_name="TinyLlama/TinyLlama-1.1B-Chat-v1.0")
    
    # Test form analysis
    print("\nTesting form analysis...")
    form_data = {
        "fields": [
            {"name": "first_name", "type": "text", "label": "Vorname"},
            {"name": "last_name", "type": "text", "label": "Nachname"},
            {"name": "email", "type": "email", "label": "E-Mail"},
            {"name": "phone", "type": "tel", "label": "Telefon"},
            {"name": "resume", "type": "file", "label": "Lebenslauf hochladen"}
        ]
    }
    
    analysis = await llm_client.analyze_form(form_data)
    print("\nForm Analysis Result:")
    print(json.dumps(analysis, indent=2))
    
    # Test cover letter generation
    print("\nTesting cover letter generation...")
    job_description = """
    Wir suchen einen motivierten Buchhalter (m/w/d) für unser Team in Berlin.
    
    Ihre Aufgaben:
    - Führung der Finanzbuchhaltung
    - Erstellung von Monats- und Jahresabschlüssen
    - Steuererklärungen und -erklärungen
    - Zusammenarbeit mit Steuerberatern
    
    Ihr Profil:
    - Abgeschlossene kaufmännische Ausbildung mit Schwerpunkt Rechnungswesen
    - Mehrjährige Berufserfahrung in der Buchhaltung
    - Sehr gute Kenntnisse in DATEV und MS-Office
    - Selbstständige und strukturierte Arbeitsweise
    - Teamfähigkeit und Kommunikationsstärke
    """
    
    profile = {
        "personal_info": {
            "first_name": "Max",
            "last_name": "Mustermann",
            "email": "max.mustermann@example.com",
            "phone": "+49 123 4567890",
            "address": "Musterstraße 123, 10115 Berlin"
        },
        "experience": [
            {
                "position": "Buchhalter",
                "company": "Musterfirma GmbH",
                "duration": "2018 - heute",
                "description": "Verantwortlich für die komplette Finanzbuchhaltung, Erstellung von Monats- und Jahresabschlüssen, Steuererklärungen und Zusammenarbeit mit Steuerberatern."
            },
            {
                "position": "Buchhaltungskaufmann",
                "company": "Beispiel AG",
                "duration": "2015 - 2018",
                "description": "Bearbeitung der Debitoren- und Kreditorenbuchhaltung, Zahlungsverkehr und Bankabstimmung."
            }
        ],
        "education": [
            {
                "degree": "Fachwirt für Finanzbuchhaltung",
                "institution": "IHK Berlin",
                "year": 2015
            },
            {
                "degree": "Kaufmann für Büromanagement",
                "institution": "Berufskolleg Musterstadt",
                "year": 2012
            }
        ],
        "skills": ["DATEV", "SAP FI", "MS-Office", "HGB", "UStG", "EÜR"],
        "languages": [
            {"language": "Deutsch", "level": "Muttersprache"},
            {"language": "Englisch", "level": "Fließend"}
        ]
    }
    
    cover_letter = await llm_client.generate_cover_letter(job_description, profile)
    print("\nGenerated Cover Letter:")
    print(cover_letter)

if __name__ == "__main__":
    print("Starting LLaMA model test...")
    asyncio.run(test_llama())
