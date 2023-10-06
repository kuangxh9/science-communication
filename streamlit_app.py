import streamlit as st
import streamlit_authenticator as stauth
from deta import Deta
import yaml
from yaml.loader import SafeLoader
import os
from langchain.llms import OpenAI
import re
from PyPDF2 import PdfReader
from streamlit_option_menu import option_menu
import streamlit_survey as ss
from cryptography.fernet import Fernet
import warnings
import openai
import json
from collections import defaultdict

warnings.filterwarnings("ignore", category=UserWarning, module='langchain')


class Validator:
    def validate_username(self, username):
        pattern = r"^[a-zA-Z0-9_-]{1,20}$"
        return bool(re.match(pattern, username))

    def validate_name(self, name):
        return 1 < len(name) < 100

    def validate_email(self, email):
        pattern = "^[a-zA-Z0-9-_]+@[a-zA-Z0-9]+\.[a-z]{1,3}$"
        if re.match(pattern, email):
            return True
        return False


def get_user_data(user):
    data = db.fetch().items
    for person in data:
        if person['key'] == user:
            return person
    return None


def user_history(time, text, ):
    pass


def update_questionnaire_response(user_response, username):
    db.update({"questionnaire_response": user_response}, key=username)
    st.success("Your responses have been recorded. Thank you!")


def generate_responses(text, chat_model="gpt-3.5-turbo", paper_title="", sci_familiarity="", tech_usage="",
                       read_news="", language_spoken="", additional_requirements="None"):
    # Incorporating the parameters into the context
    text = text[:2048]
    user_context = f"""
    The user has {sci_familiarity} with scientific concepts. He/She {tech_usage} uses technology products. 
    He/She {read_news} read or watch the news. The primary language spoken at his/her home is(are) {language_spoken}.
    """

    # print(user_context)

    # Prompt template
    prompt_template = f"""
    Here's the abstract of a paper (titled) {paper_title}: {text}.
    Considering the user's information: {user_context}.
    And user's additional requirements: {additional_requirements}.
    Generate a plain language summary that summarizes the abstract. While creating this Plain Language Summary, please keep the following must-have elements in mind:
    - Ensure fidelity to the original source.
    - Use clear and simple language, avoiding jargon.
    - Maintain ethical considerations, including objectivity and inclusivity.
    - Aim for universal readability, targeting a reading age of 14-17 years.
    - Consider multi-language accessibility.
    - Be open to audience testing for iterative improvements.
    - Take into account any operational context or guidelines that may apply.
    """

    conversation = [
        {'role': 'system', 'content': 'You are a helpful assistant.'},
        {'role': 'user', 'content': prompt_template}
    ]

    try:
        response = openai.ChatCompletion.create(
            model=chat_model,
            messages=conversation
        )
        return response['choices'][0]['message']['content']
    except:
        st.error('Invalid api key.', icon="⚠️")


@st.cache_resource
def survey(user_name):
    title = user_name + '_survey'
    return ss.StreamlitSurvey(title)


# connect to/create Deta user database
db_key = st.secrets["deta_key"]
deta = Deta(db_key)
db = deta.Base("user_data")
key = Fernet(st.secrets['fernet_key'])
config_drive = deta.Drive("config")
config = config_drive.get("config.yaml").read()
config = yaml.load(config, Loader=SafeLoader)

# Create an authenticator
authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days'],
    config['preauthorized']
)
authenticator.validator = Validator()
init_sidebar = st.sidebar.empty()

with init_sidebar:
    page = option_menu(None,
                       ["Login", 'Sign Up'],
                       icons=['lightbulb-fill', 'lightbulb'],
                       menu_icon="cast",
                       default_index=0,
                       styles={})

