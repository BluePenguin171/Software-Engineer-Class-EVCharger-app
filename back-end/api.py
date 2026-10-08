from fastapi import FastAPI,Depends, Request,UploadFile
from fastapi.responses import JSONResponse,Response
from datetime import datetime,timedelta 
from backend import filter_items,MAXRESERVEDTIME,update_point,db_init,get_changes_between_dates,total_online_points,add_session,reserved_garbage_collector,group_point_list_by_point_position,csv_to_points,_csv_response,get_all_points_between_bounds
from database import session,host,port,DBNAME
from sqlalchemy.orm import Session
import database_models
from models import ChargePoints,ChargingSessionHistory,StatusHistory,ErrorLog,UpdatePoint,Reservation
from sqlalchemy.exc import OperationalError,SQLAlchemyError,IntegrityError
from enum import Enum 
from fastapi.exceptions import RequestValidationError,HTTPException
from apscheduler.schedulers.background import BackgroundScheduler # type: ignore
from contextlib import asynccontextmanager
import csv 
import io 
from fastapi.middleware.cors import CORSMiddleware

def get_db():
    #creates a new database session, and then close it 
    db = session()
    try: 
        yield db
    finally:
        db.close()

class Error(Enum):
    #Enumerator for error codes 
    DB_CONNECTION = 1
    UNIDENTIFIED = 2
    STATUS = 3 
    POINT_NOT_FOUND = 4
    INVALID_DATE = 5
    UPDATE_FIELDS = 6
    WRONG_FIELD=7
    CSV_FILE = 8
    ENDPOINT_NOT_EXISTS = 9


def error_log_response(request : Request, error : Error,details : str = ""):
    #returns an ErrorLog Model Object
    if error == Error.DB_CONNECTION: 
        return ErrorLog(
                        call = str(request.url),
                        originator = request.client.host, 
                        error = "Bad request",
                        debuginfo = "Something went wrong with the database connection"
                        )
    elif error == Error.UNIDENTIFIED: 
        return ErrorLog(
                            call = str(request.url),
                            originator = request.client.host, 
                            error = "Internal Server Error",
                            debuginfo = "Something went wrong with the SQLAlchemy."
                        )
    elif error == Error.STATUS: 
        return ErrorLog(
                            call = str(request.url),
                            originator = request.client.host, 
                            error = "Unauthorized",
                            debuginfo = "Status should only be available, charging, reserved, malfunction or offline"
                        )
    elif error == Error.POINT_NOT_FOUND:
         return ErrorLog(
                            call = str(request.url),
                            originator = request.client.host, 
                            error = "Bad request",
                            debuginfo = "Point with the provided id does not exist!"
                        )
    elif error == Error.INVALID_DATE:
        return ErrorLog(
                            call = str(request.url),
                            originator = request.client.host, 
                            error = "Bad request",
                            debuginfo = "Provided Date should be in YYYYMMDD format"
                        )
    elif error == Error.UPDATE_FIELDS: 
        return ErrorLog(
                            call = str(request.url),
                            originator = request.client.host, 
                            error = "Bad request",
                            debuginfo = "You should provide status and/or kwhprice. Nothing more, Nothing less."
                        )
    elif error == Error.WRONG_FIELD: 
        return ErrorLog(
                            call = str(request.url),
                            originator = request.client.host, 
                            error = "Unprocessable Entity",
                            debuginfo =  details
        )
    elif error == Error.CSV_FILE:
        return ErrorLog(
                            call = str(request.url),
                            originator = request.client.host, 
                            error = "Bad request",
                            debuginfo =  "Uploaded File should be CSV (text/csv)"
        )
    elif error == Error.ENDPOINT_NOT_EXISTS: 
        return ErrorLog(
                            call = str(request.url),
                            originator = request.client.host, 
                            error = "Bad request",
                            debuginfo =  "Endpoint does not exists"
        )


def http_response(status = 200, body = {},csvflag = False): 
    '''
    Docstring for http_response
    
    :param status : int | None 
    :param body: dict | list[dict] | ErrorLog

    returns JSONResponse with the correct status code 
    if status is >= 400, body should be ErrorLog Object
    '''


    if(status >= 400): 
        if not isinstance(body,ErrorLog): 
            return JSONResponse(status_code= 200,content= {"message" : "You did nothing wrong, the programmer just forgot his own rules"})
        body.timeref = datetime.now()
        body.return_code = status 
        my_content = body.model_dump()
    else: 
        my_content = body 
    
    if(my_content is not None and (my_content == [] or my_content == {})): #return 204 code with empty body
        return  Response(status_code= 204) 

    if(csvflag):    #return csv file 
        output = _csv_response(my_content)
        return Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={
                "Content-Disposition": "attachment; filename=response.csv"
            },
        )
    
    return JSONResponse(status_code = status, content = my_content)     #return json file



#-------------------------Scheduler-------------------------
def scheduled_release():
    """Wrapper function that safely creates its own DB session."""
    db = session()
    try:
        reserved_garbage_collector(db)
    finally:
        db.close()


