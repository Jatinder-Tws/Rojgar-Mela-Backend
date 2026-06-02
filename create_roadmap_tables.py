import asyncio
from sqlalchemy import text
from database import AsyncSessionLocal

async def create_tables():
    """Create roadmap tables"""
    
    sql_statements = [
        # Create roadmaps table
        """
        CREATE TABLE IF NOT EXISTS roadmaps (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            target_role VARCHAR(100) NOT NULL,
            current_level VARCHAR(50) NOT NULL,
            target_level VARCHAR(50) NOT NULL,
            skills_to_develop TEXT[],
            estimated_duration VARCHAR(50),
            status VARCHAR(20) DEFAULT 'active' NOT NULL,
            ai_prompt_version VARCHAR(20) DEFAULT '1.0' NOT NULL,
            generation_preferences JSONB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
        );
        """,
        
        # Create milestones table
        """
        CREATE TABLE IF NOT EXISTS milestones (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            roadmap_id UUID NOT NULL REFERENCES roadmaps(id) ON DELETE CASCADE,
            title VARCHAR(200) NOT NULL,
            description TEXT,
            order_num INTEGER NOT NULL,
            skills TEXT[],
            estimated_time VARCHAR(50),
            difficulty VARCHAR(20) DEFAULT 'intermediate',
            status VARCHAR(20) DEFAULT 'pending' NOT NULL,
            dependencies UUID[],
            started_at TIMESTAMP,
            completed_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
        );
        """,
        
        # Create resources table
        """
        CREATE TABLE IF NOT EXISTS resources (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            milestone_id UUID NOT NULL REFERENCES milestones(id) ON DELETE CASCADE,
            title VARCHAR(200) NOT NULL,
            type VARCHAR(20) NOT NULL,
            url TEXT,
            platform VARCHAR(100),
            duration VARCHAR(50),
            difficulty VARCHAR(20),
            description TEXT,
            is_free BOOLEAN DEFAULT true NOT NULL,
            rating FLOAT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
        );
        """,
        
        # Create indexes
        """
        CREATE INDEX IF NOT EXISTS idx_roadmaps_user_id ON roadmaps(user_id);
        CREATE INDEX IF NOT EXISTS idx_milestones_roadmap_id ON milestones(roadmap_id);
        CREATE INDEX IF NOT EXISTS idx_resources_milestone_id ON resources(milestone_id);
        """
    ]
    
    async with AsyncSessionLocal() as session:
        for statement in sql_statements:
            await session.execute(text(statement))
        await session.commit()
        print("Roadmap tables created successfully!")

if __name__ == "__main__":
    asyncio.run(create_tables())