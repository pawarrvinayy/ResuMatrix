from typing import List, Optional
from pydantic import BaseModel, Field


class Location(BaseModel):
    """Represents a physical location."""
    address: Optional[str] = None
    postal_code: Optional[str] = Field(None, alias='postalCode')
    city: Optional[str] = None
    country_code: Optional[str] = Field(None, alias='countryCode')



class Language(BaseModel):
    """Represents proficiency in a language."""
    language: str
    fluency: Optional[str] = None  # e.g., "Native speaker", "Fluent", "Conversational"



class BasicInformation(BaseModel):
    """Basic contact and personal information."""
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    summary: Optional[str] = None
    location: Optional[Location] = None
    twitter: Optional[str] = None
    github: Optional[str] = None
    linkedin: Optional[str] = None
    languages: Optional[List[Language]] = None



class WorkExperience(BaseModel):
    """Represents a single job position."""
    company_name: str = Field(..., alias='companyName')
    position: str
    start_date: Optional[str] = Field(None, alias='startDate')
    end_date: Optional[str] = Field(None, alias='endDate')
    summary: Optional[List[str]] = None  # What the applicant has worked on
    skills: Optional[List[str]] = None


class Award(BaseModel):
    """Represents a single award received."""

    title: str
    date_received: Optional[str] = Field(..., alias='dateReceived')
    awarder: Optional[str] = None  # Organization/person who gave the award
    summary: Optional[str] = None


class Certificate(BaseModel):
    """Represents a single certification."""
    certificate_name: str = Field(..., alias='certificateName')
    date_issued: Optional[str] = Field(..., alias='dateIssued')
    issuer: str  # Organization that issued the certificate
    certificate_url: Optional[str] = Field(None, alias='certificateUrl')



class Publication(BaseModel):
    """Represents a single publication."""

    publication_name: str = Field(..., alias='publicationName')
    publisher_name: Optional[str] = Field(None, alias='publisherName')
    release_date: Optional[str] = Field(None, alias='releaseDate')
    publication_url: Optional[str] = Field(None, alias='publicationUrl')
    summary: Optional[str] = None



class Project(BaseModel):

    """Represents a personal or professional project."""
    project_name: str = Field(..., alias='projectName')
    start_date: Optional[str] = Field(None, alias='startDate')
    end_date: Optional[str] = Field(None, alias='endDate')
    highlights: Optional[List[str]] = None  # Added for common bullet points
    project_url: Optional[str] = Field(None, alias='projectUrl')
    keywords: Optional[List[str]] = None  # Added for technologies used, etc.


class Resume(BaseModel):
    """Pydantic model representing a resume."""
    basics: BasicInformation
    workexp: Optional[List[WorkExperience]] = None
    education: Optional[List[str]] = None
    awards: Optional[List[Award]] = None
    certificates: Optional[List[Certificate]] = None
    publications: Optional[List[Publication]] = None
    skills: Optional[List[str]] = None

    personal_projects: Optional[List[Project]] = None

    class Config:
        str_strip_whitespace = True

        validate_by_name = True  # Allows using snake_case or camelCase

