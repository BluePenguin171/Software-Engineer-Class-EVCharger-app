import 'package:power_point_toulouapp/Models/charger.dart';

class ChargerCluster {
  static int _totalId = 0;

  final int id;
  final List<Charger> pointList;
  late  String aggregatedStatus;

  ChargerCluster(this.pointList) : id = _totalId++ {
    final String startStatus = pointList.first.status.toStr();
    bool multicolor = false;
    bool active = false;

    for (final p in pointList) {
      final tempStatus = p.status.toStr();

      if (tempStatus != startStatus) {
        multicolor = true;
      }

      if (multicolor &&
          ["available", "reserved","charging"].contains(tempStatus)) {
        active = true;
        break;
      }
    }

    if (!multicolor) {
      aggregatedStatus = startStatus;
    } else if (active) {
      aggregatedStatus = "multicolor";
    } else {
      aggregatedStatus = "malfunction";
    }
  }
}