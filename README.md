## Science Communication Streamlit App

To run `streamlit_app.py` locally, please make sure that:
* `secrets.toml` and `credentials.toml` are under directory `C:\Users\<username>\.streamlit\`. 
* `pip install -r requirements.txt`

Then `streamlit run streamlit_app.py` to test it locally.

### Update 09/28
* Fixed KeyError issue
    - This problem might be caused by Streamlit auto-rerun mechanism. Some instances / variables initialized (`None`) outside of functions will execute even they are assigned with other values in certain pages. 
    - The weird `st.session_state.__streamlit-survey-data` KeyError is raised possibly by appending existing survey components to a `None` survey or to a new survey instance (?) (not confirmed).
    - It is fixed by defining a function `survey(username)` to return `ss.StreamlitSurvey(title)` and adding a decorator `@st.cache_data`. It keeps the original survey instance while refreshing page.