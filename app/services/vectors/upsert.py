from typing import Any

def upsert_file_chunks(
    index: Any,
    namespace: str,
    job_id: str,
    file_meta: dict,
    chunks: list[str],
    vectors: list[list[float]],
    chunk_index_offset: int = 0,
    batch_size: int = 50,
) -> None:
    file_id = file_meta["id"]
    file_name = file_meta.get("name")
    mime_type = file_meta.get("mimeType")

    total = len(vectors)
    for start in range(0, total, batch_size):
        end = min(start + batch_size, total)
        payload = []

        for i in range(start, end):
            chunk_index = chunk_index_offset + i
            payload.append(
                {
                    "id": f"{job_id}:{file_id}:{chunk_index}",
                    "values": vectors[i],
                    "metadata": {
                        "job_id": job_id,
                        "file_id": file_id,
                        "file_name": file_name,
                        "mime_type": mime_type,
                        "chunk_index": chunk_index,
                        "text_preview": chunks[i][:200],
                        "source": "gdrive",
                    },
                }
            )

        index.upsert(vectors=payload, namespace=namespace)


def upsert_resume_embedding(
    index: Any,
    namespace: str,
    file_id: str,
    file_name: str,
    vector: list[float],
    job_id: str | None = None,
) -> None:
    payload = [
        {
            "id": file_id,
            "values": vector,
            "metadata": {
                "file_id": file_id,
                "file_name": file_name,
                "job_id": job_id,
                "source": "resume_overall_summary",
            },
        }
    ]
    index.upsert(vectors=payload, namespace=namespace)