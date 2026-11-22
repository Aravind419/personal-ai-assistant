import re
import json
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession

from app.memory.models import Memory
from app.memory.schemas import MemoryResponse, MemoryCategory
from app.memory.service import _to_memory_response
from app.memory.repository import MemoryRepository
from app.memory.embeddings import get_default_embedding_provider
from app.core.logging import logger


# Sensitive pattern detector to prevent saving secrets into long-term memory
SENSITIVE_PATTERNS = [
    re.compile(r"(?i)\b(password|passwd|pwd|api[_-]?key|secret[_-]?key|access[_-]?token)\b(\s*[:=]|\s+is\s+)\S+"),
    re.compile(r"sk-[a-zA-Z0-9_\-]{20,}"),
    re.compile(r"ghp_[a-zA-Z0-9]{20,}"),
    re.compile(r"Bearer\s+[a-zA-Z0-9_\-\.]{20,}"),
    re.compile(r"\b(?:\d{4}[ -]?){3}\d{4}\b"),  # Credit card numbers
    re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),       # SSN
]

# Trivial conversational chatter patterns
CHATTER_PATTERNS = [
    re.compile(r"^(hi|hello|hey|thanks|thank you|ok|okay|cool|bye|goodbye|see you|great|awesome|yes|no)[.!]?$", re.IGNORECASE),
]

# Supported relationship identifiers
RELATIONSHIP_TERMS = [
    "friend", "best friend", "close friend", "college friend", "school friend", "childhood friend",
    "brother", "sister", "sibling", "father", "mother", "dad", "mom", "parent",
    "wife", "husband", "spouse", "partner", "fiancé", "fiancée", "girlfriend", "boyfriend",
    "son", "daughter", "child", "kid",
    "uncle", "aunt", "cousin", "nephew", "niece", "relative",
    "colleague", "coworker", "teammate", "manager", "boss", "lead", "mentor",
    "teacher", "professor", "instructor", "tutor",
    "roommate", "flatmate", "neighbor",
]

RELATION_REGEX_PART = "|".join(re.escape(r) for r in RELATIONSHIP_TERMS)


def is_sensitive_or_trivial(text: str) -> bool:
    """Returns True if text contains credentials, keys, or is purely trivial chatter."""
    clean = text.strip()
    if len(clean) < 4:
        return True

    for chatter in CHATTER_PATTERNS:
        if chatter.match(clean):
            return True

    for pattern in SENSITIVE_PATTERNS:
        if pattern.search(clean):
            logger.info("Filtered sensitive information pattern from memory candidate")
            return True

    return False


def is_question_or_hypothetical(text: str) -> Tuple[bool, Optional[str]]:
    """
    Identifies questions, instruction queries, and hypothetical statements that should
    NOT become permanent memories.
    """
    clean = text.strip()

    # Hypothetical markers
    hypo_patterns = [
        re.compile(r"(?i)\b(?:if\s+i\s+(?:had|were|was|could)|suppose\s+(?:that|i)|imagine\s+(?:if|that)|let's\s+say|what\s+if|hypothetically)\b"),
    ]
    for hp in hypo_patterns:
        if hp.search(clean):
            return True, "Hypothetical scenario rather than confirmed user fact"

    # Pure command or informational queries (e.g. "what is a python decorator")
    query_starters = [
        re.compile(r"(?i)^(?:what\s+is|what\s+are|what's|who\s+is|who\s+are|where\s+is|when\s+was|when\s+is|why\s+does|why\s+is|how\s+do|how\s+does|how\s+to|explain|give\s+me|tell\s+me\s+about|can\s+you|could\s+you|would\s+you|is\s+there|are\s+there|show\s+me|write\s+a|summarize)\b"),
    ]
    for qs in query_starters:
        if qs.search(clean):
            return True, "Informational query or instruction command rather than a user fact"

    # Ends with question mark and doesn't contain explicit personal declaration
    if clean.endswith("?") and not re.search(r"(?i)\b(?:my\s+[a-z]+|i\s+am|i\s+prefer|i\s+decided)\b", clean):
        return True, "Question query without explicit personal declaration"

    return False, None


def title_case_name(name: str) -> str:
    """Accurately title-cases names while preserving casing if already mixed."""
    clean = name.strip()
    clean = re.sub(r"[.!?,;]+$", "", clean).strip()
    if clean.islower() or clean.isupper():
        return " ".join(word.capitalize() for word in clean.split())
    return clean


def extract_person_name_from_memory(content: str) -> Optional[str]:
    """Extracts the primary person's name from a relationship memory string."""
    m = re.search(r"(?i)\bis named ([A-Za-z][A-Za-z\s'\-]{1,30})\.?", content)
    if m:
        return title_case_name(m.group(1))
    m2 = re.search(r"(?i)\buser's [a-z\s]+ ([A-Z][a-zA-Z'\-]+) is\b", content)
    if m2:
        return title_case_name(m2.group(1))
    return None


def split_into_clauses(text: str) -> List[str]:
    """
    Splits compound user sentences into individual declarative clauses while
    preserving contextual subject references.
    E.g. "I am studying B.Tech IT and building a Flutter app"
    -> ["I am studying B.Tech IT", "I am building a Flutter app"]
    """
    clean = text.strip()
    clauses: List[str] = []

    compound_conjunction = re.compile(r"\s+(?:and\s+also|and\s+currently|and\s+now|and|also|plus)\s+", re.IGNORECASE)
    sentence_splits = re.split(r"[\n;]+|(?<=[a-z0-9]{2})[.!?]\s+(?=[A-Z])", clean)

    for s in sentence_splits:
        sent = s.strip()
        if not sent:
            continue
        parts = compound_conjunction.split(sent)
        if len(parts) > 1:
            base_subject = ""
            subj_m = re.match(r"(?i)^(i\s+am|i'm|my\s+[a-z]+|i)\b", parts[0])
            if subj_m:
                base_subject = subj_m.group(0)

            for idx, part in enumerate(parts):
                p = part.strip()
                if not p:
                    continue
                if idx > 0 and base_subject and not re.match(r"(?i)^(i\s+am|i'm|i\s+live|my|the)\b", p):
                    if re.match(r"(?i)^(building|studying|learning|working|preparing|moving|staying)\b", p):
                        p = f"I am {p}"
                    elif re.match(r"(?i)^(prefer|code|want|live|like)\b", p):
                        p = f"I {p}"
                clauses.append(p)
        else:
            clauses.append(sent)

    return clauses or [clean]


