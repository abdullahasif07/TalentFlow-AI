"""Fictional demo dataset: one company, four roles, and twelve applicants.

Every person, company, and email address here is invented. Evaluations are written in
the same shape the AI evaluator produces, so the UI renders them identically.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.enums import ApplicationStatus, EvaluationConfidence, JobStatus


COMPANY = {
    "name": "Northstar Labs",
    "description": "A product studio building dependable workflow tools for modern teams.",
    "website": "https://northstar.example.com",
}

DEMO_RECRUITER = {"name": "Demo Recruiter", "role": "Talent Partner"}


@dataclass(frozen=True)
class DemoJob:
    key: str
    title: str
    description: str
    required_skills: list[str]
    preferred_skills: list[str]
    experience_requirement: str
    minimum_years: float
    domains: list[str]
    responsibilities: list[str]
    categories: list[tuple[str, str, int]]  # (name, description, weight)
    status: JobStatus = JobStatus.OPEN


JOBS: list[DemoJob] = [
    DemoJob(
        key="backend",
        title="Senior Backend Engineer",
        description=(
            "Design and operate the APIs and data services behind Northstar's workflow "
            "platform. You will own services end to end - from schema design to on-call - "
            "and help the team scale from thousands to millions of daily requests."
        ),
        required_skills=["Python", "FastAPI", "PostgreSQL"],
        preferred_skills=["GraphQL", "AWS", "Docker"],
        experience_requirement="5+ years building backend or platform systems",
        minimum_years=5,
        domains=["B2B SaaS", "API platforms"],
        responsibilities=[
            "Design and ship reliable, well-tested APIs",
            "Own database schema design and query performance",
            "Improve observability and incident response",
        ],
        categories=[
            ("Backend engineering depth", "Production experience building Python APIs and services.", 35),
            ("System design & scalability", "Evidence of designing systems for scale and reliability.", 25),
            ("Data & infrastructure", "Relational data modeling, cloud infrastructure, and deployment.", 20),
            ("Collaboration & ownership", "Mentoring, cross-team work, and end-to-end ownership.", 20),
        ],
    ),
    DemoJob(
        key="design",
        title="Product Designer",
        description=(
            "Own end-to-end product design for collaborative workflow features, from "
            "discovery research to polished, shipped interfaces, working closely with "
            "product and engineering."
        ),
        required_skills=["Figma", "User research", "Interaction design"],
        preferred_skills=["Design systems", "Prototyping", "B2B SaaS"],
        experience_requirement="4+ years designing shipped digital products",
        minimum_years=4,
        domains=["B2B SaaS", "Productivity tools"],
        responsibilities=[
            "Lead discovery and usability research",
            "Design end-to-end flows and high-fidelity UI",
            "Contribute to the shared design system",
        ],
        categories=[
            ("Product design craft", "Quality of shipped interaction and visual design work.", 35),
            ("User research", "Planning and synthesizing qualitative and quantitative research.", 25),
            ("Design systems", "Building or maintaining reusable components and standards.", 20),
            ("Cross-functional collaboration", "Partnering with product managers and engineers.", 20),
        ],
    ),
    DemoJob(
        key="data",
        title="Data Analyst",
        description=(
            "Turn product and revenue data into decisions. You will build trusted models, "
            "dashboards, and analyses that help product, sales, and leadership teams "
            "understand what drives customer success."
        ),
        required_skills=["SQL", "Data visualization", "Statistics"],
        preferred_skills=["dbt", "Python", "Looker"],
        experience_requirement="3+ years in analytics or business intelligence",
        minimum_years=3,
        domains=["Product analytics", "SaaS metrics"],
        responsibilities=[
            "Model product and revenue data",
            "Build self-serve dashboards",
            "Partner with stakeholders on analyses",
        ],
        categories=[
            ("SQL & data modeling", "Writing performant SQL and maintaining analytics models.", 35),
            ("Analytics & statistics", "Experiment analysis and sound statistical reasoning.", 25),
            ("Visualization & storytelling", "Communicating insights through dashboards and narrative.", 20),
            ("Business partnership", "Working with stakeholders to frame and answer questions.", 20),
        ],
    ),
    DemoJob(
        key="manager",
        title="Engineering Manager, Platform",
        description=(
            "Lead a team of six platform engineers responsible for core infrastructure, "
            "developer experience, and reliability. This role is still being finalized."
        ),
        required_skills=["Engineering leadership", "System design", "Hiring"],
        preferred_skills=["Kubernetes", "B2B SaaS", "Incident management"],
        experience_requirement="2+ years managing engineers; 6+ years in engineering",
        minimum_years=6,
        domains=["Platform engineering"],
        responsibilities=[
            "Grow and support a platform team",
            "Own reliability goals and roadmap",
            "Partner with product engineering leads",
        ],
        categories=[
            ("People leadership", "Managing, coaching, and growing engineers.", 40),
            ("Technical judgment", "Architecture and platform decision-making.", 35),
            ("Execution", "Planning and delivering roadmaps reliably.", 25),
        ],
        status=JobStatus.DRAFT,
    ),
]


@dataclass(frozen=True)
class Role:
    company: str
    title: str
    start: str
    end: str
    summary: str
    technologies: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Finding:
    summary: str
    evidence: str


@dataclass(frozen=True)
class DemoCandidate:
    name: str
    email: str
    phone: str
    handle: str
    job_key: str
    headline: str
    years: float
    skills: list[str]
    roles: list[Role]
    education: tuple[str, str, str]  # institution, degree, field
    projects: list[tuple[str, str]] = field(default_factory=list)
    # Evaluation, or None to leave the applicant waiting for AI screening.
    category_scores: list[tuple[int, str]] | None = None  # (score, rationale) per category
    confidence: EvaluationConfidence = EvaluationConfidence.HIGH
    strengths: list[Finding] = field(default_factory=list)
    gaps: list[Finding] = field(default_factory=list)
    status_path: list[ApplicationStatus] = field(default_factory=list)
    days_ago: int = 3
    notes: list[str] = field(default_factory=list)
    outreach: tuple[str, str] | None = None  # (subject, body), recorded as sent
    cover_letter: str = ""


S = ApplicationStatus

CANDIDATES: list[DemoCandidate] = [
    # --- Senior Backend Engineer -----------------------------------------------------------
    DemoCandidate(
        name="Aisha Rahman",
        email="aisha.rahman@example.com",
        phone="+1 415 555 0110",
        handle="aisharahman",
        job_key="backend",
        headline="Backend engineer focused on high-throughput Python APIs and PostgreSQL.",
        years=7,
        skills=["Python", "FastAPI", "PostgreSQL", "GraphQL", "AWS", "Docker", "Redis", "Celery"],
        roles=[
            Role("Ledgerly", "Senior Backend Engineer", "2021-03", "Present",
                 "Led the move of a payments API to FastAPI, cutting p95 latency from 420ms to 90ms; "
                 "designed a partitioned PostgreSQL schema for 2B+ ledger rows; mentored four engineers.",
                 ["Python", "FastAPI", "PostgreSQL", "AWS", "Redis"]),
            Role("Brightpath Health", "Backend Engineer", "2018-01", "2021-02",
                 "Built GraphQL APIs for a care-coordination product and introduced Docker-based CI.",
                 ["Python", "GraphQL", "Docker", "Celery"]),
        ],
        education=("University of Washington", "B.S.", "Computer Science"),
        projects=[("pg-partman-tools", "Open-source helpers for managing time-partitioned PostgreSQL tables.")],
        category_scores=[
            (94, "Seven years of production Python, including leading a FastAPI migration with measured latency gains."),
            (88, "Designed a partitioned schema for billions of rows and owned latency improvements end to end."),
            (90, "Deep PostgreSQL work plus AWS and Docker in production."),
            (86, "Mentored four engineers and led a cross-team migration."),
        ],
        strengths=[
            Finding("Proven FastAPI and PostgreSQL depth at scale",
                    "Led the move of a payments API to FastAPI, cutting p95 latency from 420ms to 90ms."),
            Finding("Meets every required and preferred skill",
                    "Skills include Python, FastAPI, PostgreSQL, GraphQL, AWS, and Docker."),
        ],
        gaps=[Finding("Limited evidence of on-call or incident leadership",
                      "The resume does not describe incident response responsibilities.")],
        status_path=[S.AI_REVIEWED, S.HUMAN_REVIEW, S.SHORTLISTED, S.INTERVIEW],
        days_ago=12,
        notes=[
            "Excellent phone screen - walked through the ledger partitioning design in detail.",
            "Onsite scheduled with the platform team for Thursday.",
        ],
        cover_letter="I have spent the last three years scaling payments APIs on FastAPI and PostgreSQL "
                     "and would love to bring that experience to Northstar's platform.",
    ),
    DemoCandidate(
        name="Daniel Kim",
        email="daniel.kim@example.com",
        phone="+1 415 555 0111",
        handle="danielkimdev",
        job_key="backend",
        headline="Platform engineer working across Go and Python services and event streaming.",
        years=6,
        skills=["Python", "Go", "PostgreSQL", "Kafka", "Kubernetes", "AWS", "Docker"],
        roles=[
            Role("Streamline Logistics", "Platform Engineer", "2020-06", "Present",
                 "Built event-driven shipment tracking on Kafka handling 30k events/sec; maintained "
                 "Python and Go services on Kubernetes.",
                 ["Go", "Python", "Kafka", "Kubernetes", "AWS"]),
            Role("Cobalt Retail", "Software Engineer", "2018-07", "2020-05",
                 "Developed Flask APIs and PostgreSQL reporting queries for store operations.",
                 ["Python", "Flask", "PostgreSQL"]),
        ],
        education=("University of Illinois Urbana-Champaign", "B.S.", "Computer Engineering"),
        category_scores=[
            (80, "Solid Python API work, though recent focus has been Go services; no FastAPI evidence."),
            (90, "Designed an event-driven system handling 30k events per second."),
            (84, "PostgreSQL, AWS, Kubernetes, and Docker are all evidenced."),
            (72, "Collaboration is implied but not described in detail."),
        ],
        strengths=[
            Finding("Strong distributed systems experience",
                    "Built event-driven shipment tracking on Kafka handling 30k events/sec."),
            Finding("Broad infrastructure skills", "Maintained Python and Go services on Kubernetes in AWS."),
        ],
        gaps=[Finding("No direct FastAPI experience", "Python API work is described with Flask, not FastAPI.")],
        status_path=[S.AI_REVIEWED, S.HUMAN_REVIEW, S.SHORTLISTED],
        days_ago=9,
        notes=["Strong systems background. Ask about FastAPI ramp-up in the next conversation."],
    ),
    DemoCandidate(
        name="Sofia Martinez",
        email="sofia.martinez@example.com",
        phone="+1 415 555 0112",
        handle="sofiamartinez",
        job_key="backend",
        headline="Django developer building data-heavy internal tools.",
        years=4,
        skills=["Python", "Django", "PostgreSQL", "Docker", "React"],
        roles=[
            Role("Fieldnote", "Software Engineer", "2021-09", "Present",
                 "Built Django REST APIs for a field-research platform and optimized slow PostgreSQL "
                 "reports with indexing and materialized views.",
                 ["Python", "Django", "PostgreSQL", "Docker"]),
            Role("Civic Apps Co-op", "Junior Developer", "2020-01", "2021-08",
                 "Maintained Django sites and React dashboards for public-sector clients.",
                 ["Python", "Django", "React"]),
        ],
        education=("UC San Diego", "B.S.", "Cognitive Science"),
        category_scores=[
            (76, "Four years of Python web development with Django REST APIs."),
            (62, "Query optimization is evidenced, but no large-scale system design."),
            (78, "Clear PostgreSQL performance work and Docker usage."),
            (74, "Worked directly with public-sector clients."),
        ],
        confidence=EvaluationConfidence.MEDIUM,
        strengths=[Finding("Practical PostgreSQL performance work",
                           "Optimized slow PostgreSQL reports with indexing and materialized views.")],
        gaps=[
            Finding("Below the 5-year experience requirement", "Resume shows roughly four years of experience."),
            Finding("No FastAPI or GraphQL evidence", "APIs are described as Django REST only."),
        ],
        status_path=[S.AI_REVIEWED, S.HUMAN_REVIEW],
        days_ago=6,
    ),
    DemoCandidate(
        name="Marcus Johnson",
        email="marcus.johnson@example.com",
        phone="+1 415 555 0113",
        handle="marcusj",
        job_key="backend",
        headline="Full-stack JavaScript developer moving toward backend work.",
        years=3,
        skills=["Node.js", "TypeScript", "MongoDB", "Python", "Docker"],
        roles=[
            Role("Pixelcraft Agency", "Full-Stack Developer", "2022-02", "Present",
                 "Built Node.js and TypeScript APIs backed by MongoDB for client e-commerce sites; wrote "
                 "Python scripts for data imports.",
                 ["Node.js", "TypeScript", "MongoDB", "Python"]),
        ],
        education=("Georgia State University", "B.S.", "Information Systems"),
        category_scores=[
            (55, "API experience is primarily Node.js; Python use is limited to scripts."),
            (50, "No evidence of designing systems for scale."),
            (58, "MongoDB and Docker are evidenced; no PostgreSQL experience."),
            (68, "Agency work implies frequent client collaboration."),
        ],
        confidence=EvaluationConfidence.MEDIUM,
        strengths=[Finding("Hands-on API delivery", "Built Node.js and TypeScript APIs for client sites.")],
        gaps=[
            Finding("Missing PostgreSQL and FastAPI", "Databases listed are MongoDB only; Python is used for scripts."),
            Finding("Below the experience requirement", "Resume shows about three years of experience."),
        ],
        status_path=[S.AI_REVIEWED],
        days_ago=4,
    ),
    DemoCandidate(
        name="Ethan Williams",
        email="ethan.williams@example.com",
        phone="+1 415 555 0115",
        handle="ethanwdev",
        job_key="backend",
        headline="Senior Java engineer with a decade of enterprise backend experience.",
        years=9,
        skills=["Java", "Spring Boot", "Oracle", "PostgreSQL", "AWS", "Microservices"],
        roles=[
            Role("Meridian Bank", "Senior Software Engineer", "2017-04", "Present",
                 "Led a team of five maintaining Spring Boot microservices for loan origination; migrated "
                 "two services from Oracle to PostgreSQL on AWS.",
                 ["Java", "Spring Boot", "PostgreSQL", "AWS"]),
            Role("Insurely", "Software Engineer", "2015-01", "2017-03",
                 "Built Java services for policy pricing.", ["Java", "Oracle"]),
        ],
        education=("Rutgers University", "B.S.", "Computer Science"),
        category_scores=[
            (52, "Extensive backend experience, but in Java rather than Python."),
            (80, "Owns a microservice architecture for a regulated domain."),
            (74, "Migrated services from Oracle to PostgreSQL on AWS."),
            (82, "Leads a team of five engineers."),
        ],
        strengths=[Finding("Senior architecture and leadership experience",
                           "Led a team of five maintaining Spring Boot microservices.")],
        gaps=[Finding("No Python or FastAPI experience", "All listed backend work uses Java and Spring Boot.")],
        status_path=[S.AI_REVIEWED, S.HUMAN_REVIEW, S.REJECTED],
        days_ago=10,
        notes=["Great engineer but the role needs day-one Python. Keep in mind for future Java roles."],
    ),
    DemoCandidate(
        name="Hana Sato",
        email="hana.sato@example.com",
        phone="+1 415 555 0120",
        handle="hanasato",
        job_key="backend",
        headline="Backend engineer building FastAPI services for developer tools.",
        years=5,
        skills=["Python", "FastAPI", "PostgreSQL", "Docker", "GitHub Actions"],
        roles=[
            Role("Relay CI", "Backend Engineer", "2021-05", "Present",
                 "Built FastAPI services that schedule 50k CI jobs per day; owned PostgreSQL migrations "
                 "and on-call for the scheduling service.",
                 ["Python", "FastAPI", "PostgreSQL", "Docker"]),
            Role("Openfolio", "Software Engineer", "2019-06", "2021-04",
                 "Developed Python data pipelines and REST APIs.", ["Python", "PostgreSQL"]),
        ],
        education=("University of Toronto", "B.A.Sc.", "Engineering Science"),
        status_path=[],  # Waiting for AI screening: use "Screen applicants" in the demo.
        days_ago=1,
    ),
    DemoCandidate(
        name="Ravi Patel",
        email="ravi.patel@example.com",
        phone="+1 415 555 0121",
        handle="ravipatel",
        job_key="backend",
        headline="Data engineer transitioning into backend API development.",
        years=4,
        skills=["Python", "Airflow", "PostgreSQL", "AWS", "Flask"],
        roles=[
            Role("Northwind Analytics", "Data Engineer", "2020-08", "Present",
                 "Built Airflow pipelines on AWS and small Flask APIs that expose curated datasets.",
                 ["Python", "Airflow", "PostgreSQL", "AWS", "Flask"]),
        ],
        education=("Purdue University", "B.S.", "Statistics"),
        status_path=[],
        days_ago=0,
    ),
    # --- Product Designer --------------------------------------------------------------------
    DemoCandidate(
        name="Lina Chen",
        email="lina.chen@example.com",
        phone="+1 415 555 0116",
        handle="linachen",
        job_key="design",
        headline="Senior product designer for collaborative B2B tools and design systems.",
        years=6,
        skills=["Figma", "User research", "Interaction design", "Design systems", "Prototyping"],
        roles=[
            Role("Teamboard", "Senior Product Designer", "2020-02", "Present",
                 "Led design for real-time whiteboard collaboration used by 40k teams; created the Atlas "
                 "design system adopted by 6 product squads; ran 30+ customer interviews per quarter.",
                 ["Figma", "Design systems", "User research"]),
            Role("Helio Studio", "Product Designer", "2018-01", "2020-01",
                 "Designed onboarding and billing flows for SaaS clients.", ["Figma", "Prototyping"]),
        ],
        education=("Rhode Island School of Design", "BFA", "Graphic Design"),
        category_scores=[
            (92, "Led design for a real-time collaboration product used by 40k teams."),
            (86, "Runs more than thirty customer interviews per quarter."),
            (94, "Created a design system adopted by six product squads."),
            (80, "Partnered with multiple product squads on adoption."),
        ],
        strengths=[
            Finding("Design system leadership", "Created the Atlas design system adopted by 6 product squads."),
            Finding("Directly relevant B2B collaboration work",
                    "Led design for real-time whiteboard collaboration used by 40k teams."),
        ],
        gaps=[Finding("Little detail on quantitative research",
                      "Research is described as customer interviews only.")],
        status_path=[S.AI_REVIEWED, S.HUMAN_REVIEW, S.SHORTLISTED, S.CONTACTED],
        days_ago=8,
        notes=["Portfolio is outstanding. Reached out to schedule a portfolio review."],
        outreach=(
            "Northstar Labs - Product Designer conversation",
            "Hi Lina,\n\nThank you for applying for the Product Designer role at Northstar Labs. Your work "
            "leading the Atlas design system at Teamboard stood out to our team, especially its adoption "
            "across six product squads.\n\nWould you be open to a 45-minute portfolio review next week? "
            "Reply with a few times that work for you.\n\nBest,\nDemo Recruiter\nNorthstar Labs",
        ),
    ),
    DemoCandidate(
        name="Omar Hassan",
        email="omar.hassan@example.com",
        phone="+1 415 555 0117",
        handle="omarhassan",
        job_key="design",
        headline="Product designer with a research-first approach.",
        years=4,
        skills=["Figma", "User research", "Interaction design", "Usability testing"],
        roles=[
            Role("Carely", "Product Designer", "2021-01", "Present",
                 "Redesigned appointment booking after 20 usability sessions, increasing completion by 18%.",
                 ["Figma", "User research"]),
            Role("Freelance", "UX Designer", "2020-01", "2020-12",
                 "Designed mobile apps for early-stage startups.", ["Figma"]),
        ],
        education=("Carnegie Mellon University", "M.HCI", "Human-Computer Interaction"),
        category_scores=[
            (74, "Shipped a booking redesign with a measured completion increase."),
            (88, "Ran 20 usability sessions and holds an HCI master's degree."),
            (52, "No design system work is described."),
            (70, "Collaboration is implied through shipped product work."),
        ],
        confidence=EvaluationConfidence.MEDIUM,
        strengths=[Finding("Research-driven results",
                           "Redesigned booking after 20 usability sessions, increasing completion by 18%.")],
        gaps=[Finding("No design system experience", "The resume does not mention component libraries or systems.")],
        status_path=[S.AI_REVIEWED, S.HUMAN_REVIEW, S.SHORTLISTED],
        days_ago=5,
    ),
    DemoCandidate(
        name="Grace Okafor",
        email="grace.okafor@example.com",
        phone="+1 415 555 0118",
        handle="graceokafor",
        job_key="design",
        headline="Visual designer expanding into product design.",
        years=2,
        skills=["Figma", "Illustration", "Branding", "Prototyping"],
        roles=[
            Role("Brightside Creative", "Visual Designer", "2022-06", "Present",
                 "Created brand identities and marketing sites; prototyped a mobile ordering flow.",
                 ["Figma", "Prototyping"]),
        ],
        education=("Savannah College of Art and Design", "BFA", "Illustration"),
        category_scores=[
            (60, "Strong visual work, with one product prototype."),
            (40, "No user research is described."),
            (55, "Brand systems are adjacent to product design systems."),
            (62, "Client-facing agency work."),
        ],
        confidence=EvaluationConfidence.MEDIUM,
        strengths=[Finding("Strong visual craft", "Created brand identities and marketing sites.")],
        gaps=[
            Finding("Limited product design experience", "Only one product prototype is described."),
            Finding("Below the experience requirement", "Resume shows about two years of experience."),
        ],
        status_path=[S.AI_REVIEWED],
        days_ago=3,
    ),
    # --- Data Analyst ------------------------------------------------------------------------
    DemoCandidate(
        name="Priya Nair",
        email="priya.nair@example.com",
        phone="+1 415 555 0114",
        handle="priyanair",
        job_key="data",
        headline="Analytics lead for SaaS product and revenue metrics.",
        years=5,
        skills=["SQL", "dbt", "Looker", "Python", "Statistics", "Data visualization"],
        roles=[
            Role("Pipeflow", "Senior Data Analyst", "2021-04", "Present",
                 "Built the company's dbt project (180 models) and Looker dashboards used weekly by "
                 "leadership; designed the A/B testing framework for pricing experiments.",
                 ["SQL", "dbt", "Looker", "Python"]),
            Role("Shopwise", "Data Analyst", "2019-07", "2021-03",
                 "Analyzed retention cohorts and built SQL reporting for marketing.", ["SQL", "Tableau"]),
        ],
        education=("University of Michigan", "B.S.", "Statistics"),
        category_scores=[
            (93, "Built and maintains a 180-model dbt project."),
            (88, "Designed the A/B testing framework for pricing experiments."),
            (86, "Looker dashboards used weekly by leadership."),
            (84, "Partners directly with leadership on pricing decisions."),
        ],
        strengths=[
            Finding("Owns a production analytics stack", "Built the company's dbt project (180 models)."),
            Finding("Experimentation expertise", "Designed the A/B testing framework for pricing experiments."),
        ],
        gaps=[],
        status_path=[S.AI_REVIEWED, S.HUMAN_REVIEW, S.SHORTLISTED, S.INTERVIEW, S.OFFER, S.HIRED],
        days_ago=20,
        notes=["Accepted the offer! Start date is the first Monday of next month."],
    ),
    DemoCandidate(
        name="Lucas Silva",
        email="lucas.silva@example.com",
        phone="+1 415 555 0119",
        handle="lucassilva",
        job_key="data",
        headline="Business analyst building SQL reporting for operations teams.",
        years=3,
        skills=["SQL", "Excel", "Tableau", "Data visualization"],
        roles=[
            Role("Greenline Foods", "Business Analyst", "2021-10", "Present",
                 "Built Tableau dashboards for supply-chain KPIs and automated weekly SQL reports.",
                 ["SQL", "Tableau", "Excel"]),
        ],
        education=("Arizona State University", "B.S.", "Supply Chain Management"),
        category_scores=[
            (72, "Writes SQL reports regularly; no modeling-layer experience."),
            (55, "No statistics or experimentation work is described."),
            (80, "Builds Tableau dashboards for operational KPIs."),
            (74, "Supports operations stakeholders weekly."),
        ],
        confidence=EvaluationConfidence.MEDIUM,
        strengths=[Finding("Effective dashboarding", "Built Tableau dashboards for supply-chain KPIs.")],
        gaps=[Finding("Limited statistics evidence", "No experimentation or statistical analysis is described.")],
        status_path=[S.AI_REVIEWED, S.HUMAN_REVIEW],
        days_ago=2,
    ),
]
