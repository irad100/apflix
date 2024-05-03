import os
import json
from urllib import response
import requests
import streamlit as st
from openai import OpenAI

client = OpenAI()
movies = ["The Silence of the Lambs", "Pulp Fiction", "The Shawshank Redemption", "Inception", "Jurassic Park", "The Lord of the Rings: The Fellowship of the Ring", "Fight Club", "Titanic", "The Matrix", "Forrest Gump"]
system_message = \
f"""You are a movie reccommendation bot, You should output JSON with the fields: "title", "reason".
The movie you recommend should be from the following list: {*movies,}"""


def get_data(title):
    try:
        response = requests.get(f"https://api.themoviedb.org/3/search/movie?api_key={os.environ['TMDB_API_KEY']}&query={title}").json()
    except requests.exceptions.RequestException as e:
        st.error("Failed to fetch data from the API")
        return
    
    if results := response.get('results', []):
        return results[0]

def validate_response(response):
    try:
        output = json.loads(response.choices[0].message.content)
    except json.JSONDecodeError:
        st.error("The response is not valid JSON")
        return
    if output.keys() != {"title", "reason"}:
        st.error("The response does not contain the correct fields")
        return
    if output["title"] not in movies:
        st.error("The movie title is not in the list of movies")
        return
    if data := get_data(output["title"]):
        if "poster_path" not in data:
            st.error("The response does not contain the poster_path field")
            return
        if "vote_average" not in data:
            st.error("The response does not contain the vote_average field")
            return
    output |= data
    return output

def main():
    if user_description := st.text_area("Enter User Input"):
        response = client.chat.completions.create(model="gpt-3.5-turbo-0125", response_format={ "type": "json_object" }, messages=[{"role": "system", "content": system_message}, {"role": "user", "content": user_description}])
        if output := validate_response(response):
            col1, col2 = st.columns(2)
            with col1:
                st.image(f"https://image.tmdb.org/t/p/original{output['poster_path']}")
            with col2:
                st.write(f"**Title**: {output['title']}")
                st.write(f"**Viewer Ratings**: {output['vote_average']}")
                st.write(f"### Overview\n{output['overview']}")
                st.write(f"### Reason\n{output['reason']}")

if __name__ == "__main__":
    main()