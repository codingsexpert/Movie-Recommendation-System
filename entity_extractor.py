import json
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from config import genai_client

EXTRACTION_PROMPT = """You are a precise entity extractor for a movie knowledge graph.

From the attached PDF, extract movies {START} through {END} (by their order in the document).

For EACH movie, output this EXACT JSON structure:
{{
  "movie": {{"title": "string", "year": number}},
  "director": {{"name": "string"}},
  "actors": ["string"],
  "genres": ["string"],
  "themes": ["string"],
  "awards": ["string"]
}}

Rules:
- If awards say "None", return awards as empty array []
- Keep exact names as written in the PDF
- Year must be a number, not string
- Return a JSON ARRAY of objects: [{{...}}, {{...}}, ...]
- Return ONLY valid JSON. No markdown, no backticks, no explanation."""

def upload_pdf(pdf_path: str):
    """Upload PDF to Gemini Files API."""
    print("   📤 Uploading PDF to Gemini Files API...")
    uploaded_file = genai_client.files.upload(file=pdf_path)

    # Wait until processing completes
    file_info = genai_client.files.get(name=uploaded_file.name)
    while str(getattr(file_info, "state", "")).upper() == "PROCESSING":
        print("   ⏳ PDF processing...")
        time.sleep(3)
        file_info = genai_client.files.get(name=uploaded_file.name)

    if str(getattr(file_info, "state", "")).upper() == "FAILED":
        raise RuntimeError("PDF upload processing failed")

    print(f"   ✅ PDF uploaded: {uploaded_file.name}")
    return file_info

def extract_batch(file_info, start: int, end: int, attempt: int = 1) -> list[dict]:
    """Extract one batch of movies from the uploaded PDF with retries."""
    max_retries = 3
    prompt = EXTRACTION_PROMPT.format(START=start, END=end)

    try:
        response = genai_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[file_info, prompt]
        )

        raw = response.text.strip()
        # Clean markdown code blocks if present
        raw = re.sub(r"```json\s*", "", raw)
        raw = re.sub(r"```\s*", "", raw).strip()

        parsed = json.loads(raw)
        return parsed if isinstance(parsed, list) else [parsed]
    except Exception as err:
        err_msg = str(err)
        if attempt < max_retries:
            is_429 = "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg
            wait = attempt * 30 if is_429 else attempt * 10
            reason = "Rate limited" if is_429 else "Error"
            print(f"   ⚠️ {reason}. Waiting {wait}s (retry {attempt + 1}/{max_retries})...")
            time.sleep(wait)
            return extract_batch(file_info, start, end, attempt + 1)

        print(f"   ❌ Batch {start}-{end} FAILED after {max_retries} attempts: {err_msg[:150]}")
        return []

def count_movies(file_info) -> int:
    """Ask the model to estimate total movies in the PDF."""
    prompt = "Read the attached document and return only a single integer representing the total number of movies listed in the document."
    response = genai_client.models.generate_content(model="gemini-2.5-flash", contents=[file_info, prompt])
    try:
        return int(re.sub(r'\D', '', response.text))
    except:
        return 0

def extract_all_entities(pdf_path: str, batch_size: int = 50) -> list[dict]:
    """Extract ALL entities from PDF using parallel batch requests."""
    file_info = upload_pdf(pdf_path)
    
    total_movies = count_movies(file_info)
    print(f"   🔍 Detected {total_movies} movies in document.")

    total_batches = (total_movies + batch_size - 1) // batch_size
    all_batches = []
    for i in range(total_batches):
        start = i * batch_size + 1
        end = min((i + 1) * batch_size, total_movies)
        all_batches.append({"start": start, "end": end})

    concurrency = 5
    results = []
    failed_batches = []

    print(f"\n   📊 Pass 1: Extracting {total_batches} batches ({concurrency} parallel)...\n")

    for i in range(0, len(all_batches), concurrency):
        chunk = all_batches[i:i + concurrency]
        round_num = (i // concurrency) + 1
        total_rounds = (len(all_batches) + concurrency - 1) // concurrency

        print(f"🤖 Round {round_num}/{total_rounds}: Movies {chunk[0]['start']}-{chunk[-1]['end']}...")

        with ThreadPoolExecutor(max_workers=concurrency) as executor:
            future_to_batch = {
                executor.submit(extract_batch, file_info, b["start"], b["end"]): b
                for b in chunk
            }
            for future in as_completed(future_to_batch):
                batch = future_to_batch[future]
                res = future.result()
                if res:
                    results.extend(res)
                else:
                    failed_batches.append(batch)

        print(f"   ✅ Total so far: {len(results)} movies")
        if i + concurrency < len(all_batches):
            time.sleep(2)

    # Pass 2: Retry failed batches
    if failed_batches:
        print(f"\n   🔄 Pass 2: Retrying {len(failed_batches)} failed batches...\n")
        time.sleep(5)

        for batch in failed_batches:
            print(f"🔄 Retrying movies {batch['start']}-{batch['end']}...")
            res = extract_batch(file_info, batch['start'], batch['end'])
            if res:
                results.extend(res)
                print(f"   ✅ Retry success! Got {len(res)} movies (total: {len(results)})")
            else:
                print(f"   ❌ Movies {batch['start']}-{batch['end']} permanently failed.")
            time.sleep(2)

    # Delete uploaded file from Gemini server
    try:
        genai_client.files.delete(name=file_info.name)
        print("   🗑️ PDF deleted from Gemini servers")
    except Exception:
        pass

    print(f"\n✅ Total extracted: {len(results)}/{total_movies} movies")
    if len(results) < total_movies:
        print(f"⚠️ {total_movies - len(results)} movies missing. You can re-run indexing to fill gaps.")

    return results

if __name__ == "__main__":
    entities = extract_all_entities("./data/movies.pdf", batch_size=5)
    print("Extracted sample:", len(entities))

