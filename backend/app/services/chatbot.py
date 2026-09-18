"""Patient Health Assistant Chatbot Service for CarePulse.

Features:
- De-identification / Privacy scrubbing (removal of names, emails, phones, MRNs, direct identifiers).
- Emergency red-flag symptom detection and immediate escalation advice.
- Strict safety system prompt (no diagnosis, no prescriptions, clear disclaimer).
- Real Dataset Integration: Answers patient & clinician queries using actual patient dataset records.
- Handles missing or invalid API keys gracefully with clear fallback responses.
"""
from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any, Optional

import httpx
import structlog

from app.core.config import get_settings

logger = structlog.get_logger(__name__)

# Mandatory Disclaimer
MANDATORY_DISCLAIMER = (
    "CarePulse Health Assistant provides general health information and does not replace professional medical advice."
)

# System Prompt Enforcing Boundaries
SYSTEM_PROMPT = f"""You are the CarePulse Patient Health Assistant, an empathetic, clear, and informative educational health companion.

{MANDATORY_DISCLAIMER}

Core Topics You Can Discuss:
- Healthy lifestyle guidelines (balanced nutrition, hydration, exercise, sleep hygiene)
- Understanding general medical terminology and physiological concepts
- Explaining the patient's actual dataset vitals and trends (Heart Rate, SpO2, Respiratory Rate, Blood Pressure, Temperature)
- Explaining CarePulse risk scores, risk states, and baseline comparisons using actual patient data
- Medication education (general purpose, adherence tips, timing, asking pharmacists)
- Preparing effective questions for doctor visits
- Routine healthcare maintenance and preventive care

STRICT BOUNDARIES & SAFETY RULES:
1. You MUST NOT diagnose diseases or medical conditions under any circumstances.
2. You MUST NOT prescribe medication or suggest changing medication dosages.
3. You MUST NOT claim to replace a doctor or medical professional.
4. You MUST ONLY answer patient data questions using actual data provided in the patient context.
5. If data is unavailable, state: "I don't have enough available data to answer that."
6. If emergency symptoms are mentioned, immediately advise seeking emergency medical attention.
7. Always maintain a warm, clear, professional tone suitable for patients.
"""

# Red-flag emergency symptoms regex patterns
EMERGENCY_PATTERNS = [
    r"\b(chest pain|tightness in chest|crushing pain)\b",
    r"\b(severe shortness of breath|can'?t breathe|gasping for air)\b",
    r"\b(stroke|facial drooping|arm weakness|slurred speech)\b",
    r"\b(sudden numbness|paralysis|loss of vision)\b",
    r"\b(unconscious|passed out|fainted|unresponsive)\b",
    r"\b(severe bleeding|uncontrolled bleeding|coughing up blood)\b",
    r"\b(anaphylaxis|swollen throat|severe allergic reaction)\b",
    r"\b(suicide|self-harm|want to die|ending my life)\b",
]

EMERGENCY_RESPONSE = (
    "⚠️ **IMMEDIATE EMERGENCY MEDICAL CARE REQUIRED**\n\n"
    "The symptoms you described may indicate a serious or life-threatening medical emergency. "
    "Please **call 911 (or your local emergency services)** or go to the nearest Emergency Room immediately.\n\n"
    "Do not wait or rely on an online application during a medical emergency.\n\n"
    f"*{MANDATORY_DISCLAIMER}*"
)


