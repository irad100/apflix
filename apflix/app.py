import json
import re
import requests
import streamlit as st
from openai import OpenAI
import boto3

def get_secret(secret_id):
    """
    Get the secret value from AWS Secrets Manager
    :param secret_id: The ID of the secret
    """
    sm = boto3.client('secretsmanager', region_name='us-east-1')
    return sm.get_secret_value(SecretId=secret_id)['SecretString']

def get_movie_data(title):
    """
    Get the movie data from title name using the TMDB API
    :param title: The title of the movie
    """
    try:
        # Get the movie data from the title
        response = requests.get(
            f"https://api.themoviedb.org/3/search/movie?api_key={get_secret('TMDB_API_KEY')}&query={title}"
        ).json()
    except requests.exceptions.RequestException:
        return

    # Check if the response contains movie results
    if results := response.get("results", []):
        return results[0]

def get_movie_data_from_url(imdb_url):
    """
    Get the movie data from the IMDb URL using the TMDB API
    :param imdb_url: The IMDb URL of the movie
    """
    # Check if the URL is a valid IMDb URL
    # IMDb URL format: https://www.imdb.com/title/tt1234567/<query_string>
    if not (match := re.fullmatch(r"https:\/\/www\.imdb\.com\/title\/(tt\d{7,8})\/?(\?[=&\w]*)?", imdb_url)):
        st.error("The URL is not a valid IMDb URL")
        return
    
    imdb_id = match.group(1)
    try:
        # Get the movie data from the IMDb ID
        response = requests.get(f"https://api.themoviedb.org/3/find/{imdb_id}?api_key={get_secret('TMDB_API_KEY')}&external_source=imdb_id"
            ).json()
    except requests.exceptions.RequestException:
        return

    # Check if the response contains movie results
    if results := response.get("movie_results", []):
        return results[0]

def validate_response(messages):
    """
    Validate the assistant's response
    :param messages: The messages from the assistant
    """
    # Check if the response is in a valid JSON format
    try:
        message = str(messages[0].content[0].text.value)
        output = json.loads(message)
    except json.JSONDecodeError:
        st.error("The response is not in a valid JSON format")
        return
    
    # Check if the response contains the correct fields
    if output.keys() != {"title", "reason"}:
        st.error("The response does not contain the correct fields")
        return
    
    # Get the movie data
    if not (data := get_movie_data(output["title"])):
        st.error("The movie data could not be retrieved")
        return
    
    # Check if the response contains the correct movie data
    if "poster_path" not in data:
        st.error("The response does not contain the poster_path field")
        return
    if "vote_average" not in data:
        st.error("The response does not contain the vote_average field")
        return
    
    # Add the movie data to the response
    output |= data
    return output


def main():
    st.set_page_config(page_title="APFlix", page_icon=":clapper:")
    # Create a new thread to interact with the assistant
    client = OpenAI(api_key=get_secret('OPENAI_API_KEY'))
    thread = client.beta.threads.create()
    # Create a new run in the thread based on user input
    if user_description := st.text_area("Enter User Input"):
        client.beta.threads.messages.create(
            thread_id=thread.id, role="user", content=user_description,
        )
        run = client.beta.threads.runs.create_and_poll(
        thread_id=thread.id,
        assistant_id="asst_QOfHEUkkGv7aBri9RHpMcxbF",
        )
        # Get the assistant's response
        messeges = list(client.beta.threads.messages.list(thread_id=thread.id, run_id=run.id))

        # Validate the response
        if output := validate_response(messeges):
            # Display the movie data
            col1, col2 = st.columns(2)
            with col1:
                st.image(f"https://image.tmdb.org/t/p/original{output['poster_path']}")
            with col2:
                st.write(f"**Title**: {output['title']}")
                st.write(f"**Viewer Ratings**: {output['vote_average']}")
                st.write(f"### Overview\n{output['overview']}")
                st.write(f"### Reason\n{output['reason']}")

    # Add a new movie to the vector store
    with st.expander("Add New Movie :clapper:"):
        if new_movie := st.text_input("Enter IMDb URL"):
            # Get the movie data from the URL
            if data := get_movie_data_from_url(new_movie):
                with open(f"assets/{data['id']}.json", "w") as f:
                    json.dump(data, f, indent=4)
                # Upload the movie data to the vector store
                movie_file = client.files.create(file=open(f"assets/{data['id']}.json", "rb"), purpose="assistants")
                client.beta.vector_stores.files.create_and_poll(
                        vector_store_id="vs_SWvUYppf11XGUVDcQ3LXWU0j",
                        file_id=movie_file.id
                        )
                st.success(f"Added {data['title']} to the list of movies")
            else:
                st.error("The movie data could not be retrieved")


if __name__ == "__main__":
    main()
