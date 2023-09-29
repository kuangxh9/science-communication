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


def generate_responses(prompt, text):
    prompt = prompt + '\nText: ' + text[:2048]
    conversation = [
        {'role': 'system', 'content': 'You are a helpful assistant.'},
        {'role': 'user', 'content': prompt}
    ]
    try:
        response = openai.ChatCompletion.create(
            model='gpt-3.5-turbo',
            messages=conversation
        )
        return response['choices'][0]['message']['content']
    except:
        st.error('Invalid api key.', icon="⚠️")

@st.cache_resource
def survey(user_name):
    title = user_name + '_survey'
    return ss.StreamlitSurvey(title)

@st.cache_resource
def access_db(db_key):
    deta = Deta(db_key)
    return deta

# connect to/create Deta user database
db_key = st.secrets["deta_key"]
deta = access_db(db_key)
db = deta.Base("user_data")
key = Fernet(st.secrets['fernet_key'])
config_drive = deta.Drive("passwords")
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
    name, authentication_status, username = authenticator.login('Login', 'main')
    if authentication_status:
        init_sidebar.empty()
        app_sidebar = st.sidebar.empty()
        # st.sidebar.write(f'Welcome {name}')
        with app_sidebar:
            page = option_menu(None, ["Main screen", 'History', 'Questionnaire', 'Setup'],
                               icons=['house', 'folder2', 'question-circle', 'gear'],
                               menu_icon="None",
                               default_index=0,
                               styles={})
            authenticator.logout('Logout', 'sidebar', key='unique_key')
        # Fetch user data from the database
        user_data = get_user_data(username)

        # Check if user sets up before

        if page == "Main screen":
            st.title("Plain Language Summary Model")
            st.markdown(
                '''
                #### Instructions
                * **Step 1**: Go to the set up page to set the level of your expertise, your API key and &&
                * **Step 2**: Choose whether you want to generate plain text on abstract or on .pdf
                * **Step 3**:  TO BE ADDED
                '''
            )
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
            default_prompt = 'Provide a concise summary highlighting the key findings and recommendations.'

            # Check if the "Submit" button is clicked
            if st.button("Submit"):
                submit_text = ''

                if abstract_text == '' and uploaded_file == None:
                    st.warning('Please paste Abstract or upload a file.', icon="⚠️")

                if st.session_state.api_key:
                    os.environ["OPENAI_API_KEY"] = st.session_state.api_key
                    chat_mdl = OpenAI(model_name='gpt-4', temperature=0.1)
                else:
                    st.warning('Please fill in api-key in Setup.', icon="⚠️")

                if entire_text:
                    submit_text = entire_text
                else:
                    submit_text = abstract_text
                if chat_mdl is not None and submit_text:
                    st.session_state.draft_response_content = generate_responses(default_prompt, submit_text)
            container = st.empty()
            # Output from function
            container.text_area(label="Plain Language Summary", value=st.session_state.draft_response_content,
                                height=350)
            regenerate_prompt = st.text_input("Additional prompting for regenerating PLS")

            if st.button('Regenerate'):
                if st.session_state.draft_response_content == "":
                    st.warning('Please Generate a PLS first', icon="⚠️")
                elif regenerate_prompt == "":
                    st.warning('Your new prompt is empty', icon="⚠️")
                else:
                    prompt = regenerate_prompt + default_prompt
                    st.session_state.draft_response_content = generate_responses(prompt, entire_text)
                    container.empty()
                    container.text_area(label="Plain Language Summary", value=st.session_state.draft_response_content,
                                        height=350)

            # some function to re-submit prompt and generate new PLS
        elif page == "History":
            st.write('User prompt History TODO')
        elif page == "Setup":
            st.title("Setup")
            # Input boxes with existing data

            if 'api_key' not in st.session_state:
                st.session_state.api_key = ""
            api_input = st.text_input("OpenAI API Token", value=st.session_state.api_key, type='password')
            st.session_state.api_key = api_input

            # principles = st.text_input("My Principles", value=user_data["principles"] if user_data else "")
            writing_style = st.text_area("My Writing Style (Paste Examples)",
                                         value=user_data["writing_style"] if user_data else "",
                                         height=150)

            domain = st.text_input("Domain of Expertise (optional)", value=user_data["domain"] if user_data else "")
            # Update button
            if st.button("Update"):
                db.put(
                    {"key": username, "api": key.encrypt(bytes(api_input, 'utf-8')).decode(),
                     "writing_style": writing_style, "domain": domain})
                st.success('Updating successfully!')
        elif page == "Questionnaire":
            survey = survey(username)
            page_number = 6
            survey_pages = survey.pages(page_number,
                                        on_submit=lambda: st.success("Your responses have been recorded. Thank you!"))
            # st.session_state["__streamlit-survey-data__Pages_"] = survey_pages.current
            st.progress((survey_pages.current + 1) / page_number)
            with survey_pages:
                if survey_pages.current == 0:
                    st.write("#### What is your familiarity or comfort with scientific concepts?")
                    survey.slider(
                        label="sci_familiarity",
                        min_value=1,
                        max_value=5,
                        label_visibility="collapsed",
                    )
                elif survey_pages.current == 1:
                    st.write("#### How much do you use technology?")
                    survey.checkbox('Computers')
                    survey.checkbox('Cell Phones')
                    survey.checkbox('Tablets')
                    survey.checkbox('Internet')
                    survey.checkbox('GPS')
                elif survey_pages.current == 2:
                    st.write("#### Do you use social media?")
                    social_media_freq = survey.slider(
                        label="social_media_freq",
                        min_value=1,
                        max_value=5,
                        label_visibility="collapsed",
                    )
                    if social_media_freq > 1:
                        st.write("#### Please select all that you use.")
                        survey.checkbox('Facebook')
                        survey.checkbox('X (Twitter)')
                        survey.checkbox('Reddit')
                        survey.checkbox('Instagram')
                elif survey_pages.current == 3:
                    st.write("#### Do you read the news or watch/listen to the news?")
                    read_news = survey.radio(
                        label="read_news",
                        options=["NA", "Yes", "No"],
                        index=0,
                        label_visibility="collapsed",
                        horizontal=True,
                    )
                elif survey_pages.current == 4:
                    language = survey.text_input("#### What is the primary language spoken in your home?")
                elif survey_pages.current == 5:
                    st.write("#### Do you speak other languages?")
                    survey.checkbox('L1')
                    survey.checkbox('L2')
                    survey.checkbox('L3')
                    survey.checkbox('L4')
                    survey.text_input('Other Language')
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
