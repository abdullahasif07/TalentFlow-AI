import asyncio
from decimal import Decimal

from tortoise import Tortoise

from app.config import TORTOISE_ORM
from app.db.models import Application, Candidate, Company, Job, Recruiter, Resume
from app.enums import ApplicationStatus, JobStatus


CANDIDATES = [
    ("Aisha Rahman", "aisha.rahman@example.com", "+1-415-555-0110", "aisharahman"),
    ("Daniel Kim", "daniel.kim@example.com", "+1-415-555-0111", "danielkimdev"),
    ("Sofia Martinez", "sofia.martinez@example.com", "+1-415-555-0112", "sofiamartinez"),
    ("Marcus Johnson", "marcus.johnson@example.com", "+1-415-555-0113", "marcusj"),
    ("Priya Nair", "priya.nair@example.com", "+1-415-555-0114", "priyanair"),
    ("Ethan Williams", "ethan.williams@example.com", "+1-415-555-0115", "ethanwdev"),
    ("Lina Chen", "lina.chen@example.com", "+1-415-555-0116", "linachen"),
    ("Omar Hassan", "omar.hassan@example.com", "+1-415-555-0117", "omarhassan"),
    ("Grace Okafor", "grace.okafor@example.com", "+1-415-555-0118", "graceokafor"),
    ("Lucas Silva", "lucas.silva@example.com", "+1-415-555-0119", "lucassilva"),
]


async def seed() -> None:
    await Tortoise.init(config=TORTOISE_ORM)
    try:
        company, _ = await Company.get_or_create(
            name="Northstar Labs",
            defaults={
                "description": "A product studio building dependable tools for modern teams.",
                "website": "https://northstar.example.com",
            },
        )
        await Recruiter.get_or_create(
            email="maya.patel@northstar.example.com",
            defaults={"company": company, "name": "Maya Patel", "role": "Lead Recruiter"},
        )

        backend_job, _ = await Job.get_or_create(
            company=company,
            title="Senior Backend Engineer",
            defaults={
                "description": "Build reliable APIs and data services for a growing B2B platform.",
                "required_skills": ["Python", "FastAPI", "PostgreSQL"],
                "preferred_skills": ["GraphQL", "AWS", "Docker"],
                "experience_requirement": "5+ years in backend or platform engineering",
                "evaluation_criteria": {
                    "backend_depth": 40,
                    "system_design": 30,
                    "collaboration": 30,
                },
                "status": JobStatus.OPEN,
            },
        )
        product_job, _ = await Job.get_or_create(
            company=company,
            title="Product Designer",
            defaults={
                "description": "Own end-to-end product design for collaborative workflow products.",
                "required_skills": ["Product design", "Figma", "User research"],
                "preferred_skills": ["Design systems", "B2B SaaS", "Prototyping"],
                "experience_requirement": "4+ years designing shipped digital products",
                "evaluation_criteria": {
                    "portfolio": 40,
                    "product_thinking": 35,
                    "communication": 25,
                },
                "status": JobStatus.OPEN,
            },
        )

        statuses = [
            ApplicationStatus.APPLIED,
            ApplicationStatus.HUMAN_REVIEW,
            ApplicationStatus.SHORTLISTED,
            ApplicationStatus.INTERVIEW,
            ApplicationStatus.CONTACTED,
        ]
        for index, (name, email, phone, handle) in enumerate(CANDIDATES):
            candidate, _ = await Candidate.get_or_create(
                email=email,
                defaults={
                    "name": name,
                    "phone": phone,
                    "linkedin_url": f"https://linkedin.com/in/{handle}",
                    "github_url": f"https://github.com/{handle}" if index % 2 == 0 else None,
                    "portfolio_url": f"https://{handle}.example.com" if index % 2 else None,
                },
            )
            await Resume.get_or_create(
                candidate=candidate,
                defaults={
                    "file_url": f"https://files.example.com/resumes/{handle}.pdf",
                    "parsed_data": {},
                },
            )
            job = backend_job if index < 6 else product_job
            await Application.get_or_create(
                candidate=candidate,
                job=job,
                defaults={
                    "resume_url": f"https://files.example.com/resumes/{handle}.pdf",
                    "cover_letter": f"I am excited to apply for the {job.title} role at Northstar Labs.",
                    "status": statuses[index % len(statuses)],
                    "fit_score": Decimal(str(68 + index * 2.5)),
                },
            )

        print("Seed complete: 1 company, 1 recruiter, 2 jobs, 10 candidates/applications.")
    finally:
        await Tortoise.close_connections()


if __name__ == "__main__":
    asyncio.run(seed())

