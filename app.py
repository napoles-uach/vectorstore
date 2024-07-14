import streamlit as st
from openai import OpenAI
from rich import print

#openai.api_key = st.secrets["gpt_key"]
# Initialize the OpenAI client
client = OpenAI(api_key=st.secrets["gpt_key"])

# Create a vector store called "Paper"
vector_store = client.beta.vector_stores.create(name="Paper")

# Ready the files for upload to OpenAI
file_paths = ["paper.pdf"]
file_streams = [open(path, "rb") for path in file_paths]

try:
    # Use the upload and poll SDK helper to upload the files, add them to the vector store,
    # and poll the status of the file batch for completion.
    file_batch = client.beta.vector_stores.file_batches.upload_and_poll(
      vector_store_id=vector_store.id, files=file_streams
    )

    # Print the status and the file counts of the batch to see the result of this operation.
    print(file_batch.status)
    print(file_batch.file_counts)

    # Create an assistant
    paper_assistant = client.beta.assistants.create(
      name="Paper Assistant",
      instructions="You are an author of a research paper. Use your knowledge base to answer questions about the research related to molecular packing.",
      model="gpt-4o",
      tools=[{"type": "file_search"}],
    )

    # Update the assistant to use the vector store
    paper_assistant = client.beta.assistants.update(
      assistant_id=paper_assistant.id,
      tool_resources={"file_search": {"vector_store_ids": [vector_store.id]}},
    )

    # Upload the user provided file to OpenAI
    message_file = client.files.create(
      file=open("paper.pdf", "rb"), purpose="assistants"
    )

    # Create a thread and attach the file to the message
    thread = client.beta.threads.create(
      messages=[
        {
          "role": "user",
          "content": "why is this paper important?",
          "attachments": [
            {"file_id": message_file.id, "tools": [{"type": "file_search"}]}
          ],
        }
      ]
    )

    # The thread now has a vector store with that file in its tool resources.
    print(thread.tool_resources.file_search)

    # Run the assistant and poll for completion
    run = client.beta.threads.runs.create_and_poll(
      thread_id=thread.id,
      assistant_id=paper_assistant.id,
      instructions="Please address the user as Jane Doe. The user has a premium account."
    )

    if run.status == 'completed': 
      # List the messages in the thread
      messages = client.beta.threads.messages.list(thread_id=thread.id)
      print(messages)
    else:
      print(f"Run status: {run.status}")

    # Function to extract text value from the messages
    def extraer_valor(sync_cursor_page):
      for mensaje in sync_cursor_page.data:
        for bloque in mensaje.content:
          if bloque.type == 'text':
            return bloque.text.value

    # Example usage (replace 'sync_cursor_page' with your actual object)
    valor = extraer_valor(messages)
    print(valor)
  
finally:
    # Ensure all file streams are closed
    for file_stream in file_streams:
        file_stream.close()
