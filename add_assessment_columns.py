import asyncio
from sqlalchemy import text
from database import engine

async def add_column_safe(table_name, col_name, col_type):
    async with engine.begin() as conn:
        try:
            await conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_type};"))
            print(f"Successfully added {col_name} to {table_name}.")
        except Exception as e:
            if "already exists" in str(e).lower():
                print(f"Column {col_name} already exists in {table_name}.")
            else:
                print(f"Error adding {col_name} to {table_name}: {e}")

async def add_columns():
    print("Checking/adding columns for assessment_results and assessment_sessions...")
    
    # assessment_results columns
    await add_column_safe("assessment_results", "personality_score", "INTEGER")
    await add_column_safe("assessment_results", "aptitude_score", "INTEGER")
    await add_column_safe("assessment_results", "reasoning_score", "INTEGER")
    await add_column_safe("assessment_results", "emotional_intelligence_score", "INTEGER")
    await add_column_safe("assessment_results", "tokens_utilized", "INTEGER DEFAULT 0")
    
    # assessment_sessions columns
    await add_column_safe("assessment_sessions", "tokens_utilized", "INTEGER DEFAULT 0")

if __name__ == "__main__":
    asyncio.run(add_columns())
