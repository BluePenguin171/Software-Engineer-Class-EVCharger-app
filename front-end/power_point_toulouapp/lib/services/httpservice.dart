import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:latlong2/latlong.dart';
import 'package:power_point_toulouapp/Models/charger.dart';
import 'package:power_point_toulouapp/Models/chargerCluster.dart';

final String host = '192.168.1.10:9876';

Future<Map<LatLng, ChargerCluster>?> fetchBoundedPoints(List<double> bounds) async{
  final String endpoint = '/frontend/points/bounded';

  //lat and lots for visible area box
  final double south = bounds[0];
  final double north = bounds[1]; 
  final double east = bounds[3]; 
  final double west = bounds[2]; 

  final Uri uri = Uri.http(
    host,
    endpoint,
    {
      'south': south.toString(),
      'north': north.toString(),
      'west':  west.toString(),
      'east':  east.toString(),
    },
  );

  final response = await http.get(uri);
  if(response.statusCode == 204) {return null;} 
  else if(response.statusCode > 400) {
    throw Exception(
    'HTTP ${response.statusCode}: ${response.body}',
    );
  }
  final List<dynamic> jsonList = jsonDecode(response.body);

  final clusterMap = Map<LatLng, ChargerCluster>.fromEntries(
    jsonList.map((innerListDynamic) {
      // innerListDynamic is a List<dynamic>
      final innerList = innerListDynamic as List<dynamic>;

      final chargers = innerList
          .map((item) => Charger.fromJson(item as Map<String, dynamic>))
          .toList();

      final cluster = ChargerCluster(chargers);
      final LatLng location = chargers.first.location;

      return MapEntry(location, cluster);
    }),
  );

  return clusterMap; 
}


Future<bool> reservePoint(int pointId, {int? minutes}) async {
  final String endpoint = minutes == null
      ? '/reserve/$pointId'
      : '/reserve/$pointId/$minutes';

  final Uri uri = Uri.http(host, endpoint);

  final response = await http.post(uri);

  if (response.statusCode != 200) {
    throw Exception('Something went wrong. Please try again later.');
  }

  final Map<String, dynamic> json =
      jsonDecode(response.body) as Map<String, dynamic>;

  if (json['reservationendtime'] == '1970-01-01 00:00') {
    throw Exception('Sorry, the point is no longer available!');
  }

  return true;
}

Future<bool> cancelReservation(int pointId) async {
  final String endpoint = '/frontend/cancel/$pointId';
  final Uri uri = Uri.http(host, endpoint);

  final response = await http.post(uri);

  if (response.statusCode >= 400) {
    throw Exception('Failed to cancel reservation. Please try again later.');
  }

  return true;
}