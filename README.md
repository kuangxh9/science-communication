## Science Communication Streamlit App

To run `streamlit_app.py` locally, please make sure that:
* `secrets.toml` and `credentials.toml` are under directory `C:\Users\<username>\.streamlit\`. 
* `pip install -r requirements.txt`

Then `streamlit run streamlit_app.py` to test it locally.<br>
Online web link: https://huggingface.co/spaces/yuki-816/science-communication

### Update 10/20
* Updated `generate_response` parameters.
* Updated `user_context` template in `generate_response` function.
* Modified survey questions in `Questionnaire` page.
* Move `paper familiarity` question to the home page.
* Stored user data as dictionary in Deta.

### Update 10/06
* Updated `user_context` template in `generate_response` function.
* Properly stored user response in questionnaire to Deta database
* Restructured `Questionnaire` page
* Other Issue:
    - For running speed, `generate_response` function only takes first `2048` characters of abstract or uploaded file content
    - Running speed is somehow slower while regenerating response with additional prompts.

### Update 10/04
* `KeyError` for `name` of `streamlit-authen` only exists when hosting on Streamlit Cloud
* Migrate the app to Huggingface: https://huggingface.co/spaces/yuki-816/science-communication
* Modified questionnaire response value to be stored in database
* Updated `generate_response` function to take users response (else `''`)

### Update 10/03
* Modified questionnaire questions and store user response in Deta database as Dictionary
* Implemented Sucheel's `generate_response` function
* Replaced the testing Deta key
* Issue on `generate_response` function:
    - The function can only generate response with text length less or equal to 4197
    - The `social_media_usage` is not included in the questionnaire. Template of `user_context` should be modified later.

### Update 09/28
* Fixed KeyError issue
    - This problem might be caused by Streamlit auto-rerun mechanism. Some instances / variables initialized (`None`) outside of functions will execute even they are assigned with other values in certain pages. 
    - The weird `st.session_state.__streamlit-survey-data` KeyError is raised possibly by appending existing survey components to a `None` survey or to a new survey instance (?) (not confirmed).
    - It is fixed by defining a function `survey(username)` to return `ss.StreamlitSurvey(title)` and adding a decorator `@st.cache_data`. It keeps the original survey instance while refreshing page.
* Deleted `Education Level`  in `Set Up` page.
* Streamlit Cloud Hosting: https://science-communication.streamlit.app/

