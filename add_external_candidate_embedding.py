"""
Migration: Add embedding column to external_candidates table.
Run: python add_external_candidate_embedding.py
"""
import asyncio
from sqlalchemy import text
from database import async_engine


async def migrate():
    async with async_engine.begin() as conn:
        # 1. Add the embedding column (vector(3072) for gemini-embedding-001)
        print("Adding embedding column to external_candidates...")
        await conn.execute(
            text("ALTER TABLE external_candidates ADD COLUMN IF NOT EXISTS embedding vector(3072)")
        )
        print("✓ embedding column added (or already exists)")

        # 2. Re-embed existing candidates that have profile data but no embedding
        print("\nChecking for existing candidates to embed...")
        rows = await conn.execute(
            text(
                "SELECT id, full_name, department, sub_role, industries, "
                "total_experience, available_shift, professional_journey "
                "FROM external_candidates "
                "WHERE embedding IS NULL"
            )
        )
        candidates = rows.fetchall()
        print(f"Found {len(candidates)} candidates without embeddings.")

        if not candidates:
            print("Nothing to re-embed — done.")
            return

        from services.ai_service import get_ai
        ai = get_ai()

        for row in candidates:
            parts = []
            if row.full_name:
                parts.append(f"Name: {row.full_name}")
            if row.department:
                parts.append(f"Department: {row.department}")
            if row.sub_role:
                parts.append(f"Role: {row.sub_role}")
            if row.industries:
                try:
                    import json
                    ind = json.loads(row.industries) if isinstance(row.industries, str) else row.industries
                    if isinstance(ind, list):
                        parts.append(f"Industries: {', '.join(ind)}")
                except Exception:
                    parts.append(f"Industries: {row.industries}")
            if row.total_experience:
                parts.append(f"Experience: {row.total_experience}")
            if row.available_shift:
                parts.append(f"Available Shift: {row.available_shift}")
            if row.professional_journey:
                parts.append(f"Professional Journey: {row.professional_journey}")

            text_content = "\n".join(parts)[:6000]
            if not text_content.strip():
                continue

            try:
                embedding = await ai.embed(text_content)
                await conn.execute(
                    text(
                        "UPDATE external_candidates "
                        "SET embedding = CAST(:emb AS vector) "
                        "WHERE id = :id"
                    ),
                    {"emb": str(embedding), "id": row.id},
                )
                print(f"  ✓ Embedded candidate {row.id} ({row.full_name})")
            except Exception as e:
                print(f"  ✗ Failed to embed candidate {row.id}: {e}")

        print(f"\nRe-embedding complete.")


if __name__ == "__main__":
    asyncio.run(migrate())
