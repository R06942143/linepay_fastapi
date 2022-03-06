from typing import Optional

from pydantic import BaseModel, EmailStr
from datetime import datetime

from sqlalchemy.sql.expression import text


class UserSchema(BaseModel):
    """[summary]

    Args:
        BaseModel ([type]): [description]
    """
    id: int
    email: EmailStr
    username: str
    password: str
    token: Optional[str] = None
    left_time: Optional[int] = None
    last_stored: Optional[datetime] = None
    line_token: Optional[str] = None
    veri_url: Optional[str] = None
    class Config:
        orm_mode = True



class PaymentSchema(BaseModel):
    """[summary]

    Args:
        BaseModel ([type]): [description]
    """
    id: int
    userid: int
    orderid: Optional[str] = None
    TaransactionId: Optional[str] = None
    Source: str
    CreateTime: Optional[datetime] = None
    UpdateTime: datetime = datetime.now()
    ## this is to avoid lazy loading problem
    class Config:
        orm_mode = True

## this is for data parsing&&&data validation