scheduler = BackgroundScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup phase
    scheduler.add_job(scheduled_release, "interval", minutes = 1)
    scheduler.start()
    print("Scheduler started")

    yield  # Run the app

    # shutdown phase
    scheduler.shutdown()
    print("Scheduler stopped")


app = FastAPI(lifespan=lifespan)

#TODO : Update this
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


#-------------------------Handlers-------------------------
@app.exception_handler(OperationalError)
async def operational_error_handler(request: Request, exc: OperationalError):
    return http_response(status = 400, body = error_log_response(request,Error.DB_CONNECTION)) 

@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc : IntegrityError):
    return http_response(status = 422, body = error_log_response(request,Error.WRONG_FIELD,details = str(exc.orig))) 
    

@app.exception_handler(SQLAlchemyError)
async def generic_error_handler(request: Request, exc: OperationalError):
    return http_response(status = 500, body = error_log_response(request,Error.UNIDENTIFIED))


@app.exception_handler(RequestValidationError)           
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    error_list = exc.errors()
    if(error_list[0]['type'] == 'json_invalid'):
        return http_response(status = 422, body = error_log_response(request,Error.UPDATE_FIELDS)) #get error details
    elif(error_list[0]['type'] == 'value_error'):
        return http_response(status = 422, body = error_log_response(request,Error.WRONG_FIELD,details = error_list[0]['msg']))
    print(error_list)
    info = "debugging"
    info = error_list[0]['loc'][1] +  error_list[0]['msg'][5:] #replace the word Input with the correct attribute name 
    return http_response(status = 422, body = error_log_response(request,Error.WRONG_FIELD,details = info)) #get error details


#testing
@app.exception_handler(404)
async def custom_404_handler(request: Request, exc: HTTPException):
    return http_response(status = 404, body = error_log_response(request,Error.ENDPOINT_NOT_EXISTS))

#-------------------------Admin-Endpoints-------------------------
@app.get("/admin/healthcheck")
def healthcheck(request: Request, db : Session = Depends(get_db)):    
    total_points = filter_items(db,database_models.ChargePoints, count = True)
    online_points = total_online_points(db)         #query returning all the points with status available or reserved
    offline_points = total_points - online_points 
                            
    body = {
        "status" : "OK",
        "dbconnection": f"postgresql://{host}:{port}/{DBNAME}",
        "n_charge_points": total_points,
        "n_charge_points_online": online_points,
        "n_charge_points_offline": offline_points
    }

    return http_response(status = 200, body = body)


@app.post("/admin/resetpoints")
def reset_db(request : Request, db : Session = Depends(get_db)):
    db_init(db)
    return http_response(status = 200, body = None)

@app.get("/admin/reservations")
def get_reservations(request : Request, db : Session = Depends(get_db)):
    all_points = filter_items(db,database_models.Reservations)

    points_list = [ Reservation.model_validate(item.__dict__).model_dump() for item in all_points] 

    return http_response(body = points_list) 

@app.post("/admin/addpoints")
async def add_points(request: Request, file : UploadFile, db : Session = Depends(get_db)):
    
    if file.content_type != "text/csv":
        return http_response(status = 400, body = error_log_response(request,Error.CSV_FILE))
    
    #read csv file
    content = await file.read()
    csv_text = content.decode("utf-8")
    csv_reader = csv.DictReader(io.StringIO(csv_text))

    #TODO : Maybe is not what he wants
    csv_to_points(db,csv_reader)

    return http_response(status = 200, body = None)











        
#-------------------------Global-Endpoints-------------------------
@app.get("/points") 
def get_points(request : Request, status : str | None = None,  format : str | None = None, db : Session = Depends(get_db)):
    if status is not None and status not in ["available", "charging", "reserved", "malfunction", "offline" ]:
        return http_response(status = 401, body = error_log_response(request,Error.STATUS))
    
    all_points = filter_items(db,database_models.ChargePoints,status=status)

    points_list = [ ChargePoints.model_validate(item.__dict__).data_dict(exclude={"reservation_endtime","kwhprice"}) for item in all_points] 

    return http_response(body = points_list, csvflag = format == "csv") 


@app.get("/point/{pid}")
def get_point(request : Request,pid : int , db : Session = Depends(get_db)):
    p = filter_items(db,database_models.ChargePoints,first = True, pointid=pid) #get point based on id
    if (p is None): 
        return http_response(status = 400, body = error_log_response(request,Error.POINT_NOT_FOUND))
    
    if p.reservation_endtime is None :
        p.reservation_endtime = datetime.now() 
    
    return http_response(body = ChargePoints.model_validate(p.__dict__).data_dict())



def reserve_point(request : Request,pid : int, min : int, db: Session):
    p = filter_items(db,database_models.ChargePoints,first = True, pointid=pid) #get point based on id
    if (p is None) :
        return http_response(status = 400, body = error_log_response(request,Error.POINT_NOT_FOUND))
    
    if(p.status == "available"):            #update  
        min = MAXRESERVEDTIME if min > MAXRESERVEDTIME else min  
        endtime = datetime.now() + timedelta(minutes = min)
        stat = "reserved"
        update_point(db ,p, reservation_endtime = endtime, status = stat)
    else:
        endtime = datetime.strptime("1970-01-01 00:00", "%Y-%m-%d %H:%M")     #it is what it is 
        stat = p.status
    
    return http_response(status = 200, body =   {
                                                    "pointid" : p.pointid,
                                                    "status"  : stat, 
                                                    "reservationendtime" : endtime.strftime("%Y-%m-%d %H:%M")
                                                })


