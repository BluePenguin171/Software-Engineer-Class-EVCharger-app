import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:flutter_map_marker_cluster/flutter_map_marker_cluster.dart';
import 'package:flutter_svg/svg.dart';
import 'package:latlong2/latlong.dart';
import 'package:power_point_toulouapp/Models/charger.dart';
import 'package:power_point_toulouapp/Models/chargerCluster.dart';
import 'package:power_point_toulouapp/services/httpservice.dart';


class MapBuilder extends StatefulWidget {
  final LatLng center;
  final double zoom;

  const MapBuilder({super.key , required this.zoom, required this.center});

  @override
  State<MapBuilder> createState() => _MapBuilderState();
}
class _MapBuilderState extends State<MapBuilder> {
  late MapController _mapController;
  final PopupController _popupController = PopupController();
  LatLng pos = LatLng(37.9796, 23.7827);
  List<Marker>? markers = []; 
  Map<LatLng, ChargerCluster>? all_points = {};
  late bool waiting;
  bool reserved = false; 
  Charger? reserved_point;
  // Edge positions
  LatLng? topLeftCorner;
  LatLng? bottomRightCorner;

  @override
  void initState() {
    super.initState();
    _mapController = MapController();
    waiting = false;
  }

  void _updateEdgeMarkers(MapCamera camera) {
    if(waiting) return; 
    final bounds = camera.visibleBounds;
    final center = camera.center;
    late bool need_new_points;
    try{
    need_new_points =
      center.latitude >  topLeftCorner!.latitude ||     //check if the center escapes 
      center.latitude <  bottomRightCorner!.latitude ||  //the visible bound rectangle 
      center.longitude < topLeftCorner!.longitude ||
      center.longitude > bottomRightCorner!.longitude;
    need_new_points = need_new_points ||            //check if zoom out so much that needs update 
      (bounds.north - bounds.south) > 3*(topLeftCorner!.latitude - bottomRightCorner!.latitude); 
    }
    catch(_){
      need_new_points = true;   //in case that corners has not initiallized
      topLeftCorner = LatLng(bounds.north, bounds.west);
      bottomRightCorner = LatLng(bounds.south, bounds.east);
    }
    
    pos = camera.center;
    if(need_new_points)
      {
        List<double> vis_box = [
          bottomRightCorner!.latitude.toDouble(), //south
          topLeftCorner!.latitude.toDouble(),     //north
          topLeftCorner!.longitude.toDouble(),    //west
          bottomRightCorner!.longitude.toDouble()   //east
          ];
        waiting = true;
        fetchBoundedPoints(vis_box).then((points) { 
          waiting = false;  //enable new http requests
          if(points == null) return; //if no points there is nothing to do

          //add the new points to list
          if(all_points == null) { all_points = points; }
          else {
            for(var loc in points.keys){
              if(!all_points!.containsKey(loc))  all_points![loc] = points[loc]!;
            }
          }

          setState(() {
            markers = _buildMarkers(all_points);
            waiting = false;
          });
        }
        );
        topLeftCorner = LatLng(bounds.north, bounds.west);
        bottomRightCorner = LatLng(bounds.south, bounds.east);
      }
  }


  List<Marker> _buildMarkers(Map<LatLng, ChargerCluster>? points) {
    if (points == null || points.isEmpty) return [];

    return points.entries.map((entry) {
      final loc = entry.key;
      final cluster = entry.value;

      return Marker(
        key: ValueKey(cluster.id),
        point: loc, // key is the LatLng
        width: 40,
        height: 40,
        child: SvgPicture.asset(
          "assets/icons/${cluster.aggregatedStatus}.svg",
        ),
      );
    }).toList();
  }


