import 'package:latlong2/latlong.dart';



enum Status { available, malfunction, offline, charging, reserved }
extension StatusX on Status {
  String toStr() => name;

  static Status fromString(String value) =>
      Status.values.byName(value);
}

class Charger {
  final int pointId;
  final LatLng location;
  Status status;

  Charger({
    required this.pointId,
    required this.location,
    required this.status,
  });


  factory Charger.fromJson(Map<String,dynamic> json){
    return Charger(
      pointId: json['pointid'], 
      location: LatLng(double.parse(json['lat']),double.parse(json['lon'])),
      status: StatusX.fromString(json['status']),
    );
  }
}