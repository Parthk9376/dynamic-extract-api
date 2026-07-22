import os
import json
from datetime import datetime
from typing import Dict, Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

app = FastAPI(title="Dynamic Extract API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ExtractRequest(BaseModel):
    text: str
    schema: Dict[str, str]


def convert(value, typ):
    if value is None:
        return None

    try:
        typ = typ.lower()

        if typ == "string":
            return str(value)

        elif typ == "integer":
            return int(value)

        elif typ == "float":
            return float(value)

        elif typ == "boolean":
            if isinstance(value, bool):
                return value

            if str(value).lower() in ["true", "yes", "1"]:
                return True

            if str(value).lower() in ["false", "no", "0"]:
                return False

            return None

        elif typ == "date":
            if isinstance(value, str):

                for fmt in [
                    "%Y-%m-%d",
                    "%d-%m-%Y",
                    "%d/%m/%Y",
                    "%d %B %Y",
                    "%d %b %Y"
                ]:
                    try:
                        return datetime.strptime(value, fmt).strftime("%Y-%m-%d")
                    except:
                        pass

            return None

    except:
        return None

    return value


@app.get("/")
def root():
    return {"status": "ok"}


@app.post("/dynamic-extract")
def dynamic_extract(req: ExtractRequest):

    prompt = f"""
You are an information extraction engine.

Return ONLY valid JSON.

Rules:

1. Return exactly the keys in the schema.
2. No markdown.
3. No explanation.
4. Missing values -> null.
5. Numbers must be numbers.
6. Boolean must be true/false.
7. Dates must be YYYY-MM-DD.

Schema:
{json.dumps(req.schema)}

Text:
{req.text}
"""

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {
                "role": "system",
                "content": "Return only JSON."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        response_format={"type": "json_object"}
    )

    raw = response.choices[0].message.content

    try:
        extracted = json.loads(raw)
    except:
        extracted = {}

    final = {}

    for key, typ in req.schema.items():
        final[key] = convert(extracted.get(key), typ)

    return final
