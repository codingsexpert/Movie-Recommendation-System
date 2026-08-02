import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pypdf import PdfReader
from config import embed_text, pinecone_index

EMBED_CONCURRENCY = 5
EMBED_DELAY_MS = 0.5
UPSERT_BATCH_SIZE = 100

def parse_pdf_raw(pdf_path: str) -> str:
    """Parse raw text from PDF."""
    reader = PdfReader(pdf_path)
    pages_text = [page.extract_text() for page in reader.pages if page.extract_text()]
    raw_text = "\n".join(pages_text)
    print(f"   📄 Parsed PDF: {len(reader.pages)} pages, ~{len(raw_text)} characters")
    return raw_text

def chunk_text(raw_text: str) -> list[str]:
    """Chunk raw text by separators."""
    blocks = re.split(r"\n-{5,}\n", raw_text)
    chunks = []
    for block in blocks:
        text = block.strip()
        if text and len(text) >= 20:
            chunks.append(text)
    return chunks

def embed_with_retry(text: str, max_retries: int = 3) -> list[float] | None:
    """Embed single text with retries."""
    for attempt in range(1, max_retries + 1):
        try:
            return embed_text(text)
        except Exception as err:
            err_msg = str(err)
            is_429 = "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg
            wait = attempt * 20 if is_429 else attempt * 5
            if attempt < max_retries:
                print(f"   ⚠️ Embed failed (attempt {attempt}). Waiting {wait}s...")
                time.sleep(wait)
            else:
                print(f"   ❌ Embed permanently failed: {err_msg[:100]}")
                return None

def build_vector_store(pdf_path: str):
    """Parse PDF -> Chunk -> Embed -> Upsert to Pinecone."""
    print(f"\n📐 Building vector store from PDF...")
    print(f"   ⚡ Concurrency: {EMBED_CONCURRENCY} parallel embeddings\n")

    start_time = time.time()

    # Step 1: Parse PDF
    print("   📄 Step 1: Parsing PDF...")
    raw_text = parse_pdf_raw(pdf_path)

    # Step 2: Chunk
    print("   ✂️  Step 2: Chunking text...")
    chunks = chunk_text(raw_text)
    print(f"   ✅ Created {len(chunks)} chunks")

    if not chunks:
        print("   ❌ No chunks created! Check PDF format.")
        return

    # Step 3: Embed chunks
    print(f"\n   🧠 Step 3: Embedding {len(chunks)} chunks...")
    vectors = []
    fail_count = 0

    for i in range(0, len(chunks), EMBED_CONCURRENCY):
        batch = chunks[i:i + EMBED_CONCURRENCY]
        round_num = (i // EMBED_CONCURRENCY) + 1
        total_rounds = (len(chunks) + EMBED_CONCURRENCY - 1) // EMBED_CONCURRENCY

        if (round_num - 1) % 10 == 0 or round_num == total_rounds:
            print(f"   🔄 Round {round_num}/{total_rounds} (chunks {i + 1}-{min(i + EMBED_CONCURRENCY, len(chunks))})...")

        with ThreadPoolExecutor(max_workers=EMBED_CONCURRENCY) as executor:
            future_to_idx = {
                executor.submit(embed_with_retry, text): (i + j, text)
                for j, text in enumerate(batch)
            }
            for future in as_completed(future_to_idx):
                idx, text = future_to_idx[future]
                embedding = future.result()
                if embedding:
                    vectors.append({
                        "id": f"chunk-{idx}",
                        "values": embedding,
                        "metadata": {"text": text}
                    })
                else:
                    fail_count += 1

        if i + EMBED_CONCURRENCY < len(chunks):
            time.sleep(EMBED_DELAY_MS)

    embed_time = round(time.time() - start_time, 1)
    print(f"\n   ✅ Embedded {len(vectors)}/{len(chunks)} in {embed_time}s ({fail_count} failed)")

    if not vectors:
        print("   ❌ No vectors to upsert!")
        return

    # Step 4: Upsert to Pinecone
    print(f"\n   📦 Step 4: Upserting to Pinecone...")
    # Sort by ID so order is consistent
    vectors.sort(key=lambda x: int(x["id"].split("-")[1]))

    for i in range(0, len(vectors), UPSERT_BATCH_SIZE):
        batch = vectors[i:i + UPSERT_BATCH_SIZE]
        batch_num = (i // UPSERT_BATCH_SIZE) + 1
        total_batches = (len(vectors) + UPSERT_BATCH_SIZE - 1) // UPSERT_BATCH_SIZE

        print(f"   📦 Batch {batch_num}/{total_batches} ({len(batch)} vectors)...")
        pinecone_index.upsert(vectors=batch)

    total_time = round(time.time() - start_time, 1)
    stats = pinecone_index.describe_index_stats()
    total_count = getattr(stats, "total_vector_count", getattr(stats, "total_record_count", 0))
    print(f"\n✅ Vector store built in {total_time}s! Total vectors: {total_count}")