  @override
  Widget build(BuildContext context) {
    return Stack(
      children: [
        FlutterMap(
          mapController: _mapController,
          options: MapOptions(
            initialCenter: widget.center,
            initialZoom: widget.zoom,
             onTap: (_, _ ) => _popupController.hideAllPopups(),
            onMapReady: () =>   _updateEdgeMarkers(_mapController.camera),
            onPositionChanged: (camera, _) {
              _updateEdgeMarkers(camera);
            },
          ),
          children: [
            TileLayer(
              urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
              userAgentPackageName: 'com.semester_project_car_chargers.ntua.edu',
            ),
            if (markers != null && markers!.isNotEmpty)
                PopupMarkerLayer(
                  options: PopupMarkerLayerOptions(
                    markers: markers!,
                    popupController: _popupController,
                    popupDisplayOptions: PopupDisplayOptions(
                    builder: (BuildContext context, Marker marker) => _popUpCard(context, marker)
                    ),
                    markerTapBehavior: MarkerTapBehavior.custom(
                      (PopupSpec spec, PopupState state, PopupController controller) {
                        controller.hideAllPopups();
                        controller.togglePopupSpec(spec);
                      },
                    ),
                  ),
                ),
          ],
        ),
        if (reserved)
          Positioned(
            bottom: 20,
            right: 20,
            child: FloatingActionButton(
              onPressed: _cancelReservation,
              backgroundColor: Colors.red,
              tooltip: 'Cancel reservation',
              child: const Icon(Icons.close),
            ),
          ),
      ],
    );
  }

  Widget _popUpCard(BuildContext context, Marker marker){
    //retrieve point list 
    List<Charger> points = all_points![marker.point]!.pointList;


    return SizedBox(
      width: 300,
      child: Card(
          elevation: 4,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
          shadowColor: const Color.fromARGB(255, 1, 41, 73),
          child: ConstrainedBox(
            constraints: const BoxConstraints(
              maxHeight: 250, // max height for the Card
            ),
            child: Padding(
              padding: const EdgeInsets.all(8.0),
              child: ListView.builder(
                shrinkWrap: true, // ensures it fits inside the Card
                itemCount: points.length,
                itemBuilder: (context, index) {
                  final p = points[index];
                  final pointid = p.pointId.toString();
                  final pointstatus = p.status.toStr();
                  final isAvailable = pointstatus.toLowerCase() == 'available';
                  return ListTile(
                    leading: const Icon(Icons.ev_station, size: 30), // electric/gas station icon
                    title: Text(
                      pointid, // display pointId
                      style: const TextStyle(fontWeight: FontWeight.bold),
                    ),
                    trailing: ElevatedButton(
                          onPressed: isAvailable
                              ? () {
                                   _reserveWithOverlay(context, p.pointId, p.location);
                                }
                              : null, // null disables the button
                          style: ElevatedButton.styleFrom(
                            backgroundColor: isAvailable
                                ? null
                                : Colors.grey.shade400, // faded look if disabled
                          ),
                          child: Text(
                            pointstatus,
                            style: TextStyle(
                              color: isAvailable ? null : Colors.grey.shade700,
                            ),
                          ),
                        ),
                    contentPadding: const EdgeInsets.symmetric(vertical: 4.0, horizontal: 8.0),
                  );
                },
              ),
            ),
          ),
        ),
    );
  }