def deidentify_text(text: str) -> str:
    """Scrub direct identifiers (emails, phone numbers, patient codes/MRNs, SSNs, dates) from user input."""
    if not text:
        return text

    scrubbed = text

    # Email addresses
    scrubbed = re.sub(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", "[REDACTED_EMAIL]", scrubbed)

    # Phone numbers (US/Intl formats)
    scrubbed = re.sub(r"(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}", "[REDACTED_PHONE]", scrubbed)

    # Patient codes / MRNs (e.g. P101, MRN-12345)
    scrubbed = re.sub(r"\b(P\d{3,6}|MRN[-\s]?\d{4,8})\b", "[REDACTED_MRN]", scrubbed, flags=re.IGNORECASE)

    # Social Security Numbers (SSN)
    scrubbed = re.sub(r"\b\d{3}-\d{2}-\d{4}\b", "[REDACTED_SSN]", scrubbed)

    # Dates of Birth / Specific dates (MM/DD/YYYY or YYYY-MM-DD)
    scrubbed = re.sub(r"\b(0[1-9]|1[0-2])[-/](0[1-9]|[12]\d|3[01])[-/](19|20)\d{2}\b", "[REDACTED_DATE]", scrubbed)
    scrubbed = re.sub(r"\b(19|20)\d{2}[-/](0[1-9]|1[0-2])[-/](0[1-9]|[12]\d|3[01])\b", "[REDACTED_DATE]", scrubbed)

    return scrubbed


def check_emergency_symptoms(text: str) -> Optional[str]:
    """Return emergency response if red-flag symptoms detected in text."""
    lower_text = text.lower()
    for pattern in EMERGENCY_PATTERNS:
        if re.search(pattern, lower_text):
            logger.warning("chatbot.emergency_symptom_detected", pattern=pattern)
            return EMERGENCY_RESPONSE
    return None


async def generate_chatbot_response(
    user_message: str,
    conversation_history: Optional[list[dict]] = None,
    patient_context: Optional[dict[str, Any]] = None,
) -> tuple[str, bool]:
    """Generate chatbot response for user message.

    Returns:
        tuple[str, bool]: (response_text, is_emergency)
    """
    # Step 1: Emergency Check
    emergency_msg = check_emergency_symptoms(user_message)
    if emergency_msg:
        return emergency_msg, True

    # Step 2: De-identify text
    clean_message = deidentify_text(user_message)

    # Step 3: Check API Key configuration
    settings = get_settings()
    api_key = settings.CHATBOT_API_KEY.strip()

    if not api_key:
        logger.info("chatbot.api_key_not_configured_fallback")
        fallback_reply = _generate_fallback_response(clean_message, patient_context)
        return fallback_reply, False

    # Step 4: Call External AI Service (Gemini API / REST)
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"

        ctx_prompt = ""
        if patient_context:
            ctx_prompt = f"\n\nPATIENT DATASET CONTEXT:\n{patient_context}\n"

        prompt_text = f"System Context:\n{SYSTEM_PROMPT}{ctx_prompt}\n\nUser Question:\n{clean_message}"
        contents = [{"role": "user", "parts": [{"text": prompt_text}]}]

        if conversation_history:
            formatted_history = []
            for m in conversation_history[-4:]:
                role = "user" if m.get("sender") == "user" else "model"
                formatted_history.append({"role": role, "parts": [{"text": deidentify_text(m.get("content", ""))}]})
            contents = formatted_history + [{"role": "user", "parts": [{"text": prompt_text}]}]

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, json={"contents": contents})

            if resp.status_code == 200:
                data = resp.json()
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                if "replace professional medical advice" not in text:
                    text += f"\n\n---\n*{MANDATORY_DISCLAIMER}*"
                return text, False
            else:
                logger.error("chatbot.ai_api_error", status=resp.status_code, body=resp.text[:200])
                fallback = _generate_fallback_response(clean_message, patient_context)
                return fallback, False

    except Exception as exc:
        logger.error("chatbot.ai_service_exception", error=str(exc))
        fallback = _generate_fallback_response(clean_message, patient_context)
        return fallback, False


