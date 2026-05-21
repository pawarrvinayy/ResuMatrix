# from datetime import date
from typing import List
import langchain_openai
from dotenv import load_dotenv
import pandas as pd

from pydantic import BaseModel, Field

class User(BaseModel):
    """Personal information of a candidate"""
    fname: str = Field(description="First name of the user")
    lname: str = Field(description="Last name of the user")

class WorkExp(BaseModel):
    "Work experience of the candidate"
    company: str = Field(description="Name of the company")
    start_date: str
    end_date: str

class JsonData(BaseModel):
    """A resume model"""

    user: User
    work_exp_list: List[WorkExp]


def main():
    load_dotenv()
    llm = langchain_openai.ChatOpenAI(model="gpt-4o", temperature=0)
    json_llm = llm.with_structured_output(JsonData)
    df = pd.read_parquet("hf://datasets/AhmedBou/ParsedResumes/data/train-00000-of-00001.parquet")
    res = json_llm.invoke(df.iloc[0]["Resume"])
    print(type(res))
    print(res.model_dump_json(indent=4))

if __name__ == "__main__":
    main()