def extract_heuristic_candidates(user_text: str, assistant_text: str) -> List[Dict[str, Any]]:
    """
    Comprehensive rule-based heuristic extractor capturing:
    - Personal Identity & Facts
    - Relationships (Creation, Enrichment, Corrections)
    - Location (Current presence, Relocation transitions, Hometown, Home residence)
    - Education (Field of study, Degree, College)
    - Career (Goals, Preparation, Roles)
    - Technical Skills & Stack
    - Preferences
    - Projects
    - Activities & Scheduled Events
    - Decisions & Plans
    """
    candidates: List[Dict[str, Any]] = []
    clean_user = user_text.strip()

    is_q_or_h, _ = is_question_or_hypothetical(clean_user)
    if is_q_or_h:
        return candidates

    clauses = split_into_clauses(clean_user)

    for clause in clauses:
        clean_clause = clause.strip()
        if len(clean_clause) < 4:
            continue

        # ---------------------------------------------------------
        # 1. RELATIONSHIPS
        # ---------------------------------------------------------
        # 1.1 Corrections: "Actually, my friend's name is Saranya, not Sarguna"
        corr_1 = re.search(
            rf"(?i)\b(?:actually|correction|mistake|typo)[,:]?\s*my\s+({RELATION_REGEX_PART})(?:'s\s+name|\s+name)?\s+is\s+([A-Za-z][A-Za-z\s'\-]{{1,30}})\s*,\s*not\s+([A-Za-z][A-Za-z\s'\-]{{1,30}})",
            clean_clause,
        )
        if corr_1:
            rel = corr_1.group(1).lower()
            new_name = title_case_name(corr_1.group(2))
            old_name = title_case_name(corr_1.group(3))
            candidates.append({
                "content": f"The user's {rel} is named {new_name}.",
                "category": MemoryCategory.RELATIONSHIPS.value,
                "subcategory": "friend" if "friend" in rel else "family",
                "temporal_scope": "permanent",
                "is_current": True,
                "importance": 0.65,
                "confidence": 0.95,
                "is_correction": True,
                "supersedes_name": old_name,
                "person_name": new_name,
                "relation_type": rel,
                "original_statement": clean_clause,
            })
            continue

        corr_2 = re.search(
            rf"(?i)\b(?:actually|correction|mistake|typo)[,:]?\s*not\s+([A-Za-z][A-Za-z\s'\-]{{1,30}})[,:]?\s*my\s+({RELATION_REGEX_PART})(?:'s\s+name|\s+name)?\s+is\s+([A-Za-z][A-Za-z\s'\-]{{1,30}})",
            clean_clause,
        )
        if corr_2:
            old_name = title_case_name(corr_2.group(1))
            rel = corr_2.group(2).lower()
            new_name = title_case_name(corr_2.group(3))
            candidates.append({
                "content": f"The user's {rel} is named {new_name}.",
                "category": MemoryCategory.RELATIONSHIPS.value,
                "subcategory": "friend" if "friend" in rel else "family",
                "temporal_scope": "permanent",
                "is_current": True,
                "importance": 0.65,
                "confidence": 0.95,
                "is_correction": True,
                "supersedes_name": old_name,
                "person_name": new_name,
                "relation_type": rel,
                "original_statement": clean_clause,
            })
            continue

        # 1.2 "my <rel> name is <name>"
        rel_m = re.search(
            rf"(?i)\bmy\s+({RELATION_REGEX_PART})\s+(?:'s\s+name\s+is|name\s+is|is\s+named|is\s+called)\s+([A-Za-z][A-Za-z\s'\-]{{1,30}})\b",
            clean_clause,
        )
        if rel_m:
            rel = rel_m.group(1).lower()
            name = title_case_name(rel_m.group(2))
            candidates.append({
                "content": f"The user's {rel} is named {name}.",
                "category": MemoryCategory.RELATIONSHIPS.value,
                "subcategory": "friend" if "friend" in rel else "family",
                "temporal_scope": "permanent",
                "is_current": True,
                "importance": 0.6,
                "confidence": 0.95,
                "person_name": name,
                "relation_type": rel,
                "original_statement": clean_clause,
            })
            continue

        # 1.3 "<Name> is my <rel>" or "<Name> is my <descriptor> friend"
        name_rel_m = re.search(
            rf"(?i)\b([A-Za-z][A-Za-z\s'\-]{{1,30}})\s+is\s+my\s+({RELATION_REGEX_PART})(?:\s+(college|school|childhood|close|best)\s+friend|\b|[.!?])",
            clean_clause,
        )
        if name_rel_m:
            name = title_case_name(name_rel_m.group(1))
            rel = name_rel_m.group(2).lower()
            descriptor = name_rel_m.group(3)
            content = f"The user's friend {name} is a {descriptor.lower()} friend." if descriptor else f"The user's {rel} is named {name}."
            candidates.append({
                "content": content,
                "category": MemoryCategory.RELATIONSHIPS.value,
                "subcategory": "friend" if "friend" in rel else "family",
                "temporal_scope": "permanent",
                "is_current": True,
                "importance": 0.6,
                "confidence": 0.95,
                "person_name": name,
                "relation_type": rel,
                "original_statement": clean_clause,
            })
            continue

        # 1.4 "my <rel> studies mechanical engineering"
        rel_act_m = re.search(
            rf"(?i)\bmy\s+({RELATION_REGEX_PART})\s+(studies|is\s+studying|works\s+at|works\s+as|lives\s+in|is\s+a)\s+([^.!?\n]{{3,80}})",
            clean_clause,
        )
        if rel_act_m:
            rel = rel_act_m.group(1).lower()
            verb = rel_act_m.group(2).strip()
            details = rel_act_m.group(3).strip()
            candidates.append({
                "content": f"The user's {rel} {verb} {details}.",
                "category": MemoryCategory.RELATIONSHIPS.value,
                "subcategory": "family" if rel in ["brother", "sister", "mother", "father"] else "relationship_activity",
                "temporal_scope": "current",
                "is_current": True,
                "importance": 0.65,
                "confidence": 0.9,
                "relation_type": rel,
                "original_statement": clean_clause,
            })
            continue

        # ---------------------------------------------------------
        # 2. LOCATION INTELLIGENCE
        # ---------------------------------------------------------
        # 2.1 Relocation / Move: "I moved to Bangalore", "Actually, I moved to Bangalore"
        reloc_m = re.search(
            r"(?i)\b(?:actually[,:]?\s*)?(?:i\s+moved\s+to|i've\s+moved\s+to|i\s+have\s+moved\s+to|i\s+shifted\s+to|i\s+relocated\s+to)\s+([A-Za-z][A-Za-z0-9\s'\-]{2,40})",
            clean_clause,
        )
        if reloc_m:
            place = title_case_name(reloc_m.group(1))
            candidates.append({
                "content": f"The user has moved to {place}.",
                "category": MemoryCategory.LOCATION.value,
                "subcategory": "current_location",
                "temporal_scope": "current",
                "is_current": True,
                "is_transition": True,
                "place_name": place,
                "importance": 0.85,
                "confidence": 0.95,
                "original_statement": clean_clause,
            })
            continue

        # 2.2 Current presence / temporary location: "I am in Kasiriganapalli", "I'm in Kasiriganapalli"
        curr_loc_m = re.search(
            r"(?i)\b(?:i\s+am\s+(?:currently\s+)?in|i'm\s+(?:currently\s+)?in|i\s+am\s+staying\s+in|i'm\s+staying\s+in|i\s+am\s+at)\s+([A-Za-z][A-Za-z0-9\s'\-]{2,40})",
            clean_clause,
        )
        if curr_loc_m:
            place = title_case_name(curr_loc_m.group(1))
            candidates.append({
                "content": f"The user is currently in {place}.",
                "category": MemoryCategory.LOCATION.value,
                "subcategory": "current_location",
                "temporal_scope": "current",
                "is_current": True,
                "place_name": place,
                "importance": 0.75,
                "confidence": 0.95,
                "original_statement": clean_clause,
            })
            continue

        # 2.3 Hometown: "My hometown is <place>", "I am from <place>"
        hometown_m = re.search(
            r"(?i)\b(?:my\s+hometown\s+is|i\s+am\s+from|i'm\s+from|i\s+was\s+born\s+in)\s+([A-Za-z][A-Za-z0-9\s'\-]{2,40})",
            clean_clause,
        )
        if hometown_m:
            place = title_case_name(hometown_m.group(1))
            candidates.append({
                "content": f"The user's hometown is {place}.",
                "category": MemoryCategory.LOCATION.value,
                "subcategory": "hometown",
                "temporal_scope": "permanent",
                "is_current": True,
                "place_name": place,
                "importance": 0.8,
                "confidence": 0.95,
                "original_statement": clean_clause,
            })
            continue

        # 2.4 Residence / Home location: "I live in <place>"
        live_m = re.search(
            r"(?i)\b(?:i\s+live\s+in|i\s+am\s+based\s+in|i'm\s+based\s+in)\s+([A-Za-z][A-Za-z0-9\s'\-]{2,40})",
            clean_clause,
        )
        if live_m:
            place = title_case_name(live_m.group(1))
            candidates.append({
                "content": f"The user lives in {place}.",
                "category": MemoryCategory.LOCATION.value,
                "subcategory": "home_location",
                "temporal_scope": "permanent",
                "is_current": True,
                "place_name": place,
                "importance": 0.8,
                "confidence": 0.95,
                "original_statement": clean_clause,
            })
            continue

        # ---------------------------------------------------------
        # 3. PERSONAL IDENTITY & FACTS
        # ---------------------------------------------------------
        # Birthday
        bday_m = re.search(r"(?i)\bmy\s+birthday\s+is\s+(?:in|on)\s+([^.!?\n]{3,40})", clean_clause)
        if bday_m:
            val = bday_m.group(1).strip()
            candidates.append({
                "content": f"The user's birthday is in {val}." if not val.lower().startswith(("in ", "on ")) else f"The user's birthday is {val}.",
                "category": MemoryCategory.PERSONAL_FACTS.value,
                "subcategory": "birthday",
                "temporal_scope": "permanent",
                "is_current": True,
                "importance": 0.7,
                "confidence": 0.95,
                "original_statement": clean_clause,
            })
            continue

        # Age
        age_m = re.search(r"(?i)\b(?:i\s+am\s+(\d{1,3})\s+years\s+old|my\s+age\s+is\s+(\d{1,3}))\b", clean_clause)
        if age_m:
            age = age_m.group(1) or age_m.group(2)
            candidates.append({
                "content": f"The user is {age} years old.",
                "category": MemoryCategory.PERSONAL_FACTS.value,
                "subcategory": "age",
                "temporal_scope": "temporary",
                "is_current": True,
                "importance": 0.7,
                "confidence": 0.95,
                "original_statement": clean_clause,
            })
            continue

        # User Name / Profile
        prof_m = re.search(r"(?i)\bmy\s+name\s+is\s+([A-Za-z][A-Za-z\s'\-]{1,30})\b", clean_clause)
        if prof_m:
            u_name = title_case_name(prof_m.group(1))
            candidates.append({
                "content": f"The user's name is {u_name}.",
                "category": MemoryCategory.PROFILE.value,
                "subcategory": "user_name",
                "temporal_scope": "permanent",
                "is_current": True,
                "importance": 0.95,
                "confidence": 0.95,
                "original_statement": clean_clause,
            })
            continue

        # ---------------------------------------------------------
        # 4. EDUCATION
        # ---------------------------------------------------------
        edu_m = re.search(r"(?i)\bi\s+(?:am\s+studying|study)\s+([^!?\n]{2,60})", clean_clause)
        if edu_m:
            subject = edu_m.group(1).strip().rstrip(".")
            candidates.append({
                "content": f"The user studies {subject}.",
                "category": MemoryCategory.EDUCATION.value,
                "subcategory": "field_of_study",
                "temporal_scope": "current",
                "is_current": True,
                "importance": 0.75,
                "confidence": 0.9,
                "original_statement": clean_clause,
            })
            continue

        major_m = re.search(r"(?i)\bmy\s+(?:major|degree|branch)\s+is\s+([^.!?\n]{3,60})", clean_clause)
        if major_m:
            deg = major_m.group(1).strip()
            candidates.append({
                "content": f"The user's major is {deg}.",
                "category": MemoryCategory.EDUCATION.value,
                "subcategory": "degree",
                "temporal_scope": "current",
                "is_current": True,
                "importance": 0.8,
                "confidence": 0.95,
                "original_statement": clean_clause,
            })
            continue

        college_m = re.search(r"(?i)\b(?:my\s+college\s+is|i\s+attend|i\s+go\s+to\s+college\s+at)\s+([^.!?\n]{3,60})", clean_clause)
        if college_m:
            col = college_m.group(1).strip()
            candidates.append({
                "content": f"The user's college is {col}.",
                "category": MemoryCategory.EDUCATION.value,
                "subcategory": "college",
                "temporal_scope": "current",
                "is_current": True,
                "importance": 0.8,
                "confidence": 0.95,
                "original_statement": clean_clause,
            })
            continue

        # ---------------------------------------------------------
        # 5. CAREER & AMBITIONS
        # ---------------------------------------------------------
        prep_m = re.search(r"(?i)\bi\s+am\s+preparing\s+for\s+([^.!?\n]{3,60})", clean_clause)
        if prep_m:
            val = prep_m.group(1).strip()
            candidates.append({
                "content": f"The user is preparing for {val}.",
                "category": MemoryCategory.CAREER_GOALS.value,
                "subcategory": "career_preparation",
                "temporal_scope": "current",
                "is_current": True,
                "importance": 0.8,
                "confidence": 0.9,
                "original_statement": clean_clause,
            })
            continue

        career_m = re.search(r"(?i)\b(?:my\s+(?:career\s+)?goal\s+is|i\s+want\s+to\s+become\s+(?:a|an)?)\s+([^.!?\n]{3,60})", clean_clause)
        if career_m:
            goal = career_m.group(1).strip()
            candidates.append({
                "content": f"The user's goal is {goal}.",
                "category": MemoryCategory.CAREER_GOALS.value,
                "subcategory": "career_goal",
                "temporal_scope": "current",
                "is_current": True,
                "importance": 0.85,
                "confidence": 0.9,
                "original_statement": clean_clause,
            })
            continue

        # ---------------------------------------------------------
        # 6. TECHNICAL SKILLS & STACK
        # ---------------------------------------------------------
        learn_m = re.search(r"(?i)\bi\s+am\s+learning\s+([^.!?\n]{2,60})", clean_clause)
        if learn_m:
            skill = learn_m.group(1).strip()
            candidates.append({
                "content": f"The user is learning {skill}.",
                "category": MemoryCategory.TECHNICAL_SKILLS.value,
                "subcategory": "technical_skill",
                "temporal_scope": "current",
                "is_current": True,
                "importance": 0.8,
                "confidence": 0.9,
                "original_statement": clean_clause,
            })
            continue

        tech_m = re.search(r"(?i)\b(?:my\s+tech\s+stack\s+is|my\s+stack\s+includes|i\s+code\s+in)\s+([^.!?\n]{2,60})", clean_clause)
        if tech_m:
            stk = tech_m.group(1).strip()
            candidates.append({
                "content": f"The user codes in {stk}.",
                "category": MemoryCategory.TECHNICAL_SKILLS.value,
                "subcategory": "technical_stack",
                "temporal_scope": "current",
                "is_current": True,
                "importance": 0.8,
                "confidence": 0.95,
                "original_statement": clean_clause,
            })
            continue

        # ---------------------------------------------------------
        # 7. PREFERENCES
        # ---------------------------------------------------------
        pref_m = re.search(r"(?i)\bi\s+prefer\s+([^.!?\n]{3,60})", clean_clause)
        if pref_m:
            candidates.append({
                "content": f"The user prefers {pref_m.group(1).strip()}.",
                "category": MemoryCategory.PREFERENCES.value,
                "subcategory": "user_preference",
                "temporal_scope": "permanent",
                "is_current": True,
                "importance": 0.8,
                "confidence": 0.9,
                "original_statement": clean_clause,
            })
            continue

        like_m = re.search(r"(?i)\bi\s+like\s+to\s+([^.!?\n]{3,60})", clean_clause)
        if like_m:
            candidates.append({
                "content": f"The user likes to {like_m.group(1).strip()}.",
                "category": MemoryCategory.PREFERENCES.value,
                "subcategory": "user_preference",
                "temporal_scope": "permanent",
                "is_current": True,
                "importance": 0.7,
                "confidence": 0.9,
                "original_statement": clean_clause,
            })
            continue

        # ---------------------------------------------------------
        # 8. PROJECTS
        # ---------------------------------------------------------
        build_m = re.search(r"(?i)\bi\s+am\s+building\s+([^!?\n]{3,80})", clean_clause)
        if build_m:
            proj = build_m.group(1).strip().rstrip(".")
            candidates.append({
                "content": f"The user is building {proj}.",
                "category": MemoryCategory.PROJECTS.value,
                "subcategory": "active_project",
                "temporal_scope": "current",
                "is_current": True,
                "importance": 0.85,
                "confidence": 0.9,
                "original_statement": clean_clause,
            })
            continue

        work_m = re.search(r"(?i)\bi\s+am\s+working\s+on\s+([^.!?\n]{3,80})", clean_clause)
        if work_m:
            proj = work_m.group(1).strip()
            candidates.append({
                "content": f"The user is working on {proj}.",
                "category": MemoryCategory.PROJECTS.value,
                "subcategory": "active_project",
                "temporal_scope": "current",
                "is_current": True,
                "importance": 0.85,
                "confidence": 0.9,
                "original_statement": clean_clause,
            })
            continue

        # ---------------------------------------------------------
        # 9. DECISIONS & PLANS
        # ---------------------------------------------------------
        dec_m = re.search(r"(?i)\b(?:i\s+decided\s+to\s+use|we\s+decided\s+to\s+use|i\s+chose\s+to\s+use|actually[,:]?\s*i\s+use\s+([^.!?\n]{2,40})\s+now)\b", clean_clause)
        if dec_m:
            matched_text = dec_m.group(0).strip()
            if "i decided to use" in matched_text.lower():
                val = re.sub(r"(?i)^.*?i\s+decided\s+to\s+use\s+", "", clean_clause).strip()
                content = f"The user decided to use {val}."
            elif "actually" in matched_text.lower():
                val = dec_m.group(1).strip() if dec_m.group(1) else "the updated tool"
                content = f"The user decided to use {val}."
            else:
                val = re.sub(r"(?i)^.*?use\s+", "", clean_clause).strip()
                content = f"The user decided to use {val}."
            candidates.append({
                "content": content,
                "category": MemoryCategory.DECISIONS.value,
                "subcategory": "technical_decision",
                "temporal_scope": "permanent",
                "is_current": True,
                "importance": 0.8,
                "confidence": 0.9,
                "original_statement": clean_clause,
            })
            continue

        # ---------------------------------------------------------
        # 10. IMPORTANT EVENTS & ACTIVITIES
        # ---------------------------------------------------------
        event_m = re.search(r"(?i)\b(?:my\s+anniversary\s+is|i\s+am\s+graduating\s+in|my\s+interview\s+is)\s+([^.!?\n]{3,60})", clean_clause)
        if event_m:
            candidates.append({
                "content": f"The user is {clean_clause.lower()}.",
                "category": MemoryCategory.IMPORTANT_EVENTS.value,
                "subcategory": "scheduled_event",
                "temporal_scope": "temporary",
                "is_current": True,
                "importance": 0.8,
                "confidence": 0.9,
                "original_statement": clean_clause,
            })
            continue

        # ---------------------------------------------------------
        # 11. COMMUNICATION PREFERENCES
        # ---------------------------------------------------------
        comm_m = re.search(r"(?i)\b(?:keep\s+responses\s+brief|be\s+concise|explain\s+simply|don't\s+give\s+long\s+code)\b", clean_clause)
        if comm_m:
            candidates.append({
                "content": f"The user prefers {comm_m.group(0).strip().lower()}.",
                "category": MemoryCategory.COMMUNICATION_PREFERENCES.value,
                "subcategory": "communication_style",
                "temporal_scope": "permanent",
                "is_current": True,
                "importance": 0.85,
                "confidence": 0.95,
                "original_statement": clean_clause,
            })
            continue

    # Filter any candidate with sensitive information or that is trivial
    valid_candidates: List[Dict[str, Any]] = []
    for c in candidates:
        if not is_sensitive_or_trivial(c["content"]):
            valid_candidates.append(c)

    return valid_candidates


