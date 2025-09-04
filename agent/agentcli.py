"""
 Boilerplate to run agent quicly locally. Will create a session and send one message.
"""
from agent import *
import sys
import asyncio

from google.genai import types
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

APP_NAME = "gcpagent"
USER_ID = "user1"
SESSION_ID = "session1"


# Session and Runner
async def setup_session_and_runner(agent):
  session_service = InMemorySessionService()
  session = await session_service.create_session(app_name=APP_NAME,
                                                 user_id=USER_ID,
                                                 session_id=SESSION_ID)
  runner = Runner(agent=agent,
                  app_name=APP_NAME,
                  session_service=session_service)
  return session, runner


async def query(agent, session_service, txt):
  """Call agent for one request """
  runner = Runner(agent=agent,
                  app_name=APP_NAME,
                  session_service=session_service)
  content = types.Content(role='user', parts=[types.Part(text=txt)])

  await session_service.create_session(app_name=APP_NAME,
                                       user_id=USER_ID,
                                       session_id=SESSION_ID)
  events = runner.run(user_id=USER_ID,
                      session_id=SESSION_ID,
                      new_message=content)
  for event in events:
    print(f"\nDEBUG EVENT: {event}\n")
    if event.is_final_response() and event.content:
      final_answer = event.content.parts[0].text.strip()
      print("\n🟢 FINAL ANSWER\n", final_answer, "\n")


async def main():
  session_service = InMemorySessionService()
  root_agent = agent_setup_search()
  await query(root_agent, session_service, sys.argv[1])


if __name__ == "__main__":

  # reasoning_engines.AdkApp overrides env variables and does a lot of guessing using gcloud default credentials.
  #from vertexai.preview import reasoning_engines
  # It sets its own memory, etc - but still needs create session before calling app.stream_query()
  # app = reasoning_engines.AdkApp(
  #     agent=root_agent,
  #     enable_tracing=True,
  # )
  # session = app.create_session(user_id=USER_ID)
  # print(session)
  # app.list_sessions(user_id=USER_ID)
  # session = app.get_session(user_id=USER_ID, session_id=session.id)
  # for event in app.stream_query(
  #     user_id=USER_ID,
  #     session_id=session.id,
  #     message="list runbooks",
  # ):
  #   print(event)

  asyncio.run(main())
