from pydantic.networks import import_email_validator
from sqlalchemy.orm import Session
from .models import Payment, User
from .schemas import PaymentSchema
from .schemas import UserSchema

def get_order(db: Session, id: int):
    return db.query(PaymentSchema).filter(PaymentSchema.id == id)

def get_orders(db: Session, skip: int = 0, limit: int = 100):
    return db.query(PaymentSchema).offset(skip).limit(limit).all()

def create_payment(db: Session, order_in: PaymentSchema):
    create_payment = Payment(**order_in)
    db.add(create_payment)
    db.commit()
    db.refresh(create_payment)
    return create_payment

def get_user(db: Session, username: str):
    for i in db.query(User).filter(User.username == username).order_by(User.id.desc()).limit(1):
        return UserSchema(**i.__dict__)




## this is for crud method