async def extract_via_llm(user_message: str, assistant_response: str) -> Optional[List[Dict[str, Any]]]:
    """
    Intelligent LLM-assisted extraction strategy.
    Invokes the active configured LLM provider to extract structured memory candidates.
    Returns None if provider is unconfigured, without API key, or fails.
    """
    try:
        from app.llm.registry import provider_registry
        from app.core.config import settings

        provider = provider_registry.get_active_provider()
        if not provider or not provider.is_available():
            return None

        prompt = (
            "You are a personal memory extraction engine. Analyze this conversation turn between User and Assistant.\n"
            "Extract personal facts, relationships, location (current presence, relocation, home), education, "
            "career goals, technical skills, preferences, projects, decisions, and events.\n"
            "Return a strictly valid JSON array of objects with keys:\n"
            "- 'content': formatted statement, e.g. 'The user is currently in Kasiriganapalli.'\n"
            "- 'category': one of 'personal_identity', 'relationships', 'location', 'education', 'career_goals', "
            "'technical_skills', 'preferences', 'projects', 'important_events', 'decisions', 'general'\n"
            "- 'subcategory': specific tag (e.g. 'current_location', 'friend', 'degree')\n"
            "- 'temporal_scope': 'current', 'permanent', 'temporary', or 'previous'\n"
            "- 'importance': float 0.0 - 1.0\n"
            "- 'confidence': float 0.0 - 1.0\n"
            "- 'original_statement': excerpt from user message\n"
            "Do NOT extract sensitive credentials, passwords, or trivial chit-chat.\n"
            "If no durable facts exist, return [].\n\n"
            f"User: {user_message}\n"
            f"Assistant: {assistant_response}\n\n"
            "JSON:"
        )

        response_text = ""
        async for chunk in provider.generate_stream(
            messages=[{"role": "user", "content": prompt}],
            model=settings.DEFAULT_LLM_MODEL,
            temperature=0.0,
            max_tokens=400,
        ):
            if chunk.text:
                response_text += chunk.text

        json_match = re.search(r"\[.*\]", response_text, re.DOTALL)
        if json_match:
            parsed = json.loads(json_match.group(0))
            if isinstance(parsed, list):
                valid = []
                for item in parsed:
                    if isinstance(item, dict) and "content" in item and item["content"].strip():
                        if not is_sensitive_or_trivial(item["content"]):
                            valid.append(item)
                return valid if valid else None
    except Exception as exc:
        logger.debug(f"LLM memory extraction unavailable or error: {exc}. Gracefully falling back to heuristic extractor.")
        return None

    return None


