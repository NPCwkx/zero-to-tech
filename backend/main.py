import uuid
from fastapi import FastAPI, Request, Response
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from pypinyin import lazy_pinyin, Style
from snownlp import SnowNLP
from storage import save_record, get_history, init_db
from datetime import datetime, timezone
import os
from dotenv import load_dotenv

load_dotenv()

ALLOW_ORIGINS = os.getenv("ALLOW_ORIGINS", "*").split(",")
init_db()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOW_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_credentials=True,
    
)

def get_session_id(request: Request, response: Response):
    sid = request.cookies.get("session_id")
    if not sid:
        sid = uuid.uuid4().hex
        response.set_cookie(
            "session_id", sid,
            httponly=True, samesite="lax",
            max_age= 60 * 60
        )
    return sid

profile =  {
    "heroTitle": "关于我(houduan)",
    "heroSubtitle": "项目，创意，灵感，心得，我的作品",
    "featuredWork": {
        "kicker": "作品",
        "title": "文字实验室",
        "copy": "拼音和情绪，挖掘中文里的细节",
        "linkLabel": "打开作品",
    },
    "identity": {
        "motto": "已识乾坤大，尤怜草木青",
        "learning": "零到全栈",
    },
}

class AnalyzeRequest(BaseModel):
    text: str

@app.get("/api/profile")
def get_profile():
    return profile

def score_label(score):
    if score >= 0.6:
        return "偏积极"
    elif score <= 0.4:
        return "偏消极"
    else:
        return "中性"

########################################################
# from openai import OpenAI

# client = OpenAI(
#     api_key="sk-key",
#     base_url="http://127.0.0.1:8317/v1"
# )

# def get_completion(prompt):
#     response = client.chat.completions.create(
#         model="gemini-3.8-flash-high",
#         messages=[
#             {"role": "user", "content": prompt}
#         ]
#     )
#     return response.choices[0].message.content

########################################################

@app.post("/api/analyze")
def analyze(req: AnalyzeRequest, request: Request, response: Response):
    sid = get_session_id(request, response)
    text = req.text
    score = round(SnowNLP(text).sentiments, 2)
    result = {
        "text": text,
        "score": score,
        "label": score_label(score),
        "pinyin": " ".join(lazy_pinyin(text, style=Style.TONE)),
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    save_record(sid, result)          # 存的时候盖上这个会话的记号
    return result                     # ← 返回体一个字没变，session_id 只走 cookie

@app.get("/api/history")
def history(request: Request, response: Response, limit: int = 10):
    sid = get_session_id(request, response)
    return get_history(sid, limit)    # 只回这个会话自己的
