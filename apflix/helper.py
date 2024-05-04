from openai import OpenAI
import requests
import boto3

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
 
def get_secret(secret_id):
    sm = boto3.client('secretsmanager', region_name='us-east-1')
    return sm.get_secret_value(SecretId=secret_id)['SecretString']

def get_movie_data(title):
    try:
        response = requests.get(
            f"https://api.themoviedb.org/3/search/movie?api_key={get_secret('TMDB_API_KEY')}&query={title}"
        ).json()
    except requests.exceptions.RequestException as e:
        return

    if results := response.get("results", []):
        return results[0]

def main():
    client = OpenAI()
    assistant = client.beta.assistants.create(
    name="Movie Recommendation Bot",
    instructions="You are a movie recommendation bot, You should output JSON with the fields: \"title\", \"reason\".",
    model="gpt-3.5-turbo-0125",
    response_format={"type": "json_object"},
    tools=[{"type": "file_search"}],
    )

    # Create a vector store caled "Movies"
    vector_store = client.beta.vector_stores.create(name="Movies")

    # Ready the files for upload to OpenAI
    for movie in MOVIES:
        data = get_movie_data(movie)
        if data:
            client.beta.vector_stores.add_vectors(
                vector_store_id=vector_store.id,
                vectors=[{"data": data["title"], "metadata": data}],
            )
    file_paths = ["edgar/goog-10k.pdf", "edgar/brka-10k.txt"]
    file_streams = [open(path, "rb") for path in file_paths]

    # Use the upload and poll SDK helper to upload the files, add them to the vector store,
    # and poll the status of the file batch for completion.
    file_batch = client.beta.vector_stores.file_batches.upload_and_poll(
    vector_store_id=vector_store.id, files=file_streams
    )

    # You can print the status and the file counts of the batch to see the result of this operation.
    print(file_batch.status)
    print(file_batch.file_counts)

    assistant = client.beta.assistants.update(
    assistant_id=assistant.id,
    tool_resources={"file_search": {"vector_store_ids": [vector_store.id]}},
    )

if __name__ == "__main__":
    main()