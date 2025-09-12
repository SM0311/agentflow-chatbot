import time
import streamlit as st
from langGraph_backend import chatbot
from langchain_core.messages import HumanMessage

CONFIG = {'configurable': {'thread_id': 'thread'}}

if 'message_history' not in st.session_state:
    st.session_state['message_history'] = []

# render previous messages
for message in st.session_state['message_history']:
    with st.chat_message(message['role']):
        st.text(message['content'])

user_input = st.chat_input('Type here')

if user_input:
    # add user message
    st.session_state['message_history'].append({'role': 'user', 'content': user_input})
    with st.chat_message('user'):
        st.text(user_input)

    # Prepare assistant placeholder (single chat message block)
    assistant_placeholder = st.chat_message('assistant')
    # inside that block put a text placeholder to update
    with assistant_placeholder:
        live_text = st.empty()

    # We'll stream from the backend only once
    # Adjust stream config if your backend supports chunk_size / interval
    stream_config = {
        'configurable': {'thread_id': 'thread-1'}
        # possibly add other backend controls here if supported: 'chunk_size': 64, 'token_delay': 0.02
    }

    # Buffering & rate-limiting settings
    FLUSH_INTERVAL = 0.08  # seconds between forced UI updates
    last_flush = time.monotonic()
    buffered_text = ""
    flushed_text = ""  # what we've already written to the UI

    # If chatbot.stream yields (message_chunk, metadata)
    for message_chunk, metadata in chatbot.stream(
            {'messages': [HumanMessage(content=user_input)]},
            config=stream_config,
            stream_mode='messages'  # keep same mode you used
    ):
        # message_chunk.content may be just a small fragment
        fragment = getattr(message_chunk, "content", "") or str(message_chunk)
        buffered_text += fragment

        # flush when we see sentence-ending punctuation OR if FLUSH_INTERVAL passed
        now = time.monotonic()
        should_flush = False
        if any(p in buffered_text for p in ('.', '?', '!')):  # crude sentence boundary detection
            should_flush = True
        if now - last_flush >= FLUSH_INTERVAL:
            should_flush = True

        if should_flush:
            # move buffered_text to flushed_text, update UI
            flushed_text += buffered_text
            live_text.text(flushed_text)   # update visible message
            buffered_text = ""
            last_flush = now

            # optional: tiny sleep to make typing visible (tweak as needed)
            time.sleep(0.02)

    # After stream ends, ensure we append any remaining buffer
    if buffered_text:
        flushed_text += buffered_text
        live_text.text(flushed_text)

    # store final assistant text into session state
    st.session_state['message_history'].append({'role': 'assistant', 'content': flushed_text})
