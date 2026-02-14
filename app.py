from dotenv import load_dotenv
from openai import OpenAI
import json
import os
import requests
from pypdf import PdfReader
import gradio as gr
from agents import Agent, Runner, function_tool
from pathlib import Path


load_dotenv(override=True)

def log_to_sheet(payload: dict):
    try:
        requests.post(
            os.getenv("GOOGLE_SHEET_WEBHOOK"),
            json=payload,
            timeout=5
        )
    except Exception as e:
        print("Sheet logging failed:", e)

Resume_URL = "https://drive.google.com/file/d/1kjWUU4Pj-8NqRhqx_pjrU_GYPpaqtRQG/view?usp=drive_link"

@function_tool
def get_resume_link() -> dict:
    """Return the resume download link."""
    return {"resume_url": Resume_URL}

@function_tool
def record_user_details(email: str, name: str = "", notes: str = ""):
    log_to_sheet({
        "type": "lead",
        "name": name,
        "email": email,
        "notes": notes
    })
    return {"recorded": "ok"}

@function_tool
def record_unknown_question(question: str):
    log_to_sheet({
        "type": "unknown_question",
        "question": question
    })
    return {"recorded": "ok"}

class MeAgent:
    def __init__(self):
        self.openai = OpenAI()
        self.name = "Danish Kamal Azmi"
        BASE_DIR = Path(__file__).resolve().parent
        linkedin_path = BASE_DIR / "me" / "linkedin.pdf"
        reader = PdfReader(linkedin_path)
        self.linkedin = ""  # ✅
        for page in reader.pages:
            text = page.extract_text()
            if text:
                self.linkedin += text
        summary_path = BASE_DIR / "me" / "summary.txt"
        with open(summary_path, "r", encoding="utf-8") as f:
            self.summary = f.read()


        self.agent = Agent(
            name=self.name,
            model="gpt-5-mini",
            instructions=self._instructions(),
            tools=[
                record_user_details,
                record_unknown_question,
                get_resume_link
            ],
        )

        self.runner = Runner()

    def _instructions(self)-> str:
        return f"""
You are acting as {self.name}. You are answering questions on {self.name}'s website, \
particularly questions related to {self.name}'s career, background, skills and experience. \
Your responsibility is to represent {self.name} for interactions on the website as faithfully as possible. \
You are given a summary of {self.name}'s background and LinkedIn profile which you can use to answer questions. \
Be professional and engaging, as if talking to a potential client or future employer who came across the website. \
If you don't know the answer to any question, use your record_unknown_question tool to record the question that you couldn't answer, even if it's about something trivial or unrelated to career. \
If the user is engaging in discussion, try to steer them towards getting in touch via email; ask for their name (not necessarily required) and email and record it using your record_user_details tool.\
If the user is asking about {self.name}'s resume, use your get_resume_link tool to get the resume link and return it to the user. "

## Summary
{self.summary}

## LinkedIn Profile
{self.linkedin}
"""

    async def chat(self, message, history):
        result = await self.runner.run(self.agent, input=message)
        return result.final_output  
        # Convert history to agent-compatible format if needed
        #messages = []
        #for user_msg, assistant_msg in history:
        #    messages.append({"role": "user", "content": user_msg})
        #    messages.append({"role": "assistant", "content": assistant_msg})

        #messages.append({"role": "user", "content": message})

        #response = self.openai.chat.completions.create(
          #model="gpt-4o-mini",
            #messages=messages,
            #tools=self.tools
        #)
        #return response.choices[0].message.content
    

if __name__ == "__main__":
    me = MeAgent()

    gr.ChatInterface(
        fn=me.chat,
        title="👋 Hi, I’m Danish — your AI guide to my work",
        description=(
            "Welcome! This assistant represents **Danish Kamal Azmi**.\n\n"
            "You can ask about:\n"
            "• Career & experience\n"
            "• Skills & projects\n"
            "• Background & interests\n"
            "• Or request a copy of the resume\n\n"
            "If we get chatting, I may suggest getting in touch, just type in your name and email and I'll get back to you shortly."
        ),
        examples=[
            "Can you tell me about your background?",
            "What kind of roles are you looking for?",
            "What technologies do you work with?",
            "Can I see your resume?",
            "How can I contact you?"
        ],
        chatbot=gr.Chatbot(
            height=420,
            type="messages"   
        ),
        textbox=gr.Textbox(
            placeholder="Ask me anything about my work, background, or experience…",
            container=False
        ),
        submit_btn=None
    ).queue().launch()