@app.post("/reserve/{pid}/{min}")
def reserve_point_with_min(request : Request,pid : int, min : int,db : Session = Depends(get_db)):
    return reserve_point(request,pid,min,db)


@app.post("/reserve/{pid}") 
def reserve_point_no_min(request : Request,pid : int,db : Session = Depends(get_db)):
    return reserve_point(request,pid,30,db)


@app.post("/updpoint/{pid}")
def update_the_point(request : Request,pid : int, update_data : UpdatePoint, db : Session = Depends(get_db)):
    if update_data.status is None and update_data.kwhprice is None:  #one of two should have something
        return http_response(status = 400, body = error_log_response(request,Error.UPDATE_FIELDS))
    
    p = filter_items(db,database_models.ChargePoints,first = True, pointid=pid) #get point based on id
    if (p is None): 
        return http_response(status = 400, body = error_log_response(request,Error.POINT_NOT_FOUND))
    
    update_point(db ,p, status = update_data.status, kwhprice = update_data.kwhprice)


    return http_response(status = 200, body =   {
                                                    "pointid" : p.pointid,
                                                    "status"  : p.status, 
                                                    "kwhprice": p.kwhprice
                                                })


    
@app.post("/newsession")
def upload_a_session(request : Request, session_data : ChargingSessionHistory, db : Session = Depends(get_db)):
    p = filter_items(db,database_models.ChargePoints,first = True, pointid=session_data.pointid) #get point based on id
    if (p is None): 
        return http_response(status = 400, body = error_log_response(request,Error.POINT_NOT_FOUND))
    add_session(db,session_data) 
    return http_response(status = 200, body = None)


@app.get("/sessions/{pid}/{from}/{to}")
def get_sessions(request : Request, pid : int, fr0m : str, to : str, format : str | None = None, db : Session = Depends(get_db)):
    p = filter_items(db,database_models.ChargePoints,first = True, pointid=pid) #get point based on id
    if (p is None) :
        return http_response(status = 400, body = error_log_response(request,Error.POINT_NOT_FOUND))
    
    #check for invalid date 
    try: 
        from_date = datetime.strptime(fr0m, "%Y%m%d")
        to_date = datetime.strptime(to,"%Y%m%d")
    except ValueError: 
        return http_response(status = 400, body = error_log_response(request,Error.INVALID_DATE))
    
    changes = get_changes_between_dates(db,database_models.ChargingSessionHistory,pid,from_date,to_date)

    changes_dict = [ChargingSessionHistory.model_validate(item.__dict__).model_dump(exclude={"pointid"}) for item in changes]

    return http_response(body = changes_dict,csvflag = format == "csv")


@app.get("/pointstatus/{pid}/{from}/{to}")
def get_pointstatus(request : Request, pid : int, fr0m : str, to : str, format : str | None = None, db : Session = Depends(get_db)):
    p = filter_items(db,database_models.ChargePoints,first = True, pointid=pid) #get point based on id
    if (p is None) :
        return http_response(status = 400, body = error_log_response(request,Error.POINT_NOT_FOUND))
    
    #check for invalid date 
    try: 
        from_date = datetime.strptime(fr0m, "%Y%m%d")
        to_date = datetime.strptime(to,"%Y%m%d")
    except ValueError: 
        return http_response(status = 400, body = error_log_response(request,Error.INVALID_DATE))
    
    changes = get_changes_between_dates(db,database_models.StatusHistory,pid,from_date,to_date)

    changes_dict = [StatusHistory.model_validate(item.__dict__).model_dump() for item in changes]

    return http_response(body = changes_dict, csvflag = format == csv)


#-------------------------FrontEnd-Endpoints-------------------------

@app.get("/frontend/points/bounded")
def get_bounded_points(request : Request, north : float, south : float, west: float, east: float, db : Session = Depends(get_db)):
    bounds = [south,north,east,west]
    all_points = get_all_points_between_bounds(db,bounds)
    
    
    points_list = [ ChargePoints.model_validate(item.__dict__).data_dict(exclude={"reservation_endtime","kwhprice"}) for item in all_points] 
    
    #group points by (lat,lon) for front-end purposes
    return http_response(body = group_point_list_by_point_position(points_list), csvflag = False) 

@app.post("/frontend/cancel/{pid}")
def get_bounded_points(request : Request, pid : int, db : Session = Depends(get_db)):
    p = filter_items(db,database_models.ChargePoints,first = True, pointid=pid) #get point based on id
    if (p is None): 
        return http_response(status = 400, body = error_log_response(request,Error.POINT_NOT_FOUND))
    
    if p.status == "reserved" :
        update_point(db ,p, status = "available")
    
    return http_response(status = 204, body = [])

