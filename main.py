from fastapi import FastAPI, Request, Depends, BackgroundTasks
from fastapi.templating import Jinja2Templates
from models import Stock, Base
import yfinance

from database import engine, SessionLocal
from sqlalchemy.orm import Session
from pydantic import BaseModel

Base.metadata.create_all(bind=engine)

app = FastAPI()

templates = Jinja2Templates(directory='templates')


def get_db():
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()


class StockRequest(BaseModel):
    symbol: str


@app.get('/')
def dashboard(request: Request, forward_pe=None, dividend_yield=None, ma50=None, ma200=None, db: Session = Depends(get_db)):
    """Displays a homescreen"""
    stocks = db.query(Stock)


    stocks = stocks.all()

    return templates.TemplateResponse('dashboard.html', {
        'request': request,
        'stocks': stocks,
        "dividend_yield": dividend_yield,
        "forward_pe": forward_pe,
        "ma200": ma200,
        "ma50": ma50,
    })


def fetch_stock_data(id: int):
    db = SessionLocal()
    stock = db.query(Stock).filter(Stock.id == id).first()

    yahoo_data = yfinance.Ticker(stock.symbol)

    stock.ma200 = yahoo_data.info['twoHundredDayAverage']
    stock.ma50 = yahoo_data.info['fiftyDayAverage']
    stock.price = yahoo_data.info['previousClose']
    stock.forward_pe = yahoo_data.info['forwardPE']
    stock.forward_eps = yahoo_data.info['forwardEps']
    stock.dividend_yield = yahoo_data.info['dividendYield'] * 100

    db.add(stock)
    db.commit()


@app.post('/stock')
async def create_stock(stock_request: StockRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """
    Created a stocks and stores in a database
    """
    stock = Stock()
    stock.symbol = stock_request.symbol

    db.add(stock)
    db.commit()

    background_tasks.add_task(fetch_stock_data, stock.id)
    return {
        'code': 'success',
        'message': 'stock_created',
    }