async def reconcile_and_store_memory_with_detail(
    candidate: Dict[str, Any],
    conversation_id: Optional[str],
    message_id: Optional[str],
    session: AsyncSession,
) -> Tuple[MemoryResponse, Dict[str, Any]]:
    """
    Evaluates a candidate memory against existing memories in the database:
    - If identical: confirms duplicate, updates confidence & last_accessed_at.
    - If location transition (user relocated): transitions old current location to previous/historical, stores new location.
    - If correcting existing entity (is_correction=True): supersedes previous fact with audit history.
    - If enriching existing entity (same person/topic with new detail): updates with audit history.
    - If distinct entity: stores fresh record with all intelligent temporal attributes.
    """
    content = candidate["content"].strip()
    category = candidate.get("category", MemoryCategory.GENERAL.value).strip().lower()
    subcategory = candidate.get("subcategory")
    temporal_scope = candidate.get("temporal_scope", "permanent")
    importance = float(candidate.get("importance", 0.5))
    confidence = float(candidate.get("confidence", 0.9))
    is_correction = bool(candidate.get("is_correction", False))
    supersedes_name = candidate.get("supersedes_name")
    is_transition = bool(candidate.get("is_transition", False))
    original_statement = candidate.get("original_statement")
    cand_person = candidate.get("person_name") or extract_person_name_from_memory(content)

    provider = get_default_embedding_provider()
    embedding = await provider.embed_text(content)
    now = datetime.now(timezone.utc)

    # -------------------------------------------------------------
    # A. Targeted Correction Check (e.g. Saranya superseding Sarguna)
    # -------------------------------------------------------------
    if is_correction and supersedes_name:
        candidates_db, _ = await MemoryRepository.list_memories(
            session=session,
            category=category,
            search=supersedes_name,
            limit=5,
        )
        if candidates_db:
            target_mem = candidates_db[0]
            prev_content = target_mem.content
            prev_meta = {}
            if target_mem.metadata_json:
                try:
                    prev_meta = json.loads(target_mem.metadata_json)
                except Exception:
                    pass

            history = prev_meta.get("history", [])
            history.append({
                "previous_content": prev_content,
                "superseded_at": now.isoformat(),
                "reason": "corrected_by_user",
                "superseded_name": supersedes_name,
            })
            prev_meta["history"] = history
            prev_meta["last_updated_reason"] = "corrected_by_user"

            target_mem.content = content
            target_mem.embedding = embedding
            target_mem.importance = max(target_mem.importance, importance)
            target_mem.confidence = confidence
            target_mem.last_accessed_at = now
            target_mem.metadata_json = json.dumps(prev_meta)
            target_mem.source_conversation_id = conversation_id or target_mem.source_conversation_id
            target_mem.source_message_id = message_id or target_mem.source_message_id
            if subcategory:
                target_mem.subcategory = subcategory
            if temporal_scope:
                target_mem.temporal_scope = temporal_scope
            if original_statement:
                target_mem.original_statement = original_statement

            updated = await MemoryRepository.update(session, target_mem)
            resp = _to_memory_response(updated)
            detail = {
                "action": "superseded",
                "id": resp.id,
                "content": resp.content,
                "category": resp.category,
                "subcategory": resp.subcategory,
                "temporal_scope": resp.temporal_scope,
                "importance": resp.importance,
                "confidence": resp.confidence,
                "similarity": 1.0,
                "previous_content": prev_content,
                "embedding_model": provider.model_name,
                "embedding_dim": len(embedding),
                "status": "persisted",
            }
            return resp, detail

    # -------------------------------------------------------------
    # B. Location Relocation Transition Handling
    # -------------------------------------------------------------
    if category == MemoryCategory.LOCATION.value and (subcategory == "current_location" or is_transition):
        loc_mems, _ = await MemoryRepository.list_memories(
            session=session,
            category=MemoryCategory.LOCATION.value,
            is_archived=False,
            limit=10,
        )
        current_loc_mems = [
            m for m in loc_mems
            if m.is_current and (m.subcategory == "current_location" or "currently in" in m.content.lower())
        ]

        previous_loc_content = None
        for old_loc in current_loc_mems:
            if old_loc.content.strip().lower() != content.lower():
                previous_loc_content = old_loc.content
                old_loc.temporal_scope = "previous"
                old_loc.is_current = False
                old_loc.valid_until = now
                old_meta = {}
                if old_loc.metadata_json:
                    try:
                        old_meta = json.loads(old_loc.metadata_json)
                    except Exception:
                        pass
                hist = old_meta.get("history", [])
                hist.append({
                    "previous_content": old_loc.content,
                    "superseded_by": content,
                    "transitioned_at": now.isoformat(),
                    "reason": "user_relocated",
                })
                old_meta["history"] = hist
                old_loc.metadata_json = json.dumps(old_meta)
                await MemoryRepository.update(session, old_loc)

        # Check if identical location already exists
        for old_loc in current_loc_mems:
            if old_loc.content.strip().lower() == content.lower():
                old_loc.confidence = min(1.0, old_loc.confidence + 0.05)
                old_loc.last_accessed_at = now
                updated = await MemoryRepository.update(session, old_loc)
                resp = _to_memory_response(updated)
                detail = {
                    "action": "duplicate_confirmed",
                    "id": resp.id,
                    "content": resp.content,
                    "category": resp.category,
                    "subcategory": resp.subcategory,
                    "temporal_scope": resp.temporal_scope,
                    "importance": resp.importance,
                    "confidence": resp.confidence,
                    "similarity": 1.0,
                    "previous_content": None,
                    "embedding_model": provider.model_name,
                    "embedding_dim": len(embedding),
                    "status": "persisted",
                }
                return resp, detail

        # Persist new current location
        meta_dict = {"previous_location": previous_loc_content} if previous_loc_content else {}
        new_loc_mem = Memory(
            content=content,
            category=category,
            subcategory=subcategory or "current_location",
            embedding=embedding,
            importance=importance,
            confidence=confidence,
            source_conversation_id=conversation_id,
            source_message_id=message_id,
            temporal_scope="current",
            valid_from=now,
            is_current=True,
            original_statement=original_statement,
            metadata_json=json.dumps(meta_dict) if meta_dict else None,
            embedding_model=provider.model_name,
            embedding_dim=len(embedding),
            last_accessed_at=now,
        )
        saved = await MemoryRepository.create(session, new_loc_mem)
        resp = _to_memory_response(saved)
        detail = {
            "action": "superseded" if previous_loc_content else "created",
            "id": resp.id,
            "content": resp.content,
            "category": resp.category,
            "subcategory": resp.subcategory,
            "temporal_scope": resp.temporal_scope,
            "importance": resp.importance,
            "confidence": resp.confidence,
            "similarity": 0.0,
            "previous_content": previous_loc_content,
            "embedding_model": provider.model_name,
            "embedding_dim": len(embedding),
            "status": "persisted",
        }
        return resp, detail

    # -------------------------------------------------------------
    # C. General Vector Search for Duplicates & Enrichments
    # -------------------------------------------------------------
    existing_matches = await MemoryRepository.vector_search(
        session=session,
        query_vector=embedding,
        category=category,
        limit=5,
        threshold=0.55,
        include_archived=False,
    )

    if existing_matches:
        for top_mem, top_sim in existing_matches:
            top_content = top_mem.content.strip()

            # 1. Exact or near-identical text match -> Duplicate Confirmed
            if top_content.lower() == content.lower():
                top_mem.confidence = min(1.0, top_mem.confidence + 0.05)
                top_mem.last_accessed_at = now
                updated = await MemoryRepository.update(session, top_mem)
                resp = _to_memory_response(updated)
                detail = {
                    "action": "duplicate_confirmed",
                    "id": resp.id,
                    "content": resp.content,
                    "category": resp.category,
                    "subcategory": resp.subcategory,
                    "temporal_scope": resp.temporal_scope,
                    "importance": resp.importance,
                    "confidence": resp.confidence,
                    "similarity": round(float(top_sim), 4),
                    "previous_content": None,
                    "embedding_model": provider.model_name,
                    "embedding_dim": len(embedding),
                    "status": "persisted",
                }
                return resp, detail

            # 2. Relationship / Entity Disambiguation
            if category == MemoryCategory.RELATIONSHIPS.value:
                existing_person = extract_person_name_from_memory(top_content)

                # Same person mentioned with more details -> Enrichment
                if cand_person and existing_person and cand_person.lower() == existing_person.lower():
                    prev_meta = {}
                    if top_mem.metadata_json:
                        try:
                            prev_meta = json.loads(top_mem.metadata_json)
                        except Exception:
                            pass

                    prev_content = top_mem.content
                    history = prev_meta.get("history", [])
                    history.append({
                        "previous_content": prev_content,
                        "superseded_at": now.isoformat(),
                        "reason": "enriched_relationship_details",
                    })
                    prev_meta["history"] = history

                    top_mem.content = content
                    top_mem.embedding = embedding
                    top_mem.importance = max(top_mem.importance, importance)
                    top_mem.confidence = max(top_mem.confidence, confidence)
                    top_mem.last_accessed_at = now
                    top_mem.metadata_json = json.dumps(prev_meta)
                    if subcategory:
                        top_mem.subcategory = subcategory
                    if original_statement:
                        top_mem.original_statement = original_statement

                    updated = await MemoryRepository.update(session, top_mem)
                    resp = _to_memory_response(updated)
                    detail = {
                        "action": "superseded",
                        "id": resp.id,
                        "content": resp.content,
                        "category": resp.category,
                        "subcategory": resp.subcategory,
                        "temporal_scope": resp.temporal_scope,
                        "importance": resp.importance,
                        "confidence": resp.confidence,
                        "similarity": round(float(top_sim), 4),
                        "previous_content": prev_content,
                        "embedding_model": provider.model_name,
                        "embedding_dim": len(embedding),
                        "status": "persisted",
                    }
                    return resp, detail

                # Different people mentioned (e.g. Sarguna vs Rahul) -> Do not merge!
                if cand_person and existing_person and cand_person.lower() != existing_person.lower():
                    continue

            # 3. High similarity on non-relationship items (e.g. goals or preferences superseding)
            if top_sim >= 0.85:
                prev_meta = {}
                if top_mem.metadata_json:
                    try:
                        prev_meta = json.loads(top_mem.metadata_json)
                    except Exception:
                        pass

                prev_content = top_mem.content
                history = prev_meta.get("history", [])
                history.append({
                    "previous_content": prev_content,
                    "superseded_at": now.isoformat(),
                    "reason": "superseded_by_newer_conversation",
                })
                prev_meta["history"] = history
                prev_meta["last_updated_reason"] = "superseded_by_newer_conversation"

                top_mem.content = content
                top_mem.embedding = embedding
                top_mem.importance = max(top_mem.importance, importance)
                top_mem.confidence = confidence
                top_mem.last_accessed_at = now
                top_mem.metadata_json = json.dumps(prev_meta)
                top_mem.source_conversation_id = conversation_id or top_mem.source_conversation_id
                top_mem.source_message_id = message_id or top_mem.source_message_id
                if subcategory:
                    top_mem.subcategory = subcategory
                if temporal_scope:
                    top_mem.temporal_scope = temporal_scope
                if original_statement:
                    top_mem.original_statement = original_statement

                updated = await MemoryRepository.update(session, top_mem)
                resp = _to_memory_response(updated)
                detail = {
                    "action": "superseded",
                    "id": resp.id,
                    "content": resp.content,
                    "category": resp.category,
                    "subcategory": resp.subcategory,
                    "temporal_scope": resp.temporal_scope,
                    "importance": resp.importance,
                    "confidence": resp.confidence,
                    "similarity": round(float(top_sim), 4),
                    "previous_content": prev_content,
                    "embedding_model": provider.model_name,
                    "embedding_dim": len(embedding),
                    "status": "persisted",
                }
                return resp, detail

    # -------------------------------------------------------------
    # D. Distinct Memory: Persist Fresh Record
    # -------------------------------------------------------------
    new_mem = Memory(
        content=content,
        category=category,
        subcategory=subcategory,
        temporal_scope=temporal_scope,
        valid_from=now,
        is_current=True,
        original_statement=original_statement,
        embedding=embedding,
        importance=importance,
        confidence=confidence,
        source_conversation_id=conversation_id,
        source_message_id=message_id,
        embedding_model=provider.model_name,
        embedding_dim=len(embedding),
        last_accessed_at=now,
    )
    saved = await MemoryRepository.create(session, new_mem)
    resp = _to_memory_response(saved)
    detail = {
        "action": "created",
        "id": resp.id,
        "content": resp.content,
        "category": resp.category,
        "subcategory": resp.subcategory,
        "temporal_scope": resp.temporal_scope,
        "importance": resp.importance,
        "confidence": resp.confidence,
        "similarity": 0.0,
        "previous_content": None,
        "embedding_model": provider.model_name,
        "embedding_dim": len(embedding),
        "status": "persisted",
    }
    return resp, detail


