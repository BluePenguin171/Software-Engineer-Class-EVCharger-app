from typing import Any
from database import session,engine
import database_models
from sqlalchemy.orm import Session
from sqlalchemy import  and_,or_
from models import ChargePoints,ChargingSessionHistory,StatusHistory,Reservation
from datetime import datetime
import ijson  # type: ignore
import random 
from csv import DictReader,DictWriter
import io
from collections import defaultdict
from datetime import timedelta
MAXRESERVEDTIME = 60



#------------Database-----------
def db_init(db: Session):
    '''
    Initiallize DB 
    We consider that every outlet is a charging point 
    '''

    database_models.Base.metadata.create_all(bind = engine)
    
    #empty db
    db.query(database_models.ChargingSessionHistory).delete()
    db.query(database_models.StatusHistory).delete()
    db.query(database_models.Reservations).delete()
    db.query(database_models.ChargePoints).delete()
    
    #repopulate
    with open("./sample_data/parts1234.json", "r", encoding="utf-8") as f:
        for item in ijson.items(f, "item"):         #using ijson instead of json for an Iterative JSON parser 
            fields = {                              #get location
                "lat" : float(item["latitude"]),
                "lon" : float(item["longitude"])
            }
            stations = item["stations"]
            for s in stations: 
                outlets = s["outlets"]
                for o in outlets: 
                    fields['pointid'] = o['id']         #get outlet id 
                    fields['cap'] = random.randint(1,300) if o["kilowatts"] is None else int(o["kilowatts"]) #get cap 
                    st = o['status'] 
                    if(st is None or st.lower == "unknown"):        #get status 
                        fields['status'] = 'offline'
                    elif (st.lower() in ["outoforder","under_repair"]): 
                        fields['status'] = "malfunction"
                    elif (st.lower() == "available"):
                        fields['status'] = "available"

                    fields["kwhprice"] = random.random()  # get a random price

                    new_charging_point = ChargePoints.model_validate(fields) #convert dictionary to model 

                    db.add(database_models.ChargePoints(**new_charging_point.model_dump(context={"turn_off_flag": True}))) #turn off seriallizers 
    db.commit()
    print("Database Initiallized")

            



def reserved_garbage_collector(db : Session): 
    current_time = datetime.now()
    points_to_be_released = db.query(database_models.Reservations).filter(current_time > database_models.Reservations.endtime)
    for p in points_to_be_released: 
        p.charge_point.status = "available"  #update point 
        p.charge_point.reservation_endtime = None 

        st_item = status_history_item(item = p, oldstatus= "reserved", newstatus= "available")  #update the StatusHistory Table
        db.add(database_models.StatusHistory(**st_item.model_dump(context={"turn_off_flag": True})))
        
        print(f"point with id {p.pointid} changed status to available.")
        db.delete(p)

        
    db.commit()



def csv_to_points(db : Session, file : DictReader):
    for row in file: 
        print(row)
        p = ChargePoints.model_validate(row)
        db.add(database_models.ChargePoints(**p.model_dump(context={"turn_off_flag": True})))
    db.commit() 

def _csv_response(body):
    output = io.StringIO()
    writer = None

    if isinstance(body, list):
        writer = DictWriter(output, fieldnames=body[0].keys())
        writer.writeheader()
        writer.writerows(body)

    elif isinstance(body, dict):
        writer = DictWriter(output, fieldnames=body.keys())
        writer.writeheader()
        writer.writerow(body)

    else:
        raise ValueError("CSV output requires dict or list of dicts")

    return output
#-----------Queries-------------
def filter_items(db: Session, model,first = False,count = False, **filters) -> list[Any]:
    """
    Generic filter function.

    Args:
        db: Database session
        model: SQLAlchemy model class to query
        first: returns only the first item found (optional)
        count: returns the total count of all items  (optional)
        **filters: key=value pairs corresponding to model attributes (optional)

    Returns:
        list[Any]: List of matching records
    """
    query = db.query(model)

    # Only keep filters where value is not None
    conditions = []
    for attr, value in filters.items():
        if value is not None and hasattr(model, attr):
            conditions.append(getattr(model, attr) == value)

    if conditions:
        query = query.filter(and_(*conditions))

    if first: 
        return query.first()
    if count: 
        return query.count()
    
    return  query.all()         



def update_point(db: Session, item,  **keyvalues) -> bool:
    '''
    item : the point you wish to change (from SQL query)
    keyvalues : the pair key=value you wish to change. if
    value is None or key is not a point attribute 
    then this pair will be ignored

    usage example : update_point(db,p,status="available",lat=23.3)
    '''
    add_reservation_flag = False  
    for attr, value in keyvalues.items():
        if value is not None and hasattr(database_models.ChargePoints, attr):
            if(attr == "status" and item.status != value):
                #log a status change history 
                st_item = status_history_item(item = item, oldstatus= item.status, newstatus= value)
                db.add(database_models.StatusHistory(**st_item.model_dump(context={"turn_off_flag": True})))
                
                if(item.status == "reserved"): #delete point from Reservation Table
                    p = (
                        db.query(database_models.Reservations)
                        .filter(database_models.Reservations.pointid == item.pointid)
                        .first()
                    )

                    if p is not None:
                        db.delete(p)
                    setattr(item, "reservation_endtime", None)
                if(value == "reserved"): 
                    add_reservation_flag = True
            setattr(item, attr, value)
    
    if(add_reservation_flag): #if status has changed to reserved, add the item to Reserved Table
        if(datetime.now() >= item.reservation_endtime):
            raise ValueError('The reservation endtime should be in the future, not in the past')
        reservation_item = Reservation(pointid = item.pointid, endtime = item.reservation_endtime)
        db.add(database_models.Reservations(**reservation_item.model_dump(context={"turn_off_flag": True})))
    
    db.commit()

def status_history_item(item, oldstatus, newstatus):
    #creates a new status history entry
    #commit on db from the function that called this 
    return StatusHistory(pointid = item.pointid, timeref = datetime.now(),  old_state = oldstatus, new_state = newstatus)


def get_changes_between_dates(db : Session, model , pid : int ,from_date : datetime,to_date : datetime):
    try:                                    #i was tired, please dont look at this 
        query = db.query(model).filter(
            model.pointid == pid,
            model.timeref > from_date, 
            model.timeref < to_date + timedelta(days = 1)
        )
    except AttributeError:        
        query = db.query(model).filter(
            model.pointid == pid,
            model.starttime > from_date, 
            model.endtime < to_date + timedelta(days = 1) 
        )
    return query.all()

def get_all_points_between_bounds(db: Session, bounds : list[float]):
    south, north, east, west = bounds 
    model = database_models.ChargePoints 
    query = db.query(model).filter(
        model.lat > south,
        model.lat < north,
        model.lon > west,
        model.lon < east
    )
    return query.all()


def total_online_points(db : Session):
    query = db.query(database_models.ChargePoints).filter(
        or_(   
            database_models.ChargePoints.status == "available",
            database_models.ChargePoints.status == "reserved",
            database_models.ChargePoints.status == "charging"
        )
    )

    return query.count() 


def add_session(db : Session, data : ChargingSessionHistory):
    #TODO : fetch the latest CharginSessionHistory for the current point and check the endtime. The data.starttime should be bigger or equal
    db.add(database_models.ChargingSessionHistory(**data.model_dump()))
    db.commit()


def group_point_list_by_point_position(points : list[ChargePoints]):
    groups = defaultdict(list)

    for p in points: 
        groups[(p["lat"],p["lon"])].append(p) 
    return list(groups.values()); 