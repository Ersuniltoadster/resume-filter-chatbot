from __future__ import annotations

import argparse
import asyncio
import json
from io import BytesIO
from pathlib import Path

from docx import Document

from app.services.llm.groq_llm import groq_chat_json
from app.services.processing.pdf_extract import extract_text_from_pdf_bytes
from app.services.resume.profile_schema import ResumeProfile


def extract_text_from_local_file(path: Path) -> str:
    suffix = path.suffix.lower()

    if suffix == ".pdf":
        return extract_text_from_pdf_bytes(path.read_bytes())

    if suffix == ".docx":
        doc = Document(BytesIO(path.read_bytes()))
        parts: list[str] = []
        for p in doc.paragraphs:
            t = (p.text or "").strip()
            if t:
                parts.append(t)
        return "\n".join(parts).strip()

    raise ValueError(f"Unsupported local file type: {suffix}")


async def llm_build_resume_profile(text: str) -> ResumeProfile:
    text = (text or "").strip()

    # Keep prompts within a reasonable size (tune later if needed)
    text = text[:12000]

    system = (
        "You are an expert resume parser.\n"
        "Return ONLY valid JSON (no markdown, no explanation, no extra text).\n"
        "The JSON MUST match this schema:\n"
        "{\n"
        '  "total_years_experience": number|null,\n'
        '  "skills": string[],\n'
        '  "skill_experience_years": { [skill: string]: number },\n'
        '  "overall_summary": string|null,\n'
        '  "company_experience_years": { [company: string]: number },\n'
        '  "projects": [ { "domain": string|null, "project_name": string, "project_description": string|null } ]\n'
        "}\n"
        "Rules:\n"
        "- skills must be lowercase\n"
        "- If unknown, use null or empty list/dict\n"
        "- Years must be numbers (example 2.5)\n"
        "- overall_summary must be an overall summary of the ENTIRE resume (not only the Summary section).\n"
        "- overall_summary must be between 190 and 200 words.\n"
        "- Do not use bullet points in overall_summary; write as a paragraph.\n"
        "- For skill_experience_years and company_experience_years: NEVER use null values. If unknown, omit the key or use an empty object {}.\n"
    )

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": f"Resume text:\n\n{text}"},
    ]
    
    data = await groq_chat_json(messages=messages, temperature=0.0, max_tokens=1200)

    def _clean_float_map(x):
        if not isinstance(x, dict):
            return {}
        out = {}
        for k, v in x.items():
            if v is None:
                continue
            try:
                out[str(k)] = float(v)
            except Exception:
                continue
        return out

    data["skill_experience_years"] = _clean_float_map(data.get("skill_experience_years"))
    data["company_experience_years"] = _clean_float_map(data.get("company_experience_years"))

    profile = ResumeProfile.model_validate(data)

    def _wc(s: str | None) -> int:
        return len((s or "").split())

    # 1) If too short (<190), ask LLM to expand (1 retry)
    if profile.overall_summary and _wc(profile.overall_summary) < 190:
        expand_system = (
            "Return ONLY valid JSON.\n"
            'Schema: { "overall_summary": string }\n'
            "Rules:\n"
            "- overall_summary must be between 190 and 200 words\n"
            "- single paragraph, no bullet points\n"
            "- must summarize the ENTIRE resume\n"
        )

        expand_user = (
            "Expand the summary to meet the 190-200 word requirement using the resume text.\n\n"
            f"RESUME TEXT:\n{text}\n\n"
            f"CURRENT SUMMARY:\n{profile.overall_summary}\n"
        )

        expand_data = await groq_chat_json(
            messages=[
                {"role": "system", "content": expand_system},
                {"role": "user", "content": expand_user},
            ],
            temperature=0.0,
            max_tokens=800,
        )

        new_summary = expand_data.get("overall_summary")
        if isinstance(new_summary, str) and new_summary.strip():
            profile.overall_summary = new_summary.strip()

    # 2) Hard cap to 200 words
    if profile.overall_summary:
        words = profile.overall_summary.split()
        if len(words) > 200:
            profile.overall_summary = " ".join(words[:200])

    return profile


async def process_one(path: Path, overwrite: bool) -> tuple[bool, str]:
    try:
        out_path = path.with_name(path.stem + ".llm.json")
        if out_path.exists() and not overwrite:
            return True, f"SKIP (exists): {path.name}"

        text = extract_text_from_local_file(path)
        if not text or len(text.strip()) < 30:
            return False, f"NO TEXT: {path.name}"

        profile = await llm_build_resume_profile(text)
        out = profile.model_dump(mode="json", exclude_none=True)

        out_path.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
        return True, f"OK: {path.name} -> {out_path.name}"
    except Exception as e:
        return False, f"FAIL: {path.name} ({e})"


async def main_async(folder: Path, concurrency: int, overwrite: bool) -> None:
    files: list[Path] = []
    for ext in (".pdf", ".docx"):
        files.extend(folder.rglob(f"*{ext}"))

    files = sorted(set(files))
    if not files:
        print("No .pdf or .docx files found in:", folder)
        return

    sem = asyncio.Semaphore(concurrency)

    async def guarded(p: Path) -> tuple[bool, str]:
        async with sem:
            return await process_one(p, overwrite=overwrite)

    tasks = [asyncio.create_task(guarded(p)) for p in files]
    results = await asyncio.gather(*tasks)

    ok = sum(1 for success, _ in results if success)
    fail = sum(1 for success, _ in results if not success)

    for _, msg in results:
        print(msg)

    print("\nSUMMARY")
    print("Total:", len(results))
    print("OK:", ok)
    print("FAILED:", fail)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("folder", help="Folder containing resumes (.pdf/.docx)")
    parser.add_argument("--concurrency", type=int, default=1, help="Concurrent Groq requests (start with 1)")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing .llm.json files")
    args = parser.parse_args()

    folder = Path(args.folder).resolve()
    if not folder.exists() or not folder.is_dir():
        raise SystemExit(f"Folder not found: {folder}")

    asyncio.run(main_async(folder, concurrency=max(1, args.concurrency), overwrite=args.overwrite))


if __name__ == "__main__":
    main()