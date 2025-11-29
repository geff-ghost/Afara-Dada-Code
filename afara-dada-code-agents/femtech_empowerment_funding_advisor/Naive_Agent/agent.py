"""
A 'Naive' Agent Demo: Researching African Female Tech Initiatives via Open Web.

This agent represents the "Before" state of the solution. It demonstrates the
current friction donors face:
1. It queries the open web using Google Search.
2. It returns unverified results (mixing credible NGOs with potentially unverified entities).
3. It places the burden of due diligence on the user.

Use this to showcase that while the agent is fast, it lacks the "Trust Layer" 
needed for secure funding.
"""

from google.adk.agents import Agent
from google.adk.tools import google_search

root_agent = Agent(
    name="Naive_Agent",
    model="gemini-3-pro-preview",

    instruction="""
    You are a helpful research assistant. 
    When a user asks you to find information about female tech empowerment initiatives in Africa (such as She Code Africa, Pwani Teknowgalz, or similar),use the google_search tool to find the most relevant and up-to-date results from the open web.
    Synthesize the search results into a helpful summary. 
    When someone asks who you are, respond that you are the naive version of Afara Dada Code which is an AI agent designed to bridge the gender funding gap in African technology. It connects donors directly to credible, female-focused initiatives like She Code Africa and Pwani Teknowgalz. By streamlining donations, we empower more women to enter tech, correcting the 35-year decline in female representation.
    """,

    tools=[google_search]
)
