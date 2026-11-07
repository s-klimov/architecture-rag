"""Режет базу знаний на чанки и сохраняет векторный индекс FAISS."""

import json
import time
from pathlib import Path

import faiss
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer

ROOT = Path(__file__).parent
KB = ROOT / "knowledge_base"
INDEX_PATH = ROOT / "faiss.index"
CHUNKS_PATH = ROOT / "chunks.json"

# Модель из задания 1. Вектор — 384 числа.
# https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

# 200 слов на чанк (задание просит 100–300), с перекрытием, чтобы фраза на стыке не потерялась.
SPLITTER = RecursiveCharacterTextSplitter(
    chunk_size=200,
    chunk_overlap=40,
    length_function=lambda text: len(text.split()),
    add_start_index=True,
)

QUERIES = [
    "Who is Lir Kass?",
    "What is the Void Core?",
    "What is Edict 66?",
]


def load_chunks():
    chunks = []
    for path in sorted(KB.glob("*.md")):
        raw = path.read_text(encoding="utf-8")
        lines = raw.splitlines()
        # У обычных статей первая строка — заголовок. Файл без «#» берём целиком.
        if lines and lines[0].startswith("#"):
            title = lines[0].lstrip("# ").strip()
            text = "\n".join(lines[1:]).strip()
        else:
            title = path.stem
            text = raw.strip()
        if not text:
            continue
        # Смещение тела относительно начала файла, чтобы start указывал позицию в исходнике.
        body_at = raw.find(text)
        docs = SPLITTER.create_documents(
            [text],
            metadatas=[{"source": f"knowledge_base/{path.name}", "title": title}],
        )
        parts = []
        for doc in docs:
            part = {
                "text": doc.page_content,
                "source": doc.metadata["source"],
                "title": title,
                "start": body_at + doc.metadata.get("start_index", 0),
            }
            # Короткий хвост приклеиваем к предыдущему куску, если вместе выходит не больше 300 слов.
            if parts and len(part["text"].split()) < 100:
                merged = parts[-1]["text"] + "\n\n" + part["text"]
                if len(merged.split()) <= 300:
                    parts[-1]["text"] = merged
                    continue
            parts.append(part)
        if len(parts) >= 2 and len(parts[0]["text"].split()) < 100:
            merged = parts[0]["text"] + "\n\n" + parts[1]["text"]
            if len(merged.split()) <= 300:
                parts[1]["text"] = merged
                parts[1]["start"] = parts[0]["start"]
                parts = parts[1:]
        for number, part in enumerate(parts, start=1):
            part["id"] = f"{path.stem}-{number}"
            chunks.append(part)
    return chunks


def search(model, index, chunks, query, k=2):
    vector = model.encode([query], convert_to_numpy=True).astype("float32")
    faiss.normalize_L2(vector)
    scores, ids = index.search(vector, k)
    found = []
    for score, idx in zip(scores[0], ids[0]):
        chunk = chunks[int(idx)]
        found.append((float(score), chunk))
    return found


def main():
    started = time.perf_counter()
    chunks = load_chunks()
    model = SentenceTransformer(MODEL_NAME)
    vectors = model.encode(
        [chunk["text"] for chunk in chunks],
        convert_to_numpy=True,
        show_progress_bar=False,
    ).astype("float32")
    # Для этой модели близость считают косинусом: векторы нормализуют и ищут скалярное произведение.
    faiss.normalize_L2(vectors)
    index = faiss.IndexFlatIP(vectors.shape[1])
    index.add(vectors)
    faiss.write_index(index, str(INDEX_PATH))
    CHUNKS_PATH.write_text(
        json.dumps(chunks, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    elapsed = time.perf_counter() - started
    print(f"Модель: {MODEL_NAME}")
    print(f"Размер эмбеддинга: {vectors.shape[1]}")
    print(f"Чанков: {len(chunks)}")
    print(f"Время: {elapsed:.1f} с")
    print(f"Индекс: {INDEX_PATH.name}, тексты чанков: {CHUNKS_PATH.name}")

    for query in QUERIES:
        print(f"\nЗапрос: {query}")
        for score, chunk in search(model, index, chunks, query):
            preview = " ".join(chunk["text"].split())[:220]
            print(f"- {chunk['title']} | {chunk['id']} | {chunk['source']} | сходство {score:.3f}")
            print(f"  {preview}")


if __name__ == "__main__":
    main()
