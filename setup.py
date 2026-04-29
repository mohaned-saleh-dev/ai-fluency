"""
Setup script for PRD and Ticket Writing Agent.
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [
        line.strip() 
        for line in fh 
        if line.strip() and not line.startswith("#")
    ]

setup(
    name="prd-ticket-agent",
    version="0.1.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="An intelligent agent for creating PRDs and Jira tickets using Gemini AI",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/prd-ticket-agent",
    packages=find_packages(exclude=["tests", "*.tests", "*.tests.*", "tests.*"]),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Documentation",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "prd-agent=prd_ticket_agent.cli:main",
            "prd-ticket-agent=prd_ticket_agent.cli:main",
        ],
    },
    keywords="prd jira ticket notion gemini ai documentation",
    project_urls={
        "Bug Reports": "https://github.com/yourusername/prd-ticket-agent/issues",
        "Source": "https://github.com/yourusername/prd-ticket-agent",
    },
)



