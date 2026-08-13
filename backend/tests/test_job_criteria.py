from __future__ import annotations

import json
import unittest
from typing import Any

from pydantic import BaseModel
from tortoise import Tortoise

from app.db.models import Company, Job
from app.enums import JobStatus
from app.schemas import JobEvaluationCriteria
from app.services.ai.job_criteria import JobCriteriaService
from app.services.errors import (
    InvalidJobCriteriaOutputError,
    JobCriteriaJobNotFoundError,
)


class MockStructuredOutputClient:
    def __init__(self, result: object) -> None:
        self.result = result
        self.calls: list[dict[str, object]] = []

    async def generate_structured(
        self,
        *,
        instructions: str,
        input_text: str,
        response_model: type[BaseModel],
    ) -> Any:
        self.calls.append(
            {
                "instructions": instructions,
                "input_text": input_text,
                "response_model": response_model,
            }
        )
        return self.result


def criteria_result() -> dict[str, object]:
    return {
        "required_skills": ["Python", "PostgreSQL"],
        "preferred_skills": ["FastAPI", "Docker"],
        "minimum_experience_years": 3,
        "relevant_domains": ["Recruitment technology"],
        "relevant_experience": [
            "Building production APIs",
            "Designing relational data models",
        ],
        "education_requirements": [],
        "important_responsibilities": [
            "Build reliable backend services",
            "Collaborate with product teams",
        ],
        "evaluation_categories": [
            {
                "name": "Required Technical Skills",
                "description": "Evidence of Python and PostgreSQL experience.",
                "weight": 40,
            },
            {
                "name": "Relevant Experience",
                "description": "Experience delivering production APIs.",
                "weight": 35,
            },
            {
                "name": "Core Responsibilities",
                "description": "Experience owning reliable backend services.",
                "weight": 15,
            },
            {
                "name": "Preferred Skills",
                "description": "Evidence of FastAPI or Docker experience.",
                "weight": 10,
            },
        ],
    }


class JobCriteriaTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        await Tortoise.init(
            db_url="sqlite://:memory:", modules={"models": ["app.db.models"]}
        )
        await Tortoise.generate_schemas()
        self.company = await Company.create(name="Criteria Test Company")
        self.job = await Job.create(
            company=self.company,
            title="Backend Engineer",
            description=(
                "Build reliable Python APIs backed by PostgreSQL and collaborate "
                "with product teams in recruitment technology."
            ),
            required_skills=["Python", "PostgreSQL"],
            preferred_skills=["FastAPI", "Docker"],
            experience_requirement="3+ years building production APIs",
            evaluation_criteria={"previous": "value"},
            status=JobStatus.OPEN,
        )

    async def asyncTearDown(self) -> None:
        await Tortoise.close_connections()

    async def test_generates_job_specific_structured_criteria(self) -> None:
        client = MockStructuredOutputClient(criteria_result())
        service = JobCriteriaService(client=client)

        criteria = await service.generate(self.job)

        self.assertIsInstance(criteria, JobEvaluationCriteria)
        self.assertEqual(criteria.minimum_experience_years, 3)
        self.assertEqual(criteria.relevant_domains, ["Recruitment technology"])
        self.assertEqual(
            sum(category.weight for category in criteria.evaluation_categories),
            100,
        )
        self.assertIs(client.calls[0]["response_model"], JobEvaluationCriteria)
        instructions = str(client.calls[0]["instructions"])
        self.assertIn("Never invent", instructions)
        self.assertIn("Do not\n  reuse a fixed category list", instructions)

    async def test_required_and_preferred_skills_remain_distinct(self) -> None:
        criteria = await JobCriteriaService(
            client=MockStructuredOutputClient(criteria_result())
        ).generate(self.job)

        self.assertEqual(criteria.required_skills, ["Python", "PostgreSQL"])
        self.assertEqual(criteria.preferred_skills, ["FastAPI", "Docker"])
        self.assertFalse(
            {skill.casefold() for skill in criteria.required_skills}
            & {skill.casefold() for skill in criteria.preferred_skills}
        )

    async def test_missing_optional_job_fields_are_passed_as_empty_values(self) -> None:
        job = await Job.create(
            company=self.company,
            title="Operations Coordinator",
            description="Coordinate daily operational activities.",
            required_skills=[],
            preferred_skills=[],
            experience_requirement=None,
        )
        client = MockStructuredOutputClient(
            {
                "required_skills": [],
                "preferred_skills": [],
                "minimum_experience_years": None,
                "important_responsibilities": [
                    "Coordinate daily operational activities"
                ],
                "evaluation_categories": [
                    {
                        "name": "Operational Responsibilities",
                        "description": "Relevant coordination experience.",
                        "weight": 100,
                    }
                ],
            }
        )

        criteria = await JobCriteriaService(client=client).generate(job)

        self.assertEqual(criteria.required_skills, [])
        self.assertEqual(criteria.preferred_skills, [])
        self.assertIsNone(criteria.minimum_experience_years)
        input_text = str(client.calls[0]["input_text"])
        encoded = input_text.split("<job_information>\n", 1)[1].split(
            "\n</job_information>", 1
        )[0]
        job_information = json.loads(encoded)
        self.assertEqual(job_information["required_skills"], [])
        self.assertEqual(job_information["preferred_skills"], [])
        self.assertIsNone(job_information["experience_requirement"])

    async def test_invalid_weights_and_skill_overlap_are_rejected(self) -> None:
        invalid_weight = criteria_result()
        invalid_weight["evaluation_categories"] = [
            {
                "name": "Technical Skills",
                "description": "Required technical evidence.",
                "weight": 90,
            }
        ]
        with self.assertRaisesRegex(
            InvalidJobCriteriaOutputError, "invalid structured data"
        ):
            await JobCriteriaService(
                client=MockStructuredOutputClient(invalid_weight)
            ).generate(self.job)

        overlap = criteria_result()
        overlap["preferred_skills"] = ["python"]
        with self.assertRaisesRegex(
            InvalidJobCriteriaOutputError, "invalid structured data"
        ):
            await JobCriteriaService(
                client=MockStructuredOutputClient(overlap)
            ).generate(self.job)

    async def test_generated_criteria_are_saved_without_changing_job_fields(self) -> None:
        original_fields = {
            "title": self.job.title,
            "description": self.job.description,
            "required_skills": self.job.required_skills,
            "preferred_skills": self.job.preferred_skills,
            "experience_requirement": self.job.experience_requirement,
        }
        service = JobCriteriaService(
            client=MockStructuredOutputClient(criteria_result())
        )

        criteria = await service.generate_and_save(self.job.id)

        await self.job.refresh_from_db()
        self.assertEqual(
            self.job.evaluation_criteria,
            criteria.model_dump(mode="json"),
        )
        for field_name, original_value in original_fields.items():
            self.assertEqual(getattr(self.job, field_name), original_value)

    async def test_missing_job_record_is_rejected(self) -> None:
        service = JobCriteriaService(
            client=MockStructuredOutputClient(criteria_result())
        )

        with self.assertRaisesRegex(JobCriteriaJobNotFoundError, "record not found"):
            await service.generate_and_save(999_999)


if __name__ == "__main__":
    unittest.main()
