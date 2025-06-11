import streamlit as st
import asyncio
from pathlib import Path
import yaml
import json
from typing import Dict, List
from core.ai.cv_parser import CVParser
from core.automation.form_detector import FormDetector
from core.integrations.linkedin_api import LinkedInAPI
from core.storage.redis_client import RedisClient
import uuid

# Page config
st.set_page_config(
    page_title="coBoarding",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)


class CoboardingApp:
    def __init__(self):
        self.cv_parser = CVParser()
        self.form_detector = FormDetector()
        self.linkedin_api = LinkedInAPI()
        self.redis_client = RedisClient()
        self.load_translations()
        self.load_companies()

    def load_translations(self):
        """Load language translations"""
        self.translations = {}
        locales_dir = Path("ui/locales")

        for lang_file in locales_dir.glob("*.yaml"):
            lang_code = lang_file.stem
            with open(lang_file, 'r', encoding='utf-8') as f:
                self.translations[lang_code] = yaml.safe_load(f)

    def load_companies(self):
        """Load company database"""
        with open("data/companies/companies.json", 'r', encoding='utf-8') as f:
            self.companies = json.load(f)

    def t(self, key: str, lang: str = "en") -> str:
        """Get translation for key"""
        keys = key.split('.')
        value = self.translations.get(lang, self.translations["en"])

        for k in keys:
            value = value.get(k, key)
        return value

    async def main(self):
        """Main application interface"""

        # Sidebar for language selection
        with st.sidebar:
            st.image("ui/assets/logo.png", width=200)

            # Language selector
            language = st.selectbox(
                "Language / Język / Sprache",
                options=["en", "pl", "de"],
                format_func=lambda x: {"en": "🇺🇸 English", "pl": "🇵🇱 Polski", "de": "🇩🇪 Deutsch"}[x]
            )

            st.session_state.language = language

        # Main title
        st.title(self.t("ui.title", language))

        # Initialize session state
        if 'step' not in st.session_state:
            st.session_state.step = 1
        if 'cv_data' not in st.session_state:
            st.session_state.cv_data = None
        if 'session_id' not in st.session_state:
            st.session_state.session_id = str(uuid.uuid4())

        # Progress indicator
        progress_labels = [
            self.t("ui.step_upload", language),
            self.t("ui.step_review", language),
            self.t("ui.step_companies", language),
            self.t("ui.step_automate", language)
        ]

        cols = st.columns(4)
        for i, label in enumerate(progress_labels, 1):
            with cols[i - 1]:
                if st.session_state.step >= i:
                    st.success(f"✅ {i}. {label}")
                else:
                    st.info(f"⏳ {i}. {label}")

        st.divider()

        # Step 1: CV Upload
        if st.session_state.step == 1:
            await self.render_upload_step(language)

        # Step 2: CV Review and Chat
        elif st.session_state.step == 2:
            await self.render_review_step(language)

        # Step 3: Company Selection
        elif st.session_state.step == 3:
            await self.render_company_selection(language)

        # Step 4: Automation
        elif st.session_state.step == 4:
            await self.render_automation_step(language)

    async def render_upload_step(self, language: str):
        """Render CV upload interface"""
        st.header(self.t("ui.upload_cv", language))

        col1, col2 = st.columns([2, 1])

        with col1:
            uploaded_file = st.file_uploader(
                self.t("ui.choose_file", language),
                type=['pdf', 'docx', 'doc', 'jpg', 'jpeg', 'png'],
                help=self.t("ui.file_help", language)
            )

            if uploaded_file is not None:
                # Save uploaded file temporarily
                temp_path = f"temp_{st.session_state.session_id}_{uploaded_file.name}"
                with open(temp_path, "wb") as f:
                    f.write(uploaded_file.getvalue())

                # Show processing spinner
                with st.spinner(self.t("ui.processing_cv", language)):
                    try:
                        # Parse CV
                        cv_data = await self.cv_parser.parse_cv(temp_path, language)
                        st.session_state.cv_data = cv_data

                        # Store in Redis with TTL
                        await self.redis_client.store_cv_data(
                            st.session_state.session_id,
                            cv_data
                        )

                        st.success(self.t("ui.cv_processed", language))

                        # Show preview
                        with st.expander(self.t("ui.cv_preview", language)):
                            st.json(cv_data)

                        if st.button(self.t("ui.continue", language), type="primary"):
                            st.session_state.step = 2
                            st.rerun()

                    except Exception as e:
                        st.error(f"{self.t('ui.error_processing', language)}: {str(e)}")

                    finally:
                        # Clean up temp file
                        Path(temp_path).unlink(missing_ok=True)

        with col2:
            st.info(self.t("ui.supported_formats", language))
            st.markdown("""
            - PDF (.pdf)
            - Word (.docx, .doc)  
            - Images (.jpg, .png)
            """)

            st.warning(self.t("ui.data_retention", language))

    async def render_review_step(self, language: str):
        """Render CV review and chat interface"""
        st.header(self.t("ui.review_data", language))

        if not st.session_state.cv_data:
            st.error(self.t("ui.no_cv_data", language))
            return

        col1, col2 = st.columns([1, 1])

        with col1:
            st.subheader(self.t("ui.extracted_data", language))

            # Editable form for CV data
            cv_data = st.session_state.cv_data

            with st.form("cv_edit_form"):
                # Personal Info
                st.markdown("**" + self.t("ui.personal_info", language) + "**")
                name = st.text_input(self.t("ui.name", language),
                                     value=cv_data.get("personal_info", {}).get("name", ""))
                email = st.text_input(self.t("ui.email", language),
                                      value=cv_data.get("personal_info", {}).get("email", ""))
                phone = st.text_input(self.t("ui.phone", language),
                                      value=cv_data.get("personal_info", {}).get("phone", ""))
                location = st.text_input(self.t("ui.location", language),
                                         value=cv_data.get("personal_info", {}).get("location", ""))

                # Professional Summary
                st.markdown("**" + self.t("ui.professional_summary", language) + "**")
                summary = st.text_area(self.t("ui.summary", language),
                                       value=cv_data.get("professional_summary", ""),
                                       height=100)

                # Skills
                st.markdown("**" + self.t("ui.skills", language) + "**")
                technical_skills = st.text_area(
                    self.t("ui.technical_skills", language),
                    value=", ".join(cv_data.get("skills", {}).get("technical", [])),
                    help=self.t("ui.comma_separated", language)
                )

                if st.form_submit_button(self.t("ui.update_data", language)):
                    # Update CV data
                    updated_data = cv_data.copy()
                    updated_data["personal_info"] = {
                        "name": name,
                        "email": email,
                        "phone": phone,
                        "location": location
                    }
                    updated_data["professional_summary"] = summary
                    updated_data["skills"]["technical"] = [s.strip() for s in technical_skills.split(",")]

                    st.session_state.cv_data = updated_data
                    await self.redis_client.store_cv_data(st.session_state.session_id, updated_data)
                    st.success(self.t("ui.data_updated", language))

        with col2:
            st.subheader(self.t("ui.chat_assistant", language))

            # Chat interface
            if "messages" not in st.session_state:
                st.session_state.messages = []

            # Display chat messages
            for message in st.session_state.messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])

            # Chat input
            if prompt := st.chat_input(self.t("ui.chat_placeholder", language)):
                # Add user message
                st.session_state.messages.append({"role": "user", "content": prompt})

                # Generate AI response
                with st.chat_message("assistant"):
                    with st.spinner(self.t("ui.thinking", language)):
                        response = await self.generate_chat_response(prompt, language)
                        st.markdown(response)
                        st.session_state.messages.append({"role": "assistant", "content": response})

        # Continue button
        st.divider()
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button(self.t("ui.back", language)):
                st.session_state.step = 1
                st.rerun()
        with col2:
            if st.button(self.t("ui.continue_to_companies", language), type="primary"):
                st.session_state.step = 3
                st.rerun()

    async def render_company_selection(self, language: str):
        """Render company selection interface"""
        st.header(self.t("ui.select_companies", language))

        # Filter options
        col1, col2, col3 = st.columns(3)

        with col1:
            industry_filter = st.selectbox(
                self.t("ui.filter_industry", language),
                options=["all"] + list(set(c.get("industry", "") for c in self.companies))
            )

        with col2:
            location_filter = st.selectbox(
                self.t("ui.filter_location", language),
                options=["all"] + list(set(c.get("location", "") for c in self.companies))
            )

        with col3:
            company_size = st.selectbox(
                self.t("ui.filter_size", language),
                options=["all", "startup", "mid", "large", "enterprise"]
            )

        # Filter companies
        filtered_companies = self.companies
        if industry_filter != "all":
            filtered_companies = [c for c in filtered_companies if c.get("industry") == industry_filter]
        if location_filter != "all":
            filtered_companies = [c for c in filtered_companies if c.get("location") == location_filter]
        if company_size != "all":
            filtered_companies = [c for c in filtered_companies if c.get("size") == company_size]

        # Company selection
        st.subheader(f"{len(filtered_companies)} " + self.t("ui.companies_found", language))

        selected_companies = []
        for company in filtered_companies[:20]:  # Show first 20
            col1, col2, col3, col4 = st.columns([1, 3, 2, 1])

            with col1:
                if st.checkbox("", key=f"company_{company['id']}"):
                    selected_companies.append(company)

            with col2:
                st.markdown(f"**{company['name']}**")
                st.caption(company.get('description', '')[:100] + "...")

            with col3:
                st.text(f"📍 {company.get('location', 'Remote')}")
                st.text(f"🏢 {company.get('industry', 'Various')}")

            with col4:
                if company.get('urgent_hiring'):
                    st.error("🔥 " + self.t("ui.urgent", language))
                else:
                    st.success("✅ " + self.t("ui.open", language))

        # Store selected companies
        if selected_companies:
            st.session_state.selected_companies = selected_companies
            st.success(f"{len(selected_companies)} " + self.t("ui.companies_selected", language))

            if st.button(self.t("ui.start_automation", language), type="primary"):
                st.session_state.step = 4
                st.rerun()

        # Back button
        if st.button(self.t("ui.back", language)):
            st.session_state.step = 2
            st.rerun()

    async def render_automation_step(self, language: str):
        """Render automation progress interface"""
        st.header(self.t("ui.automation_progress", language))

        if not hasattr(st.session_state, 'selected_companies'):
            st.error(self.t("ui.no_companies", language))
            return

        # Start automation
        if st.button(self.t("ui.start_now", language), type="primary"):
            await self.run_automation(language)

        # Show progress
        if "automation_progress" in st.session_state:
            progress = st.session_state.automation_progress

            # Overall progress
            st.progress(progress["overall"], text=f"Overall: {progress['overall'] * 100:.0f}%")

            # Individual company progress
            for company_name, status in progress["companies"].items():
                col1, col2, col3 = st.columns([2, 1, 1])

                with col1:
                    st.text(company_name)

                with col2:
                    if status == "completed":
                        st.success("✅ " + self.t("ui.completed", language))
                    elif status == "in_progress":
                        st.info("⏳ " + self.t("ui.in_progress", language))
                    elif status == "failed":
                        st.error("❌ " + self.t("ui.failed", language))
                    else:
                        st.text("⏸️ " + self.t("ui.pending", language))

                with col3:
                    if status == "completed":
                        st.text("🎉 " + self.t("ui.applied", language))

    async def generate_chat_response(self, prompt: str, language: str) -> str:
        """Generate AI chat response"""
        from core.ai.llm_client import LLMClient

        llm_client = LLMClient()

        context_prompts = {
            "en": f"You are a job application assistant. Help the user with their CV and job search. Current CV data: {st.session_state.cv_data}. User question: {prompt}",
            "pl": f"Jesteś asystentem aplikacji o pracę. Pomóż użytkownikowi z CV i poszukiwaniem pracy. Aktualne dane CV: {st.session_state.cv_data}. Pytanie użytkownika: {prompt}",
            "de": f"Du bist ein Bewerbungsassistent. Hilf dem Benutzer mit seinem Lebenslauf und der Jobsuche. Aktuelle CV-Daten: {st.session_state.cv_data}. Benutzerfrage: {prompt}"
        }

        response = await llm_client.generate(
            context_prompts.get(language, context_prompts["en"]),
            model="mistral:7b"
        )

        return response

    async def run_automation(self, language: str):
        """Run the automation process"""
        from core.automation.stealth_browser import StealthBrowser

        companies = st.session_state.selected_companies
        progress = {
            "overall": 0.0,
            "companies": {c["name"]: "pending" for c in companies}
        }
        st.session_state.automation_progress = progress

        browser = StealthBrowser()
        await browser.initialize()

        try:
            for i, company in enumerate(companies):
                # Update progress
                progress["companies"][company["name"]] = "in_progress"
                st.session_state.automation_progress = progress
                st.rerun()

                # Navigate to company application page
                page = await browser.new_page()
                await page.goto(company["application_url"])

                # Analyze form
                form_analysis = await self.form_detector.analyze_page(page, language)

                # Fill form with CV data
                success = await self.fill_application_form(
                    page, form_analysis, st.session_state.cv_data, language
                )

                # Update status
                if success:
                    progress["companies"][company["name"]] = "completed"
                    # Send notification to company
                    await self.send_notification(company, st.session_state.cv_data)
                else:
                    progress["companies"][company["name"]] = "failed"

                # Update overall progress
                progress["overall"] = (i + 1) / len(companies)
                st.session_state.automation_progress = progress
                st.rerun()

                await page.close()

        finally:
            await browser.close()

    async def fill_application_form(self, page, form_analysis: Dict, cv_data: Dict, language: str) -> bool:
        """Fill application form based on analysis and CV data"""
        try:
            # Map CV data to form fields
            field_mappings = await self.map_cv_to_form_fields(form_analysis, cv_data, language)

            # Fill each field
            for field_selector, value in field_mappings.items():
                await self.fill_form_field(page, field_selector, value)

            # Submit form
            submit_selector = form_analysis.get("submit_button", "input[type='submit']")
            await page.click(submit_selector)

            # Wait for confirmation
            await page.wait_for_load_state("networkidle")

            return True

        except Exception as e:
            st.error(f"Form filling error: {str(e)}")
            return False

    async def map_cv_to_form_fields(self, form_analysis: Dict, cv_data: Dict, language: str) -> Dict:
        """Map CV data to form fields using AI"""
        from core.ai.llm_client import LLMClient

        llm_client = LLMClient()

        mapping_prompt = f"""
        Map the CV data to the form fields based on the form analysis.

        Form Analysis: {form_analysis}
        CV Data: {cv_data}

        Return a JSON mapping of form field selectors to values from the CV.
        Language: {language}
        """

        mapping = await llm_client.generate(
            mapping_prompt,
            model="mistral:7b",
            response_format="json"
        )

        return mapping

    async def fill_form_field(self, page, selector: str, value: str):
        """Fill a specific form field"""
        from core.automation.stealth_browser import StealthBrowser

        browser = StealthBrowser()

        try:
            element = await page.wait_for_selector(selector, timeout=5000)
            field_type = await element.get_attribute("type")

            if field_type == "file":
                # Handle file upload
                await element.set_input_files(value)
            elif field_type in ["text", "email", "tel"]:
                # Handle text input with human-like typing
                await browser.human_type(page, selector, value)
            elif await element.tag_name() == "select":
                # Handle dropdown
                await element.select_option(value)
            elif field_type == "checkbox":
                # Handle checkbox
                if value.lower() in ["true", "yes", "1"]:
                    await element.check()
            else:
                # Default text input
                await browser.human_type(page, selector, value)

        except Exception as e:
            st.warning(f"Could not fill field {selector}: {str(e)}")

    async def send_notification(self, company: Dict, cv_data: Dict):
        """Send notification to company about new application"""
        from core.integrations.slack_bot import SlackBot
        from core.integrations.teams_webhook import TeamsWebhook

        message = f"""
        🎯 New Job Application Received!

        **Candidate:** {cv_data.get('personal_info', {}).get('name', 'Unknown')}
        **Position Interest:** {company.get('name', 'Unknown Company')}
        **Skills:** {', '.join(cv_data.get('skills', {}).get('technical', [])[:5])}

        ⏰ Response requested within 24 hours for best candidate engagement.

        💰 View full profile: $10 USD
        """

        # Send to Slack if configured
        if company.get("slack_webhook"):
            slack_bot = SlackBot()
            await slack_bot.send_message(company["slack_webhook"], message)

        # Send to Teams if configured
        if company.get("teams_webhook"):
            teams = TeamsWebhook()
            await teams.send_message(company["teams_webhook"], message)


# Run the app
if __name__ == "__main__":
    app = CoboardingApp()
    asyncio.run(app.main())