if page == 'Login':
    st.cache_data.clear()
    name, authentication_status, username = authenticator.login('Login', 'main')
    if authentication_status:
        init_sidebar.empty()
        app_sidebar = st.sidebar.empty()
        # st.sidebar.write(f'Welcome {name}')
        with app_sidebar:
            # 'History'
            # 'folder2',
            page = option_menu(None, ["Generate Plain Language Summary", 'Questionnaire', 'Setup'],
                               icons=['house', 'question-circle', 'gear'],
                               menu_icon="None",
                               default_index=0,
                               styles={})
            authenticator.logout('Logout', 'sidebar', key='unique_key')
        # Fetch user data from the database
        user_data = get_user_data(username)
        if page == "Generate Plain Language Summary":

            st.title("Generate Plain Language Summary")
            st.markdown(
                '''
                ### What is a Plain Language Summary?
                A Plain Language Summary is a clear and concise summary of a scientific paper. It's designed to make complex research findings more accessible and understandable to a general audience.
                #### Detailed Instructions for Generating a Plain Language Summary
                1. **Set Up**: Navigate to the 'Set Up' page to input your API key and specify your writing style. This will help tailor the summary to your preferences.
                2. **Complete the Questionnaire**: On the 'Questionnaire' page, you'll also find a questionnaire designed to further tailor the summary to your needs. Please complete it.
                3. **Choose Content Source**: 
                    - **Option A**: If you have access to the full paper, you can upload the whole document.
                    - **Option B**: Alternatively, you can input the abstract of the paper.
                4. **Input Paper Title**: Paste the exact title of the paper you wish to summarize in the text input field below. An accurate title ensures a more relevant summary.
                5. **Generate Summary**: After completing the above steps, click on the 'Generate' button to receive your Plain Language Summary.
                6. **Additional Steps**: (TO BE ADDED)
                '''
            )

            # Title input box
            title_text = st.text_area("Paste Your Paper Title Here", height=25)

            # Abstract input box
            abstract_text = st.text_area("Paste Abstract Here", height=200)
            # background_info = st.text_area("Background information on original post (references, relevant information, best practices for responding)",  height=200)

            # PDF input box and text extraction
            uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")

            chat_mdl = None
            draft_response = ''

            entire_text = ""
            if uploaded_file is not None:
                reader = PdfReader(uploaded_file)
                num_pages = len(reader.pages)

                for page_num in range(num_pages):
                    page = reader.pages[page_num]
                    page_text = page.extract_text()
                    entire_text += page_text

            if user_data:
                st.session_state.api_key = key.decrypt(user_data['api'].encode()).decode()
            else:
                st.session_state.api_key = ''

            if 'draft_response_content' not in st.session_state:
                st.session_state.draft_response_content = ""

            draft_response = ''
            user_response = user_data['questionnaire_response'] if user_data else defaultdict(lambda: '')

            submit_text = ''
            if entire_text:
                submit_text = entire_text
            else:
                submit_text = abstract_text
            # Check if the "Submit" button is clicked
            if st.button("Submit"):
                if abstract_text == '' and uploaded_file == None:
                    st.warning('Please paste Abstract or upload a file.', icon="⚠️")

                if st.session_state.api_key:
                    os.environ["OPENAI_API_KEY"] = st.session_state.api_key
                    chat_mdl = OpenAI(model_name='gpt-4', temperature=0.1)
                else:
                    st.warning('Please fill in api-key in Setup.', icon="⚠️")

                if chat_mdl is not None and submit_text:
                    st.session_state.draft_response_content = generate_responses(
                        text=submit_text,
                        paper_title=title_text,
                        sci_familiarity=user_response[
                            'paper_familiarity'],
                        tech_usage=user_response[
                            'tech_usage'],
                        read_news=user_response[
                            'news_read'],
                        language_spoken=user_response[
                            'language_spoken'],)

            container = st.empty()
            # Output from function
            container.text_area(label="Plain Language Summary", value=st.session_state.draft_response_content,
                                height=350)
            regenerate_prompt = st.text_area("Additional prompting for regenerating summary", height=100)

            if st.button('Regenerate'):
                if st.session_state.draft_response_content == "":
                    st.warning('Please Generate a PLS first', icon="⚠️")
                elif regenerate_prompt == "":
                    st.warning('Your new prompt is empty', icon="⚠️")
                else:
                    additional_prompt = regenerate_prompt
                    st.session_state.draft_response_content = generate_responses(
                        text=submit_text,
                        paper_title=title_text,
                        sci_familiarity=user_response[
                            'paper_familiarity'],
                        tech_usage=user_response[
                            'tech_usage'],
                        read_news=user_response[
                            'news_read'],
                        language_spoken=user_response[
                            'language_spoken'],
                        additional_requirements=additional_prompt)
                    container.empty()
                    container.text_area(label="Plain Language Summary", value=st.session_state.draft_response_content,
                                        height=350)

            # some function to re-submit prompt and generate new PLS
        # elif page == "History":
        #     st.write('User prompt History TODO')
        elif page == "Setup":
            st.title("Setup")
            # Input boxes with existing data

            if 'api_key' not in st.session_state:
                st.session_state.api_key = ""
            api_input = st.text_input("OpenAI API Token", value=st.session_state.api_key, type='password')
            st.session_state.api_key = api_input

            questionnaire_response = user_data['questionnaire_response'] if user_data else {}

            # Update button
            if st.button("Update"):
                db.put(
                    {"key": username, "api": key.encrypt(bytes(api_input, 'utf-8')).decode(),
                     "questionnaire_response": questionnaire_response})
                st.success('Updating successfully!')
        elif page == "Questionnaire":
            survey = survey(username)
            if 'questionnaire_response' not in st.session_state:
                st.session_state['questionnaire_response'] = {}
            # print(st.session_state['questionnaire_response'])
            page_number = 10
            survey_pages = survey.pages(page_number,
                                        on_submit=lambda: update_questionnaire_response(
                                            st.session_state['questionnaire_response'], username))
            # st.session_state["__streamlit-survey-data__Pages_"] = survey_pages.current
            st.progress((survey_pages.current + 1) / page_number)
            with survey_pages:
                if survey_pages.current == 0:
                    st.write("#### What is your level of education? (for research purposes)")
                    level_education = survey.radio(
                        label="level_education",
                        options=["Primary School", "Middle School", "Secondary School",
                                 "College", "Masters", "PhD"],
                        index=0,
                        label_visibility="collapsed",
                        horizontal=False,
                    )
                    st.session_state['questionnaire_response']['level_education'] = level_education
                elif survey_pages.current == 1:
                    st.write("#### What domains are you most interested in?")
                    domains = ['Global Studies', 'Arts', 'Business & Economics', 'History', 'Humanities',
                               'Law', 'Medicine and Health', 'Science - Biology', 'Science - Chemistry',
                               'Science - Environmental Science', 'Science - Physics', 'Mathematics',
                               'Engineering', 'Social Sciences']
                    domains_interested = {}
                    for i in range(len(domains)):
                        domains_interested[domains[i]] = survey.checkbox(domains[i])
                    interested_domain = []
                    for domain in domains_interested:
                        if domains_interested[domain]:
                            interested_domain.append(domain)
                    st.session_state['questionnaire_response']['interested_domain'] = interested_domain
                elif survey_pages.current == 2:
                    paper_discovery_method = survey.text_area("#### How did you come across this paper?")
                    st.session_state['questionnaire_response']['paper_discovery_method'] = paper_discovery_method
                elif survey_pages.current == 3:
                    reading_purpose = survey.text_area("#### For what purpose are you reading this paper?")
                    st.session_state['questionnaire_response']['reading_purpose'] = reading_purpose
                elif survey_pages.current == 4:
                    st.write("#### What information do you want to get out of this paper?")
                    information_options = ["Main findings and conclusions",
                                           'Methodology and experimental design',
                                           'Data and statistical analysis',
                                           'Limitations or gaps in the research']
                    info_interested = {}
                    for i in range(len(information_options)):
                        info_interested[information_options[i]] = survey.checkbox(information_options[i])
                    desired_information = []
                    for info in info_interested:
                        if info_interested[info]:
                            desired_information.append(info)
                    other_info = survey.text_input('Other aspects:')
                    if other_info:
                        desired_information.append(other_info)
                    st.session_state['questionnaire_response']['desired_information'] = desired_information
                elif survey_pages.current == 5:
                    st.write("#### What is your familiarity with the concepts of the paper?")
                    st.markdown('''
                        * No Familiarity: entirely unfamiliar, no prior knowledge
                        * Limited Familiarity: basic awareness of the concepts in the paper, but not in-depth knowledge
                        * Moderate Familiarity: reasonable understanding of the concepts in the paper, encountered before, or some background knowledge
                        * Good Familiarity: a solid understanding due to prior exposure or study
                        * Expert: highly knowledgeable and experienced in the field and has worked extensively with these concepts
                    ''')
                    paper_familiarity = survey.select_slider(
                        label="paper_familiarity",
                        options=['No Familiarity', 'Limited Familiarity', 'Moderate Familiarity',
                                 'Good Familiarity', 'Expert Familiarity'],
                        # min_value=1,
                        # max_value=5,
                        label_visibility="collapsed",
                    )
                    st.session_state['questionnaire_response']['paper_familiarity'] = paper_familiarity
                elif survey_pages.current == 6:
                    st.write(
                        "#### How much do you use technology (computers, cell phones, tablets, GPS, internet, etc.)?")
                    st.markdown('''
                        * Always: relies heavily on daily tasks
                        * Often in a day: not necessarily every task, but plays a significant role in life
                        * Occasionally: use constantly but not essential for most daily activities
                        * Rarely: use only for specific tasks
                        * Never: avoid using technology
                    ''')
                    tech_usage = survey.select_slider(
                        label="tech_usage",
                        options=['Never', 'Rarely', 'Occasionally',
                                 'Often', 'Always'],
                        # min_value=1,
                        # max_value=5,
                        label_visibility="collapsed",
                    )
                    st.session_state['questionnaire_response']['tech_usage'] = tech_usage
                elif survey_pages.current == 7:
                    st.write("#### How often do you read or watch/listen to the news?")
                    news_read = survey.radio(
                        label="news_read",
                        options=["Never", "Once or Twice a Month", "Once a Week",
                                 "Once in 2-3 Days", "Every Day"],
                        index=0,
                        label_visibility="collapsed",
                        horizontal=False,
                    )
                    st.session_state['questionnaire_response']['news_read'] = news_read
                elif survey_pages.current == 8:
                    st.write("#### How many books do you read or listen to a month?")
                    books_read = survey.radio(
                        label="books_read",
                        options=["None", "1-3", "4-6", "7+"],
                        index=0,
                        label_visibility="collapsed",
                        horizontal=True,
                    )
                    st.session_state['questionnaire_response']['books_read'] = books_read
                elif survey_pages.current == 9:
                    st.write("#### What is the primary language spoken in your home? (click from the list and others)")
                    languages = ['English', 'Spanish', ]
                    language_options = {}
                    for i in range(len(languages)):
                        language_options[languages[i]] = survey.checkbox(languages[i])
                    language_spoken = []
                    for language in language_options:
                        if language_options[language]:
                            language_spoken.append(language)
                    other_language = survey.text_input('Other')

                    if other_language:
                        language_spoken.append(other_language)
                    st.session_state['questionnaire_response']['language_spoken'] = language_spoken

    elif authentication_status is False:
        st.error('Username or Password is incorrect', icon="⚠️")
elif page == 'Sign Up':
    try:
        if authenticator.register_user('Register user', preauthorization=False):
            st.success('User registered successfully')
            st.balloons()
    except Exception as e:
        st.error(e)

with open('config.yaml', 'w') as file:
    yaml.dump(config, file, default_flow_style=False)
config_drive.put("config.yaml", path="config.yaml")