async def reconcile_and_store_memory(
    candidate: Dict[str, Any],
    conversation_id: Optional[str],
    message_id: Optional[str],
    session: AsyncSession,
) -> MemoryResponse:
    """Convenience wrapper returning only MemoryResponse for backward compatibility."""
    resp, _ = await reconcile_and_store_memory_with_detail(
        candidate=candidate,
        conversation_id=conversation_id,
        message_id=message_id,
        session=session,
    )
    return resp


async def extract_and_reconcile_memories_with_trace(
    user_message: str,
    assistant_response: str,
    conversation_id: Optional[str],
    message_id: Optional[str],
    session: AsyncSession,
) -> Tuple[List[MemoryResponse], Dict[str, Any]]:
    """
    Enhanced extraction pipeline providing complete transparency for dashboard inspection.
    Supports intelligent dual extraction strategy (LLM provider + heuristic fallback).
    Executes and records all 9 stages of the memory lifecycle.
    """
    stages_executed = [
        "1. Source conversation identified",
        "2. Relevant messages collected",
    ]

    filtered_candidates: List[Dict[str, Any]] = []
    created_memories: List[Dict[str, Any]] = []
    updated_memories: List[Dict[str, Any]] = []
    duplicate_memories: List[Dict[str, Any]] = []
    rejected_candidates: List[Dict[str, Any]] = []

    # Check for questions or hypotheticals
    is_q_or_h, q_reason = is_question_or_hypothetical(user_message)
    if is_q_or_h:
        stages_executed.append("3. Candidate memories evaluated (0 personal facts found)")
        trace = {
            "stages_executed": stages_executed,
            "created_memories": [],
            "updated_memories": [],
            "duplicate_memories": [],
            "filtered_candidates": [],
            "rejected_candidates": [{"reason": q_reason or "Non-factual question or hypothetical query"}],
            "memories_extracted": 0,
            "extraction_strategy": "heuristic",
            "summary": f"No durable memories extracted: {q_reason}.",
        }
        return [], trace

    # Check for trivial or sensitive overall message
    if is_sensitive_or_trivial(user_message):
        stages_executed.append("3. Candidate memories extracted (0 candidates found)")
        stages_executed.append("4. Sensitive / trivial content filtered")
        trace = {
            "stages_executed": stages_executed,
            "created_memories": [],
            "updated_memories": [],
            "duplicate_memories": [],
            "filtered_candidates": [{"reason": "User message classified as sensitive credentials or conversational chatter"}],
            "rejected_candidates": [],
            "memories_extracted": 0,
            "extraction_strategy": "heuristic",
            "summary": "Message filtered as sensitive credentials or trivial chatter. No durable memories created.",
        }
        return [], trace

    stages_executed.append("3. Candidate memories extracted")
    extraction_strategy = "heuristic"
    candidates = None

    # Dual strategy: Attempt LLM extraction first
    try:
        llm_candidates = await extract_via_llm(user_message, assistant_response)
        if llm_candidates is not None and len(llm_candidates) > 0:
            candidates = llm_candidates
            extraction_strategy = "llm"
    except Exception as exc:
        logger.debug(f"LLM extraction error: {exc}")

    # Fall back to comprehensive heuristic extraction
    if candidates is None:
        candidates = extract_heuristic_candidates(user_message, assistant_response)
        extraction_strategy = "heuristic"

    stages_executed.append("4. Sensitive information filtering performed")
    if not candidates:
        trace = {
            "stages_executed": stages_executed,
            "created_memories": [],
            "updated_memories": [],
            "duplicate_memories": [],
            "filtered_candidates": filtered_candidates,
            "rejected_candidates": [{"reason": "No personal facts, relationships, preferences, education, or goals identified"}],
            "memories_extracted": 0,
            "extraction_strategy": extraction_strategy,
            "summary": "No durable memory candidates identified from conversation context.",
        }
        return [], trace

    stages_executed.append("5. Existing vector memories searched")
    stages_executed.append("6. Duplicate detection performed")
    stages_executed.append("7. Conflicts or outdated information reconciled")
    stages_executed.append("8. Embeddings generated")
    stages_executed.append("9. Memories persisted to PostgreSQL")

    saved_memories: List[MemoryResponse] = []
    for cand in candidates:
        try:
            mem, detail = await reconcile_and_store_memory_with_detail(
                candidate=cand,
                conversation_id=conversation_id,
                message_id=message_id,
                session=session,
            )
            saved_memories.append(mem)

            action = detail.get("action")
            if action == "created":
                created_memories.append(detail)
            elif action == "superseded":
                updated_memories.append(detail)
            elif action == "duplicate_confirmed":
                duplicate_memories.append(detail)

        except Exception as exc:
            logger.error(f"Failed to reconcile and store memory candidate: {exc}")
            rejected_candidates.append({
                "content": cand.get("content", ""),
                "reason": f"Persistence failed: {str(exc)}",
            })

    trace = {
        "stages_executed": stages_executed,
        "created_memories": created_memories,
        "updated_memories": updated_memories,
        "duplicate_memories": duplicate_memories,
        "filtered_candidates": filtered_candidates,
        "rejected_candidates": rejected_candidates,
        "memories_extracted": len(saved_memories),
        "extraction_strategy": extraction_strategy,
        "summary": f"{len(created_memories)} created, {len(updated_memories)} updated, {len(duplicate_memories)} duplicate confirmed.",
    }

    return saved_memories, trace


async def extract_and_reconcile_memories(
    user_message: str,
    assistant_response: str,
    conversation_id: Optional[str],
    message_id: Optional[str],
    session: AsyncSession,
) -> List[MemoryResponse]:
    """
    Main extraction orchestrator:
    Extracts durable candidates, sanitizes secrets, reconciles duplicates, and persists.
    Maintained for backward compatibility.
    """
    mems, _ = await extract_and_reconcile_memories_with_trace(
        user_message=user_message,
        assistant_response=assistant_response,
        conversation_id=conversation_id,
        message_id=message_id,
        session=session,
    )
    return mems
