import re
from pypdf import PdfReader

def parse_pdf(pdf_path: str) -> list[str]:
    """
    Parses a PDF file and splits text by dash separator into movie blocks.
    
    Input: './data/movies.pdf'
    Output: ['Movie Title: Movie 0001\n...', 'Movie Title: Movie 0002\n...', ...]
    """
    reader = PdfReader(pdf_path)
    pages_text = [page.extract_text() for page in reader.pages if page.extract_text()]
    raw_text = "\n".join(pages_text)

    print(f"📄 PDF parsed: {len(reader.pages)} pages, {len(raw_text)} characters")

    # Split by separator (10+ dashes in a row)
    blocks = re.split(r"-{10,}", raw_text)
    movie_blocks = [
        block.strip()
        for block in blocks
        if block and block.strip() and "Movie Title" in block
    ]

    print(f"🎬 Found {len(movie_blocks)} movie blocks")
    return movie_blocks

if __name__ == "__main__":
    blocks = parse_pdf("./data/movies.pdf")
    if blocks:
        print("Sample block 1 snippet:\n", blocks[0][:200])
