import uuid
import os
from datetime import datetime, timedelta
from typing import Optional
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv
from os.path import join, dirname
from linepay import LinePayApi
from starlette.responses import HTMLResponse
from sqlalchemy.orm import Session
from fastapi.encoders import jsonable_encoder
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sql.database import get_db_session
from sql.crud import create_payment, get_user
from sql.models import Payment, User
from sql.schemas import PaymentSchema
from sql.schemas import UserSchema
from jose import JWTError, jwt
from passlib.context import CryptContext


# TBD load_env
SECRET_KEY = "df2f77bd544240801a048bd4293afd8eeb7fff3cb7050e42c791db4b83ebadcd"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 5
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def authenticate_user(db_sesion: Session, username: str, password: str):
    user = get_user(db_sesion, username)
    if not user:
        return False
    if not verify_password(password, user.password):
        return False
    return user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(db_sesion: Session, token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = get_user(db_sesion, username=username)
    if user is None:
        raise credentials_exception
    return user


dotenv_path = join(dirname(__file__),'./env/test.env') ## sandbox
load_dotenv(dotenv_path)
templates = Jinja2Templates(directory="templates")

LINE_PAY_CHANNEL_ID = os.environ.get("LINE_PAY_CHANNEL_ID")
LINE_PAY_CHANNEL_SECRET = os.environ.get("LINE_PAY_CHANNEL_SECRET")
LINE_PAY_REQEST_BASE_URL = "https://{}".format(os.environ.get("HOST_NAME"))
line = LinePayApi(LINE_PAY_CHANNEL_ID, LINE_PAY_CHANNEL_SECRET, is_sandbox=True)

# CACHE
CACHE = {}

# Fastapi
app = FastAPI()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


@app.get('/')
def hello():
    return templates.TemplateResponse("login.html",{"request": {}})


@app.post('/')
def hello(form_data: OAuth2PasswordRequestForm = Depends(), db_sesion: Session = Depends(get_db_session)):
    user = authenticate_user(db_sesion, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    index = {}
    index["product"] = "早鳥方案"
    index["amount"] = 1200
    index["url"] = "/request"
    index["name"] = user.username
    return {"access_token": access_token, "token_type": "bearer"}


@app.post('/request', response_class=HTMLResponse)
async def pay_request(token: str = Depends(oauth2_scheme), db_sesion: Session = Depends(get_db_session)):
    user = get_current_user(db_sesion, token)
    order_id = str(uuid.uuid4())
    amount = 1200
    currency = "TWD"
    CACHE["orderid"] = order_id
    CACHE["amount"] = amount
    CACHE["currency"] = currency
    CACHE["userid"] = user.id
    request_options ={
        "amount" : amount,
        "currency" : currency,
        "orderId" : order_id,
        "packages" : [
            {
                "id" : "早鳥方案",
                "amount" : 1200,
                "products" :[
                    {
                        "name" : "早鳥方案",
                        "quantity" : 1,
                        "price" : 1200,
                        "imageUrl" : "https://kb.rspca.org.au/wp-content/uploads/2018/11/golder-retriever-puppy.jpeg"
                    }
                ]
            }

        ],
        "redirectUrls" : {
            "confirmUrl" : LINE_PAY_REQEST_BASE_URL + "/confirm/",
            "cancelUrl" : LINE_PAY_REQEST_BASE_URL + "/cancel/"
        }
    }
    response = line.request(request_options)
    transaction_id = int(response.get("info",{}).get("transactionId",0))
    check_result = line.check_payment_status(transaction_id)
    response["transaction_id"] = transaction_id
    response["paymentStatusCheckReturnCode"] = check_result.get("returnCode", None)
    response["paymentStatusCheckReturnMessage"] = check_result.get("returnMessage", None)
    response["full_name"] = user.username
    return templates.TemplateResponse("request.html", {"request":response})


@app.get('/confirm/')
async def pay_confirm(transactionId: int, orderId: Optional[str] = None, db_sesion: Session = Depends(get_db_session)):
    CACHE["transaction_id"] = transactionId
    response = line.confirm(transactionId,float(CACHE.get("amount",0)),CACHE.get("currency","TWD"))
    check_result = line.check_payment_status(transactionId)
    payment_details = line.payment_details(transaction_id=transactionId)
    response["transaction_id"] = transactionId
    response["paymentStatusCheckReturnCode"] = check_result.get("returnCode", None)
    response["paymentStatusCheckReturnMessage"] = check_result.get("returnMessage",None)
    response["payment_details"] = payment_details
    if(response["paymentStatusCheckReturnCode"] == '0123'):
        orderin = {}
        orderin["OrderId"] = CACHE["orderid"]
        orderin["UserId"] = CACHE["userid"]
        orderin["TransactionId"] = CACHE["transaction_id"]
        orderin["Source"] = "linepay"
        orderin["UpdateTime"] = datetime.now()
        create_payment(db_sesion, order_in= orderin)
    return templates.TemplateResponse("confirm.html", {"request":response})


@app.get('/payments')
async def pay_payments(orderId : str):
    payment_details = line.payment_details(order_id=orderId)
    return payment_details