  Future<void> _reserveWithOverlay(BuildContext context, int pointId, LatLng loc) async {
      int? minutes;
      // Ask the user for confirmation
      final bool? confirm = await showDialog<bool>(
        context: context,
        builder: (_) => AlertDialog(
          title: const Text('Reservation'),
          content:  Text('Reserve point with id : $pointId ?'),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(context).pop(false), // No
              child: const Text('No'),
            ),
            TextButton(
              onPressed: () => Navigator.of(context).pop(true), // Yes
              child: const Text('Yes'),
            ),
          ],
        ),
      );
      
      
      //If Yes, ask for minutes
      if(!reserved){
      if (confirm == true) {
        final TextEditingController controller = TextEditingController();
        bool cancel = false;
        await showDialog(
          context: context,
          builder: (_) => AlertDialog(
            title: const Text('Enter minutes'),
            content: TextField(
              controller: controller,
              keyboardType: TextInputType.number,
              decoration: const InputDecoration(
                hintText: 'Enter minutes (0–90)',
              ),
            ),
            actions: [
              TextButton(
                onPressed: () {
                  cancel = true;          // set flag
                  Navigator.of(context).pop();
                }, // Cancel
                child: const Text('Cancel'),
              ),
              TextButton(
                onPressed: () {
                  final input = int.tryParse(controller.text);
                  if (input != null && input >= 0 && input <= 90) {
                    minutes = input;
                    Navigator.of(context).pop();
                  } else if (input == null) {
                    minutes = null; //default value
                  }
                  else{
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(content: Text('Please enter a number between 0 and 90')),
                    );
                  }
                },
                child: const Text('OK'),
              ),
            ],
          ),
        );

        if(cancel) return; 
      }
      else return; 
      }
      
      // Show loading overlay
      if(!reserved){
        showDialog(
          context: context,
          barrierDismissible: false, // prevent closing while loading
          builder: (_) {
            return const AlertDialog(
              content: Row(
                children: [
                  CircularProgressIndicator(),
                  SizedBox(width: 16),
                  Text('Please wait...'),
                ],
              ),
            );
          },
        );
      }
      else{
        showDialog(
          context: context,
          builder: (_) => AlertDialog(
            title: const Text('Error'),
            content: Text("Sorry, you can only reserve one point at a time!"),
            actions: [
              TextButton(
                onPressed: () => Navigator.of(context).pop(),
                child: const Text('OK'),
              ),
            ],
          ),
        );

        return;
      }

      


      try {
        await reservePoint(pointId, minutes: minutes);

        // Close loading dialog
        Navigator.of(context).pop();
        setState(() {
          reserved = true;
          all_points![loc]!.aggregatedStatus = "multicolor"; 
          for(Charger c in all_points![loc]!.pointList){
            if(c.pointId == pointId) {
              c.status = StatusX.fromString("reserved"); 
              reserved_point = c;
              break;
            }
          }
        });
        // Show success dialog
        showDialog(
          context: context,
          builder: (_) => AlertDialog(
            title: const Text('Success'),
            content: const Text('Reservation successful!'),
            actions: [
              TextButton(
                onPressed: () => Navigator.of(context).pop(),
                child: const Text('OK'),
              ),
            ],
          ),
        );
      } catch (e) {
        // Close loading dialog
        Navigator.of(context).pop();

        // Show error dialog
        showDialog(
          context: context,
          builder: (_) => AlertDialog(
            title: const Text('Error'),
            content: Text(e.toString().replaceFirst('Exception: ', '')),
            actions: [
              TextButton(
                onPressed: () => Navigator.of(context).pop(),
                child: const Text('OK'),
              ),
            ],
          ),
        );
      }
    }

  Future<void> _cancelReservation() async {
    if (reserved_point == null) return;

    Charger p = reserved_point!;

    // Ask the user for confirmation
    final bool? confirm = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('Cancel reservation'),
        content: const Text('Are you sure you want to cancel your reservation?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false), // No
            child: const Text('No'),
          ),
          TextButton(
            onPressed: () => Navigator.of(context).pop(true), // Yes
            child: const Text('Yes'),
          ),
        ],
      ),
    );

    if (confirm != true) return; // user cancelled


    try {
      // Show loading dialog while cancelling
      showDialog(
        context: context,
        barrierDismissible: false,
        builder: (_) => const AlertDialog(
          content: Row(
            children: [
              CircularProgressIndicator(),
              SizedBox(width: 16),
              Text('Cancelling reservation...'),
            ],
          ),
        ),
      );

      // Call API
      await cancelReservation(p.pointId);

      Navigator.of(context).pop(); // close loading dialog

      setState(() {
        reserved = false;
        all_points![p.location]!.aggregatedStatus = "multicolor";
        for (Charger c in all_points![p.location]!.pointList) {
          if (c.pointId == p.pointId) {
            c.status = StatusX.fromString("available");
            break;
          }
        }
        reserved_point = null;
      });

      // Show success dialog
      showDialog(
        context: context,
        builder: (_) => AlertDialog(
          title: const Text('Success'),
          content: const Text('Reservation cancelled!'),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(context).pop(),
              child: const Text('OK'),
            ),
          ],
        ),
      );
    } catch (e) {
      Navigator.of(context).pop(); // close loading dialog if open

      // Show error dialog
      showDialog(
        context: context,
        builder: (_) => AlertDialog(
          title: const Text('Error'),
          content: Text('Please try again later!'),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(context).pop(),
              child: const Text('OK'),
            ),
          ],
        ),
      );
    }
  }

}