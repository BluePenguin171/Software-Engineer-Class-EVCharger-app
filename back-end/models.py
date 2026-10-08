from pydantic import BaseModel,Field,PositiveInt,field_serializer,AnyUrl,model_validator
from typing import Literal,Optional,Set,Self
from datetime import datetime 


StatusVals = Literal[ "available", "charging", "reserved", "malfunction", "offline" ]
provider_name = "bestPowerGR"

class ChargePoints(BaseModel): 
    '''
    when you want to add a point in the database :
    **p.model_dump(context={"turn_off_flag": True})
    '''
    pointid : int 
    lat: float = Field(ge=-90, le=90)   #Latitude in decimal degrees -90 < lat < 90
    lon: float = Field(ge=-180, le=180) #Longitude in decimal degrees -180 < lon < 180
    status  : Optional[StatusVals] = "offline"   
    cap : Optional[PositiveInt] = None
    reservation_endtime: Optional[datetime] = None
    kwhprice: float = Field(default=1.0, ge=0)

    @field_serializer("lat", "lon", when_used="always")                #Format lat,lon
    def serialize_floats(self, v: float,info) -> str | float:
        if info.context and info.context.get("turn_off_flag"):
            return v
        return str(v)

    @field_serializer("reservation_endtime", when_used="unless-none")        #Format time 
    def serialize_datetime(self, v: datetime,info) -> str:
        if info.context and info.context.get("turn_off_flag"):
            return v
        return v.strftime("%Y-%m-%d %H:%M")


    def data_dict(self, exclude: Optional[Set[str]] = None) -> dict:    #use this to add provider name , with exclude parameter optional 
        exclude = exclude or set() #If exclude is None (default), it assigns an empty set.
        data = self.model_dump(exclude=exclude)
        return {"providerName": provider_name, **data}



    model_config = {     
        "from_attributes": True
    }





class ChargingSessionHistory(BaseModel): #only the completed transactions here
    pointid: int  # FK → ChargePoint

    starttime: datetime
    endtime: datetime

    startsoc: int = Field(ge=0, le=100)     #state of charge
    endsoc: int = Field(ge=0, le=100)

    totalkwh: float = Field(gt=0)
    kwhprice: float = Field(ge=0)
    amount: float = Field(ge=0)    #money money

    @model_validator(mode = 'after')
    def check_soc_and_time(self) -> Self:
        if self.starttime >= self.endtime:
            raise ValueError('endtime must be after starttime')
        if self.startsoc > self.endsoc:
            raise ValueError('endsoc must be greater than or equal to startsoc')
        return self

    @model_validator(mode = 'after') 
    def check_amount(self) -> Self:
        total = self.totalkwh * self.kwhprice 
        if self.amount != total: 
            raise ValueError(f"Total amount should be totalkwh*kwhprice={total}")
        return self
    
    @field_serializer("starttime","endtime", when_used="unless-none")        #Format time 
    def serialize_datetime(self, v: datetime,info) -> str:
        if info.context and info.context.get("turn_off_flag"):
            return v
        return v.strftime("%Y-%m-%d %H:%M")

class StatusHistory(BaseModel): 
    pointid: int  # FK → ChargePoint

    timeref: datetime

    old_state: StatusVals
    new_state: StatusVals

    @field_serializer("timeref", when_used="unless-none")        #Format time 
    def serialize_datetime(self, v: datetime,info) -> str:
        if info.context and info.context.get("turn_off_flag"):
            return v
        return v.strftime("%Y-%m-%d %H:%M")



class ErrorLog(BaseModel):
    call : AnyUrl                          #το πλήρες url της κλήσης
    timeref : Optional[datetime] = None                   #το timestamp της κλήσης
    originator : str                      #IP προέλευσης της κλήσης
    return_code : Optional[int]  = None         #Ο http κωδικός επιστροφής
    error : str                           #περιγραφή του σφάλματος
    debuginfo : str                       #λοιπά αναλυτικά στοιχεία διερεύνησης 

    
    @field_serializer("timeref", when_used="unless-none")        #Format time 
    def serialize_datetime(self, v: datetime,info) -> str:
        if info.context and info.context.get("turn_off_flag"):
            return v
        return v.strftime("%Y-%m-%d %H:%M")
    
    @field_serializer("call")
    def serialize_call(self, v: AnyUrl, _info):
        return str(v)


class  UpdatePoint(BaseModel): #for endpoint d. updpoint 
    status  : Optional[StatusVals] = None  
    kwhprice: Optional[float] = Field(default=None, ge=0)


class Reservation(BaseModel):
    pointid : int # FK → ChargePoint
    endtime: datetime

    @field_serializer("endtime", when_used="unless-none")        #Format time 
    def serialize_datetime(self, v: datetime,info) -> str:
        if info.context and info.context.get("turn_off_flag"):
            return v
        return v.strftime("%Y-%m-%d %H:%M")

if __name__ == "__main__": 
    t = ChargePoints(pointid = 5, lat = 43.3, lon = 173.5, status = "available",cap = 20)
    print(t.model_dump_json(indent=2))