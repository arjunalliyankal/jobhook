from groq import Groq
import json
from flask import current_app
from .prompts import (
    RESUME_PARSE_PROMPT,
    RESUME_SUGGESTIONS_PROMPT,
    COVER_LETTER_PROMPT,
    SKILL_GAP_ADVICE_PROMPT
)


class GroqClient:
    def __init__(self):
        self._client = None

    @property
    def client(self):
        if self._client is None:
            self._client = Groq(api_key=current_app.config["GROQ_API_KEY"])
        return self._client

    def _chat(self, prompt: str, system: str = "You are a helpful assistant.",
              max_tokens: int = 2000, temperature: float = 0.3, json_mode: bool = False) -> str:
        kwargs = {
            "model": current_app.config["GROQ_MODEL"],
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
            
        response = self.client.chat.completions.create(**kwargs)
        return response.choices[0].message.content.strip()

    def parse_resume(self, resume_text: str) -> dict:
        prompt = RESUME_PARSE_PROMPT.format(resume_text=resume_text[:4000])
        raw = self._chat(prompt, system="You are a precise JSON extractor.", json_mode=True)
        try:
            # Strip any markdown code fences if present
            raw = raw.replace("```json", "").replace("```", "").strip()
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"error": "Failed to parse resume", "raw": raw}

    def get_resume_suggestions(self, resume_text: str, jd_text: str,
                                missing_keywords: list, score: int = 0,
                                parsed_experience: list = None) -> dict:
        if parsed_experience is None:
            parsed_experience = []
            
        prompt = RESUME_SUGGESTIONS_PROMPT.format(
            resume_text=resume_text[:3000],
            jd_text=jd_text[:2000],
            missing_keywords=", ".join(missing_keywords),
            score=score,
            parsed_experience=json.dumps(parsed_experience)
        )
        raw = self._chat(prompt, json_mode=True, max_tokens=3000)
        try:
            raw = raw.replace("```json", "").replace("```", "").strip()
            return json.loads(raw)
        except json.JSONDecodeError:
            return {
                "improvements": [], 
                "keyword_suggestions": [], 
                "language_upgrades": [],
                "revised_summary": "",
                "revised_experience": []
            }

    def generate_cover_letter(self, name: str, role: str, company: str,
                               skills: list, achievements: list, jd_text: str) -> str:
        prompt = COVER_LETTER_PROMPT.format(
            name=name,
            role=role,
            company=company,
            skills=", ".join(skills[:8]),
            achievements="\n".join(f"- {a}" for a in achievements[:5]),
            jd_text=jd_text[:2000]
        )
        return self._chat(prompt, temperature=0.6, max_tokens=800)

    def get_skill_gap_advice(self, target_role: str,
                              current_skills: list, missing_skills: list) -> dict:
        prompt = SKILL_GAP_ADVICE_PROMPT.format(
            target_role=target_role,
            current_skills=", ".join(current_skills),
            missing_skills=", ".join(missing_skills[:10])
        )
        raw = self._chat(prompt, json_mode=True)
        try:
            raw = raw.replace("```json", "").replace("```", "").strip()
            return json.loads(raw)
        except json.JSONDecodeError:
            return {}
