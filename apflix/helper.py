import os
import json
import requests
from openai import OpenAI

MOVIES = [
    "The Silence of the Lambs",
    "Pulp Fiction",
    "The Shawshank Redemption",
    "Inception",
    "Jurassic Park",
    "The Lord of the Rings: The Fellowship of the Ring",
    "Fight Club",
    "Titanic",
    "The Matrix",
    "Forrest Gump",
]

SYSTEM_MESSEGE = """
You are a movie recommendation bot.
Return ONLY a JSON format object (without the prefix ```json and postfix ```) with title and reason fields in your response
For example (Response format):
{"title": "The Matrix", "reason": "It's a classic sci-fi movie."}
Do not include any other information in your response.
Do not include citations or references in your response.
"""


def get_movie_data(title):
    """
    Get the movie data from title name using the TMDB API
    :param title: The title of the movie
    """
    try:
        # Get the movie data from the title
        response = requests.get(
            f"https://api.themoviedb.org/3/search/movie?api_key={os.get_env('TMDB_API_KEY')}&query={title}"
        ).json()
    except requests.exceptions.RequestException:
        return

    # Check if the response contains movie results
    if results := response.get("results", []):
        return results[0]


def main():
    client = OpenAI()
    assistant = client.beta.assistants.create(
        name="Movie Recommendation Bot",
        instructions=SYSTEM_MESSEGE,
        model="gpt-4-turbo",
        tools=[{"type": "file_search"}],
    )

    # Create a vector store caled "Movies"
    vector_store = client.beta.vector_stores.create(name="Movies")

    # testing the vector store with initial data
    movie_ids = []
    # Ready the files for upload to OpenAI
    for movie in MOVIES:
        data = get_movie_data(movie)
        if data:
            movie_ids.append(data["id"])
            with open(f"assets/{data['id']}.json", "w") as f:
                json.dump(data, f, indent=4)

    # Create a list of file streams to upload to OpenAI
    movie_data_streams = [
        open(f"assets/{movie_id}.json", "rb") for movie_id in movie_ids
    ]
    # Use the upload and poll SDK helper to upload the files, add them to the vector store,
    # and poll the status of the file batch for completion.
    file_batch = client.beta.vector_stores.file_batches.upload_and_poll(
        vector_store_id=vector_store.id, files=movie_data_streams
    )

    print(file_batch.file_counts)

    # Update the assistant with the vector store
    assistant = client.beta.assistants.update(
        assistant_id=assistant.id,
        tool_resources={"file_search": {"vector_store_ids": [vector_store.id]}},
    )

    print(f"{assistant.id} is ready to use the vector store {vector_store.id}")


if __name__ == "__main__":
    main()