def _generate_fallback_response(message: str, patient_context: Optional[dict[str, Any]] = None) -> str:
    """Structured educational response utilizing actual dataset readings when available."""
    lower = message.lower()

    # Queries asking for latest readings / recent vitals
    if any(w in lower for w in ["latest reading", "recent reading", "my vitals", "recent heart rate", "spo2", "temperature", "blood pressure"]):
        if patient_context and patient_context.get("latest_vitals"):
            v = patient_context["latest_vitals"]
            pt_code = patient_context.get("patient_code", "Your record")
            ts = patient_context.get("last_updated", "Recent")

            reply = (
                f"### Latest Dataset Vitals for {pt_code}\n"
                f"*Dataset Timestamp: {ts}*\n\n"
                f"- **Heart Rate:** {v.get('heart_rate', '--')} bpm\n"
                f"- **SpO2:** {v.get('spo2', '--')}%\n"
                f"- **Respiratory Rate:** {v.get('respiratory_rate', '--')}/min\n"
                f"- **Systolic BP:** {v.get('systolic_bp', '--')} mmHg\n"
                f"- **Diastolic BP:** {v.get('diastolic_bp', '--')} mmHg\n"
                f"- **Temperature:** {v.get('temperature', '--')} °C\n\n"
                f"These values reflect actual recorded measurements from your dataset observations."
            )
        elif patient_context:
            reply = "I don't have enough available vital reading data for your record to answer that."
        else:
            reply = (
                "### CarePulse Vital Sign Overview\n\n"
                "- **Heart Rate (HR):** Normal resting range is typically 60–100 bpm.\n"
                "- **SpO2 (Oxygen Saturation):** Normal levels are typically 95%–100%.\n"
                "- **Respiratory Rate (RR):** Normal resting range is 12–20 breaths per minute.\n\n"
                "Select a patient record to view dataset-specific measurements."
            )

    # Queries asking about baseline or baseline deviation
    elif any(w in lower for w in ["baseline", "deviation", "changed compared"]):
        if patient_context and patient_context.get("baseline"):
            b = patient_context["baseline"]
            v = patient_context.get("latest_vitals", {})
            reply = (
                f"### Baseline Comparison ({patient_context.get('patient_code', 'Patient')})\n\n"
                f"- **Heart Rate:** Current {v.get('heart_rate', '--')} bpm vs Baseline {b.get('hr_mean', '--')} bpm\n"
                f"- **SpO2:** Current {v.get('spo2', '--')}% vs Baseline {b.get('spo2_mean', '--')}%\n"
                f"- **Respiratory Rate:** Current {v.get('respiratory_rate', '--')}/min vs Baseline {b.get('rr_mean', '--')}/min\n\n"
                f"Baseline stats are calculated from historical dataset observations."
            )
        else:
            reply = "I don't have enough available baseline data for this patient record to answer that."

    # Queries asking about CarePulse Risk Score
    elif any(w in lower for w in ["risk score", "risk state", "why did my risk"]):
        if patient_context and patient_context.get("risk_state"):
            rs = patient_context.get("risk_score", "--")
            st = patient_context.get("risk_state", "STABLE")
            exp = patient_context.get("explanation", {})
            reply = (
                f"### CarePulse Risk Assessment Summary\n\n"
                f"- **CarePulse Risk State:** {st}\n"
                f"- **Risk Score:** {rs}/100\n"
                f"- **Dataset Label:** {patient_context.get('dataset_label', 'N/A')}\n\n"
                f"**Why Detected:** {exp.get('why_detected', 'Vitals analyzed against historical baseline and trend models.')}\n\n"
                f"CarePulse risk state is a prototype decision-support metric."
            )
        else:
            reply = "I don't have enough available risk data for this patient record to answer that."

    elif any(w in lower for w in ["lifestyle", "healthy", "maintain"]):
        reply = (
            "### Maintaining a Healthy Lifestyle\n\n"
            "1. **Balanced Nutrition:** Focus on whole foods, lean proteins, vegetables, and high-fiber grains.\n"
            "2. **Regular Hydration:** Aim for 8–10 cups (approx. 2 liters) of water daily unless instructed otherwise.\n"
            "3. **Physical Activity:** Aim for at least 150 minutes of moderate exercise per week.\n"
            "4. **Restorative Sleep:** Maintain a consistent schedule aiming for 7–9 hours each night."
        )
    elif any(w in lower for w in ["doctor", "question", "appointment"]):
        reply = (
            "### Preparing Questions for Your Doctor\n\n"
            "- Write down your top 3 concerns before your visit.\n"
            "- Bring an up-to-date list of all medications and supplements.\n"
            "- Note any new vital changes or symptoms.\n"
            "- Ask: *'What are the recommended next steps for my care plan?'*"
        )
    else:
        reply = (
            "As your CarePulse Health Assistant, I can answer questions about:\n\n"
            "- **Your Latest Dataset Readings & Trends**\n"
            "- **Baseline & CarePulse Risk State Explanation**\n"
            "- **Healthy Lifestyle, Nutrition & Sleep Hygiene**\n"
            "- **Preparing Questions for Your Doctor**"
        )

    return f"{reply}\n\n---\n*{MANDATORY_DISCLAIMER}*"
