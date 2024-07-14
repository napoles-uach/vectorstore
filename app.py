import streamlit as st
from openai import OpenAI
import os
import json
import time

# Initialize the OpenAI client
client = OpenAI(api_key=st.secrets["gpt_key"])

# Path to the local PDF file
local_file_path = "paper.pdf"
vector_store_id_path = "vector_store_id.json"
file_id_path = "file_id.json"

def save_vector_store_id(vector_store_id):
    with open(vector_store_id_path, 'w') as f:
        json.dump({"vector_store_id": vector_store_id}, f)

def load_vector_store_id():
    if os.path.exists(vector_store_id_path):
        with open(vector_store_id_path, 'r') as f:
            data = json.load(f)
            return data.get("vector_store_id")
    return None

def save_file_id(file_id):
    with open(file_id_path, 'w') as f:
        json.dump({"file_id": file_id}, f)

def load_file_id():
    if os.path.exists(file_id_path):
        with open(file_id_path, 'r') as f:
            data = json.load(f)
            return data.get("file_id")
    return None

vector_store_id = load_vector_store_id()
file_id = load_file_id()

if vector_store_id is None:
    # Create a vector store called "Paper" if it does not exist
    with st.spinner('Creating vector store...'):
        vector_store = client.beta.vector_stores.create(name="Paper")
        vector_store_id = vector_store.id
        save_vector_store_id(vector_store_id)
else:
    # Use the existing vector store
    with st.spinner('Using existing vector store...'):
        vector_store = client.beta.vector_stores.retrieve(vector_store_id)

if file_id is None:
    if os.path.exists(local_file_path):
        # Ready the file for upload to OpenAI
        file_streams = [open(local_file_path, "rb")]

        try:
            # Use the upload and poll SDK helper to upload the files, add them to the vector store,
            # and poll the status of the file batch for completion.
            with st.spinner('Uploading files and polling status...'):
                file_batch = client.beta.vector_stores.file_batches.upload_and_poll(
                  vector_store_id=vector_store.id, files=file_streams
                )

            st.success('Files uploaded and processed successfully!')
            st.write(f"Status: {file_batch.status}")
            st.write(f"File counts: {file_batch.file_counts}")

            # Upload the user provided file to OpenAI
            with st.spinner('Uploading file to assistant...'):
                message_file = client.files.create(
                  file=open(local_file_path, "rb"), purpose="assistants"
                )
                file_id = message_file.id
                save_file_id(file_id)

        finally:
            # Ensure all file streams are closed
            for file_stream in file_streams:
                file_stream.close()
    else:
        st.error("The file 'paper.pdf' does not exist. Please make sure the file is in the correct location.")
else:
    st.success('Using previously uploaded file.')

# Create an assistant
with st.spinner('Creating assistant...'):
    paper_assistant = client.beta.assistants.create(
      name="Paper Assistant",
      instructions="You are an author of a research paper. Use your knowledge base to answer questions about the research related to molecular packing. Use latex to show mathematical formulas. (remember, for  equations or math expressions use double $$ symbol to render correctly, example $$x^2$$)",
      model="gpt-4o",
      tools=[{"type": "file_search"}],
    )

    # Update the assistant to use the vector store
    paper_assistant = client.beta.assistants.update(
      assistant_id=paper_assistant.id,
      tool_resources={"file_search": {"vector_store_ids": [vector_store_id]}},
    )

ask = st.text_input("Ask")
if ask:
    with st.spinner('Processing your request...'):
        # Create a thread and attach the file to the message
        thread = client.beta.threads.create(
          messages=[
            {
              "role": "user",
              "content": ask,
              "attachments": [
                {"file_id": file_id, "tools": [{"type": "file_search"}]}
              ],
            }
          ]
        )

        # Run the assistant and poll for completion
        run = client.beta.threads.runs.create_and_poll(
          thread_id=thread.id,
          assistant_id=paper_assistant.id,
          instructions="Please address the user as Dear reader. The user has a premium account."
        )

        if run.status == 'completed':
            # List the messages in the thread
            messages = client.beta.threads.messages.list(thread_id=thread.id)
            # Function to extract text value from the messages
            def extraer_valor(sync_cursor_page):
                for mensaje in sync_cursor_page.data:
                    for bloque in mensaje.content:
                        if bloque.type == 'text':
                            yield bloque.text.value + " "
                            time.sleep(0.1)

            # Example usage (replace 'sync_cursor_page' with your actual object)
            st.write_stream(extraer_valor(messages))
        else:
            st.warning(f"Run status: {run.status}")
